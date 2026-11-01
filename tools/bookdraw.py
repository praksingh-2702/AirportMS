"""Small Pillow drawing helpers for the diagrams: the stick-figure actor used by the use case and
collaboration diagrams. Everything else is drawn with Graphviz (see make_design_diagrams.py)."""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookstyle as B  # noqa: E402


def stick_figure(path, height=150):
    """Actor figure with a pale-yellow head, transparent background."""
    s = 2
    img = Image.new("RGBA", (90 * s, height * s), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    w = 3 * s
    d.ellipse((30 * s, 6 * s, 60 * s, 36 * s), outline="black", fill=B.YELLOW, width=w)
    d.line((45 * s, 36 * s, 45 * s, 92 * s), fill="black", width=w)
    d.line((14 * s, 56 * s, 76 * s, 56 * s), fill="black", width=w)
    d.line((45 * s, 92 * s, 18 * s, 140 * s), fill="black", width=w)
    d.line((45 * s, 92 * s, 72 * s, 140 * s), fill="black", width=w)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.resize((90, height), Image.LANCZOS).save(path)
