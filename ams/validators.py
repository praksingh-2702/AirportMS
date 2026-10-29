"""Pure input-validation functions.

Each function takes raw (usually string) input from the GUI, returns the
normalised value, or raises ValidationError with a message the user can act on.
They touch no database and no GUI, so they are easy to black-box test.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from .config import (DATE_FMT, DATETIME_FMT, MAX_BAG_WEIGHT_KG, MAX_FARE,
                     MAX_FLIGHT_HOURS, MAX_ROWS, MIN_FARE, MIN_ROWS, SEAT_COLUMNS)
from .errors import ValidationError

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[6-9]\d{9}$")                  # 10-digit Indian mobile number
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,49}$")
FLIGHT_NO_RE = re.compile(r"^(?:[A-Z]{2}|[A-Z]\d|\d[A-Z])\d{1,4}$")  # AI202, 6E5021, G8123
AIRPORT_RE = re.compile(r"^[A-Z]{3}$")                   # IATA code, e.g. DEL
GATE_RE = re.compile(r"^[A-D](?:[1-9]|1[0-9]|20)$")      # A1 .. D20
SEAT_RE = re.compile(r"^(\d{1,2})([A-Z])$")              # e.g. 12C
PNR_RE = re.compile(r"^[A-Z0-9]{6}$")


def _text(value) -> str:
    return "" if value is None else str(value).strip()


# ---------- accounts ----------
def validate_username(value) -> str:
    v = _text(value).lower()
    if not USERNAME_RE.match(v):
        raise ValidationError("Username must be 3-20 characters using lowercase letters, digits or _.")
    return v


def validate_password(value) -> str:
    v = "" if value is None else str(value)
    if len(v) < 6 or len(v) > 64:
        raise ValidationError("Password must be 6-64 characters long.")
    if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
        raise ValidationError("Password must contain at least one letter and one digit.")
    return v


def validate_full_name(value) -> str:
    v = " ".join(_text(value).split())
    if not NAME_RE.match(v):
        raise ValidationError("Full name must be 2-50 letters (spaces, . ' - allowed).")
    return v


def validate_email(value) -> str:
    v = _text(value)
    if not EMAIL_RE.match(v):
        raise ValidationError("Enter a valid e-mail address, e.g. name@example.com.")
    return v.lower()


def validate_phone(value) -> str:
    v = _text(value).replace(" ", "")
    if not PHONE_RE.match(v):
        raise ValidationError("Phone must be a 10-digit mobile number starting with 6-9.")
    return v


# ---------- flights ----------
def validate_flight_no(value) -> str:
    v = _text(value).upper().replace(" ", "")
    if not FLIGHT_NO_RE.match(v):
        raise ValidationError("Flight number must be a 2-character airline code + 1-4 digits, e.g. AI202.")
    return v


def validate_airline(value) -> str:
    v = " ".join(_text(value).split())
    if len(v) < 2 or len(v) > 40:
        raise ValidationError("Airline name must be 2-40 characters.")
    return v


def validate_airport_code(value, field: str = "Airport code") -> str:
    v = _text(value).upper()
    if not AIRPORT_RE.match(v):
        raise ValidationError(f"{field} must be a 3-letter IATA code, e.g. DEL.")
    return v


def validate_route(origin, destination) -> Tuple[str, str]:
    o = validate_airport_code(origin, "Origin")
    d = validate_airport_code(destination, "Destination")
    if o == d:
        raise ValidationError("Origin and destination must be different airports.")
    return o, d


def parse_datetime(value, field: str = "Date/time") -> datetime:
    try:
        return datetime.strptime(_text(value), DATETIME_FMT)
    except ValueError:
        raise ValidationError(f"{field} must be in YYYY-MM-DD HH:MM format, e.g. 2026-11-05 14:30.") from None


def parse_date(value) -> Optional[str]:
    """Optional search date. Empty -> None, otherwise must be YYYY-MM-DD."""
    v = _text(value)
    if not v:
        return None
    try:
        datetime.strptime(v, DATE_FMT)
    except ValueError:
        raise ValidationError("Date must be in YYYY-MM-DD format, e.g. 2026-11-05.") from None
    return v


def validate_schedule(departure: datetime, arrival: datetime, now: datetime) -> None:
    if departure <= now:
        raise ValidationError("Departure time must be in the future.")
    if arrival <= departure:
        raise ValidationError("Arrival time must be after departure time.")
    if arrival - departure > timedelta(hours=MAX_FLIGHT_HOURS):
        raise ValidationError(f"Flight duration cannot exceed {MAX_FLIGHT_HOURS} hours.")


def validate_rows(value) -> int:
    try:
        rows = int(_text(value))
    except ValueError:
        raise ValidationError("Number of seat rows must be a whole number.") from None
    if rows < MIN_ROWS or rows > MAX_ROWS:
        raise ValidationError(f"Number of seat rows must be between {MIN_ROWS} and {MAX_ROWS}.")
    return rows


def validate_fare(value) -> int:
    try:
        fare = int(_text(value))
    except ValueError:
        raise ValidationError("Fare must be a whole number of rupees.") from None
    if fare < MIN_FARE or fare > MAX_FARE:
        raise ValidationError(f"Fare must be between Rs {MIN_FARE} and Rs {MAX_FARE}.")
    return fare


def validate_gate(value) -> Optional[str]:
    """Empty gate means 'not yet assigned' and returns None."""
    v = _text(value).upper()
    if not v:
        return None
    if not GATE_RE.match(v):
        raise ValidationError("Gate must be a terminal letter A-D followed by 1-20, e.g. B7.")
    return v


# ---------- bookings / check-in ----------
def parse_seat(value, rows: int) -> str:
    """Validate a seat label like '12C' for an aircraft with `rows` rows."""
    v = _text(value).upper()
    match = SEAT_RE.match(v)
    if not match:
        raise ValidationError("Seat must be a row number followed by a letter, e.g. 12C.")
    row, col = int(match.group(1)), match.group(2)
    if col not in SEAT_COLUMNS:
        raise ValidationError(f"Seat letter must be one of {', '.join(SEAT_COLUMNS)}.")
    if row < 1 or row > rows:
        raise ValidationError(f"Seat row must be between 1 and {rows} on this flight.")
    return f"{row}{col}"


def validate_pnr(value) -> str:
    v = _text(value).upper()
    if not PNR_RE.match(v):
        raise ValidationError("PNR must be exactly 6 letters/digits, e.g. K7Q2MA.")
    return v


def validate_bag_weight(value) -> float:
    try:
        weight = float(_text(value))
    except ValueError:
        raise ValidationError("Bag weight must be a number in kg, e.g. 18.5.") from None
    if weight <= 0:
        raise ValidationError("Bag weight must be greater than 0 kg.")
    if weight > MAX_BAG_WEIGHT_KG:
        raise ValidationError(f"A single bag cannot exceed {MAX_BAG_WEIGHT_KG:g} kg; send it as cargo.")
    return round(weight, 1)
