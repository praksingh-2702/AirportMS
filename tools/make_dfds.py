"""Render all DFDs (context, level 1, level 2, level 3) from tools/dfd_spec.py with Graphviz,
and check that every level balances with its parent.

Style: yellow rectangle = external entity (repeated beside each process to avoid crossing
lines), blue circle = process, open-ended rectangle D# = data store, arrow = data flow.
Usage: python tools/make_dfds.py  (needs the Graphviz 'dot' program)
"""
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dfd_spec as S  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "diagrams")
FONT = "DejaVu Sans"
ENTITY_STYLE = f'shape=box style=filled fillcolor="#FFF4C2" color="#000000" penwidth=1.6 fontname="{FONT}" fontsize=12 margin="0.15,0.08"'
PROC_STYLE = f'shape=circle style=filled fillcolor="#D9E8FB" color="#000000" penwidth=1.6 fontname="{FONT}" fontsize=12 fixedsize=true'
EDGE_STYLE = f'color="#444444" fontname="{FONT}" fontsize=10 arrowsize=0.7'


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def store_node(node_id, code):
    label = (f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5">'
             f'<TR><TD SIDES="TBR" BGCOLOR="#E6E6E6"><B>{code}</B></TD>'
             f'<TD SIDES="TB" WIDTH="110" ALIGN="LEFT">{esc(S.STORES[code])}</TD></TR></TABLE>>')
    return f'  "{node_id}" [shape=plain label={label} fontname="{FONT}" fontsize=12];'


def proc_node(pid, name, size=1.25):
    label = f"{pid}\\n" + name.replace("\n", "\\n")
    return f'  "{pid}" [{PROC_STYLE} width={size} label="{label}"];'


def render(name, dot_src):
    os.makedirs(OUT, exist_ok=True)
    dot_path = os.path.join(OUT, f"{name}.dot")
    with open(dot_path, "w", encoding="utf-8") as fh:
        fh.write(dot_src)
    subprocess.run(["dot", "-Tpng", "-Gdpi=170", dot_path, "-o", os.path.join(OUT, f"{name}.png")], check=True)
    print("rendered", name)


def diagram(name, processes, flows, extra_procs=None, rankdir="TB", nodesep=0.5, ranksep=0.9,
            proc_size=1.25, top=None):
    """Generic DFD laid out in five bands: entities / processes (row 1) / data stores /
    processes (row 2) / entities. Entities are repeated once per process they touch."""
    all_procs = dict(processes)
    all_procs.update(extra_procs or {})
    ids = sorted(all_procs, key=lambda p: tuple(int(x) for x in p.split(".")))
    top = top if top is not None else ids[: (len(ids) + 1) // 2]
    level = {pid: (1 if pid in top else 3) for pid in ids}
    lines = [f'digraph "{name}" {{', f'  graph [rankdir={rankdir} splines=true nodesep={nodesep} '
             f'ranksep={ranksep} fontname="{FONT}" pad=0.3 newrank=true];',
             f'  edge [{EDGE_STYLE}];']
    for pid, pname in processes.items():
        lines.append(proc_node(pid, pname, proc_size))
    for pid, pname in (extra_procs or {}).items():   # neighbours from the parent level, dashed
        lines.append(proc_node(pid, pname, proc_size).replace('style=filled', 'style="filled,dashed"'))
    stores_used = sorted({x for f in flows for x in f[:2] if x in S.STORES})
    for code in stores_used:
        lines.append(store_node(code, code))
        level[code] = 2
    entity_copies = {}
    for src, dst, _ in flows:
        for ent, proc in ((src, dst), (dst, src)):
            if ent in S.ENTITIES and (ent, proc) not in entity_copies:
                nid = f"{ent}_{proc}"
                entity_copies[(ent, proc)] = nid
                level[nid] = 0 if level[proc] == 1 else 4
                lines.append(f'  "{nid}" [{ENTITY_STYLE} label="{S.ENTITIES[ent]}"];')

    def node(x, other):
        return entity_copies[(x, other)] if x in S.ENTITIES else x

    merged = defaultdict(list)
    for src, dst, labels in flows:
        merged[(node(src, dst), node(dst, src))].extend(labels)
    newline = "\\n"
    for (a, b), labels in merged.items():
        label = newline.join(labels)
        if level[a] == level[b]:
            lines.append(f'  "{a}" -> "{b}" [label="{label}" constraint=false];')
        elif level[a] < level[b]:
            lines.append(f'  "{a}" -> "{b}" [label="{label}"];')
        else:   # draw top-to-bottom for layout, arrow still points to the real target
            lines.append(f'  "{b}" -> "{a}" [label="{label}" dir=back];')
    for row in (1, 3):   # keep process numbering left-to-right within each row
        row_ids = [pid for pid in ids if level[pid] == row]
        for a, b in zip(row_ids, row_ids[1:]):
            lines.append(f'  "{a}" -> "{b}" [style=invis weight=10];')
    for band in range(5):
        members = [n for n, lv in level.items() if lv == band]
        if members:
            lines.append("  { rank=same; " + " ".join(f'"{m}";' for m in members) + " }")
    lines.append("}")
    return "\n".join(lines)


def context_diagram():
    lines = ['digraph context {', f'  graph [rankdir=LR splines=true nodesep=0.9 ranksep=2.6 '
             f'fontname="{FONT}" pad=0.3];', f'  edge [{EDGE_STYLE} fontsize=11];',
             f'  "0" [{PROC_STYLE} width=2.4 fontsize=15 penwidth=2.2 label="0\\nAirport\\nManagement\\nSystem"];']
    for code, name in S.ENTITIES.items():
        lines.append(f'  "{code}" [{ENTITY_STYLE} fontsize=14 label="{name}"];')
    for src, dst, labels in S.CONTEXT:
        lines.append(f'  "{src}" -> "{dst}" [label="{chr(10).join(labels)}"];'.replace(chr(10), "\\n"))
    lines.append('  { rank=min; "PAX"; } { rank=max; "STF"; "ADM"; }')
    lines.append("}")
    return "\n".join(lines)


# ---------------- balancing check ----------------
def _labels(flows, side_filter):
    out = set()
    for src, dst, labels in flows:
        if side_filter(src, dst):
            out.update((src if src in S.ENTITIES or src in S.STORES else "*",
                        dst if dst in S.ENTITIES or dst in S.STORES else "*", l) for l in labels)
    return out


def check_balance():
    problems = []
    # Context vs level 1: entity flows must match exactly
    ctx = {(s if s != "0" else "*", d if d != "0" else "*", l) for s, d, ls in S.CONTEXT for l in ls}
    l1 = _labels(S.LEVEL1_FLOWS, lambda s, d: s in S.ENTITIES or d in S.ENTITIES)
    if ctx != l1:
        problems.append(f"Context vs Level 1 mismatch: missing in L1 {ctx - l1}, extra in L1 {l1 - ctx}")
    # Level 1 process vs its level-2 diagram: external (entity/store) flows must match
    for pid, spec in S.LEVEL2.items():
        parent = _labels([f for f in S.LEVEL1_FLOWS if pid in f[:2]], lambda s, d: True)
        child = _labels(spec["flows"], lambda s, d: s not in spec["processes"] or d not in spec["processes"])
        if parent != child:
            problems.append(f"{pid}: missing in L2 {parent - child}, extra in L2 {child - parent}")
    return problems


def main():
    render("dfd_context_level0", context_diagram())
    render("dfd_level1", diagram("Level 1", S.LEVEL1_PROCESSES, S.LEVEL1_FLOWS,
                                 nodesep=0.3, ranksep=1.3, proc_size=1.5, top=["1.0", "3.0", "4.0"]))
    for pid, spec in S.LEVEL2.items():
        render(f"dfd_level2_{pid.replace('.', '_')}",
               diagram(f"Level 2 - {pid}", spec["processes"], spec["flows"], proc_size=1.45))
    for pid, spec in S.LEVEL3.items():
        render(f"dfd_level3_{pid.replace('.', '_')}",
               diagram(f"Level 3 - {pid}", spec["processes"], spec["flows"],
                       extra_procs=spec["external_processes"], proc_size=1.45, ranksep=1.1,
                       top=["5.1", "5.2.1", "5.2.2", "5.2.3", "5.2.4", "5.3"]))
    problems = check_balance()
    print("BALANCING:", "OK" if not problems else "\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    main()
