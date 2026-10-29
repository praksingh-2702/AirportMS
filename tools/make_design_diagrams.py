"""Render the remaining design diagrams with Graphviz:
life-cycle model, decomposition tree, module coupling, structure charts (transaction +
transform analysis), collaboration diagrams and white-box control-flow graphs (CFGs).
Usage: python tools/make_design_diagrams.py
"""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "diagrams")
FONT = "DejaVu Sans"
BLUE, YELLOW, GREY = "#D9E8FB", "#FFF4C2", "#EEEEEE"


def render(name, body, graph_attrs=""):
    src = (f'digraph "{name}" {{\n  graph [fontname="{FONT}" pad=0.3 {graph_attrs}];\n'
           f'  node [fontname="{FONT}" fontsize=12];\n  edge [fontname="{FONT}" fontsize=10 color="#333333"];\n'
           f'{body}\n}}\n')
    path = os.path.join(OUT, f"{name}.dot")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    subprocess.run(["dot", "-Tpng", "-Gdpi=160", path, "-o", os.path.join(OUT, f"{name}.png")], check=True)
    print("rendered", name)


# ------------------------------------------------------------------ life cycle
def lifecycle():
    phases = ["Feasibility Study", "Requirements Analysis\n& Specification (SRS)", "Design\n(SA/SD + OOD)",
              "Coding &\nUnit Testing", "Integration &\nSystem Testing", "Maintenance"]
    body = [f'  node [shape=box style="rounded,filled" fillcolor="{BLUE}" width=2.3 height=0.8];']
    for i, p in enumerate(phases):
        body.append(f'  p{i} [label="{p}"];')
    for i in range(len(phases) - 1):
        body.append(f'  p{i} -> p{i+1} [weight=10];')
        body.append(f'  p{i+1} -> p{i} [style=dashed color="#C62828" constraint=false label="feedback" fontcolor="#C62828"];')
    render("lifecycle_iterative_waterfall", "\n".join(body), "rankdir=TB nodesep=0.4 ranksep=0.35")
    # simple sketch: spiral/prototype not drawn - compared in a table in the report


# ------------------------------------------------------------------ decomposition
def decomposition():
    tree = {
        "Airport Management System": ["Login & Accounts", "Flight Scheduling", "Passenger Booking", "Check-in & Baggage"],
        "Login & Accounts": ["Verify credentials", "Register passenger", "Create staff account", "List users"],
        "Flight Scheduling": ["Add / update flight", "Check gate availability", "Assign gate", "Change status", "Cancel flight"],
        "Passenger Booking": ["Search flights", "Show seat map", "Book ticket", "Cancel booking", "List bookings"],
        "Check-in & Baggage": ["Find booking by PNR", "Check in", "Boarding pass", "Add bag + tag", "Excess fee", "Bag status"],
    }
    body = ['  node [shape=box style="filled" fillcolor="white"];']
    ids = {}

    def nid(name):
        return ids.setdefault(name, f"n{len(ids)}")
    for parent, children in tree.items():
        color = BLUE if parent == "Airport Management System" else YELLOW
        body.append(f'  {nid(parent)} [label="{parent}" fillcolor="{color}" penwidth=1.5];')
        for c in children:
            if c not in tree:
                body.append(f'  {nid(c)} [label="{c}" fontsize=11];')
            body.append(f"  {nid(parent)} -> {nid(c)} [arrowhead=none];")
    render("decomposition", "\n".join(body), "rankdir=LR nodesep=0.12 ranksep=0.9 splines=line")


# ------------------------------------------------------------------ coupling / layers
def coupling():
    body = [f'  node [shape=box style="filled" fillcolor="{BLUE}"];']
    body.append(f'  subgraph cluster_gui {{ label="Presentation layer (ams.gui)" style=dashed; '
                f'app [label="AirportApp / AppContext"]; lv [label="LoginView"]; fv [label="FlightView"]; '
                f'bv [label="BookingView"]; cv [label="CheckInView"]; uv [label="UsersView"]; }}')
    body.append(f'  subgraph cluster_svc {{ label="Service layer (ams.services)" style=dashed; '
                f'as [label="AuthService"]; fs [label="FlightService"]; bs [label="BookingService"]; cs [label="CheckInService"]; }}')
    body.append(f'  subgraph cluster_util {{ label="Utility / data layer" style=dashed; node [fillcolor="{YELLOW}"]; '
                f'val [label="validators"]; acc [label="access"]; sec [label="security"]; mod [label="models"]; '
                f'cfg [label="config"]; err [label="errors"]; }}')
    body.append(f'  db [shape=cylinder fillcolor="{GREY}" label="SQLite\\nairport.db"];')
    for a, b in [("app", "lv"), ("app", "fv"), ("app", "bv"), ("app", "cv"), ("app", "uv"),
                 ("lv", "as"), ("uv", "as"), ("fv", "fs"), ("bv", "bs"), ("bv", "fs"), ("cv", "cs"), ("cv", "bs")]:
        body.append(f"  {a} -> {b};")
    for s in ("as", "fs", "bs", "cs"):
        for u in ("val", "acc", "mod"):
            body.append(f"  {s} -> {u} [color=\"#777777\"];")
        body.append(f"  {s} -> db [color=\"#1E3A5F\" penwidth=1.3];")
    body.append("  as -> sec [color=\"#777777\"]; cs -> bs [style=dashed label=\"DETAILS_SQL\"];")
    body.append("  val -> cfg; val -> err; acc -> err;")
    render("module_coupling", "\n".join(body), "rankdir=TB nodesep=0.3 ranksep=0.7 compound=true")


# ------------------------------------------------------------------ structure charts
DATA = "○"     # data couple
FLAG = "●"     # control flag


def chart(name, nodes, edges, transaction=None, title=""):
    """nodes: id -> label; edges: (parent, child, down_couples, up_couples)."""
    body = [f'  node [shape=box style="filled" fillcolor="white" penwidth=1.3 width=1.6];',
            f'  labelloc=t label="{title}" fontsize=14;']
    for nid_, label in nodes.items():
        fill = BLUE if nid_ == "root" else ("#E8F5E9" if transaction and nid_ == transaction else "white")
        body.append(f'  {nid_} [label="{label}" fillcolor="{fill}"];')
    if transaction:
        body.append(f'  {transaction}_sel [shape=diamond label="" width=0.35 height=0.35 style=filled fillcolor="{YELLOW}"];')
        body.append(f'  {transaction} -> {transaction}_sel [arrowhead=none];')
    for parent, child, down, up in edges:
        src = f"{parent}_sel" if transaction and parent == transaction else parent
        parts = [f"{c} ↓" for c in down] + [f"{c} ↑" for c in up]
        label = "\\n".join(parts)
        body.append(f'  {src} -> {child} [label="{label}" arrowsize=0.7];')
    body.append(f'  legend [shape=note fillcolor="{GREY}" fontsize=10 label="{DATA} data couple   {FLAG} control flag\\n'
                f'↓ passed to called module   ↑ returned to caller"];')
    render(name, "\n".join(body), "rankdir=TB nodesep=0.35 ranksep=0.9")


def structure_charts():
    # --- Transaction analysis: the dashboard dispatches one of several transaction types
    nodes = {
        "root": "AirportApp\\n(main)", "login": "Get Login\\nLoginView.login()",
        "disp": "Dispatch Transaction\\nshow_dashboard(user)",
        "t1": "Flight Scheduling\\nFlightView", "t2": "Passenger Booking\\nBookingView",
        "t3": "Check-in & Baggage\\nCheckInView", "t4": "User Management\\nUsersView",
        "t5": "Boarding Pass\\nBoardingPassView",
        "f1": "FlightService\\nadd/update/cancel", "b1": "BookingService\\nsearch/book/cancel",
        "c1": "CheckInService\\ncheck_in/add_bag", "u1": "AuthService\\ncreate_staff_account",
        "a1": "AuthService\\nlogin()",
    }
    edges = [
        ("root", "login", [], [f"{DATA} user"]),
        ("login", "a1", [f"{DATA} username, password"], [f"{DATA} user", f"{FLAG} auth_ok"]),
        ("root", "disp", [f"{DATA} user", f"{FLAG} role"], []),
        ("disp", "t1", [f"{DATA} ctx"], []), ("disp", "t2", [f"{DATA} ctx"], []),
        ("disp", "t3", [f"{DATA} ctx"], []), ("disp", "t4", [f"{DATA} ctx"], []),
        ("disp", "t5", [f"{DATA} ctx"], []),
        ("t1", "f1", [f"{DATA} flight fields"], [f"{DATA} flight"]),
        ("t2", "b1", [f"{DATA} flight_id, seat"], [f"{DATA} booking"]),
        ("t3", "c1", [f"{DATA} pnr, weight"], [f"{DATA} boarding pass, bag"]),
        ("t4", "u1", [f"{DATA} account fields"], [f"{DATA} user"]),
    ]
    chart("structure_chart_transaction", nodes, edges, transaction="disp",
          title="Structure Chart 1 - Transaction Analysis (role-based dashboard)")

    # --- Transform analysis: Check In Passenger (DFD 5.0)
    nodes = {
        "root": "Check In Passenger\\nCheckInService.check_in()",
        "aff": "Get Booking Details\\nfind_booking()", "rd": "Read PNR\\nCheckInView.pnr",
        "vp": "Validate PNR\\nvalidate_pnr()", "fb": "Fetch Booking Row\\nDETAILS_SQL query",
        "ce": "Verify Eligibility\\n(status + 48h/45min window)", "seq": "Assign Boarding Seq\\nMAX(seq)+1, UPDATE",
        "eff": "Produce Boarding Pass\\nget_boarding_pass()", "fmt": "Format Pass\\nBoardingPass.as_text()",
        "show": "Display Pass\\nCheckInView._write()",
    }
    edges = [
        ("root", "aff", [], [f"{DATA} booking_details"]),
        ("aff", "rd", [], [f"{DATA} raw_pnr"]),
        ("aff", "vp", [f"{DATA} raw_pnr"], [f"{DATA} pnr"]),
        ("aff", "fb", [f"{DATA} pnr"], [f"{DATA} booking_details"]),
        ("root", "ce", [f"{DATA} booking_details", f"{DATA} now"], [f"{FLAG} eligible"]),
        ("root", "seq", [f"{DATA} booking_id"], [f"{DATA} boarding_seq"]),
        ("root", "eff", [f"{DATA} pnr"], [f"{DATA} boarding_pass"]),
        ("eff", "fmt", [f"{DATA} boarding_pass"], [f"{DATA} pass_text"]),
        ("eff", "show", [f"{DATA} pass_text"], []),
    ]
    chart("structure_chart_transform_checkin", nodes, edges,
          title="Structure Chart 2 - Transform Analysis of DFD 5.0 (afferent | central transform | efferent)")

    # --- Transform analysis: Book Ticket (DFD 4.0)
    nodes = {
        "root": "Book Ticket\\nBookingService.book_ticket()",
        "aff": "Get Valid Request", "gf": "Get Flight\\nSELECT flights", "ps": "Validate Seat\\nparse_seat()",
        "chk": "Check Seat & Duplicate\\nget_taken_seats()", "pnr": "Generate PNR\\n_unique_pnr()",
        "eff": "Record & Confirm", "ins": "Insert Booking\\nINSERT bookings", "msg": "Show Confirmation\\nBookingView",
    }
    edges = [
        ("root", "aff", [f"{DATA} flight_id, seat"], [f"{DATA} flight, seat"]),
        ("aff", "gf", [f"{DATA} flight_id"], [f"{DATA} flight", f"{FLAG} bookable"]),
        ("aff", "ps", [f"{DATA} seat, rows"], [f"{DATA} seat"]),
        ("root", "chk", [f"{DATA} flight_id, seat, user_id"], [f"{FLAG} seat_free"]),
        ("root", "pnr", [], [f"{DATA} pnr"]),
        ("root", "eff", [f"{DATA} pnr, flight, seat"], [f"{DATA} booking"]),
        ("eff", "ins", [f"{DATA} booking row"], [f"{DATA} booking_id"]),
        ("eff", "msg", [f"{DATA} booking"], []),
    ]
    chart("structure_chart_transform_booking", nodes, edges,
          title="Structure Chart 3 - Transform Analysis of DFD 4.0 (Book Ticket)")


# ------------------------------------------------------------------ collaboration diagrams
def collaboration(name, objects, links, title):
    body = [f'  node [shape=box style=filled fillcolor="{BLUE}" penwidth=1.3 fontsize=13];',
            '  edge [fontsize=12];',
            f'  labelloc=t label="{title}" fontsize=16;']
    for oid, label in objects.items():
        shape = 'shape=none image="' + os.path.join(OUT, "_actor.png") + '" labelloc=b height=1.6 fillcolor=white' if oid == "actor" else ""
        body.append(f'  {oid} [{shape} label=<<U>{label}</U>>];' if oid != "actor" else f'  {oid} [{shape} label="{label}"];')
    newline = "\\n"
    for a, b, msgs in links:
        body.append(f'  {a} -> {b} [dir=none label="{newline.join(msgs)}"];')
    render(name, "\n".join(body), "rankdir=TB nodesep=0.6 ranksep=1.0")


def collaborations():
    collaboration("collaboration_booking", {
        "actor": "Passenger", "bv": ":BookingView", "sm": ":SeatMap", "bs": ":BookingService",
        "ac": "access", "va": "validators", "db": ":SQLite DB"},
        [("actor", "bv", ["1: select flight, Book →", "3: pick(seat), confirm() → (SeatMap)"]),
         ("bv", "sm", ["2: SeatMap(flight, taken) →", "4: on_pick(seat) ←"]),
         ("bv", "bs", ["1.1: get_taken_seats(flight_id) →", "5: book_ticket(user, flight_id, seat) →",
                       "5.7: Booking ←"]),
         ("bs", "ac", ["5.1: require_role(user, PASSENGER) →"]),
         ("bs", "va", ["5.3: parse_seat(seat, rows) →"]),
         ("bs", "db", ["1.2: SELECT taken seats →", "5.2: SELECT flight →", "5.4: SELECT taken seats →",
                       "5.5: SELECT existing PNR →", "5.6: INSERT booking →"])],
        "Collaboration Diagram - Book Ticket")
    collaboration("collaboration_checkin", {
        "actor": "Check-in Staff", "cv": ":CheckInView", "cs": ":CheckInService", "ac": "access",
        "va": "validators", "db": ":SQLite DB", "bp": ":BoardingPass"},
        [("actor", "cv", ["1: enter PNR, Check in →", "3: show boarding pass ←"]),
         ("cv", "cs", ["2: check_in(user, pnr, now) →", "2.8: BoardingPass ←"]),
         ("cs", "ac", ["2.1: require_role(user, STAFF, ADMIN) →"]),
         ("cs", "va", ["2.2: validate_pnr(pnr) →"]),
         ("cs", "db", ["2.3: SELECT booking+flight+user →", "2.4: SELECT MAX(boarding_seq)+1 →",
                       "2.5: UPDATE booking CHECKED_IN →", "2.6: SELECT booking (get_boarding_pass) →"]),
         ("cs", "bp", ["2.7: create BoardingPass(...) →"]),
         ("cv", "bp", ["2.9: as_text() →"])],
        "Collaboration Diagram - Check In Passenger")


# ------------------------------------------------------------------ CFGs
def cfg(name, nodes, edges, title):
    body = [f'  labelloc=t label="{title}" fontsize=13;',
            f'  node [shape=circle style=filled fillcolor="{BLUE}" width=0.45 fixedsize=true fontsize=11];']
    for nid_, (kind, tip) in nodes.items():
        if kind == "raise":
            body.append(f'  "{nid_}" [fillcolor="#F6D5D5" shape=box fixedsize=false width=0.3 label="{nid_}"];')
        elif kind == "decision":
            body.append(f'  "{nid_}" [fillcolor="{YELLOW}"];')
        else:
            body.append(f'  "{nid_}";')
    for a, b, lbl in edges:
        body.append(f'  "{a}" -> "{b}" [label="{lbl}"];')
    n, e = len(nodes), len(edges)
    decisions = sum(1 for k, _ in nodes.values() if k == "decision")
    body.append(f'  info [shape=note fixedsize=false fillcolor="{GREY}" fontsize=10 label="N = {n}, E = {e}\\n'
                f'V(G) = E - N + 2 = {e - n + 2}\\nV(G) = P + 1 = {decisions + 1}"];')
    render(name, "\n".join(body), "rankdir=TB nodesep=0.35 ranksep=0.35")
    assert e - n + 2 == decisions + 1, name
    return n, e, e - n + 2


def cfgs():
    # check_in(): numbered as in the white-box section of the report
    nodes = {"1": ("decision", ""), "2": ("decision", ""), "3": ("decision", ""), "4": ("decision", ""),
             "5": ("decision", ""), "6": ("decision", ""), "7": ("decision", ""), "8": ("stmt", ""),
             "9": ("stmt", ""), "E": ("stmt", "")}
    edges = [("1", "2", "F"), ("2", "3", "F"), ("3", "4", "F"), ("4", "5", "F"), ("5", "6", "F"),
             ("6", "7", "F"), ("7", "8", "F"), ("8", "9", ""), ("9", "E", "")]
    for i in range(1, 8):
        nodes[f"R{i}"] = ("raise", "")
        edges.append((str(i), f"R{i}", "T"))
        edges.append((f"R{i}", "E", ""))
    results = {"check_in": cfg("cfg_check_in", nodes, edges, "CFG - CheckInService.check_in()")}

    nodes = {"1": ("decision", ""), "2": ("stmt", ""), "3": ("decision", ""), "4": ("decision", ""),
             "5": ("decision", ""), "6": ("stmt", ""), "7": ("stmt", ""), "E": ("stmt", "")}
    edges = [("1", "E", "T: return True"), ("1", "2", "F"), ("2", "3", ""), ("3", "4", "next row"),
             ("3", "7", "rows done"), ("4", "3", "T: continue"), ("4", "5", "F"), ("5", "6", "T"),
             ("5", "3", "F"), ("6", "E", "return False"), ("7", "E", "return True")]
    results["is_gate_available"] = cfg("cfg_gate", nodes, edges, "CFG - FlightService.is_gate_available()")

    nodes = {"1": ("decision", ""), "2": ("stmt", ""), "3": ("decision", ""), "4": ("stmt", ""),
             "5": ("stmt", ""), "R": ("raise", ""), "E": ("stmt", "")}
    edges = [("1", "R", "T"), ("1", "2", "F"), ("2", "3", ""), ("3", "4", "T"), ("3", "5", "F"),
             ("4", "E", "return 0"), ("5", "E", "return fee"), ("R", "E", "")]
    results["compute_excess_fee"] = cfg("cfg_excess_fee", nodes, edges, "CFG - compute_excess_fee()")
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
