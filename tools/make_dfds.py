"""Render all DFDs (context, level 1, level 2, level 3) from tools/dfd_spec.py with Graphviz:

  yellow rectangle = external entity      blue circle = process (number on top, e.g. 0.2.1, then its name)
  open-ended box with D# = data store     arrow = data flow, labelled with the data name

and check that every level balances with its parent. Dashed circles in a level 2/3 diagram are the
neighbouring bubbles of the parent level that exchange data with the one being decomposed.
Usage: python tools/make_dfds.py   (needs Graphviz; see tools/bookstyle.py)
"""
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookstyle as B  # noqa: E402
import dfd_spec as S  # noqa: E402

ENTITY = f'shape=box style=filled fillcolor="{B.YELLOW}" penwidth=1.6 margin="0.16,0.09" fontsize=13'
EDGE_LABELS = f'fontsize=11'


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pid_key(pid):
    return tuple(int(x) for x in pid.split("."))


def store_node(code):
    """Open-ended rectangle: a grey cell with the store code (D1..) and the store's name."""
    label = (f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5">'
             f'<TR><TD SIDES="TBR" BGCOLOR="{B.GREY}"><B>{code}</B></TD>'
             f'<TD SIDES="TB" WIDTH="120" ALIGN="LEFT">{esc(B.hy(S.STORES[code]))}</TD></TR></TABLE>>')
    return f'  "{code}" [shape=plain style=none fontsize=12 label={label}];'


def proc_node(pid, name, size=1.3, dashed=False, fontsize=12):
    label = f"{pid}\\n" + B.wrap_name(name).replace("\n", "\\n")
    style = 'style="filled,dashed"' if dashed else "style=filled"
    return (f'  "{pid}" [shape=circle {style} fillcolor="{B.BLUE}" penwidth=1.6 fixedsize=true width={size} '
            f'fontsize={fontsize} label="{label}"];')


def flow_label(labels):
    return "\\n".join(B.hy(x) for x in labels)


def level2_neighbours(spec):
    """Level-1 bubbles (not in this diagram) that exchange data with it."""
    out = {}
    for src, dst, _ in spec["flows"]:
        for x in (src, dst):
            if x in S.LEVEL1_PROCESSES and x not in spec["processes"]:
                out[x] = S.LEVEL1_PROCESSES[x]
    return out


def diagram(name, processes, flows, extra_procs=None, nodesep=0.5, ranksep=0.9, proc_size=1.3, top=None):
    """Generic DFD laid out in five bands: entities / processes (row 1) / data stores /
    processes (row 2) / entities. Entities are repeated once per process they touch."""
    extra_procs = extra_procs or {}
    ids = sorted(processes, key=pid_key)
    top = top if top is not None else ids[: (len(ids) + 1) // 2]
    level = {pid: (1 if pid in top else 3) for pid in ids}
    for pid in sorted(extra_procs, key=pid_key):              # neighbours go to the emptier row
        if pid in top:                                         # unless the caller placed them explicitly
            level[pid] = 1
            continue
        row1 = sum(1 for v in level.values() if v == 1)
        row3 = sum(1 for v in level.values() if v == 3)
        level[pid] = 1 if row1 <= row3 else 3
    lines = B.graph_header(name, "TB", f"nodesep={nodesep} ranksep={ranksep} newrank=true")
    for pid, pname in processes.items():
        lines.append(proc_node(pid, pname, proc_size))
    for pid, pname in extra_procs.items():
        lines.append(proc_node(pid, pname, proc_size, dashed=True))
    stores_used = sorted({x for f in flows for x in f[:2] if x in S.STORES})
    for code in stores_used:
        lines.append(store_node(code))
        level[code] = 2
    entity_copies = {}
    for src, dst, _ in flows:
        for ent, proc in ((src, dst), (dst, src)):
            if ent in S.ENTITIES and (ent, proc) not in entity_copies:
                nid = f"{ent}_{proc}"
                entity_copies[(ent, proc)] = nid
                level[nid] = 0 if level[proc] == 1 else 4
                lines.append(f'  "{nid}" [{ENTITY} label="{B.hy(S.ENTITIES[ent])}"];')

    def node(x, other):
        return entity_copies[(x, other)] if x in S.ENTITIES else x

    merged = defaultdict(list)
    for src, dst, labels in flows:
        merged[(node(src, dst), node(dst, src))].extend(labels)
    for (a, b), labels in merged.items():
        label = flow_label(labels)
        if level[a] == level[b]:
            lines.append(f'  "{a}" -> "{b}" [label="{label}" constraint=false];')
        elif level[a] < level[b]:
            lines.append(f'  "{a}" -> "{b}" [label="{label}"];')
        else:   # draw top-to-bottom for layout; the arrowhead still points to the real target
            lines.append(f'  "{b}" -> "{a}" [label="{label}" dir=back];')
    for row in (1, 3):   # keep numbering left-to-right within each row
        order = top if row == 1 else sorted(level, key=lambda p: pid_key(p) if p[0].isdigit() else (99,))
        row_ids = [pid for pid in order if pid in level and p_is_proc(pid) and level[pid] == row]
        for a, b in zip(row_ids, row_ids[1:]):
            lines.append(f'  "{a}" -> "{b}" [style=invis weight=10];')
    for band in range(5):
        members = [n for n, lv in level.items() if lv == band]
        if members:
            lines.append("  { rank=same; " + " ".join(f'"{m}";' for m in members) + " }")
    lines.append("}")
    return "\n".join(lines)


def columns_diagram(name, processes, flows, order=None, e_order=None, s_order=None, proc_size=1.5, ranksep=3.2, nodesep=0.45):
    """Level-1 layout used by the book's larger examples: every external entity drawn once on the left,
    the bubbles in the middle, the data stores on the right (compact, and portrait-shaped for the page)."""
    lines = B.graph_header(name, "LR", f"nodesep={nodesep} ranksep={ranksep} newrank=true")
    for pid, pname in processes.items():
        lines.append(proc_node(pid, pname, proc_size))
    used_e = [e for e in S.ENTITIES if any(e in f[:2] for f in flows)]
    used_s = sorted({x for f in flows for x in f[:2] if x in S.STORES})
    for e in used_e:
        lines.append(f'  "{e}" [{ENTITY} label="{B.hy(S.ENTITIES[e])}"];')
    for code in used_s:
        lines.append(store_node(code))
    lines.append("  { rank=same; " + " ".join(f'"{e}";' for e in used_e) + " }")
    lines.append("  { rank=same; " + " ".join(f'"{p}";' for p in processes) + " }")
    lines.append("  { rank=same; " + " ".join(f'"{c}";' for c in used_s) + " }")
    merged = defaultdict(list)
    for src, dst, labels in flows:
        merged[(src, dst)].extend(labels)
    for (a, b), labels in merged.items():
        label = flow_label(labels)
        if a in S.ENTITIES:
            lines.append(f'  "{a}" -> "{b}" [label="{label}"];')
        elif b in S.ENTITIES:
            lines.append(f'  "{b}" -> "{a}" [label="{label}" dir=back];')
        elif b in S.STORES:
            lines.append(f'  "{a}" -> "{b}" [label="{label}"];')
        elif a in S.STORES:
            lines.append(f'  "{b}" -> "{a}" [label="{label}" dir=back];')
        else:   # bubble to bubble: no influence on the columns; the two directions leave on opposite sides
            side = "w" if a < b else "e"
            lines.append(f'  "{a}":{side} -> "{b}":{side} [label="{label}" constraint=false];')
    def chain(ids):
        for a, b in zip(ids, ids[1:]):
            lines.append(f'  "{a}" -> "{b}" [style=invis weight=100];')
    chain(order or list(processes))
    chain([e for e in (e_order or used_e) if e in used_e])
    chain([c for c in (s_order or used_s) if c in used_s])
    lines.append("}")
    return "\n".join(lines)


def p_is_proc(x):
    return x[0].isdigit()


def context_diagram():
    lines = B.graph_header("context", "LR", "nodesep=0.9 ranksep=2.8")
    lines.append(f'  "0" [shape=circle style=filled fillcolor="{B.BLUE}" penwidth=2.2 fixedsize=true width=2.4 '
                 f'fontsize=15 label="0\\nAirport\\nManagement\\nSystem"];')
    for code, name in S.ENTITIES.items():
        lines.append(f'  "{code}" [{ENTITY} fontsize=14 label="{B.hy(name)}"];')
    for src, dst, labels in S.CONTEXT:
        lines.append(f'  "{src}" -> "{dst}" [label="{flow_label(labels)}"];')
    lines.append('  { rank=min; "PAX"; } { rank=max; "STF"; "ADM"; "GW"; }')
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
    ctx = {(s if s != "0" else "*", d if d != "0" else "*", l) for s, d, ls in S.CONTEXT for l in ls}
    l1 = _labels(S.LEVEL1_FLOWS, lambda s, d: s in S.ENTITIES or d in S.ENTITIES)
    if ctx != l1:
        problems.append(f"Context vs Level 1 mismatch: missing in L1 {ctx - l1}, extra in L1 {l1 - ctx}")
    for pid, spec in S.LEVEL2.items():
        parent = _labels([f for f in S.LEVEL1_FLOWS if pid in f[:2]], lambda s, d: True)
        child = _labels(spec["flows"], lambda s, d: s not in spec["processes"] or d not in spec["processes"])
        if parent != child:
            problems.append(f"{pid}: missing in L2 {parent - child}, extra in L2 {child - parent}")
    return problems


def main():
    for old in glob.glob(os.path.join(B.DIAGRAMS, "dfd_*")):       # stale files from the previous numbering
        os.remove(old)
    B.run_dot("dfd_context_level0", context_diagram())
    B.run_dot("dfd_level1", diagram("Level 1", S.LEVEL1_PROCESSES, S.LEVEL1_FLOWS, nodesep=0.3, ranksep=1.3,
                                    proc_size=1.55, top=["0.1", "0.3", "0.4", "0.8"]))
    for pid, spec in S.LEVEL2.items():
        B.run_dot(f"dfd_level2_{pid.replace('.', '_')}",
                  diagram(f"Level 2 - {pid}", spec["processes"], spec["flows"],
                          extra_procs=level2_neighbours(spec), proc_size=1.5))
    for pid, spec in S.LEVEL3.items():
        B.run_dot(f"dfd_level3_{pid.replace('.', '_')}",
                  diagram(f"Level 3 - {pid}", spec["processes"], spec["flows"],
                          extra_procs=spec["external_processes"], proc_size=1.5, ranksep=1.1,
                          top=["0.5.1", "0.5.2.1", "0.5.2.2", "0.5.2.3", "0.5.2.4", "0.5.2.5", "0.5.3"]))
    problems = check_balance()
    print("BALANCING:", "OK" if not problems else "\n  " + "\n  ".join(problems))
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
