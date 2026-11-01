"""Render the remaining design diagrams with Graphviz (look defined in tools/bookstyle.py):
life-cycle model, decomposition tree, module layering, structure charts (transaction + transform
analysis), collaboration diagrams and white-box control-flow graphs (CFGs).
Usage: python tools/make_design_diagrams.py   (needs Graphviz; Pillow for the actor figure)
"""
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookdraw as D  # noqa: E402
import bookstyle as B  # noqa: E402

OUT = B.DIAGRAMS
DATA = "○"     # data couple
FLAG = "●"     # control flag


# ------------------------------------------------------------------ life cycle
def lifecycle():
    phases = ["Feasibility Study", "Requirements Analysis\\n& Specification (SRS)", "Design\\n(SA/SD + OOD)",
              "Coding &\\nUnit Testing", "Integration &\\nSystem Testing", "Maintenance"]
    L = B.graph_header("lifecycle", "TB", "nodesep=0.4 ranksep=0.35")
    L.append('  node [shape=box style="rounded,filled" width=2.3 height=0.8];')
    for i, p in enumerate(phases):
        L.append(f'  p{i} [label="{p}"];')
    for i in range(len(phases) - 1):
        L.append(f'  p{i} -> p{i + 1} [weight=10 color="#333333"];')
        L.append(f'  p{i + 1} -> p{i} [style=dashed color="#C62828" constraint=false label="feedback" fontcolor="#C62828"];')
    B.run_dot("lifecycle_iterative_waterfall", "\n".join(L) + "\n}")


# ------------------------------------------------------------------ decomposition
def decomposition():
    tree = {
        "Airport Management System": ["Login & Accounts", "Flight Scheduling", "Recurring Schedule",
                                      "Passenger Booking", "Payments", "Check-in & Baggage"],
        "Login & Accounts": ["Verify credentials", "Register passenger", "Create staff account", "List users"],
        "Flight Scheduling": ["Add / update flight", "Check gate availability", "Assign gate", "Change status",
                              "Cancel flight"],
        "Recurring Schedule": ["Add recurring service", "Switch service on/off", "Generate flights",
                               "Price flight", "Plan gates"],
        "Passenger Booking": ["Search flights", "Show seat map", "Book ticket", "Cancel booking", "List bookings"],
        "Payments": ["Compute fare breakdown", "Validate payment details", "Authorize payment", "Record payment",
                     "Refund payment", "Issue receipt PDF"],
        "Check-in & Baggage": ["Find booking by PNR", "Check payment status", "Check in",
                               "Boarding pass + PDF", "Add bag + tag", "Excess fee", "Bag status"],
    }
    L = B.graph_header("decomposition", "LR", "nodesep=0.12 ranksep=0.9 splines=line")
    L.append('  node [shape=box fillcolor="white"];')
    ids = {}

    def nid(name):
        return ids.setdefault(name, f"n{len(ids)}")
    for parent, children in tree.items():
        color = B.BLUE if parent == "Airport Management System" else B.YELLOW
        L.append(f'  {nid(parent)} [label="{parent}" fillcolor="{color}" penwidth=1.5];')
        for c in children:
            if c not in tree:
                L.append(f'  {nid(c)} [label="{c}" fontsize=11];')
            L.append(f"  {nid(parent)} -> {nid(c)} [arrowhead=none];")
    B.run_dot("decomposition", "\n".join(L) + "\n}")


# ------------------------------------------------------------------ layering / coupling
def coupling():
    L = B.graph_header("module_coupling", "TB", "nodesep=0.3 ranksep=0.7 compound=true")
    L.append('  node [shape=box];')

    def cluster(cid, title, nodes, fill=B.BLUE):
        body = " ".join(f'{k} [label="{v}" fillcolor="{fill}"];' for k, v in nodes.items())
        L.append(f'  subgraph cluster_{cid} {{ label="{title}" style=dashed fontname="{B.FONT}" {body} }}')
    cluster("gui", "Presentation layer (ams.gui)", {
        "app": "AirportApp / AppContext", "lv": "LoginView", "fv": "FlightView", "sv": "ScheduleView",
        "bv": "BookingView", "pd": "PaymentDialog", "cv": "CheckInView", "uv": "UsersView"})
    cluster("svc", "Service layer (ams.services)", {
        "as": "AuthService", "fs": "FlightService", "ss": "ScheduleService", "bs": "BookingService",
        "ps": "PaymentService", "cs": "CheckInService"})
    cluster("util", "Utility / data layer", {
        "val": "validators", "acc": "access", "sec": "security", "mod": "models", "cfg": "config",
        "gw": "gateway", "pc": "payments_core", "pdf": "boarding_pdf, receipt_pdf"}, B.YELLOW)
    L.append(f'  db [shape=cylinder fillcolor="{B.GREY}" label="SQLite\\nairport.db"];')
    for a, b in [("app", "lv"), ("app", "fv"), ("app", "sv"), ("app", "bv"), ("app", "cv"), ("app", "uv"),
                 ("bv", "pd"), ("lv", "as"), ("uv", "as"), ("fv", "fs"), ("sv", "ss"), ("bv", "bs"), ("bv", "fs"),
                 ("pd", "ps"), ("cv", "cs"), ("cv", "bs"), ("cv", "ps")]:
        L.append(f"  {a} -> {b};")
    # every service uses validators, access and models, and every service reads/writes the database:
    # drawn once, from the service layer as a whole (compound edges), to keep the figure readable
    L.append('  fs -> mod [ltail=cluster_svc lhead=cluster_util color="#777777" penwidth=1.4 label="every service:\\nvalidators, access,\\nmodels"];')
    L.append('  bs -> db [ltail=cluster_svc color="#1E3A5F" penwidth=1.6 label="every service\\n(SQL)"];')
    L.append('  as -> sec [color="#777777"]; ps -> gw; ps -> pc; bs -> pc; fs -> pc; ps -> pdf; cs -> pdf;')
    L.append('  cs -> bs [style=dashed label="DETAILS_SQL"]; ps -> bs [style=dashed];')
    L.append("  val -> cfg; pc -> cfg;")
    B.run_dot("module_coupling", "\n".join(L) + "\n}")


# ------------------------------------------------------------------ structure charts
def chart(name, nodes, edges, title, select=None, library=()):
    """nodes: id -> label; edges: (parent, child, [down couples], [up couples]).
    A couple starting with '!' is a control flag (drawn ●), otherwise a data couple (○).
    `select`: module whose calls go through a selection diamond. `library`: double-edged modules."""
    L = B.graph_header(name, "TB", "nodesep=0.35 ranksep=0.9")
    L.append('  node [shape=box style=filled fillcolor="white" width=1.6];')
    L.append(f'  labelloc=t label="{title}" fontsize=14;')
    for nid_, label in nodes.items():
        fill = B.BLUE if nid_ == "root" else ("#E8F5E9" if nid_ == select else "white")
        periph = " peripheries=2" if nid_ in library else ""
        L.append(f'  {nid_} [label="{label}" fillcolor="{fill}"{periph}];')
    if select:
        L.append(f'  {select}_sel [shape=diamond label="" width=0.35 height=0.35 style=filled fillcolor="{B.YELLOW}"];')
        L.append(f'  {select} -> {select}_sel [arrowhead=none];')

    def couple(c, arrow):
        return f"{FLAG} {c[1:]} {arrow}" if c.startswith("!") else f"{DATA} {c} {arrow}"
    for parent, child, down, up in edges:
        src = f"{parent}_sel" if select and parent == select else parent
        label = "\\n".join([couple(c, "↓") for c in down] + [couple(c, "↑") for c in up])
        L.append(f'  {src} -> {child} [label="{label}" arrowsize=0.7];')
    L.append(f'  legend [shape=note fillcolor="{B.GREY}" fontsize=10 label="{DATA} data couple   {FLAG} control flag\\n'
             f'↓ passed to called module   ↑ returned to caller\\ndouble border = library module"];')
    B.run_dot(name, "\n".join(L) + "\n}")


def structure_charts():
    # 1. Transaction analysis: the dashboard dispatches one of several transaction types
    chart("structure_chart_transaction", {
        "root": "AirportApp\\n(main)", "login": "Get Login\\nLoginView.login()", "a1": "AuthService\\nlogin()",
        "disp": "Dispatch Transaction\\nshow_dashboard(user)",
        "t1": "Flight Scheduling\\nFlightView", "t7": "Recurring Schedule\\nScheduleView",
        "t2": "Passenger Booking\\nBookingView", "t3": "Check-in & Baggage\\nCheckInView",
        "t4": "User Management\\nUsersView", "t5": "Boarding Pass\\nBoardingPassView",
    }, [
        ("root", "login", [], ["user"]),
        ("login", "a1", ["username, password"], ["user", "!auth_ok"]),
        ("root", "disp", ["user", "!role"], []),
        ("disp", "t1", ["ctx"], []), ("disp", "t7", ["ctx"], []), ("disp", "t2", ["ctx"], []),
        ("disp", "t3", ["ctx"], []), ("disp", "t4", ["ctx"], []), ("disp", "t5", ["ctx"], []),
    ], "Structure Chart 1 - Transaction Analysis (role-based dashboard)", select="disp")

    # 2. Transform analysis: Check In Passenger (DFD 0.5)
    chart("structure_chart_transform_checkin", {
        "root": "Check In Passenger\\nCheckInService.check_in()",
        "aff": "Get Booking Details\\nfind_booking()", "vp": "Validate PNR\\nvalidate_pnr()",
        "fb": "Fetch Booking Row\\nDETAILS_SQL query",
        "ce": "Verify Eligibility\\n(status, payment, window)", "pay": "Check Payment Status\\nSELECT payments (PAID)",
        "win": "Check Time Window\\n48 h / 45 min",
        "seq": "Assign Boarding Seq\\nMAX(seq)+1, UPDATE",
        "eff": "Produce Boarding Pass\\nget_boarding_pass()", "fmt": "Format Pass\\nBoardingPass.as_text()",
        "pdf": "Export Pass PDF\\nrender_boarding_pass()",
    }, [
        ("root", "aff", [], ["booking_details"]),
        ("aff", "vp", ["raw_pnr"], ["pnr"]),
        ("aff", "fb", ["pnr"], ["booking_details"]),
        ("root", "ce", ["booking_details", "now"], ["!eligible"]),
        ("ce", "pay", ["booking_id"], ["!paid"]),
        ("ce", "win", ["departure", "now"], ["!window_open"]),
        ("root", "seq", ["booking_id"], ["boarding_seq"]),
        ("root", "eff", ["pnr"], ["boarding_pass"]),
        ("eff", "fmt", ["boarding_pass"], ["pass_text"]),
        ("eff", "pdf", ["boarding_pass"], ["pdf_bytes"]),
    ], "Structure Chart 2 - Transform Analysis of DFD 0.5 (Check In Passenger)", library=("vp",))

    # 3. Transform analysis: Book Ticket (DFD 0.4)
    chart("structure_chart_transform_booking", {
        "root": "Book Ticket\\nBookingService.book_ticket()",
        "aff": "Get Valid Request", "gf": "Get Flight\\nSELECT flights", "ps": "Validate Seat\\nparse_seat()",
        "chk": "Check Seat & Duplicate\\nget_taken_seats()", "pnr": "Generate PNR\\n_unique_pnr()",
        "eff": "Record & Confirm", "ins": "Insert Booking\\nINSERT bookings", "msg": "Show Confirmation\\nBookingView",
    }, [
        ("root", "aff", ["flight_id, seat"], ["flight, seat"]),
        ("aff", "gf", ["flight_id"], ["flight", "!bookable"]),
        ("aff", "ps", ["seat, rows"], ["seat"]),
        ("root", "chk", ["flight_id, seat, user_id"], ["!seat_free"]),
        ("root", "pnr", [], ["pnr"]),
        ("root", "eff", ["pnr, flight, seat"], ["booking"]),
        ("eff", "ins", ["booking row"], ["booking_id"]),
        ("eff", "msg", ["booking"], []),
    ], "Structure Chart 3 - Transform Analysis of DFD 0.4 (Book Ticket)", library=("ps",))

    # 4. Transform analysis: Process Payment (DFD 0.8) - book_and_pay()
    chart("structure_chart_transform_payment", {
        "root": "Book and Pay\\nPaymentService.book_and_pay()",
        "aff": "Get Valid Payment Details\\n_clean(method, details)",
        "card": "Validate Card Details\\nvalidate_card_number/expiry/cvv", "upi": "Validate UPI ID\\nvalidate_upi_id()",
        "bank": "Validate Bank\\nvalidate_bank()",
        "res": "Reserve Seat\\nbook_ticket()", "auth": "Authorize Payment\\nfare_breakdown()",
        "gw": "Payment Gateway\\ngateway.authorize()",
        "eff": "Record Payment\\nrecord_payment()", "rel": "Release Seat\\nDELETE booking",
    }, [
        ("root", "aff", ["method, details"], ["clean_details"]),
        ("aff", "card", ["card details"], ["valid_card"]),
        ("aff", "upi", ["upi_id"], ["upi_id"]),
        ("aff", "bank", ["bank"], ["bank"]),
        ("root", "res", ["flight_id, seat"], ["booking"]),
        ("root", "auth", ["clean_details, fare"], ["result"]),
        ("auth", "gw", ["method, details, amount"], ["!approved"]),
        ("root", "eff", ["booking, result"], ["payment"]),
        ("root", "rel", ["booking_id"], []),
    ], "Structure Chart 4 - Transform Analysis of DFD 0.8 (Process Payment)", select="aff",
        library=("card", "upi", "bank"))

    # 5. Transform analysis: Generate Flights (DFD 0.7) - ScheduleService
    chart("structure_chart_transform_schedule", {
        "root": "Generate Flights\\nScheduleService.generate_flights()",
        "aff": "Get Due Services", "ls": "List Active Services\\nlist_templates()",
        "ex": "Read Existing Flights\\nSELECT flights",
        "price": "Price Flight", "fare": "Dynamic Fare\\ndynamic_fare()",
        "plan": "Plan Gates", "gp": "Gate Planner\\n_GatePlanner.assign()",
        "eff": "Create Flights", "ins": "Insert Flights\\nINSERT flights", "sum": "Summarise Generation\\nGenerationResult",
    }, [
        ("root", "aff", ["days"], ["due_services"]),
        ("aff", "ls", [], ["services"]),
        ("aff", "ex", ["date range"], ["existing flights"]),
        ("root", "price", ["due_services"], ["priced flights"]),
        ("price", "fare", ["base_fare, departure"], ["fare"]),
        ("root", "plan", ["priced flights"], ["planned flights"]),
        ("plan", "gp", ["departure"], ["gate"]),
        ("root", "eff", ["planned flights"], ["count"]),
        ("eff", "ins", ["flight rows"], []),
        ("eff", "sum", ["count"], ["summary"]),
    ], "Structure Chart 5 - Transform Analysis of DFD 0.7 (Generate Flights)", library=("fare",))


# ------------------------------------------------------------------ collaboration diagrams
def collaboration(name, objects, messages, title):
    """objects: id -> label ('actor' draws the stick figure); messages: (from, to, 'n: text').
    Messages between the same two objects are written on one link, with an arrow showing direction."""
    actor_png = os.path.join(OUT, "_actor.png")
    D.stick_figure(actor_png)
    L = B.graph_header(name, "TB", "nodesep=0.6 ranksep=1.0")
    L.append('  node [shape=box fontsize=13]; edge [fontsize=12 dir=none];')
    L.append(f'  labelloc=t label="{title}" fontsize=16;')
    for oid, label in objects.items():
        if oid == "actor":
            L.append(f'  actor [shape=none style=none image="{actor_png}" labelloc=b height=1.6 label="{label}"];')
        else:
            L.append(f'  {oid} [label=<<U>{label}</U>>];')
    links = OrderedDict()
    for a, b, text in messages:
        key = (a, b) if (b, a) not in links else (b, a)
        arrow = "→" if key == (a, b) else "←"
        links.setdefault(key, []).append(f"{text} {arrow}")
    newline = "\\n"
    for (a, b), msgs in links.items():
        L.append(f'  {a} -> {b} [label="{newline.join(msgs)}"];')
    B.run_dot(name, "\n".join(L) + "\n}")


def collaborations():
    collaboration("collaboration_booking", {
        "actor": "Passenger", "bv": ":BookingView", "pd": ":PaymentDialog", "ps": ":PaymentService",
        "bs": ":BookingService", "gw": ":Gateway", "db": ":SQLite DB"},
        [("actor", "bv", "1: select flight and seat"),
         ("bv", "pd", "2: open(fare breakdown)"),
         ("actor", "pd", "3: pay(method, details)"),
         ("pd", "ps", "4: book_and_pay(user, flight, seat, ...)"),
         ("ps", "bs", "4.1: book_ticket(user, flight, seat)"),
         ("bs", "db", "4.2: INSERT booking"),
         ("ps", "gw", "4.3: authorize(method, details, amount)"),
         ("gw", "ps", "4.4: approved / declined"),
         ("ps", "db", "4.5: INSERT payment"),
         ("ps", "pd", "4.6: (booking, payment)"),
         ("pd", "actor", "5: payment successful (PNR, invoice)")],
        "Collaboration Diagram - Book and Pay")
    collaboration("collaboration_checkin", {
        "actor": "Check-in Staff", "cv": ":CheckInView", "cs": ":CheckInService", "db": ":SQLite DB",
        "bp": ":BoardingPass", "pdf": "boarding_pdf"},
        [("actor", "cv", "1: enter PNR, Check in"),
         ("cv", "cs", "2: check_in(user, pnr, now)"),
         ("cs", "db", "2.1: SELECT booking + payment"),
         ("cs", "db", "2.2: UPDATE booking CHECKED_IN"),
         ("cs", "bp", "2.3: create BoardingPass(...)"),
         ("cs", "cv", "2.4: boarding pass"),
         ("cv", "actor", "3: show pass"),
         ("actor", "cv", "4: Download boarding pass (PDF)"),
         ("cv", "pdf", "5: render_boarding_pass(pass)"),
         ("pdf", "cv", "6: PDF bytes")],
        "Collaboration Diagram - Check In Passenger")


# ------------------------------------------------------------------ CFGs
def cfg(name, nodes, edges, title):
    """nodes: list of ids ('R..' are raised exceptions); decisions are nodes with more than one exit."""
    out_deg = {n: sum(1 for a, _b, _l in edges if a == n) for n in nodes}
    L = B.graph_header(name, "TB", "nodesep=0.35 ranksep=0.35")
    L.append(f'  labelloc=t label="{title}" fontsize=13;')
    L.append('  node [shape=circle width=0.45 fixedsize=true fontsize=11];')
    for n in nodes:
        if n.startswith("R"):
            L.append(f'  "{n}" [shape=box fixedsize=false width=0.3 fillcolor="{B.RED}"];')
        elif out_deg[n] > 1:
            L.append(f'  "{n}" [fillcolor="{B.YELLOW}"];')
        else:
            L.append(f'  "{n}";')
    for a, b, lbl in edges:
        L.append(f'  "{a}" -> "{b}" [label="{lbl}"];' if lbl else f'  "{a}" -> "{b}";')
    n, e = len(nodes), len(edges)
    decisions = sum(1 for v in out_deg.values() if v > 1)
    L.append(f'  info [shape=note fixedsize=false fillcolor="{B.GREY}" fontsize=10 label="N = {n}, E = {e}\\n'
             f'V(G) = E - N + 2 = {e - n + 2}\\nV(G) = P + 1 = {decisions + 1}"];')
    B.run_dot(name, "\n".join(L) + "\n}")
    assert e - n + 2 == decisions + 1, f"{name}: V(G) mismatch"
    return n, e, e - n + 2


def cfgs():
    results = {}
    nodes = [str(i) for i in range(1, 11)] + ["E"] + [f"R{i}" for i in range(1, 9)]
    edges = [(str(i), str(i + 1), "F") for i in range(1, 9)] + [("9", "10", ""), ("10", "E", "")]
    for i in range(1, 9):
        edges += [(str(i), f"R{i}", "T"), (f"R{i}", "E", "")]
    results["check_in"] = cfg("cfg_check_in", nodes, edges, "CFG - CheckInService.check_in()")

    nodes = ["1", "2", "3", "4", "5", "6", "7", "E"]
    edges = [("1", "E", "T: return True"), ("1", "2", "F"), ("2", "3", ""), ("3", "4", "next row"),
             ("3", "7", "rows done"), ("4", "3", "T: continue"), ("4", "5", "F"), ("5", "6", "T"), ("5", "3", "F"),
             ("6", "E", "return False"), ("7", "E", "return True")]
    results["is_gate_available"] = cfg("cfg_gate", nodes, edges, "CFG - FlightService.is_gate_available()")

    nodes = ["1", "2", "3", "4", "5", "R", "E"]
    edges = [("1", "R", "T"), ("1", "2", "F"), ("2", "3", ""), ("3", "4", "T"), ("3", "5", "F"),
             ("4", "E", "return 0"), ("5", "E", "return fee"), ("R", "E", "")]
    results["compute_excess_fee"] = cfg("cfg_excess_fee", nodes, edges, "CFG - compute_excess_fee()")

    nodes = [str(i) for i in range(1, 13)] + ["E"]
    edges = [("1", "3", "T"), ("1", "2", "F"), ("2", "3", "T"), ("2", "4", "F"), ("3", "E", ""),
             ("4", "5", "T"), ("4", "10", "F"), ("5", "6", "T"), ("5", "9", "F"), ("6", "7", "T"), ("6", "8", "F"),
             ("7", "9", ""), ("8", "9", ""), ("9", "4", ""), ("10", "11", "T"), ("10", "12", "F"),
             ("11", "E", ""), ("12", "E", "")]
    results["validate_card_number"] = cfg("cfg_card_number", nodes, edges, "CFG - validate_card_number()")

    nodes = ["1", "2", "3", "4", "E"]
    edges = [("1", "2", "T"), ("1", "4", "F"), ("2", "3", "T"), ("2", "1", "F"), ("3", "E", ""), ("4", "E", "")]
    results["cancellation_percent"] = cfg("cfg_refund_tier", nodes, edges, "CFG - cancellation_percent()")
    for k, (n, e, v) in results.items():
        print(f"  {k}: N={n} E={e} V(G)={v}")


def main():
    os.makedirs(OUT, exist_ok=True)
    lifecycle()
    decomposition()
    coupling()
    structure_charts()
    collaborations()
    cfgs()


if __name__ == "__main__":
    main()
