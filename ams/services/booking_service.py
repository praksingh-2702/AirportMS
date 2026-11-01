"""Module 2 - Passenger booking: search flights, select seats, book and cancel tickets."""
import secrets
import sqlite3
from datetime import datetime
from typing import Callable, List, Optional, Set, Tuple

from ..access import require_role
from ..config import LIST_LIMIT
from ..errors import BusinessRuleError, NotFoundError
from ..models import (Booking, BookingDetails, BookingStatus, Flight, FlightStatus, Role,
                      User, fmt_dt)
from .. import validators as v
from ..payments_core import refund_booking

BOOKABLE_STATUSES = (FlightStatus.SCHEDULED, FlightStatus.DELAYED)
PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no I, O, 0, 1 (easily confused)

DETAILS_SQL = """
SELECT b.*, u.full_name, f.flight_no, f.origin, f.destination, f.departure, f.gate,
       f.status AS flight_status
FROM bookings b JOIN users u ON u.user_id = b.user_id JOIN flights f ON f.flight_id = b.flight_id
"""


def random_pnr() -> str:
    return "".join(secrets.choice(PNR_ALPHABET) for _ in range(6))


class BookingService:
    def __init__(self, conn: sqlite3.Connection, pnr_generator: Callable[[], str] = random_pnr):
        self.conn = conn
        self.pnr_generator = pnr_generator

    # ----- search -----
    def search_flights(self, origin=None, destination=None, date=None,
                       now: Optional[datetime] = None, limit: int = LIST_LIMIT) -> List[Tuple[Flight, int]]:
        """Return (flight, seats_left) for bookable future flights matching the filters, earliest first,
        at most `limit` of them. Blank filters match everything."""
        now = now or datetime.now()
        sql = ("SELECT * FROM flights WHERE status IN (?,?) AND departure > ?")
        params = [BOOKABLE_STATUSES[0].value, BOOKABLE_STATUSES[1].value, fmt_dt(now)]
        if origin and str(origin).strip():
            sql += " AND origin = ?"
            params.append(v.validate_airport_code(origin, "From"))
        if destination and str(destination).strip():
            sql += " AND destination = ?"
            params.append(v.validate_airport_code(destination, "To"))
        day = v.parse_date(date)
        if day:
            sql += " AND substr(departure,1,10) = ?"
            params.append(day)
        taken = {r[0]: r[1] for r in self.conn.execute(
            "SELECT flight_id, COUNT(*) FROM bookings WHERE status <> 'CANCELLED' GROUP BY flight_id")}
        results = []
        for row in self.conn.execute(sql + " ORDER BY departure LIMIT ?", params + [int(limit)]).fetchall():
            flight = Flight.from_row(row)
            results.append((flight, flight.capacity - taken.get(flight.flight_id, 0)))
        return results

    def get_taken_seats(self, flight_id: int) -> Set[str]:
        rows = self.conn.execute(
            "SELECT seat FROM bookings WHERE flight_id = ? AND status <> 'CANCELLED'", (flight_id,))
        return {r["seat"] for r in rows}

    # ----- book / cancel -----
    def book_ticket(self, actor: User, flight_id: int, seat, now: Optional[datetime] = None) -> Booking:
        require_role(actor, Role.PASSENGER)
        now = now or datetime.now()
        row = self.conn.execute("SELECT * FROM flights WHERE flight_id = ?", (flight_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Flight with id {flight_id} not found.")
        flight = Flight.from_row(row)
        if flight.status not in BOOKABLE_STATUSES:
            raise BusinessRuleError(f"Flight {flight.flight_no} is {flight.status.value}; booking is closed.")
        if flight.departure <= now:
            raise BusinessRuleError(f"Flight {flight.flight_no} has already departed.")
        seat = v.parse_seat(seat, flight.rows)
        if seat in self.get_taken_seats(flight_id):
            raise BusinessRuleError(f"Seat {seat} is already taken. Please choose another seat.")
        if self.conn.execute(
                "SELECT 1 FROM bookings WHERE user_id = ? AND flight_id = ? AND status <> 'CANCELLED'",
                (actor.user_id, flight_id)).fetchone():
            raise BusinessRuleError(f"You already hold a booking on flight {flight.flight_no}.")
        pnr = self._unique_pnr()
        try:
            cur = self.conn.execute(
                "INSERT INTO bookings (pnr, user_id, flight_id, seat, fare, status, booked_at)"
                " VALUES (?,?,?,?,?,'BOOKED',?)",
                (pnr, actor.user_id, flight_id, seat, flight.fare, fmt_dt(now)))
        except sqlite3.IntegrityError:   # seat taken by a concurrent booking
            self.conn.rollback()
            raise BusinessRuleError(f"Seat {seat} was just taken. Please choose another seat.") from None
        self.conn.commit()
        return self.get_booking(cur.lastrowid)

    def _unique_pnr(self) -> str:
        for _ in range(20):
            pnr = self.pnr_generator()
            if not self.conn.execute("SELECT 1 FROM bookings WHERE pnr = ?", (pnr,)).fetchone():
                return pnr
        raise BusinessRuleError("Could not generate a unique PNR; please try again.")

    def cancel_booking(self, actor: User, booking_id: int, now: Optional[datetime] = None) -> Booking:
        """Passengers may cancel their own bookings; admins may cancel any booking."""
        require_role(actor, Role.PASSENGER, Role.ADMIN)
        now = now or datetime.now()
        booking = self.get_booking(booking_id)
        if actor.role == Role.PASSENGER and booking.user_id != actor.user_id:
            raise BusinessRuleError("You can only cancel your own bookings.")
        if booking.status == BookingStatus.CANCELLED:
            raise BusinessRuleError(f"Booking {booking.pnr} is already cancelled.")
        if booking.status == BookingStatus.CHECKED_IN:
            raise BusinessRuleError(f"Booking {booking.pnr} is checked in and can no longer be cancelled.")
        dep = self.conn.execute("SELECT departure FROM flights WHERE flight_id = ?",
                                (booking.flight_id,)).fetchone()["departure"]
        if dep <= fmt_dt(now):
            raise BusinessRuleError("The flight has already departed.")
        self.conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = ?", (booking_id,))
        refund_booking(self.conn, booking_id, now, False, "Cancelled by " + ("passenger" if actor.role == Role.PASSENGER else "administrator"))
        self.conn.commit()
        return self.get_booking(booking_id)

    # ----- queries -----
    def get_booking(self, booking_id: int) -> Booking:
        row = self.conn.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Booking {booking_id} not found.")
        return Booking.from_row(row)

    def list_bookings(self, actor: User) -> List[BookingDetails]:
        """Passengers see their own bookings; staff and admins see all bookings."""
        require_role(actor, Role.PASSENGER, Role.STAFF, Role.ADMIN)
        if actor.role == Role.PASSENGER:
            rows = self.conn.execute(DETAILS_SQL + " WHERE b.user_id = ? ORDER BY f.departure",
                                     (actor.user_id,)).fetchall()
        else:
            rows = self.conn.execute(DETAILS_SQL + " ORDER BY f.departure, b.seat").fetchall()
        return [BookingDetails.from_row(r) for r in rows]
