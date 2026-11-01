"""Write and render every UML diagram with PlantUML (colours and font from tools/bookstyle.py):
class diagrams, sequence diagrams, activity diagrams (with swim lanes) and state chart diagrams.

The .puml sources are written to docs/uml/ so they can be edited and re-rendered with PlantUML directly.
Usage: python tools/make_uml.py     (needs Java + plantuml.jar + Graphviz; see tools/bookstyle.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookstyle as B  # noqa: E402

STYLE = f"""skinparam dpi 160
skinparam defaultFontName {B.FONT}
skinparam defaultFontSize 12
skinparam shadowing false
skinparam backgroundColor #FFFFFF
skinparam ArrowColor #333333
skinparam ActorBorderColor #333333
skinparam ActorBackgroundColor {B.YELLOW}
skinparam UsecaseBackgroundColor {B.BLUE}
skinparam UsecaseBorderColor #333333
skinparam ClassBackgroundColor #FFFFFF
skinparam ClassHeaderBackgroundColor {B.BLUE}
skinparam ClassBorderColor #333333
skinparam PackageBackgroundColor #FAFAFA
skinparam StateBackgroundColor {B.BLUE}
skinparam StateBorderColor #333333
skinparam ActivityBackgroundColor {B.BLUE}
skinparam ActivityBorderColor #333333
skinparam ActivityDiamondBackgroundColor {B.YELLOW}
skinparam ParticipantBackgroundColor {B.BLUE}
skinparam ParticipantBorderColor #333333
skinparam DatabaseBackgroundColor {B.GREY}
skinparam DatabaseBorderColor #333333
skinparam SequenceLifeLineBorderColor #777777
skinparam NoteBackgroundColor #FFFBE6
skinparam NoteBorderColor #999999
skinparam SwimlaneTitleFontStyle bold
"""

S = {}

# ============================================================ class diagrams (Figures 7.23 - 7.28 of the book)
S["class_domain"] = """@startuml
!include _style.iuml
hide empty members
package "ams.models (entity classes)" {
  enum Role {
    ADMIN
    STAFF
    PASSENGER
  }
  enum FlightStatus {
    SCHEDULED
    DELAYED
    BOARDING
    DEPARTED
    CANCELLED
  }
  enum BookingStatus {
    BOOKED
    CHECKED_IN
    CANCELLED
  }
  enum BagStatus {
    CHECKED_IN
    LOADED
    UNLOADED
    CLAIMED
    MISHANDLED
  }
  enum PaymentStatus {
    PAID
    REFUNDED
  }
  class User {
    +user_id : int
    +username : str
    +role : Role
    +full_name : str
    +email : str
    +phone : str
  }
  class Flight {
    +flight_id : int
    +flight_no : str
    +airline : str
    +origin : str
    +destination : str
    +departure : datetime
    +arrival : datetime
    +gate : str [0..1]
    +rows : int
    +fare : int
    +status : FlightStatus
    +capacity() : int
  }
  class FlightTemplate {
    +template_id : int
    +flight_no : str
    +origin : str
    +destination : str
    +dep_time : str
    +duration_min : int
    +days : str
    +base_fare : int
    +active : bool
    +days_label() : str
  }
  class Booking {
    +booking_id : int
    +pnr : str
    +seat : str
    +fare : int
    +status : BookingStatus
    +booked_at : datetime
    +boarding_seq : int [0..1]
  }
  class Bag {
    +bag_id : int
    +tag_no : str
    +weight_kg : float
    +status : BagStatus
  }
  class BoardingPass {
    +pnr : str
    +passenger_name : str
    +flight_no : str
    +boarding_time : datetime
    +gate : str [0..1]
    +seat : str
    +boarding_seq : int
    +as_text() : str
  }
  class Payment {
    +payment_id : int
    +invoice_no : str
    +method : str
    +instrument : str
    +amount : int
    +status : PaymentStatus
    +reference : str
    +paid_at : datetime
    +refund_amount : int
    +refund_reason : str [0..1]
  }
  class FareBreakdown {
    +base_fare : int
    +airport_fee : int
    +gst : int
    +convenience_fee : int
    +total() : int
  }
  class RefundQuote {
    +refund : int
    +charge : int
    +percent : int
    +convenience_fee : int
  }
}
User "1" -- "*" Booking : holds >
Flight "1" -- "*" Booking : carries >
Booking "1" -- "*" Bag : has >
Booking "1" -- "0..1" Payment : is paid by >
Payment *-- "1" FareBreakdown
FlightTemplate "1" -- "*" Flight : generates >
BoardingPass ..> Booking : built from
RefundQuote ..> Payment : computed from
User ..> Role
Flight ..> FlightStatus
Booking ..> BookingStatus
Bag ..> BagStatus
Payment ..> PaymentStatus
@enduml
"""

S["class_services"] = """@startuml
!include _style.iuml
hide empty members
package "ams.services (one class per module)" {
  class AuthService {
    +login(username, password) : User
    +register_passenger(...) : User
    +create_staff_account(actor, ...) : User
    +list_users(actor) : list
  }
  class FlightService {
    +list_flights(statuses, date, search, limit) : list
    +count_flights(...) : int
    +booked_counts() : dict
    +add_flight(actor, ...) : Flight
    +update_flight(actor, id, ...) : Flight
    +assign_gate(actor, id, gate) : Flight
    +change_status(actor, id, status) : Flight
    +cancel_flight(actor, id, now) : int
    +is_gate_available(gate, departure) : bool
  }
  class ScheduleService {
    +list_templates() : list
    +add_template(actor, ...) : FlightTemplate
    +set_active(actor, id, active) : FlightTemplate
    +seed_default_network() : int
    +generate_flights(actor, days, now) : GenerationResult
    +ensure_schedule(days, now) : GenerationResult
  }
  class GatePlanner {
    +assign(departure) : str
  }
  class BookingService {
    +search_flights(origin, dest, date, now, limit) : list
    +get_taken_seats(flight_id) : set
    +book_ticket(actor, flight_id, seat, now) : Booking
    +cancel_booking(actor, id, now) : Booking
    +list_bookings(actor) : list
  }
  class PaymentService {
    +quote(base_fare) : FareBreakdown
    +book_and_pay(actor, flight_id, seat, method, details, now) : tuple
    +pay_booking(actor, id, method, details, now) : Payment
    +refund_quote(id, now) : RefundQuote
    +receipt_file(actor, id) : tuple
    +migrate_legacy(now) : int
    +revenue() : int
  }
  class CheckInService {
    +find_booking(pnr) : BookingDetails
    +check_in(actor, pnr, now) : BoardingPass
    +get_boarding_pass(actor, pnr) : BoardingPass
    +boarding_pass_file(actor, pnr) : tuple
    +add_bag(actor, pnr, weight, now) : Bag
    +update_bag_status(actor, id, status, now) : Bag
    +baggage_summary(pnr) : tuple
  }
}
package "helper modules" {
  class payments_core <<module>> {
    +fare_breakdown(base_fare)
    +quote_refund(payment, hours, full)
    +refund_booking(conn, id, now, full, reason)
    +refund_flight(conn, flight_id, now)
    +record_payment(conn, ...)
  }
  class gateway <<module>> {
    +authorize(method, details, amount) : GatewayResult
  }
  class boarding_pdf <<module>> {
    +render_boarding_pass(pass) : bytes
    +code128_widths(text) : list
  }
  class receipt_pdf <<module>> {
    +render_receipt(payment, ...) : bytes
  }
  class validators <<module>>
  class access <<module>> {
    +require_role(actor, roles)
  }
}
ScheduleService *-- GatePlanner
PaymentService o-- BookingService : uses >
PaymentService ..> gateway
PaymentService ..> payments_core
PaymentService ..> receipt_pdf
BookingService ..> payments_core : refund
FlightService ..> payments_core : refund all
CheckInService ..> boarding_pdf
CheckInService ..> BookingService : DETAILS_SQL
AuthService ..> access
FlightService ..> access
ScheduleService ..> access
BookingService ..> access
PaymentService ..> access
CheckInService ..> access
AuthService ..> validators
FlightService ..> validators
ScheduleService ..> validators
BookingService ..> validators
PaymentService ..> validators
CheckInService ..> validators
@enduml
"""

S["class_gui"] = """@startuml
!include _style.iuml
hide empty members
package "ams.gui (presentation layer)" {
  class AirportApp {
    +show_login()
    +show_dashboard(user)
    +refresh_stats()
  }
  class AppContext {
    +auth : AuthService
    +flights : FlightService
    +schedule : ScheduleService
    +bookings : BookingService
    +payments : PaymentService
    +checkin : CheckInService
    +user : User
    +now() : datetime
    +stats() : list
  }
  class Header
  class TabHost {
    +add(view, text)
    +select(view)
  }
  class StatCard {
    +set(value)
  }
  class LoginView {
    +login()
    +open_register()
  }
  class RegisterDialog
  class FlightView {
    +refresh(quiet)
    +add()  +update()  +cancel()
  }
  class ScheduleView {
    +generate()
    +add()  +toggle()
  }
  class BookingView {
    +search()
    +book()
    +pay_selected()
    +download_receipt()
    +cancel()
  }
  class SeatMap {
    +pick(seat)
    +confirm()
  }
  class PaymentDialog {
    +pay()
    +download_receipt()
  }
  class CheckInView {
    +lookup()
    +check_in()
    +download()
    +add_bag()
  }
  class BoardingPassView {
    +refresh()
    +download()
  }
  class UsersView
  class DataTable {
    +load(rows)
    +selected_id()
  }
  class FormPanel
  class DateEntry
  class CalendarPopup
  class Button
}
AirportApp *-- AppContext
AirportApp *-- Header
AirportApp *-- TabHost
AirportApp *-- "4" StatCard
TabHost o-- "*" FlightView
TabHost o-- "*" ScheduleView
TabHost o-- "*" BookingView
TabHost o-- "*" CheckInView
TabHost o-- "*" BoardingPassView
TabHost o-- "*" UsersView
AirportApp ..> LoginView : shows
LoginView ..> RegisterDialog
BookingView ..> SeatMap : opens
BookingView ..> PaymentDialog : opens
FlightView *-- DataTable
BookingView *-- DataTable
ScheduleView *-- DataTable
CheckInView *-- DataTable
BoardingPassView *-- DataTable
FlightView *-- FormPanel
ScheduleView *-- FormPanel
UsersView *-- FormPanel
FormPanel o-- DateEntry
FlightView *-- DateEntry
BookingView *-- DateEntry
DateEntry ..> CalendarPopup : opens
FlightView ..> AppContext : uses services
BookingView ..> AppContext
CheckInView ..> AppContext
PaymentDialog ..> AppContext
@enduml
"""

# ============================================================ sequence diagrams (Figure 7.30 style)
S["sequence_login"] = """@startuml
!include _style.iuml
participant ":LoginView" as LV
participant ":AuthService" as AS
participant ":security" as SEC
database ":Database" as DB
participant ":AirportApp" as APP
[-> LV : login(username, password)
activate LV
LV -> AS : login(username, password)
activate AS
alt blank field
  AS --> LV : [blank] ValidationError
else
  AS -> DB : SELECT user
  DB --> AS : row / none
  AS -> SEC : verify_password(pw, hash, salt)
  SEC --> AS : True / False
  alt no row or wrong password
    AS --> LV : [invalid] AuthenticationError
    LV --> LV : error dialog, shake card
  else valid
    AS --> LV : User
    deactivate AS
    LV -> APP : show_dashboard(user)
    activate APP
    APP -> APP : build tabs for the role
    deactivate APP
  end
end
deactivate LV
@enduml
"""

S["sequence_booking"] = """@startuml
!include _style.iuml
participant ":BookingView" as BV
participant ":SeatMap" as SM
participant ":PaymentDialog" as PD
participant ":PaymentService" as PS
participant ":BookingService" as BS
participant ":Gateway" as GW
database ":Database" as DB
[-> BV : book()
activate BV
BV -> BS : get_taken_seats(flight_id)
BS -> DB : SELECT seats
DB --> BS : seats
BS --> BV : taken
BV -> SM ** : SeatMap(flight, taken)
SM --> BV : on_pick(seat)
BV -> PD ** : PaymentDialog(fare breakdown)
activate PD
PD -> PS : book_and_pay(user, flight, seat, method, details)
activate PS
PS -> PS : validate details
PS -> BS : book_ticket(user, flight, seat)
activate BS
BS -> DB : INSERT booking
BS --> PS : Booking
deactivate BS
PS -> GW : authorize(method, details, amount)
alt [declined]
  GW --> PS : declined
  PS -> DB : DELETE booking
  PS --> PD : PaymentError
  PD --> PD : show reason, allow retry
else [approved]
  GW --> PS : approved
  PS -> DB : INSERT payment
  PS --> PD : (booking, payment)
  deactivate PS
  PD --> PD : success screen (PNR, invoice)
  PD --> BV : on_done()
end
deactivate PD
BV -> BV : refresh tables
deactivate BV
@enduml
"""

S["sequence_checkin"] = """@startuml
!include _style.iuml
participant ":CheckInView" as CV
participant ":CheckInService" as CS
participant ":access" as AC
participant ":validators" as V
database ":Database" as DB
participant ":BoardingPass" as BP
participant ":boarding_pdf" as PDF
[-> CV : check_in()
activate CV
CV -> CS : check_in(user, pnr, now)
activate CS
CS -> AC : require_role(STAFF, ADMIN)
CS -> V : validate_pnr(pnr)
CS -> DB : SELECT booking, flight, passenger
DB --> CS : row
alt [cancelled / checked in / flight not operating]
  CS --> CV : BusinessRuleError
else [no PAID payment]
  CS -> DB : SELECT payment
  CS --> CV : BusinessRuleError(payment pending)
else [outside 48 h .. 45 min window]
  CS --> CV : BusinessRuleError(window)
else eligible
  CS -> DB : SELECT MAX(boarding_seq) + 1
  CS -> DB : UPDATE booking CHECKED_IN
  CS -> BP ** : BoardingPass(...)
  CS --> CV : BoardingPass
  deactivate CS
  CV -> BP : as_text()
  CV --> CV : show pass, enable download
end
deactivate CV
[-> CV : download()
activate CV
CV -> CS : boarding_pass_file(user, pnr)
activate CS
CS -> PDF : render_boarding_pass(pass)
PDF --> CS : pdf bytes
CS --> CV : (file name, bytes)
deactivate CS
CV --> CV : save dialog, write file
deactivate CV
@enduml
"""

S["sequence_refund"] = """@startuml
!include _style.iuml
participant ":BookingView" as BV
participant ":PaymentService" as PS
participant ":BookingService" as BS
participant ":payments_core" as PC
database ":Database" as DB
[-> BV : cancel()
activate BV
BV -> PS : refund_quote(booking_id, now)
PS -> DB : SELECT payment, departure
PS --> BV : RefundQuote
BV --> BV : confirm dialog shows refund and charges
BV -> BS : cancel_booking(user, booking_id, now)
activate BS
BS -> DB : UPDATE booking CANCELLED
BS -> PC : refund_booking(booking_id, now, full=False)
activate PC
PC -> PC : quote_refund(payment, hours)
PC -> DB : UPDATE payment REFUNDED
deactivate PC
BS --> BV : Booking
deactivate BS
BV --> BV : show "refunded to (instrument)"
deactivate BV
@enduml
"""

S["sequence_schedule"] = """@startuml
!include _style.iuml
participant ":ScheduleView" as SV
participant ":ScheduleService" as SS
participant ":GatePlanner" as GP
database ":Database" as DB
[-> SV : generate()
activate SV
SV -> SS : generate_flights(admin, days, now)
activate SS
SS -> SS : validate_horizon_days(days)
SS -> DB : SELECT existing (flight_no, date)
SS -> DB : SELECT busy gates
SS -> GP ** : GatePlanner(busy)
loop for each active service and each day
  alt runs that weekday, departure in future, not yet created
    SS -> SS : dynamic_fare(base, departure, now)
    SS -> GP : assign(departure)
    GP --> SS : gate
  end
end
SS -> DB : INSERT flights (one batch)
SS --> SV : GenerationResult(created, skipped, through)
deactivate SS
SV --> SV : show summary, refresh
deactivate SV
@enduml
"""

# ============================================================ activity diagrams (Figure 7.32 style, swim lanes)
S["activity_booking"] = """@startuml
!include _style.iuml
|Passenger|
start
:Search flights (From / To / date);
|System|
:Display bookable flights with seats left;
|Passenger|
:Select a flight;
|System|
if (Passenger already holds\\na booking on it?) then (yes)
  :Show "already booked";
  stop
endif
:Show seat map\\n(taken seats disabled);
|Passenger|
:Pick a free seat;
|System|
:Show fare breakdown\\nand payment window;
|Passenger|
:Choose Card / UPI / Net banking\\nand enter the details;
|System|
if (Details valid?) then (no)
  :Show the problem;
  stop
endif
:Reserve the seat;
|Payment Gateway|
:Authorize the payment;
|System|
if (Approved?) then (no)
  :Release the seat;
  :Show the bank's reason;
  stop
endif
:Generate unique PNR;
:Save booking and payment;
:Show PNR and invoice;
|Passenger|
:Download receipt (optional);
stop
@enduml
"""

S["activity_checkin"] = """@startuml
!include _style.iuml
|Check-in Staff|
start
:Enter passenger PNR;
|System|
if (PNR valid and booking exists?) then (no)
  :Show error;
  stop
endif
:Display booking details\\nand payment status;
|Check-in Staff|
:Click "Check in passenger";
|System|
if (Cancelled or already checked in?) then (yes)
  :Show reason;
  stop
endif
if (Flight cancelled or departed?) then (yes)
  :Show reason;
  stop
endif
if (Booking paid?) then (no)
  :Show "payment pending";
  stop
endif
if (Within 48 h .. 45 min\\nbefore departure?) then (no)
  :Show "check-in opens / closed";
  stop
endif
:Assign next boarding sequence;
:Set booking CHECKED_IN;
:Generate boarding pass;
fork
  |Check-in Staff|
  :Hand over boarding pass\\n(download PDF if needed);
fork again
  |Check-in Staff|
  while (Another bag?) is (yes)
    :Weigh bag and enter weight;
    |System|
    if (0 < weight <= 32 kg\\nand fewer than 3 bags?) then (yes)
      :Save bag, generate tag;
      :Recompute weight and excess fee;
    else (no)
      :Show error;
    endif
    |Check-in Staff|
  endwhile (no)
  :Attach tags, collect excess fee;
end fork
stop
@enduml
"""

S["activity_schedule"] = """@startuml
!include _style.iuml
|Administrator|
start
:Open Flights tab;
:Enter flight details\\n(dates chosen on the calendar);
:Click "Add flight";
|System|
if (Role = ADMIN?) then (no)
  :Show "Access denied";
  stop
endif
if (All fields valid?) then (no)
  :Show field-specific error;
  stop
endif
if (Same flight no. already\\non that date?) then (yes)
  :Show duplicate error;
  stop
endif
if (Gate given and another active\\nflight at it within 60 min?) then (yes)
  :Show gate conflict error;
  stop
endif
:Insert flight (status SCHEDULED);
:Refresh schedule table;
|Administrator|
:See new flight in schedule;
stop
@enduml
"""

S["activity_generate"] = """@startuml
!include _style.iuml
|Administrator|
start
:Open Schedule tab;
:Enter number of days;
:Click "Generate flights";
|System|
if (Days between 1 and 90?) then (no)
  :Show error;
  stop
endif
:Read active recurring services;
:Read flights that already exist;
while (Next service and day?) is (yes)
  if (Runs that weekday and\\ndeparts in the future?) then (no)
  else (yes)
    if (Flight already exists\\n(or was cancelled)?) then (yes)
      :Count as skipped;
    else (no)
      :Price the flight (dynamic fare);
      :Plan a free gate (60-minute rule);
      :Add to batch;
    endif
  endif
endwhile (no)
:Insert all new flights;
:Show created / skipped summary;
|Administrator|
stop
@enduml
"""

# ============================================================ state chart diagrams (Figure 7.33 style)
S["state_booking"] = """@startuml
!include _style.iuml
hide empty description
[*] --> BOOKED : book_ticket()\\n[seat free, flight bookable]
BOOKED --> CHECKED_IN : check_in()\\n[paid, 48 h >= time to dep >= 45 min]\\n/ assign boarding_seq
BOOKED --> CANCELLED : cancel_booking()\\n[before departure]\\n/ refund
BOOKED --> CANCELLED : cancel_flight()\\n/ full refund
CHECKED_IN --> CANCELLED : cancel_flight()\\n/ full refund
CHECKED_IN --> [*]
CANCELLED --> [*]
BOOKED : seat held
CHECKED_IN : boarding pass available\\nbags can be added
CANCELLED : seat released
@enduml
"""

S["state_flight"] = """@startuml
!include _style.iuml
hide empty description
[*] --> SCHEDULED : add_flight() / generate_flights()
SCHEDULED --> DELAYED : change_status(DELAYED)
DELAYED --> SCHEDULED : change_status(SCHEDULED)
SCHEDULED --> BOARDING : change_status(BOARDING)
DELAYED --> BOARDING : change_status(BOARDING)
BOARDING --> DELAYED : change_status(DELAYED)
BOARDING --> DEPARTED : change_status(DEPARTED)
SCHEDULED --> CANCELLED : cancel_flight()\\n/ cancel bookings, refund, free gate
DELAYED --> CANCELLED : cancel_flight()\\n/ cancel bookings, refund, free gate
DEPARTED --> [*]
CANCELLED --> [*]
SCHEDULED : bookable, editable
DELAYED : bookable, editable
BOARDING : not bookable
DEPARTED : final
CANCELLED : final
@enduml
"""

S["state_bag"] = """@startuml
!include _style.iuml
hide empty description
[*] --> CHECKED_IN : add_bag()\\n/ generate tag
CHECKED_IN --> LOADED : update_bag_status(LOADED)
LOADED --> UNLOADED : update_bag_status(UNLOADED)
UNLOADED --> CLAIMED : update_bag_status(CLAIMED)
CHECKED_IN --> MISHANDLED : update_bag_status(MISHANDLED)
LOADED --> MISHANDLED : update_bag_status(MISHANDLED)
UNLOADED --> MISHANDLED : update_bag_status(MISHANDLED)
MISHANDLED --> CLAIMED : update_bag_status(CLAIMED)
CLAIMED --> [*]
@enduml
"""

S["state_payment"] = """@startuml
!include _style.iuml
hide empty description
[*] --> UNPAID : book_ticket()\\n(booking without payment)
[*] --> PAID : book_and_pay()\\n[gateway approves]
UNPAID --> PAID : pay_booking()\\n[gateway approves]
PAID --> REFUNDED : cancel_booking()\\n/ refund minus charges
PAID --> REFUNDED : cancel_flight()\\n/ full refund
UNPAID --> [*] : cancel_booking()\\n(nothing to refund)
REFUNDED --> [*]
UNPAID : cannot be checked in
PAID : receipt available\\ncheck-in allowed
REFUNDED : refund_amount recorded
@enduml
"""


def main():
    os.makedirs(B.UML, exist_ok=True)
    with open(os.path.join(B.UML, "_style.iuml"), "w", encoding="utf-8") as fh:
        fh.write(STYLE)
    for name, src in S.items():
        path = os.path.join(B.UML, f"{name}.puml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        B.run_plantuml(path, B.UML)
        print("rendered", name)


if __name__ == "__main__":
    main()
