"""Module 3 - Check-in and baggage: check in, boarding pass, baggage tags and status."""
import math
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from ..access import require_role
from ..boarding_pdf import render_boarding_pass, suggested_filename
from ..config import (BOARDING_BEFORE_MINUTES, CHECKIN_CLOSES_MINUTES, CHECKIN_OPENS_HOURS,
                      EXCESS_RATE_PER_KG, FREE_BAGGAGE_KG, MAX_BAGS_PER_BOOKING)
from ..errors import BusinessRuleError, NotFoundError, ValidationError
from ..models import (Bag, BagStatus, BoardingPass, BookingDetails, BookingStatus, FlightStatus,
                      Role, User, fmt_dt)
from .. import validators as v
from .booking_service import DETAILS_SQL

# Allowed baggage status transitions (see the Baggage state-chart diagram)
BAG_TRANSITIONS = {
    BagStatus.CHECKED_IN: {BagStatus.LOADED, BagStatus.MISHANDLED},
    BagStatus.LOADED: {BagStatus.UNLOADED, BagStatus.MISHANDLED},
    BagStatus.UNLOADED: {BagStatus.CLAIMED, BagStatus.MISHANDLED},
    BagStatus.MISHANDLED: {BagStatus.CLAIMED},
    BagStatus.CLAIMED: set(),
}


def compute_excess_fee(total_weight_kg: float) -> int:
    """Excess-baggage fee in INR: Rs 500 for every started kg above the 15 kg allowance."""
    if total_weight_kg < 0:
        raise ValidationError("Total baggage weight cannot be negative.")
    excess = total_weight_kg - FREE_BAGGAGE_KG
    if excess <= 0:
        return 0
    return math.ceil(round(excess, 1)) * EXCESS_RATE_PER_KG


class CheckInService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ----- lookup -----
    def find_booking(self, pnr) -> BookingDetails:
        pnr = v.validate_pnr(pnr)
        row = self.conn.execute(DETAILS_SQL + " WHERE b.pnr = ?", (pnr,)).fetchone()
        if row is None:
            raise NotFoundError(f"No booking found with PNR {pnr}.")
        return BookingDetails.from_row(row)

    # ----- check-in -----
    def check_in(self, actor: User, pnr, now: Optional[datetime] = None) -> BoardingPass:
        """Check a passenger in and return the boarding pass.
        Check-in is open from 48 h until 45 min before departure."""
        require_role(actor, Role.STAFF, Role.ADMIN)
        now = now or datetime.now()
        details = self.find_booking(pnr)                                    # may raise NotFoundError
        booking = details.booking
        if booking.status == BookingStatus.CANCELLED:
            raise BusinessRuleError(f"Booking {booking.pnr} is cancelled.")
        if booking.status == BookingStatus.CHECKED_IN:
            raise BusinessRuleError(f"Passenger {details.passenger_name} is already checked in.")
        if details.flight_status in (FlightStatus.CANCELLED, FlightStatus.DEPARTED):
            raise BusinessRuleError(f"Flight {details.flight_no} is {details.flight_status.value}.")
        if not self.conn.execute("SELECT 1 FROM payments WHERE booking_id = ? AND status = 'PAID'",
                                 (booking.booking_id,)).fetchone():
            raise BusinessRuleError(f"Payment for booking {booking.pnr} is pending. "
                                    "The passenger must pay before check-in.")
        if now < details.departure - timedelta(hours=CHECKIN_OPENS_HOURS):
            raise BusinessRuleError(f"Check-in opens {CHECKIN_OPENS_HOURS} hours before departure.")
        if now > details.departure - timedelta(minutes=CHECKIN_CLOSES_MINUTES):
            raise BusinessRuleError(f"Check-in closed {CHECKIN_CLOSES_MINUTES} minutes before departure.")
        seq = self.conn.execute(
            "SELECT COALESCE(MAX(boarding_seq), 0) + 1 FROM bookings WHERE flight_id = ?",
            (booking.flight_id,)).fetchone()[0]
        self.conn.execute(
            "UPDATE bookings SET status = 'CHECKED_IN', checked_in_at = ?, boarding_seq = ?"
            " WHERE booking_id = ?", (fmt_dt(now), seq, booking.booking_id))
        self.conn.commit()
        return self.get_boarding_pass(actor, booking.pnr)

    def get_boarding_pass(self, actor: User, pnr) -> BoardingPass:
        """Staff/admin may view any pass; a passenger only their own."""
        require_role(actor, Role.STAFF, Role.ADMIN, Role.PASSENGER)
        details = self.find_booking(pnr)
        b = details.booking
        if actor.role == Role.PASSENGER and b.user_id != actor.user_id:
            raise BusinessRuleError("You can only view your own boarding pass.")
        if b.status != BookingStatus.CHECKED_IN:
            raise BusinessRuleError(f"Booking {b.pnr} is not checked in yet.")
        return BoardingPass(b.pnr, details.passenger_name, details.flight_no, details.origin,
                            details.destination, details.departure,
                            details.departure - timedelta(minutes=BOARDING_BEFORE_MINUTES),
                            details.gate, b.seat, b.boarding_seq)

    def boarding_pass_file(self, actor: User, pnr) -> Tuple[str, bytes]:
        """(suggested file name, PDF bytes) of a boarding pass. Same access rules as get_boarding_pass:
        staff/admin any pass, a passenger only their own, and only once the booking is checked in."""
        bp = self.get_boarding_pass(actor, pnr)
        return suggested_filename(bp), render_boarding_pass(bp)

    # ----- baggage -----
    def list_bags(self, pnr) -> List[Bag]:
        details = self.find_booking(pnr)
        rows = self.conn.execute("SELECT * FROM baggage WHERE booking_id = ? ORDER BY bag_id",
                                 (details.booking.booking_id,)).fetchall()
        return [Bag.from_row(r) for r in rows]

    def baggage_summary(self, pnr) -> Tuple[float, int]:
        """Return (total weight in kg, excess fee in INR) for a booking."""
        total = round(sum(b.weight_kg for b in self.list_bags(pnr)), 1)
        return total, compute_excess_fee(total)

    def add_bag(self, actor: User, pnr, weight, now: Optional[datetime] = None) -> Bag:
        require_role(actor, Role.STAFF, Role.ADMIN)
        now = now or datetime.now()
        details = self.find_booking(pnr)
        if details.booking.status != BookingStatus.CHECKED_IN:
            raise BusinessRuleError("Bags can be added only after the passenger has checked in.")
        if details.flight_status in (FlightStatus.CANCELLED, FlightStatus.DEPARTED):
            raise BusinessRuleError(f"Flight {details.flight_no} is {details.flight_status.value}.")
        weight = v.validate_bag_weight(weight)
        if len(self.list_bags(pnr)) >= MAX_BAGS_PER_BOOKING:
            raise BusinessRuleError(f"A passenger may check in at most {MAX_BAGS_PER_BOOKING} bags.")
        cur = self.conn.execute(
            "INSERT INTO baggage (booking_id, weight_kg, status, updated_at) VALUES (?,?,?,?)",
            (details.booking.booking_id, weight, BagStatus.CHECKED_IN.value, fmt_dt(now)))
        tag = f"AMS{cur.lastrowid:06d}"
        self.conn.execute("UPDATE baggage SET tag_no = ? WHERE bag_id = ?", (tag, cur.lastrowid))
        self.conn.commit()
        return self.get_bag(cur.lastrowid)

    def get_bag(self, bag_id: int) -> Bag:
        row = self.conn.execute("SELECT * FROM baggage WHERE bag_id = ?", (bag_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Bag {bag_id} not found.")
        return Bag.from_row(row)

    def update_bag_status(self, actor: User, bag_id: int, new_status,
                          now: Optional[datetime] = None) -> Bag:
        require_role(actor, Role.STAFF, Role.ADMIN)
        bag = self.get_bag(bag_id)
        try:
            new_status = BagStatus(new_status)
        except ValueError:
            raise ValidationError(f"Unknown baggage status '{new_status}'.") from None
        if new_status not in BAG_TRANSITIONS[bag.status]:
            raise BusinessRuleError(
                f"Bag {bag.tag_no} cannot change from {bag.status.value} to {new_status.value}.")
        self.conn.execute("UPDATE baggage SET status = ?, updated_at = ? WHERE bag_id = ?",
                          (new_status.value, fmt_dt(now or datetime.now()), bag_id))
        self.conn.commit()
        return self.get_bag(bag_id)
