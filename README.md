# Airport Management System (SAD Lab Mini-Project)

A desktop Airport Management System built with **Python 3 + Tkinter + SQLite**.
It has four modules: flight scheduling, passenger booking, check-in & baggage, and
role-based login (Admin / Staff / Passenger).

The flight schedule is **recurring**: a built-in India network (21 airports including Mangalore, ~420 daily services) is turned
into real dated flights for the next 30 days every time the app starts (see *Recurring schedule* below).

## Requirements
* Python 3.9 or newer (Windows/macOS installers from python.org include Tkinter and SQLite).
* No third-party packages are needed to run the app or the tests.
* Optional: `pip install coverage pillow` (coverage report / screenshot script only).

## Run
```bash
cd AirportMS
python run.py              # first run creates data/airport.db with sample data
python run.py --reset      # wipe the database and recreate fresh sample data
```
On Windows you can also double-click **run.bat**.

> The sample flight times are generated relative to the moment the database is created
> (e.g. AI202 departs 3 hours later). This makes the check-in window rules easy to demo.
> Before a demo/viva, run `python run.py --reset` so the times are fresh.

### Demo accounts
| Role      | Username | Password  |
|-----------|----------|-----------|
| Admin     | admin    | admin123  |
| Staff     | staff1   | staff123  |
| Staff     | staff2   | staff123  |
| Passenger | priya    | pass1234  |
| Passenger | rahul    | pass1234  |
| Passenger | sneha    | pass1234  |

New passengers can register from the login screen. Only an admin can create staff/admin accounts.

### Suggested demo flow
1. **admin** -> Flights: add a flight (try a wrong date or gate `Z9` to see validation errors), assign a gate, set status, cancel a flight.
2. **priya** -> Book Flights: search `DEL`, select a flight, pick a seat on the seat map, confirm (PNR shown). Cancel a booking.
3. **staff1** -> Check-in & Baggage: enter PNR `K7Q2MA`, *Check in passenger* (boarding pass shown), add bags (17.5 and 4 kg -> excess fee Rs 3500), update bag status to LOADED.
4. **priya** -> Boarding Pass tab shows the pass. Try PNR `H2N6YE` at check-in to see "check-in opens 48 hours before departure".

## Recurring schedule
* `ams/network.py` holds a **synthetic** domestic timetable (not any airline's real one): 21 Indian airports
  (including Mangalore, IXE), 66 routes, 2-4 departures a day in each direction, paired flight numbers (outbound n, return n+1).
* Each service is a *template* (table `flight_templates`). `ScheduleService` turns templates into dated flights
  with an arrival time, a **dynamic fare** (peak hours, Fri/Sun and last-minute cost more) and an automatic
  **gate** that respects the 60-minute gate buffer. Generation is idempotent and never recreates a flight an
  admin cancelled.
* On every start `run.py` tops the schedule up to 30 days ahead (a fresh database is also seeded with the
  network). Admins can add services, switch them on/off and generate up to 90 days from the **Schedule** tab.
* New airports/routes added to the built-in network are merged into existing databases on the next start
  (services an admin switched off stay off).
* Every date field has a **drop-down calendar** (month arrows, month list, year box, Today/Clear; you can still type).
* Flight lists and searches show at most 300 rows; use the date picker or search box to narrow them.

## Payments (simulated)
Passengers pay when they book: after choosing a seat a **payment window** opens (Card, UPI or Net banking) with
the fare breakdown (base fare + airport user fee + 5% GST + convenience fee). The booking is created **only if
the demo gateway approves**, so a declined payment never holds a seat. Afterwards the passenger can download a
**PDF receipt**.
* **No real money moves.** `ams/gateway.py` is a simulator. Test values: card `4111 1111 1111 1111` is approved,
  `4000 0000 0000 0002` is declined, `4000 0000 0000 9995` has no funds, a UPI id containing "fail" is rejected,
  "Demo Bank (offline)" is unavailable. Card numbers and CVV are never stored, only a masked label.
* **Refunds:** cancelling refunds the amount paid minus the convenience fee and a cancellation charge that
  depends on how close the flight is (10% of the base fare at 48 h or more, 25% at 24-48 h, 50% at 2-24 h, 100%
  inside 2 h). If the airline cancels a flight (admin), every passenger is refunded in full. The cancel
  dialog shows the exact refund first. The numbers live in `ams/config.py`.
* **Check-in rule:** staff can only check in a passenger whose booking is paid; the check-in screen shows
  PAID / UNPAID. Admins see a Revenue tile on the dashboard.
* **Older databases:** on start-up, bookings made before payments existed are marked as paid (method LEGACY) once,
  so they can still be checked in. Unpaid bookings can be paid later with **Pay now** on My bookings.
* All fees, the tax rate and refund tiers are illustrative, not real airline policy.

## Boarding pass PDF
After check-in the boarding pass can be saved as a one-page, ticket-style **PDF**: staff use *Download boarding
pass (PDF)* on the Check-in screen, passengers use *Download PDF* on their Boarding Pass tab (only their own
passes). It has the route, passenger, flight, date, gate, seat, boarding time and a scannable **Code 128
barcode** that carries the PNR (what the counter's *Find booking* box takes). The PDF is written by
`ams/boarding_pdf.py` using only the standard library - no PDF package is needed.

## Tests
```bash
python -m unittest discover -s tests -t . -v
```
* `tests/test_blackbox.py` - black-box tests (equivalence classes + boundary values), IDs BB01-BB26
* `tests/test_whitebox.py` - white-box tests (basis paths / branch coverage), IDs WB01-WB17
* `tests/test_services.py` - unit tests per service class, IDs UT01-UT33
* `tests/test_schedule.py` - recurring schedule / flight generator tests, IDs SG01-SG27
* `tests/test_boarding_pdf.py` - boarding-pass PDF and Code 128 barcode tests, IDs BP01-BP17
* `tests/test_payments.py` - simulated payments, refunds, receipts and the check-in payment rule, IDs PY01-PY40

Tests use an in-memory database and a fixed clock, so they never touch `data/airport.db`.
Coverage (optional): `python -m coverage run --source=ams --omit="ams/gui/*" -m unittest discover -s tests -t .` then `python -m coverage report -m`.

## Project structure
```
AirportMS/
├── run.py                 # starts the GUI
├── init_db.py             # creates/resets the database only
├── run.bat                # Windows double-click launcher
├── ams/
│   ├── config.py          # business-rule constants (limits, windows, fees)
│   ├── errors.py          # exception hierarchy shown to the user
│   ├── models.py          # entity classes + status enums
│   ├── validators.py      # pure input validation
│   ├── security.py        # PBKDF2 password hashing
│   ├── access.py          # role check (require_role)
│   ├── database.py        # schema + sample data (D1 users, D2 flights, D3 bookings, D4 baggage)
│   ├── services/          # one class per module (business logic, no GUI)
│   │   ├── auth_service.py
│   │   ├── flight_service.py
│   │   ├── booking_service.py
│   │   └── checkin_service.py
│   └── gui/               # Tkinter views (call services only)
├── tests/                 # unittest suites
├── tools/capture_screenshots.py
└── docs/                  # report, diagrams, test evidence
```

## Documentation (docs/)
* `AMS_SAD_Report.docx` - the full lab report (SRS, specs, SA/SD, OOD, testing, traceability). Every diagram is drawn in the notation and page style of the textbook (Rajib Mall, *Fundamentals of Software Engineering*, 4th ed.). When Word asks to update fields on opening, click **Yes** so the table of contents fills in.
* `diagrams/` - DFDs (context, level 1-3, numbered 0, 0.1, 0.2.1 ... as in the book), use case diagrams, structure charts, collaboration diagrams, CFGs, life-cycle, decomposition, layering (PNG; Graphviz `.dot` source where Graphviz draws them)
* `uml/` - class, activity (swim lanes), state-chart and sequence diagrams (PNG + PlantUML `.puml` source, written by `tools/make_uml.py`)
* `screenshots/` - the 21 GUI screenshots and PDF pictures used in the report (`python tools/capture_screenshots.py`)
* `test_results.txt`, `coverage_report.txt` - output of the last test run
* `data_dictionary.json` - data dictionary used in the report

Regenerating the diagrams/report is optional and needs extra tools: Graphviz `dot`, Java + `plantuml.jar`
(set `AMS_DOT` / `AMS_PLANTUML` if they are not on the PATH), Pillow, and Node.js with the `docx` package
(`cd tools/report && npm install`). In this order:
```bash
python tools/make_dfds.py             # all DFDs; also checks that every level balances with its parent
python tools/make_design_diagrams.py  # life cycle, decomposition, layering, structure charts, collaboration, CFGs
python tools/make_usecase.py          # use case packaging + three use case diagrams
python tools/make_uml.py              # class, sequence, activity, state-chart diagrams (PlantUML)
python tools/data_dictionary.py       # data dictionary (checks every flow of every DFD is defined)
python tools/capture_screenshots.py   # GUI screenshots (needs a display)
python -m coverage run --source=ams --omit="ams/gui/*" -m unittest discover -s tests -t . -v > docs/test_results.txt
node tools/report/build.js            # builds docs/AMS_SAD_Report.docx from all of the above
```
`tools/dfd_spec.py` is the single source of all DFD names; `tools/bookstyle.py` holds the textbook look
(font, grey figure panel, hyphenated names) shared by all diagram scripts.

## Implemented vs. not implemented
Implemented: everything listed in the six modules above, input validation with clear error
messages, role-based access checks in the service layer, password hashing, gate-conflict check
(60-minute buffer), seat map with taken seats, check-in window (48 h to 45 min), boarding pass,
baggage tags, excess-baggage fee, baggage status tracking, flight and baggage state machines.

Not implemented (outside lab scope): real payment processing (payments are simulated), e-mail/SMS
notifications, printing straight to a physical printer (the boarding pass can be saved as a PDF and printed from the PDF viewer; the bag tag is shown on screen),
multi-user network access (SQLite single-user desktop app), connecting flights,
seat classes/pricing tiers, password reset.
