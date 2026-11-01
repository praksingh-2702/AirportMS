"""SQLite connection, schema creation and realistic sample data.

The four tables correspond to the four data stores of the DFDs:
D1 USERS, D2 FLIGHTS, D3 BOOKINGS, D4 BAGGAGE.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from .config import DB_PATH
from .models import fmt_dt
from .security import hash_password

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('ADMIN','STAFF','PASSENGER')),
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    phone         TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS flights (
    flight_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_no   TEXT    NOT NULL,
    airline     TEXT    NOT NULL,
    origin      TEXT    NOT NULL CHECK (length(origin) = 3),
    destination TEXT    NOT NULL CHECK (length(destination) = 3),
    departure   TEXT    NOT NULL,
    arrival     TEXT    NOT NULL,
    gate        TEXT,
    rows        INTEGER NOT NULL CHECK (rows BETWEEN 1 AND 40),
    fare        INTEGER NOT NULL CHECK (fare > 0),
    status      TEXT    NOT NULL DEFAULT 'SCHEDULED'
                CHECK (status IN ('SCHEDULED','DELAYED','BOARDING','DEPARTED','CANCELLED')),
    UNIQUE (flight_no, departure)
);

-- D5: recurring services; the schedule generator turns them into dated rows of D2 FLIGHTS
CREATE TABLE IF NOT EXISTS flight_templates (
    template_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_no    TEXT    NOT NULL UNIQUE,
    airline      TEXT    NOT NULL,
    origin       TEXT    NOT NULL CHECK (length(origin) = 3),
    destination  TEXT    NOT NULL CHECK (length(destination) = 3),
    dep_time     TEXT    NOT NULL,
    duration_min INTEGER NOT NULL CHECK (duration_min BETWEEN 20 AND 1200),
    days         TEXT    NOT NULL DEFAULT '1234567',
    rows         INTEGER NOT NULL CHECK (rows BETWEEN 1 AND 40),
    base_fare    INTEGER NOT NULL CHECK (base_fare > 0),
    active       INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_flights_departure ON flights (departure);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    pnr           TEXT    NOT NULL UNIQUE,
    user_id       INTEGER NOT NULL REFERENCES users(user_id),
    flight_id     INTEGER NOT NULL REFERENCES flights(flight_id),
    seat          TEXT    NOT NULL,
    fare          INTEGER NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'BOOKED'
                  CHECK (status IN ('BOOKED','CHECKED_IN','CANCELLED')),
    booked_at     TEXT    NOT NULL,
    checked_in_at TEXT,
    boarding_seq  INTEGER
);

-- a seat can be held by at most one non-cancelled booking
CREATE UNIQUE INDEX IF NOT EXISTS ux_active_seat
    ON bookings (flight_id, seat) WHERE status <> 'CANCELLED';

-- D6: payments (simulated gateway). Card numbers and CVV are never stored, only a masked label.
CREATE TABLE IF NOT EXISTS payments (
    payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id      INTEGER NOT NULL REFERENCES bookings(booking_id),
    invoice_no      TEXT    NOT NULL UNIQUE,
    method          TEXT    NOT NULL CHECK (method IN ('CARD','UPI','NETBANKING','LEGACY')),
    instrument      TEXT    NOT NULL DEFAULT '',
    amount          INTEGER NOT NULL CHECK (amount > 0),
    base_fare       INTEGER NOT NULL,
    airport_fee     INTEGER NOT NULL,
    gst             INTEGER NOT NULL,
    convenience_fee INTEGER NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('PAID','REFUNDED')),
    reference       TEXT    NOT NULL,
    paid_at         TEXT    NOT NULL,
    refund_amount   INTEGER NOT NULL DEFAULT 0,
    refund_reason   TEXT,
    refunded_at     TEXT
);

-- a booking is paid for at most once
CREATE UNIQUE INDEX IF NOT EXISTS ux_payment_booking ON payments (booking_id);

CREATE TABLE IF NOT EXISTS baggage (
    bag_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(booking_id),
    tag_no     TEXT    UNIQUE,
    weight_kg  REAL    NOT NULL CHECK (weight_kg > 0 AND weight_kg <= 32),
    status     TEXT    NOT NULL DEFAULT 'CHECKED_IN'
               CHECK (status IN ('CHECKED_IN','LOADED','UNLOADED','CLAIMED','MISHANDLED')),
    updated_at TEXT    NOT NULL
);
"""


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    """Open a connection with dict-like rows and foreign keys enforced."""
    path = path or DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def is_empty(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def _insert_user(conn, username, password, role, full_name, email, phone, now):
    pw_hash, salt = hash_password(password)
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, salt, role, full_name, email, phone, created_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (username, pw_hash, salt, role, full_name, email, phone, fmt_dt(now)))
    return cur.lastrowid


def seed_sample_data(conn: sqlite3.Connection, now: Optional[datetime] = None) -> None:
    """Insert demo users, flights, bookings and bags. Times are relative to `now`
    so that the check-in window rules can always be demonstrated."""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    base = now.replace(minute=(now.minute // 5) * 5)   # round down to 5 minutes

    users = {
        "admin":  ("admin123", "ADMIN", "Anita Sharma", "admin@ams.local", "9876500001"),
        "staff1": ("staff123", "STAFF", "Vikram Rao", "vikram.rao@ams.local", "9876500002"),
        "staff2": ("staff123", "STAFF", "Meera Iyer", "meera.iyer@ams.local", "9876500003"),
        "priya":  ("pass1234", "PASSENGER", "Priya Verma", "priya.verma@mail.com", "9123456780"),
        "rahul":  ("pass1234", "PASSENGER", "Rahul Mehta", "rahul.mehta@mail.com", "9123456781"),
        "sneha":  ("pass1234", "PASSENGER", "Sneha Kulkarni", "sneha.k@mail.com", "9123456782"),
    }
    ids = {u: _insert_user(conn, u, *data, now) for u, data in users.items()}

    # (flight_no, airline, origin, dest, dep offset, duration min, gate, rows, fare, status)
    flights = [
        ("AI202",  "Air India",       "DEL", "BOM", timedelta(hours=3),           130, "A3", 20, 5400, "SCHEDULED"),
        ("6E5021", "IndiGo",          "BLR", "DEL", timedelta(days=1, hours=2),   165, "B7", 30, 6200, "SCHEDULED"),
        ("UK811",  "Vistara",         "BOM", "BLR", timedelta(days=2, hours=6),   100, "C2", 25, 4800, "SCHEDULED"),
        ("SG134",  "SpiceJet",        "DEL", "GOI", timedelta(hours=5),           150, "A5", 18, 5100, "DELAYED"),
        ("AI505",  "Air India",       "MAA", "CCU", timedelta(days=3, hours=1),   140, "D4", 22, 5900, "SCHEDULED"),
        ("QP1302", "Akasa Air",       "BOM", "DEL", timedelta(minutes=30),        125, "B1", 20, 5600, "BOARDING"),
        ("IX345",  "Air India Express", "CCU", "DEL", timedelta(days=1, hours=5), 140, None, 20, 4500, "CANCELLED"),
        ("6E2140", "IndiGo",          "DEL", "BLR", timedelta(days=1, hours=8),   170, "A3", 30, 6900, "SCHEDULED"),
    ]
    fid = {}
    for no, airline, o, d, off, dur, gate, rows, fare, status in flights:
        dep = base + off
        cur = conn.execute(
            "INSERT INTO flights (flight_no, airline, origin, destination, departure, arrival,"
            " gate, rows, fare, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (no, airline, o, d, fmt_dt(dep), fmt_dt(dep + timedelta(minutes=dur)), gate, rows, fare, status))
        fid[no] = cur.lastrowid

    # (pnr, user, flight, seat, status, boarding_seq)
    bookings = [
        ("K7Q2MA", "priya", "AI202",  "4A",  "BOOKED", None),
        ("R4T9XB", "rahul", "AI202",  "4B",  "CHECKED_IN", 1),
        ("M3J8LC", "sneha", "AI202",  "10F", "BOOKED", None),
        ("P9W1ZD", "priya", "6E5021", "12C", "BOOKED", None),
        ("H2N6YE", "rahul", "UK811",  "7D",  "BOOKED", None),
        ("T5V3QF", "sneha", "QP1302", "3C",  "BOOKED", None),
        ("C8L4KG", "priya", "IX345",  "5A",  "CANCELLED", None),
        ("B6D7RH", "sneha", "SG134",  "2E",  "BOOKED", None),
    ]
    fares = {f[0]: f[8] for f in flights}
    bid = {}
    for pnr, user, flight, seat, status, seq in bookings:
        checked = fmt_dt(now - timedelta(minutes=20)) if status == "CHECKED_IN" else None
        cur = conn.execute(
            "INSERT INTO bookings (pnr, user_id, flight_id, seat, fare, status, booked_at,"
            " checked_in_at, boarding_seq) VALUES (?,?,?,?,?,?,?,?,?)",
            (pnr, ids[user], fid[flight], seat, fares[flight], status,
             fmt_dt(now - timedelta(days=4)), checked, seq))
        bid[pnr] = cur.lastrowid

    # Sample payments: every live sample booking is paid; the booking on the cancelled flight was refunded in full.
    from .payments_core import fare_breakdown, record_payment, refund_booking
    sample_pay = {"K7Q2MA": ("UPI", "pr***@okaxis"), "R4T9XB": ("CARD", "VISA XXXX 4242"),
                  "M3J8LC": ("CARD", "MASTERCARD XXXX 4444"), "P9W1ZD": ("UPI", "pr***@oksbi"),
                  "H2N6YE": ("NETBANKING", "HDFC Bank"), "T5V3QF": ("CARD", "VISA XXXX 1881"),
                  "C8L4KG": ("UPI", "pr***@okaxis"), "B6D7RH": ("UPI", "sn***@ybl")}
    for pnr, _user, flight_no, *_rest in bookings:
        method, instrument = sample_pay[pnr]
        record_payment(conn, bid[pnr], method, instrument, fare_breakdown(fares[flight_no]), None,
                       now - timedelta(days=4))
    refund_booking(conn, bid["C8L4KG"], now - timedelta(days=1), True, "Flight cancelled by the airline")

    for weight, status in ((18.5, "LOADED"), (6.0, "CHECKED_IN")):
        cur = conn.execute(
            "INSERT INTO baggage (booking_id, weight_kg, status, updated_at) VALUES (?,?,?,?)",
            (bid["R4T9XB"], weight, status, fmt_dt(now)))
        conn.execute("UPDATE baggage SET tag_no = ? WHERE bag_id = ?",
                     (f"AMS{cur.lastrowid:06d}", cur.lastrowid))
    conn.commit()


def create_database(path: Optional[str] = None, reset: bool = False,
                    now: Optional[datetime] = None) -> sqlite3.Connection:
    """Create (or reset) the database file and seed it when it is empty."""
    path = path or DB_PATH
    if reset and path != ":memory:" and os.path.exists(path):
        os.remove(path)
    conn = connect(path)
    init_schema(conn)
    if is_empty(conn):
        seed_sample_data(conn, now)
    return conn
