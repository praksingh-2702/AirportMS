"""Payment receipt / invoice PDF (standard library only, same tiny PDF writer as the boarding pass).

The receipt is for a SIMULATED payment and says so on the page: no money was charged and the fees and tax
shown are illustrative.
"""
from datetime import datetime

from .boarding_pdf import ACCENT, INK, MUTED, NAVY, PAGE_BG, PAPER, _Canvas
from .models import Payment, PaymentStatus
from .network import AIRPORTS

GREEN, AMBER = "#15803D", "#B45309"


def receipt_filename(payment: Payment, pnr: str) -> str:
    return f"Receipt_{payment.invoice_no}_{pnr}.pdf"


def _rs(amount: int) -> str:
    return f"Rs {amount:,}"


def render_receipt(payment: Payment, passenger: str, email: str, pnr: str, flight_no: str, origin: str,
                   destination: str, departure: datetime, seat: str) -> bytes:
    W, H = 595, 640
    c = _Canvas(W, H)
    c.rect(0, 0, W, H, fill=PAGE_BG)
    c.rect(20, 20, W - 40, H - 40, fill=PAPER, stroke="#C3CEDC", lw=0.8)

    # header
    c.rect(20, H - 100, W - 40, 80, fill=NAVY)
    c.text(44, H - 52, "PAYMENT RECEIPT", 20, "#FFFFFF", bold=True)
    c.text(44, H - 72, "Airport Management System", 9.5, "#9DB7DC")
    c.text(W - 44, H - 48, payment.invoice_no, 12, "#FFFFFF", bold=True, align="r")
    c.text(W - 44, H - 66, payment.paid_at.strftime("%d %b %Y, %H:%M"), 9.5, "#9DB7DC", align="r")
    stamp, stamp_color = ("PAID", GREEN) if payment.status == PaymentStatus.PAID else ("REFUNDED", AMBER)
    c.rect(W - 44 - 74, H - 92, 74, 17, fill=stamp_color)
    c.text(W - 44 - 37, H - 87, stamp, 9.5, "#FFFFFF", bold=True, align="c")

    # billed to / booking
    y = H - 135
    c.text(44, y, "BILLED TO", 8, MUTED)
    c.text(44, y - 17, passenger, 13, INK, bold=True)
    c.text(44, y - 33, email, 9.5, MUTED)
    c.text(310, y, "BOOKING", 8, MUTED)
    c.text(310, y - 17, f"PNR {pnr}", 13, INK, bold=True)
    c.text(310, y - 33, f"{flight_no}   {origin} to {destination}", 9.5, MUTED)
    cities = f"{AIRPORTS.get(origin, origin)} to {AIRPORTS.get(destination, destination)}"
    c.text(310, y - 47, f"{cities}  |  Seat {seat}", 9.5, MUTED)
    c.text(310, y - 61, f"Departs {departure.strftime('%d %b %Y, %H:%M')}", 9.5, MUTED)

    # charges table
    top = y - 100
    c.rect(44, top - 22, W - 88, 22, fill="#E3EAF3")
    c.text(56, top - 15, "DESCRIPTION", 8, MUTED, bold=True)
    c.text(W - 56, top - 15, "AMOUNT", 8, MUTED, bold=True, align="r")
    b = payment.breakdown
    rows = [("Base fare", b.base_fare), ("Airport user fee", b.airport_fee), ("GST (5% on fare + airport fee)", b.gst),
            ("Convenience fee", b.convenience_fee)]
    row_y = top - 42
    for label, amount in rows:
        c.text(56, row_y, label, 11, INK)
        c.text(W - 56, row_y, _rs(amount), 11, INK, align="r")
        c.line(44, row_y - 8, W - 44, row_y - 8, "#EEF2F7", 0.8)
        row_y -= 26
    c.rect(44, row_y - 12, W - 88, 30, fill="#EEF4FF")
    c.text(56, row_y - 2, "TOTAL PAID", 12, INK, bold=True)
    c.text(W - 56, row_y - 2, _rs(payment.amount), 14, ACCENT, bold=True, align="r")
    row_y -= 48

    # payment details
    c.text(44, row_y, "PAYMENT METHOD", 8, MUTED)
    method = {"CARD": "Card", "UPI": "UPI", "NETBANKING": "Net banking", "LEGACY": "Recorded earlier"}[payment.method]
    c.text(44, row_y - 16, f"{method}  -  {payment.instrument}", 11, INK, bold=True)
    c.text(310, row_y, "GATEWAY REFERENCE", 8, MUTED)
    c.text(310, row_y - 16, payment.reference, 11, INK, bold=True)
    row_y -= 52

    if payment.status == PaymentStatus.REFUNDED:
        c.rect(44, row_y - 50, W - 88, 66, fill="#FFF7ED", stroke="#FED7AA", lw=0.8)
        c.text(56, row_y - 2, "REFUND", 8, AMBER, bold=True)
        when = payment.refunded_at.strftime("%d %b %Y, %H:%M") if payment.refunded_at else ""
        c.text(56, row_y - 20, f"{_rs(payment.refund_amount)} refunded on {when}", 11, INK, bold=True)
        kept = payment.amount - payment.refund_amount
        c.text(56, row_y - 36, f"{payment.refund_reason or ''}   |   Kept: {_rs(kept)}", 9.5, MUTED)
        row_y -= 78

    c.line(44, 82, W - 44, 82, "#E2E8F0", 0.8)
    c.text(44, 64, "DEMO PAYMENT - no money was charged. Fees and tax shown are illustrative.", 8.5, MUTED)
    c.text(44, 51, "Card numbers and CVV are never stored; only the masked label above is kept.", 8.5, MUTED)
    return c.to_pdf(f"Receipt {payment.invoice_no}")
