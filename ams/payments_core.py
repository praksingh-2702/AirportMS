"""Payment arithmetic and the few SQL helpers shared by the booking, flight and payment services.

Kept free of service imports so BookingService and FlightService can issue refunds without a circular import.
Everything is SIMULATED and illustrative: fees, tax rate and refund tiers live in config.py.
"""
import secrets
import sqlite3
from datetime import datetime
from typing import Optional

from .config import AIRPORT_USER_FEE, CONVENIENCE_FEE, GST_RATE_PERCENT, REFUND_TIERS
from .models import FareBreakdown, Payment, RefundQuote, fmt_dt, to_dt


def fare_breakdown(base_fare: int) -> FareBreakdown:
    gst = int(round((base_fare + AIRPORT_USER_FEE) * GST_RATE_PERCENT / 100.0))
    return FareBreakdown(base_fare, AIRPORT_USER_FEE, gst, CONVENIENCE_FEE)


def cancellation_percent(hours_to_departure: float) -> int:
    """Cancellation charge (% of base fare) for a passenger-initiated cancellation."""
    for min_hours, percent in REFUND_TIERS:
        if hours_to_departure >= min_hours:
            return percent
    return 100


def quote_refund(payment: Payment, hours_to_departure: float, full: bool = False) -> RefundQuote:
    """Refund = amount paid - convenience fee - cancellation charge (never below zero).
    `full` (the airline cancelled the flight) refunds everything, convenience fee included."""
    if full:
        return RefundQuote(payment.amount, 0, 0, 0)
    percent = cancellation_percent(hours_to_departure)
    charge = int(round(payment.breakdown.base_fare * percent / 100.0))
    refund = max(0, payment.amount - payment.breakdown.convenience_fee - charge)
    return RefundQuote(refund, charge, percent, payment.breakdown.convenience_fee)


def gateway_reference() -> str:
    return "GW" + secrets.token_hex(5).upper()


def record_payment(conn: sqlite3.Connection, booking_id: int, method: str, instrument: str,
                   breakdown: FareBreakdown, reference: Optional[str], paid_at: datetime) -> int:
    """Insert a PAID payment and give it its invoice number. Does not commit."""
    cur = conn.execute(
        "INSERT INTO payments (booking_id, invoice_no, method, instrument, amount, base_fare, airport_fee, gst,"
        " convenience_fee, status, reference, paid_at) VALUES (?, 'PENDING', ?,?,?,?,?,?,?,'PAID',?,?)",
        (booking_id, method, instrument, breakdown.total, breakdown.base_fare, breakdown.airport_fee,
         breakdown.gst, breakdown.convenience_fee, reference or gateway_reference(), fmt_dt(paid_at)))
    pid = cur.lastrowid
    conn.execute("UPDATE payments SET invoice_no = ? WHERE payment_id = ?",
                 (f"INV-{paid_at:%Y%m%d}-{pid:05d}", pid))
    return pid


def get_payment(conn: sqlite3.Connection, booking_id: int) -> Optional[Payment]:
    row = conn.execute("SELECT * FROM payments WHERE booking_id = ?", (booking_id,)).fetchone()
    return Payment.from_row(row) if row else None


def refund_booking(conn: sqlite3.Connection, booking_id: int, now: datetime, full: bool, reason: str) -> int:
    """Refund the booking's payment if it has an unrefunded one. Returns the amount refunded (0 if none).
    Does not commit: the caller refunds inside the same transaction that cancels the booking."""
    payment = get_payment(conn, booking_id)
    if payment is None or payment.status.value != "PAID":
        return 0
    departure = to_dt(conn.execute(
        "SELECT f.departure FROM bookings b JOIN flights f ON f.flight_id = b.flight_id WHERE b.booking_id = ?",
        (booking_id,)).fetchone()[0])
    hours = (departure - now).total_seconds() / 3600.0
    quote = quote_refund(payment, hours, full)
    conn.execute("UPDATE payments SET status = 'REFUNDED', refund_amount = ?, refund_reason = ?, refunded_at = ?"
                 " WHERE payment_id = ?", (quote.refund, reason, fmt_dt(now), payment.payment_id))
    return quote.refund


def refund_flight(conn: sqlite3.Connection, flight_id: int, now: datetime) -> int:
    """Full refund for every active booking on a flight the airline is cancelling. Returns total refunded."""
    ids = [r[0] for r in conn.execute(
        "SELECT booking_id FROM bookings WHERE flight_id = ? AND status <> 'CANCELLED'", (flight_id,))]
    return sum(refund_booking(conn, b, now, True, "Flight cancelled by the airline") for b in ids)
