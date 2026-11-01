"""Reusable GUI building blocks: theme, animation helpers, buttons, tables, forms, stat cards, tabs."""
import calendar as _calendar
import math
import os
import subprocess
import sys
import time
import tkinter as tk
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from tkinter import filedialog
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..errors import AMSError

COLORS = {
    "bg": "#EEF2F7", "card": "#FFFFFF", "header": "#0B1F3A", "header_fg": "#FFFFFF",
    "accent": "#2563EB", "accent_hover": "#1D4ED8", "accent_press": "#1E40AF", "accent_soft": "#E0EAFF",
    "text": "#0F172A", "muted": "#64748B", "border": "#CBD5E1", "ok": "#15803D", "danger": "#DC2626",
    "seat_free": "#FFFFFF", "seat_taken": "#E8A1A1", "seat_selected": "#43A047", "seat_hover": "#DBEAFE",
    "row_cancelled": "#9AA3AE", "row_warn": "#B26A00", "zebra": "#F6F8FB", "gold": "#FFD166",
}


# ----------------------------------------------------------------------------- animation helpers
_NAMED = {"white": "#FFFFFF", "black": "#000000"}


def hex_to_rgb(color: str) -> Tuple[int, int, int]:
    color = _NAMED.get(color.lower(), color).lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def mix(c1: str, c2: str, t: float) -> str:
    """Linear blend of two #RRGGBB colours (t=0 -> c1, t=1 -> c2)."""
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    return 3 * t * t - 2 * t ** 3


def linear(t: float) -> float:
    return t


def animate(widget, ms: int, step: Callable[[float], None], done: Optional[Callable] = None,
            ease: Callable[[float], float] = ease_out, key: str = "default") -> None:
    """Run step(progress 0..1) for `ms` milliseconds on the Tk event loop. Starting a new animation
    with the same key on the same widget cancels the previous one."""
    tokens = widget.__dict__.setdefault("_anim_tokens", {})
    token = object()
    tokens[key] = token
    start = time.monotonic()

    def tick():
        try:
            if tokens.get(key) is not token or not widget.winfo_exists():
                return
            t = min(1.0, (time.monotonic() - start) * 1000.0 / max(ms, 1))
            step(ease(t))
            if t < 1.0:
                widget.after(15, tick)
            elif done:
                done()
        except tk.TclError:
            pass
    tick()


def fade_in(win, ms: int = 260) -> None:
    """Fade a top-level window in (silently skipped where alpha is unsupported)."""
    try:
        win.attributes("-alpha", 0.0)
        animate(win, ms, lambda t: win.attributes("-alpha", t), key="fade")
    except tk.TclError:
        pass


def upcoming_dates(n: int = 30) -> List[str]:
    """YYYY-MM-DD strings for today and the next n-1 days (drop-down values for date pickers)."""
    from datetime import date, timedelta
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(n)]


def center_on(win, parent) -> None:
    """Place a dialog in the middle of its parent window instead of the screen corner."""
    win.update_idletasks()
    top = parent.winfo_toplevel()
    x = top.winfo_rootx() + (top.winfo_width() - win.winfo_reqwidth()) // 2
    y = top.winfo_rooty() + (top.winfo_height() - win.winfo_reqheight()) // 2
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def draw_plane(canvas: tk.Canvas, x: float, y: float, scale: float, fill: str, tag: str) -> int:
    """Top-down airliner silhouette pointing right, centred on (x, y)."""
    pts = [(30, 0), (12, -4), (-2, -20), (-8, -20), (0, -4), (-14, -3), (-20, -9), (-24, -9), (-20, 0),
           (-24, 9), (-20, 9), (-14, 3), (0, 4), (-8, 20), (-2, 20), (12, 4)]
    flat = [c for px, py in pts for c in (x + px * scale, y + py * scale)]
    return canvas.create_polygon(flat, fill=fill, outline="", tags=tag)


# ----------------------------------------------------------------------------- theme
def apply_style(root: tk.Tk) -> None:
    default = tkfont.nametofont("TkDefaultFont")
    default.configure(size=10)
    family = default.actual("family")
    root._ams_fonts = fonts = []      # keep references: Tk deletes a named font when its Font object is collected
    mk = lambda **kw: fonts.append(tkfont.Font(root, family=family, **kw))   # noqa: E731
    mk(name="AMSTitle", size=20, weight="bold")
    mk(name="AMSHeading", size=12, weight="bold")
    mk(name="AMSBold", size=10, weight="bold")
    mk(name="AMSButton", size=10, weight="bold")
    mk(name="AMSTab", size=11, weight="bold")
    mk(name="AMSStat", size=20, weight="bold")
    mk(name="AMSSmall", size=9)
    mono = tkfont.nametofont("TkFixedFont").actual("family")
    fonts.append(tkfont.Font(root, name="AMSMono", family=mono, size=12))
    root.option_add("*Font", default)
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=COLORS["bg"])
    c = COLORS
    style.configure(".", background=c["bg"], foreground=c["text"])
    style.configure("Card.TFrame", background=c["card"])
    style.configure("Card.TLabel", background=c["card"])
    style.configure("Card.TCheckbutton", background=c["card"], foreground=c["muted"])
    style.configure("Header.TFrame", background=c["header"])
    style.configure("Header.TLabel", background=c["header"], foreground=c["header_fg"])
    style.configure("Title.TLabel", font="AMSTitle", foreground=c["text"])
    style.configure("Heading.TLabel", font="AMSHeading", foreground=c["text"])
    style.configure("Muted.TLabel", foreground=c["muted"])
    style.configure("TCheckbutton", background=c["bg"])
    style.configure("TEntry", fieldbackground="white", bordercolor=c["border"], lightcolor=c["border"],
                    darkcolor=c["border"], padding=5)
    style.map("TEntry", bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["accent"])],
              darkcolor=[("focus", c["accent"])])
    style.configure("TCombobox", fieldbackground="white", background="white", bordercolor=c["border"],
                    lightcolor=c["border"], darkcolor=c["border"], arrowcolor=c["muted"], padding=4)
    style.map("TCombobox", bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["accent"])],
              darkcolor=[("focus", c["accent"])], fieldbackground=[("readonly", "white")])
    style.configure("TLabelframe", background=c["bg"], bordercolor=c["border"], lightcolor=c["border"],
                    darkcolor=c["border"])
    style.configure("TLabelframe.Label", background=c["bg"], foreground=c["muted"], font="AMSBold")
    style.configure("Treeview", rowheight=28, background="white", fieldbackground="white", borderwidth=0,
                    foreground=c["text"])
    style.map("Treeview", background=[("selected", c["accent"])], foreground=[("selected", "white")])
    style.configure("Treeview.Heading", font="AMSBold", background="#E3EAF3", foreground=c["text"],
                    relief="flat", padding=(6, 7))
    style.map("Treeview.Heading", background=[("active", "#D3DEEC")])
    style.configure("Vertical.TScrollbar", background="#C3CEDC", troughcolor=c["bg"], bordercolor=c["bg"],
                    arrowcolor=c["muted"], relief="flat", arrowsize=13)
    style.map("Vertical.TScrollbar", background=[("active", "#9FB0C7")])


def show_error(parent, exc: Exception) -> None:
    """Expected errors show their own message; anything else is reported as unexpected."""
    if isinstance(exc, AMSError):
        messagebox.showerror("Cannot complete action", str(exc), parent=parent)
    else:
        messagebox.showerror("Unexpected error", f"{type(exc).__name__}: {exc}", parent=parent)


def open_file(path: str) -> None:
    """Open a saved file in the system's default viewer."""
    if sys.platform.startswith("win"):
        os.startfile(path)   # noqa: S606
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])


def save_file(parent, data: bytes, default_name: str, title: str = "Save file") -> Optional[str]:
    """Ask where to save `data`, write it, and offer to open it. Returns the path (None if cancelled)."""
    path = filedialog.asksaveasfilename(parent=parent, title=title, initialfile=default_name,
                                        defaultextension=os.path.splitext(default_name)[1],
                                        filetypes=[("PDF document", "*.pdf"), ("All files", "*.*")])
    if not path:
        return None
    try:
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError as exc:
        messagebox.showerror("Cannot save file", f"Could not write {path}\n{exc}", parent=parent)
        return None
    if messagebox.askyesno("Saved", f"Saved to:\n{path}\n\nOpen it now?", parent=parent):
        try:
            open_file(path)
        except OSError as exc:
            messagebox.showerror("Cannot open file", str(exc), parent=parent)
    return path


def run_action(parent, action: Callable, on_success: Optional[Callable] = None):
    """Run a service call; show errors in a dialog instead of crashing the GUI."""
    try:
        result = action()
    except Exception as exc:   # noqa: BLE001 - every failure must reach the user
        show_error(parent, exc)
        return None
    if on_success:
        on_success(result)
    return result


# ----------------------------------------------------------------------------- animated button
class Button(tk.Label):
    """Flat button with animated hover / press colours. Drop-in for ttk.Button(text, command, style)."""
    KINDS = {
        "primary": dict(bg=COLORS["accent"], hover=COLORS["accent_hover"], press=COLORS["accent_press"],
                        fg="white", border=COLORS["accent"]),
        "danger": dict(bg="#FFFFFF", hover="#FEE2E2", press="#FECACA", fg=COLORS["danger"], border="#FCA5A5"),
        "secondary": dict(bg="#FFFFFF", hover="#EEF4FF", press="#DBE7FF", fg=COLORS["text"],
                          border=COLORS["border"]),
    }
    STYLE_MAP = {"Accent.TButton": "primary", "Danger.TButton": "danger"}

    def __init__(self, parent, text: str = "", command: Optional[Callable] = None, style: Optional[str] = None,
                 **kw):
        kind = self.STYLE_MAP.get(style, style if style in self.KINDS else "secondary")
        self.k = self.KINDS[kind]
        super().__init__(parent, text=text, font="AMSButton", bg=self.k["bg"], fg=self.k["fg"], padx=16,
                         pady=7, cursor="hand2", bd=0, relief="flat", takefocus=True, highlightthickness=1,
                         highlightbackground=self.k["border"], highlightcolor=COLORS["accent"], **kw)
        self.command = command
        self._disabled = False
        self.bind("<Enter>", lambda _e: self._to(self.k["hover"], 130))
        self.bind("<Leave>", lambda _e: self._to(self.k["bg"], 180))
        self.bind("<ButtonPress-1>", lambda _e: self._to(self.k["press"], 60))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())

    def _to(self, color: str, ms: int) -> None:
        if self._disabled:
            return
        start = self.cget("bg")
        animate(self, ms, lambda t: self.configure(bg=mix(start, color, t)), key="bg")

    def _release(self, e) -> None:
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self._to(self.k["hover"] if inside else self.k["bg"], 100)
        if inside:
            self.invoke()

    def invoke(self):
        if self.command and not self._disabled:
            return self.command()

    def configure(self, cnf=None, **kw):   # noqa: D401 - supports state=disabled|normal like ttk
        if "state" in kw:
            self._disabled = kw.pop("state") == "disabled"
            kw["fg"] = COLORS["muted"] if self._disabled else self.k["fg"]
            kw["cursor"] = "arrow" if self._disabled else "hand2"
        if "command" in kw:
            self.command = kw.pop("command")
        return super().configure(cnf, **kw) if cnf else super().configure(**kw)

    config = configure


# ----------------------------------------------------------------------------- data table
class DataTable(ttk.Frame):
    """A Treeview with headings, zebra rows, hover highlight, fade-in on load and an empty-state message.
    Row iids are record ids. The selection survives a reload when the row still exists."""

    TAG_COLORS = {"base": COLORS["text"], "cancelled": COLORS["row_cancelled"], "warn": COLORS["row_warn"],
                  "ok": COLORS["ok"]}

    def __init__(self, parent, columns: Sequence[Tuple[str, str, int]], height: int = 10,
                 empty_text: str = "No records to show."):
        super().__init__(parent)
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], show="headings",
                                 height=height, selectmode="browse")
        for key, heading, width in columns:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, minwidth=40, anchor="w", stretch=True)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        for tag, color in self.TAG_COLORS.items():
            self.tree.tag_configure(tag, foreground=color)
        self.tree.tag_configure("odd", background=COLORS["zebra"])
        self.tree.tag_configure("hover", background=COLORS["accent_soft"])
        self.empty = tk.Label(self.tree, text=empty_text, fg=COLORS["muted"], bg="white", font="AMSHeading")
        self._base_tags: Dict[str, tuple] = {}
        self._hover: Optional[str] = None
        self._notified: Optional[str] = None
        self.tree.bind("<Motion>", self._on_motion)
        self.tree.bind("<Leave>", lambda _e: self._set_hover(None))

    # ----- loading -----
    def load(self, rows: List[Tuple[str, Sequence, str]], animate_rows: bool = True) -> None:
        """rows: (iid, values, tag)."""
        keep = self.selected_id()
        self._hover = None
        self.tree.delete(*self.tree.get_children())
        self._base_tags = {}
        for n, (iid, values, tag) in enumerate(rows):
            tags = (tag or "base",) + (("odd",) if n % 2 else ())
            self._base_tags[str(iid)] = tags
            self.tree.insert("", "end", iid=str(iid), values=list(values), tags=tags)
        if keep is not None and self.tree.exists(keep):
            self._notified = keep          # already reflected in the UI: do not re-fire on_select
            self.tree.selection_set(keep)
        if rows:
            self.empty.place_forget()
            if animate_rows:
                self._fade_rows()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")

    def _fade_rows(self) -> None:
        def step(t):
            for tag, final in self.TAG_COLORS.items():
                self.tree.tag_configure(tag, foreground=mix("#FFFFFF", final, t))
        animate(self, 320, step, key="fade")

    # ----- hover -----
    def _on_motion(self, e) -> None:
        self._set_hover(self.tree.identify_row(e.y) or None)

    def _set_hover(self, iid: Optional[str]) -> None:
        if iid == self._hover:
            return
        if self._hover and self.tree.exists(self._hover):
            self.tree.item(self._hover, tags=self._base_tags.get(self._hover, ()))
        self._hover = iid
        if iid and self.tree.exists(iid):
            self.tree.item(iid, tags=tuple(t for t in self._base_tags.get(iid, ()) if t != "odd") + ("hover",))

    # ----- selection -----
    def selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def select(self, iid) -> None:
        if self.tree.exists(str(iid)):
            self._notified = None
            self.tree.selection_set(str(iid))
            self.tree.see(str(iid))

    def on_select(self, callback: Callable) -> None:
        def handler(_e):
            sel = self.selected_id()
            if sel is None:
                self._notified = None
            elif sel != self._notified:
                self._notified = sel
                callback()
        self.tree.bind("<<TreeviewSelect>>", handler)


# ----------------------------------------------------------------------------- forms
class FormPanel(ttk.Frame):
    """Grid of labelled inputs. fields: (key, label, kind, options) with kind in
    'entry' | 'password' | 'combo' | 'date' | 'datetime' (a calendar drop-down)."""

    def __init__(self, parent, fields: Sequence[Tuple[str, str, str, Sequence[str]]],
                 columns: int = 2, entry_width: int = 22, style: str = "TFrame"):
        super().__init__(parent, style=style)
        label_style = "Card.TLabel" if style == "Card.TFrame" else "TLabel"
        self.vars: Dict[str, tk.StringVar] = {}
        self.widgets: Dict[str, tk.Widget] = {}
        for i, (key, label, kind, options) in enumerate(fields):
            r, c = divmod(i, columns)
            ttk.Label(self, text=label, style=label_style).grid(row=r, column=c * 2, sticky="w",
                                                                padx=(0 if c == 0 else 16, 6), pady=4)
            var = tk.StringVar()
            if kind == "combo":
                w = ttk.Combobox(self, textvariable=var, values=list(options), width=entry_width - 2,
                                 state="readonly" if options else "normal")
            elif kind in ("date", "datetime"):
                w = DateEntry(self, var, width=entry_width if kind == "datetime" else entry_width - 4,
                              with_time=(kind == "datetime"))
            else:
                w = ttk.Entry(self, textvariable=var, width=entry_width, show="*" if kind == "password" else "")
            w.grid(row=r, column=c * 2 + 1, sticky="we", pady=4)
            self.vars[key], self.widgets[key] = var, w

    def get(self) -> Dict[str, str]:
        return {k: var.get() for k, var in self.vars.items()}

    def set(self, values: Dict[str, object]) -> None:
        for k, val in values.items():
            if k in self.vars:
                self.vars[k].set("" if val is None else str(val))

    def clear(self) -> None:
        for var in self.vars.values():
            var.set("")


# ----------------------------------------------------------------------------- stat card
class StatCard(tk.Frame):
    """Dashboard KPI tile whose number counts up/down smoothly when the value changes."""

    def __init__(self, parent, title: str, accent: str):
        super().__init__(parent, bg=COLORS["card"], highlightthickness=1, highlightbackground=COLORS["border"])
        tk.Frame(self, bg=accent, width=5).pack(side="left", fill="y")
        inner = tk.Frame(self, bg=COLORS["card"])
        inner.pack(side="left", fill="both", expand=True, padx=14, pady=8)
        self.value_label = tk.Label(inner, text="0", font="AMSStat", bg=COLORS["card"], fg=COLORS["text"])
        self.value_label.pack(anchor="w")
        tk.Label(inner, text=title, font="AMSSmall", bg=COLORS["card"], fg=COLORS["muted"]).pack(anchor="w")
        self.current = 0

    def set(self, value) -> None:
        if isinstance(value, (int, float)):
            start, end = self.current, int(value)
            if start != end:
                animate(self, 700, lambda t: self.value_label.configure(text=str(int(round(start + (end - start) * t)))),
                        key="count")
            self.current = end
        else:
            self.value_label.configure(text=str(value))


# ----------------------------------------------------------------------------- animated tabs
class TabHost(ttk.Frame):
    """Tab strip with a sliding accent underline; pages slide in when switched.
    API mirrors the bits of ttk.Notebook the app uses: add(view, text=...), select(view)."""

    def __init__(self, parent, on_change: Optional[Callable] = None):
        super().__init__(parent)
        self.on_change = on_change
        self.bar = tk.Canvas(self, height=46, bg=COLORS["bg"], highlightthickness=0)
        self.bar.pack(fill="x")
        self.baseline = self.bar.create_line(0, 45, 4000, 45, fill=COLORS["border"])
        self.indicator = self.bar.create_rectangle(0, 42, 0, 46, fill=COLORS["accent"], width=0)
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)
        self._tabs: List[dict] = []
        self._next_x = 4
        self.current = None

    def add(self, view, text: str = "") -> None:
        width = tkfont.nametofont("AMSTab").measure(text) + 40
        x0, x1 = self._next_x, self._next_x + width
        self._next_x = x1 + 2
        tag = f"tab{len(self._tabs)}"
        self.bar.create_rectangle(x0, 4, x1, 42, fill=COLORS["bg"], outline="", tags=(tag, f"{tag}bg"))
        label = self.bar.create_text((x0 + x1) / 2, 23, text=text, font="AMSTab", fill=COLORS["muted"], tags=tag)
        tab = dict(view=view, x0=x0, x1=x1, label=label, tag=tag)
        self._tabs.append(tab)
        self.bar.tag_bind(tag, "<Button-1>", lambda _e, v=view: self.select(v))
        self.bar.tag_bind(tag, "<Enter>", lambda _e, t=tab: self._hover(t, True))
        self.bar.tag_bind(tag, "<Leave>", lambda _e, t=tab: self._hover(t, False))
        if self.current is None:
            self._activate(tab, animate_it=False)

    def _hover(self, tab, inside: bool) -> None:
        self.bar.configure(cursor="hand2" if inside else "")
        if tab is not self.current:
            self.bar.itemconfigure(tab["label"], fill=COLORS["text"] if inside else COLORS["muted"])

    def select(self, view) -> None:
        tab = next((t for t in self._tabs if t["view"] is view), None)
        if tab is not None and tab is not self.current:
            self._activate(tab, animate_it=True)
            if self.on_change:
                self.on_change(view)

    def _activate(self, tab, animate_it: bool) -> None:
        old, self.current = self.current, tab
        for t in self._tabs:
            self.bar.itemconfigure(t["label"], fill=COLORS["accent"] if t is tab else COLORS["muted"])
        x0, y0, x1, y1 = self.bar.coords(self.indicator)
        nx0, nx1 = tab["x0"] + 8, tab["x1"] - 8
        if animate_it:
            animate(self.bar, 260, lambda t: self.bar.coords(
                self.indicator, x0 + (nx0 - x0) * t, 42, x1 + (nx1 - x1) * t, 46), ease=ease_in_out, key="ind")
        else:
            self.bar.coords(self.indicator, nx0, 42, nx1, 46)
        if old is not None:
            old["view"].place_forget()
        view = tab["view"]
        view.place(x=0, y=0, relwidth=1, relheight=1, in_=self.body)
        if animate_it:
            animate(self, 220, lambda t: view.place_configure(x=int(46 * (1 - t))), key="slide")


# ----------------------------------------------------------------------------- drop-down calendar
MONTH_NAMES = list(_calendar.month_name)[1:]


class CalendarPopup(tk.Toplevel):
    """Borderless month calendar that drops down under `anchor`. Pick a day to choose it; use the arrows,
    the month list or the year box to reach any month. Closes on pick, Escape or a click outside."""
    CELL_W = 5

    def __init__(self, anchor, current: Optional[_date], on_pick: Callable[[_date], None],
                 on_clear: Optional[Callable[[], None]] = None):
        super().__init__(anchor.winfo_toplevel())
        self.overrideredirect(True)
        self.anchor, self.on_pick, self.on_clear = anchor, on_pick, on_clear
        self.today, self.selected = _date.today(), current
        base = current or self.today
        self.year, self.month = base.year, base.month
        self._closed = False
        self.configure(bg=COLORS["accent"], padx=1, pady=1)          # 1px accent border
        body = tk.Frame(self, bg="white", padx=12, pady=10)
        body.pack()

        head = tk.Frame(body, bg="white")
        head.pack(fill="x", pady=(0, 6))
        self._nav(head, "\u2039", -1).pack(side="left")
        self.month_var, self.year_var = tk.StringVar(), tk.StringVar()
        self.month_box = ttk.Combobox(head, textvariable=self.month_var, values=MONTH_NAMES, state="readonly", width=10)
        self.month_box.pack(side="left", padx=(6, 4))
        self.month_box.bind("<<ComboboxSelected>>", lambda _e: self._jump())
        self.year_box = ttk.Spinbox(head, from_=1990, to=2100, textvariable=self.year_var, width=5, command=self._jump)
        self.year_box.pack(side="left")
        self.year_box.bind("<Return>", lambda _e: self._jump())
        self.year_box.bind("<FocusOut>", lambda _e: self._jump())
        self._nav(head, "\u203a", +1).pack(side="right")

        self.grid_frame = tk.Frame(body, bg="white")
        self.grid_frame.pack()
        for c, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            tk.Label(self.grid_frame, text=name, width=self.CELL_W, bg="white", fg=COLORS["muted"],
                     font="AMSSmall").grid(row=0, column=c, pady=(0, 2))
        self.cells, self.cell_dates, self.cell_style = [], [], []
        for i in range(42):
            lab = tk.Label(self.grid_frame, width=self.CELL_W, height=1, bg="white", cursor="hand2",
                           highlightthickness=1, highlightbackground="white", pady=3)
            lab.grid(row=1 + i // 7, column=i % 7, padx=1, pady=1)
            lab.bind("<Enter>", lambda _e, k=i: self._hover(k, True))
            lab.bind("<Leave>", lambda _e, k=i: self._hover(k, False))
            lab.bind("<Button-1>", lambda _e, k=i: self._pick(k))
            self.cells.append(lab)

        foot = tk.Frame(body, bg="white")
        foot.pack(fill="x", pady=(8, 0))
        Button(foot, text="Today", command=lambda: self._choose(self.today)).pack(side="left")
        if on_clear:
            Button(foot, text="Clear", command=self._clear).pack(side="right")
        self._render(fade=False)

        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<ButtonPress-1>", self._outside_click)
        self._place()
        fade_in(self, 140)
        self.update()
        try:
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            pass

    # ----- building blocks -----
    def _nav(self, parent, glyph, step):
        lab = tk.Label(parent, text=glyph, font="AMSHeading", bg="white", fg=COLORS["accent"], cursor="hand2", width=2)
        lab.bind("<Enter>", lambda _e: lab.configure(bg=COLORS["accent_soft"]))
        lab.bind("<Leave>", lambda _e: lab.configure(bg="white"))
        lab.bind("<Button-1>", lambda _e: self._shift(step))
        return lab

    def _place(self):
        self.update_idletasks()
        a = self.anchor
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x, y = a.winfo_rootx(), a.winfo_rooty() + a.winfo_height() + 2
        if x + w > self.winfo_screenwidth():
            x = self.winfo_screenwidth() - w - 8
        if y + h > self.winfo_screenheight():
            y = a.winfo_rooty() - h - 2                                  # not enough room below: open upwards
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    # ----- navigation -----
    def _shift(self, step: int):
        month = self.month + step
        self.year += (month - 1) // 12
        self.month = (month - 1) % 12 + 1
        self._render()

    def _jump(self):
        try:
            year = int(self.year_var.get())
        except ValueError:
            year = self.year
        month = MONTH_NAMES.index(self.month_var.get()) + 1 if self.month_var.get() in MONTH_NAMES else self.month
        year = min(max(year, 1990), 2100)
        if (year, month) != (self.year, self.month):
            self.year, self.month = year, month
            self._render()
        else:
            self.year_var.set(str(self.year))

    def _render(self, fade: bool = True):
        self.month_var.set(MONTH_NAMES[self.month - 1])
        self.year_var.set(str(self.year))
        first = _date(self.year, self.month, 1)
        start = first - _timedelta(days=first.weekday())               # Monday on or before the 1st
        self.cell_dates = [start + _timedelta(days=i) for i in range(42)]
        self.cell_style = []
        for lab, d in zip(self.cells, self.cell_dates):
            in_month = d.month == self.month
            if d == self.selected:
                style = dict(bg=COLORS["accent"], fg="white", font="AMSBold", hb=COLORS["accent"])
            else:
                style = dict(bg="white", fg=COLORS["text"] if in_month else "#B4BFCE",
                             font="AMSBold" if d == self.today else "TkDefaultFont",
                             hb=COLORS["accent"] if d == self.today else "white")
            self.cell_style.append(style)
            lab.configure(text=str(d.day), bg=style["bg"], fg=style["fg"], font=style["font"],
                          highlightbackground=style["hb"])
        if fade:
            def step(t):
                for lab, st in zip(self.cells, self.cell_style):
                    if st["bg"] == "white":
                        lab.configure(fg=mix("#FFFFFF", st["fg"], t))
            animate(self.grid_frame, 200, step, key="month")

    def _hover(self, i: int, inside: bool):
        st = self.cell_style[i]
        if st["bg"] == "white":
            self.cells[i].configure(bg=COLORS["accent_soft"] if inside else "white")

    # ----- choosing -----
    def _pick(self, i: int):
        self._choose(self.cell_dates[i])

    def _choose(self, d: _date):
        self.close()
        self.on_pick(d)

    def _clear(self):
        self.close()
        if self.on_clear:
            self.on_clear()

    def _outside_click(self, e):
        inside = (0 <= e.x_root - self.winfo_rootx() < self.winfo_width()
                  and 0 <= e.y_root - self.winfo_rooty() < self.winfo_height())
        if not inside:
            self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.grab_release()
            self.destroy()
        except tk.TclError:
            pass


class CalendarIcon(tk.Canvas):
    """Small drawn calendar icon used as the button of a DateEntry (no image or emoji font needed)."""

    def __init__(self, parent, command: Callable):
        super().__init__(parent, width=32, height=28, bg="white", highlightthickness=1,
                         highlightbackground=COLORS["border"], cursor="hand2", takefocus=False)
        self.command = command
        self.create_rectangle(8, 7, 24, 22, outline=COLORS["muted"], width=1.4)
        self.create_rectangle(8, 7, 24, 12, fill=COLORS["accent"], outline=COLORS["accent"])
        for x in (12, 20):
            self.create_line(x, 4, x, 9, fill=COLORS["muted"], width=1.6)
        for r in range(2):
            for c in range(3):
                self.create_rectangle(11 + c * 4, 14 + r * 4, 13 + c * 4, 16 + r * 4, fill=COLORS["muted"], width=0)
        self.bind("<Enter>", lambda _e: self._to(COLORS["accent_soft"]))
        self.bind("<Leave>", lambda _e: self._to("white"))
        self.bind("<Button-1>", lambda _e: self.command())

    def _to(self, color):
        start = self.cget("bg")
        animate(self, 140, lambda t: self.configure(bg=mix(start, color, t)), key="bg")


class DateEntry(ttk.Frame):
    """A text box (you can still type) plus a calendar button that opens a drop-down calendar.
    Works on a StringVar holding 'YYYY-MM-DD', or 'YYYY-MM-DD HH:MM' when with_time=True (the time part
    is kept when you pick another day). `command` runs after a day is picked or cleared."""

    def __init__(self, parent, textvariable: tk.StringVar, width: int = 12, with_time: bool = False,
                 default_time: str = "08:00", command: Optional[Callable] = None):
        super().__init__(parent)
        self.var, self.with_time, self.default_time, self.command = textvariable, with_time, default_time, command
        self.popup: Optional[CalendarPopup] = None
        self.entry = ttk.Entry(self, textvariable=textvariable, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        self.icon = CalendarIcon(self, self.toggle)
        self.icon.pack(side="left", padx=(3, 0))
        self.entry.bind("<Down>", lambda _e: self.open())

    def current_date(self) -> Optional[_date]:
        text = self.var.get().strip()[:10]
        try:
            return _datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    def toggle(self):
        if self.popup is not None and self.popup.winfo_exists() and not self.popup._closed:
            self.popup.close()
        else:
            self.open()

    def open(self):
        self.popup = CalendarPopup(self.entry, self.current_date(), self._picked,
                                   on_clear=self._cleared if not self.with_time else None)

    def _picked(self, d: _date):
        text = d.isoformat()
        if self.with_time:
            old = self.var.get().strip()[11:16]
            text += " " + (old if len(old) == 5 and old[2] == ":" else self.default_time)
        self.var.set(text)
        self.entry.focus_set()
        if self.command:
            self.command()

    def _cleared(self):
        self.var.set("")
        if self.command:
            self.command()
