"""Domain entities (immutable data classes) and status enumerations.

These classes carry data only; all behaviour lives in the service classes.
They correspond one-to-one to the entity classes in the class diagram.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .config import DATETIME_FMT, SEAT_COLUMNS


def to_dt(text: Optional[str]) -> Optional[datetime]:
    """Convert a stored 'YYYY-MM-DD HH:MM' string to datetime (None stays None)."""
    return datetime.strptime(text, DATETIME_FMT) if text else None


def fmt_dt(value: Optional[datetime]) -> str:
    """Convert a datetime to the stored/displayed string format."""
    return value.strftime(DATETIME_FMT) if value else ""


class Role(str, Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    PASSENGER = "PASSENGER"


class FlightStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DELAYED = "DELAYED"
    BOARDING = "BOARDING"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"


class BookingStatus(str, Enum):
    BOOKED = "BOOKED"
    CHECKED_IN = "CHECKED_IN"
    CANCELLED = "CANCELLED"


class BagStatus(str, Enum):
    CHECKED_IN = "CHECKED_IN"
    LOADED = "LOADED"
    UNLOADED = "UNLOADED"
    CLAIMED = "CLAIMED"
    MISHANDLED = "MISHANDLED"


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    role: Role
    full_name: str
    email: str
    phone: str

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(row["user_id"], row["username"], Role(row["role"]),
                   row["full_name"], row["email"], row["phone"])


@dataclass(frozen=True)
class Flight:
    flight_id: int
    flight_no: str
    airline: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    gate: Optional[str]
    rows: int
    fare: int
    status: FlightStatus

    @property
    def capacity(self) -> int:
        return self.rows * len(SEAT_COLUMNS)

    @classmethod
    def from_row(cls, row) -> "Flight":
        return cls(row["flight_id"], row["flight_no"], row["airline"], row["origin"],
                   row["destination"], to_dt(row["departure"]), to_dt(row["arrival"]),
                   row["gate"], row["rows"], row["fare"], FlightStatus(row["status"]))


DAY_NAMES = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


@dataclass(frozen=True)
class FlightTemplate:
    """A recurring service, e.g. 6E6001 DEL->BOM at 06:10 on the days listed. `days` holds ISO weekday
    digits (1 = Monday ... 7 = Sunday)."""
    template_id: int
    flight_no: str
    airline: str
    origin: str
    destination: str
    dep_time: str
    duration_min: int
    days: str
    rows: int
    base_fare: int
    active: bool

    @property
    def days_label(self) -> str:
        if self.days == "1234567":
            return "Daily"
        return ",".join(DAY_NAMES[int(d)] for d in self.days)

    @classmethod
    def from_row(cls, row) -> "FlightTemplate":
        return cls(row["template_id"], row["flight_no"], row["airline"], row["origin"], row["destination"],
                   row["dep_time"], row["duration_min"], row["days"], row["rows"], row["base_fare"],
                   bool(row["active"]))


@dataclass(frozen=True)
class Booking:
    booking_id: int
    pnr: str
    user_id: int
    flight_id: int
    seat: str
    fare: int
    status: BookingStatus
    booked_at: datetime
    checked_in_at: Optional[datetime]
    boarding_seq: Optional[int]

    @classmethod
    def from_row(cls, row) -> "Booking":
        return cls(row["booking_id"], row["pnr"], row["user_id"], row["flight_id"],
                   row["seat"], row["fare"], BookingStatus(row["status"]),
                   to_dt(row["booked_at"]), to_dt(row["checked_in_at"]), row["boarding_seq"])


@dataclass(frozen=True)
class BookingDetails:
    """A booking joined with its passenger and flight, used for display."""
    booking: Booking
    passenger_name: str
    flight_no: str
    origin: str
    destination: str
    departure: datetime
    gate: Optional[str]
    flight_status: FlightStatus

    @classmethod
    def from_row(cls, row) -> "BookingDetails":
        return cls(Booking.from_row(row), row["full_name"], row["flight_no"], row["origin"],
                   row["destination"], to_dt(row["departure"]), row["gate"],
                   FlightStatus(row["flight_status"]))


class PaymentStatus(str, Enum):
    PAID = "PAID"
    REFUNDED = "REFUNDED"


@dataclass(frozen=True)
class FareBreakdown:
    base_fare: int
    airport_fee: int
    gst: int
    convenience_fee: int

    @property
    def total(self) -> int:
        return self.base_fare + self.airport_fee + self.gst + self.convenience_fee


@dataclass(frozen=True)
class RefundQuote:
    """What a passenger would get back if they cancelled now (refund = 0 when there is nothing to refund)."""
    refund: int
    charge: int                 # cancellation charge kept by the airline
    percent: int                # that charge as a percentage of the base fare
    convenience_fee: int        # never refunded


@dataclass(frozen=True)
class Payment:
    payment_id: int
    booking_id: int
    invoice_no: str
    method: str                 # CARD | UPI | NETBANKING | LEGACY
    instrument: str             # masked, e.g. "VISA XXXX 4242" - the full number and CVV are never stored
    amount: int
    breakdown: FareBreakdown
    status: PaymentStatus
    reference: str
    paid_at: datetime
    refund_amount: int
    refund_reason: Optional[str]
    refunded_at: Optional[datetime]

    @classmethod
    def from_row(cls, row) -> "Payment":
        return cls(row["payment_id"], row["booking_id"], row["invoice_no"], row["method"], row["instrument"],
                   row["amount"], FareBreakdown(row["base_fare"], row["airport_fee"], row["gst"],
                                                row["convenience_fee"]),
                   PaymentStatus(row["status"]), row["reference"], to_dt(row["paid_at"]), row["refund_amount"],
                   row["refund_reason"], to_dt(row["refunded_at"]))


@dataclass(frozen=True)
class Bag:
    bag_id: int
    booking_id: int
    tag_no: str
    weight_kg: float
    status: BagStatus
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "Bag":
        return cls(row["bag_id"], row["booking_id"], row["tag_no"], row["weight_kg"],
                   BagStatus(row["status"]), to_dt(row["updated_at"]))


@dataclass(frozen=True)
class BoardingPass:
    pnr: str
    passenger_name: str
    flight_no: str
    origin: str
    destination: str
    departure: datetime
    boarding_time: datetime
    gate: Optional[str]
    seat: str
    boarding_seq: int

    def as_text(self) -> str:
        return (
            "BOARDING PASS\n"
            f"Passenger : {self.passenger_name}\n"
            f"PNR       : {self.pnr}\n"
            f"Flight    : {self.flight_no}   {self.origin} -> {self.destination}\n"
            f"Departure : {fmt_dt(self.departure)}\n"
            f"Boarding  : {fmt_dt(self.boarding_time)}\n"
            f"Gate      : {self.gate or 'TBA'}    Seat: {self.seat}    Seq: {self.boarding_seq:03d}"
        )
