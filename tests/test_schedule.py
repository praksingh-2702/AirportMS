"""Tests for the recurring schedule / flight generator. Test-case IDs SG01-SG26.

NOW (see helpers) is Tuesday 2026-11-10 09:00."""
import re
import unittest
from datetime import datetime, timedelta

from ams.config import GATE_BUFFER_MINUTES, GATES, MAX_FARE, MIN_FARE
from ams.errors import AuthorizationError, BusinessRuleError, NotFoundError, ValidationError
from ams.models import FlightStatus, to_dt
from ams.network import AIRPORTS, build_default_templates
from ams.services import ScheduleService
from ams.services.schedule_service import dynamic_fare
from ams import validators as v
from tests.helpers import NOW, ServiceTestCase


class TestScheduleValidators(unittest.TestCase):
    def test_SG01_dep_time_valid_and_boundaries(self):
        self.assertEqual(v.validate_dep_time("00:00"), "00:00")
        self.assertEqual(v.validate_dep_time(" 23:59 "), "23:59")

    def test_SG02_dep_time_invalid(self):
        for bad in ("24:00", "12:60", "9:30", "0930", "", "ab:cd"):
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_dep_time(bad)

    def test_SG03_duration_boundaries(self):
        self.assertEqual(v.validate_duration("20"), 20)
        self.assertEqual(v.validate_duration("1200"), 1200)
        for bad in ("19", "1201", "abc", ""):
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_duration(bad)

    def test_SG04_parse_days_words_names_and_digits(self):
        self.assertEqual(v.parse_days("Daily"), "1234567")
        self.assertEqual(v.parse_days("weekdays"), "12345")
        self.assertEqual(v.parse_days("Weekends"), "67")
        self.assertEqual(v.parse_days("Fri, mon ,Wed"), "135")
        self.assertEqual(v.parse_days("246"), "246")
        self.assertEqual(v.parse_days("Monday,Sunday"), "17")

    def test_SG05_parse_days_invalid(self):
        for bad in ("", "Funday", "8", "0", "Mon,Xyz"):
            with self.assertRaises(ValidationError, msg=bad):
                v.parse_days(bad)

    def test_SG06_horizon_days_boundaries(self):
        self.assertEqual(v.validate_horizon_days("1"), 1)
        self.assertEqual(v.validate_horizon_days("90"), 90)
        for bad in ("0", "91", "x", ""):
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_horizon_days(bad)


class TestDefaultNetwork(unittest.TestCase):
    def setUp(self):
        self.templates = build_default_templates()

    def test_SG07_network_is_large_and_covers_all_airports(self):
        self.assertGreater(len(self.templates), 300)
        used = {t["origin"] for t in self.templates} | {t["destination"] for t in self.templates}
        self.assertEqual(used, set(AIRPORTS))

    def test_SG08_every_template_passes_the_validators(self):
        for t in self.templates:
            v.validate_flight_no(t["flight_no"])
            v.validate_route(t["origin"], t["destination"])
            v.validate_dep_time(t["dep_time"])
            v.validate_duration(t["duration_min"])
            v.validate_rows(t["rows"])
            v.validate_fare(t["base_fare"])
            v.parse_days(t["days"])

    def test_SG09_flight_numbers_unique_and_every_route_has_a_return(self):
        numbers = [t["flight_no"] for t in self.templates]
        self.assertEqual(len(numbers), len(set(numbers)))
        pairs = {(t["origin"], t["destination"]) for t in self.templates}
        for a, b in pairs:
            self.assertIn((b, a), pairs)

    def test_SG10_network_is_deterministic(self):
        self.assertEqual(self.templates, build_default_templates())


class TestDynamicFare(unittest.TestCase):
    base = 5000

    def test_SG11_peak_costs_more_than_red_eye(self):
        day = datetime(2026, 12, 1, 0, 0)     # Tuesday, far ahead
        peak = dynamic_fare(self.base, day.replace(hour=8), NOW)
        off = dynamic_fare(self.base, day.replace(hour=14), NOW)
        red_eye = dynamic_fare(self.base, day.replace(hour=23), NOW)
        self.assertGreater(peak, off)
        self.assertGreater(off, red_eye)

    def test_SG12_last_minute_costs_more_than_early_booking(self):
        soon = dynamic_fare(self.base, NOW + timedelta(days=1, hours=5), NOW)
        far = dynamic_fare(self.base, NOW + timedelta(days=40), NOW)
        self.assertGreater(soon, far)

    def test_SG13_friday_costs_more_than_tuesday(self):
        tue = dynamic_fare(self.base, datetime(2026, 12, 1, 14, 0), NOW)
        fri = dynamic_fare(self.base, datetime(2026, 12, 4, 14, 0), NOW)
        self.assertGreater(fri, tue)

    def test_SG14_fare_is_clamped_to_allowed_range(self):
        self.assertEqual(dynamic_fare(1, NOW + timedelta(days=40), NOW), MIN_FARE)
        self.assertEqual(dynamic_fare(10 ** 7, NOW + timedelta(days=1), NOW), MAX_FARE)


class TestScheduleService(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.schedule = ScheduleService(self.conn)

    def add(self, **kw):
        d = dict(flight_no="ZZ100", airline="Test Air", origin="DEL", destination="BOM", dep_time="08:00",
                 duration=120, days="Daily", rows=20, base_fare=5000)
        d.update(kw)
        return self.schedule.add_template(self.admin, **d)

    def generated(self, flight_no):
        return [f for f in self.flights.list_flights() if f.flight_no == flight_no]

    def test_SG15_add_template_and_label(self):
        t = self.add(days="Mon,Wed,Fri")
        self.assertEqual((t.flight_no, t.dep_time, t.days, t.days_label), ("ZZ100", "08:00", "135", "Mon,Wed,Fri"))
        self.assertEqual(self.add(flight_no="ZZ101", days="Daily").days_label, "Daily")

    def test_SG16_duplicate_template_number_rejected(self):
        self.add()
        with self.assertRaises(BusinessRuleError):
            self.add()

    def test_SG17_only_admin_can_add_or_generate(self):
        for actor in (self.staff, self.priya, None):
            with self.assertRaises(AuthorizationError):
                self.schedule.add_template(actor, "ZZ100", "Test Air", "DEL", "BOM", "08:00", 120, "Daily", 20, 5000)
            with self.assertRaises(AuthorizationError):
                self.schedule.generate_flights(actor, 3, now=NOW)

    def test_SG18_generates_one_flight_per_day_and_skips_past_departures(self):
        self.add()                                            # 08:00 daily; NOW is 09:00 so today is skipped
        result = self.schedule.generate_flights(self.admin, 3, now=NOW)
        flights = self.generated("ZZ100")
        self.assertEqual(result.created, 2)
        self.assertEqual([f.departure.strftime("%Y-%m-%d %H:%M") for f in flights],
                         ["2026-11-11 08:00", "2026-11-12 08:00"])
        self.assertTrue(all(f.arrival - f.departure == timedelta(minutes=120) for f in flights))
        self.assertTrue(all(f.status == FlightStatus.SCHEDULED for f in flights))

    def test_SG19_generation_is_idempotent(self):
        self.add()
        self.schedule.generate_flights(self.admin, 5, now=NOW)
        again = self.schedule.generate_flights(self.admin, 5, now=NOW)
        self.assertEqual(again.created, 0)
        self.assertEqual(again.skipped, 4)
        self.assertEqual(len(self.generated("ZZ100")), 4)

    def test_SG20_extending_the_horizon_only_adds_new_days(self):
        self.add()
        self.schedule.generate_flights(self.admin, 3, now=NOW)
        more = self.schedule.generate_flights(self.admin, 6, now=NOW)
        self.assertEqual(more.created, 3)
        self.assertEqual(len(self.generated("ZZ100")), 5)

    def test_SG21_days_of_week_respected(self):
        self.add(days="Mon")                                  # NOW is a Tuesday; Mondays are 16 and 23 Nov
        self.schedule.generate_flights(self.admin, 14, now=NOW)
        dates = [f.departure.strftime("%Y-%m-%d") for f in self.generated("ZZ100")]
        self.assertEqual(dates, ["2026-11-16", "2026-11-23"])

    def test_SG22_inactive_template_not_generated_and_can_be_reactivated(self):
        t = self.add()
        self.schedule.set_active(self.admin, t.template_id, False)
        self.assertEqual(self.schedule.generate_flights(self.admin, 3, now=NOW).created, 0)
        self.schedule.set_active(self.admin, t.template_id, True)
        self.assertEqual(self.schedule.generate_flights(self.admin, 3, now=NOW).created, 2)
        with self.assertRaises(NotFoundError):
            self.schedule.set_active(self.admin, 9999, True)

    def test_SG23_cancelled_flight_is_not_recreated(self):
        self.add()
        self.schedule.generate_flights(self.admin, 3, now=NOW)
        victim = self.generated("ZZ100")[0]
        self.flights.cancel_flight(self.admin, victim.flight_id)
        result = self.schedule.generate_flights(self.admin, 3, now=NOW)
        self.assertEqual(result.created, 0)
        self.assertEqual(len(self.generated("ZZ100")), 2)

    def test_SG24_full_network_has_no_gate_conflicts(self):
        self.schedule.seed_default_network()
        self.schedule.generate_flights(self.admin, 3, now=NOW)
        rows = self.conn.execute("SELECT gate, departure FROM flights WHERE gate IS NOT NULL "
                                 "AND status <> 'CANCELLED' ORDER BY gate, departure").fetchall()
        self.assertGreater(len(rows), 1000)
        by_gate = {}
        for r in rows:
            self.assertIn(r["gate"], GATES)
            by_gate.setdefault(r["gate"], []).append(to_dt(r["departure"]))
        for gate, times in by_gate.items():
            for a, b in zip(times, times[1:]):
                self.assertGreaterEqual((b - a).total_seconds() / 60, GATE_BUFFER_MINUTES,
                                        f"gate {gate}: {a} and {b} too close")

    def test_SG25_ensure_schedule_seeds_once_and_tops_up(self):
        first = self.schedule.ensure_schedule(2, now=NOW)
        count = self.conn.execute("SELECT COUNT(*) FROM flight_templates").fetchone()[0]
        self.assertGreater(count, 300)
        self.assertGreater(first.created, 300)
        self.assertEqual(self.schedule.seed_default_network(), 0)           # never seeded twice
        later = self.schedule.ensure_schedule(3, now=NOW)                  # one more day appears
        self.assertGreater(later.created, 300)
        self.assertEqual(self.schedule.ensure_schedule(3, now=NOW).created, 0)
        self.assertEqual(later.through.isoformat(), "2026-11-12")
        self.assertEqual(self.conn.execute("SELECT MAX(substr(departure,1,10)) FROM flights WHERE flight_no LIKE '6E6%'"
                                           ).fetchone()[0], "2026-11-12")

    def test_SG26_generated_flights_are_searchable_and_bookable(self):
        self.schedule.ensure_schedule(3, now=NOW)
        found = self.bookings.search_flights("DEL", "BOM", "2026-11-11", now=NOW)
        self.assertGreaterEqual(len(found), 3)
        flight, left = found[0]
        self.assertEqual(left, flight.capacity)
        booking = self.bookings.book_ticket(self.priya, flight.flight_id, "1A", now=NOW)
        self.assertEqual(booking.fare, flight.fare)
        again = dict((f.flight_id, l) for f, l in self.bookings.search_flights("DEL", "BOM", "2026-11-11", now=NOW))
        self.assertEqual(again[flight.flight_id], flight.capacity - 1)
        self.assertLessEqual(len(self.bookings.search_flights(now=NOW, limit=5)), 5)


class TestMangalore(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.schedule = ScheduleService(self.conn)

    def test_SG28_mangalore_is_connected_in_both_directions_and_bookable(self):
        self.assertEqual(AIRPORTS["IXE"], "Mangalore")
        tpl = [t for t in build_default_templates() if "IXE" in (t["origin"], t["destination"])]
        self.assertGreaterEqual(len({t["destination"] for t in tpl if t["origin"] == "IXE"}), 5)
        self.assertEqual({(t["origin"], t["destination"]) for t in tpl if t["origin"] == "IXE"},
                         {(t["destination"], t["origin"]) for t in tpl if t["destination"] == "IXE"})
        self.schedule.ensure_schedule(3, now=NOW)
        out = self.bookings.search_flights("IXE", "BLR", "2026-11-11", now=NOW)
        back = self.bookings.search_flights("BLR", "IXE", "2026-11-11", now=NOW)
        self.assertGreaterEqual(len(out), 3)
        self.assertGreaterEqual(len(back), 3)
        self.assertIn("IXE", self.flights.list_airports())
        booking = self.bookings.book_ticket(self.priya, out[0][0].flight_id, "2C", now=NOW)
        self.assertEqual(booking.seat, "2C")

    def test_SG29_existing_database_gets_new_routes_without_disturbing_old_ones(self):
        self.schedule.seed_default_network()
        total = self.conn.execute("SELECT COUNT(*) FROM flight_templates").fetchone()[0]
        ixe = self.conn.execute("SELECT COUNT(*) FROM flight_templates WHERE origin='IXE' OR destination='IXE'").fetchone()[0]
        self.assertGreater(ixe, 20)
        # simulate a database created before Mangalore existed, with one service switched off by the admin
        self.conn.execute("DELETE FROM flight_templates WHERE origin='IXE' OR destination='IXE'")
        victim = self.schedule.list_templates()[0]
        self.schedule.set_active(self.admin, victim.template_id, False)
        self.assertEqual(self.schedule.seed_default_network(), ixe)            # only the missing ones come back
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM flight_templates").fetchone()[0], total)
        self.assertFalse(self.schedule.get_template(victim.template_id).active)   # admin's choice is respected
        self.assertEqual(self.schedule.seed_default_network(), 0)


class TestFlightListFilters(ServiceTestCase):
    def test_SG27_list_flights_filters_and_count(self):
        self.assertEqual(len(self.flights.list_flights()), 8)
        self.assertEqual([f.flight_no for f in self.flights.list_flights(search="ai202")], ["AI202"])
        self.assertEqual({f.origin for f in self.flights.list_flights(search="DEL")} |
                         {f.destination for f in self.flights.list_flights(search="DEL")} >= {"DEL"}, True)
        day = self.flight("AI202").departure.strftime("%Y-%m-%d")
        self.assertEqual(self.flights.count_flights(date=day), len(self.flights.list_flights(date=day)))
        self.assertEqual(len(self.flights.list_flights(limit=3)), 3)
        with self.assertRaises(ValidationError):
            self.flights.list_flights(date="tomorrow")
        self.assertEqual(self.flights.booked_counts()[self.flight("AI202").flight_id], 3)


if __name__ == "__main__":
    unittest.main()
