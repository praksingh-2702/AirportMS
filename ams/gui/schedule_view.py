"""Module 1b GUI - Recurring schedule (admin): flight templates and the "generate flights" button."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..config import MAX_SCHEDULE_DAYS, SCHEDULE_HORIZON_DAYS
from .widgets import Button, DataTable, FormPanel, run_action

COLUMNS = [("flight_no", "Flight", 75), ("airline", "Airline", 120), ("route", "Route", 85),
           ("dep_time", "Departs", 70), ("duration", "Duration", 75), ("days", "Runs on", 110),
           ("rows", "Rows", 50), ("fare", "Base fare (Rs)", 100), ("active", "Active", 65)]

FIELDS = [("flight_no", "Flight no.", "entry", ()), ("airline", "Airline", "entry", ()),
          ("origin", "From (IATA)", "entry", ()), ("destination", "To (IATA)", "entry", ()),
          ("dep_time", "Departs (HH:MM)", "entry", ()), ("duration", "Duration (min)", "entry", ()),
          ("days", "Days (Daily / Mon,Wed,Fri)", "entry", ()), ("rows", "Seat rows (1-40)", "entry", ()),
          ("base_fare", "Base fare (Rs)", "entry", ())]


class ScheduleView(ttk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        self._templates = []

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Recurring schedule", style="Heading.TLabel", font="AMSHeading").pack(side="left")
        self.status_var = tk.StringVar()
        ttk.Label(top, textvariable=self.status_var, style="Muted.TLabel").pack(side="right")

        gen = ttk.LabelFrame(self, text="Generate flights from the recurring services", padding=6)
        gen.pack(fill="x", pady=(4, 0))
        ttk.Label(gen, text="Create dated flights for the next").pack(side="left")
        self.days_var = tk.StringVar(value=str(SCHEDULE_HORIZON_DAYS))
        ttk.Entry(gen, textvariable=self.days_var, width=5).pack(side="left", padx=6)
        ttk.Label(gen, text=f"days (1-{MAX_SCHEDULE_DAYS}). Existing and cancelled flights are left alone.").pack(
            side="left")
        Button(gen, text="Generate flights", style="Accent.TButton", command=self.generate).pack(side="right")

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Label(bar, text="Filter").pack(side="left", padx=(0, 4))
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.filter_var, width=18)
        entry.pack(side="left")
        self.filter_var.trace_add("write", lambda *_a: self._show())
        ttk.Label(bar, text="flight no., airline or airport code", style="Muted.TLabel").pack(side="left", padx=8)
        Button(bar, text="Activate / deactivate selected", command=self.toggle).pack(side="right")

        box = ttk.LabelFrame(self, text="Add a recurring service", padding=6)
        box.pack(side="bottom", fill="x")
        self.form = FormPanel(box, FIELDS, columns=3, entry_width=18)
        self.form.pack(fill="x")
        self.form.set({"days": "Daily"})
        Button(box, text="Add recurring service", style="Accent.TButton", command=self.add).pack(anchor="e", pady=(8, 0))

        self.table = DataTable(self, COLUMNS, height=2, empty_text="No recurring services match.")
        self.table.pack(fill="both", expand=True, pady=8)
        self.refresh()

    # ----- data -----
    def refresh(self):
        self._templates = self.ctx.schedule.list_templates()
        self._show()
        end = self.ctx.schedule.schedule_end()
        active = sum(1 for t in self._templates if t.active)
        self.status_var.set(f"{len(self._templates):,} recurring services ({active:,} active)  -  "
                            f"flights exist up to {end or 'nothing yet'}")

    def on_show(self):
        self.refresh()

    def _show(self):
        text = self.filter_var.get().strip().upper()
        rows = []
        for t in self._templates:
            if text and text not in f"{t.flight_no} {t.airline} {t.origin} {t.destination}".upper():
                continue
            rows.append((t.template_id, (t.flight_no, t.airline, f"{t.origin} -> {t.destination}", t.dep_time,
                                         f"{t.duration_min // 60}h {t.duration_min % 60:02d}m", t.days_label,
                                         t.rows, t.base_fare, "Yes" if t.active else "No"),
                         "" if t.active else "cancelled"))
        self.table.load(rows, animate_rows=len(rows) < 120)

    # ----- actions -----
    def generate(self):
        def done(result):
            self.refresh()
            messagebox.showinfo("Schedule generated", result.summary(), parent=self)
        run_action(self, lambda: self.ctx.schedule.generate_flights(self.ctx.user, self.days_var.get(),
                                                                    now=self.ctx.now()), done)

    def add(self):
        d = self.form.get()
        run_action(self, lambda: self.ctx.schedule.add_template(
            self.ctx.user, d["flight_no"], d["airline"], d["origin"], d["destination"], d["dep_time"],
            d["duration"], d["days"], d["rows"], d["base_fare"]),
            lambda t: (self.form.clear(), self.form.set({"days": "Daily"}), self.refresh(),
                       self.table.select(t.template_id),
                       messagebox.showinfo("Added", f"Recurring service {t.flight_no} added ({t.days_label}). "
                                           "Press 'Generate flights' to create its dated flights.", parent=self)))

    def toggle(self):
        iid = self.table.selected_id()
        if iid is None:
            messagebox.showwarning("No service selected", "Select a recurring service first.", parent=self)
            return
        t = self.ctx.schedule.get_template(int(iid))
        run_action(self, lambda: self.ctx.schedule.set_active(self.ctx.user, t.template_id, not t.active),
                   lambda n: (self.refresh(), self.table.select(n.template_id)))
