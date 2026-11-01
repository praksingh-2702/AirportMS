"""Data dictionary for every data flow and data store in the DFDs (Rajib Mall notation).

Names are written in the textbook's lower-case hyphenated form (valid-data) in the JSON that the report uses.
Notation:  =  is composed of   +  and   [a | b]  either a or b   {x}  zero or more x
           {x}n  up to n of x   (x)  optional x   "..."  literal
Running this file checks that every flow name used in tools/dfd_spec.py is defined
and writes docs/data_dictionary.json for the report generator.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookstyle as B  # noqa: E402
import dfd_spec as S  # noqa: E402

# name: (composition, description)
COMPOSITE = {
    # ---- data stores
    "D1 Users": ("{user_id + username + password_hash + salt + role + full_name + email + phone + created_at}",
                 "Data store (table users). One record per account."),
    "D2 Flights": ("{flight_id + flight_no + airline + origin + destination + departure + arrival + (gate) + rows + fare + flight_status}",
                   "Data store (table flights). UNIQUE(flight_no, departure)."),
    "D3 Bookings": ("{booking_id + pnr + user_id + flight_id + seat + fare + booking_status + booked_at + (checked_in_at) + (boarding_seq)}",
                    "Data store (table bookings). A seat is unique per flight among non-cancelled bookings."),
    "D4 Baggage": ("{bag_id + booking_id + tag_no + weight_kg + bag_status + updated_at}",
                   "Data store (table baggage)."),
    "D5 Recurring Services": ("{template_id + flight_no + airline + origin + destination + dep_time + duration_min + days + rows + base_fare + active}",
                              "Data store (table flight_templates). One row per daily service, e.g. 6E6001 DEL-BOM 06:25."),
    "D6 Payments": ("{payment_id + booking_id + invoice_no + method + instrument + amount + base_fare + airport_fee + gst + convenience_fee + payment_status + reference + paid_at + refund_amount + (refund_reason) + (refunded_at)}",
                    "Data store (table payments). At most one payment per booking. Card number and CVV are never stored."),
    # ---- flows
    "Registration details": ("username + password + confirm_password + full_name + email + phone",
                             "Entered by a new passenger on the registration dialog."),
    "Registration confirmation": ("\"Account created\" + username", "Shown after successful registration."),
    "Login credentials": ("username + password", "Entered on the login screen by any user."),
    "Authentication result": ("[user + role | error_message]", "User object (opens the role dashboard) or 'Invalid username or password.'"),
    "Stored credentials": ("username + password_hash + salt + role", "Read from D1 to verify a login."),
    "Existing usernames": ("{username}", "Used to reject a duplicate username."),
    "User record": ("user_id + username + password_hash + salt + role + full_name + email + phone + created_at", "One row of D1."),
    "User list": ("{username + role + full_name + email + phone}", "Shown to the administrator."),
    "Staff account details": ("username + password + full_name + email + phone + role", "role = [\"STAFF\" | \"ADMIN\"]."),
    "Flight details": ("flight_no + airline + origin + destination + departure + arrival + rows + fare + (gate)",
                       "Entered by the administrator to add or update a flight."),
    "Valid flight details": ("Flight details", "Flight details that passed all format and schedule checks."),
    "Gate schedule": ("{gate + departure + flight_status}", "Active flights at a gate, used for the 60-minute conflict check."),
    "Gate-checked flight": ("Valid flight details", "Flight whose gate (if any) has no conflict."),
    "Gate assignment": ("flight_id + gate", "Administrator assigns or changes the gate."),
    "Gate request": ("gate + departure + flight_id", "Sent to 0.2.2 to check a gate."),
    "Gate free": ("[\"true\" | \"false\"]", "Result of the gate availability check."),
    "Flight record": ("flight_id + flight_no + airline + origin + destination + departure + arrival + (gate) + rows + fare + flight_status",
                      "One row of D2."),
    "Flight schedule": ("{flight_no + airline + origin + destination + departure + arrival + gate + booked_count + capacity + fare + flight_status}",
                        "Schedule table shown on the Flights tab."),
    "Schedule confirmation": ("message", "e.g. 'Flight AI777 added.'"),
    "Flight status change": ("flight_id + new_status", "new_status = [SCHEDULED | DELAYED | BOARDING | DEPARTED]."),
    "Flight cancellation": ("flight_id", "Request to cancel a flight (cascades to bookings)."),
    "Cancel request": ("flight_id", "Raised by 0.2.5 when the new status is CANCELLED."),
    "Booking status update": ("flight_id + \"CANCELLED\"", "All active bookings of a cancelled flight become CANCELLED."),
    "Search criteria": ("(origin) + (destination) + (travel_date)", "Blank fields match all flights."),
    "Valid criteria": ("Search criteria", "Criteria in valid IATA / date format."),
    "Matching flights": ("{Flight record}", "Bookable (SCHEDULED/DELAYED) future flights matching the criteria."),
    "Flight list": ("{flight_no + airline + origin + destination + departure + arrival + fare + seats_left + flight_status}",
                    "Search result shown to the passenger."),
    "Taken seats": ("{seat}", "Seats held by non-cancelled bookings of a flight."),
    "Booking request": ("flight_id + user_id", "Passenger selects a flight and opens the seat map."),
    "Seat availability": ("{seat + [\"free\" | \"taken\"]}", "Seat map; taken seats are disabled."),
    "Selected seat": ("seat", "Seat clicked on the seat map."),
    "Valid booking": ("user_id + flight_id + seat + fare", "Booking request that passed seat, status and duplicate checks."),
    "Existing PNRs": ("{pnr}", "Used to guarantee a unique PNR."),
    "PNR": ("6{alphanumeric}6", "Booking reference, e.g. K7Q2MA (letters I, O and digits 0, 1 are not generated)."),
    "Booking record": ("booking_id + pnr + user_id + flight_id + seat + fare + booking_status + booked_at + (checked_in_at) + (boarding_seq)",
                       "One row of D3."),
    "Booking confirmation": ("pnr + seat", "Shown after a successful booking."),
    "Cancellation request": ("booking_id", "Passenger (own booking) or administrator."),
    "Cancellation confirmation": ("message", "e.g. 'Booking P9W1ZD cancelled.'"),
    "Passenger name": ("full_name", "Read from D1 for the boarding pass."),
    "Booking details": ("Booking record + passenger_name + flight_no + origin + destination + departure + (gate) + flight_status",
                        "Booking joined with its passenger and flight (class BookingDetails)."),
    "Active booking": ("Booking details", "Booking whose status is BOOKED."),
    "Operating flight": ("Booking details", "Active booking whose flight is not CANCELLED or DEPARTED."),
    "Opened booking": ("Booking details", "Check-in has opened (now >= departure - 48 h)."),
    "Eligible booking": ("Booking details", "Check-in still open (now <= departure - 45 min)."),
    "Rejection reason": ("message", "Why check-in was refused."),
    "Boarding sequence": ("integer", "MAX(boarding_seq of the flight) + 1."),
    "Check-in status": ("booking_id + \"CHECKED_IN\" + checked_in_at + boarding_seq", "Update written to D3."),
    "Boarding pass": ("pnr + passenger_name + flight_no + origin + destination + departure + boarding_time + (gate) + seat + boarding_seq",
                      "boarding_time = departure - 30 min (class BoardingPass)."),
    "Bag details": ("pnr + weight_kg", "Entered at the check-in counter."),
    "Valid bag": ("booking_id + weight_kg", "0 < weight_kg <= 32 and fewer than 3 bags on the booking."),
    "Bag record": ("bag_id + booking_id + tag_no + weight_kg + bag_status + updated_at", "One row of D4."),
    "Bag tag": ("\"AMS\" + 6{digit}6", "e.g. AMS000003; derived from bag_id."),
    "Baggage summary": ("bag_count + total_weight_kg + excess_fee", "excess_fee = 500 x ceil(total - 15) if total > 15 else 0."),
    "Bag status update": ("bag_id + new_bag_status", "new_bag_status = [LOADED | UNLOADED | CLAIMED | MISHANDLED]."),
    # ---- recurring schedule
    "Service details": ("flight_no + airline + origin + destination + dep_time + duration_min + days + rows + base_fare",
                        "Entered by the administrator for one daily service; days = [\"Daily\" | \"Weekdays\" | {weekday}]."),
    "Valid service": ("Service details", "Service details that passed the format checks and are not a duplicate."),
    "Service record": ("template_id + flight_no + airline + origin + destination + dep_time + duration_min + days + rows + base_fare + active",
                       "One row of D5."),
    "Service list": ("{Service record}", "Table of recurring services on the Schedule tab."),
    "Generation request": ("days", "Number of days (1-90) for which dated flights are to be created."),
    "Existing flights": ("{flight_no + departure + flight_status}", "Used so that a generated flight is never created twice, or re-created after a cancellation."),
    "Due services": ("{Service record + departure}", "Active services that run on a given date and depart in the future."),
    "Priced flights": ("{Due services + fare}", "fare = base_fare x time-of-day, weekday and days-ahead factors, kept within 500..200000."),
    "Gate-assigned flights": ("{Priced flights + (gate)}", "A free gate is chosen so that no two active flights at one gate depart within 60 minutes."),
    "Generation summary": ("created_count + skipped_count + last_day", "e.g. 'Created 1,200 flight(s); 30 already existed.'"),
    # ---- payments and refunds
    "Payment request": ("booking_id + base_fare", "Sent by 0.4 when a seat has been reserved and must be paid for."),
    "Fare breakdown": ("base_fare + airport_fee + gst + convenience_fee + total", "total = base_fare + 200 + 5% of (base_fare + 200) + 150."),
    "Amount due": ("total", "Passed on to be authorised."),
    "Payment details": ("method + [card_number + expiry + cvv + name_on_card | upi_id | bank]", "method = [\"CARD\" | \"UPI\" | \"NETBANKING\"]."),
    "Valid payment details": ("Payment details", "Details that passed the Luhn check, expiry, CVV, UPI-id and bank checks."),
    "Authorization request": ("method + details + amount", "Sent to the (simulated) payment gateway."),
    "Authorization result": ("[approved + reference | declined + message]", "e.g. 'Card declined by the issuing bank.'"),
    "Approved payment": ("Valid payment details + reference", "Payment the gateway has approved."),
    "Payment result": ("[payment | message]", "payment on success; the bank's reason when declined."),
    "Payment record": ("payment_id + booking_id + invoice_no + method + instrument + amount + base_fare + airport_fee + gst + convenience_fee + payment_status + reference + paid_at + refund_amount + (refund_reason) + (refunded_at)",
                       "One row of D6."),
    "Payment receipt": ("invoice_no + passenger_name + pnr + flight_no + breakdown + instrument + reference + (refund)", "One-page PDF receipt."),
    "Cancellation notice": ("booking_id", "Sent by 0.4 when a passenger or administrator cancels a booking."),
    "Flight cancellation notice": ("flight_id", "Sent by 0.2 so that every paid booking on the flight is refunded in full."),
    "Refund amount": ("amount + charge + percent", "refund = amount - convenience_fee - charge; charge = percent of base_fare (10 / 25 / 50 / 100 by time to departure)."),
    "Refund confirmation": ("message", "e.g. 'Rs 5,170 refunded to UPI pr***@oksbi (demo).'"),
    "Revenue summary": ("total_paid - total_refunded", "Shown as a tile on the administrator's dashboard."),
    "Paid booking": ("Booking details", "Operating-flight booking that has a PAID payment."),
    "Boarding pass data": ("Boarding pass", "Input to the PDF writer."),
}

ELEMENTARY = [
    ("username", "3-20 chars: a-z, 0-9, _", "lower-cased"),
    ("password", "6-64 chars, >= 1 letter and >= 1 digit", "stored only as PBKDF2 hash + salt"),
    ("role", "[ADMIN | STAFF | PASSENGER]", "enum Role"),
    ("phone", "10 digits, first digit 6-9", "Indian mobile number"),
    ("flight_no", "2-char airline code (not both digits) + 1-4 digits", "e.g. AI202, 6E5021"),
    ("origin / destination", "3 uppercase letters (IATA)", "origin <> destination"),
    ("departure / arrival", "YYYY-MM-DD HH:MM", "departure in future; 0 < duration <= 20 h"),
    ("gate", "terminal A-D + number 1-20", "optional; e.g. B7"),
    ("rows", "integer 1-40", "6 seats (A-F) per row"),
    ("fare", "integer 500-200000 (INR)", ""),
    ("seat", "row (1..rows) + column [A|B|C|D|E|F]", "e.g. 12C"),
    ("flight_status", "[SCHEDULED | DELAYED | BOARDING | DEPARTED | CANCELLED]", "enum FlightStatus"),
    ("booking_status", "[BOOKED | CHECKED_IN | CANCELLED]", "enum BookingStatus"),
    ("weight_kg", "real, 0 < w <= 32, 1 decimal", ""),
    ("bag_status", "[CHECKED_IN | LOADED | UNLOADED | CLAIMED | MISHANDLED]", "enum BagStatus"),
    ("dep_time", "HH:MM, 24-hour", "departure time of a recurring service"),
    ("duration_min", "integer 20-1200", "flying time in minutes"),
    ("days", "ISO weekday digits 1-7 (1 = Monday)", "'Daily' = 1234567"),
    ("method", "[CARD | UPI | NETBANKING | LEGACY]", "LEGACY marks bookings made before payments existed"),
    ("card_number", "13-19 digits passing the Luhn check", "never stored; only 'VISA XXXX 1111' is kept"),
    ("expiry", "MM/YY, not in the past", "never stored"),
    ("cvv", "3 digits (4 for American Express)", "never stored"),
    ("upi_id", "name@bank", "stored masked, e.g. pr***@okaxis"),
    ("amount", "integer INR", "total = fare + airport fee + GST + convenience fee"),
    ("invoice_no", "INV-YYYYMMDD-nnnnn", "unique per payment"),
    ("payment_status", "[PAID | REFUNDED]", "enum PaymentStatus"),
]


def all_flow_names():
    names = set()
    for flows in [S.CONTEXT, S.LEVEL1_FLOWS] + [d["flows"] for d in S.LEVEL2.values()] + \
                 [d["flows"] for d in S.LEVEL3.values()]:
        for _, _, labels in flows:
            names.update(labels)
    return names


def hyphenate(entries):
    """Rewrite names, and references to other names inside compositions, in the book's hyphenated form."""
    names = sorted((k for k in entries if k[:2] not in ("D1", "D2", "D3", "D4", "D5", "D6")), key=len, reverse=True)

    def fix(text):
        for n in names:
            text = re.sub(r"(?<![A-Za-z_-])" + re.escape(n) + r"(?![A-Za-z_-])", B.hy(n), text)
        return text
    out = {}
    for k, (comp, desc) in entries.items():
        key = f"{k[:2]} {B.hy(k[3:])}" if k[:2] in ("D1", "D2", "D3", "D4", "D5", "D6") else B.hy(k)
        out[key] = (fix(comp), desc)
    return out


def main():
    missing = all_flow_names() - set(COMPOSITE)
    stores = {f"{k} {v}" for k, v in S.STORES.items()} - set(COMPOSITE)
    if missing or stores:
        sys.exit(f"Data dictionary incomplete: flows {sorted(missing)}, stores {sorted(stores)}")
    unused = set(COMPOSITE) - all_flow_names() - {f"{k} {v}" for k, v in S.STORES.items()}
    if unused:
        sys.exit(f"Entries not used in any DFD: {sorted(unused)}")
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "data_dictionary.json")
    entries = hyphenate(COMPOSITE)
    stores_first = sorted(entries, key=lambda k: (0, k) if k[:2] in ("D1", "D2", "D3", "D4", "D5", "D6") else (1, k))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"composite": [[k, *entries[k]] for k in stores_first], "elementary": ELEMENTARY}, fh, indent=1)
    print(f"Data dictionary OK: {len(COMPOSITE)} composite entries, {len(ELEMENTARY)} elementary items -> {out}")


if __name__ == "__main__":
    main()
