"""Module 1b - Recurring schedule: flight templates and the generator that turns them into dated flights.

A template is "6E6001 DEL->BOM at 06:10, daily". Generating N days creates one real, dated flight (with a
price, gate and arrival time) for every template and every day it runs. Generation is idempotent: running it
twice never duplicates flights, and a flight an administrator cancelled is not recreated.
"""
import bisect
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from ..access import require_role
from ..config import (GATE_BUFFER_MINUTES, GATES, MAX_FARE, MIN_FARE, SCHEDULE_HORIZON_DAYS)
from ..errors import BusinessRuleError, NotFoundError
from ..models import FlightTemplate, Role, User, fmt_dt, to_dt
from ..network import build_default_templates
from .. import validators as v

ACTIVE = ("SCHEDULED", "DELAYED", "BOARDING")


@dataclass(frozen=True)
class GenerationResult:
    created: int            # new flights inserted
    skipped: int            # already existed (or were cancelled earlier) so left alone
    through: date           # last day covered by this run

    def summary(self) -> str:
        return (f"Created {self.created:,} flight(s); {self.skipped:,} already existed. "
                f"Schedule now covers up to {self.through:%Y-%m-%d}.")


def dynamic_fare(base_fare: int, departure: datetime, now: datetime) -> int:
    """Price one dated flight from its template's base fare: peak hours and Fri/Sun cost more, red-eyes less,
    last-minute seats cost more and very early bookings less. Always within the allowed fare range."""
    factor = 1.0
    if 6 <= departure.hour < 10 or 17 <= departure.hour < 21:
        factor *= 1.12
    elif departure.hour >= 22 or departure.hour < 5:
        factor *= 0.88
    if departure.isoweekday() in (5, 7):
        factor *= 1.07
    days_ahead = (departure - now).total_seconds() / 86400
    if days_ahead < 3:
        factor *= 1.25
    elif days_ahead < 8:
        factor *= 1.10
    elif days_ahead > 21:
        factor *= 0.93
    fare = int(round(base_fare * factor / 10.0)) * 10
    return max(MIN_FARE, min(MAX_FARE, fare))


class _GatePlanner:
    """Hands out gates so that no two active flights at one gate depart within the buffer (kept in memory so
    thousands of flights can be planned without a query each)."""

    def __init__(self, busy: Dict[str, List[datetime]]):
        self.busy = {gate: sorted(times) for gate, times in busy.items()}
        self.buffer = timedelta(minutes=GATE_BUFFER_MINUTES)
        self.counter = 0

    def assign(self, departure: datetime) -> Optional[str]:
        self.counter += 1
        start = (self.counter * 7) % len(GATES)          # spread flights over all terminals
        for i in range(len(GATES)):
            gate = GATES[(start + i) % len(GATES)]
            times = self.busy.setdefault(gate, [])
            pos = bisect.bisect_left(times, departure)
            before_ok = pos == 0 or departure - times[pos - 1] >= self.buffer
            after_ok = pos == len(times) or times[pos] - departure >= self.buffer
            if before_ok and after_ok:
                times.insert(pos, departure)
                return gate
        return None                                       # every gate busy: leave unassigned for the admin


class ScheduleService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ----- templates -----
    def list_templates(self, active_only: bool = False) -> List[FlightTemplate]:
        sql = "SELECT * FROM flight_templates" + (" WHERE active = 1" if active_only else "")
        rows = self.conn.execute(sql + " ORDER BY origin, destination, dep_time").fetchall()
        return [FlightTemplate.from_row(r) for r in rows]

    def get_template(self, template_id: int) -> FlightTemplate:
        row = self.conn.execute("SELECT * FROM flight_templates WHERE template_id = ?", (template_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Schedule template {template_id} not found.")
        return FlightTemplate.from_row(row)

    def add_template(self, actor: User, flight_no, airline, origin, destination, dep_time, duration,
                     days, rows, base_fare) -> FlightTemplate:
        require_role(actor, Role.ADMIN)
        data = dict(flight_no=v.validate_flight_no(flight_no), airline=v.validate_airline(airline))
        data["origin"], data["destination"] = v.validate_route(origin, destination)
        data.update(dep_time=v.validate_dep_time(dep_time), duration_min=v.validate_duration(duration),
                    days=v.parse_days(days), rows=v.validate_rows(rows), base_fare=v.validate_fare(base_fare))
        if self.conn.execute("SELECT 1 FROM flight_templates WHERE flight_no = ?", (data["flight_no"],)).fetchone():
            raise BusinessRuleError(f"A recurring service {data['flight_no']} already exists.")
        cur = self.conn.execute(
            "INSERT INTO flight_templates (flight_no, airline, origin, destination, dep_time, duration_min,"
            " days, rows, base_fare) VALUES (:flight_no,:airline,:origin,:destination,:dep_time,:duration_min,"
            ":days,:rows,:base_fare)", data)
        self.conn.commit()
        return self.get_template(cur.lastrowid)

    def set_active(self, actor: User, template_id: int, active: bool) -> FlightTemplate:
        """Switch a recurring service on or off. Already-generated flights are not touched."""
        require_role(actor, Role.ADMIN)
        self.get_template(template_id)
        self.conn.execute("UPDATE flight_templates SET active = ? WHERE template_id = ?",
                          (1 if active else 0, template_id))
        self.conn.commit()
        return self.get_template(template_id)

    def seed_default_network(self) -> int:
        """Add every built-in recurring service that is not in the table yet and return how many were added.
        On a fresh database that is the whole network; on an existing one it only brings in newer routes
        (for example a newly added airport) and never touches or re-activates services already there."""
        have = {r[0] for r in self.conn.execute("SELECT flight_no FROM flight_templates")}
        rows = [t for t in build_default_templates() if t["flight_no"] not in have]
        if rows:
            self.conn.executemany(
                "INSERT OR IGNORE INTO flight_templates (flight_no, airline, origin, destination, dep_time,"
                " duration_min, days, rows, base_fare) VALUES (:flight_no,:airline,:origin,:destination,"
                ":dep_time,:duration_min,:days,:rows,:base_fare)", rows)
            self.conn.commit()
        return len(rows)

    # ----- generation -----
    def generate_flights(self, actor: User, days, now: Optional[datetime] = None) -> GenerationResult:
        """Administrator action: create dated flights for the next `days` days."""
        require_role(actor, Role.ADMIN)
        return self._generate(v.validate_horizon_days(days), now or datetime.now())

    def ensure_schedule(self, days: int = SCHEDULE_HORIZON_DAYS, now: Optional[datetime] = None) -> GenerationResult:
        """Start-up routine: seed the default network on a fresh database, then top the schedule up so
        flights always exist for the next `days` days."""
        self.seed_default_network()
        return self._generate(days, now or datetime.now())

    def schedule_end(self) -> Optional[str]:
        """Date of the last generated departure (YYYY-MM-DD) or None."""
        row = self.conn.execute("SELECT MAX(substr(departure, 1, 10)) FROM flights").fetchone()
        return row[0]

    def _generate(self, days: int, now: datetime) -> GenerationResult:
        now = now.replace(second=0, microsecond=0)
        first_day = now.date()
        last_day = first_day + timedelta(days=days - 1)
        existing = {(r[0], r[1]) for r in self.conn.execute(
            "SELECT flight_no, substr(departure, 1, 10) FROM flights WHERE departure >= ? AND departure < ?",
            (first_day.isoformat(), (last_day + timedelta(days=1)).isoformat()))}
        busy: Dict[str, List[datetime]] = {}
        for r in self.conn.execute(
                "SELECT gate, departure FROM flights WHERE gate IS NOT NULL AND status IN (?,?,?) AND departure >= ?",
                (*ACTIVE, (first_day - timedelta(days=1)).isoformat())):
            busy.setdefault(r[0], []).append(to_dt(r[1]))
        planner = _GatePlanner(busy)

        new_rows, skipped = [], 0
        for tpl in self.list_templates(active_only=True):
            hour, minute = (int(x) for x in tpl.dep_time.split(":"))
            for offset in range(days):
                day = first_day + timedelta(days=offset)
                if str(day.isoweekday()) not in tpl.days:
                    continue
                departure = datetime(day.year, day.month, day.day, hour, minute)
                if departure <= now:
                    continue                                          # never create flights in the past
                if (tpl.flight_no, day.isoformat()) in existing:
                    skipped += 1
                    continue
                arrival = departure + timedelta(minutes=tpl.duration_min)
                new_rows.append((tpl.flight_no, tpl.airline, tpl.origin, tpl.destination, fmt_dt(departure),
                                 fmt_dt(arrival), planner.assign(departure), tpl.rows,
                                 dynamic_fare(tpl.base_fare, departure, now), "SCHEDULED"))
        before = self.conn.total_changes
        self.conn.executemany(
            "INSERT OR IGNORE INTO flights (flight_no, airline, origin, destination, departure, arrival, gate,"
            " rows, fare, status) VALUES (?,?,?,?,?,?,?,?,?,?)", new_rows)
        self.conn.commit()
        created = self.conn.total_changes - before
        return GenerationResult(created, skipped + (len(new_rows) - created), last_day)
