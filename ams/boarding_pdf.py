"""Boarding-pass PDF, written with the standard library only (no PDF package needed).

`render_boarding_pass(bp)` returns the bytes of a one-page, ticket-shaped PDF: route, passenger, flight, date,
gate, seat, boarding time, a perforated stub and a scannable Code 128 barcode. The file uses only PDF's
built-in Helvetica fonts, so it opens in any viewer.
"""
import math
from datetime import datetime
from typing import List, Optional, Tuple

from .models import BoardingPass
from .network import AIRPORTS

# ----------------------------------------------------------------------------- Code 128 (subset B)
# Bar/space widths for symbol values 0..105 (alternating bar, space, ... ; each symbol is 11 modules wide).
# Cross-checked symbol by symbol against the python-barcode library; the stop symbol (106) is _STOP.
_PATTERNS = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 "
    "113222 123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
    "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 "
    "113123 113321 133121 313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
    "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 "
    "142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 "
    "212141 214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 "
    "211214 211232").split()
_STOP = "2331112"
START_B, STOP = 104, 106


def code128_symbols(text: str) -> List[int]:
    """Symbol values for `text` (ASCII 32..126): start B, characters, checksum, stop."""
    values = []
    for ch in text:
        if not 32 <= ord(ch) <= 126:
            raise ValueError(f"Code 128-B cannot encode {ch!r}")
        values.append(ord(ch) - 32)
    checksum = (START_B + sum(i * v for i, v in enumerate(values, start=1))) % 103
    return [START_B] + values + [checksum, STOP]


def code128_widths(text: str) -> List[int]:
    """Alternating bar/space widths in modules, beginning with a bar."""
    out: List[int] = []
    for value in code128_symbols(text):
        pattern = _STOP if value == STOP else _PATTERNS[value]
        out.extend(int(c) for c in pattern)
    return out


# ----------------------------------------------------------------------------- Helvetica metrics (1000 units/em)
_W_REG = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556,
          556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278,
          500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469,
          556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500,
          278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_W_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556,
           556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278,
           556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584,
           556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556,
           333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]


def text_width(text: str, size: float, bold: bool = False) -> float:
    table = _W_BOLD if bold else _W_REG
    return sum(table[ord(c) - 32] if 32 <= ord(c) <= 126 else 556 for c in text) * size / 1000.0


# ----------------------------------------------------------------------------- tiny PDF canvas
def _rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return " ".join(f"{int(h[i:i + 2], 16) / 255:.3f}" for i in (0, 2, 4))


class _Canvas:
    def __init__(self, width: float, height: float):
        self.width, self.height = width, height
        self.ops: List[str] = []

    def rect(self, x, y, w, h, fill: Optional[str] = None, stroke: Optional[str] = None, lw: float = 1):
        self.ops.append("q")
        if fill:
            self.ops.append(f"{_rgb(fill)} rg")
        if stroke:
            self.ops.append(f"{_rgb(stroke)} RG {lw} w")
        paint = "B" if fill and stroke else "f" if fill else "S"
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {paint}")
        self.ops.append("Q")

    def circle(self, cx, cy, r, fill: str):
        k = 0.5523 * r
        pts = [(cx + r, cy), (cx + r, cy + k, cx + k, cy + r, cx, cy + r), (cx - k, cy + r, cx - r, cy + k, cx - r, cy),
               (cx - r, cy - k, cx - k, cy - r, cx, cy - r), (cx + k, cy - r, cx + r, cy - k, cx + r, cy)]
        ops = [f"{pts[0][0]:.2f} {pts[0][1]:.2f} m"]
        ops += [" ".join(f"{v:.2f}" for v in seg) + " c" for seg in pts[1:]]
        self.ops.append(f"q {_rgb(fill)} rg " + " ".join(ops) + " f Q")

    def polygon(self, points: List[Tuple[float, float]], fill: str):
        path = f"{points[0][0]:.2f} {points[0][1]:.2f} m " + " ".join(f"{x:.2f} {y:.2f} l" for x, y in points[1:])
        self.ops.append(f"q {_rgb(fill)} rg {path} f Q")

    def line(self, x1, y1, x2, y2, color: str, lw: float = 1, dash: Optional[Tuple[int, int]] = None):
        d = f"[{dash[0]} {dash[1]}] 0 d" if dash else "[] 0 d"
        self.ops.append(f"q {_rgb(color)} RG {lw} w {d} {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q")

    def text(self, x, y, s: str, size: float, color: str = "#0F172A", bold: bool = False, align: str = "l"):
        width = text_width(s, size, bold)
        if align == "r":
            x -= width
        elif align == "c":
            x -= width / 2
        safe = s.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        self.ops.append(f"q {_rgb(color)} rg BT /{'F2' if bold else 'F1'} {size} Tf {x:.2f} {y:.2f} Td ({safe}) Tj ET Q")

    def to_pdf(self, title: str) -> bytes:
        stream = "\n".join(self.ops).encode("latin-1")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:g} {self.height:g}] "
             "/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>").encode(),
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
            b"<< /Title (" + title.encode("latin-1", "replace") + b") /Producer (Airport Management System) >>",
        ]
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for n, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        for off in offsets:
            out += f"{off:010d} 00000 n \n".encode()
        out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info 7 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode()
        return bytes(out)


# ----------------------------------------------------------------------------- the boarding pass
NAVY, ACCENT, MUTED, INK, PAPER, PAGE_BG = "#0B1F3A", "#2563EB", "#64748B", "#0F172A", "#FFFFFF", "#E5EAF2"
_PLANE = [(30, 0), (12, -4), (-2, -20), (-8, -20), (0, -4), (-14, -3), (-20, -9), (-24, -9), (-20, 0),
          (-24, 9), (-20, 9), (-14, 3), (0, 4), (-8, 20), (-2, 20), (12, 4)]


def barcode_text(bp: BoardingPass) -> str:
    """The barcode carries just the PNR - exactly what the counter's 'Find booking' box takes - which keeps
    the bars wide enough to scan reliably even at 150 dpi."""
    return bp.pnr


def suggested_filename(bp: BoardingPass) -> str:
    return f"BoardingPass_{bp.pnr}_{bp.flight_no}.pdf"


def render_boarding_pass(bp: BoardingPass) -> bytes:
    W, H = 612, 270
    c = _Canvas(W, H)
    c.rect(0, 0, W, H, fill=PAGE_BG)
    c.rect(14, 14, 584, 242, fill=PAPER, stroke="#C3CEDC", lw=0.8)
    main_right, stub_left = 440, 440

    # header bands
    c.rect(14, 214, 584, 42, fill=NAVY)
    c.text(30, 229, "BOARDING PASS", 16, "#FFFFFF", bold=True)
    c.text(main_right - 14, 231, "Airport Management System", 9, "#9DB7DC", align="r")
    c.text(main_right - 14, 220, "Economy", 8, "#9DB7DC", align="r")
    c.text(stub_left + 18, 229, "BOARDING PASS", 11, "#FFFFFF", bold=True)

    # route
    origin_city, dest_city = AIRPORTS.get(bp.origin, ""), AIRPORTS.get(bp.destination, "")
    c.text(30, 168, bp.origin, 42, INK, bold=True)
    c.text(main_right - 18, 168, bp.destination, 42, INK, bold=True, align="r")
    c.text(30, 150, origin_city.upper(), 9, MUTED)
    c.text(main_right - 18, 150, dest_city.upper(), 9, MUTED, align="r")
    cx, cy = (30 + text_width(bp.origin, 42, True) + main_right - 18 - text_width(bp.destination, 42, True)) / 2, 183
    c.line(cx - 62, cy, cx - 22, cy, "#C3CEDC", 1.2, dash=(3, 3))
    c.line(cx + 22, cy, cx + 62, cy, "#C3CEDC", 1.2, dash=(3, 3))
    c.polygon([(cx + px * 0.5, cy + py * 0.5) for px, py in _PLANE], ACCENT)

    # details grid
    def field(x, y, label, value, size=13, bold=True):
        c.text(x, y + 15, label, 7.5, MUTED)
        c.text(x, y, value, size, INK, bold=bold)

    field(30, 108, "PASSENGER", bp.passenger_name.upper(), 14)
    field(250, 108, "FLIGHT", bp.flight_no)
    field(335, 108, "DATE", bp.departure.strftime("%d %b %Y").upper())
    field(30, 62, "DEPARTS", bp.departure.strftime("%H:%M"), 16)
    field(120, 62, "BOARDING", bp.boarding_time.strftime("%H:%M"), 16)
    field(215, 62, "GATE", bp.gate or "TBA", 16)
    field(290, 62, "SEAT", bp.seat, 16)
    field(355, 62, "SEQ", f"{bp.boarding_seq:03d}", 16)
    c.line(30, 48, main_right - 18, 48, "#E2E8F0", 0.8)
    c.text(30, 32, "Be at the gate by the boarding time shown and carry a valid photo ID.", 8, MUTED)

    # perforation with notches
    c.line(stub_left, 14, stub_left, 256, "#9DB7DC", 1, dash=(4, 4))
    c.circle(stub_left, 256, 9, PAGE_BG)
    c.circle(stub_left, 14, 9, PAGE_BG)

    # stub
    sx = stub_left + 18
    c.text(sx, 190, bp.origin + "  >  " + bp.destination, 14, INK, bold=True)
    c.text(sx, 174, f"{bp.flight_no}   {bp.departure.strftime('%d %b %Y').upper()}", 9, MUTED)
    c.text(sx, 146, "SEAT", 7.5, MUTED)
    c.text(sx, 120, bp.seat, 28, ACCENT, bold=True)
    c.text(sx + 70, 146, "GATE", 7.5, MUTED)
    c.text(sx + 70, 120, bp.gate or "TBA", 28, INK, bold=True)
    c.text(sx, 100, "PNR", 7.5, MUTED)
    c.text(sx + 22, 100, bp.pnr, 10, INK, bold=True)
    c.text(sx + 68, 100, "BOARDS", 7.5, MUTED)
    c.text(sx + 102, 100, bp.boarding_time.strftime("%H:%M"), 10, INK, bold=True)

    # Code 128 barcode (quiet zone of 10 modules each side)
    widths = code128_widths(barcode_text(bp))
    total = sum(widths) + 20
    module = (W - 14 - 14 - sx) / total
    x = sx + 10 * module
    for i, w in enumerate(widths):
        if i % 2 == 0:
            c.rect(x, 40, w * module, 42, fill="#000000")
        x += w * module
    c.text(sx + (W - 14 - 14 - sx) / 2, 29, barcode_text(bp), 7, MUTED, align="c")

    return c.to_pdf(f"Boarding pass {bp.pnr}")
