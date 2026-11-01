"""Default domestic network: 21 Indian airports and 66 routes with realistic daily frequencies.

The timetable is SYNTHETIC. It is shaped like a real domestic schedule (several departures a day on the
busy metro routes, fewer on thin ones, a return flight for every outbound) but it is not any airline's
actual timetable. Flight numbers are paired like real ones: outbound n, return n+1.
"""
from typing import Dict, List

AIRPORTS: Dict[str, str] = {
    "DEL": "Delhi", "BOM": "Mumbai", "BLR": "Bengaluru", "MAA": "Chennai", "CCU": "Kolkata",
    "HYD": "Hyderabad", "AMD": "Ahmedabad", "PNQ": "Pune", "GOI": "Goa", "JAI": "Jaipur",
    "LKO": "Lucknow", "COK": "Kochi", "TRV": "Thiruvananthapuram", "PAT": "Patna", "GAU": "Guwahati",
    "IXC": "Chandigarh", "SXR": "Srinagar", "BBI": "Bhubaneswar", "IDR": "Indore", "NAG": "Nagpur",
    "IXE": "Mangalore",
}

METROS = {"DEL", "BOM", "BLR", "MAA", "CCU", "HYD"}

# (airport A, airport B, flying time in minutes)
ROUTES = [
    ("DEL", "BOM", 130), ("DEL", "BLR", 170), ("DEL", "MAA", 175), ("DEL", "CCU", 135), ("DEL", "HYD", 140),
    ("BOM", "BLR", 100), ("BOM", "MAA", 115), ("BOM", "CCU", 165), ("BOM", "HYD", 85), ("BLR", "MAA", 65),
    ("BLR", "HYD", 80), ("BLR", "CCU", 160), ("MAA", "HYD", 80), ("MAA", "CCU", 140), ("HYD", "CCU", 130),
    ("DEL", "AMD", 100), ("DEL", "PNQ", 125), ("DEL", "GOI", 150), ("DEL", "JAI", 60), ("DEL", "LKO", 65),
    ("DEL", "PAT", 100), ("DEL", "GAU", 150), ("DEL", "IXC", 55), ("DEL", "SXR", 95), ("DEL", "BBI", 130),
    ("DEL", "IDR", 90), ("DEL", "NAG", 105), ("DEL", "COK", 190),
    ("BOM", "AMD", 80), ("BOM", "PNQ", 50), ("BOM", "GOI", 70), ("BOM", "JAI", 120), ("BOM", "LKO", 135),
    ("BOM", "COK", 110), ("BOM", "TRV", 120), ("BOM", "IDR", 85), ("BOM", "NAG", 90), ("BOM", "BBI", 140),
    ("BLR", "GOI", 80), ("BLR", "PNQ", 95), ("BLR", "COK", 70), ("BLR", "TRV", 85), ("BLR", "AMD", 120),
    ("BLR", "BBI", 125), ("BLR", "NAG", 115),
    ("HYD", "GOI", 85), ("HYD", "PNQ", 80), ("HYD", "COK", 95), ("HYD", "TRV", 110), ("HYD", "AMD", 105),
    ("HYD", "BBI", 85), ("HYD", "NAG", 70),
    ("MAA", "COK", 70), ("MAA", "TRV", 75),
    ("CCU", "GAU", 75), ("CCU", "PAT", 75), ("CCU", "BBI", 65), ("CCU", "LKO", 120),
    ("JAI", "AMD", 70), ("AMD", "PNQ", 85),
    # Mangalore (added later; new routes go at the END so existing flight numbers never change)
    ("IXE", "BOM", 85), ("IXE", "BLR", 55), ("IXE", "DEL", 195), ("IXE", "HYD", 100), ("IXE", "MAA", 95),
    ("IXE", "COK", 45),
]

# (airline, IATA code, first flight number)
AIRLINES = [("IndiGo", "6E", 6001), ("Air India", "AI", 2401), ("Akasa Air", "QP", 1101), ("SpiceJet", "SG", 8001)]

# departure slots (hour, minute) for 1..5 daily frequencies
TIME_BANK = {
    1: [(8, 30)],
    2: [(7, 5), (18, 40)],
    3: [(6, 40), (12, 55), (19, 15)],
    4: [(6, 10), (10, 35), (15, 20), (20, 0)],
    5: [(5, 50), (8, 45), (12, 30), (16, 15), (20, 25)],
}


def frequency(a: str, b: str) -> int:
    """Daily departures in each direction."""
    if a in METROS and b in METROS:
        return 4
    if a in METROS or b in METROS:
        return 3
    return 2


def _seed(*codes: str) -> int:
    return sum(ord(c) for code in codes for c in code)


def build_default_templates() -> List[dict]:
    """Return template dicts (flight_no, airline, origin, destination, dep_time, duration_min, days, rows,
    base_fare). Deterministic: the same call always gives the same network."""
    next_no = {code: first for _name, code, first in AIRLINES}
    out: List[dict] = []
    for idx, (a, b, duration) in enumerate(ROUTES):
        n = frequency(a, b)
        offset = (_seed(a, b) % 24) * 5                      # staggers routes (0-115 min) so departures spread out
        factor = 0.92 + (_seed(a, b) % 9) * 0.02             # some routes are pricier than others
        base_fare = int(round((1800 + duration * 18) * factor / 50.0)) * 50
        rows = 25 if duration <= 90 else 30 if duration <= 150 else 35
        for k, (hour, minute) in enumerate(TIME_BANK[n]):
            airline, code, _first = AIRLINES[(idx + k) % len(AIRLINES)]
            outbound = next_no[code]
            next_no[code] += 2
            for step, (origin, dest) in enumerate(((a, b), (b, a))):
                total = hour * 60 + minute + offset + step * 25
                out.append(dict(flight_no=f"{code}{outbound + step}", airline=airline, origin=origin,
                                destination=dest, dep_time=f"{total // 60 % 24:02d}:{total % 60:02d}",
                                duration_min=duration, days="1234567", rows=rows, base_fare=base_fare))
    return out
