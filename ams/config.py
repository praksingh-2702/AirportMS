"""Central configuration and business-rule constants for the Airport Management System.

Every limit used by the validators and services is defined here, so a rule
(e.g. the free baggage allowance) is changed in exactly one place.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("AMS_DB_PATH", os.path.join(BASE_DIR, "data", "airport.db"))

DATETIME_FMT = "%Y-%m-%d %H:%M"   # format used in the database and in the GUI
DATE_FMT = "%Y-%m-%d"

# Aircraft seat layout: rows x columns (A-F), aisle between C and D
SEAT_COLUMNS = "ABCDEF"
MIN_ROWS = 1
MAX_ROWS = 40

# Flight scheduling rules
GATE_BUFFER_MINUTES = 60      # two active flights at one gate must depart >= 60 min apart
MAX_FLIGHT_HOURS = 20         # longest allowed flight duration
MIN_FARE = 500                # INR
MAX_FARE = 200_000            # INR

# Check-in rules
CHECKIN_OPENS_HOURS = 48      # check-in opens 48 h before departure
CHECKIN_CLOSES_MINUTES = 45   # and closes 45 min before departure
BOARDING_BEFORE_MINUTES = 30  # boarding time printed on the boarding pass

# Baggage rules
MAX_BAGS_PER_BOOKING = 3
MAX_BAG_WEIGHT_KG = 32.0      # heavier bags must go as cargo
FREE_BAGGAGE_KG = 15.0        # free allowance per passenger (economy)
EXCESS_RATE_PER_KG = 500      # INR per started kg above the allowance

# Password hashing
PBKDF2_ITERATIONS = 100_000
