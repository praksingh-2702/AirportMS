"""Pure input-validation functions.

Each function takes raw (usually string) input from the GUI, returns the
normalised value, or raises ValidationError with a message the user can act on.
They touch no database and no GUI, so they are easy to black-box test.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from .config import (BANKS, DATE_FMT, DATETIME_FMT, MAX_BAG_WEIGHT_KG, MAX_FARE, MAX_FLIGHT_HOURS,
                     MAX_ROWS, MAX_SCHEDULE_DAYS, MIN_DURATION_MIN, MIN_FARE, MIN_ROWS, SEAT_COLUMNS)
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


# ---------- recurring schedule ----------
TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_DAY_WORDS = {"MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6, "SUN": 7}


def validate_dep_time(value) -> str:
    v = _text(value)
    if not TIME_RE.match(v):
        raise ValidationError("Departure time must be HH:MM in 24-hour format, e.g. 06:45.")
    return v


def validate_duration(value) -> int:
    try:
        minutes = int(_text(value))
    except ValueError:
        raise ValidationError("Duration must be a whole number of minutes.") from None
    if minutes < MIN_DURATION_MIN or minutes > MAX_FLIGHT_HOURS * 60:
        raise ValidationError(f"Duration must be between {MIN_DURATION_MIN} and {MAX_FLIGHT_HOURS * 60} minutes.")
    return minutes


def parse_days(value) -> str:
    """'Daily', 'Weekdays', 'Weekends', 'Mon,Wed,Fri' or digits like '135' -> sorted ISO weekday digits."""
    v = _text(value).upper().replace(" ", "")
    if v in ("DAILY", "EVERYDAY", "ALL"):
        return "1234567"
    if v == "WEEKDAYS":
        return "12345"
    if v == "WEEKENDS":
        return "67"
    parts = [p for p in re.split(r"[,;/]", v) if p]
    days = set()
    if len(parts) == 1 and parts[0].isdigit():
        parts = list(parts[0])                           # '135'
    for part in parts:
        if part.isdigit() and part in "1234567" and len(part) == 1:
            days.add(int(part))
        elif part[:3] in _DAY_WORDS:
            days.add(_DAY_WORDS[part[:3]])
        else:
            raise ValidationError("Days must be Daily, Weekdays, Weekends, or a list like Mon,Wed,Fri.")
    if not days:
        raise ValidationError("Choose at least one day of the week (e.g. Daily or Mon,Wed,Fri).")
    return "".join(str(d) for d in sorted(days))


def validate_horizon_days(value) -> int:
    try:
        days = int(_text(value))
    except ValueError:
        raise ValidationError("Number of days must be a whole number.") from None
    if days < 1 or days > MAX_SCHEDULE_DAYS:
        raise ValidationError(f"Number of days must be between 1 and {MAX_SCHEDULE_DAYS}.")
    return days


# ---------- payments (simulated) ----------
UPI_RE = re.compile(r"^[A-Za-z0-9._-]{2,64}@[A-Za-z][A-Za-z0-9]{1,30}$")
EXPIRY_RE = re.compile(r"^(0[1-9]|1[0-2])\s*/\s*(\d{2})$")


def card_brand(number: str) -> str:
    if number.startswith("4"):
        return "VISA"
    if number[:2] in ("34", "37"):
        return "AMEX"
    if number[:2] in ("51", "52", "53", "54", "55") or 2221 <= int(number[:4] or 0) <= 2720:
        return "MASTERCARD"
    return "CARD"


def validate_card_number(value) -> str:
    digits = re.sub(r"[ -]", "", _text(value))
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        raise ValidationError("Card number must be 13-19 digits.")
    total = 0
    for i, ch in enumerate(reversed(digits)):          # Luhn check catches mistyped digits
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    if total % 10 != 0:
        raise ValidationError("That card number is not valid. Check the digits.")
    return digits


def validate_expiry(value, now: datetime) -> str:
    match = EXPIRY_RE.match(_text(value))
    if not match:
        raise ValidationError("Expiry must be in MM/YY format, e.g. 08/29.")
    month, year = int(match.group(1)), 2000 + int(match.group(2))
    if (year, month) < (now.year, now.month):
        raise ValidationError("This card has expired.")
    return f"{month:02d}/{year % 100:02d}"


def validate_cvv(value, number: str = "") -> str:
    cvv = _text(value)
    want = 4 if number[:2] in ("34", "37") else 3
    if not cvv.isdigit() or len(cvv) != want:
        raise ValidationError(f"CVV must be {want} digits.")
    return cvv


def validate_cardholder(value) -> str:
    name = " ".join(_text(value).split())
    if not NAME_RE.match(name):
        raise ValidationError("Enter the name as printed on the card (letters only).")
    return name


def validate_upi_id(value) -> str:
    upi = _text(value)
    if not UPI_RE.match(upi):
        raise ValidationError("UPI ID must look like name@bank, e.g. priya@okaxis.")
    return upi


def validate_bank(value) -> str:
    bank = _text(value)
    if bank not in BANKS:
        raise ValidationError("Choose your bank from the list.")
    return bank
