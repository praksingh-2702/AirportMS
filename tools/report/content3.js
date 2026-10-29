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
const SUMMARY = (RESULTS_TXT.match(/Ran (\d+) tests? in ([\d.]+)s/) || []);
const FINAL = /\nOK\s*$/.test(RESULTS_TXT.trim() + "\n") || /\nOK\b/.test(RESULTS_TXT) ? "OK" : "FAILED";
const st = (id) => { if (!STATUS[id]) throw new Error(`No result for ${id} in test_results.txt`); return STATUS[id]; };

const COV = fs.readFileSync(path.join(L.ROOT, "docs", "coverage_report.txt"), "utf8").split("\n")
  .filter((l) => /^(ams\/|TOTAL)/.test(l)).map((l) => l.trim().split(/\s+/));

function ch10() {
  setChapter(10);
  const shots = [
    ["00_login_admin", "Login screen (demo accounts shown for the lab demonstration)"],
    ["01_login_error", "Wrong password: the same message is shown for unknown user and wrong password (NF4)"],
    ["02_admin_flights", "Administrator - Flight Schedule tab with add/update form, gate assignment, status and cancel controls"],
    ["03_admin_flight_validation_error", "Validation error when adding a flight with an invalid flight number"],
    ["04_admin_users", "Administrator - Users tab (create staff/admin accounts)"],
    ["05_admin_all_bookings", "Administrator - all bookings, cancelled bookings greyed out"],
    ["06_passenger_search", "Passenger - search results (only bookable future flights) and own bookings"],
    ["07_passenger_seat_map", "Passenger - seat map: taken seats disabled, selected seat green"],
    ["08_passenger_booking_confirmed", "Booking confirmed with generated PNR"],
    ["09_staff_checkin_boarding_pass", "Check-in staff - boarding pass after check-in; two bags tagged, 21.5 kg, excess fee Rs 3500"],
    ["10_staff_bag_weight_error", "Bag heavier than 32 kg rejected with an explanatory message"],
    ["11_passenger_boarding_pass", "Passenger - own boarding pass after check-in"],
  ];
  return [
    H1("10. Implementation and Working GUI"),
    H2("10.1 Architecture"),
    P("The program has three layers. Dependencies point only downwards, which is what keeps coupling low (Chapter 6)."),
    ...Tbl(["Layer", "Package / files", "Responsibility"], [
      ["Presentation (boundary)", "ams/gui/: app.py, login_view.py, flight_view.py, booking_view.py, checkin_view.py, users_view.py, widgets.py", "Windows, tabs, forms, tables, seat map; shows errors in dialogs."],
      ["Service (control)", "ams/services/: auth_service.py, flight_service.py, booking_service.py, checkin_service.py", "All business rules and role checks."],
      ["Utility & data", "ams/: models.py, validators.py, access.py, security.py, errors.py, config.py, database.py", "Entities, validation, hashing, constants, schema and sample data."],
      ["Entry points", "run.py, init_db.py, run.bat", "Start the GUI; create/reset the database."],
      ["Tests", "tests/: test_blackbox.py, test_whitebox.py, test_services.py, helpers.py", "76 automated tests on an in-memory database with a fixed clock."],
    ], [1.8, 4.4, 2.8], { caption: "Source code organisation" }),
    H2("10.2 Important Algorithms and Mechanisms"),
    ...Bullets([
      "**Seat uniqueness:** checked in `book_ticket` and also guaranteed by the partial unique index `ux_active_seat ON bookings(flight_id, seat) WHERE status <> 'CANCELLED'`; if two bookings race for one seat the database rejects the second and the user sees 'Seat ... was just taken.'",
      "**Gate clash check:** `is_gate_available` compares the departure time with every other active flight at the same gate and rejects a gap below 60 minutes (white-box tested, Section 11.3).",
      "**PNR generation:** 6 random characters from an alphabet without I, O, 0, 1 (`secrets` module), retried until unused.",
      "**Check-in window and boarding sequence:** see the axiomatic specification in Section 5.2.",
      "**Excess-baggage fee:** Rs 500 per started kilogram above 15 kg (`compute_excess_fee`).",
      "**State machines:** flight and bag statuses change only through the transition tables shown in Section 9.5.",
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
    ], [1.4, 3.0, 4.6], { caption: "Validation rules and messages", size: 17 }),
    H2("10.4 Sample Data"),
    ...Tbl(["Data", "Records"], [
      ["Users", "admin/admin123 (ADMIN), staff1, staff2/staff123 (STAFF), priya, rahul, sneha/pass1234 (PASSENGER)"],
      ["Flights", "AI202 DEL-BOM, 6E5021 BLR-DEL, UK811 BOM-BLR, SG134 DEL-GOI (DELAYED), AI505 MAA-CCU, QP1302 BOM-DEL (BOARDING), IX345 CCU-DEL (CANCELLED), 6E2140 DEL-BLR"],
      ["Bookings", "8 bookings incl. one CHECKED_IN (R4T9XB) and one CANCELLED (C8L4KG); PNR K7Q2MA is ready for a check-in demo"],
      ["Bags", "2 bags on booking R4T9XB (one LOADED)"],
    ], [1.4, 7.6]),
    H2("10.5 GUI Screenshots"),
    P("The screenshots below were captured from the running application by the script `tools/capture_screenshots.py`, which logs in as each role and performs the actions shown. Message boxes are redrawn as plain windows by the script so that they appear in the capture; the message text is the program's own."),
    ...shots.flatMap(([f, cap]) => Img(`docs/screenshots/${f}.png`, cap, { maxH: 420 })),
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
  ["WB06", "check_in", "...6T-R6-E", "PNR H2N6YE, flight 54 h away", "BusinessRuleError 'opens'"],
  ["WB07", "check_in", "...7T-R7-E", "PNR T5V3QF, flight 30 min away", "BusinessRuleError 'closed'"],
  ["WB08", "check_in", "1F-2F-...-7F-8-9-E", "PNR K7Q2MA, 3 h before departure", "Boarding pass: seat 4A, gate A3, seq 2, boarding = dep - 30 min"],
  ["WB09", "check_in", "boundary of node 7", "now = dep - 45 min / dep - 44 min", "accepted / rejected"],
  ["WB10", "is_gate_available", "1T-E", "gate None", "True"],
  ["WB11", "is_gate_available", "1F-2-3-7-E (loop 0 times)", "gate D20 (unused)", "True"],
  ["WB12", "is_gate_available", "1F-2-3-4F-5T-6-E", "A3 at AI202 dep + 59 min", "False"],
  ["WB13", "is_gate_available", "1F-2-3-4F-5F-3-...-7-E", "A3 at AI202 dep + 60 min", "True"],
  ["WB14", "is_gate_available", "1F-2-3-4T-3-...-7-E", "A3 at AI202 dep, exclude AI202", "True"],
  ["WB15", "compute_excess_fee", "1T-R-E", "-0.5", "ValidationError"],
  ["WB16", "compute_excess_fee", "1F-2-3T-4-E", "10", "0"],
  ["WB17", "compute_excess_fee", "1F-2-3F-5-E", "21.5", "3500 (ceil 6.5 = 7)"],
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
    P("Testing was done at three levels on the real code: **black-box testing** of the functions' specified behaviour (the algorithmic rules), **white-box testing** of the source code paths, and **unit testing** of each service class. Black-box + white-box testing of individual units together form the unit testing of the system. All tests are automated with Python `unittest` and can be re-run with one command (Section 11.6). The results reported here are the actual output of that run (`docs/test_results.txt`)."),
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
    P("White-box test cases are derived from the source code. For each unit the **control-flow graph (CFG)** was drawn, its **cyclomatic complexity** V(G) computed in two ways (V(G) = E - N + 2 and V(G) = number of decision nodes + 1), and one test case written for each **basis path** (path coverage), plus boundary tests of the decisions. Yellow nodes are decisions, red boxes are raised exceptions, E is the exit."),
    H3("11.3.1 Unit 1: CheckInService.check_in()"),
    ...Code(pySource("ams/services/checkin_service.py", "check_in")),
    ...Tbl(["Node", "Statement / decision"], [
      ["1", "require_role(actor, STAFF, ADMIN) - role not allowed?"], ["2", "find_booking(pnr) - booking not found (or bad PNR)?"],
      ["3", "booking.status == CANCELLED?"], ["4", "booking.status == CHECKED_IN?"], ["5", "flight_status in (CANCELLED, DEPARTED)?"],
      ["6", "now < departure - 48 h?"], ["7", "now > departure - 45 min?"], ["8", "compute seq; UPDATE booking; commit"],
      ["9", "return get_boarding_pass(...)"], ["R1-R7", "raise the corresponding error (T branch of nodes 1-7)"], ["E", "exit"],
    ], [1.0, 8.0], { caption: "CFG node numbering for check_in()" }),
    ...Img("docs/diagrams/cfg_check_in.png", "Control-flow graph of check_in(): N = 17, E = 23, V(G) = 8", { maxH: 640 }),
    H3("11.3.2 Unit 2: FlightService.is_gate_available()"),
    ...Code(pySource("ams/services/flight_service.py", "is_gate_available")),
    P("Nodes: 1 `gate is None?`, 2 query active flights at the gate, 3 loop `for row in rows` (next row / rows done), 4 `row is the excluded flight?`, 5 `gap_minutes < 60?`, 6 `return False`, 7 `return True` after the loop, E exit."),
    ...Img("docs/diagrams/cfg_gate.png", "Control-flow graph of is_gate_available(): N = 8, E = 11, V(G) = 5", { maxH: 470 }),
    H3("11.3.3 Unit 3: compute_excess_fee()"),
    ...Code(pySource("ams/services/checkin_service.py", "compute_excess_fee")),
    P("Nodes: 1 `total < 0?`, R raise, 2 `excess = total - 15`, 3 `excess <= 0?`, 4 `return 0`, 5 `return ceil(...) * 500`, E exit."),
    ...Img("docs/diagrams/cfg_excess_fee.png", "Control-flow graph of compute_excess_fee(): N = 7, E = 8, V(G) = 3", { maxH: 380, maxW: 330 }),
    H3("11.3.4 Basis paths, test cases and results"),
    ...Tbl(["Unit", "V(G)", "Independent paths needed", "Tests written"], [
      ["check_in", "8", "8", "WB01-WB08 (+ WB09 boundary)"], ["is_gate_available", "5", "5", "WB10-WB14"], ["compute_excess_fee", "3", "3", "WB15-WB17"],
    ], [2.4, 1.0, 2.4, 3.2], { caption: "Cyclomatic complexity and number of basis-path tests" }),
    ...Tbl(["ID", "Unit", "Path", "Test data", "Expected", "Result"], WB.map((r) => [...r, st(r[0])]),
      [0.7, 1.6, 2.0, 2.3, 2.3, 0.7], { caption: "White-box test cases (tests/test_whitebox.py)", size: 16, zebra: true }),
    H2("11.4 Unit Testing of Service Classes"),
    P("Each service class was tested as a unit against an in-memory database, covering normal behaviour, every business rule and role check."),
    ...Tbl(["ID", "Class", "Scenario", "Expected", "Result"], UT.map((r) => [...r, st(r[0])]),
      [0.7, 1.5, 3.6, 2.5, 0.7], { caption: "Unit test cases (tests/test_services.py)", size: 16, zebra: true }),
    H2("11.5 Test Results Summary"),
    ...Tbl(["Suite", "Test methods", "Passed", "Failed"], [
      ["Black-box (BB)", String(n("BB").length), String(passed("BB")), String(n("BB").length - passed("BB"))],
      ["White-box (WB)", String(n("WB").length), String(passed("WB")), String(n("WB").length - passed("WB"))],
      ["Unit (UT)", String(n("UT").length), String(passed("UT")), String(n("UT").length - passed("UT"))],
      ["Total", SUMMARY[1] || "?", String(passed("")), String(Object.keys(STATUS).length - passed(""))],
    ], [3.0, 2.0, 2.0, 2.0], { caption: `Test summary (unittest: "Ran ${SUMMARY[1]} tests in ${SUMMARY[2]}s", result ${FINAL})` }),
    P("Several test methods check more than one input using `subTest` (e.g. BB08 checks 5 malformed seats), so the number of individual checks is larger than the number of methods."),
    P("**Statement coverage** of the non-GUI code, measured with the `coverage` tool while running all tests:"),
    ...Tbl(["File", "Statements", "Missed", "Cover", "Missed lines"], covRows, [3.2, 1.1, 0.9, 0.9, 2.9],
      { caption: "Statement coverage of the non-GUI code", size: 16 }),
    P("The GUI layer is excluded from coverage because it is tested manually (system testing through the screenshots in Section 10.5). Most uncovered lines are secondary error branches (e.g. 'Unknown flight status', 'User not found') and the retry-exhausted branch of PNR generation."),
    H2("11.6 How to Run the Tests"),
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
      ["Payment is not processed; the fare is only recorded.", "Integrate a payment gateway; add refunds on cancellation."],
      ["Boarding passes and bag tags are shown on screen, not printed.", "Generate PDF passes with a barcode/QR code; print bag tags."],
      ["Single-user desktop application with one SQLite file.", "Client-server version (web front end, PostgreSQL) for many counters."],
      ["One cabin class; fixed 6-abreast layout; fixed fare.", "Seat classes, aircraft types with layouts, dynamic pricing."],
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
    H1("13. Conclusion"),
    P("The Airport Management System was analysed, designed, implemented and tested following the iterative waterfall model. The function-oriented design (context diagram, balanced Level 1-3 DFDs, a data dictionary covering every flow, and structure charts from transaction and transform analysis) and the object-oriented design (use case, class, activity, state chart, sequence and collaboration diagrams) describe the same system with the same names, and both map directly onto the code."),
    P(`The working Tkinter + SQLite application implements all four modules with role-based access, input validation and clear error messages. Its layered structure gives high cohesion and low coupling, which made it possible to test every business rule without the GUI: ${SUMMARY[1]} automated black-box, white-box and unit tests pass, with ${(COV.find((r) => r[0] === "TOTAL") || [])[3]} statement coverage of the non-GUI code, and testing found and fixed one real defect in input validation.`),
  ];
}

function references() {
  return [
    H1("14. References"),
    ...Bullets([
      "Rajib Mall, Fundamentals of Software Engineering, 5th ed., PHI Learning.",
      "Roger S. Pressman, Software Engineering: A Practitioner's Approach, McGraw-Hill.",
      "IEEE Std 830-1998, IEEE Recommended Practice for Software Requirements Specifications.",
      "Python Software Foundation, Python 3 documentation: tkinter, sqlite3, unittest, hashlib.",
      "SQLite documentation: partial indexes, CHECK and foreign-key constraints (sqlite.org).",
      "Object Management Group, UML 2.5 specification (diagram notation).",
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
    H1("Appendix B. Setup and Run Instructions"),
    ...Bullets(["Install Python 3.9 or newer from python.org (Tkinter and SQLite are included). Nothing else is needed to run the program."]),
    ...Code(["cd AirportMS", "python run.py --reset      # create fresh sample data and start", "python run.py              # start with the existing data",
      "python init_db.py --reset  # only (re)create the database", "run.bat                    # Windows: double-click to start"]),
    ...Tbl(["Role", "Username", "Password"], [["Administrator", "admin", "admin123"], ["Check-in staff", "staff1 / staff2", "staff123"],
      ["Passenger", "priya / rahul / sneha", "pass1234"]], [3, 3, 3], { caption: "Demo accounts" }),
    H2("Suggested demonstration (about 5 minutes)"),
    ...Bullets([
      "**admin**: Flights tab - add a flight with gate Z9 to show validation; add a valid one; assign a gate already in use to show the clash rule; set status DELAYED; cancel a flight and see its bookings cancelled.",
      "**priya**: search DEL, select a flight, pick a seat on the seat map, confirm and note the PNR; cancel a booking.",
      "**staff1**: Check-in tab - PNR K7Q2MA, check in (boarding pass), add bags of 17.5 and 4 kg (fee Rs 3500), try 40 kg (error), set a bag to LOADED. Try PNR H2N6YE to show 'check-in opens 48 hours before departure'.",
      "**priya**: Boarding Pass tab shows the pass.",
      "Run `python -m unittest discover -s tests -t . -v` to show 76 passing tests.",
    ]),
  ];
}

module.exports = { ch10, ch11, ch12, ch13, references, appendixA, appendixB };
