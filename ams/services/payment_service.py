"""Module 5 - Payments (simulated): fare breakdown, pay for a booking, refunds and PDF receipts.

A passenger pays when booking: `book_and_pay` creates the booking only if the demo gateway approves, so a
declined payment never leaves a seat held. Cancelling refunds according to config.REFUND_TIERS; a flight
cancelled by the airline refunds everything. No real money moves and no card number or CVV is stored.
"""
import sqlite3
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple

from .. import gateway
from .. import validators as v
from ..access import require_role
from ..errors import BusinessRuleError, NotFoundError, PaymentError, ValidationError
from ..models import (Booking, BookingStatus, FareBreakdown, FlightStatus, Payment, PaymentStatus, RefundQuote,
                      Role, User, fmt_dt, to_dt)
from ..payments_core import fare_breakdown, get_payment, quote_refund, record_payment
from ..receipt_pdf import receipt_filename, render_receipt
from .booking_service import DETAILS_SQL, BookingService

METHODS = ("CARD", "UPI", "NETBANKING")


class PaymentService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._bookings = BookingService(conn)

    # ----- pricing / lookup -----
    @staticmethod
    def quote(base_fare: int) -> FareBreakdown:
        return fare_breakdown(int(base_fare))

    def get_payment(self, booking_id: int) -> Optional[Payment]:
        return get_payment(self.conn, booking_id)

    def payments_for(self, booking_ids: Iterable[int]) -> Dict[int, Payment]:
        ids = list(booking_ids)
        if not ids:
            return {}
        rows = self.conn.execute(f"SELECT * FROM payments WHERE booking_id IN ({','.join('?' * len(ids))})", ids)
        return {r["booking_id"]: Payment.from_row(r) for r in rows}

    def revenue(self) -> int:
        """Money kept: everything paid minus everything refunded."""
        row = self.conn.execute("SELECT COALESCE(SUM(amount - refund_amount), 0) FROM payments").fetchone()
        return int(row[0])

    # ----- validation of what the passenger typed -----
    def _clean(self, method: str, details: dict, now: datetime) -> Tuple[dict, str]:
        """Validate the details for `method`; return (clean details, masked label to store)."""
        details = details or {}
        if method == "CARD":
            number = v.validate_card_number(details.get("number"))
            clean = dict(number=number, expiry=v.validate_expiry(details.get("expiry"), now),
                         cvv=v.validate_cvv(details.get("cvv"), number), name=v.validate_cardholder(details.get("name")))
            return clean, f"{v.card_brand(number)} XXXX {number[-4:]}"
        if method == "UPI":
            upi = v.validate_upi_id(details.get("upi_id"))
            user, handle = upi.split("@", 1)
            return dict(upi_id=upi), f"{user[:2]}***@{handle}"
        if method == "NETBANKING":
            bank = v.validate_bank(details.get("bank"))
            return dict(bank=bank), bank
        raise ValidationError("Choose a payment method: card, UPI or net banking.")

    # ----- paying -----
    def book_and_pay(self, actor: User, flight_id: int, seat, method: str, details: dict,
                     now: Optional[datetime] = None) -> Tuple[Booking, Payment]:
        """Reserve the seat, charge the (demo) gateway and confirm - or leave nothing behind if it declines."""
        require_role(actor, Role.PASSENGER)
        now = now or datetime.now()
        clean, instrument = self._clean(method, details, now)         # bad input never reaches the gateway
        booking = self._bookings.book_ticket(actor, flight_id, seat, now=now)   # also checks seat/flight rules
        breakdown = fare_breakdown(booking.fare)
        result = gateway.authorize(method, clean, breakdown.total)
        if not result.approved:
            self.conn.execute("DELETE FROM bookings WHERE booking_id = ?", (booking.booking_id,))   # release the seat
            self.conn.commit()
            raise PaymentError(result.message)
        record_payment(self.conn, booking.booking_id, method, instrument, breakdown, result.reference, now)
        self.conn.commit()
        return booking, self.get_payment(booking.booking_id)

    def pay_booking(self, actor: User, booking_id: int, method: str, details: dict,
                    now: Optional[datetime] = None) -> Payment:
        """Pay for an existing, still-unpaid booking."""
        require_role(actor, Role.PASSENGER)
        now = now or datetime.now()
        booking = self._bookings.get_booking(booking_id)
        if booking.user_id != actor.user_id:
            raise BusinessRuleError("You can only pay for your own bookings.")
        if booking.status == BookingStatus.CANCELLED:
            raise BusinessRuleError(f"Booking {booking.pnr} is cancelled.")
        status = FlightStatus(self.conn.execute("SELECT status FROM flights WHERE flight_id = ?",
                                                (booking.flight_id,)).fetchone()[0])
        if status in (FlightStatus.CANCELLED, FlightStatus.DEPARTED):
            raise BusinessRuleError(f"This flight is {status.value}; payment is closed.")
        if self.get_payment(booking_id):
            raise BusinessRuleError(f"Booking {booking.pnr} is already paid.")
        clean, instrument = self._clean(method, details, now)
        breakdown = fare_breakdown(booking.fare)
        result = gateway.authorize(method, clean, breakdown.total)
        if not result.approved:
            raise PaymentError(result.message)
        record_payment(self.conn, booking_id, method, instrument, breakdown, result.reference, now)
        self.conn.commit()
        return self.get_payment(booking_id)

    # ----- refunds -----
    def refund_quote(self, booking_id: int, now: Optional[datetime] = None) -> RefundQuote:
        """What cancelling this booking now would refund (all zeros when it is unpaid or already refunded)."""
        now = now or datetime.now()
        payment = self.get_payment(booking_id)
        if payment is None or payment.status != PaymentStatus.PAID:
            return RefundQuote(0, 0, 0, 0)
        departure = to_dt(self.conn.execute(
            "SELECT f.departure FROM bookings b JOIN flights f ON f.flight_id = b.flight_id WHERE b.booking_id = ?",
            (booking_id,)).fetchone()[0])
        return quote_refund(payment, (departure - now).total_seconds() / 3600.0)

    # ----- receipts -----
    def receipt_file(self, actor: User, booking_id: int) -> Tuple[str, bytes]:
        """(file name, PDF bytes). A passenger can only get their own receipt; staff and admins any."""
        require_role(actor, Role.PASSENGER, Role.STAFF, Role.ADMIN)
        row = self.conn.execute(DETAILS_SQL + " WHERE b.booking_id = ?", (booking_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Booking {booking_id} not found.")
        if actor.role == Role.PASSENGER and row["user_id"] != actor.user_id:
            raise BusinessRuleError("You can only view your own receipts.")
        payment = self.get_payment(booking_id)
        if payment is None:
            raise BusinessRuleError(f"Booking {row['pnr']} has not been paid, so there is no receipt yet.")
        city = self.conn.execute("SELECT email FROM users WHERE user_id = ?", (row["user_id"],)).fetchone()
        data = render_receipt(payment, passenger=row["full_name"], email=city["email"] if city else "",
                              pnr=row["pnr"], flight_no=row["flight_no"], origin=row["origin"],
                              destination=row["destination"], departure=to_dt(row["departure"]), seat=row["seat"])
        return receipt_filename(payment, row["pnr"]), data

    # ----- one-time upgrade of databases created before payments existed -----
    def migrate_legacy(self, now: Optional[datetime] = None) -> int:
        """If the payments table is empty but bookings exist (a database from before payments), record those
        active bookings as paid (method LEGACY) so they can still be checked in. Runs only once."""
        if self.conn.execute("SELECT 1 FROM payments LIMIT 1").fetchone():
            return 0
        rows = self.conn.execute("SELECT booking_id, fare, booked_at FROM bookings WHERE status <> 'CANCELLED'").fetchall()
        for r in rows:
            record_payment(self.conn, r["booking_id"], "LEGACY", "Booked before online payments",
                           fare_breakdown(r["fare"]), None, to_dt(r["booked_at"]))
        self.conn.commit()
        return len(rows)
