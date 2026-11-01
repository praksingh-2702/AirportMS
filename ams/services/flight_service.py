"""Module 1 - Flight scheduling: add, update, cancel, view flights and manage gates."""
import sqlite3
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from ..access import require_role
from ..config import GATE_BUFFER_MINUTES, SEAT_COLUMNS
from ..errors import BusinessRuleError, NotFoundError, ValidationError
from ..models import BookingStatus, Flight, FlightStatus, Role, fmt_dt, to_dt
from .. import validators as v
from ..payments_core import refund_flight

# Flights that still occupy a gate
ACTIVE_STATUSES = (FlightStatus.SCHEDULED, FlightStatus.DELAYED, FlightStatus.BOARDING)

# Allowed state transitions (see the Flight state-chart diagram)
FLIGHT_TRANSITIONS = {
    FlightStatus.SCHEDULED: {FlightStatus.DELAYED, FlightStatus.BOARDING, FlightStatus.CANCELLED},
    FlightStatus.DELAYED: {FlightStatus.SCHEDULED, FlightStatus.BOARDING, FlightStatus.CANCELLED},
    FlightStatus.BOARDING: {FlightStatus.DELAYED, FlightStatus.DEPARTED},
    FlightStatus.DEPARTED: set(),
    FlightStatus.CANCELLED: set(),
}


class FlightService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ----- queries -----
    def get_flight(self, flight_id: int) -> Flight:
        row = self.conn.execute("SELECT * FROM flights WHERE flight_id = ?", (flight_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Flight with id {flight_id} not found.")
        return Flight.from_row(row)

    @staticmethod
    def _filters(statuses, date, search):
        clauses, params = [], []
        if statuses:
            statuses = [FlightStatus(s).value for s in statuses]
            clauses.append(f"status IN ({','.join('?' * len(statuses))})")
            params += statuses
        day = v.parse_date(date)
        if day:
            clauses.append("substr(departure,1,10) = ?")
            params.append(day)
        text = (search or "").strip().upper()
        if text:
            clauses.append("(flight_no LIKE ? OR origin = ? OR destination = ? OR upper(airline) LIKE ?)")
            params += [f"%{text}%", text, text, f"%{text}%"]
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def list_flights(self, statuses: Optional[Iterable[FlightStatus]] = None, date=None, search=None,
                     limit: Optional[int] = None) -> List[Flight]:
        """Flights in departure order. Optional filters: status list, one date (YYYY-MM-DD), free text
        (flight number, airline or airport code) and a row limit."""
        where, params = self._filters(statuses, date, search)
        sql = "SELECT * FROM flights" + where + " ORDER BY departure"
        if limit:
            sql += " LIMIT ?"
            params = params + [int(limit)]
        return [Flight.from_row(r) for r in self.conn.execute(sql, params).fetchall()]

    def count_flights(self, statuses=None, date=None, search=None) -> int:
        where, params = self._filters(statuses, date, search)
        return self.conn.execute("SELECT COUNT(*) FROM flights" + where, params).fetchone()[0]

    def booked_counts(self) -> dict:
        """flight_id -> number of active bookings, for every flight, in one query."""
        return {r[0]: r[1] for r in self.conn.execute(
            "SELECT flight_id, COUNT(*) FROM bookings WHERE status <> 'CANCELLED' GROUP BY flight_id")}

    def booked_count(self, flight_id: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE flight_id = ? AND status <> 'CANCELLED'",
            (flight_id,)).fetchone()[0]

    def list_airports(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT origin AS code FROM flights UNION SELECT destination FROM flights ORDER BY code")
        return [r["code"] for r in rows]

    # ----- gate management -----
    def is_gate_available(self, gate: Optional[str], departure: datetime,
                          exclude_flight_id: Optional[int] = None) -> bool:
        """A gate is free if no other active flight at it departs within the buffer."""
        if gate is None:
            return True
        rows = self.conn.execute(
            "SELECT flight_id, departure FROM flights WHERE gate = ? AND status IN (?,?,?)",
            (gate, *[s.value for s in ACTIVE_STATUSES])).fetchall()
        for row in rows:
            if exclude_flight_id is not None and row["flight_id"] == exclude_flight_id:
                continue
            gap_minutes = abs((to_dt(row["departure"]) - departure).total_seconds()) / 60
            if gap_minutes < GATE_BUFFER_MINUTES:
                return False
        return True

    def _check_gate(self, gate, departure, exclude_flight_id=None):
        if not self.is_gate_available(gate, departure, exclude_flight_id):
            raise BusinessRuleError(
                f"Gate {gate} is already assigned to another flight departing within "
                f"{GATE_BUFFER_MINUTES} minutes of {fmt_dt(departure)}.")

    def assign_gate(self, actor, flight_id: int, gate) -> Flight:
        require_role(actor, Role.ADMIN)
        flight = self.get_flight(flight_id)
        self._ensure_editable(flight)
        gate = v.validate_gate(gate)
        if gate is None:
            raise ValidationError("Enter a gate to assign, e.g. B7.")
        self._check_gate(gate, flight.departure, flight_id)
        self.conn.execute("UPDATE flights SET gate = ? WHERE flight_id = ?", (gate, flight_id))
        self.conn.commit()
        return self.get_flight(flight_id)

    # ----- add / update -----
    def _validate_fields(self, flight_no, airline, origin, destination, departure, arrival,
                         rows, fare, gate, now):
        data = {
            "flight_no": v.validate_flight_no(flight_no),
            "airline": v.validate_airline(airline),
        }
        data["origin"], data["destination"] = v.validate_route(origin, destination)
        dep = v.parse_datetime(departure, "Departure")
        arr = v.parse_datetime(arrival, "Arrival")
        v.validate_schedule(dep, arr, now)
        data.update(departure=dep, arrival=arr, rows=v.validate_rows(rows),
                    fare=v.validate_fare(fare), gate=v.validate_gate(gate))
        return data

    def _check_duplicate(self, flight_no, departure, exclude_flight_id=None):
        row = self.conn.execute(
            "SELECT flight_id FROM flights WHERE flight_no = ? AND substr(departure,1,10) = ?"
            " AND status <> 'CANCELLED'",
            (flight_no, departure.strftime("%Y-%m-%d"))).fetchone()
        if row and row["flight_id"] != exclude_flight_id:
            raise BusinessRuleError(f"Flight {flight_no} is already scheduled on {departure:%Y-%m-%d}.")

    def add_flight(self, actor, flight_no, airline, origin, destination, departure, arrival,
                   rows, fare, gate=None, now: Optional[datetime] = None) -> Flight:
        require_role(actor, Role.ADMIN)
        d = self._validate_fields(flight_no, airline, origin, destination, departure, arrival,
                                  rows, fare, gate, now or datetime.now())
        self._check_duplicate(d["flight_no"], d["departure"])
        self._check_gate(d["gate"], d["departure"])
        cur = self.conn.execute(
            "INSERT INTO flights (flight_no, airline, origin, destination, departure, arrival,"
            " gate, rows, fare, status) VALUES (?,?,?,?,?,?,?,?,?,'SCHEDULED')",
            (d["flight_no"], d["airline"], d["origin"], d["destination"], fmt_dt(d["departure"]),
             fmt_dt(d["arrival"]), d["gate"], d["rows"], d["fare"]))
        self.conn.commit()
        return self.get_flight(cur.lastrowid)

    def update_flight(self, actor, flight_id: int, flight_no, airline, origin, destination,
                      departure, arrival, rows, fare, gate=None,
                      now: Optional[datetime] = None) -> Flight:
        require_role(actor, Role.ADMIN)
        flight = self.get_flight(flight_id)
        self._ensure_editable(flight)
        d = self._validate_fields(flight_no, airline, origin, destination, departure, arrival,
                                  rows, fare, gate, now or datetime.now())
        if self.booked_count(flight_id) and (d["origin"], d["destination"]) != (flight.origin, flight.destination):
            raise BusinessRuleError("Route cannot be changed after tickets have been booked.")
        highest = self._highest_booked_row(flight_id)
        if d["rows"] < highest:
            raise BusinessRuleError(f"Cannot reduce rows to {d['rows']}: seats up to row {highest} are booked.")
        self._check_duplicate(d["flight_no"], d["departure"], flight_id)
        self._check_gate(d["gate"], d["departure"], flight_id)
        self.conn.execute(
            "UPDATE flights SET flight_no=?, airline=?, origin=?, destination=?, departure=?,"
            " arrival=?, gate=?, rows=?, fare=? WHERE flight_id=?",
            (d["flight_no"], d["airline"], d["origin"], d["destination"], fmt_dt(d["departure"]),
             fmt_dt(d["arrival"]), d["gate"], d["rows"], d["fare"], flight_id))
        self.conn.commit()
        return self.get_flight(flight_id)

    def _highest_booked_row(self, flight_id: int) -> int:
        seats = self.conn.execute(
            "SELECT seat FROM bookings WHERE flight_id = ? AND status <> 'CANCELLED'", (flight_id,))
        return max((int(r["seat"].rstrip(SEAT_COLUMNS)) for r in seats), default=0)

    @staticmethod
    def _ensure_editable(flight: Flight) -> None:
        if flight.status in (FlightStatus.DEPARTED, FlightStatus.CANCELLED):
            raise BusinessRuleError(f"Flight {flight.flight_no} is {flight.status.value} and cannot be changed.")

    # ----- status / cancellation -----
    def change_status(self, actor, flight_id: int, new_status) -> Flight:
        require_role(actor, Role.ADMIN)
        flight = self.get_flight(flight_id)
        try:
            new_status = FlightStatus(new_status)
        except ValueError:
            raise ValidationError(f"Unknown flight status '{new_status}'.") from None
        if new_status not in FLIGHT_TRANSITIONS[flight.status]:
            raise BusinessRuleError(
                f"Flight status cannot change from {flight.status.value} to {new_status.value}.")
        if new_status == FlightStatus.CANCELLED:
            self.cancel_flight(actor, flight_id)
        else:
            self.conn.execute("UPDATE flights SET status = ? WHERE flight_id = ?",
                              (new_status.value, flight_id))
            self.conn.commit()
        return self.get_flight(flight_id)

    def cancel_flight(self, actor, flight_id: int, now: Optional[datetime] = None) -> int:
        """Cancel the flight and all its active bookings (paid ones are refunded in full).
        Returns bookings cancelled."""
        require_role(actor, Role.ADMIN)
        flight = self.get_flight(flight_id)
        if FlightStatus.CANCELLED not in FLIGHT_TRANSITIONS[flight.status]:
            raise BusinessRuleError(f"Flight {flight.flight_no} is {flight.status.value} and cannot be cancelled.")
        refund_flight(self.conn, flight_id, now or datetime.now())
        cur = self.conn.execute(
            "UPDATE bookings SET status = ? WHERE flight_id = ? AND status <> ?",
            (BookingStatus.CANCELLED.value, flight_id, BookingStatus.CANCELLED.value))
        self.conn.execute("UPDATE flights SET status = 'CANCELLED', gate = NULL WHERE flight_id = ?",
                          (flight_id,))
        self.conn.commit()
        return cur.rowcount
