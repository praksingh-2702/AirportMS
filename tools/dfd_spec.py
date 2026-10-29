"""Single source of truth for the Structured Analysis (DFD) model.

Every DFD level, the balancing check and the data dictionary are generated from
these definitions, so names stay identical across all diagrams.
"""

ENTITIES = {"PAX": "Passenger", "STF": "Check-in Staff", "ADM": "Administrator"}

STORES = {"D1": "Users", "D2": "Flights", "D3": "Bookings", "D4": "Baggage"}

# ---------------- Context diagram (Level 0) ----------------
# (source, target, [labels])  - "0" is the whole system
CONTEXT = [
    ("PAX", "0", ["Registration details", "Login credentials", "Search criteria",
                  "Booking request", "Cancellation request"]),
    ("0", "PAX", ["Registration confirmation", "Authentication result", "Flight list",
                  "Seat availability", "Booking confirmation", "Cancellation confirmation",
                  "Boarding pass"]),
    ("STF", "0", ["Login credentials", "PNR", "Bag details", "Bag status update"]),
    ("0", "STF", ["Authentication result", "Booking details", "Boarding pass", "Bag tag",
                  "Baggage summary"]),
    ("ADM", "0", ["Login credentials", "Flight details", "Gate assignment",
                  "Flight status change", "Flight cancellation", "Staff account details"]),
    ("0", "ADM", ["Authentication result", "Flight schedule", "Schedule confirmation",
                  "User list"]),
]

# ---------------- Level 1 ----------------
LEVEL1_PROCESSES = {
    "1.0": "Manage Users &\nAuthenticate",
    "2.0": "Schedule\nFlights",
    "3.0": "Search\nFlights",
    "4.0": "Book / Cancel\nTicket",
    "5.0": "Check In\nPassenger",
    "6.0": "Manage\nBaggage",
}

LEVEL1_FLOWS = [
    # 1.0 Manage Users & Authenticate
    ("PAX", "1.0", ["Registration details", "Login credentials"]),
    ("1.0", "PAX", ["Registration confirmation", "Authentication result"]),
    ("STF", "1.0", ["Login credentials"]),
    ("1.0", "STF", ["Authentication result"]),
    ("ADM", "1.0", ["Login credentials", "Staff account details"]),
    ("1.0", "ADM", ["Authentication result", "User list"]),
    ("1.0", "D1", ["User record"]),
    ("D1", "1.0", ["Stored credentials", "Existing usernames", "User record"]),
    # 2.0 Schedule Flights
    ("ADM", "2.0", ["Flight details", "Gate assignment", "Flight status change", "Flight cancellation"]),
    ("2.0", "ADM", ["Flight schedule", "Schedule confirmation"]),
    ("D2", "2.0", ["Flight record", "Gate schedule"]),
    ("2.0", "D2", ["Flight record"]),
    ("2.0", "D3", ["Booking status update"]),
    # 3.0 Search Flights
    ("PAX", "3.0", ["Search criteria"]),
    ("3.0", "PAX", ["Flight list"]),
    ("D2", "3.0", ["Flight record"]),
    ("D3", "3.0", ["Taken seats"]),
    # 4.0 Book / Cancel Ticket
    ("PAX", "4.0", ["Booking request", "Cancellation request"]),
    ("4.0", "PAX", ["Seat availability", "Booking confirmation", "Cancellation confirmation"]),
    ("D2", "4.0", ["Flight record"]),
    ("D3", "4.0", ["Taken seats", "Booking record", "Existing PNRs"]),
    ("4.0", "D3", ["Booking record"]),
    # 5.0 Check In Passenger
    ("STF", "5.0", ["PNR"]),
    ("5.0", "STF", ["Booking details", "Boarding pass"]),
    ("5.0", "PAX", ["Boarding pass"]),
    ("D3", "5.0", ["Booking record"]),
    ("D2", "5.0", ["Flight record"]),
    ("D1", "5.0", ["Passenger name"]),
    ("5.0", "D3", ["Check-in status"]),
    # 6.0 Manage Baggage
    ("STF", "6.0", ["Bag details", "Bag status update"]),
    ("6.0", "STF", ["Bag tag", "Baggage summary"]),
    ("D3", "6.0", ["Booking record"]),
    ("6.0", "D4", ["Bag record"]),
    ("D4", "6.0", ["Bag record"]),
]

# ---------------- Level 2 (one diagram per Level-1 process) ----------------
LEVEL2 = {
    "1.0": {
        "processes": {"1.1": "Register\nPassenger", "1.2": "Create Staff\nAccount",
                      "1.3": "Verify\nCredentials", "1.4": "List\nUsers"},
        "flows": [
            ("PAX", "1.1", ["Registration details"]),
            ("1.1", "PAX", ["Registration confirmation"]),
            ("D1", "1.1", ["Existing usernames"]),
            ("1.1", "D1", ["User record"]),
            ("ADM", "1.2", ["Staff account details"]),
            ("D1", "1.2", ["Existing usernames"]),
            ("1.2", "D1", ["User record"]),
            ("PAX", "1.3", ["Login credentials"]),
            ("STF", "1.3", ["Login credentials"]),
            ("ADM", "1.3", ["Login credentials"]),
            ("D1", "1.3", ["Stored credentials"]),
            ("1.3", "PAX", ["Authentication result"]),
            ("1.3", "STF", ["Authentication result"]),
            ("1.3", "ADM", ["Authentication result"]),
            ("D1", "1.4", ["User record"]),
            ("1.4", "ADM", ["User list"]),
        ],
    },
    "2.0": {
        "processes": {"2.1": "Validate\nFlight Details", "2.2": "Check Gate\nAvailability",
                      "2.3": "Save Flight", "2.4": "Assign\nGate",
                      "2.5": "Change Flight\nStatus", "2.6": "Cancel\nFlight"},
        "flows": [
            ("ADM", "2.1", ["Flight details"]),
            ("D2", "2.1", ["Flight record"]),
            ("2.1", "2.2", ["Valid flight details"]),
            ("D2", "2.2", ["Gate schedule"]),
            ("2.2", "2.3", ["Gate-checked flight"]),
            ("2.3", "D2", ["Flight record"]),
            ("2.3", "ADM", ["Schedule confirmation"]),
            ("ADM", "2.4", ["Gate assignment"]),
            ("2.4", "2.2", ["Gate request"]),
            ("2.2", "2.4", ["Gate free"]),
            ("2.4", "D2", ["Flight record"]),
            ("ADM", "2.5", ["Flight status change"]),
            ("D2", "2.5", ["Flight record"]),
            ("2.5", "D2", ["Flight record"]),
            ("2.5", "2.6", ["Cancel request"]),
            ("ADM", "2.6", ["Flight cancellation"]),
            ("2.6", "D2", ["Flight record"]),
            ("2.6", "D3", ["Booking status update"]),
            ("D2", "2.3", ["Flight record"]),
            ("2.3", "ADM", ["Flight schedule"]),
        ],
    },
    "3.0": {
        "processes": {"3.1": "Validate\nSearch Criteria", "3.2": "Filter\nBookable Flights",
                      "3.3": "Compute\nSeats Left"},
        "flows": [
            ("PAX", "3.1", ["Search criteria"]),
            ("3.1", "3.2", ["Valid criteria"]),
            ("D2", "3.2", ["Flight record"]),
            ("3.2", "3.3", ["Matching flights"]),
            ("D3", "3.3", ["Taken seats"]),
            ("3.3", "PAX", ["Flight list"]),
        ],
    },
    "4.0": {
        "processes": {"4.1": "Show\nSeat Map", "4.2": "Validate\nBooking", "4.3": "Generate\nPNR",
                      "4.4": "Record\nBooking", "4.5": "Cancel\nBooking"},
        "flows": [
            ("PAX", "4.1", ["Booking request"]),
            ("D2", "4.1", ["Flight record"]),
            ("D3", "4.1", ["Taken seats"]),
            ("4.1", "PAX", ["Seat availability"]),
            ("4.1", "4.2", ["Selected seat"]),
            ("D3", "4.2", ["Taken seats"]),
            ("4.2", "4.3", ["Valid booking"]),
            ("D3", "4.3", ["Existing PNRs"]),
            ("4.3", "4.4", ["Valid booking", "PNR"]),
            ("4.4", "D3", ["Booking record"]),
            ("4.4", "PAX", ["Booking confirmation"]),
            ("PAX", "4.5", ["Cancellation request"]),
            ("D3", "4.5", ["Booking record"]),
            ("4.5", "D3", ["Booking record"]),
            ("4.5", "PAX", ["Cancellation confirmation"]),
        ],
    },
    "5.0": {
        "processes": {"5.1": "Retrieve\nBooking", "5.2": "Verify Check-in\nEligibility",
                      "5.3": "Assign\nBoarding Seq.", "5.4": "Generate\nBoarding Pass"},
        "flows": [
            ("STF", "5.1", ["PNR"]),
            ("D3", "5.1", ["Booking record"]),
            ("D2", "5.1", ["Flight record"]),
            ("D1", "5.1", ["Passenger name"]),
            ("5.1", "STF", ["Booking details"]),
            ("5.1", "5.2", ["Booking details"]),
            ("5.2", "5.3", ["Eligible booking"]),
            ("D3", "5.3", ["Booking record"]),
            ("5.3", "D3", ["Check-in status"]),
            ("5.3", "5.4", ["Boarding sequence"]),
            ("5.4", "STF", ["Boarding pass"]),
            ("5.4", "PAX", ["Boarding pass"]),
        ],
    },
    "6.0": {
        "processes": {"6.1": "Validate\nBag", "6.2": "Generate\nBag Tag", "6.3": "Compute\nExcess Fee",
                      "6.4": "Update\nBag Status"},
        "flows": [
            ("STF", "6.1", ["Bag details"]),
            ("D3", "6.1", ["Booking record"]),
            ("D4", "6.1", ["Bag record"]),
            ("6.1", "6.2", ["Valid bag"]),
            ("6.2", "D4", ["Bag record"]),
            ("6.2", "STF", ["Bag tag"]),
            ("D4", "6.3", ["Bag record"]),
            ("6.3", "STF", ["Baggage summary"]),
            ("STF", "6.4", ["Bag status update"]),
            ("D4", "6.4", ["Bag record"]),
            ("6.4", "D4", ["Bag record"]),
        ],
    },
}

# ---------------- Level 3 (atomic decomposition of 5.2) ----------------
LEVEL3 = {
    "5.2": {
        "processes": {"5.2.1": "Check\nBooking Status", "5.2.2": "Check\nFlight Status",
                      "5.2.3": "Check Opening\nTime (48 h)", "5.2.4": "Check Closing\nTime (45 min)"},
        "flows": [
            ("5.1", "5.2.1", ["Booking details"]),
            ("5.2.1", "5.2.2", ["Active booking"]),
            ("5.2.2", "5.2.3", ["Operating flight"]),
            ("5.2.3", "5.2.4", ["Opened booking"]),
            ("5.2.4", "5.3", ["Eligible booking"]),
            ("5.2.1", "STF", ["Rejection reason"]),
            ("5.2.2", "STF", ["Rejection reason"]),
            ("5.2.3", "STF", ["Rejection reason"]),
            ("5.2.4", "STF", ["Rejection reason"]),
        ],
        "external_processes": {"5.1": "Retrieve\nBooking", "5.3": "Assign\nBoarding Seq."},
    },
}
