"""Use-case diagrams: stick-figure actors outside the system boundary, use cases as ellipses grouped by
module, a solid line for association, a hollow-headed arrow for generalisation and dashed
<<include>> / <<extend>> arrows. One overview diagram (packages) and one diagram per group of modules.
Use-case names match the use-case descriptions UC-01.. in the report.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookdraw as D  # noqa: E402
import bookstyle as B  # noqa: E402

# id: (label, module)
USE_CASES = {
    "UC01": ("Login", "Accounts"), "UC02": ("Logout", "Accounts"),
    "UC03": ("Register Account", "Accounts"), "UC04": ("Create Staff Account", "Accounts"),
    "UC05": ("View Users", "Accounts"),
    "UC06": ("Search Flights", "Booking"), "UC07": ("Book Ticket", "Booking"),
    "UC08": ("Select Seat", "Booking"), "UC09": ("Cancel Booking", "Booking"),
    "UC10": ("View All Bookings", "Booking"),
    "UC11": ("Check In Passenger", "Check-in & Baggage"), "UC12": ("Generate Boarding Pass", "Check-in & Baggage"),
    "UC13": ("View Boarding Pass", "Check-in & Baggage"), "UC14": ("Add Bag", "Check-in & Baggage"),
    "UC15": ("Generate Bag Tag", "Check-in & Baggage"), "UC16": ("Update Bag Status", "Check-in & Baggage"),
    "UC17": ("View Flight Schedule", "Flight Scheduling"), "UC18": ("Add / Update Flight", "Flight Scheduling"),
    "UC19": ("Assign Gate", "Flight Scheduling"), "UC20": ("Change Flight Status", "Flight Scheduling"),
    "UC21": ("Cancel Flight", "Flight Scheduling"), "UC22": ("Check Gate Availability", "Flight Scheduling"),
    "UC23": ("Add Recurring Service", "Recurring Schedule"), "UC24": ("Switch Service On / Off", "Recurring Schedule"),
    "UC25": ("Generate Flights", "Recurring Schedule"),
    "UC26": ("Pay for Booking", "Payments"), "UC27": ("Authorize Payment", "Payments"),
    "UC28": ("Download Receipt", "Payments"), "UC29": ("Refund Payment", "Payments"),
    "UC30": ("View Revenue", "Payments"),
    "UC31": ("Download Boarding Pass", "Check-in & Baggage"),
}
ASSOC = {
    "PAX": ["UC03", "UC06", "UC07", "UC09", "UC13", "UC26", "UC28", "UC31"],
    "STF": ["UC10", "UC11", "UC14", "UC16", "UC28", "UC31"],
    "USR": ["UC01", "UC02", "UC17"],
    "ADM": ["UC04", "UC05", "UC09", "UC10", "UC11", "UC18", "UC19", "UC20", "UC21", "UC23", "UC24", "UC25",
            "UC28", "UC30"],
    "GW": ["UC27"],
}
INCLUDE = [("UC07", "UC08"), ("UC07", "UC26"), ("UC26", "UC27"), ("UC11", "UC12"), ("UC14", "UC15"),
           ("UC18", "UC22"), ("UC19", "UC22"), ("UC25", "UC22"), ("UC21", "UC09"), ("UC09", "UC29")]
PACKAGES = ["Accounts", "Flight Scheduling", "Recurring Schedule", "Booking", "Payments", "Check-in & Baggage"]
EXTEND = [("UC31", "UC13")]            # downloading is an optional extension of viewing the boarding pass


ACTOR_LABEL = {"USR": "User", "PAX": "Passenger", "STF": "Check-in Staff", "ADM": "Administrator",
               "GW": "Payment Gateway\\n(external system)"}
RIGHT = ("ADM", "GW")            # actors drawn on the right-hand side


def build(name, modules, extras=()):
    """One use-case diagram for the given packages. `extras` are use cases that belong to another diagram
    but are included from here; they are drawn dashed."""
    fig = os.path.join(B.DIAGRAMS, "_actor.png")
    actor = f'shape=none style="" image="{fig}" imagepos=tc labelloc=b height=1.9 width=1.0 fontsize=13'
    uc = f'shape=ellipse style=filled fillcolor="{B.BLUE}" color="#333333" penwidth=1.0 margin="0.14,0.06" fontsize=12'
    ucs = [u for u, (_l, m) in USE_CASES.items() if m in modules] + list(extras)
    assoc = {a: [u for u in us if u in ucs] for a, us in ASSOC.items()}
    shown = [a for a in ("USR", "PAX", "STF", "ADM", "GW") if assoc[a]]
    L = B.graph_header(name, "LR", "nodesep=0.22 ranksep=1.3")
    L.append("  edge [dir=none arrowsize=0.8];")
    for a in shown:
        L.append(f'  {a} [{actor} label="{ACTOR_LABEL[a]}"];')
    L.append(f'  subgraph cluster_sys {{ label="Airport Management System" fontname="{B.FONT}" fontsize=15 '
             f'style=rounded color="#333333" penwidth=1.5 bgcolor="#FFFFFF";')
    for i, mod in enumerate(m for m in PACKAGES if m in modules):
        L.append(f'    subgraph cluster_m{i} {{ label="{B.hy(mod)}" fontname="{B.FONT}" fontsize=12 '
                 f'style=dashed color="#888888";')
        for uid, (label, m) in USE_CASES.items():
            if m == mod:
                L.append(f'      {uid} [{uc} label="{label}"];')
        L.append("    }")
    for uid in extras:
        L.append(f'    {uid} [{uc.replace("style=filled", "style=\"filled,dashed\"")} label="{USE_CASES[uid][0]}"];')
    L.append("  }")
    for a in shown:
        for u in assoc[a]:
            L.append(f"  {u} -> {a};" if a in RIGHT else f"  {a} -> {u};")
    for x, y in INCLUDE:
        if x in ucs and y in ucs:
            L.append(f'  {x} -> {y} [dir=forward style=dashed xlabel="«include»" fontsize=10 constraint=false];')
    for x, y in EXTEND:
        if x in ucs and y in ucs:
            L.append(f'  {x} -> {y} [dir=forward style=dashed xlabel="«extend»" fontsize=10 constraint=false];')
    if "USR" in shown:                                   # generalisation: Passenger, Staff, Administrator are Users
        for a in ("PAX", "STF"):
            if a in shown:
                L.append(f'  USR -> {a} [dir=back arrowtail=onormal arrowsize=1.2 constraint=false];')
        if "ADM" in shown:
            L.append('  ADM -> USR [dir=forward arrowhead=onormal arrowsize=1.2 constraint=false];')
    L.append("}")
    B.run_dot(name, "\n".join(L))


def overview():
    """Use case packaging (Figure 7.22): actors and the packages they use."""
    fig = os.path.join(B.DIAGRAMS, "_actor.png")
    actor = f'shape=none style="" image="{fig}" imagepos=tc labelloc=b height=1.9 width=1.0 fontsize=13'
    L = B.graph_header("use_case", "LR", "nodesep=0.5 ranksep=2.4")
    L.append("  edge [dir=none];")
    for a in ("USR", "PAX", "STF", "ADM", "GW"):
        L.append(f'  {a} [{actor} label="{ACTOR_LABEL[a]}"];')
    L.append(f'  subgraph cluster_sys {{ label="Airport Management System" fontname="{B.FONT}" fontsize=15 '
             f'style=rounded color="#333333" penwidth=1.5 bgcolor="#FFFFFF";')
    for i, mod in enumerate(PACKAGES):
        count = sum(1 for _l, m in USE_CASES.values() if m == mod)
        L.append(f'    P{i} [shape=folder style=filled fillcolor="{B.BLUE}" fontsize=13 margin="0.25,0.18" '
                 f'label="{B.hy(mod)}\\n({count} use cases)"];')
    L.append("  }")
    links = {"USR": [0, 1], "PAX": [3, 4, 5], "STF": [3, 4, 5], "ADM": [0, 1, 2, 3, 4, 5], "GW": [4]}
    for a, idx in links.items():
        for i in idx:
            L.append(f"  P{i} -> {a};" if a in RIGHT else f"  {a} -> P{i};")
    for src, dst in ((3, 4), (4, 5)):                     # packages that depend on each other
        L.append(f'  P{src} -> P{dst} [dir=forward style=dashed constraint=false];')
    for a in ("PAX", "STF"):
        L.append(f'  USR -> {a} [dir=back arrowtail=onormal arrowsize=1.2 constraint=false];')
    L.append('  ADM -> USR [dir=forward arrowhead=onormal arrowsize=1.2 constraint=false];')
    L.append("}")
    B.run_dot("use_case", "\n".join(L))


def main():
    os.makedirs(B.DIAGRAMS, exist_ok=True)
    D.stick_figure(os.path.join(B.DIAGRAMS, "_actor.png"))
    overview()
    build("use_case_accounts_flights", ["Accounts", "Flight Scheduling", "Recurring Schedule"], extras=["UC09", "UC29"])
    build("use_case_booking_payments", ["Booking", "Payments"])
    build("use_case_checkin", ["Check-in & Baggage"])


if __name__ == "__main__":
    main()
