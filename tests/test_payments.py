"""Tests for the simulated payment feature: validation, gateway, pay-at-booking, refunds, check-in rule,
receipts. Test-case IDs PY01-PY40.

NOW (see helpers) is Tuesday 2026-11-10 09:00. Sample flights: AI202 departs in 3 h (fare 5400), UK811 in
2 d 6 h = 54 h (fare 4800)."""
import unittest
from datetime import datetime, timedelta

from ams import gateway
from ams import validators as v
from ams.errors import AuthorizationError, BusinessRuleError, NotFoundError, PaymentError, ValidationError
from ams.models import BookingStatus, PaymentStatus
from ams.payments_core import cancellation_percent, fare_breakdown
from ams.services import PaymentService
from tests.helpers import NOW, ServiceTestCase

GOOD_CARD = dict(number="4111 1111 1111 1111", expiry="12/29", cvv="123", name="Priya Verma")
UPI = dict(upi_id="priya@okaxis")
BANK = dict(bank="HDFC Bank")


class TestFareArithmetic(unittest.TestCase):
    def test_PY01_breakdown_adds_up(self):
        b = fare_breakdown(5400)
        self.assertEqual((b.base_fare, b.airport_fee, b.gst, b.convenience_fee), (5400, 200, 280, 150))
        self.assertEqual(b.total, 6030)                       # 5400 + 200 + 5% of 5600 + 150

    def test_PY02_gst_rounds_to_whole_rupees(self):
        self.assertEqual(fare_breakdown(4510).gst, 236)       # 5% of 4710 = 235.5 -> 236
        self.assertEqual(fare_breakdown(500).total, 500 + 200 + 35 + 150)

    def test_PY03_cancellation_tiers_and_boundaries(self):
        for hours, pct in ((200, 10), (48, 10), (47.9, 25), (24, 25), (23.9, 50), (2, 50), (1.9, 100), (-5, 100)):
            self.assertEqual(cancellation_percent(hours), pct, hours)


class TestPaymentValidators(unittest.TestCase):
    def test_PY04_card_number_luhn(self):
        self.assertEqual(v.validate_card_number("4111 1111-1111 1111"), "4111111111111111")
        self.assertEqual(v.validate_card_number("5555555555554444"), "5555555555554444")
        for bad in ("4111111111111112", "1234", "abcd efgh ijkl mnop", "", "4" * 20):
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_card_number(bad)

    def test_PY05_expiry_format_and_boundaries(self):
        self.assertEqual(v.validate_expiry("11/26", NOW), "11/26")          # this month is still valid
        self.assertEqual(v.validate_expiry("12 / 29", NOW), "12/29")
        for bad, why in (("10/26", "last month"), ("13/29", "month 13"), ("1/29", "format"), ("", "empty"), ("12/2029", "yyyy")):
            with self.assertRaises(ValidationError, msg=why):
                v.validate_expiry(bad, NOW)

    def test_PY06_cvv_length_depends_on_card(self):
        self.assertEqual(v.validate_cvv("123", "4111111111111111"), "123")
        self.assertEqual(v.validate_cvv("1234", "378282246310005"), "1234")     # Amex has 4
        for bad, number in (("12", "4111111111111111"), ("1234", "4111111111111111"), ("123", "378282246310005"), ("abc", "")):
            with self.assertRaises(ValidationError):
                v.validate_cvv(bad, number)

    def test_PY07_upi_bank_and_name(self):
        self.assertEqual(v.validate_upi_id("priya.v@okaxis"), "priya.v@okaxis")
        for bad in ("priya", "@okaxis", "priya@", "pri ya@okaxis", "a@b"):
            with self.assertRaises(ValidationError, msg=bad):
                v.validate_upi_id(bad)
        self.assertEqual(v.validate_bank("HDFC Bank"), "HDFC Bank")
        with self.assertRaises(ValidationError):
            v.validate_bank("Bank of Nowhere")
        self.assertEqual(v.validate_cardholder("  priya   verma "), "priya verma")
        with self.assertRaises(ValidationError):
            v.validate_cardholder("1234")

    def test_PY08_card_brand(self):
        self.assertEqual([v.card_brand(n) for n in ("4111", "5555", "2221", "378282", "6011")],
                         ["VISA", "MASTERCARD", "MASTERCARD", "AMEX", "CARD"])


class TestGateway(unittest.TestCase):
    def test_PY09_approvals_and_declines(self):
        self.assertTrue(gateway.authorize("CARD", {"number": "4111111111111111"}, 100).approved)
        no_bank = gateway.authorize("CARD", {"number": "4000000000000002"}, 100)
        self.assertFalse(no_bank.approved)
        self.assertIn("declined", no_bank.message)
        self.assertIn("Insufficient", gateway.authorize("CARD", {"number": "4000000000009995"}, 100).message)
        self.assertFalse(gateway.authorize("UPI", {"upi_id": "fail@okaxis"}, 100).approved)
        self.assertTrue(gateway.authorize("UPI", {"upi_id": "ok@okaxis"}, 100).approved)
        self.assertFalse(gateway.authorize("NETBANKING", {"bank": "Demo Bank (offline)"}, 100).approved)
        self.assertTrue(gateway.authorize("NETBANKING", {"bank": "HDFC Bank"}, 100).approved)

    def test_PY10_references_are_unique(self):
        refs = {gateway.authorize("UPI", UPI, 1).reference for _ in range(50)}
        self.assertEqual(len(refs), 50)


class PaymentCase(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.pay = PaymentService(self.conn)

    def uk(self):
        return self.flight("UK811").flight_id

    def row_count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


class TestPayAtBooking(PaymentCase):
    def test_PY11_card_payment_creates_booking_and_payment(self):
        booking, payment = self.pay.book_and_pay(self.priya, self.uk(), "1A", "CARD", GOOD_CARD, now=NOW)
        self.assertEqual((booking.status, booking.seat, booking.fare), (BookingStatus.BOOKED, "1A", 4800))
        self.assertEqual((payment.status, payment.method, payment.amount), (PaymentStatus.PAID, "CARD", 5400))
        self.assertEqual(payment.instrument, "VISA XXXX 1111")
        self.assertEqual(payment.invoice_no, f"INV-20261110-{payment.payment_id:05d}")
        self.assertTrue(payment.reference.startswith("GW"))
        self.assertEqual(payment.breakdown.total, payment.amount)

    def test_PY12_card_number_cvv_and_expiry_are_never_stored(self):
        self.pay.book_and_pay(self.priya, self.uk(), "1A", "CARD", GOOD_CARD, now=NOW)
        dump = " ".join(str(tuple(r)) for r in self.conn.execute("SELECT * FROM payments"))
        for secret in ("4111111111111111", "4111 1111 1111 1111", "12/29", "cvv"):
            self.assertNotIn(secret, dump.lower(), secret)
        self.assertIn("XXXX 1111", dump)                                    # only the masked label is kept

    def test_PY13_upi_and_netbanking(self):
        _b, p1 = self.pay.book_and_pay(self.priya, self.uk(), "1A", "UPI", UPI, now=NOW)
        self.assertEqual((p1.method, p1.instrument), ("UPI", "pr***@okaxis"))
        _b, p2 = self.pay.book_and_pay(self.rahul, self.flight("AI505").flight_id, "1A", "NETBANKING", BANK, now=NOW)
        self.assertEqual((p2.method, p2.instrument), ("NETBANKING", "HDFC Bank"))

    def test_PY14_declined_payment_leaves_no_booking_and_frees_the_seat(self):
        before = self.row_count("bookings")
        with self.assertRaises(PaymentError) as ctx:
            self.pay.book_and_pay(self.priya, self.uk(), "1A", "CARD", {**GOOD_CARD, "number": "4000000000000002"}, now=NOW)
        self.assertIn("declined", str(ctx.exception))
        self.assertEqual(self.row_count("bookings"), before)
        self.assertEqual(self.row_count("payments"), 8)                     # only the sample payments
        self.assertNotIn("1A", self.bookings.get_taken_seats(self.uk()))
        # the same seat can be paid for straight away with a good card
        self.pay.book_and_pay(self.priya, self.uk(), "1A", "CARD", GOOD_CARD, now=NOW)

    def test_PY15_other_decline_reasons(self):
        for method, details in (("CARD", {**GOOD_CARD, "number": "4000000000009995"}),
                                ("UPI", {"upi_id": "fail@okaxis"}), ("NETBANKING", {"bank": "Demo Bank (offline)"})):
            with self.assertRaises(PaymentError):
                self.pay.book_and_pay(self.priya, self.uk(), "2A", method, details, now=NOW)
        self.assertEqual(self.row_count("payments"), 8)

    def test_PY16_bad_input_is_rejected_before_anything_happens(self):
        before = self.row_count("bookings")
        bad = [("CARD", {**GOOD_CARD, "number": "4111111111111112"}), ("CARD", {**GOOD_CARD, "expiry": "01/20"}),
               ("CARD", {**GOOD_CARD, "cvv": "12"}), ("UPI", {"upi_id": "nope"}), ("NETBANKING", {"bank": ""}),
               ("CASH", {}), ("CARD", {})]
        for method, details in bad:
            with self.assertRaises(ValidationError, msg=(method, details)):
                self.pay.book_and_pay(self.priya, self.uk(), "1A", method, details, now=NOW)
        self.assertEqual(self.row_count("bookings"), before)

    def test_PY17_seat_and_flight_rules_still_apply_and_nobody_is_charged(self):
        with self.assertRaises(BusinessRuleError):                          # 7D already taken on UK811
            self.pay.book_and_pay(self.priya, self.uk(), "7D", "CARD", GOOD_CARD, now=NOW)
        with self.assertRaises(BusinessRuleError):                          # cancelled flight
            self.pay.book_and_pay(self.priya, self.flight("IX345").flight_id, "1A", "CARD", GOOD_CARD, now=NOW)
        with self.assertRaises(BusinessRuleError):                          # priya already holds AI202
            self.pay.book_and_pay(self.priya, self.flight("AI202").flight_id, "1A", "CARD", GOOD_CARD, now=NOW)
        self.assertEqual(self.row_count("payments"), 8)

    def test_PY18_only_passengers_can_pay(self):
        for actor in (self.staff, self.admin, None):
            with self.assertRaises(AuthorizationError):
                self.pay.book_and_pay(actor, self.uk(), "1A", "CARD", GOOD_CARD, now=NOW)


class TestPayExistingBooking(PaymentCase):
    def unpaid(self):
        return self.bookings.book_ticket(self.priya, self.uk(), "1A", now=NOW)      # old-style booking, no payment

    def test_PY19_unpaid_booking_cannot_check_in_until_paid(self):
        b = self.unpaid()
        with self.assertRaises(BusinessRuleError) as ctx:
            self.checkin.check_in(self.staff, b.pnr, now=NOW + timedelta(days=2))
        self.assertIn("Payment", str(ctx.exception))
        self.pay.pay_booking(self.priya, b.booking_id, "UPI", UPI, now=NOW)
        self.assertEqual(self.checkin.check_in(self.staff, b.pnr, now=NOW + timedelta(days=2)).seat, "1A")

    def test_PY20_pay_booking_rules(self):
        b = self.unpaid()
        with self.assertRaises(BusinessRuleError):                          # somebody else's booking
            self.pay.pay_booking(self.rahul, b.booking_id, "UPI", UPI, now=NOW)
        with self.assertRaises(PaymentError):
            self.pay.pay_booking(self.priya, b.booking_id, "UPI", {"upi_id": "fail@okaxis"}, now=NOW)
        self.assertIsNone(self.pay.get_payment(b.booking_id))               # a decline records nothing
        p = self.pay.pay_booking(self.priya, b.booking_id, "UPI", UPI, now=NOW)
        self.assertEqual(p.amount, 5400)
        with self.assertRaises(BusinessRuleError):                          # never twice
            self.pay.pay_booking(self.priya, b.booking_id, "UPI", UPI, now=NOW)

    def test_PY21_cannot_pay_for_cancelled_booking_or_cancelled_flight(self):
        b = self.unpaid()
        self.bookings.cancel_booking(self.priya, b.booking_id, now=NOW)
        with self.assertRaises(BusinessRuleError):
            self.pay.pay_booking(self.priya, b.booking_id, "UPI", UPI, now=NOW)
        other = self.bookings.book_ticket(self.priya, self.flight("AI505").flight_id, "1A", now=NOW)
        self.flights.cancel_flight(self.admin, self.flight("AI505").flight_id)
        with self.assertRaises(BusinessRuleError):
            self.pay.pay_booking(self.priya, other.booking_id, "UPI", UPI, now=NOW)

    def test_PY22_staff_see_payment_state_through_get_payment(self):
        b = self.unpaid()
        self.assertIsNone(self.pay.get_payment(b.booking_id))
        paid = self.pay.get_payment(self.bookings.list_bookings(self.priya)[0].booking.booking_id)
        self.assertEqual(paid.status, PaymentStatus.PAID)


class TestSamplePayments(PaymentCase):
    def test_PY23_every_live_sample_booking_is_paid_and_the_cancelled_one_refunded(self):
        for d in self.bookings.list_bookings(self.admin):
            p = self.pay.get_payment(d.booking.booking_id)
            self.assertIsNotNone(p, d.booking.pnr)
            if d.booking.pnr == "C8L4KG":
                self.assertEqual((p.status, p.refund_amount, p.refund_reason), (PaymentStatus.REFUNDED, p.amount,
                                                                                  "Flight cancelled by the airline"))
            else:
                self.assertEqual(p.status, PaymentStatus.PAID, d.booking.pnr)

    def test_PY24_invoice_numbers_are_unique(self):
        invoices = [r[0] for r in self.conn.execute("SELECT invoice_no FROM payments")]
        self.assertEqual(len(invoices), len(set(invoices)))
        self.assertTrue(all(i.startswith("INV-") for i in invoices))


class TestRefunds(PaymentCase):
    def booking_of(self, pnr):
        return self.checkin.find_booking(pnr).booking

    def test_PY25_cancel_inside_two_to_24_hours_keeps_half_the_fare(self):
        b = self.booking_of("K7Q2MA")                                       # AI202 departs in 3 h; fare 5400
        quote = self.pay.refund_quote(b.booking_id, now=NOW)
        self.assertEqual((quote.percent, quote.charge, quote.convenience_fee, quote.refund), (50, 2700, 150, 3180))
        self.bookings.cancel_booking(self.priya, b.booking_id, now=NOW)
        p = self.pay.get_payment(b.booking_id)
        self.assertEqual((p.status, p.refund_amount, p.refund_reason), (PaymentStatus.REFUNDED, 3180, "Cancelled by passenger"))

    def test_PY26_cancel_well_ahead_costs_ten_percent(self):
        b = self.booking_of("H2N6YE")                                       # UK811 in 54 h; fare 4800, total 5400
        self.assertEqual(self.pay.refund_quote(b.booking_id, now=NOW).refund, 5400 - 150 - 480)
        self.bookings.cancel_booking(self.rahul, b.booking_id, now=NOW)
        self.assertEqual(self.pay.get_payment(b.booking_id).refund_amount, 4770)

    def test_PY27_cancel_in_the_last_two_hours_refunds_only_taxes_not_fare(self):
        b = self.booking_of("K7Q2MA")
        late = NOW + timedelta(hours=2, minutes=30)                         # 30 minutes before departure
        q = self.pay.refund_quote(b.booking_id, now=late)
        self.assertEqual((q.percent, q.charge), (100, 5400))
        self.assertEqual(q.refund, 6030 - 150 - 5400)                       # airport fee + GST come back

    def test_PY28_admin_cancellation_refunds_the_same_way(self):
        b = self.booking_of("H2N6YE")
        self.bookings.cancel_booking(self.admin, b.booking_id, now=NOW)
        p = self.pay.get_payment(b.booking_id)
        self.assertEqual((p.refund_amount, p.refund_reason), (4770, "Cancelled by administrator"))

    def test_PY29_unpaid_booking_cancels_with_nothing_to_refund(self):
        b = self.bookings.book_ticket(self.priya, self.uk(), "1A", now=NOW)
        self.assertEqual(self.pay.refund_quote(b.booking_id, now=NOW).refund, 0)
        self.bookings.cancel_booking(self.priya, b.booking_id, now=NOW)
        self.assertIsNone(self.pay.get_payment(b.booking_id))

    def test_PY30_airline_cancelling_a_flight_refunds_every_passenger_in_full(self):
        before = self.pay.revenue()
        self.assertEqual(self.flights.cancel_flight(self.admin, self.flight("AI202").flight_id, now=NOW), 3)
        for pnr in ("K7Q2MA", "R4T9XB", "M3J8LC"):
            b = self.booking_of(pnr)
            p = self.pay.get_payment(b.booking_id)
            self.assertEqual((b.status, p.status, p.refund_amount), (BookingStatus.CANCELLED, PaymentStatus.REFUNDED, p.amount), pnr)
            self.assertEqual(p.refund_reason, "Flight cancelled by the airline")
        self.assertEqual(self.pay.revenue(), before - 3 * 6030)             # all three paid 5400 + fees

    def test_PY31_a_refund_happens_only_once(self):
        b = self.booking_of("K7Q2MA")
        self.bookings.cancel_booking(self.priya, b.booking_id, now=NOW)
        first = self.pay.get_payment(b.booking_id).refund_amount
        self.flights.cancel_flight(self.admin, self.flight("AI202").flight_id, now=NOW)   # must not refund it again
        self.assertEqual(self.pay.get_payment(b.booking_id).refund_amount, first)

    def test_PY32_checked_in_booking_cannot_be_cancelled_so_is_not_refunded(self):
        with self.assertRaises(BusinessRuleError):
            self.bookings.cancel_booking(self.rahul, self.booking_of("R4T9XB").booking_id, now=NOW)
        self.assertEqual(self.pay.get_payment(self.booking_of("R4T9XB").booking_id).status, PaymentStatus.PAID)

    def test_PY33_revenue_tracks_payments_and_refunds(self):
        start = self.pay.revenue()
        b, p = self.pay.book_and_pay(self.priya, self.uk(), "1A", "UPI", UPI, now=NOW)
        self.assertEqual(self.pay.revenue(), start + 5400)
        self.bookings.cancel_booking(self.priya, b.booking_id, now=NOW)                    # 54 h ahead -> 10% charge
        self.assertEqual(self.pay.revenue(), start + 5400 - 4770)


class TestReceipts(PaymentCase):
    def test_PY34_receipt_for_a_paid_booking(self):
        b = self.checkin.find_booking("K7Q2MA").booking
        name, data = self.pay.receipt_file(self.priya, b.booking_id)
        self.assertTrue(name.startswith("Receipt_INV-") and name.endswith("_K7Q2MA.pdf"))
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        for text in (b"PAYMENT RECEIPT", b"(PAID)", b"Rs 5,400", b"Rs 6,030", b"Priya Verma", b"K7Q2MA",
                     b"AI202", b"DEMO PAYMENT"):
            self.assertIn(text, data, text)

    def test_PY35_receipt_of_a_refunded_booking_shows_the_refund(self):
        b = self.checkin.find_booking("K7Q2MA").booking
        self.bookings.cancel_booking(self.priya, b.booking_id, now=NOW)
        _name, data = self.pay.receipt_file(self.priya, b.booking_id)
        for text in (b"(REFUNDED)", b"Rs 3,180 refunded", b"Cancelled by passenger", b"Kept: Rs 2,850"):
            self.assertIn(text, data, text)

    def test_PY36_receipt_access_rules(self):
        b = self.checkin.find_booking("K7Q2MA").booking
        self.assertTrue(self.pay.receipt_file(self.staff, b.booking_id)[1].startswith(b"%PDF"))
        self.assertTrue(self.pay.receipt_file(self.admin, b.booking_id)[1].startswith(b"%PDF"))
        with self.assertRaises(BusinessRuleError):
            self.pay.receipt_file(self.rahul, b.booking_id)                 # not his
        with self.assertRaises(AuthorizationError):
            self.pay.receipt_file(None, b.booking_id)
        with self.assertRaises(NotFoundError):
            self.pay.receipt_file(self.priya, 99999)

    def test_PY37_no_receipt_before_payment(self):
        b = self.bookings.book_ticket(self.priya, self.uk(), "1A", now=NOW)
        with self.assertRaises(BusinessRuleError):
            self.pay.receipt_file(self.priya, b.booking_id)


class TestLegacyMigration(PaymentCase):
    def test_PY38_old_databases_get_their_bookings_marked_paid_once(self):
        self.assertEqual(self.pay.migrate_legacy(now=NOW), 0)               # fresh database: nothing to do
        self.conn.execute("DELETE FROM payments")                           # simulate a pre-payments database
        self.conn.commit()
        live = self.conn.execute("SELECT COUNT(*) FROM bookings WHERE status <> 'CANCELLED'").fetchone()[0]
        self.assertEqual(self.pay.migrate_legacy(now=NOW), live)
        p = self.pay.get_payment(self.checkin.find_booking("K7Q2MA").booking.booking_id)
        self.assertEqual((p.method, p.status), ("LEGACY", PaymentStatus.PAID))
        self.assertEqual(self.pay.migrate_legacy(now=NOW), 0)               # never again
        self.assertEqual(self.checkin.check_in(self.staff, "K7Q2MA", now=NOW).pnr, "K7Q2MA")
        self.assertTrue(self.pay.receipt_file(self.priya, p.booking_id)[1].startswith(b"%PDF"))

    def test_PY39_one_payment_per_booking_is_enforced_by_the_database(self):
        import sqlite3
        b = self.checkin.find_booking("K7Q2MA").booking
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO payments (booking_id, invoice_no, method, instrument, amount, base_fare,"
                              " airport_fee, gst, convenience_fee, status, reference, paid_at)"
                              " VALUES (?, 'X', 'UPI', '', 1, 1, 0, 0, 0, 'PAID', 'r', '2026-01-01 00:00')", (b.booking_id,))

    def test_PY40_payments_for_returns_a_map_in_one_call(self):
        ids = [d.booking.booking_id for d in self.bookings.list_bookings(self.admin)]
        mapping = self.pay.payments_for(ids)
        self.assertEqual(set(mapping), set(ids))
        self.assertEqual(self.pay.payments_for([]), {})


if __name__ == "__main__":
    unittest.main()
