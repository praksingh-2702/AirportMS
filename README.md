# Airport Management System (SAD Lab Mini-Project)

A desktop Airport Management System built with **Python 3 + Tkinter + SQLite**.
It has four modules: flight scheduling, passenger booking, check-in & baggage, and
role-based login (Admin / Staff / Passenger).

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

## Tests
```bash
python -m unittest discover -s tests -t . -v
```
* `tests/test_blackbox.py` - black-box tests (equivalence classes + boundary values), IDs BB01-BB26
* `tests/test_whitebox.py` - white-box tests (basis paths / branch coverage), IDs WB01-WB17
* `tests/test_services.py` - unit tests per service class, IDs UT01-UT33

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
* `AMS_SAD_Report.docx` - the full lab report (SRS, specs, SA/SD, OOD, testing). When Word asks to update fields on opening, click **Yes** so the table of contents fills in.
* `diagrams/` - DFDs (context, level 1-3), use case, structure charts, collaboration diagrams, CFGs, life-cycle, decomposition, coupling (PNG + Graphviz `.dot` source)
* `uml/` - class, activity, state-chart and sequence diagrams (PNG + PlantUML `.puml` source)
* `screenshots/` - GUI screenshots used in the report
* `test_results.txt`, `coverage_report.txt` - output of the last test run
* `data_dictionary.json` - data dictionary used in the report

Regenerating the diagrams/report is optional and needs extra tools (Graphviz `dot`, Java + PlantUML,
Node.js with the `docx` package): `python tools/make_dfds.py`, `python tools/make_usecase.py`,
`python tools/make_design_diagrams.py`, `python tools/data_dictionary.py`, then `node tools/report/build.js`.
`tools/dfd_spec.py` is the single source of all DFD names; `make_dfds.py` also checks that the levels balance.

## Implemented vs. not implemented
Implemented: everything listed in the four modules above, input validation with clear error
messages, role-based access checks in the service layer, password hashing, gate-conflict check
(60-minute buffer), seat map with taken seats, check-in window (48 h to 45 min), boarding pass,
baggage tags, excess-baggage fee, baggage status tracking, flight and baggage state machines.

Not implemented (outside lab scope): real payment processing (fare is recorded only), e-mail/SMS
notifications, printing to a physical printer (boarding pass and tag are shown on screen),
multi-user network access (SQLite single-user desktop app), refunds, connecting flights,
seat classes/pricing tiers, password reset.
