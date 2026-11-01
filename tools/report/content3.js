// Chapters 10-14 + appendices: implementation, testing, limitations, conclusion, traceability, setup
const fs = require("fs");
const path = require("path");
const L = require("./lib");
const { H1, H2, H3, P, Bullets, Code, Img, Tbl, setChapter, pySource } = L;
const REQUIREMENTS = require("./requirements");

// ---- real test results (from docs/test_results.txt, produced by `python -m unittest -v`)
const RESULTS_TXT = fs.readFileSync(path.join(L.ROOT, "docs", "test_results.txt"), "utf8");
const STATUS = {};
for (const m of RESULTS_TXT.matchAll(/test_([A-Z]{2}\d{2})\w*\s+\([^)]*\)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)/g)) {
  STATUS[m[1]] = m[2] === "ok" ? "Pass" : m[2].toUpperCase();
}
const NAMES = {};   // id -> {cls, scenario} from the verbose unittest output
for (const m of RESULTS_TXT.matchAll(/test_([A-Z]{2}\d{2})_(\w+)\s+\(tests\.\w+\.(\w+)\./g)) {
  NAMES[m[1]] = { cls: m[3].replace(/^Test/, ""), scenario: m[2].replace(/_/g, " ") };
}
const SUMMARY = (RESULTS_TXT.match(/Ran (\d+) tests? in ([\d.]+)s/) || []);
const FINAL = /\nOK\s*$/.test(RESULTS_TXT.trim() + "\n") || /\nOK\b/.test(RESULTS_TXT) ? "OK" : "FAILED";
const st = (id) => { if (!STATUS[id]) throw new Error(`No result for ${id} in test_results.txt`); return STATUS[id]; };

const COV = fs.readFileSync(path.join(L.ROOT, "docs", "coverage_report.txt"), "utf8").split("\n")
  .filter((l) => /^(ams\/|TOTAL)/.test(l)).map((l) => l.trim().split(/\s+/));

// rows [id, class, scenario, result] for one suite prefix (SG, BP, PY, ...), straight from the test run
const suiteRows = (prefix) => Object.keys(NAMES).filter((k) => k.startsWith(prefix)).sort()
  .map((k) => [k, NAMES[k].cls, NAMES[k].scenario, st(k)]);

const KEEP_SHOTS = ["00_login", "03_admin_flights", "06_admin_schedule", "09_passenger_search", "10_passenger_seat_map", "11_payment_window", "13_payment_success", "14_passenger_cancel_refund", "16_staff_checkin_boarding_pass", "19_boarding_pass_pdf", "20_receipt_pdf"];

function ch10() {
  setChapter(10);
  const shots = [
    ["00_login", "Login screen: animated sky, planes and runway lights; quick-fill buttons for the demo accounts"],
    ["01_login_error", "Wrong password: the same message is shown for an unknown user and a wrong password (NF4); the card shakes"],
    ["02_register", "Passenger registration dialog"],
    ["03_admin_flights", "Administrator - Flights tab: statistic tiles, date and search filters, 'Showing 300 of n flights', add/update form"],
    ["04_calendar", "Drop-down calendar of a date field: month arrows, month list, year box, Today and Clear (today outlined)"],
    ["05_admin_flight_validation_error", "Validation error when adding a flight with an invalid flight number"],
    ["06_admin_schedule", "Administrator - Schedule tab: recurring services (filtered to Mangalore, IXE), 'Generate flights', add a service"],
    ["07_admin_users", "Administrator - Users tab (create staff/admin accounts)"],
    ["08_admin_all_bookings", "Administrator - all bookings with the Payment column; cancelled and refunded bookings greyed out"],
    ["09_passenger_search", "Passenger - search Mangalore to Bengaluru on a chosen date; 'Your booking' column; own bookings below"],
    ["10_passenger_seat_map", "Passenger - seat map: taken seats disabled, selected seat green, Cancel button"],
    ["11_payment_window", "Payment window: fare breakdown, Card / UPI / Net banking, card number grouped as typed, demo notice"],
    ["12_payment_declined", "Declined card (4000 0000 0000 0002): the bank's reason is shown in the window and no booking is created"],
    ["13_payment_success", "Payment successful: PNR, seat, invoice number, gateway reference, receipt download"],
    ["14_passenger_cancel_refund", "Cancelling a booking: the dialog states the refund and what is kept (50% tier); the table then shows 'Refunded'"],
    ["15_staff_unpaid_refused", "Check-in staff - an unpaid booking shows 'UNPAID' and check-in is refused"],
    ["16_staff_checkin_boarding_pass", "Check-in staff - boarding pass after check-in (Download boarding pass (PDF) enabled); two bags tagged, 21.5 kg, excess fee Rs 3500"],
    ["17_staff_bag_weight_error", "Bag heavier than 32 kg rejected with an explanatory message"],
    ["18_passenger_boarding_pass", "Passenger - own boarding passes with a preview and Download PDF"],
    ["19_boarding_pass_pdf", "The downloaded boarding pass (PDF): route, details, perforated stub and Code 128 barcode of the PNR"],
    ["20_receipt_pdf", "The downloaded payment receipt (PDF): itemised charges, masked payment method, invoice number"],
  ];
  return [
    H1("10. Implementation and Working GUI"),
    H2("10.1 Architecture"),
    P("The program has three layers. Dependencies point only downwards, which is what keeps coupling low (Chapter 6)."),
    ...Tbl(["Layer", "Package / files", "Responsibility"], [
      ["Presentation (boundary)", "ams/gui/: app.py, login_view.py, flight_view.py, schedule_view.py, booking_view.py, payment_dialog.py, checkin_view.py, users_view.py, widgets.py", "Windows, animated tabs, forms, tables, seat map, payment window, drop-down calendar; shows errors in dialogs."],
      ["Service (control)", "ams/services/: auth_service.py, flight_service.py, schedule_service.py, booking_service.py, payment_service.py, checkin_service.py", "All business rules and role checks."],
      ["Utility & data", "ams/: models.py, validators.py, access.py, security.py, errors.py, config.py, database.py, network.py, payments_core.py, gateway.py, boarding_pdf.py, receipt_pdf.py", "Entities, validation, hashing, constants, schema and sample data, built-in timetable, fare/refund arithmetic, simulated gateway, PDF writers."],
      ["Entry points", "run.py, init_db.py, run.bat", "Start the GUI; create/reset the database."],
      ["Tests", "tests/: test_blackbox.py, test_whitebox.py, test_whitebox_payments.py, test_services.py, test_schedule.py, test_boarding_pdf.py, test_payments.py, helpers.py", SUMMARY[1] + " automated tests on an in-memory database with a fixed clock."],
      ["Diagram and report tools", "tools/: bookstyle.py, bookdraw.py, make_dfds.py, make_design_diagrams.py, make_usecase.py, make_uml.py, data_dictionary.py, capture_screenshots.py, report/", "Regenerate every diagram, the data dictionary, the screenshots and this report."],
    ], [1.8, 4.4, 2.8], { caption: "Source code organisation" }),
    H2("10.2 Important Algorithms and Mechanisms"),
    ...Bullets([
      "**Seat uniqueness:** checked in `book_ticket` and also guaranteed by the partial unique index `ux_active_seat ON bookings(flight_id, seat) WHERE status <> 'CANCELLED'`; if two bookings race for one seat the database rejects the second and the user sees 'Seat ... was just taken.'",
      "**Gate clash check:** `is_gate_available` compares the departure time with every other active flight at the same gate and rejects a gap below 60 minutes (white-box tested, Section 11.3).",
      "**PNR generation:** 6 random characters from an alphabet without I, O, 0, 1 (`secrets` module), retried until unused.",
      "**Check-in window and boarding sequence:** see the axiomatic specification in Section 5.2.",
      "**Excess-baggage fee:** Rs 500 per started kilogram above 15 kg (`compute_excess_fee`).",
      "**State machines:** flight and bag statuses change only through the transition tables shown in Section 9.5.",
      "**Recurring schedule:** a service is a row of D5; `generate_flights` makes one flight per service per running day, skipping dates that already have the flight number (cancelled ones too, so the administrator's cancellation is respected). All flights of a run are inserted in one batch (about 11,000 flights in 0.2 s).",
      "**Dynamic fare:** `dynamic_fare(base, departure, now)` multiplies the base fare by 1.12 in the 06-10 and 17-21 h peaks, 0.88 for departures at 22-05 h, 1.07 on Fridays and Sundays, and by 1.25 / 1.10 / 0.93 for departures under 3 days, under 8 days or over 21 days ahead; the result is clamped to Rs 500-2,00,000.",
      "**Gate planning:** an in-memory planner keeps a sorted list of departure times per gate and uses binary search to find a gate whose neighbours are at least 60 minutes away, so thousands of flights are planned without a query each.",
      "**Atomic book-and-pay:** `book_and_pay` validates the payment details, reserves the seat with `book_ticket`, asks the gateway, and records the payment; if the gateway declines the reserved booking is deleted, so a decline never leaves a booking or a held seat.",
      "**Fare, refund and receipt:** total = base fare + Rs 200 + 5% GST on (fare + 200) + Rs 150; refund = amount - convenience fee - a charge of 10 / 25 / 50 / 100% of the base fare by time to departure (full refund when the airline cancels). Card numbers are checked with the Luhn algorithm; only a masked label is stored.",
      "**PDF without a library:** `boarding_pdf.py` writes the PDF objects, the cross-reference table and the page content itself, with Helvetica font metrics for alignment and a Code 128 (subset B) encoder for the barcode. The 106 bar patterns were cross-checked against an independent encoder, and a software scanner read the printed codes at 144-288 dpi.",
      "**Start-up upgrade:** every start creates missing tables, tops the schedule up to 30 days, adds services that are new in the built-in network (for example Mangalore) without touching existing ones, and, once, marks bookings made before payments existed as paid (method LEGACY) so that they can still be checked in.",
      "**Passwords:** PBKDF2-HMAC-SHA256, 100,000 iterations, random 16-byte salt; compared with `hmac.compare_digest`.",
      "**Sample data relative to the current time:** `seed_sample_data` places flights 30 minutes to 3 days ahead of the moment the database is created, so the check-in window rules can always be demonstrated (`python run.py --reset` before a demo).",
    ]),
    H2("10.3 Input Validation and Error Messages"),
    ...Tbl(["Field", "Rule", "Message shown on error"], [
      ["Flight no.", "2-char airline code (not both digits) + 1-4 digits", "Flight number must be a 2-character airline code + 1-4 digits, e.g. AI202."],
      ["Airport code", "3 letters", "Origin must be a 3-letter IATA code, e.g. DEL."],
      ["Date/time", "YYYY-MM-DD HH:MM, future, arrival after departure, <= 20 h", "Departure must be in YYYY-MM-DD HH:MM format, e.g. 2026-11-05 14:30. / Departure time must be in the future."],
      ["Gate", "A-D + 1-20, optional", "Gate must be a terminal letter A-D followed by 1-20, e.g. B7."],
      ["Seat rows / fare", "1-40 / 500-200000", "Number of seat rows must be between 1 and 40. / Fare must be between Rs 500 and Rs 200000."],
      ["Seat", "row 1..rows + A-F", "Seat must be a row number followed by a letter, e.g. 12C."],
      ["PNR", "6 letters/digits", "PNR must be exactly 6 letters/digits, e.g. K7Q2MA."],
      ["Bag weight", "0 < w <= 32", "A single bag cannot exceed 32 kg; send it as cargo."],
      ["Password", "6-64, letter + digit", "Password must contain at least one letter and one digit."],
      ["Mobile", "10 digits, starts 6-9", "Phone must be a 10-digit mobile number starting with 6-9."],
      ["Card number", "13-19 digits, Luhn checksum", "Card number must be 13-19 digits. / That card number is not valid. Check the digits."],
      ["Card expiry / CVV", "MM/YY not in the past / 3 digits (4 for Amex)", "This card has expired. / CVV must be 3 digits."],
      ["UPI id / bank", "name@bank / one of the listed banks", "UPI ID must look like name@bank, e.g. priya@okaxis. / Choose your bank from the list."],
      ["Service time / duration / days", "HH:MM / 20-1200 min / Daily, Weekdays, Weekends or Mon,Wed,Fri", "Departure time must be HH:MM in 24-hour format, e.g. 06:45. / Days must be Daily, Weekdays, Weekends, or a list like Mon,Wed,Fri."],
      ["Days to generate", "1-90", "Number of days must be between 1 and 90."],
    ], [1.4, 3.0, 4.6], { caption: "Validation rules and messages", size: 17 }),
    H2("10.4 Sample Data"),
    ...Tbl(["Data", "Records"], [
      ["Users", "admin/admin123 (ADMIN), staff1, staff2/staff123 (STAFF), priya, rahul, sneha/pass1234 (PASSENGER)"],
      ["Flights", "8 hand-made flights (AI202 DEL-BOM, 6E5021 BLR-DEL, UK811 BOM-BLR, SG134 DEL-GOI (DELAYED), AI505 MAA-CCU, QP1302 BOM-DEL (BOARDING), IX345 CCU-DEL (CANCELLED), 6E2140 DEL-BLR) plus about 11,000 flights generated for the next 30 days from 420 recurring services (21 airports)"],
      ["Bookings", "8 bookings incl. one CHECKED_IN (R4T9XB) and one CANCELLED and refunded (C8L4KG); PNR K7Q2MA is ready for a check-in demo"],
      ["Payments", "Every live sample booking is PAID (card, UPI or net banking); C8L4KG is REFUNDED in full because its flight was cancelled"],
      ["Bags", "2 bags on booking R4T9XB (one LOADED)"],
    ], [1.4, 7.6]),
    H2("10.5 GUI Screenshots"),
    P("The screenshots below were captured from the running application by the script `tools/capture_screenshots.py`, which logs in as each role and performs the actions shown (against a throw-away database with the full 30-day schedule). Message boxes are redrawn as plain windows by the script so that they appear in the capture; the message text is the program's own."),
    ...shots.filter(([f]) => KEEP_SHOTS.includes(f)).flatMap(([f, cap]) => Img(`docs/screenshots/${f}.png`, cap, { maxH: 300 })),
    P("All 21 screenshots, including the error messages for each role, are in the folder `docs/screenshots`."),
  ];
}

const BB = [
  ["BB01", "parse_seat", "ECP valid", "'12C', rows=20", "'12C'"],
  ["BB02", "parse_seat", "ECP valid (case/space)", "' 7d '", "'7D'"],
  ["BB03", "parse_seat", "BVA min row", "'1A'", "'1A'"],
  ["BB04", "parse_seat", "BVA max row", "'20F'", "'20F'"],
  ["BB05", "parse_seat", "BVA min-1", "'0A'", "ValidationError"],
  ["BB06", "parse_seat", "BVA max+1", "'21A'", "ValidationError"],
  ["BB07", "parse_seat", "ECP invalid column", "'5G'", "ValidationError"],
  ["BB08", "parse_seat", "ECP invalid format", "'A5', '', '12', '1 2C', None", "ValidationError"],
  ["BB09", "validate_bag_weight", "ECP valid", "'18.5'", "18.5"],
  ["BB10", "validate_bag_weight", "BVA max", "'32'", "32.0"],
  ["BB11", "validate_bag_weight", "BVA max+", "'32.1'", "ValidationError"],
  ["BB12", "validate_bag_weight", "BVA min valid", "'0.1'", "0.1"],
  ["BB13", "validate_bag_weight", "BVA / ECP <= 0", "'0', '-5'", "ValidationError"],
  ["BB14", "validate_bag_weight", "ECP non-numeric", "'heavy'", "ValidationError"],
  ["BB15", "compute_excess_fee", "BVA 0", "0", "0"],
  ["BB16", "compute_excess_fee", "BVA allowance", "15.0", "0"],
  ["BB17", "compute_excess_fee", "BVA allowance+", "15.1", "500"],
  ["BB18", "compute_excess_fee", "ECP over", "20.0", "2500"],
  ["BB19", "compute_excess_fee", "ECP invalid", "-1", "ValidationError"],
  ["BB20", "validate_flight_no", "ECP valid / invalid", "'ai202', '6E5021' / '22202', 'AI', 'AI20202', 'AI-202'", "'AI202', '6E5021' / ValidationError"],
  ["BB21", "validate_route", "ECP", "DEL,BOM / DEL,DEL", "('DEL','BOM') / ValidationError"],
  ["BB22", "validate_rows", "BVA 1..40", "'1', '40' / '0', '41', 'ten'", "1, 40 / ValidationError"],
  ["BB23", "validate_fare", "BVA 500..200000", "'500', '200000' / '499', '200001', '12.5'", "500, 200000 / ValidationError"],
  ["BB24", "validate_gate", "ECP + BVA", "'' , 'b7', 'D20' / 'E1', 'A0', 'A21', '7B'", "None, 'B7', 'D20' / ValidationError"],
  ["BB25", "validate_password", "BVA length 6, ECP", "'abc123' / 'ab12', 'abcdefg', '1234567'", "accepted / ValidationError"],
  ["BB26", "validate_phone, validate_email", "ECP", "'98765 43210', 'Om@Example.com' / '5876543210', '987654321', 'om@example'", "normalised / ValidationError"],
];

const WB = [
  ["WB01", "check_in", "1T-R1-E", "role = PASSENGER", "AuthorizationError"],
  ["WB02", "check_in", "1F-2T-R2-E", "PNR 'ZZZZZZ' (absent)", "NotFoundError"],
  ["WB03", "check_in", "...3T-R3-E", "PNR C8L4KG (cancelled)", "BusinessRuleError 'cancelled'"],
  ["WB04", "check_in", "...4T-R4-E", "PNR R4T9XB (already checked in)", "BusinessRuleError 'already checked in'"],
  ["WB05", "check_in", "...5T-R5-E", "AI202 set DEPARTED, PNR K7Q2MA", "BusinessRuleError 'DEPARTED'"],
  ["WB06", "check_in", "...7T-R7-E", "PNR H2N6YE, flight 54 h away", "BusinessRuleError 'opens'"],
  ["WB07", "check_in", "...8T-R8-E", "PNR T5V3QF, flight 30 min away", "BusinessRuleError 'closed'"],
  ["WB08", "check_in", "1F-2F-...-8F-9-10-E", "PNR K7Q2MA, 3 h before departure", "Boarding pass: seat 4A, gate A3, seq 2, boarding = dep - 30 min"],
  ["WB09", "check_in", "boundary of nodes 7 and 8", "now = dep - 45 min / dep - 44 min", "accepted / rejected"],
  ["WB27", "check_in", "...5F-6T-R6-E", "Unpaid booking on UK811 (54 h away)", "BusinessRuleError 'Payment ... pending'"],
  ["WB28", "check_in", "6T before 7T", "same booking, unpaid then paid", "'Payment' first; after paying 'opens' (order of the checks)"],
  ["WB10", "is_gate_available", "1T-E", "gate None", "True"],
  ["WB11", "is_gate_available", "1F-2-3-7-E (loop 0 times)", "gate D20 (unused)", "True"],
  ["WB12", "is_gate_available", "1F-2-3-4F-5T-6-E", "A3 at AI202 dep + 59 min", "False"],
  ["WB13", "is_gate_available", "1F-2-3-4F-5F-3-...-7-E", "A3 at AI202 dep + 60 min", "True"],
  ["WB14", "is_gate_available", "1F-2-3-4T-3-...-7-E", "A3 at AI202 dep, exclude AI202", "True"],
  ["WB15", "compute_excess_fee", "1T-R-E", "-0.5", "ValidationError"],
  ["WB16", "compute_excess_fee", "1F-2-3T-4-E", "10", "0"],
  ["WB17", "compute_excess_fee", "1F-2-3F-5-E", "21.5", "3500 (ceil 6.5 = 7)"],
  ["WB18", "validate_card_number", "1T-3-E", "'4111-ABCD-1111-1111'", "ValidationError '13-19 digits'"],
  ["WB19", "validate_card_number", "1F-2T-3-E", "'1234'", "ValidationError '13-19 digits'"],
  ["WB20", "validate_card_number", "1F-2F-4T-(5T,6F | 5F)-...-4F-10F-12-E", "'4111 1111 1111 1111'", "'4111111111111111'"],
  ["WB21", "validate_card_number", "...5T-6T-7-9-4...", "'5555555555554444' (5 doubled = 10 > 4)", "accepted"],
  ["WB22", "validate_card_number", "...4F-10T-11-E", "'4111111111111112'", "ValidationError 'not valid'"],
  ["WB23", "validate_card_number", "boundary of node 2", "13 and 19 digits / 12 and 20 digits", "accepted / ValidationError"],
  ["WB24", "cancellation_percent", "1T-2T-3-E", "100 hours", "10"],
  ["WB25", "cancellation_percent", "1T-2F-1T-2T-3-E", "30 h / 10 h", "25 / 50"],
  ["WB26", "cancellation_percent", "1T-2F-...-1F-4-E", "1.9 h (and 2 h boundary)", "100 (and 50)"],
];

const UT = [
  ["UT01", "AuthService", "Login with 'ADMIN ' (case/space) and correct password", "role ADMIN"],
  ["UT02", "AuthService", "Wrong password", "AuthenticationError"],
  ["UT03", "AuthService", "Blank username and password", "ValidationError"],
  ["UT04", "AuthService", "Register new passenger, then log in", "role PASSENGER, same user_id"],
  ["UT05", "AuthService", "Register with existing username", "'already taken'"],
  ["UT06", "AuthService", "Staff tries to create staff; admin creates staff", "AuthorizationError; then STAFF account"],
  ["UT07", "AuthService", "Stored hash does not contain the password", "plain text absent"],
  ["UT08", "FlightService", "Add valid flight (15 rows)", "SCHEDULED, capacity 90"],
  ["UT09", "FlightService", "Staff adds a flight", "AuthorizationError"],
  ["UT10", "FlightService", "Departure in the past", "ValidationError 'future'"],
  ["UT11", "FlightService", "Second flight at same gate 30 min later", "'Gate C9' conflict"],
  ["UT12", "FlightService", "Same flight number same day", "'already scheduled'"],
  ["UT13", "FlightService", "Update rows/fare, then assign gate 'd11'", "rows 20, fare 4500; gate D11"],
  ["UT14", "FlightService", "Reduce AI202 to 8 rows (row 10 booked)", "'row 10' error"],
  ["UT15", "FlightService", "Cancel AI202", "3 bookings cancelled, gate None, no taken seats"],
  ["UT16", "FlightService", "CANCELLED -> SCHEDULED; SCHEDULED -> DELAYED", "error; DELAYED"],
  ["UT17", "BookingService", "Search from DEL", "AI202, SG134, 6E2140; AI202 has 117 seats left"],
  ["UT18", "BookingService", "Search all", "IX345 (cancelled) and QP1302 (boarding) excluded"],
  ["UT19", "BookingService", "Book UK811 seat '1a' (fixed PNR generator)", "PNR TEST01, seat 1A, fare 4800, BOOKED"],
  ["UT20", "BookingService", "Book taken seat 7D", "'taken'"],
  ["UT21", "BookingService", "Book cancelled flight IX345", "'CANCELLED'"],
  ["UT22", "BookingService", "Second booking on same flight", "'already hold'"],
  ["UT23", "BookingService", "Staff books", "AuthorizationError"],
  ["UT24", "BookingService", "Cancel own booking P9W1ZD", "seat 12C free"],
  ["UT25", "BookingService", "Cancel another passenger's booking", "'own' error"],
  ["UT26", "BookingService", "Cancel checked-in booking", "'checked in' error"],
  ["UT27", "BookingService", "List bookings as passenger / staff", "own only / all 8"],
  ["UT28", "CheckInService", "Add 12.4 kg bag", "tag AMSnnnnnn, CHECKED_IN"],
  ["UT29", "CheckInService", "Add bag before check-in", "error"],
  ["UT30", "CheckInService", "Fourth bag", "'at most 3'"],
  ["UT31", "CheckInService", "Bags 17.5 + 4 kg", "(21.5, 3500)"],
  ["UT32", "CheckInService", "LOADED -> UNLOADED -> CLAIMED, then LOADED", "CLAIMED; then error"],
  ["UT33", "CheckInService", "Passenger views own / other's boarding pass", "seat 4A / 'own' error"],
];

function ch11() {
  setChapter(11);
  const covRows = COV.map((r) => [r[0], r[1], r[2], r[3], r.slice(4).join(" ")]);
  const n = (prefix) => Object.keys(STATUS).filter((k) => k.startsWith(prefix));
  const passed = (prefix) => n(prefix).filter((k) => STATUS[k] === "Pass").length;
  return [
    H1("11. Software Testing"),
    H2("11.1 Testing Strategy"),
    P("Testing was done at three levels on the real code: **black-box testing** of the functions' specified behaviour (the algorithmic rules), **white-box testing** of the source code paths, and **unit testing** of each service class. Black-box + white-box testing of individual units together form the unit testing of the system. All tests are automated with Python `unittest` and can be re-run with one command (Section 11.7). The results reported here are the actual output of that run (`docs/test_results.txt`)."),
    P("To make tests repeatable, each test creates a fresh **in-memory database** seeded at a fixed time `NOW = 2026-11-10 09:00` and passes that time explicitly to the services (the injectable clock described in NF8)."),
    H2("11.2 Black-Box Testing"),
    P("Black-box test cases are designed from the specification only (SRS Sections 4.3 and 4.6), without looking at the code, using **Equivalence Class Partitioning (ECP)** - one test per valid and invalid class - and **Boundary Value Analysis (BVA)** - tests at, just inside and just outside each boundary."),
    H3("11.2.1 Equivalence classes and boundaries"),
    ...Tbl(["Input", "Valid classes", "Invalid classes", "Boundary values tested"], [
      ["Seat (rows = 20)", "row 1-20 and column A-F", "row < 1; row > 20; column not A-F; wrong format/empty", "0, 1, 20, 21"],
      ["Bag weight (kg)", "0 < w <= 32", "w <= 0; w > 32; non-numeric", "0, 0.1, 32, 32.1"],
      ["Total baggage for fee", "0 <= w <= 15 (fee 0); w > 15 (fee > 0)", "w < 0", "0, 15.0, 15.1"],
      ["Seat rows", "1-40", "< 1; > 40; non-integer", "0, 1, 40, 41"],
      ["Fare (Rs)", "500-200000", "< 500; > 200000; non-integer", "499, 500, 200000, 200001"],
      ["Gate", "empty; A-D + 1-20", "letter E+; number 0 or > 20; wrong order", "A0, D20, A21"],
      ["Password length", "6-64 with letter + digit", "< 6; no digit; no letter", "length 4 and 6"],
    ], [1.6, 2.6, 2.9, 1.9], { caption: "Equivalence classes and boundary values", size: 18 }),
    H3("11.2.2 Black-box test cases and results"),
    ...Tbl(["ID", "Unit", "Technique", "Input", "Expected", "Result"], BB.map((r) => [...r, st(r[0])]),
      [0.7, 1.6, 1.4, 2.5, 2.1, 0.7], { caption: "Black-box test cases (tests/test_blackbox.py)", size: 16, zebra: true }),
    P("**Defect found by black-box testing.** In the first run, BB20 failed: the input 'A202' was accepted because the pattern allowed any two letters/digits as the airline code. The specification was clarified (the airline code must contain at least one letter, e.g. AI, 6E, G8), the validator in `validators.py` was corrected, and the ambiguous input was replaced by the clearly invalid '22202'. All black-box tests pass after the fix."),

    H2("11.3 White-Box Testing"),
    P("White-box test cases are derived from the source code. For each unit the **control-flow graph (CFG)** was drawn, its **cyclomatic complexity** V(G) computed in two ways (V(G) = E - N + 2 and V(G) = number of decision nodes + 1), and one test case written for each **basis path** (path coverage), plus boundary tests of the decisions. Circles are the statements and decisions of the code (a node with two outgoing edges is a decision; T and F label its branches), R1, R2 ... are raised exceptions and E is the exit, as in Figure 10.7 of the textbook."),
    H3("11.3.1 Unit 1: CheckInService.check_in()"),
    ...Code(pySource("ams/services/checkin_service.py", "check_in")),
    ...Tbl(["Node", "Statement / decision"], [
      ["1", "require_role(actor, STAFF, ADMIN) - role not allowed?"], ["2", "find_booking(pnr) - booking not found (or bad PNR)?"],
      ["3", "booking.status == CANCELLED?"], ["4", "booking.status == CHECKED_IN?"], ["5", "flight_status in (CANCELLED, DEPARTED)?"],
      ["6", "no PAID payment for the booking? (added with payments)"],
      ["7", "now < departure - 48 h?"], ["8", "now > departure - 45 min?"], ["9", "compute seq; UPDATE booking; commit"],
      ["10", "return get_boarding_pass(...)"], ["R1-R8", "raise the corresponding error (T branch of nodes 1-8)"], ["E", "exit"],
    ], [1.0, 8.0], { caption: "CFG node numbering for check_in()" }),
    ...Img("docs/diagrams/cfg_check_in.png", "Control-flow graph of check_in(): N = 19, E = 26, V(G) = 9", { maxH: 500 }),
    H3("11.3.2 Unit 2: FlightService.is_gate_available()"),
    ...Code(pySource("ams/services/flight_service.py", "is_gate_available")),
    P("Nodes: 1 `gate is None?`, 2 query active flights at the gate, 3 loop `for row in rows` (next row / rows done), 4 `row is the excluded flight?`, 5 `gap_minutes < 60?`, 6 `return False`, 7 `return True` after the loop, E exit."),
    ...Img("docs/diagrams/cfg_gate.png", "Control-flow graph of is_gate_available(): N = 8, E = 11, V(G) = 5", { maxH: 470 }),
    H3("11.3.3 Unit 3: compute_excess_fee()"),
    ...Code(pySource("ams/services/checkin_service.py", "compute_excess_fee")),
    P("Nodes: 1 `total < 0?`, R raise, 2 `excess = total - 15`, 3 `excess <= 0?`, 4 `return 0`, 5 `return ceil(...) * 500`, E exit."),
    ...Img("docs/diagrams/cfg_excess_fee.png", "Control-flow graph of compute_excess_fee(): N = 7, E = 8, V(G) = 3", { maxH: 380, maxW: 330 }),
    H3("11.3.4 Unit 4: validators.validate_card_number()"),
    ...Code(pySource("ams/validators.py", "validate_card_number")),
    P("Nodes: 1 `not digits.isdigit()?`, 2 `not 13 <= len(digits) <= 19?` (the two halves of the `or` are separate decisions), 3 `raise` (format), 4 loop `for i, ch in enumerate(reversed(digits))`, 5 `i % 2 == 1?`, 6 `d > 4?` (the conditional expression), 7 `d = d * 2 - 9`, 8 `d = d * 2`, 9 `total += d`, 10 `total % 10 != 0?`, 11 `raise` (checksum), 12 `return digits`, E exit. The two paths that run the loop zero times cannot happen (a valid length is at least 13 digits), so five of the seven basis paths are feasible; they give 100% branch coverage (all twelve branch outcomes of the six decisions)."),
    ...Img("docs/diagrams/cfg_card_number.png", "Control-flow graph of validate_card_number(): N = 13, E = 18, V(G) = 7", { maxH: 420, maxW: 420 }),
    H3("11.3.5 Unit 5: payments_core.cancellation_percent()"),
    ...Code(pySource("ams/payments_core.py", "cancellation_percent")),
    P("Nodes: 1 loop head (`for min_hours, percent in REFUND_TIERS` - T: another tier, F: tiers exhausted), 2 `hours >= min_hours?`, 3 `return percent`, 4 `return 100`, E exit."),
    ...Img("docs/diagrams/cfg_refund_tier.png", "Control-flow graph of cancellation_percent(): N = 5, E = 6, V(G) = 3", { maxH: 380, maxW: 360 }),
    H3("11.3.6 Basis paths, test cases and results"),
    ...Tbl(["Unit", "V(G)", "Independent paths needed", "Tests written"], [
      ["check_in", "9", "9", "WB01-WB08, WB27 (+ WB09 boundary, WB28 order of checks)"], ["is_gate_available", "5", "5", "WB10-WB14"], ["compute_excess_fee", "3", "3", "WB15-WB17"],
      ["validate_card_number", "7", "5 feasible (2 need an empty loop)", "WB18-WB22 (+ WB23 boundary)"], ["cancellation_percent", "3", "3", "WB24-WB26"],
    ], [2.4, 1.0, 2.4, 3.2], { caption: "Cyclomatic complexity and number of basis-path tests" }),
    ...Tbl(["ID", "Unit", "Path", "Test data", "Expected", "Result"], WB.map((r) => [...r, st(r[0])]),
      [0.7, 1.6, 2.0, 2.3, 2.3, 0.7], { caption: "White-box test cases (tests/test_whitebox.py and tests/test_whitebox_payments.py)", size: 16, zebra: true }),
    H2("11.4 Unit Testing of Service Classes"),
    P("Each service class was tested as a unit against an in-memory database, covering normal behaviour, every business rule and role check."),
    ...Tbl(["ID", "Class", "Scenario", "Expected", "Result"], UT.map((r) => [...r, st(r[0])]),
      [0.7, 1.5, 3.6, 2.5, 0.7], { caption: "Unit test cases (tests/test_services.py)", size: 16, zebra: true }),
    H2("11.5 Tests of the Recurring Schedule, the Boarding-Pass PDF and the Payments"),
    P("The three later iterations came with their own suites. They mix black-box tests of the rules (equivalence classes and boundaries of the time, duration, day, card, expiry and CVV fields; the refund tiers at 48, 24 and 2 hours) with unit tests of the service classes and with checks of the generated files. The scenario column is taken from the name of each test method in the real test run."),
    ...Tbl(["Suite (file)", "IDs", "Tests", "What is covered", "Result"], [
      ["Recurring schedule (tests/test_schedule.py)", "SG01-SG29", String(n("SG").length), "Service validation (time, duration, days, rows, fare), dynamic fare, gate planning, generation without duplicates, horizon limits, activate/deactivate", `${passed("SG")} passed`],
      ["Boarding-pass PDF (tests/test_boarding_pdf.py)", "BP01-BP17", String(n("BP").length), "Code 128 barcode symbols and widths, PDF structure, text escaping, file names, who may download a pass", `${passed("BP")} passed`],
      ["Payments (tests/test_payments.py)", "PY01-PY40", String(n("PY").length), "Card number (Luhn), expiry, CVV, UPI, bank; fare breakdown; approve/decline paths that leave no held seat; refund tiers at 48, 24 and 2 hours; full refund on flight cancellation; receipts", `${passed("PY")} passed`],
    ], [2.4, 1.2, 0.7, 3.9, 0.9], { caption: "Tests of the later iterations (every test listed by name in docs/test_results.txt)", size: 16 }),
    P("The barcode was also verified against an independent encoder and a software scanner, which read the printed barcodes of seven PNRs correctly at three resolutions. This cross-check found a real defect: an extra entry in the first version of the pattern table shifted every symbol after value 66, so the code would not have scanned although the page looked correct."),
    H3("11.5.4 Error seeding and defects found"),
    P("**Error seeding** (section 10.12.3 of the textbook) was used to check that the new tests can fail: a refund tier was changed from 25% to 15%, and separately the payment check in `check_in` was disabled. In each case the suite reported a failure and passed again when the code was restored. Defects found while building the later iterations: (1) the wrong bar-code table entry described above, found by the cross-check; (2) in the scripted GUI run, the payment-method tabs used a colour name that the colour blender could not parse, which would have crashed when switching tabs; (3) the card-number box showed unformatted text because it was reformatted inside its own write callback (now deferred); (4) three of the new tests were themselves wrong (an expected boarding sequence in BP16, an expected last flight date in SG25 and an over-weak escape assertion in BP11) and were corrected, which is why every expected value was recomputed by hand."),
    H2("11.6 Test Results Summary"),
    ...Tbl(["Suite", "Test methods", "Passed", "Failed"], [
      ["Black-box (BB)", String(n("BB").length), String(passed("BB")), String(n("BB").length - passed("BB"))],
      ["White-box (WB)", String(n("WB").length), String(passed("WB")), String(n("WB").length - passed("WB"))],
      ["Unit (UT)", String(n("UT").length), String(passed("UT")), String(n("UT").length - passed("UT"))],
      ["Recurring schedule (SG)", String(n("SG").length), String(passed("SG")), String(n("SG").length - passed("SG"))],
      ["Boarding-pass PDF (BP)", String(n("BP").length), String(passed("BP")), String(n("BP").length - passed("BP"))],
      ["Payments (PY)", String(n("PY").length), String(passed("PY")), String(n("PY").length - passed("PY"))],
      ["Total", SUMMARY[1] || "?", String(passed("")), String(Object.keys(STATUS).length - passed(""))],
    ], [3.0, 2.0, 2.0, 2.0], { caption: `Test summary (unittest: "Ran ${SUMMARY[1]} tests in ${SUMMARY[2]}s", result ${FINAL})` }),
    P("Several test methods check more than one input using `subTest` (e.g. BB08 checks 5 malformed seats), so the number of individual checks is larger than the number of methods."),
    P("**Statement coverage** of the non-GUI code, measured with the `coverage` tool while running all tests:"),
    ...Tbl(["File", "Statements", "Missed", "Cover"], covRows.map((r) => r.slice(0, 4)), [4.6, 1.5, 1.4, 1.5],
      { caption: "Statement coverage of the non-GUI code", size: 16 }),
    P("The GUI layer is excluded from coverage because it is tested manually and by the screenshot script that drives every role through the main flows (system testing, Section 10.5). Most uncovered lines are secondary error branches (e.g. 'Unknown flight status', 'User not found') and the retry-exhausted branch of PNR generation."),
    H2("11.7 How to Run the Tests"),
    ...Code(["cd AirportMS", "python -m unittest discover -s tests -t . -v",
      "", "# optional coverage report", "pip install coverage",
      "python -m coverage run --source=ams --omit=\"ams/gui/*\" -m unittest discover -s tests -t .",
      "python -m coverage report -m"]),
  ];
}

function ch12() {
  setChapter(12);
  return [
    H1("12. Limitations and Future Scope"),
    ...Tbl(["Limitation (not implemented)", "Possible extension"], [
      ["Payment is simulated: a built-in gateway approves or declines and no money moves.", "Integrate a real payment gateway (tokenised cards, webhooks); charge the excess-baggage fee as a payment at the counter."],
      ["Boarding passes and receipts are PDF files; bag tags are shown on screen only; no QR code or direct printing.", "QR code on the pass, print bag tags, send the pass by e-mail."],
      ["The timetable is synthetic and the same every day; no seasonal changes or delays feed.", "Import a real timetable; seasonal templates; automatic delay messages."],
      ["Single-user desktop application with one SQLite file.", "Client-server version (web front end, PostgreSQL) for many counters."],
      ["One cabin class; fixed 6-abreast layout; fares depend only on time of day, weekday and days ahead.", "Seat classes, aircraft types with layouts, demand-based pricing."],
      ["No notifications.", "E-mail/SMS on booking, gate change, delay and cancellation."],
      ["No password reset or account deactivation.", "Self-service reset, admin deactivation, audit log of changes."],
      ["Local times only.", "Time-zone aware schedules for international flights."],
      ["GUI tested manually.", "Automated GUI tests."],
    ], [4.5, 4.5], { caption: "Limitations and future scope" }),
  ];
}

function ch13() {
  setChapter(13);
  return [
    H1("13. Conclusion", { newPage: false }),
    P("The Airport Management System was analysed, designed, implemented and tested following the iterative waterfall model, and later extended in three further iterations (recurring schedule, boarding-pass PDF and calendar, payments). The function-oriented design (context diagram, balanced Level 1-3 DFDs, a data dictionary covering every flow, and structure charts from transaction and transform analysis) and the object-oriented design (use case, class, activity, state chart, sequence and collaboration diagrams) describe the same system with the same names, drawn in the notation of the prescribed textbook, and both map directly onto the code."),
    P(`The working Tkinter + SQLite application implements all six modules with role-based access, input validation and clear error messages. Its layered structure gives high cohesion and low coupling, which made it possible to test every business rule without the GUI: ${SUMMARY[1]} automated black-box, white-box and unit tests pass, with ${(COV.find((r) => r[0] === "TOTAL") || [])[3]} statement coverage of the non-GUI code, and testing and cross-checking found and fixed real defects (an invalid flight-number rule, a wrong bar-code table entry, and two GUI faults).`),
  ];
}

function references() {
  return [
    H1("14. References", { newPage: false }),
    ...Bullets([
      "Rajib Mall, Fundamentals of Software Engineering, 4th ed., PHI Learning - the prescribed textbook; the notation of every diagram in this report is taken from its Figures 2.3, 6.2, 6.8-6.23, 7.15-7.33 and 10.7.",
      "Roger S. Pressman, Software Engineering: A Practitioner's Approach, McGraw-Hill.",
      "IEEE Std 830-1998, IEEE Recommended Practice for Software Requirements Specifications.",
      "Python Software Foundation, Python 3 documentation: tkinter, sqlite3, unittest, hashlib.",
      "SQLite documentation: partial indexes, CHECK and foreign-key constraints (sqlite.org).",
      "Object Management Group, UML 2.5 specification (diagram notation).",
      "ISO/IEC 15417, Code 128 bar code symbology specification (subset B, start/stop patterns, modulo-103 check character).",
      "H. P. Luhn, mod-10 checksum algorithm for identification numbers (ISO/IEC 7812-1).",
    ]),
  ];
}

function appendixA() {
  setChapter("A");
  const rows = [];
  for (const mod of REQUIREMENTS) for (const r of mod.items) rows.push([r.id, r.name, ...r.trace]);
  return [
    H1("Appendix A. Requirements Traceability Matrix"),
    P("Each functional requirement is traced to the DFD process that models it, the use case, the code that implements it and the tests that verify it."),
    ...Tbl(["Req.", "Name", "DFD process", "Use case", "Code", "Tests"], rows, [0.6, 1.6, 1.1, 1.0, 2.9, 1.8],
      { caption: "Requirements traceability matrix", size: 16, zebra: true }),
  ];
}

function appendixB() {
  return [
    H1("Appendix B. Setup and Run Instructions", { newPage: false }),
    ...Bullets(["Install Python 3.9 or newer from python.org (Tkinter and SQLite are included). Nothing else is needed to run the program, the tests, or the PDF and calendar features.",
      "Optional tools: `pip install coverage` (coverage report), Graphviz + Java + plantuml.jar (re-draw the diagrams: `python tools/make_dfds.py`, `make_design_diagrams.py`, `make_usecase.py`, `make_uml.py`, `data_dictionary.py`), Node.js with `npm install docx` (re-build this report: `node tools/report/build.js`)."]),
    ...Code(["cd AirportMS", "python run.py --reset      # create fresh sample data and start", "python run.py              # start with the existing data",
      "python init_db.py --reset  # only (re)create the database", "run.bat                    # Windows: double-click to start"]),
    ...Tbl(["Role", "Username", "Password"], [["Administrator", "admin", "admin123"], ["Check-in staff", "staff1 / staff2", "staff123"],
      ["Passenger", "priya / rahul / sneha", "pass1234"]], [3, 3, 3], { caption: "Demo accounts" }),
    H2("Suggested demonstration (about 5 minutes)"),
    ...Bullets([
      "**admin**: Flights tab - open the calendar on the date filter; add a flight with gate Z9 to show validation; add a valid one; assign a gate already in use to show the clash rule; set status DELAYED. Schedule tab - filter IXE (Mangalore), generate flights and show that a second run creates nothing.",
      "**priya**: search IXE - Mangalore to BLR - Bengaluru on a date picked on the calendar, select a flight, pick a seat; in the payment window try card 4000 0000 0000 0002 (declined, nothing booked), then 4111 1111 1111 1111; download the receipt; cancel the booking and show the refund preview.",
      "**staff1**: Check-in tab - PNR K7Q2MA, check in (boarding pass), download the boarding pass PDF, add bags of 17.5 and 4 kg (fee Rs 3500), try 40 kg (error), set a bag to LOADED. Try PNR H2N6YE to show 'check-in opens 48 hours before departure'.",
      "**priya**: Boarding Pass tab shows the pass and downloads it.",
      "Run `python -m unittest discover -s tests -t . -v` to show " + SUMMARY[1] + " passing tests.",
    ]),
  ];
}

module.exports = { ch10, ch11, ch12, ch13, references, appendixA, appendixB };
