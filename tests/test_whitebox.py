"""WHITE-BOX TESTS - derived from the source code (control-flow graphs).

Unit 1: CheckInService.check_in       -> basis-path testing (cyclomatic complexity V(G) = 8)
Unit 2: FlightService.is_gate_available -> branch + loop coverage (V(G) = 5)
Unit 3: compute_excess_fee            -> statement + branch coverage (V(G) = 3)
Path IDs (WB-xx) match the white-box tables and CFG figures in the report.
"""
import unittest
from datetime import datetime, timedelta

from ams.errors import (AuthorizationError, BusinessRuleError, NotFoundError,
                        ValidationError)
from ams.models import BookingStatus
from ams.services import compute_excess_fee
from tests.helpers import NOW, ServiceTestCase


class TestCheckInBasisPaths(ServiceTestCase):
    """Decisions in check_in (see CFG): D1 role, D2 PNR found, D3 cancelled,
    D4 already checked in, D5 flight cancelled/departed, D6 too early, D7 too late."""

    def setUp(self):
        super().setUp()
        # Seed data at NOW: AI202 departs NOW+3h, 6E5021 NOW+26h, UK811 NOW+54h,
        # QP1302 NOW+30min, IX345 cancelled.

    def test_WB01_wrong_role(self):                      # D1 true
        with self.assertRaises(AuthorizationError):
            self.checkin.check_in(self.priya, "K7Q2MA", now=NOW)

    def test_WB02_pnr_not_found(self):                   # D1 F, D2 true
        with self.assertRaises(NotFoundError):
            self.checkin.check_in(self.staff, "ZZZZZZ", now=NOW)

    def test_WB03_booking_cancelled(self):               # D3 true
        with self.assertRaisesRegex(BusinessRuleError, "cancelled"):
            self.checkin.check_in(self.staff, "C8L4KG", now=NOW)

    def test_WB04_already_checked_in(self):              # D4 true
        with self.assertRaisesRegex(BusinessRuleError, "already checked in"):
            self.checkin.check_in(self.staff, "R4T9XB", now=NOW)

    def test_WB05_flight_not_operating(self):            # D5 true (flight departed)
        fid = self.flight("AI202").flight_id
        self.conn.execute("UPDATE flights SET status='DEPARTED' WHERE flight_id=?", (fid,))
        with self.assertRaisesRegex(BusinessRuleError, "DEPARTED"):
            self.checkin.check_in(self.staff, "K7Q2MA", now=NOW)

    def test_WB06_too_early(self):                       # D6 true (UK811 is 54 h away)
        with self.assertRaisesRegex(BusinessRuleError, "opens"):
            self.checkin.check_in(self.staff, "H2N6YE", now=NOW)

    def test_WB07_too_late(self):                        # D7 true (QP1302 is 30 min away)
        with self.assertRaisesRegex(BusinessRuleError, "closed"):
            self.checkin.check_in(self.staff, "T5V3QF", now=NOW)

    def test_WB08_success_path(self):                    # all decisions false -> boarding pass
        bp = self.checkin.check_in(self.staff, "K7Q2MA", now=NOW)
        self.assertEqual((bp.pnr, bp.seat, bp.gate, bp.boarding_seq), ("K7Q2MA", "4A", "A3", 2))
        self.assertEqual(bp.boarding_time, bp.departure - timedelta(minutes=30))
        booking = self.checkin.find_booking("K7Q2MA").booking
        self.assertEqual(booking.status, BookingStatus.CHECKED_IN)

    def test_WB09_window_boundaries(self):               # boundary of D6/D7 conditions
        dep = self.flight("AI202").departure
        # exactly 45 min before departure is still allowed (condition is now > dep-45)
        bp = self.checkin.check_in(self.staff, "K7Q2MA", now=dep - timedelta(minutes=45))
        self.assertEqual(bp.pnr, "K7Q2MA")
        with self.assertRaises(BusinessRuleError):        # one minute later is rejected
            self.checkin.check_in(self.staff, "M3J8LC", now=dep - timedelta(minutes=44))


class TestGateAvailabilityBranches(ServiceTestCase):
    """is_gate_available: gate None? / loop over flights / excluded? / gap < 60?"""

    def test_WB10_no_gate_requested(self):               # first decision true
        self.assertTrue(self.flights.is_gate_available(None, NOW))

    def test_WB11_loop_zero_iterations(self):            # gate with no flights
        self.assertTrue(self.flights.is_gate_available("D20", NOW))

    def test_WB12_conflict_within_buffer(self):          # gap < 60 -> False
        ai202 = self.flight("AI202")                     # gate A3
        self.assertFalse(self.flights.is_gate_available("A3", ai202.departure + timedelta(minutes=59)))

    def test_WB13_no_conflict_at_buffer(self):           # gap == 60 -> loop continues, True
        ai202 = self.flight("AI202")
        self.assertTrue(self.flights.is_gate_available("A3", ai202.departure + timedelta(minutes=60)))

    def test_WB14_own_flight_excluded(self):             # exclude branch taken
        ai202 = self.flight("AI202")
        self.assertTrue(self.flights.is_gate_available("A3", ai202.departure, ai202.flight_id))


class TestExcessFeeBranches(unittest.TestCase):
    def test_WB15_negative_branch(self):
        with self.assertRaises(ValidationError):
            compute_excess_fee(-0.5)

    def test_WB16_within_allowance_branch(self):
        self.assertEqual(compute_excess_fee(10), 0)

    def test_WB17_excess_branch_with_rounding(self):
        self.assertEqual(compute_excess_fee(21.5), 3500)   # 6.5 kg -> 7 started kg


if __name__ == "__main__":
    unittest.main()
