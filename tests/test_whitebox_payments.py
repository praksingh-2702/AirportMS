"""WHITE-BOX tests for the payment units, designed from their control-flow graphs
(docs/diagrams/cfg_card_number.png and cfg_refund_tier.png). Test-case IDs WB18-WB28.

validate_card_number() - V(G) = 7. Decisions: 1 not-all-digits, 2 wrong length, 4 loop over digits,
5 odd position, 6 doubled digit > 4, 10 checksum fails. The paths that run the loop zero times are infeasible
(a valid length is at least 13 digits), so the five feasible paths below give 100% branch coverage.

cancellation_percent() - V(G) = 3. Decisions: 1 more tiers, 2 hours >= tier minimum.
"""
import unittest

from ams import validators as v
from ams.errors import BusinessRuleError, ValidationError
from ams.payments_core import cancellation_percent
from ams.services import PaymentService
from tests.helpers import NOW, ServiceTestCase


class TestCardNumberPaths(unittest.TestCase):
    def test_WB18_path_1T_not_all_digits(self):
        with self.assertRaises(ValidationError) as ctx:
            v.validate_card_number("4111-ABCD-1111-1111")
        self.assertIn("13-19 digits", str(ctx.exception))

    def test_WB19_path_1F_2T_wrong_length(self):
        with self.assertRaises(ValidationError) as ctx:
            v.validate_card_number("1234")
        self.assertIn("13-19 digits", str(ctx.exception))

    def test_WB20_path_loop_odd_and_even_positions_checksum_ok(self):
        # 5T/5F alternate; every doubled digit is 1 so node 6 takes F; checksum passes (10F)
        self.assertEqual(v.validate_card_number("4111 1111 1111 1111"), "4111111111111111")

    def test_WB21_path_doubled_digit_above_4(self):
        # the 5s sit on odd positions: 5 * 2 = 10 > 4, so node 6 takes T (digit sum 10 - 9 = 1)
        self.assertEqual(v.validate_card_number("5555555555554444"), "5555555555554444")

    def test_WB22_path_checksum_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            v.validate_card_number("4111111111111112")
        self.assertIn("not valid", str(ctx.exception))

    def test_WB23_boundary_lengths_13_and_19_accepted_12_and_20_rejected(self):
        self.assertEqual(len(v.validate_card_number("4222222222222")), 13)          # 13 digits, Luhn valid
        self.assertEqual(len(v.validate_card_number("4111111111111111110")), 19)        # 19 digits, Luhn valid
        for bad in ("411111111111", "41111111111111111111"):                          # 12 and 20 digits
            with self.assertRaises(ValidationError):
                v.validate_card_number(bad)


class TestRefundTierPaths(unittest.TestCase):
    def test_WB24_path_first_tier_matches(self):
        self.assertEqual(cancellation_percent(100), 10)          # 1T-2T-3-E

    def test_WB25_path_loop_runs_again_then_matches(self):
        self.assertEqual(cancellation_percent(30), 25)           # 1T-2F-1T-2T-3-E
        self.assertEqual(cancellation_percent(10), 50)           # 1T-2F-1T-2F-1T-2T-3-E

    def test_WB26_path_all_tiers_fail_falls_through_to_100(self):
        self.assertEqual(cancellation_percent(1.9), 100)         # 1T-2F-...-1F-4-E
        self.assertEqual(cancellation_percent(2), 50)            # boundary: exactly 2 h is still the 50% tier


class TestCheckInPaymentPath(ServiceTestCase):
    """check_in() has a decision (node 6 of docs/diagrams/cfg_check_in.png) that did not exist before payments:
    the booking must be PAID. WB27 takes its T branch, WB28 proves it is examined before the window rule."""

    def unpaid_far_booking(self):
        return self.bookings.book_ticket(self.priya, self.flight("UK811").flight_id, "2A", now=NOW)   # 54 h away

    def test_WB27_path_6T_unpaid_booking_is_refused(self):
        b = self.unpaid_far_booking()
        with self.assertRaises(BusinessRuleError) as ctx:
            self.checkin.check_in(self.staff, b.pnr, now=NOW)
        self.assertIn("Payment", str(ctx.exception))

    def test_WB28_payment_is_checked_before_the_check_in_window(self):
        b = self.unpaid_far_booking()                                  # also outside the 48 h window
        with self.assertRaises(BusinessRuleError) as before:
            self.checkin.check_in(self.staff, b.pnr, now=NOW)
        self.assertNotIn("opens", str(before.exception))               # the payment rule fired first
        PaymentService(self.conn).pay_booking(self.priya, b.booking_id, "UPI", {"upi_id": "priya@okaxis"}, now=NOW)
        with self.assertRaises(BusinessRuleError) as after:
            self.checkin.check_in(self.staff, b.pnr, now=NOW)
        self.assertIn("opens", str(after.exception))                   # once paid, the window rule is reached


if __name__ == "__main__":
    unittest.main()
