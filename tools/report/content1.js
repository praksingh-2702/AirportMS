// Chapters 1-6: introduction, abstraction & decomposition, life cycle, SRS, formal specification, cohesion & coupling
const L = require("./lib");
const { H1, H2, H3, P, Bullets, Code, Img, Tbl, KV, setChapter } = L;

const REQUIREMENTS = require("./requirements");

function ch1() {
  setChapter(1);
  return [
    H1("1. Introduction"),
    H2("1.1 Problem Statement"),
    P("An airport handles a large number of flights, passengers and bags every day. Flight schedules change, gates must be allocated without clashes, passengers need to find flights and reserve seats, and check-in counters must verify bookings, issue boarding passes and track every checked bag. When these activities are handled with spreadsheets or paper registers, the same seat can be sold twice, two flights can be given the same gate, and a bag's whereabouts can be lost."),
    P("The **Airport Management System (AMS)** developed in this mini-project is a desktop application that keeps flights, bookings and baggage in one consistent database and gives each type of user (administrator, check-in staff and passenger) exactly the functions they need."),
    H2("1.2 Objectives"),
    ...Bullets([
      "Analyse the problem using both the **Function-Oriented Design** approach (Structured Analysis + Structured Design) and the **Object-Oriented Design** approach (UML).",
      "Write a complete **Software Requirements Specification (SRS)** and formal (algebraic and axiomatic) specifications for key operations.",
      "Implement a working GUI application in **Python (Tkinter) with SQLite**, organised into modules with high cohesion and low coupling.",
      "Verify the implementation with **black-box**, **white-box** and **unit tests** that can be run locally, and report their real results.",
    ]),
    H2("1.3 Scope of the System"),
    P("The system covers four modules:"),
    ...Tbl(["Module", "What it does", "Main user"], [
      ["M1  Login & Accounts", "Login/logout, passenger self-registration, admin creates staff/admin accounts, role-based access control.", "All users"],
      ["M2  Flight Scheduling", "Add, update, view and cancel flights; change flight status; assign gates with a clash check.", "Administrator"],
      ["M3  Passenger Booking", "Search flights, choose a seat on a seat map, book and cancel tickets, view bookings.", "Passenger"],
      ["M4  Check-in & Baggage", "Find booking by PNR, check in, issue boarding pass, add bags with tags, compute excess-baggage fee, track bag status.", "Check-in staff"],
    ], [2.2, 5.5, 1.6], { caption: "Modules of the Airport Management System" }),
    P("Payments, airline-to-airline messaging, e-mail/SMS notifications and physical printing are outside the scope of this lab project (see Section 4.9 and Chapter 12)."),
    H2("1.4 Technology Used"),
    ...Tbl(["Item", "Choice", "Reason"], [
      ["Language", "Python 3.9+", "Readable, quick to develop, standard library has everything needed."],
      ["GUI", "Tkinter / ttk", "Ships with Python on Windows/macOS; no installation needed for the lab demo."],
      ["Database", "SQLite 3 (file data/airport.db)", "Serverless, single file, supports SQL constraints and transactions."],
      ["Testing", "unittest (+ optional coverage)", "Standard library; tests run with one command."],
      ["Diagrams", "Graphviz (DFDs, structure charts, CFGs, use case, collaboration), PlantUML (class, activity, state, sequence)", "Diagrams are generated from text, so names stay consistent with the code."],
    ], [1.4, 3.2, 4.4]),
    H2("1.5 Organisation of this Report"),
    P("Chapters 2-4 cover analysis (abstraction, life-cycle model, SRS). Chapter 5 gives formal specifications. Chapter 6 discusses cohesion and coupling. Chapters 7 and 8 form the **Function-Oriented Design (FOD = SA + SD)**: DFDs and data dictionary, then structure charts. Chapter 9 is the **Object-Oriented Design**. Chapter 10 describes the implementation and GUI, Chapter 11 the testing, and Appendix A gives a traceability matrix linking every requirement to its DFD process, use case, code and tests."),
  ];
}

function ch2() {
  setChapter(2);
  return [
    H1("2. Abstraction and Decomposition"),
    P("Software engineering handles complexity with two principles. **Abstraction** means concentrating on the aspects of a problem that matter at a given level and ignoring irrelevant details. **Decomposition** means dividing a large problem into smaller, mostly independent sub-problems that can be solved one at a time and then combined."),
    H2("2.1 Abstraction in the AMS"),
    ...Tbl(["Kind of abstraction", "Where it is used in the AMS"], [
      ["Functional (procedural) abstraction", "Each service method hides its steps behind one name, e.g. `check_in(actor, pnr)` hides the PNR lookup, the eligibility rules, the boarding-sequence update and the boarding-pass creation."],
      ["Data abstraction", "Entity classes `User`, `Flight`, `Booking`, `Bag`, `BoardingPass` expose only their fields; how they are stored (SQL rows) is hidden in `from_row()`."],
      ["Control abstraction", "Flight and bag life cycles are expressed as transition tables (`FLIGHT_TRANSITIONS`, `BAG_TRANSITIONS`); callers just request a new status."],
      ["Levels of DFD", "The context diagram shows the whole system as one process; Level 1 shows 6 processes; Level 2 and 3 add detail only where it is needed."],
      ["Layering", "GUI views know nothing about SQL; services know nothing about Tkinter; validators know nothing about either."],
    ], [2.4, 6.6], { caption: "Abstraction mechanisms used" }),
    H2("2.2 Decomposition of the AMS"),
    P("The system was decomposed top-down: first into four modules (one per user goal), then each module into functions small enough to implement and test as one unit. Figure 2.1 shows the decomposition tree; Table 2.2 maps each part to its source file."),
    ...Img("docs/diagrams/decomposition.png", "Functional decomposition of the Airport Management System", { maxH: 700 }),
    ...Tbl(["Module", "Functions (service methods)", "Source file"], [
      ["Login & Accounts", "login, register_passenger, create_staff_account, list_users", "ams/services/auth_service.py"],
      ["Flight Scheduling", "add_flight, update_flight, is_gate_available, assign_gate, change_status, cancel_flight", "ams/services/flight_service.py"],
      ["Passenger Booking", "search_flights, get_taken_seats, book_ticket, cancel_booking, list_bookings", "ams/services/booking_service.py"],
      ["Check-in & Baggage", "find_booking, check_in, get_boarding_pass, add_bag, baggage_summary, update_bag_status, compute_excess_fee", "ams/services/checkin_service.py"],
      ["Shared utilities", "validation, role check, password hashing, entity classes, schema", "validators.py, access.py, security.py, models.py, database.py"],
    ], [1.7, 4.5, 2.8], { caption: "Decomposition mapped to the source code" }),
  ];
}

function ch3() {
  setChapter(3);
  return [
    H1("3. Software Development Life-Cycle Models"),
    P("A **software life-cycle model** is a descriptive and diagrammatic representation of the life cycle of a software product: the phases it passes through and the order in which they are carried out. Following a model makes the work disciplined, defines entry and exit criteria for each phase, and lets progress be measured."),
    H2("3.1 Common Life-Cycle Models"),
    ...Tbl(["Model", "Key idea", "Strengths", "Weaknesses"], [
      ["Classical Waterfall", "Phases in strict sequence: feasibility, requirements, design, coding & unit testing, integration & system testing, maintenance.", "Simple; clear documents at every phase.", "No way to go back to fix errors found later; unrealistic."],
      ["Iterative Waterfall", "Waterfall with feedback paths from every phase to earlier ones.", "Errors can be corrected where they were made; still document-driven; easy to manage.", "Requirements still fixed early; no working product until late."],
      ["Prototyping", "Build a quick throw-away prototype to clarify unclear requirements, then develop as waterfall.", "Good when the user interface or requirements are unclear.", "Extra cost of the prototype."],
      ["Incremental / Evolutionary", "Deliver the system in increments, each adding features.", "Early partial product; customer feedback.", "Needs a modular design; integration overhead."],
      ["Spiral", "Loops of objective setting, risk analysis, development and planning.", "Explicit risk handling; good for large risky projects.", "Complex; needs risk-analysis expertise."],
      ["Agile (Scrum/XP)", "Short iterations, working software over documents, continuous customer involvement.", "Handles changing requirements well.", "Less documentation; needs an always-available customer."],
    ], [1.5, 2.9, 2.3, 2.3], { caption: "Comparison of life-cycle models", size: 18 }),
    H2("3.2 Selected Model: Iterative Waterfall"),
    ...Img("docs/diagrams/lifecycle_iterative_waterfall.png", "Iterative waterfall model followed in this project (dashed arrows are feedback paths)", { maxH: 480 }),
    P("**Justification.** The iterative waterfall model was chosen for the following reasons:"),
    ...Bullets([
      "**Requirements are well understood and stable.** Airport operations (scheduling, booking, check-in, baggage) are familiar, and the lab brief fixes the scope, so a heavy prototyping or risk-driven model is not needed.",
      "**The lab deliverable is document-centred.** The evaluation needs an SRS, SA/SD and OOD documents, which map naturally onto the separate phases of the waterfall model.",
      "**Feedback was actually needed.** Two examples: (1) while drawing the Level-2 DFDs, three store reads were found missing from Level 1, so the analysis was revised (an automatic balancing check now catches this); (2) black-box test BB20 found that the flight-number rule accepted an all-digit airline code, so the validator in the coding phase was corrected. The iterative model allows exactly this kind of going back.",
      "**Small team, short time, low risk.** The spiral model's risk analysis and agile's continuous customer involvement add overhead that does not pay off for a 3-4 week lab project.",
    ]),
    H2("3.3 Phases as Carried Out"),
    ...Tbl(["Phase", "Activities in this project", "Output"], [
      ["Feasibility study", "Checked that Python + Tkinter + SQLite can run on lab PCs without installation; estimated effort.", "Decision to build a desktop app."],
      ["Requirements analysis & specification", "Identified actors and functions; wrote numbered functional and non-functional requirements.", "SRS (Chapter 4)"],
      ["Design", "SA: context diagram, DFDs, data dictionary. SD: structure charts. OOD: UML diagrams. Formal specs.", "Chapters 5-9"],
      ["Coding & unit testing", "Implemented validators, services and GUI; wrote black-box, white-box and unit tests.", "Source code, tests"],
      ["Integration & system testing", "Ran the GUI for every role end-to-end; captured screenshots.", "Chapter 10-11"],
      ["Maintenance", "README with setup instructions; limitations and future scope recorded.", "README, Chapter 12"],
    ], [2.0, 4.8, 2.2]),
  ];
}

function ch4() {
  setChapter(4);
  const reqBlocks = [];
  for (const mod of REQUIREMENTS) {
    reqBlocks.push(H3(mod.title));
    for (const r of mod.items) {
      reqBlocks.push(...KV([
        ["Requirement", `**${r.id} ${r.name}**`],
        ["Description", r.desc],
        ["Input", r.input],
        ["Output", r.output],
        ["Processing / rules", r.rules],
      ]));
    }
  }
  return [
    H1("4. Software Requirements Specification (SRS)"),
    P("This SRS follows the structure recommended by IEEE Std 830-1998. Requirements are numbered so that they can be traced to DFD processes, use cases, code and test cases (Appendix A)."),
    H2("4.1 Introduction"),
    H3("4.1.1 Purpose"),
    P("This document specifies the requirements of the Airport Management System (AMS). It is intended for the development team, the lab instructor who evaluates the project, and anyone who will test or maintain the software."),
    H3("4.1.2 Scope"),
    P("AMS is a single-site desktop application used at an airport to schedule flights and gates, let passengers book and cancel seats, and let check-in staff check passengers in and manage baggage. It stores all data in a local SQLite database. It does not process payments or communicate with external airline systems."),
    H3("4.1.3 Definitions, Acronyms and Abbreviations"),
    ...Tbl(["Term", "Meaning"], [
      ["AMS", "Airport Management System (this software)"],
      ["PNR", "Passenger Name Record: a 6-character booking reference, e.g. K7Q2MA"],
      ["IATA code", "3-letter airport code, e.g. DEL (Delhi), BOM (Mumbai)"],
      ["Gate", "Boarding gate, written as terminal letter A-D and number 1-20, e.g. B7"],
      ["Boarding sequence", "Order in which passengers of a flight were checked in (001, 002, ...)"],
      ["Bag tag", "Unique bag identifier printed at check-in, format AMSnnnnnn"],
      ["Excess baggage fee", "Charge for checked baggage above the free allowance"],
      ["Admin / Staff / Passenger", "The three user roles"],
      ["SA / SD / FOD / OOD", "Structured Analysis / Structured Design / Function-Oriented Design / Object-Oriented Design"],
    ], [2.0, 7.0]),
    H3("4.1.4 References"),
    ...Bullets(["IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications.",
      "Rajib Mall, Fundamentals of Software Engineering, PHI Learning.", "Python 3 documentation: tkinter, sqlite3, unittest."]),
    H3("4.1.5 Overview"),
    P("Section 4.2 describes the product in general terms. Section 4.3 lists the functional requirements module by module. Sections 4.4-4.6 cover interfaces, non-functional requirements and business rules. Section 4.7 gives the data requirements and Section 4.8 separates implemented features from limitations."),

    H2("4.2 Overall Description"),
    H3("4.2.1 Product Perspective"),
    P("AMS is a new, self-contained product. It is organised in three layers: a Tkinter presentation layer, a service layer that holds all business rules, and an SQLite data layer. The context diagram in Section 7.1 shows its interaction with the three external entities (Passenger, Check-in Staff, Administrator)."),
    H3("4.2.2 Product Functions"),
    ...Bullets([
      "Authenticate users and show a role-specific dashboard; let passengers register; let the administrator create staff accounts.",
      "Maintain the flight schedule: add, update, change status, cancel, and assign gates without clashes.",
      "Let passengers search flights, pick a seat on a seat map, book (receive a PNR) and cancel bookings.",
      "Let staff check passengers in within the check-in window, issue boarding passes, tag bags, show the excess-baggage fee and track bag status.",
    ]),
    H3("4.2.3 User Classes and Characteristics"),
    ...Tbl(["User class", "Characteristics", "Functions allowed"], [
      ["Administrator", "Airport operations staff; trained; few users.", "All flight-scheduling functions; create staff/admin accounts; view users and all bookings; cancel any booking; check-in functions."],
      ["Check-in Staff", "Counter staff; trained; frequent daily use; speed matters.", "Check-in, boarding pass, baggage; view schedule and all bookings (read-only)."],
      ["Passenger", "General public; no training; occasional use.", "Register, search, book and cancel own bookings, view own boarding pass, view schedule."],
    ], [1.6, 3.0, 4.4], { caption: "User classes" }),
    H3("4.2.4 Operating Environment"),
    ...Bullets(["Windows 10/11, macOS or Linux with Python 3.9 or newer (Tkinter and sqlite3 included).",
      "Minimum 1366 x 768 screen; the main window is 1100 x 700 and resizable.", "No network connection is required."]),
    H3("4.2.5 Design and Implementation Constraints"),
    ...Bullets(["Only the Python standard library may be used at run time (lab PCs may not allow installing packages).",
      "Single-user desktop application: one SQLite file is accessed by one running instance at a time.",
      "Times are local time in the format YYYY-MM-DD HH:MM; time zones are not modelled."]),
    H3("4.2.6 Assumptions and Dependencies"),
    ...Bullets(["The computer clock is correct (check-in window rules depend on it).",
      "Every aircraft has 6 seats per row (A-F) and a single cabin class.",
      "A passenger books one seat per booking and at most one active booking per flight.",
      "Fares are recorded but payment happens outside the system."]),

    H2("4.3 Functional Requirements"),
    P("Each requirement lists its input, output and processing rules. Requirement IDs (R1.x - R4.x) are used in the traceability matrix in Appendix A."),
    ...reqBlocks,

    H2("4.4 External Interface Requirements"),
    ...Tbl(["Interface", "Requirement"], [
      ["User interface", "Single window with a login screen and a tabbed dashboard. Tables list records; forms have labelled fields with the expected format shown in the label; every error is shown in a dialog with a message that says what to correct. Destructive actions (cancel flight/booking) ask for confirmation."],
      ["Hardware interface", "Keyboard and mouse. No printer/scanner integration; the boarding pass and bag tag are displayed on screen."],
      ["Software interface", "SQLite 3 database file `data/airport.db` created automatically on first run."],
      ["Communication interface", "None."],
    ], [2.0, 7.0]),
    H2("4.5 Non-Functional Requirements"),
    ...Tbl(["ID", "Category", "Requirement"], [
      ["NF1", "Performance", "Any screen action (search, book, check-in) completes in under 1 second for the sample data size (hundreds of records)."],
      ["NF2", "Security", "Passwords are never stored in plain text; PBKDF2-HMAC-SHA256 with a random 16-byte salt and 100,000 iterations is used."],
      ["NF3", "Security", "Every data-changing service operation checks the caller's role (not only the GUI), so a hidden button cannot be bypassed."],
      ["NF4", "Security", "Login gives the same message for an unknown username and a wrong password."],
      ["NF5", "Reliability / integrity", "Database constraints back up the service rules: CHECK constraints on statuses, rows, fare and bag weight; a partial UNIQUE index prevents two active bookings for the same seat; foreign keys are enforced."],
      ["NF6", "Usability", "Error messages state the rule that was broken and the expected format, e.g. 'Seat must be a row number followed by a letter, e.g. 12C.'"],
      ["NF7", "Maintainability", "Business limits live in one file (`config.py`); services are independent of the GUI; code is split into modules of one responsibility each."],
      ["NF8", "Testability", "All business rules are reachable without the GUI and accept an injectable clock (`now`), so tests are repeatable."],
      ["NF9", "Portability", "Runs unchanged on Windows, macOS and Linux with standard Python."],
    ], [0.7, 1.8, 6.5], { caption: "Non-functional requirements" }),
    H2("4.6 Business Rules"),
    ...Tbl(["Rule", "Value", "Defined in"], [
      ["Seats per row / rows per flight", "6 (A-F) / 1-40", "config.SEAT_COLUMNS, MAX_ROWS"],
      ["Minimum gap between two active flights at one gate", "60 minutes", "config.GATE_BUFFER_MINUTES"],
      ["Maximum flight duration", "20 hours", "config.MAX_FLIGHT_HOURS"],
      ["Fare range", "Rs 500 - Rs 2,00,000", "config.MIN_FARE, MAX_FARE"],
      ["Check-in window", "opens 48 h, closes 45 min before departure", "config.CHECKIN_OPENS_HOURS, CHECKIN_CLOSES_MINUTES"],
      ["Boarding time on pass", "30 min before departure", "config.BOARDING_BEFORE_MINUTES"],
      ["Bags per booking / max bag weight", "3 / 32 kg", "config.MAX_BAGS_PER_BOOKING, MAX_BAG_WEIGHT_KG"],
      ["Free baggage allowance / excess rate", "15 kg / Rs 500 per started kg", "config.FREE_BAGGAGE_KG, EXCESS_RATE_PER_KG"],
      ["Bookable flight statuses", "SCHEDULED, DELAYED", "booking_service.BOOKABLE_STATUSES"],
    ], [3.6, 2.6, 2.8], { caption: "Business rules and where they are implemented" }),
    H2("4.7 Data Requirements"),
    P("The database has four tables, which are exactly the four data stores D1-D4 of the DFDs."),
    ...Tbl(["Table (store)", "Key columns", "Constraints"], [
      ["users (D1)", "user_id PK, username UNIQUE, password_hash, salt, role, full_name, email, phone, created_at", "role IN (ADMIN, STAFF, PASSENGER)"],
      ["flights (D2)", "flight_id PK, flight_no, airline, origin, destination, departure, arrival, gate, rows, fare, status", "UNIQUE(flight_no, departure); rows 1-40; fare > 0; status enum"],
      ["bookings (D3)", "booking_id PK, pnr UNIQUE, user_id FK, flight_id FK, seat, fare, status, booked_at, checked_in_at, boarding_seq", "UNIQUE(flight_id, seat) WHERE status <> 'CANCELLED'; status enum"],
      ["baggage (D4)", "bag_id PK, booking_id FK, tag_no UNIQUE, weight_kg, status, updated_at", "0 < weight_kg <= 32; status enum"],
    ], [1.5, 4.6, 2.9], { caption: "Database tables" }),
    H2("4.8 Implemented Features and Limitations"),
    P("**Implemented and demonstrated:** all functional requirements R1.1-R4.6 above, all non-functional requirements NF1-NF9, realistic sample data (6 users, 8 flights, 8 bookings, 2 bags), and 76 automated tests."),
    P("**Not implemented (out of scope):** online payment and refunds, e-mail/SMS notifications, physical printing of boarding passes and bag tags, multi-terminal network access, seat classes and dynamic pricing, connecting flights, password reset, audit log, and time-zone handling. These are listed again as future scope in Chapter 12."),
  ];
}

function ch5() {
  setChapter(5);
  return [
    H1("5. Formal Specification"),
    P("A formal specification describes what a system must do using mathematical notation, so that it is precise and can be checked for consistency and completeness. Two styles are used here: **algebraic specification** (an abstract data type defined by its operations and the axioms relating them) and **axiomatic specification** (each function defined by a pre-condition and a post-condition)."),
    H2("5.1 Algebraic Specification"),
    P("An algebraic specification has four sections: **types** (the sort being defined and the sorts it uses), **exceptions**, **syntax** (operation signatures) and **equations** (axioms). Operations are classified as basic constructors (build every value), extra constructors, and inspectors (return a value of another sort). Equations are written for each inspector and extra constructor applied to each basic constructor, which makes the specification complete."),
    H3("5.1.1 ADT SeatAllocation (seats held on one flight)"),
    P("**Assumptions:** a `Seat` value is already valid for the aircraft (checked by `parse_seat`); `n` is the capacity (rows x 6). Equality on seats is string equality (e.g. 12C)."),
    ...Code([
      "Types:",
      "   defines  SeatAllocation",
      "   uses     Seat, Integer, Boolean",
      "Exceptions:",
      "   SEAT_TAKEN, FLIGHT_FULL",
      "Syntax:",
      "   create   : Integer                 -> SeatAllocation            (basic constructor)",
      "   book     : SeatAllocation x Seat   -> SeatAllocation + {SEAT_TAKEN, FLIGHT_FULL}  (basic constructor)",
      "   cancel   : SeatAllocation x Seat   -> SeatAllocation            (extra constructor)",
      "   isTaken  : SeatAllocation x Seat   -> Boolean                   (inspector)",
      "   count    : SeatAllocation          -> Integer                   (inspector)",
      "   capacity : SeatAllocation          -> Integer                   (inspector)",
      "   free     : SeatAllocation          -> Integer                   (inspector)",
      "Equations:   (a : SeatAllocation;  s, t : Seat;  n : Integer)",
      "   1.  isTaken(create(n), t)   = false",
      "   2.  isTaken(book(a, s), t)  = if s = t then true else isTaken(a, t)",
      "   3.  count(create(n))        = 0",
      "   4.  count(book(a, s))       = count(a) + 1",
      "   5.  capacity(create(n))     = n",
      "   6.  capacity(book(a, s))    = capacity(a)",
      "   7.  free(a)                 = capacity(a) - count(a)",
      "   8.  book(a, s)              = SEAT_TAKEN   if isTaken(a, s)",
      "   9.  book(a, s)              = FLIGHT_FULL  if count(a) = capacity(a)",
      "  10.  cancel(create(n), t)    = create(n)",
      "  11.  cancel(book(a, s), t)   = if s = t then a else book(cancel(a, t), s)",
    ]),
    P("**Mapping to the code:** `get_taken_seats(flight_id)` returns the set represented by the allocation; `book_ticket` implements `book` (raising `BusinessRuleError` for SEAT_TAKEN); `cancel_booking` implements `cancel`; `search_flights` reports `free` as 'Seats left'. Equation 8 is additionally enforced by the database index `ux_active_seat`. FLIGHT_FULL cannot arise separately in the code because a full flight has no free seat to select, so equation 9 is always reached through equation 8."),
    H3("5.1.2 ADT BagList (checked bags of one booking)"),
    P("**Assumptions:** weights are real numbers in kg; the free allowance is 15 kg and the excess rate Rs 500 per started kg; `ceil` rounds up to an integer."),
    ...Code([
      "Types:",
      "   defines  BagList",
      "   uses     Real, Integer",
      "Exceptions:",
      "   TOO_MANY_BAGS, INVALID_WEIGHT",
      "Syntax:",
      "   create      :                -> BagList                                 (basic constructor)",
      "   addBag      : BagList x Real -> BagList + {TOO_MANY_BAGS, INVALID_WEIGHT} (basic constructor)",
      "   bagCount    : BagList        -> Integer                                 (inspector)",
      "   totalWeight : BagList        -> Real                                    (inspector)",
      "   excessFee   : BagList        -> Integer                                 (inspector)",
      "Equations:   (b : BagList;  w : Real)",
      "   1.  bagCount(create())       = 0",
      "   2.  bagCount(addBag(b, w))   = bagCount(b) + 1",
      "   3.  totalWeight(create())    = 0",
      "   4.  totalWeight(addBag(b, w))= totalWeight(b) + w",
      "   5.  addBag(b, w)             = INVALID_WEIGHT  if w <= 0 or w > 32",
      "   6.  addBag(b, w)             = TOO_MANY_BAGS   if bagCount(b) = 3",
      "   7.  excessFee(b)             = 0                                if totalWeight(b) <= 15",
      "   8.  excessFee(b)             = 500 * ceil(totalWeight(b) - 15)  if totalWeight(b) > 15",
    ]),
    P("**Mapping to the code:** `add_bag` (with `validate_bag_weight`) implements `addBag`; `baggage_summary` returns (`totalWeight`, `excessFee`); `compute_excess_fee` implements equations 7-8. Example: bags of 17.5 kg and 4.0 kg give totalWeight = 21.5 and excessFee = 500 x ceil(6.5) = Rs 3,500 (verified by tests UT31 and WB17)."),
    H2("5.2 Axiomatic Specification"),
    P("In axiomatic specification each operation is described by a **pre-condition** (what must hold before it is called) and a **post-condition** (what holds after it returns). A primed name (b') denotes the value after the operation. If the pre-condition is false, the implementation raises an exception instead of changing the state."),
    P("**Assumptions used below:** `Bookings`, `Flights`, `Bags` are the sets of records in D3, D2, D4; `flight(b)` is the flight of booking b; `dep(f)` is its departure time; `now` is the current time; `max` of an empty set is 0."),
    ...KV([
      ["Function", "**book_ticket(actor, f, s, now) : Booking**"],
      ["Pre-condition", ["actor.role = PASSENGER  AND  f IN Flights  AND  f.status IN {SCHEDULED, DELAYED}  AND  dep(f) > now",
        "AND  s = r.c with 1 <= r <= f.rows, c IN {A..F}",
        "AND  NOT EXISTS b IN Bookings : b.flight = f AND b.seat = s AND b.status <> CANCELLED",
        "AND  NOT EXISTS b IN Bookings : b.flight = f AND b.user = actor AND b.status <> CANCELLED"]],
      ["Post-condition", ["Bookings' = Bookings UNION {b}  where  b.user = actor, b.flight = f, b.seat = s, b.fare = f.fare, b.status = BOOKED, b.booked_at = now",
        "AND  b.pnr is 6 characters  AND  NOT EXISTS x IN Bookings : x.pnr = b.pnr  AND  result = b"]],
    ], "Axiomatic specification of book_ticket"),
    ...KV([
      ["Function", "**check_in(actor, p, now) : BoardingPass**"],
      ["Pre-condition", ["actor.role IN {STAFF, ADMIN}  AND  EXISTS b IN Bookings : b.pnr = p  AND  b.status = BOOKED",
        "AND  flight(b).status NOT IN {CANCELLED, DEPARTED}",
        "AND  dep(flight(b)) - 48 h  <=  now  <=  dep(flight(b)) - 45 min"]],
      ["Post-condition", ["b'.status = CHECKED_IN  AND  b'.checked_in_at = now",
        "AND  b'.boarding_seq = max{ x.boarding_seq | x IN Bookings, x.flight = flight(b) } + 1",
        "AND  result.seat = b.seat  AND  result.gate = flight(b).gate  AND  result.boarding_time = dep(flight(b)) - 30 min",
        "AND  all other bookings are unchanged"]],
    ], "Axiomatic specification of check_in"),
    ...KV([
      ["Function", "**compute_excess_fee(w) : Integer**"],
      ["Pre-condition", "w >= 0"],
      ["Post-condition", ["(w <= 15  AND  result = 0)  OR  (w > 15  AND  result = 500 * ceil(w - 15))"]],
    ], "Axiomatic specification of compute_excess_fee"),
    ...KV([
      ["Function", "**assign_gate(actor, f, g) : Flight**"],
      ["Pre-condition", ["actor.role = ADMIN  AND  f IN Flights  AND  f.status NOT IN {DEPARTED, CANCELLED}  AND  g matches [A-D](1..20)",
        "AND  NOT EXISTS x IN Flights : x <> f  AND  x.gate = g  AND  x.status IN {SCHEDULED, DELAYED, BOARDING}  AND  |dep(x) - dep(f)| < 60 min"]],
      ["Post-condition", "f'.gate = g  AND  all other attributes of f and all other flights are unchanged"],
    ], "Axiomatic specification of assign_gate"),
    ...KV([
      ["Function", "**add_bag(actor, p, w, now) : Bag**"],
      ["Pre-condition", ["actor.role IN {STAFF, ADMIN}  AND  EXISTS b IN Bookings : b.pnr = p AND b.status = CHECKED_IN",
        "AND  flight(b).status NOT IN {CANCELLED, DEPARTED}  AND  0 < w <= 32",
        "AND  | { g IN Bags : g.booking = b } | < 3"]],
      ["Post-condition", ["Bags' = Bags UNION {g}  where  g.booking = b, g.weight = round(w, 1), g.status = CHECKED_IN, g.updated_at = now",
        "AND  g.tag_no = \"AMS\" + 6-digit g.bag_id  AND  result = g"]],
    ], "Axiomatic specification of add_bag"),
    ...KV([
      ["Function", "**cancel_booking(actor, b, now) : Booking**"],
      ["Pre-condition", ["actor.role IN {PASSENGER, ADMIN}  AND  (actor.role = ADMIN  OR  b.user = actor)",
        "AND  b.status = BOOKED  AND  dep(flight(b)) > now"]],
      ["Post-condition", "b'.status = CANCELLED  AND  seat b.seat becomes free on flight(b) (isTaken = false)"],
    ], "Axiomatic specification of cancel_booking"),
  ];
}

function ch6() {
  setChapter(6);
  return [
    H1("6. Cohesion and Coupling"),
    P("**Cohesion** measures how strongly the elements inside one module belong together; **coupling** measures how strongly one module depends on others. A good design has **high cohesion and low coupling**: each module does one well-defined job and talks to other modules through narrow, explicit interfaces. This makes modules easier to understand, test and change independently."),
    H2("6.1 Classification"),
    ...Tbl(["Cohesion (worst to best)", "Meaning"], [
      ["Coincidental", "Elements are unrelated."], ["Logical", "Elements do similar kinds of things (e.g. all output)."],
      ["Temporal", "Elements run at the same time (e.g. initialisation)."], ["Procedural", "Elements are steps of one procedure, operating on different data."],
      ["Communicational", "Elements operate on the same data."], ["Sequential", "Output of one element is input to the next."],
      ["Functional", "All elements contribute to one single function."],
    ], [2.5, 6.5]),
    ...Tbl(["Coupling (best to worst)", "Meaning"], [
      ["Data", "Modules exchange only elementary data items as parameters."], ["Stamp", "Modules exchange a composite data structure."],
      ["Control", "One module passes a flag that controls the other's logic."], ["Common", "Modules share global data."],
      ["Content", "One module modifies or jumps into another's internals."],
    ], [2.5, 6.5]),
    H2("6.2 Cohesion of AMS Modules"),
    ...Tbl(["Module", "Cohesion", "Justification"], [
      ["validators.py", "Functional (each function)", "Each function validates exactly one kind of field and returns the normalised value; no function depends on another's state."],
      ["security.py", "Functional", "Only password hashing and verification."],
      ["access.py", "Functional", "One function, `require_role`."],
      ["models.py", "Communicational (data abstraction)", "Entity classes and enums that describe the same domain data; no behaviour beyond conversions."],
      ["auth_service.py", "Communicational", "All operations act on user accounts (D1)."],
      ["flight_service.py", "Communicational", "All operations act on flights (D2) and gate allocation."],
      ["booking_service.py", "Communicational", "All operations act on bookings (D3) for passengers."],
      ["checkin_service.py", "Communicational / sequential", "Check-in, boarding pass and baggage all act on a checked-in booking; check_in's steps form a sequence (find -> verify -> assign -> pass)."],
      ["gui/*_view.py", "Functional per screen", "Each view handles one tab's widgets and forwards every action to a service."],
      ["database.py", "Communicational", "Schema creation and sample data for the same database."],
      ["config.py", "Logical (by design)", "Groups all business-rule constants so that each rule is changed in one place."],
    ], [1.8, 2.0, 5.2], { caption: "Cohesion analysis", size: 18 }),
    H2("6.3 Coupling between AMS Modules"),
    ...Img("docs/diagrams/module_coupling.png", "Module dependency (coupling) diagram: arrows point from the user of a module to the module used", { maxH: 560 }),
    ...Tbl(["Modules", "Coupling type", "How it is kept low"], [
      ["GUI views -> services", "Data / stamp", "Views call service methods with plain values (strings from the form, ids) and receive entity objects. Views never run SQL."],
      ["services -> validators", "Data", "Pass one raw value, get back one normalised value or a ValidationError."],
      ["services -> access", "Stamp", "Pass the `User` object; nothing else is shared."],
      ["services -> database", "Data (via SQL parameters)", "Every query uses `?` parameters; each service receives the connection in its constructor (dependency injection), so tests pass an in-memory database."],
      ["services <-> services", "None, except one", "Services do not call each other. CheckInService re-uses the `DETAILS_SQL` query constant from booking_service: a small stamp coupling accepted to avoid duplicating the join."],
      ["services -> GUI", "None", "Verified: no file in ams/services or the utility modules imports ams.gui. This is why every business rule can be unit-tested without a display."],
      ["Shared database tables", "Common (controlled)", "Bookings (D3) is written by BookingService (book/cancel), CheckInService (check-in) and FlightService (cascade on flight cancel). This is unavoidable shared data; it is controlled by database constraints and by keeping each kind of update in exactly one method."],
    ], [2.0, 1.6, 5.4], { caption: "Coupling analysis", size: 18 }),
    H2("6.4 Design Decisions that Raise Cohesion and Lower Coupling"),
    ...Bullets([
      "**Layered architecture** (GUI -> services -> data); dependencies only point downwards.",
      "**One service class per module**, each owning one main table.",
      "**Pure functions** for validation and fee calculation (no hidden state).",
      "**Dependency injection** of the database connection and of the clock (`now` parameter) and PNR generator.",
      "**Single source for constants** (`config.py`) instead of magic numbers spread across modules.",
      "**Exceptions instead of control flags:** services raise typed errors (`ValidationError`, `BusinessRuleError`, ...) rather than returning status codes that the caller must interpret, which avoids control coupling.",
    ]),
  ];
}

module.exports = { ch1, ch2, ch3, ch4, ch5, ch6 };
