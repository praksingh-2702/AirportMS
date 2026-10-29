// Chapters 7-9: Structured Analysis, Structured Design, Object-Oriented Design
const fs = require("fs");
const path = require("path");
const L = require("./lib");
const { H1, H2, H3, P, Bullets, Img, Tbl, KV, setChapter } = L;

const DD = JSON.parse(fs.readFileSync(path.join(L.ROOT, "docs", "data_dictionary.json"), "utf8"));

function ch7() {
  setChapter(7);
  const lvl2 = [
    ["1_0", "1.0 Manage Users & Authenticate"], ["2_0", "2.0 Schedule Flights"], ["3_0", "3.0 Search Flights"],
    ["4_0", "4.0 Book / Cancel Ticket"], ["5_0", "5.0 Check In Passenger"], ["6_0", "6.0 Manage Baggage"],
  ];
  const lvl2Notes = {
    "1_0": "1.1 and 1.2 both read existing usernames from D1 to reject duplicates before writing a new user record; 1.3 serves all three kinds of user; 1.4 is used only by the administrator.",
    "2_0": "2.1 validates the form, 2.2 checks the 60-minute gate rule against the gate schedule in D2 (it is used by both 2.3 and 2.4), 2.5 applies the state chart and hands cancellations to 2.6, which also updates bookings in D3.",
    "3_0": "Search is a pure read: 3.1 validates the criteria, 3.2 selects bookable future flights from D2 and 3.3 subtracts taken seats (D3) from capacity.",
    "4_0": "4.1 builds the seat map from D2 and D3; 4.2 re-checks the selected seat and the one-booking-per-flight rule; 4.3 produces a PNR not present in D3; 4.4 writes the booking. 4.5 cancels a booking.",
    "5_0": "5.2 is decomposed further in Level 3 (Figure 7.9). 5.3 reads the highest boarding sequence of the flight and writes the CHECKED_IN status.",
    "6_0": "6.1 checks the weight and bag count, 6.2 stores the bag and creates its tag, 6.3 sums the weights and applies the fee rule, 6.4 applies the bag state chart.",
  };
  const blocks = [];
  for (const [i, [file, title]] of lvl2.entries()) {
    blocks.push(H3(`7.3.${i + 1} Level 2: ${title}`));
    blocks.push(...Img(`docs/diagrams/dfd_level2_${file}.png`, `Level 2 DFD - decomposition of process ${title}`, { maxH: 600 }));
    blocks.push(P(lvl2Notes[file]));
  }
  return [
    H1("7. Structured Analysis (SA)"),
    P("Structured analysis models **what** the system does as a hierarchy of Data Flow Diagrams (DFDs), starting from the context diagram and refining each process until the processes are atomic (each can be implemented as a single, simple function). It is the first half of **Function-Oriented Design: FOD = SA + SD**."),
    P("**Notation used** (the same as in the reference case studies): yellow rectangle = external entity (repeated beside each process it interacts with, to avoid crossing lines); blue circle = process, numbered hierarchically; open-ended rectangle with D# = data store; labelled arrow = data flow."),
    ...Tbl(["Element", "Names used consistently in every diagram, in the code and in the data dictionary"], [
      ["External entities", "Passenger, Check-in Staff, Administrator"],
      ["Data stores", "D1 Users (table users), D2 Flights (table flights), D3 Bookings (table bookings), D4 Baggage (table baggage)"],
      ["Level-1 processes", "1.0 Manage Users & Authenticate, 2.0 Schedule Flights, 3.0 Search Flights, 4.0 Book / Cancel Ticket, 5.0 Check In Passenger, 6.0 Manage Baggage"],
    ], [2.0, 7.0], { caption: "DFD vocabulary" }),
    H2("7.1 Context Diagram (Level 0 DFD)"),
    P("The context diagram shows the whole system as a single process (bubble 0) and all data that crosses the system boundary."),
    ...Img("docs/diagrams/dfd_context_level0.png", "Context diagram (Level 0 DFD) of the Airport Management System", { maxH: 420 }),
    H2("7.2 Level 1 DFD"),
    P("Bubble 0 is decomposed into six processes (between 3 and 7, as recommended). Every flow to or from an external entity in Figure 7.1 appears in Figure 7.2 with the same name, so the two levels are **balanced**."),
    ...Img("docs/diagrams/dfd_level1.png", "Level 1 DFD", { maxH: 720 }),
    H2("7.3 Level 2 DFDs"),
    P("Each Level-1 process is decomposed in its own diagram. Dashed circles are not used here; all processes shown belong to the parent bubble. The flows entering and leaving each diagram are exactly those of the parent bubble in Level 1."),
    ...blocks,
    H2("7.4 Level 3 DFD: 5.2 Verify Check-in Eligibility"),
    P("Process 5.2 contains four independent rules, so it is decomposed once more. Each of 5.2.1-5.2.4 is a single comparison and corresponds to one decision node in the control-flow graph of `check_in` (Section 11.3); these are the **atomic** processes. Dashed circles 5.1 and 5.3 are the neighbouring processes from Level 2, shown only to make the inputs and outputs clear. The four rejection reasons together form the 'Booking details' error path of 5.2 at Level 2."),
    ...Img("docs/diagrams/dfd_level3_5_2.png", "Level 3 DFD - decomposition of 5.2 Verify Check-in Eligibility", { maxH: 330 }),
    P("Processes at Level 2 that are not decomposed further (for example 4.3 Generate PNR, 6.3 Compute Excess Fee) are already atomic: each maps to one short function in the code (`_unique_pnr`, `compute_excess_fee`)."),
    H2("7.5 Balancing"),
    P("A DFD is balanced when the data flowing into and out of a bubble equals the data flowing into and out of its child diagram. All DFDs are generated from one specification file (`tools/dfd_spec.py`), and the script `tools/make_dfds.py` checks balancing automatically: (a) the external flows of the context diagram equal those of Level 1, and (b) for each Level-1 bubble, the flows to entities and stores equal those of its Level-2 diagram. The final run reports **BALANCING: OK**. (During development this check found three store reads that had been drawn in Level 2 but not in Level 1; Level 1 was corrected.)"),
    H2("7.6 Data Dictionary"),
    P("The data dictionary defines every data flow and data store that appears in the DFDs. Notation: `=` is composed of, `+` and, `[a | b]` either a or b, `{x}` zero or more x, `(x)` optional x, `\"...\"` literal value. The script `tools/data_dictionary.py` verifies that every one of the " +
      `${DD.composite.length - 4} flow names and 4 stores in the DFDs is defined below and that no entry is unused.`),
    ...Tbl(["Name", "Composition", "Description"],
      DD.composite.map(([n, c, d]) => [`**${n}**`, c, d]), [2.0, 4.2, 2.8], { caption: "Data dictionary - data stores and data flows", size: 17, zebra: true }),
    ...Tbl(["Elementary item", "Type / domain", "Notes"], DD.elementary, [2.0, 4.2, 2.8],
      { caption: "Data dictionary - elementary data items", size: 17 }),
  ];
}

function ch8() {
  setChapter(8);
  return [
    H1("8. Structured Design (SD)"),
    P("Structured design transforms the DFD model into a **structure chart**: a hierarchy of modules showing which module calls which, and the parameters passed between them. The two strategies are **transform analysis** (for DFDs where data flows through input -> processing -> output) and **transaction analysis** (for DFDs where one input selects one of several processing paths)."),
    H2("8.1 Structure Chart Notation"),
    ...Tbl(["Symbol", "Meaning"], [
      ["Rectangle", "Module (a function or class method); the name of the implementing code is given in the box"],
      ["Arrow between modules", "Module invocation (the caller is above)"],
      ["○ name ↓ / ○ name ↑", "Data couple passed to the called module / returned to the caller"],
      ["● name ↑", "Control flag returned to the caller (e.g. eligible, seat_free)"],
      ["Diamond under a module", "Selection: the module calls exactly one of the modules below it (transaction centre)"],
    ], [2.6, 6.4], { caption: "Structure-chart notation" }),
    H2("8.2 Transaction Analysis"),
    P("After login, the dashboard receives the user and, depending on the role and the tab the user opens, starts one of several independent transactions. This is a **transaction-centred** flow: the transaction centre `show_dashboard(user)` (selected using `ROLE_TABS[user.role]`) dispatches to one of five transaction modules, each of which calls exactly one service. The steps followed were: (1) identify the transaction centre in the Level-1 DFD (the role/tab selection in front of processes 2.0-6.0); (2) draw one branch per transaction type; (3) factor each branch further using transform analysis (Sections 8.3-8.4)."),
    ...Img("docs/diagrams/structure_chart_transaction.png", "Structure chart from transaction analysis (top level)", { maxH: 520 }),
    H2("8.3 Transform Analysis of 5.0 Check In Passenger"),
    P("For DFD 5.0, the input, central-transform and output portions were identified as follows, and each became one first-level branch of the structure chart:"),
    ...Tbl(["Portion", "DFD processes", "Structure-chart modules"], [
      ["Afferent (input) branch", "5.1 Retrieve Booking (read PNR, validate, fetch from D1/D2/D3)", "Get Booking Details -> Read PNR, Validate PNR, Fetch Booking Row"],
      ["Central transform", "5.2 Verify Check-in Eligibility, 5.3 Assign Boarding Seq.", "Verify Eligibility, Assign Boarding Seq"],
      ["Efferent (output) branch", "5.4 Generate Boarding Pass", "Produce Boarding Pass -> Format Pass, Display Pass"],
    ], [2.0, 3.6, 3.4], { caption: "Transform analysis of DFD 5.0" }),
    ...Img("docs/diagrams/structure_chart_transform_checkin.png", "Structure chart from transform analysis of DFD 5.0", { maxH: 420 }),
    H2("8.4 Transform Analysis of 4.0 Book / Cancel Ticket (booking path)"),
    ...Tbl(["Portion", "DFD processes", "Structure-chart modules"], [
      ["Afferent branch", "4.1 Show Seat Map (selected seat), flight record from D2", "Get Valid Request -> Get Flight, Validate Seat"],
      ["Central transform", "4.2 Validate Booking, 4.3 Generate PNR", "Check Seat & Duplicate, Generate PNR"],
      ["Efferent branch", "4.4 Record Booking (write D3, confirmation)", "Record & Confirm -> Insert Booking, Show Confirmation"],
    ], [2.0, 3.6, 3.4], { caption: "Transform analysis of DFD 4.0" }),
    ...Img("docs/diagrams/structure_chart_transform_booking.png", "Structure chart from transform analysis of DFD 4.0", { maxH: 420 }),
    H2("8.5 Parameter (Variable) Passing"),
    P("The table lists the couples of the structure charts with the actual function signatures in the code. All couples are **data couples** except the two control flags, which in the code are realised as exceptions (a `False` flag becomes a raised `BusinessRuleError`) so that callers do not need to test flags."),
    ...Tbl(["Module (code)", "Parameters in (↓)", "Returned (↑)", "Couple type"], [
      ["AuthService.login(username, password)", "username, password", "User (role inside)", "Data / stamp"],
      ["AirportApp.show_dashboard(user)", "user", "-", "Stamp"],
      ["CheckInService.find_booking(pnr)", "pnr", "BookingDetails", "Data in, stamp out"],
      ["validators.validate_pnr(value)", "raw pnr string", "normalised pnr", "Data"],
      ["CheckInService.check_in(actor, pnr, now)", "actor, pnr, now", "BoardingPass", "Stamp"],
      ["(eligibility checks inside check_in)", "booking details, now", "eligible (flag; error if false)", "Control flag"],
      ["CheckInService.get_boarding_pass(actor, pnr)", "actor, pnr", "BoardingPass", "Stamp"],
      ["BoardingPass.as_text()", "-", "pass text", "Data"],
      ["BookingService.book_ticket(actor, flight_id, seat, now)", "actor, flight_id, seat, now", "Booking", "Stamp"],
      ["validators.parse_seat(value, rows)", "seat, rows", "seat", "Data"],
      ["BookingService.get_taken_seats(flight_id)", "flight_id", "set of seats", "Data"],
      ["BookingService._unique_pnr()", "-", "pnr", "Data"],
      ["FlightService.is_gate_available(gate, departure, exclude_flight_id)", "gate, departure, flight id", "bool (gate_free)", "Control flag"],
      ["CheckInService.add_bag(actor, pnr, weight, now)", "actor, pnr, weight, now", "Bag", "Stamp"],
      ["compute_excess_fee(total_weight_kg)", "total weight", "fee", "Data"],
    ], [3.8, 2.2, 1.9, 1.1], { caption: "Parameter passing between modules", size: 17 }),
  ];
}

const USE_CASES = [
  { id: "UC01", name: "Login", actors: "User (Passenger, Check-in Staff, Administrator)",
    pre: "The user has an account. The login screen is shown.",
    post: "Success: the role dashboard is shown and the user is stored in the application context. Failure: the user stays on the login screen.",
    main: ["User enters username and password and clicks Login (or presses Enter).", "System looks up the username (case-insensitive) in D1 Users.",
      "System verifies the password against the stored salted hash.", "System builds the tabs for the user's role and shows the dashboard."],
    alt: ["1a. A field is blank: 'Enter both username and password.'", "2a/3a. Unknown username or wrong password: 'Invalid username or password.' (same message in both cases)."] },
  { id: "UC03", name: "Register Account", actors: "Passenger",
    pre: "Login screen is shown.", post: "A PASSENGER account exists; the username is filled in on the login screen.",
    main: ["Passenger clicks 'New passenger? Register'.", "Passenger enters username, full name, password twice, e-mail and mobile number and clicks Register.",
      "System validates every field and checks that the username is unused.", "System stores the user with a hashed password and confirms."],
    alt: ["2a. Passwords differ: 'Passwords do not match.'", "3a. A field is invalid: field-specific message (e.g. 'Phone must be a 10-digit mobile number starting with 6-9.')",
      "3b. Username exists: 'Username ... is already taken.'"] },
  { id: "UC06", name: "Search Flights", actors: "Passenger",
    pre: "Passenger is logged in.", post: "Matching flights are listed with seats left.",
    main: ["Passenger optionally enters From, To and Date and clicks Search.", "System validates the criteria.",
      "System selects SCHEDULED/DELAYED flights departing in the future that match.", "System shows each flight with fare and seats left."],
    alt: ["2a. Invalid code or date: e.g. 'Date must be in YYYY-MM-DD format, e.g. 2026-11-05.'", "3a. No match: the table is empty."] },
  { id: "UC07", name: "Book Ticket", actors: "Passenger", includes: "UC08 Select Seat",
    pre: "Passenger is logged in and has searched for flights.", post: "A booking with status BOOKED and a unique PNR exists; the seat is no longer free.",
    main: ["Passenger selects a flight and clicks 'Book selected flight'.", "System shows the seat map with taken seats disabled (include UC08).",
      "Passenger clicks a free seat and confirms the seat and fare.", "System re-checks that the flight is bookable, the seat is valid and free, and the passenger has no other booking on this flight.",
      "System generates a unique PNR, stores the booking and shows the PNR and seat."],
    alt: ["1a. No flight selected: 'Search and select a flight first.'", "4a. Flight cancelled/boarding/departed meanwhile: 'Flight ... is CANCELLED; booking is closed.'",
      "4b. Seat taken meanwhile: 'Seat ... is already taken. Please choose another seat.'", "4c. Duplicate: 'You already hold a booking on flight ...'"] },
  { id: "UC09", name: "Cancel Booking", actors: "Passenger (own bookings), Administrator (any booking)",
    pre: "A booking with status BOOKED exists.", post: "The booking is CANCELLED and its seat is free again.",
    main: ["Actor selects a booking and clicks 'Cancel selected booking'.", "System asks for confirmation.", "System checks ownership, status and departure time.", "System sets the status to CANCELLED and refreshes the lists."],
    alt: ["3a. Not the passenger's booking: 'You can only cancel your own bookings.'", "3b. Already checked in: '... is checked in and can no longer be cancelled.'", "3c. Flight departed: 'The flight has already departed.'"] },
  { id: "UC11", name: "Check In Passenger", actors: "Check-in Staff, Administrator", includes: "UC12 Generate Boarding Pass",
    pre: "Staff is logged in; the passenger gives a PNR.", post: "Booking is CHECKED_IN with the next boarding sequence; the boarding pass is shown.",
    main: ["Staff enters the PNR and clicks 'Find booking'; system shows the booking.", "Staff clicks 'Check in passenger'.",
      "System checks the booking status, the flight status and the check-in window.", "System assigns the next boarding sequence, saves the check-in time and status.",
      "System generates and shows the boarding pass (include UC12)."],
    alt: ["1a. Bad PNR format or unknown PNR: error message.", "3a. Booking cancelled or already checked in.", "3b. Flight cancelled or departed.",
      "3c. More than 48 h before departure: 'Check-in opens 48 hours before departure.'", "3d. Less than 45 min before departure: 'Check-in closed 45 minutes before departure.'"] },
  { id: "UC14", name: "Add Bag", actors: "Check-in Staff, Administrator", includes: "UC15 Generate Bag Tag",
    pre: "The booking is checked in.", post: "A bag with tag AMSnnnnnn and status CHECKED_IN is stored; the summary and excess fee are updated.",
    main: ["Staff enters the bag weight and clicks 'Add bag & print tag'.", "System validates the weight and the number of bags.",
      "System stores the bag and creates its tag (include UC15).", "System shows the tag and recomputes '#bags, total kg, excess fee'."],
    alt: ["2a. Weight not a number, <= 0 or > 32 kg: e.g. 'A single bag cannot exceed 32 kg; send it as cargo.'", "2b. Already 3 bags: 'A passenger may check in at most 3 bags.'",
      "2c. Booking not checked in: 'Bags can be added only after the passenger has checked in.'"] },
  { id: "UC16", name: "Update Bag Status", actors: "Check-in Staff, Administrator",
    pre: "A bag exists.", post: "The bag has the new status and a new time stamp.",
    main: ["Staff selects a bag and a new status and clicks 'Update bag status'.", "System checks the transition against the bag state chart.", "System saves the new status and refreshes the list."],
    alt: ["1a. No bag selected: warning.", "2a. Transition not allowed (e.g. CLAIMED -> LOADED): 'Bag ... cannot change from CLAIMED to LOADED.'"] },
  { id: "UC18", name: "Add / Update Flight", actors: "Administrator", includes: "UC22 Check Gate Availability",
    pre: "Administrator is logged in.", post: "The flight is stored (new flights with status SCHEDULED).",
    main: ["Administrator fills in the flight form (or selects a flight to load it) and clicks 'Add flight' or 'Update selected'.",
      "System validates all fields and the schedule.", "System checks for a duplicate flight number on the same date.",
      "If a gate is given, system checks gate availability (include UC22).", "System saves the flight and refreshes the schedule."],
    alt: ["2a. Invalid field: field-specific message.", "3a. Duplicate: 'Flight ... is already scheduled on ...'", "4a. Gate busy: 'Gate ... is already assigned to another flight departing within 60 minutes of ...'",
      "Update only: route change after bookings, or fewer rows than the highest booked row, is refused."] },
  { id: "UC19", name: "Assign Gate", actors: "Administrator", includes: "UC22 Check Gate Availability",
    pre: "A flight that is not departed or cancelled is selected.", post: "The flight has the new gate.",
    main: ["Administrator types a gate and clicks 'Assign gate'.", "System validates the gate format and checks availability (include UC22).", "System saves the gate."],
    alt: ["2a. Invalid gate: 'Gate must be a terminal letter A-D followed by 1-20, e.g. B7.'", "2b. Gate busy: conflict message."] },
  { id: "UC20", name: "Change Flight Status", actors: "Administrator",
    pre: "A flight is selected.", post: "The flight has the new status.",
    main: ["Administrator chooses a status and clicks 'Set status'.", "System checks the transition against the flight state chart.", "System saves the status."],
    alt: ["2a. Transition not allowed: 'Flight status cannot change from X to Y.'"] },
  { id: "UC21", name: "Cancel Flight", actors: "Administrator", includes: "UC09 Cancel Booking (for every active booking)",
    pre: "A SCHEDULED or DELAYED flight is selected.", post: "Flight is CANCELLED, its gate is released and all its active bookings are CANCELLED.",
    main: ["Administrator clicks 'Cancel flight' and confirms.", "System cancels all non-cancelled bookings of the flight.", "System sets the flight to CANCELLED, clears the gate and reports how many bookings were cancelled."],
    alt: ["1a. Flight is BOARDING, DEPARTED or already CANCELLED: '... cannot be cancelled.'"] },
  { id: "UC04", name: "Create Staff Account", actors: "Administrator",
    pre: "Administrator is logged in (Users tab).", post: "A STAFF or ADMIN account exists.",
    main: ["Administrator fills in username, name, password, role, e-mail, mobile and clicks 'Create account'.", "System validates the fields and checks the username is free.", "System stores the account and refreshes the user list."],
    alt: ["Any non-admin calling the service: 'Access denied: this action requires role ADMIN.'", "2a. Invalid field or duplicate username: error message."] },
];

function ch9() {
  setChapter(9);
  const ucBlocks = [];
  for (const uc of USE_CASES) {
    const pairs = [["Use case", `**${uc.id} ${uc.name}**`], ["Actors", uc.actors], ["Pre-condition", uc.pre]];
    pairs.push(["Main flow", uc.main.map((s, i) => `${i + 1}. ${s}`)]);
    pairs.push(["Alternate flows / exceptions", uc.alt]);
    if (uc.includes) pairs.push(["Includes", uc.includes]);
    pairs.push(["Post-condition", uc.post]);
    ucBlocks.push(...KV(pairs));
  }
  return [
    H1("9. Object-Oriented Design (OOD)"),
    P("The object-oriented model describes the same system in terms of interacting objects, using UML. Class, method and state names in every diagram below are the actual names in the source code."),
    H2("9.1 Use Case Diagram"),
    P("Passenger, Check-in Staff and Administrator are specialisations of the abstract actor **User**, which inherits Login, Logout and View Flight Schedule. Use cases are grouped by module. «include» marks behaviour that is always performed as part of the base use case."),
    ...Img("docs/diagrams/use_case.png", "Use case diagram", { maxH: 800 }),
    ...Tbl(["ID", "Use case", "Actor(s)", "Module"], [
      ["UC01", "Login", "User", "M1"], ["UC02", "Logout", "User", "M1"], ["UC03", "Register Account", "Passenger", "M1"],
      ["UC04", "Create Staff Account", "Administrator", "M1"], ["UC05", "View Users", "Administrator", "M1"],
      ["UC06", "Search Flights", "Passenger", "M3"], ["UC07", "Book Ticket", "Passenger", "M3"], ["UC08", "Select Seat", "(included)", "M3"],
      ["UC09", "Cancel Booking", "Passenger, Administrator", "M3"], ["UC10", "View All Bookings", "Staff, Administrator", "M3"],
      ["UC11", "Check In Passenger", "Staff, Administrator", "M4"], ["UC12", "Generate Boarding Pass", "(included)", "M4"],
      ["UC13", "View Boarding Pass", "Passenger", "M4"], ["UC14", "Add Bag", "Staff", "M4"], ["UC15", "Generate Bag Tag", "(included)", "M4"],
      ["UC16", "Update Bag Status", "Staff", "M4"], ["UC17", "View Flight Schedule", "User", "M2"], ["UC18", "Add / Update Flight", "Administrator", "M2"],
      ["UC19", "Assign Gate", "Administrator", "M2"], ["UC20", "Change Flight Status", "Administrator", "M2"], ["UC21", "Cancel Flight", "Administrator", "M2"],
      ["UC22", "Check Gate Availability", "(included)", "M2"],
    ], [0.9, 3.0, 3.0, 1.0], { caption: "List of use cases", size: 18 }),
    H2("9.2 Use Case Descriptions"),
    P("Detailed descriptions are given for the main use cases. UC02, UC05, UC10, UC13 and UC17 are simple viewing operations (actor opens the tab; system lists the records allowed for the role). UC08, UC12, UC15 and UC22 are included use cases, described inside the base use cases."),
    ...ucBlocks,
    H2("9.3 Class Diagrams"),
    P("Classes follow the entity-boundary-control pattern: **entity** classes (ams.models) hold data, **control** classes (ams.services) hold business logic, and **boundary** classes (ams.gui) interact with users."),
    ...Img("docs/uml/class_domain.png", "Class diagram - entity classes and enumerations", { maxH: 720 }),
    ...Img("docs/uml/class_services.png", "Class diagram - control (service) classes and utility modules", { maxH: 480 }),
    ...Img("docs/uml/class_gui.png", "Class diagram - boundary (GUI) classes", { maxH: 520 }),
    ...Tbl(["Class", "Stereotype", "Responsibility"], [
      ["User, Flight, Booking, Bag", "entity", "Immutable records of D1-D4; `from_row()` converts an SQL row."],
      ["BookingDetails, BoardingPass", "entity (derived)", "Booking joined with passenger and flight; boarding pass with `as_text()`."],
      ["Role, FlightStatus, BookingStatus, BagStatus", "enumeration", "Allowed values of roles and states."],
      ["AuthService", "control", "Login, registration, staff accounts, user list."],
      ["FlightService", "control", "Flight CRUD, gate availability and assignment, status transitions, cancellation."],
      ["BookingService", "control", "Search, seat availability, booking, cancellation, booking lists."],
      ["CheckInService", "control", "PNR lookup, check-in, boarding pass, baggage."],
      ["AirportApp, AppContext", "boundary / coordinator", "Main window; holds the four services and the logged-in user."],
      ["LoginView, RegisterDialog, FlightView, BookingView, SeatMap, CheckInView, BoardingPassView, UsersView", "boundary", "One screen or dialog each; every action calls one service method."],
    ], [3.0, 1.5, 4.5], { caption: "Class responsibilities", size: 18 }),
    H2("9.4 Activity Diagrams"),
    ...Img("docs/uml/activity_booking.png", "Activity diagram - Book Ticket", { maxH: 760 }),
    ...Img("docs/uml/activity_checkin.png", "Activity diagram - Check-in and Baggage (fork: pass hand-over and bag loop proceed in parallel)", { maxH: 760 }),
    ...Img("docs/uml/activity_schedule.png", "Activity diagram - Schedule Flight", { maxH: 760 }),
    H2("9.5 State Chart Diagrams"),
    P("The flight and bag diagrams are exactly the transition tables `FLIGHT_TRANSITIONS` (flight_service.py) and `BAG_TRANSITIONS` (checkin_service.py); any other transition is rejected with a `BusinessRuleError`. The booking life cycle is enforced by the conditions in `book_ticket`, `check_in`, `cancel_booking` and `cancel_flight`."),
    ...Img("docs/uml/state_flight.png", "State chart - Flight", { maxH: 520 }),
    ...Img("docs/uml/state_booking.png", "State chart - Booking", { maxH: 520 }),
    ...Img("docs/uml/state_bag.png", "State chart - Bag", { maxH: 560 }),
    H2("9.6 Sequence Diagrams"),
    ...Img("docs/uml/sequence_login.png", "Sequence diagram - Login", { maxH: 520 }),
    ...Img("docs/uml/sequence_booking.png", "Sequence diagram - Book Ticket", { maxH: 700 }),
    ...Img("docs/uml/sequence_checkin.png", "Sequence diagram - Check In Passenger", { maxH: 640 }),
    H2("9.7 Collaboration (Communication) Diagrams"),
    P("A collaboration diagram shows the same interaction as a sequence diagram but emphasises the links between objects; the order of messages is given by their numbers (nested numbers such as 5.2 are calls made while handling message 5)."),
    ...Img("docs/diagrams/collaboration_booking.png", "Collaboration diagram - Book Ticket", { maxH: 620 }),
    ...Img("docs/diagrams/collaboration_checkin.png", "Collaboration diagram - Check In Passenger", { maxH: 560 }),
  ];
}

module.exports = { ch7, ch8, ch9 };
