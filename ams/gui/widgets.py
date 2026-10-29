"""Reusable GUI building blocks: styling, data tables, forms and error display."""
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..errors import AMSError

COLORS = {
    "bg": "#F3F5F8", "card": "#FFFFFF", "header": "#1E3A5F", "header_fg": "#FFFFFF",
    "accent": "#2563EB", "muted": "#5B6675", "ok": "#2E7D32", "danger": "#C62828",
    "seat_free": "#FFFFFF", "seat_taken": "#E8A1A1", "seat_selected": "#43A047",
    "row_cancelled": "#9AA3AE", "row_warn": "#B26A00",
}


def apply_style(root: tk.Tk) -> None:
    default = tkfont.nametofont("TkDefaultFont")
    default.configure(size=10)
    family = default.actual("family")
    tkfont.Font(root, name="AMSTitle", family=family, size=18, weight="bold")
    tkfont.Font(root, name="AMSHeading", family=family, size=12, weight="bold")
    mono = tkfont.nametofont("TkFixedFont").actual("family")
    tkfont.Font(root, name="AMSMono", family=mono, size=12)
    root.option_add("*Font", default)
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=COLORS["bg"])
    style.configure(".", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["card"])
    style.configure("Card.TLabel", background=COLORS["card"])
    style.configure("Header.TFrame", background=COLORS["header"])
    style.configure("Header.TLabel", background=COLORS["header"], foreground=COLORS["header_fg"])
    style.configure("Title.TLabel", font="AMSTitle")
    style.configure("Heading.TLabel", font="AMSHeading")
    style.configure("Muted.TLabel", foreground=COLORS["muted"])
    style.configure("Accent.TButton", background=COLORS["accent"], foreground="white")
    style.map("Accent.TButton", background=[("active", "#1D4ED8")])
    style.configure("Danger.TButton", foreground=COLORS["danger"])
    style.configure("Treeview", rowheight=24)
    style.configure("Treeview.Heading", font="AMSHeading")
    style.configure("TNotebook.Tab", padding=(14, 6))


def show_error(parent, exc: Exception) -> None:
    """Expected errors show their own message; anything else is reported as unexpected."""
    if isinstance(exc, AMSError):
        messagebox.showerror("Cannot complete action", str(exc), parent=parent)
    else:
        messagebox.showerror("Unexpected error", f"{type(exc).__name__}: {exc}", parent=parent)


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


class DataTable(ttk.Frame):
    """A Treeview with headings and a vertical scrollbar. Row iids are record ids."""

    def __init__(self, parent, columns: Sequence[Tuple[str, str, int]], height: int = 10):
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
        self.tree.tag_configure("cancelled", foreground=COLORS["row_cancelled"])
        self.tree.tag_configure("warn", foreground=COLORS["row_warn"])
        self.tree.tag_configure("ok", foreground=COLORS["ok"])

    def load(self, rows: List[Tuple[str, Sequence, str]]) -> None:
        """rows: (iid, values, tag)."""
        self.tree.delete(*self.tree.get_children())
        for iid, values, tag in rows:
            self.tree.insert("", "end", iid=str(iid), values=list(values), tags=(tag,) if tag else ())

    def selected_id(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def select(self, iid) -> None:
        if self.tree.exists(str(iid)):
            self.tree.selection_set(str(iid))
            self.tree.see(str(iid))

    def on_select(self, callback: Callable) -> None:
        self.tree.bind("<<TreeviewSelect>>", lambda _e: callback())


class FormPanel(ttk.Frame):
    """Grid of labelled inputs. fields: (key, label, kind, options) with kind in
    'entry' | 'password' | 'combo'."""

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
