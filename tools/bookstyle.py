"""Shared look of every generated diagram, so all figures in the report match:

  * white background, sans-serif font;
  * external entities and actors in pale yellow, processes / use cases / UML elements in pale blue;
  * data stores drawn as an open-ended box with a grey D# cell; decisions in yellow, error exits in red;
  * names written in plain words exactly as in the code and the data dictionary ("Booking record").

It also finds the two external programs the diagram scripts need (Graphviz `dot`, PlantUML jar).
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIAGRAMS = os.path.join(ROOT, "docs", "diagrams")
UML = os.path.join(ROOT, "docs", "uml")

FONT = "DejaVu Sans"
PANEL_HEX = "#FFFFFF"            # background of every figure
PANEL = (255, 255, 255)
BLUE = "#D9E8FB"                 # processes, use cases, modules, UML elements
YELLOW = "#FFF4C2"               # external entities, actors, decisions
GREY = "#EEEEEE"                 # store codes, notes
RED = "#F6D5D5"                  # error exits in control-flow graphs
EDGE = "#444444"


# ----------------------------------------------------------------------------- finding the tools
def _candidates(env, names, extra):
    seen = []
    if os.environ.get(env):
        seen.append(os.environ[env])
    for n in names:
        found = shutil.which(n)
        if found:
            seen.append(found)
    seen += extra
    return [p for p in seen if p and os.path.isfile(p)]


_TOOLS = [os.path.join(ROOT, "tools", "bin")]


def dot_exe() -> str:
    found = _candidates("AMS_DOT", ["dot"], [os.path.join(t, "graphviz", "bin", "dot.exe") for t in _TOOLS])
    if not found:
        sys.exit("Graphviz 'dot' not found. Install Graphviz or set AMS_DOT=<path to dot>.")
    return found[0]


def plantuml_jar() -> str:
    found = _candidates("AMS_PLANTUML", [], [os.path.join(t, "plantuml.jar") for t in _TOOLS])
    if not found:
        sys.exit("plantuml.jar not found. Download PlantUML or set AMS_PLANTUML=<path to the jar>.")
    return found[0]


# ----------------------------------------------------------------------------- names
def hy(name: str) -> str:
    """Display form of a data / process / entity name: plain words on one line ("Valid flight details").
    (Kept under its old name because every diagram script calls it.)"""
    return " ".join(name.replace("\n", " ").split())


def wrap_name(name: str, limit: int = 14) -> str:
    """Break a name into lines at spaces; line breaks already in the name are kept."""
    out = []
    for part in name.split("\n"):
        cur = ""
        for w in part.split():
            if cur and len(cur) + 1 + len(w) > limit:
                out.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        out.append(cur)
    return "\n".join(out)


# ----------------------------------------------------------------------------- rendering
def frame(png_path: str, pad: int = 0) -> None:
    """Figures are used as rendered (white background, no frame). Kept so older callers still work."""
    return None


def run_dot(name: str, dot_src: str, out_dir: str = DIAGRAMS, dpi: int = 160, panel: bool = False) -> str:
    """Write <name>.dot and render <name>.png with Graphviz."""
    os.makedirs(out_dir, exist_ok=True)
    dot_path = os.path.join(out_dir, f"{name}.dot")
    png_path = os.path.join(out_dir, f"{name}.png")
    with open(dot_path, "w", encoding="utf-8") as fh:
        fh.write(dot_src)
    proc = subprocess.run([dot_exe(), "-Tpng", f"-Gdpi={dpi}", dot_path, "-o", png_path],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"dot failed for {name}:\n{proc.stderr}")
    print("rendered", name)
    return png_path


def graph_header(name: str, rankdir: str = "TB", extra: str = "") -> list:
    """Common graph/node/edge defaults."""
    return [f'digraph "{name}" {{',
            f'  graph [rankdir={rankdir} bgcolor="{PANEL_HEX}" fontname="{FONT}" pad=0.3 splines=true {extra}];',
            f'  node [fontname="{FONT}" fontsize=12 color="#000000" fillcolor="{BLUE}" style=filled penwidth=1.3];',
            f'  edge [fontname="{FONT}" fontsize=10 color="{EDGE}" arrowsize=0.7];']


def run_plantuml(puml_path: str, out_dir: str) -> None:
    """Render one .puml to PNG next to the other UML outputs."""
    env = dict(os.environ, GRAPHVIZ_DOT=dot_exe())
    proc = subprocess.run(["java", "-Djava.awt.headless=true", "-jar", plantuml_jar(), "-tpng", "-charset", "UTF-8",
                           "-o", os.path.abspath(out_dir), puml_path], capture_output=True, text=True, env=env)
    if proc.returncode != 0 or "Error" in proc.stdout + proc.stderr:
        sys.exit(f"PlantUML failed for {puml_path}:\n{proc.stdout}\n{proc.stderr}")
