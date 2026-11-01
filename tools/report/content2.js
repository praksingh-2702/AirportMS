// Chapters 7-9: Structured Analysis, Structured Design, Object-Oriented Design
// Diagram look: tools/bookstyle.py.
const fs = require("fs");
const path = require("path");
const L = require("./lib");
const { H1, H2, H3, P, Bullets, Img, ImgPair, Tbl, KV, setChapter } = L;

const DD = JSON.parse(fs.readFileSync(path.join(L.ROOT, "docs", "data_dictionary.json"), "utf8"));

function ch7() {
  setChapter(7);
  const lvl2 = [
    ["0_1", "0.1 Manage Users & Authenticate"], ["0_2", "0.2 Schedule Flights"], ["0_3", "0.3 Search Flights"],
    ["0_4", "0.4 Book / Cancel Ticket"], ["0_5", "0.5 Check In Passenger"], ["0_6", "0.6 Manage Baggage"],
    ["0_7", "0.7 Manage Recurring Schedule"], ["0_8", "0.8 Process Payment & Refund"],
  ];
  const lvl2Notes = {
    "0_1": "0.1.1 and 0.1.2 both read existing usernames from the users store to reject duplicates before writing a new user record; 0.1.3 serves all three kinds of user; 0.1.4 is used only by the administrator.",
    "0_2": "0.2.1 validates the form, 0.2.2 checks the 60-minute gate rule against the gate schedule in the flights store (it is used by both 0.2.3 and 0.2.4), 0.2.5 applies the state chart and hands cancellations to 0.2.6, which also updates bookings and tells the dashed bubble 0.8 so that every paid booking is refunded.",
    "0_3": "Search is a pure read: 0.3.1 validates the criteria, 0.3.2 selects bookable future flights from the flights store and 0.3.3 subtracts taken seats (bookings store) from capacity.",
    "0_4": "0.4.1 builds the seat map; 0.4.2 re-checks the selected seat and the one-booking-per-flight rule; 0.4.3 produces a PNR not present in the bookings store; 0.4.4 writes the booking and asks the dashed bubble 0.8 to take the payment (the booking is confirmed only when the Payment result is positive). 0.4.5 cancels a booking and receives the Refund amount from 0.8.",
    "0_5": "0.5.2 is decomposed further in Level 3 (Figure 7.11); it now also reads the payments store because an unpaid booking cannot be checked in. 0.5.3 reads the highest boarding sequence of the flight and writes the CHECKED_IN status. 0.5.5 turns the Boarding pass data into the downloadable PDF.",
    "0_6": "0.6.1 checks the weight and bag count, 0.6.2 stores the bag and creates its tag, 0.6.3 sums the weights and applies the fee rule, 0.6.4 applies the bag state chart.",
    "0_7": "0.7.1 and 0.7.2 maintain the recurring services; 0.7.3 to 0.7.6 form the generation pipeline: select the services due, price each flight, plan a free gate, and create the flights. The Existing flights flow is what makes generation repeatable without duplicates.",
    "0_8": "0.8.1 shows the fare breakdown; 0.8.2 validates what the passenger typed; 0.8.3 asks the payment gateway (an external entity) to authorise; 0.8.4 records the payment. 0.8.5 computes a refund when 0.4 reports a cancellation or 0.2 reports a cancelled flight; 0.8.6 produces the receipt and 0.8.7 the revenue summary. Dashed bubbles 0.4 and 0.2 are the neighbouring Level-1 processes.",
  };
  // built lazily, at its place in the array below, so that the figure numbers follow reading order
  const level2Blocks = () => {
    const blocks = [];
    for (const [i, [file, title]] of lvl2.entries()) {
      blocks.push(H3(`7.3.${i + 1} Level 2: ${title}`));
      blocks.push(...Img(`docs/diagrams/dfd_level2_${file}.png`, `Level 2 DFD - decomposition of process ${title}`, { maxH: 440 }));
      blocks.push(P(lvl2Notes[file]));
    }
    return blocks;
  };
  const nStores = DD.composite.filter(([n]) => /^D\d /.test(n)).length;
  return [
    H1("7. Structured Analysis (SA)"),
    P("Structured analysis models **what** the system does as a hierarchy of Data Flow Diagrams (DFDs), starting from the context diagram and refining each process until the processes are atomic (each can be implemented as a single, simple function). It is the first half of **Function-Oriented Design: FOD = SA + SD**."),
    P("**Notation used:** yellow rectangle = external entity (repeated beside each process it interacts with, to avoid crossing lines); blue circle = process, with its hierarchical number above its name (the whole system is 0, its sub-processes 0.1, 0.2 ..., and those of 0.2 are 0.2.1, 0.2.2 ..., as in the textbook); open-ended rectangle with D# = data store; labelled arrow = data flow. In the Level 2 and 3 diagrams a **dashed circle** is a neighbouring bubble of the parent level."),
    ...Tbl(["Element", "Names used consistently in every diagram, in the code and in the data dictionary"], [
      ["External entities", "Passenger, Check-in Staff, Administrator, Payment Gateway (a simulator inside the program, drawn as an external entity because a real gateway would be one)"],
      ["Data stores", "D1 Users (table users), D2 Flights, D3 Bookings, D4 Baggage, D5 Recurring Services (table flight_templates), D6 Payments"],
      ["Level-1 processes", "0.1 Manage Users & Authenticate, 0.2 Schedule Flights, 0.3 Search Flights, 0.4 Book / Cancel Ticket, 0.5 Check In Passenger, 0.6 Manage Baggage, 0.7 Manage Recurring Schedule, 0.8 Process Payment & Refund"],
    ], [2.0, 7.0], { caption: "DFD vocabulary" }),
    H2("7.1 Context Diagram (Level 0 DFD)"),
    P("The context diagram shows the whole system as a single process (bubble 0) and all data that crosses the system boundary."),
    ...Img("docs/diagrams/dfd_context_level0.png", "Context diagram (Level 0 DFD) of the Airport Management System", { maxH: 440 }),
    H2("7.2 Level 1 DFD"),
    P("Bubble 0 is decomposed into eight processes. The textbook advises about seven bubbles at a level; an eighth was accepted deliberately, because payment and refund are one distinct function that both booking (0.4) and flight cancellation (0.2) depend on, and folding it into 0.4 would have produced a bubble with eleven flows, which the book warns against (Figure 6.7). Every flow to or from an external entity in Figure 7.1 appears in Figure 7.2 with the same name, so the two levels are **balanced**. Bubbles that serve passengers (0.1, 0.3, 0.4, 0.8) are in the upper row and those used by staff and the administrator (0.2, 0.5, 0.6, 0.7) in the lower row, with the data stores between them."),
    ...Img("docs/diagrams/dfd_level1.png", "Level 1 DFD", { maxH: 800 }),
    H2("7.3 Level 2 DFDs"),
    P("Each Level-1 process is decomposed in its own diagram. Dashed circles are the neighbouring Level-1 bubbles that exchange data with the one being decomposed (for example 0.4 and 0.2 around 0.8). The flows entering and leaving each diagram are exactly those of the parent bubble in Level 1."),
    ...level2Blocks(),
    H2("7.4 Level 3 DFD: 0.5.2 Verify Check-in Eligibility"),
    P("Process 0.5.2 contains five independent rules, so it is decomposed once more. Each of 0.5.2.1 to 0.5.2.5 is a single comparison and corresponds to one decision node in the control-flow graph of `check_in` (Section 11.3); these are the **atomic** processes. 0.5.2.3, the payment check, was added when payments were introduced. Dashed circles 0.5.1 and 0.5.3 are the neighbouring processes from Level 2, shown only to make the inputs and outputs clear. The five rejection reasons together form the error path of 0.5.2."),
    ...Img("docs/diagrams/dfd_level3_0_5_2.png", "Level 3 DFD - decomposition of 0.5.2 Verify Check-in Eligibility", { maxH: 330 }),
    P("Processes at Level 2 that are not decomposed further (for example 0.4.3 Generate PNR, 0.6.3 Compute Excess Fee, 0.7.4 Price Flight) are already atomic: each maps to one short function in the code (`_unique_pnr`, `compute_excess_fee`, `dynamic_fare`)."),
    H2("7.5 Balancing"),
    P("A DFD is balanced when the data flowing into and out of a bubble equals the data flowing into and out of its child diagram. All DFDs are generated from one specification file (`tools/dfd_spec.py`), and the script `tools/make_dfds.py` checks balancing automatically: (a) the external flows of the context diagram equal those of Level 1, and (b) for each Level-1 bubble, the flows to entities, stores and neighbouring bubbles equal those of its Level-2 diagram. The final run, made after the last iteration, reports **BALANCING: OK**. (During development this check found three store reads that had been drawn in Level 2 but not in Level 1; Level 1 was corrected. It was run again after each of the later iterations that added the recurring schedule and the payments.)"),
    H2("7.6 Data Dictionary"),
    P("The data dictionary defines every data flow and data store that appears in the DFDs, in the textbook's notation: `=` is composed of, `+` and, `[a | b]` either a or b, `{x}` zero or more x, `(x)` optional x, `\"...\"` literal value. Names are exactly the names that label the arrows. The script `tools/data_dictionary.py` verifies that every one of the " +
      `${DD.composite.length - nStores} flow names and ${nStores} stores in the DFDs is defined below and that no entry is unused.`),
    ...Tbl(["Name", "Composition"],
      DD.composite.map(([n, c]) => [`**${n}**`, c]), [2.4, 6.6], { caption: "Data dictionary - data stores and data flows", size: 16 }),
    ...Tbl(["Elementary item", "Type / domain", "Notes"], DD.elementary, [2.0, 4.2, 2.8],
      { caption: "Data dictionary - elementary data items", size: 17 }),
  ];
}

function ch8() {
  setChapter(8);
  return [
    H1("8. Structured Design (SD)"),
    P("Structured design transforms the DFD model into a **structure chart**: a hierarchy of modules showing which module calls which, and the data passed between them. The two strategies are **transform analysis** (for DFDs where data flows through input -> processing -> output) and **transaction analysis** (for DFDs where one input selects one of several processing paths)."),
    H2("8.1 Structure Chart Notation"),
    ...Tbl(["Symbol", "Meaning"], [
      ["Rectangle", "Module (a function or class method); the name of the implementing code is given in the box"],
      ["Rectangle with double border", "Library module: a module invoked by many others (here the validators and the fare function)"],
      ["Arrow between modules", "Module invocation (the caller is above)"],
      ["○ name ↓ / ○ name ↑", "Data couple passed to the called module / returned to the caller"],
      ["● name ↑", "Control flag returned to the caller (e.g. eligible, seat_free, approved)"],
      ["Diamond under a module", "Selection: the module calls exactly one of the modules below it (transaction centre)"],
    ], [2.6, 6.4], { caption: "Structure-chart notation" }),
    H2("8.2 Transaction Analysis"),
    P("After login, the dashboard receives the user and, depending on the role and the tab the user opens, starts one of several independent transactions. This is a **transaction-centred** flow: the transaction centre `show_dashboard(user)` (selected using `ROLE_TABS[user.role]`) dispatches to one of six transaction modules (flight scheduling, recurring schedule, passenger booking, check-in and baggage, user management, boarding pass), each of which calls the matching service. The steps followed were: (1) identify the transaction centre in the Level-1 DFD (the role/tab selection in front of processes 0.2-0.8); (2) draw one branch per transaction type; (3) factor each branch further using transform analysis (Sections 8.3-8.6)."),
    ...Img("docs/diagrams/structure_chart_transaction.png", "Structure chart from transaction analysis (top level)", { maxH: 360 }),
    H2("8.3 Transform Analysis of 0.5 Check In Passenger"),
    P("For DFD 0.5, the input, central-transform and output portions were identified as follows, and each became one first-level branch of the structure chart:"),
    ...Tbl(["Portion", "DFD processes", "Structure-chart modules (code)"], [
      ["Afferent (input) branch", "0.5.1 Retrieve Booking (read PNR, validate, fetch from users/flights/bookings)", "Get Booking Details -> Validate PNR (`validate_pnr`), Fetch Booking Row (`find_booking`)"],
      ["Central transform", "0.5.2 Verify Check-in Eligibility, 0.5.3 Assign Boarding Seq.", "Verify Eligibility -> Check Payment Status, Check Time Window; Assign Boarding Seq"],
      ["Efferent (output) branch", "0.5.4 Generate Boarding Pass, 0.5.5 Export Boarding Pass PDF", "Produce Boarding Pass -> Format Pass (`as_text`), Export Pass PDF (`render_boarding_pass`)"],
    ], [2.0, 3.6, 3.4], { caption: "Transform analysis of DFD 0.5" }),
    ...Img("docs/diagrams/structure_chart_transform_checkin.png", "Structure chart from transform analysis of DFD 0.5", { maxH: 340 }),
    H2("8.4 Transform Analysis of 0.4 Book / Cancel Ticket (booking path)"),
    ...Tbl(["Portion", "DFD processes", "Structure-chart modules (code)"], [
      ["Afferent branch", "0.4.1 Show Seat Map (selected seat), flight record from the flights store", "Get Valid Request -> Get Flight, Validate Seat (`parse_seat`)"],
      ["Central transform", "0.4.2 Validate Booking, 0.4.3 Generate PNR", "Check Seat & Duplicate (`get_taken_seats`), Generate PNR (`_unique_pnr`)"],
      ["Efferent branch", "0.4.4 Record Booking (write bookings store, confirmation)", "Record & Confirm -> Insert Booking, Show Confirmation"],
    ], [2.0, 3.6, 3.4], { caption: "Transform analysis of DFD 0.4" }),
    ...Img("docs/diagrams/structure_chart_transform_booking.png", "Structure chart from transform analysis of DFD 0.4", { maxH: 340 }),
    H2("8.5 Transform Analysis of 0.8 Process Payment (book_and_pay)"),
    P("Payment is the one place where the input branch contains a **selection**: depending on the chosen method exactly one of three validators is invoked (diamond). The payment gateway is the lowest module of the central transform. If the gateway declines, Release Seat is invoked and the whole transaction leaves nothing behind."),
    ...Tbl(["Portion", "DFD processes", "Structure-chart modules (code)"], [
      ["Afferent branch", "0.8.2 Validate Payment Details", "Get Valid Payment Details (diamond) -> Validate Card Details (`validate_card_number`, `validate_expiry`, `validate_cvv`), Validate UPI ID, Validate Bank"],
      ["Central transform", "0.8.1 Compute Fare Breakdown, 0.8.3 Authorize Payment", "Reserve Seat (`book_ticket`), Authorize Payment -> Payment Gateway (`gateway.authorize`)"],
      ["Efferent branch", "0.8.4 Record Payment", "Record Payment (`record_payment`), Release Seat (decline path)"],
    ], [2.0, 3.6, 3.4], { caption: "Transform analysis of DFD 0.8" }),
    ...Img("docs/diagrams/structure_chart_transform_payment.png", "Structure chart from transform analysis of DFD 0.8", { maxH: 340 }),
    H2("8.6 Transform Analysis of 0.7 Manage Recurring Schedule (generate flights)"),
    ...Tbl(["Portion", "DFD processes", "Structure-chart modules (code)"], [
      ["Afferent branch", "0.7.3 Select Services Due (reads the recurring services and the existing flights)", "Get Due Services -> List Active Services (`list_templates`), Read Existing Flights"],
      ["Central transform", "0.7.4 Price Flight, 0.7.5 Plan Gates", "Price Flight -> Dynamic Fare (`dynamic_fare`); Plan Gates -> Gate Planner (`_GatePlanner.assign`)"],
      ["Efferent branch", "0.7.6 Create Flights", "Create Flights -> Insert Flights, Summarise Generation (`GenerationResult`)"],
    ], [2.0, 3.6, 3.4], { caption: "Transform analysis of DFD 0.7" }),
    ...Img("docs/diagrams/structure_chart_transform_schedule.png", "Structure chart from transform analysis of DFD 0.7", { maxH: 340 }),
    H2("8.7 Parameter (Variable) Passing"),
    P("The table lists the data couples of the structure charts with the actual function signatures in the code. All couples are **data couples** or stamp couples (a composite object such as `User` or `Booking`). The control flags in the charts (●, for example eligible, seat_free, approved) are realised in the code as exceptions: a false flag becomes a raised `BusinessRuleError` or `PaymentError`, so callers need not test flags."),
    ...Tbl(["Module (code)", "Parameters in (down)", "Returned (up)", "Couple type"], [
      ["AuthService.login(username, password)", "username, password", "User (role inside)", "Data / stamp"],
      ["AirportApp.show_dashboard(user)", "user", "-", "Stamp"],
      ["CheckInService.find_booking(pnr)", "pnr", "BookingDetails", "Data in, stamp out"],
      ["validators.validate_pnr(value)", "raw pnr string", "normalised pnr", "Data"],
      ["CheckInService.check_in(actor, pnr, now)", "actor, pnr, now", "BoardingPass (or an error if not eligible or not paid)", "Stamp"],
      ["CheckInService.get_boarding_pass(actor, pnr)", "actor, pnr", "BoardingPass", "Stamp"],
      ["CheckInService.boarding_pass_file(actor, pnr)", "actor, pnr", "(file name, PDF bytes)", "Stamp"],
      ["boarding_pdf.render_boarding_pass(pass)", "BoardingPass", "PDF bytes", "Stamp / data"],
      ["boarding_pdf.code128_widths(text)", "pnr text", "list of bar widths", "Data"],
      ["BoardingPass.as_text()", "-", "pass text", "Data"],
      ["BookingService.book_ticket(actor, flight_id, seat, now)", "actor, flight_id, seat, now", "Booking", "Stamp"],
      ["validators.parse_seat(value, rows)", "seat, rows", "seat", "Data"],
      ["BookingService.get_taken_seats(flight_id)", "flight_id", "set of seats", "Data"],
      ["BookingService._unique_pnr()", "-", "pnr", "Data"],
      ["PaymentService.book_and_pay(actor, flight_id, seat, method, details, now)", "actor, flight_id, seat, method, details, now", "(Booking, Payment) or PaymentError", "Stamp"],
      ["validators.validate_card_number(value)", "raw card number", "digits (Luhn-valid)", "Data"],
      ["gateway.authorize(method, details, amount)", "method, cleaned details, amount", "GatewayResult (approved, reference, message)", "Stamp"],
      ["payments_core.fare_breakdown(base_fare)", "base fare", "FareBreakdown", "Data in, stamp out"],
      ["PaymentService.refund_quote(booking_id, now)", "booking_id, now", "RefundQuote", "Stamp"],
      ["payments_core.refund_booking(conn, booking_id, now, full, reason)", "connection, booking_id, now, full, reason", "refund amount", "Data"],
      ["PaymentService.receipt_file(actor, booking_id)", "actor, booking_id", "(file name, PDF bytes)", "Stamp"],
      ["ScheduleService.generate_flights(actor, days, now)", "actor, days, now", "GenerationResult", "Stamp"],
      ["schedule_service.dynamic_fare(base_fare, departure, now)", "base fare, departure, now", "fare (INR)", "Data"],
      ["FlightService.is_gate_available(gate, departure, exclude_flight_id)", "gate, departure, flight id", "bool (gate free)", "Data (flag in the DFD)"],
      ["CheckInService.add_bag(actor, pnr, weight, now)", "actor, pnr, weight, now", "Bag", "Stamp"],
      ["compute_excess_fee(total_weight_kg)", "total weight", "fee", "Data"],
    ], [3.8, 2.2, 1.9, 1.1], { caption: "Parameter passing between modules", size: 17 }),
  ];
}

const USE_CASES = [
  { id: "UC01", name: "Login", actors: "User (Passenger, Check-in Staff, Administrator)",
    pre: "The user has an account. The login screen is shown.",
    post: "Success: the role dashboard is shown and the user is stored in the application context. Failure: the user stays on the login screen.",
    main: ["User enters username and password and clicks Login (or presses Enter).", "System looks up the username (case-insensitive) in the users store.",
      "System verifies the password against the stored salted hash.", "System builds the tabs for the user's role and shows the dashboard."],
    alt: ["1a. A field is blank: 'Enter both username and password.'", "2a/3a. Unknown username or wrong password: 'Invalid username or password.' (same message in both cases; the login card shakes)."] },
  { id: "UC03", name: "Register Account", actors: "Passenger",
    pre: "Login screen is shown.", post: "A PASSENGER account exists; the username is filled in on the login screen.",
    main: ["Passenger clicks 'New passenger? Register'.", "Passenger enters username, full name, password twice, e-mail and mobile number and clicks Register (or presses Enter).",
      "System validates every field and checks that the username is unused.", "System stores the user with a hashed password and confirms."],
    alt: ["2a. Passwords differ: 'Passwords do not match.'", "3a. A field is invalid: field-specific message (e.g. 'Phone must be a 10-digit mobile number starting with 6-9.')",
      "3b. Username exists: 'Username ... is already taken.'"] },
  { id: "UC06", name: "Search Flights", actors: "Passenger",
    pre: "Passenger is logged in.", post: "Matching flights are listed with seats left; flights the passenger has already booked are marked.",
    main: ["Passenger optionally chooses From and To from the airport list (e.g. 'IXE - Mangalore') and a date on the drop-down calendar, and clicks Search.", "System validates the criteria.",
      "System selects SCHEDULED/DELAYED flights departing in the future that match, earliest first, at most 300.", "System shows each flight with fare, seats left and the passenger's own PNR if booked."],
    alt: ["2a. Invalid code or date: e.g. 'Date must be in YYYY-MM-DD format, e.g. 2026-11-05.'", "3a. No match: the table shows 'No flights match your search.'"] },
  { id: "UC07", name: "Book Ticket", actors: "Passenger", includes: "UC08 Select Seat, UC26 Pay for Booking",
    pre: "Passenger is logged in and has searched for flights.", post: "A booking with status BOOKED, a unique PNR and a PAID payment exists; the seat is no longer free.",
    main: ["Passenger selects a flight and clicks 'Book selected flight'.", "System checks that the passenger does not already hold a booking on it, then shows the seat map with taken seats disabled (include UC08).",
      "Passenger clicks a free seat and confirms.", "System opens the payment window with the fare breakdown (include UC26).", "Passenger pays; the gateway approves.",
      "System re-checks the flight and the seat, generates a unique PNR, stores the booking and the payment, and shows PNR, seat and invoice."],
    alt: ["1a. No flight selected: 'Search and select a flight first.'", "2a. Already booked: 'You already hold booking ... on ...' (before the seat map opens).",
      "5a. Payment declined: the bank's reason is shown, no booking exists and the seat stays free; the passenger may retry or cancel.", "6a. Seat taken meanwhile: 'Seat ... is already taken. Please choose another seat.'"] },
  { id: "UC09", name: "Cancel Booking", actors: "Passenger (own bookings), Administrator (any booking)", includes: "UC29 Refund Payment",
    pre: "A booking with status BOOKED exists.", post: "The booking is CANCELLED, its seat is free again and, if it was paid, the refund is recorded.",
    main: ["Actor selects a booking and clicks 'Cancel selected booking'.", "System states the refund and what is kept (cancellation charge and convenience fee) and asks for confirmation.", "System checks ownership, status and departure time.",
      "System sets the status to CANCELLED, refunds the payment (include UC29) and refreshes the lists."],
    alt: ["3a. Not the passenger's booking: 'You can only cancel your own bookings.'", "3b. Already checked in: '... is checked in and can no longer be cancelled.'", "3c. Flight departed: 'The flight has already departed.'",
      "2a. Booking unpaid: 'This booking is unpaid, so nothing will be refunded.'"] },
  { id: "UC11", name: "Check In Passenger", actors: "Check-in Staff, Administrator", includes: "UC12 Generate Boarding Pass",
    pre: "Staff is logged in; the passenger gives a PNR.", post: "Booking is CHECKED_IN with the next boarding sequence; the boarding pass is shown.",
    main: ["Staff enters the PNR and clicks 'Find booking'; system shows the booking with its payment status.", "Staff clicks 'Check in passenger'.",
      "System checks the booking status, the flight status, the payment and the check-in window.", "System assigns the next boarding sequence, saves the check-in time and status.",
      "System generates and shows the boarding pass (include UC12)."],
    alt: ["1a. Bad PNR format or unknown PNR: error message; the screen is cleared.", "3a. Booking cancelled or already checked in.", "3b. Flight cancelled or departed.",
      "3c. Not paid: 'Payment for booking ... is pending. The passenger must pay before check-in.'",
      "3d. More than 48 h before departure: 'Check-in opens 48 hours before departure.'", "3e. Less than 45 min before departure: 'Check-in closed 45 minutes before departure.'"] },
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
    main: ["Administrator fills in the flight form (dates typed or picked on the calendar, or a flight is selected to load it) and clicks 'Add flight' or 'Update selected'.",
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
    alt: ["1a. No status chosen: 'Pick a new status from the drop-down first.'", "2a. Transition not allowed: 'Flight status cannot change from X to Y.'"] },
  { id: "UC21", name: "Cancel Flight", actors: "Administrator", includes: "UC09 Cancel Booking (for every active booking), UC29 Refund Payment",
    pre: "A SCHEDULED or DELAYED flight is selected.", post: "Flight is CANCELLED, its gate is released, all its active bookings are CANCELLED and every paid booking is refunded in full.",
    main: ["Administrator clicks 'Cancel flight' and confirms.", "System refunds the payment of every non-cancelled booking of the flight in full (include UC29) and cancels those bookings.", "System sets the flight to CANCELLED, clears the gate and reports how many bookings were cancelled."],
    alt: ["1a. Flight is BOARDING, DEPARTED or already CANCELLED: '... cannot be cancelled.'"] },
  { id: "UC04", name: "Create Staff Account", actors: "Administrator",
    pre: "Administrator is logged in (Users tab).", post: "A STAFF or ADMIN account exists.",
    main: ["Administrator fills in username, name, password, role, e-mail, mobile and clicks 'Create account'.", "System validates the fields and checks the username is free.", "System stores the account and refreshes the user list."],
    alt: ["Any non-admin calling the service: 'Access denied: this action requires role ADMIN.'", "2a. Invalid field or duplicate username: error message."] },
  { id: "UC23", name: "Add Recurring Service", actors: "Administrator",
    pre: "Administrator is logged in (Schedule tab).", post: "An active recurring service exists; no flight has been created yet.",
    main: ["Administrator fills in flight number, airline, route, departure time, duration, days, rows and base fare and clicks 'Add recurring service'.",
      "System validates every field and checks that the flight number is new.", "System stores the service as active and says that 'Generate flights' will create its dated flights."],
    alt: ["2a. Time not HH:MM, duration outside 20-1200 min, days not recognised, rows or fare out of range: field-specific message.", "2b. Flight number already used by a service: 'A recurring service ... already exists.'"] },
  { id: "UC25", name: "Generate Flights", actors: "Administrator", includes: "UC22 Check Gate Availability (gate planning)",
    pre: "Administrator is logged in (Schedule tab); at least one active service exists.", post: "Dated flights exist for every active service and every day it runs in the next n days; none is duplicated.",
    main: ["Administrator enters the number of days and clicks 'Generate flights'.", "System validates 1 <= days <= 90.",
      "For each active service and each day it runs (departure still in the future) that has no flight yet, system prices the flight, plans a free gate (include UC22) and adds it.", "System inserts all new flights and shows 'Created n flight(s); m already existed. Schedule now covers up to <date>.'"],
    alt: ["2a. Days not 1-90: 'Number of days must be between 1 and 90.'", "3a. Flight already exists or was cancelled earlier: counted as 'already existed'; running again creates 0.", "The same generation also runs automatically for 30 days every time the program starts."] },
  { id: "UC26", name: "Pay for Booking", actors: "Passenger, Payment Gateway (external system)", includes: "UC27 Authorize Payment",
    pre: "A seat has been chosen (booking) or an unpaid booking is selected ('Pay now').", post: "A PAID payment with an invoice number exists for the booking.",
    main: ["System shows the payment window: fare breakdown (base fare, airport fee, GST, convenience fee, total) and the 'demo mode' notice.", "Passenger chooses Card, UPI or Net banking and enters the details (the card number is grouped as typed).",
      "System validates every field.", "System asks the gateway to authorise (include UC27).", "On approval the booking and the payment are saved; the window shows 'Payment successful' with PNR, seat, invoice and a receipt button."],
    alt: ["3a. Invalid card number (Luhn), expired card, wrong CVV, bad UPI id or no bank: the message is shown in the window, nothing is sent to the gateway.",
      "4a. Declined (e.g. 'Card declined by the issuing bank.'): the reason is shown in red, no booking is created, the window stays open for another attempt.", "Pay now on an already paid booking: 'Booking ... is already paid.'"] },
  { id: "UC28", name: "Download Receipt", actors: "Passenger (own), Check-in Staff, Administrator",
    pre: "The booking has a payment.", post: "A one-page PDF receipt is saved where the actor chose.",
    main: ["Actor selects a booking and clicks 'Download receipt' (or the button in the success window).", "System builds the receipt with invoice number, itemised charges, masked payment method and, if refunded, the refund box.",
      "System shows the Save dialog and, after saving, offers to open the file."],
    alt: ["1a. Booking unpaid: 'Booking ... has not been paid, so there is no receipt yet.'", "1b. Another passenger's booking: 'You can only view your own receipts.'", "2a. Save dialog cancelled: nothing is written."] },
  { id: "UC29", name: "Refund Payment", actors: "(included by UC09 and UC21)",
    pre: "A booking is being cancelled.", post: "If the booking was paid, its payment is REFUNDED with the refund amount, reason and time recorded.",
    main: ["System finds the PAID payment of the booking.", "For a passenger or administrator cancellation: charge = 10 / 25 / 50 / 100% of the base fare by time to departure; refund = amount - convenience fee - charge.",
      "For a cancelled flight: refund = amount paid.", "System records REFUNDED, the refund amount and the reason."],
    alt: ["1a. No payment (unpaid booking) or already refunded: nothing is refunded."] },
  { id: "UC31", name: "Download Boarding Pass", actors: "Passenger (own pass), Check-in Staff, Administrator", extendsUc: "UC13 View Boarding Pass",
    pre: "The booking is CHECKED_IN.", post: "A one-page ticket-shaped PDF with a Code 128 barcode (the PNR) is saved.",
    main: ["Actor clicks 'Download boarding pass (PDF)' (staff) or selects a pass and clicks 'Download PDF' (passenger).", "System builds the PDF: route, passenger, flight, date, gate, seat, boarding time, perforated stub and barcode.",
      "System shows the Save dialog and, after saving, offers to open the file."],
    alt: ["1a. Booking not checked in: the button is disabled / 'Booking ... is not checked in yet.'", "1b. Another passenger's pass: 'You can only view your own boarding pass.'"] },
];

function ch9() {
  setChapter(9);
  const KEY_UC = ["UC01", "UC07", "UC26", "UC09", "UC11", "UC14", "UC18", "UC25"];
  const ucBlocks = [];
  const ucOthers = USE_CASES.filter((uc) => !KEY_UC.includes(uc.id))
    .map((uc) => [uc.id, uc.name, uc.actors, `${uc.pre}\n-> ${uc.post}`]);
  for (const uc of USE_CASES.filter((u) => KEY_UC.includes(u.id))) {
    const pairs = [["Use case", `**${uc.id} ${uc.name}**`], ["Actors", uc.actors], ["Pre-condition", uc.pre]];
    pairs.push(["Main flow", uc.main.map((s, i) => `${i + 1}. ${s}`)]);
    pairs.push(["Alternate flows / exceptions", uc.alt]);
    if (uc.includes) pairs.push(["Includes", uc.includes]);
    if (uc.extendsUc) pairs.push(["Extends", uc.extendsUc]);
    pairs.push(["Post-condition", uc.post]);
    ucBlocks.push(...KV(pairs));
  }
  return [
    H1("9. Object-Oriented Design (OOD)"),
    P("The object-oriented model describes the same system in terms of interacting objects, using UML in the notation of the textbook (Chapter 7). Class, method and state names in every diagram below are the actual names in the source code."),
    H2("9.1 Use Case Diagrams"),
    P("Passenger, Check-in Staff and Administrator are specialisations of the abstract actor **User**, which inherits Login, Logout and View Flight Schedule (generalisation, hollow arrowhead). The Payment Gateway is an actor too: a stick figure marked as an **external system**, as the book describes for external systems. A **dashed arrow labelled «include»** marks behaviour that is always performed as part of the base use case; a dashed arrow labelled **«extend»** marks optional behaviour (downloading a boarding pass extends viewing it). A rectangle drawn around the use cases is the system boundary. With 31 use cases one diagram would be unreadable, so, as the book does with use case packaging (Figure 7.22), Figure 9.1 shows the packages and Figures 9.2-9.4 the use cases of each group; a dashed ellipse is a use case that belongs to another figure."),
    ...Img("docs/diagrams/use_case.png", "Use case packaging: the actors and the six packages of use cases", { maxH: 360 }),
    ...Img("docs/diagrams/use_case_accounts_flights.png", "Use case diagram - accounts, flight scheduling and recurring schedule", { maxH: 560 }),
    ...Img("docs/diagrams/use_case_booking_payments.png", "Use case diagram - booking and payments", { maxH: 500 }),
    ...Img("docs/diagrams/use_case_checkin.png", "Use case diagram - check-in, boarding pass and baggage", { maxH: 400 }),
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
      ["UC23", "Add Recurring Service", "Administrator", "M5"], ["UC24", "Switch Service On / Off", "Administrator", "M5"], ["UC25", "Generate Flights", "Administrator", "M5"],
      ["UC26", "Pay for Booking", "Passenger, Payment Gateway", "M6"], ["UC27", "Authorize Payment", "Payment Gateway (included)", "M6"],
      ["UC28", "Download Receipt", "Passenger, Staff, Administrator", "M6"], ["UC29", "Refund Payment", "(included)", "M6"], ["UC30", "View Revenue", "Administrator", "M6"],
      ["UC31", "Download Boarding Pass", "Passenger, Staff, Administrator", "M4"],
    ], [0.9, 3.0, 3.0, 1.0], { caption: "List of use cases", size: 18 }),
    H2("9.2 Use Case Descriptions"),
    P("Full descriptions are given for the eight main use cases, one or more from every module. The remaining use cases are summarised in Table 9.3 by their pre- and post-conditions. UC02, UC05, UC10, UC13, UC17, UC24 and UC30 are simple viewing or switching operations; UC08, UC12, UC15, UC22 and UC27 are included use cases, described inside the base use cases."),
    ...ucBlocks,
    ...Tbl(["ID", "Use case", "Actor(s)", "Pre-condition -> Post-condition"], ucOthers, [0.7, 1.9, 2.0, 4.4],
      { caption: "Summary of the other use cases", size: 16 }),
    H2("9.3 Class Diagrams"),
    P("Classes follow the entity-boundary-control pattern (section 8.3 of the book): **entity** classes (ams.models) hold data, **control** classes (ams.services) hold business logic, and **boundary** classes (ams.gui) interact with users. Associations carry a name, a reading direction and multiplicities (Figure 7.24); the filled diamond is composition (a payment owns its fare breakdown); dashed arrows are dependencies."),
    ...Img("docs/uml/class_domain.png", "Class diagram - entity classes and enumerations", { maxH: 620 }),
    ...Img("docs/uml/class_services.png", "Class diagram - control (service) classes and helper modules", { maxH: 500 }),
    ...Img("docs/uml/class_gui.png", "Class diagram - boundary (GUI) classes", { maxH: 540 }),
    ...Tbl(["Class", "Stereotype", "Responsibility"], [
      ["User, Flight, FlightTemplate, Booking, Bag, Payment", "entity", "Immutable records of D1-D6; `from_row()` converts an SQL row."],
      ["FareBreakdown, RefundQuote", "entity (value)", "The four parts of a fare and their total; what a cancellation would refund and what is kept."],
      ["BookingDetails, BoardingPass", "entity (derived)", "Booking joined with passenger and flight; boarding pass with `as_text()`."],
      ["Role, FlightStatus, BookingStatus, BagStatus, PaymentStatus", "enumeration", "Allowed values of roles and states."],
      ["AuthService", "control", "Login, registration, staff accounts, user list."],
      ["FlightService", "control", "Flight lists with filters, CRUD, gate availability and assignment, status transitions, cancellation."],
      ["ScheduleService", "control", "Recurring services, flight generation with dynamic fares and gate planning, start-up top-up."],
      ["BookingService", "control", "Search, seat availability, booking, cancellation, booking lists."],
      ["PaymentService", "control", "Fare quote, book-and-pay, pay later, refund quote, receipts, revenue, legacy migration."],
      ["CheckInService", "control", "PNR lookup, check-in (incl. the payment rule), boarding pass and its PDF, baggage."],
      ["AirportApp, AppContext, Header, TabHost, StatCard", "boundary / coordinator", "Main window; holds the six services and the logged-in user; animated header, tabs and statistic tiles."],
      ["LoginView, RegisterDialog, FlightView, ScheduleView, BookingView, SeatMap, PaymentDialog, CheckInView, BoardingPassView, UsersView", "boundary", "One screen or dialog each; every action calls one service method."],
      ["DataTable, FormPanel, DateEntry, CalendarPopup, Button", "boundary (widgets)", "Reusable controls: table with hover and empty state, form grid, date field with a drop-down calendar, animated button."],
    ], [3.0, 1.5, 4.5], { caption: "Class responsibilities", size: 18 }),
    H2("9.4 Activity Diagrams"),
    P("Swim lanes (section 7.7 of the book) show who performs each activity: the passenger, the system and, for payment, the gateway. A filled circle is the start; a filled circle inside a ring is the end."),
    ...ImgPair("docs/uml/activity_booking.png", "Activity diagram - Book and pay for a ticket",
               "docs/uml/activity_schedule.png", "Activity diagram - Schedule Flight", { maxH: 600 }),
    ...ImgPair("docs/uml/activity_checkin.png", "Activity diagram - Check-in and Baggage (fork: pass hand-over and bag loop proceed in parallel)",
               "docs/uml/activity_generate.png", "Activity diagram - Generate flights from the recurring schedule", { maxH: 560 }),
    H2("9.5 State Chart Diagrams"),
    P("The flight and bag diagrams are exactly the transition tables `FLIGHT_TRANSITIONS` (flight_service.py) and `BAG_TRANSITIONS` (checkin_service.py); any other transition is rejected with a `BusinessRuleError`. The booking life cycle is enforced by the conditions in `book_ticket`, `check_in`, `cancel_booking` and `cancel_flight`. The payment diagram shows that a booking is unpaid (no payment row), PAID, or REFUNDED, and that only a PAID booking can be checked in."),
    ...ImgPair("docs/uml/state_flight.png", "State chart - Flight", "docs/uml/state_booking.png", "State chart - Booking", { maxH: 320 }),
    ...ImgPair("docs/uml/state_payment.png", "State chart - Payment of a booking", "docs/uml/state_bag.png", "State chart - Bag", { maxH: 320 }),
    H2("9.6 Sequence Diagrams"),
    P("As in Figure 7.30 of the book, each object is a box with an underlined `:Class` name, the dashed vertical line is its life line, the thin rectangle on it is its activation, and a dashed arrow is a return."),
    ...Img("docs/uml/sequence_login.png", "Sequence diagram - Login", { maxH: 380 }),
    ...Img("docs/uml/sequence_booking.png", "Sequence diagram - Book and pay for a ticket", { maxH: 540 }),
    ...Img("docs/uml/sequence_refund.png", "Sequence diagram - Cancel a booking and refund it", { maxH: 420 }),
    ...Img("docs/uml/sequence_checkin.png", "Sequence diagram - Check In Passenger and download the boarding pass", { maxH: 540 }),
    ...Img("docs/uml/sequence_schedule.png", "Sequence diagram - Generate flights", { maxH: 460 }),
    H2("9.7 Collaboration (Communication) Diagrams"),
    P("A collaboration diagram shows the same interaction as a sequence diagram but emphasises the links between objects (section 7.6 of the book); the order of messages is given by their numbers (nested numbers such as 4.2 are calls made while handling message 4). The stick figure is the actor."),
    ...ImgPair("docs/diagrams/collaboration_booking.png", "Collaboration diagram - Book and pay for a ticket",
               "docs/diagrams/collaboration_checkin.png", "Collaboration diagram - Check In Passenger and download the boarding pass", { maxH: 420 }),
  ];
}

module.exports = { ch7, ch8, ch9 };
