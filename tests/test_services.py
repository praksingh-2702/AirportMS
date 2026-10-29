"""UNIT TESTS of each service class (one TestCase per module) against an in-memory SQLite database.
Test-case IDs (UT-xx) match the unit-testing table in the report."""
import unittest
from datetime import timedelta

from ams.errors import (AuthenticationError, AuthorizationError, BusinessRuleError,
                        ValidationError)
from ams.models import BagStatus, BookingStatus, FlightStatus, Role
from tests.helpers import NOW, ServiceTestCase

FUTURE_DEP = (NOW + timedelta(days=5)).strftime("%Y-%m-%d 10:00")
FUTURE_ARR = (NOW + timedelta(days=5)).strftime("%Y-%m-%d 12:15")


class TestAuthService(ServiceTestCase):
    def test_UT01_login_success_returns_role(self):
        self.assertEqual(self.auth.login("ADMIN ", "admin123").role, Role.ADMIN)

    def test_UT02_login_wrong_password(self):
        with self.assertRaises(AuthenticationError):
            self.auth.login("admin", "wrong123")

    def test_UT03_login_blank_fields(self):
        with self.assertRaises(ValidationError):
            self.auth.login("", "")

    def test_UT04_register_passenger(self):
        u = self.auth.register_passenger("om_b", "secret12", "Om Bhagat", "om@mail.com", "9000000001", now=NOW)
        self.assertEqual(u.role, Role.PASSENGER)
        self.assertEqual(self.auth.login("om_b", "secret12").user_id, u.user_id)

    def test_UT05_duplicate_username(self):
        with self.assertRaisesRegex(BusinessRuleError, "taken"):
            self.auth.register_passenger("priya", "secret12", "Priya Two", "p2@mail.com", "9000000002", now=NOW)

    def test_UT06_only_admin_creates_staff(self):
        with self.assertRaises(AuthorizationError):
            self.auth.create_staff_account(self.staff, "newstaff", "staff999", "New Staff",
                                           "ns@ams.local", "9000000003")
        u = self.auth.create_staff_account(self.admin, "newstaff", "staff999", "New Staff",
                                           "ns@ams.local", "9000000003", now=NOW)
        self.assertEqual(u.role, Role.STAFF)

    def test_UT07_password_is_not_stored_in_plain_text(self):
        row = self.conn.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
        self.assertNotIn("admin123", row["password_hash"])


class TestFlightService(ServiceTestCase):
    def add(self, **over):
        data = dict(flight_no="AI777", airline="Air India", origin="DEL", destination="HYD",
                    departure=FUTURE_DEP, arrival=FUTURE_ARR, rows="15", fare="4200", gate="C9")
        data.update(over)
        return self.flights.add_flight(self.admin, now=NOW, **data)

    def test_UT08_add_flight(self):
        f = self.add()
        self.assertEqual((f.flight_no, f.capacity, f.status), ("AI777", 90, FlightStatus.SCHEDULED))

    def test_UT09_staff_cannot_add_flight(self):
        with self.assertRaises(AuthorizationError):
            self.flights.add_flight(self.staff, "AI778", "Air India", "DEL", "HYD", FUTURE_DEP,
                                    FUTURE_ARR, "15", "4200", now=NOW)

    def test_UT10_past_departure_rejected(self):
        with self.assertRaisesRegex(ValidationError, "future"):
            self.add(departure="2026-01-01 10:00", arrival="2026-01-01 12:00")

    def test_UT11_gate_conflict_rejected(self):
        self.add()
        with self.assertRaisesRegex(BusinessRuleError, "Gate C9"):
            self.add(flight_no="AI778", departure=FUTURE_DEP.replace("10:00", "10:30"),
                     arrival=FUTURE_ARR.replace("12:15", "12:45"))

    def test_UT12_duplicate_flight_same_day(self):
        self.add()
        with self.assertRaisesRegex(BusinessRuleError, "already scheduled"):
            self.add(gate="")

    def test_UT13_update_and_assign_gate(self):
        f = self.add(gate="")
        f = self.flights.update_flight(self.admin, f.flight_id, "AI777", "Air India", "DEL", "HYD",
                                       FUTURE_DEP, FUTURE_ARR, "20", "4500", "", now=NOW)
        self.assertEqual((f.rows, f.fare, f.gate), (20, 4500, None))
        self.assertEqual(self.flights.assign_gate(self.admin, f.flight_id, "d11").gate, "D11")

    def test_UT14_cannot_shrink_below_booked_row(self):
        ai = self.flight("AI202")                       # seat 10F is booked
        with self.assertRaisesRegex(BusinessRuleError, "row 10"):
            self.flights.update_flight(self.admin, ai.flight_id, "AI202", ai.airline, "DEL", "BOM",
                                       ai.departure.strftime("%Y-%m-%d %H:%M"),
                                       ai.arrival.strftime("%Y-%m-%d %H:%M"), "8", ai.fare, ai.gate, now=NOW)

    def test_UT15_cancel_flight_cascades_to_bookings(self):
        ai = self.flight("AI202")
        self.assertEqual(self.flights.cancel_flight(self.admin, ai.flight_id), 3)
        f = self.flights.get_flight(ai.flight_id)
        self.assertEqual((f.status, f.gate), (FlightStatus.CANCELLED, None))
        self.assertEqual(self.bookings.get_taken_seats(ai.flight_id), set())

    def test_UT16_illegal_status_transition(self):
        ix = self.flight("IX345")                       # CANCELLED is a final state
        with self.assertRaises(BusinessRuleError):
            self.flights.change_status(self.admin, ix.flight_id, "SCHEDULED")
        ai = self.flight("AI202")
        self.assertEqual(self.flights.change_status(self.admin, ai.flight_id, "DELAYED").status,
                         FlightStatus.DELAYED)


class TestBookingService(ServiceTestCase):
    def test_UT17_search_filters(self):
        results = self.bookings.search_flights("DEL", "", "", now=NOW)
        self.assertEqual({f.flight_no for f, _ in results}, {"AI202", "SG134", "6E2140"})
        ai = next(left for f, left in results if f.flight_no == "AI202")
        self.assertEqual(ai, 120 - 3)

    def test_UT18_search_excludes_cancelled_and_boarding(self):
        names = {f.flight_no for f, _ in self.bookings.search_flights(now=NOW)}
        self.assertNotIn("IX345", names)
        self.assertNotIn("QP1302", names)

    def test_UT19_book_ticket(self):
        uk = self.flight("UK811")
        self.bookings.pnr_generator = lambda: "TEST01"
        b = self.bookings.book_ticket(self.priya, uk.flight_id, "1a", now=NOW)
        self.assertEqual((b.pnr, b.seat, b.fare, b.status), ("TEST01", "1A", 4800, BookingStatus.BOOKED))

    def test_UT20_seat_already_taken(self):
        with self.assertRaisesRegex(BusinessRuleError, "taken"):
            self.bookings.book_ticket(self.priya, self.flight("UK811").flight_id, "7D", now=NOW)

    def test_UT21_cannot_book_cancelled_flight(self):
        with self.assertRaisesRegex(BusinessRuleError, "CANCELLED"):
            self.bookings.book_ticket(self.priya, self.flight("IX345").flight_id, "1A", now=NOW)

    def test_UT22_one_booking_per_passenger_per_flight(self):
        with self.assertRaisesRegex(BusinessRuleError, "already hold"):
            self.bookings.book_ticket(self.priya, self.flight("AI202").flight_id, "1A", now=NOW)

    def test_UT23_staff_cannot_book(self):
        with self.assertRaises(AuthorizationError):
            self.bookings.book_ticket(self.staff, self.flight("UK811").flight_id, "1A", now=NOW)

    def test_UT24_cancel_own_booking_frees_seat(self):
        d = next(x for x in self.bookings.list_bookings(self.priya) if x.booking.pnr == "P9W1ZD")
        self.bookings.cancel_booking(self.priya, d.booking.booking_id, now=NOW)
        self.assertNotIn("12C", self.bookings.get_taken_seats(d.booking.flight_id))

    def test_UT25_cannot_cancel_others_booking(self):
        d = next(x for x in self.bookings.list_bookings(self.rahul) if x.booking.pnr == "H2N6YE")
        with self.assertRaisesRegex(BusinessRuleError, "own"):
            self.bookings.cancel_booking(self.priya, d.booking.booking_id, now=NOW)

    def test_UT26_cannot_cancel_checked_in_booking(self):
        d = next(x for x in self.bookings.list_bookings(self.rahul) if x.booking.pnr == "R4T9XB")
        with self.assertRaisesRegex(BusinessRuleError, "checked in"):
            self.bookings.cancel_booking(self.rahul, d.booking.booking_id, now=NOW)

    def test_UT27_passenger_sees_only_own_bookings(self):
        self.assertTrue(all(d.passenger_name == "Priya Verma" for d in self.bookings.list_bookings(self.priya)))
        self.assertEqual(len(self.bookings.list_bookings(self.staff)), 8)


class TestCheckInService(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.checkin.check_in(self.staff, "K7Q2MA", now=NOW)

    def test_UT28_add_bag_generates_tag(self):
        bag = self.checkin.add_bag(self.staff, "K7Q2MA", "12.4", now=NOW)
        self.assertRegex(bag.tag_no, r"^AMS\d{6}$")
        self.assertEqual(bag.status, BagStatus.CHECKED_IN)

    def test_UT29_bag_requires_check_in(self):
        with self.assertRaisesRegex(BusinessRuleError, "after the passenger has checked in"):
            self.checkin.add_bag(self.staff, "M3J8LC", "10", now=NOW)

    def test_UT30_max_three_bags(self):
        for w in ("5", "5", "5"):
            self.checkin.add_bag(self.staff, "K7Q2MA", w, now=NOW)
        with self.assertRaisesRegex(BusinessRuleError, "at most 3"):
            self.checkin.add_bag(self.staff, "K7Q2MA", "5", now=NOW)

    def test_UT31_baggage_summary_fee(self):
        self.checkin.add_bag(self.staff, "K7Q2MA", "17.5", now=NOW)
        self.checkin.add_bag(self.staff, "K7Q2MA", "4", now=NOW)
        self.assertEqual(self.checkin.baggage_summary("K7Q2MA"), (21.5, 3500))

    def test_UT32_bag_status_transitions(self):
        bag = self.checkin.add_bag(self.staff, "K7Q2MA", "10", now=NOW)
        for status in ("LOADED", "UNLOADED", "CLAIMED"):
            bag = self.checkin.update_bag_status(self.staff, bag.bag_id, status, now=NOW)
        self.assertEqual(bag.status, BagStatus.CLAIMED)
        with self.assertRaises(BusinessRuleError):          # CLAIMED is final
            self.checkin.update_bag_status(self.staff, bag.bag_id, "LOADED", now=NOW)

    def test_UT33_passenger_views_only_own_boarding_pass(self):
        self.assertEqual(self.checkin.get_boarding_pass(self.priya, "K7Q2MA").seat, "4A")
        with self.assertRaisesRegex(BusinessRuleError, "own"):
            self.checkin.get_boarding_pass(self.sneha(), "K7Q2MA")

    def sneha(self):
        return self.auth.login("sneha", "pass1234")


if __name__ == "__main__":
    unittest.main()
