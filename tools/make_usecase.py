"""Use-case diagram drawn with Graphviz (cleaner layout than PlantUML for many actors).
Use-case names match the use-case descriptions UC-01..UC-20 in the report."""
import os
import subprocess

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "diagrams")
FONT = "DejaVu Sans"


def stick_figure(path):
    img = Image.new("RGBA", (90, 150), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((30, 6, 60, 36), outline="black", fill="#FFF4C2", width=3)
    d.line((45, 36, 45, 92), fill="black", width=3)
    d.line((14, 56, 76, 56), fill="black", width=3)
    d.line((45, 92, 18, 140), fill="black", width=3)
    d.line((45, 92, 72, 140), fill="black", width=3)
    img.save(path)


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
}
ASSOC = {
    "PAX": ["UC03", "UC06", "UC07", "UC09", "UC13"],
    "STF": ["UC10", "UC11", "UC14", "UC16"],
    "USR": ["UC01", "UC02", "UC17"],
    "ADM": ["UC04", "UC05", "UC09", "UC10", "UC11", "UC18", "UC19", "UC20", "UC21"],
}
INCLUDE = [("UC07", "UC08"), ("UC11", "UC12"), ("UC14", "UC15"), ("UC18", "UC22"),
           ("UC19", "UC22"), ("UC21", "UC09")]
EXTEND = []   # no optional behaviour modelled


def main():
    os.makedirs(OUT, exist_ok=True)
    fig = os.path.join(OUT, "_actor.png")
    stick_figure(fig)
    actor = (f'shape=none image="{fig}" imagepos=tc labelloc=b height=1.9 width=1.0 '
             f'fontname="{FONT}" fontsize=13')
    uc = f'shape=ellipse style=filled fillcolor="#D9E8FB" color="#333333" fontname="{FONT}" fontsize=12 margin="0.12,0.05"'
    L = ["digraph usecase {", f'  graph [rankdir=LR nodesep=0.22 ranksep=1.2 fontname="{FONT}" pad=0.3];',
         '  edge [dir=none color="#333333" arrowsize=0.8];']
    L += [f'  USR [{actor} label="User"];', f'  PAX [{actor} label="Passenger"];',
          f'  STF [{actor} label="Check-in Staff"];', f'  ADM [{actor} label="Administrator"];']
    L.append(f'  subgraph cluster_sys {{ label="Airport Management System" fontname="{FONT}" fontsize=15 '
             f'style=rounded color="#333333" penwidth=1.5;')
    modules = ["Accounts", "Flight Scheduling", "Booking", "Check-in & Baggage"]
    for i, mod in enumerate(modules):
        L.append(f'    subgraph cluster_m{i} {{ label="{mod}" fontname="{FONT}" fontsize=12 style="dashed,rounded" color="#888888";')
        for uid, (label, m) in USE_CASES.items():
            if m == mod:
                L.append(f'      {uid} [{uc} label="{label}"];')
        L.append("    }")
    L.append("  }")
    for act in ("PAX", "STF", "USR"):
        for u in ASSOC[act]:
            L.append(f"  {act} -> {u};")
    for u in ASSOC["ADM"]:
        L.append(f"  {u} -> ADM;")
    for a, b in INCLUDE:
        L.append(f'  {a} -> {b} [dir=forward style=dashed label="«include»" fontname="{FONT}" fontsize=10 constraint=false];')
    # generalisation: Passenger, Staff, Administrator are Users
    for act in ("PAX", "STF"):
        L.append(f'  USR -> {act} [dir=back arrowtail=onormal arrowsize=1.2 constraint=false];')
    L.append('  ADM -> USR [dir=forward arrowhead=onormal arrowsize=1.2 constraint=false];')
    L.append("}")
    dot = os.path.join(OUT, "use_case.dot")
    with open(dot, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    subprocess.run(["dot", "-Tpng", "-Gdpi=160", dot, "-o", os.path.join(OUT, "use_case.png")], check=True)
    print("rendered use_case")


if __name__ == "__main__":
    main()
