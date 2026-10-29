"""Module 1 GUI - Flight scheduling (admin edits; staff and passengers view only)."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..models import FlightStatus, Role, fmt_dt
from .widgets import DataTable, FormPanel, run_action

COLUMNS = [("flight_no", "Flight", 80), ("airline", "Airline", 130), ("route", "Route", 90),
           ("departure", "Departure", 130), ("arrival", "Arrival", 130), ("gate", "Gate", 55),
           ("seats", "Booked/Cap", 90), ("fare", "Fare (Rs)", 80), ("status", "Status", 95)]

FIELDS = [("flight_no", "Flight no.", "entry", ()), ("airline", "Airline", "entry", ()),
          ("origin", "From (IATA)", "entry", ()), ("destination", "To (IATA)", "entry", ()),
          ("departure", "Departure (YYYY-MM-DD HH:MM)", "entry", ()),
          ("arrival", "Arrival (YYYY-MM-DD HH:MM)", "entry", ()),
          ("rows", "Seat rows (1-40, 6 per row)", "entry", ()), ("fare", "Fare (Rs)", "entry", ()),
          ("gate", "Gate (A1-D20, optional)", "entry", ())]


class FlightView(ttk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        self.is_admin = ctx.user.role == Role.ADMIN

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Flight Schedule", style="Heading.TLabel").pack(side="left")
        self.show_all = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Include departed/cancelled", variable=self.show_all,
                        command=self.refresh).pack(side="right")
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right", padx=8)

        self.table = DataTable(self, COLUMNS, height=11)
        self.table.pack(fill="both", expand=True, pady=8)
        self.table.on_select(self.on_select)

        if not self.is_admin:
            ttk.Label(self, text="View only: flights are added and edited by an administrator.",
                      style="Muted.TLabel").pack(anchor="w")
        else:
            self._build_editor()
        self.refresh()

    def _build_editor(self):
        box = ttk.LabelFrame(self, text="Add / update flight", padding=10)
        box.pack(fill="x")
        self.form = FormPanel(box, FIELDS, columns=3, entry_width=18)
        self.form.pack(fill="x")
        actions = ttk.Frame(box)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Add flight", style="Accent.TButton", command=self.add).pack(side="left")
        ttk.Button(actions, text="Update selected", command=self.update).pack(side="left", padx=6)
        ttk.Button(actions, text="Clear form", command=self.clear).pack(side="left")
        ttk.Button(actions, text="Cancel flight", style="Danger.TButton", command=self.cancel).pack(side="right")
        self.status_var = tk.StringVar()
        ttk.Button(actions, text="Set status", command=self.set_status).pack(side="right", padx=6)
        ttk.Combobox(actions, textvariable=self.status_var, state="readonly", width=12,
                     values=[s.value for s in FlightStatus if s != FlightStatus.CANCELLED]).pack(side="right")
        self.gate_var = tk.StringVar()
        ttk.Label(actions, text="   Gate:").pack(side="left", padx=(20, 4))
        ttk.Entry(actions, textvariable=self.gate_var, width=6).pack(side="left")
        ttk.Button(actions, text="Assign gate", command=self.assign_gate).pack(side="left", padx=6)

    # ----- data -----
    def refresh(self):
        fs = self.ctx.flights
        statuses = None if self.show_all.get() else [FlightStatus.SCHEDULED, FlightStatus.DELAYED,
                                                      FlightStatus.BOARDING]
        rows = []
        for f in fs.list_flights(statuses):
            tag = {"CANCELLED": "cancelled", "DEPARTED": "cancelled", "DELAYED": "warn",
                   "BOARDING": "ok"}.get(f.status.value, "")
            rows.append((f.flight_id, (f.flight_no, f.airline, f"{f.origin} -> {f.destination}",
                                       fmt_dt(f.departure), fmt_dt(f.arrival), f.gate or "—",
                                       f"{fs.booked_count(f.flight_id)}/{f.capacity}", f.fare,
                                       f.status.value), tag))
        self.table.load(rows)

    def selected(self):
        iid = self.table.selected_id()
        if iid is None:
            messagebox.showwarning("No flight selected", "Select a flight in the table first.", parent=self)
            return None
        return int(iid)

    def on_select(self):
        if not self.is_admin or self.table.selected_id() is None:
            return
        f = self.ctx.flights.get_flight(int(self.table.selected_id()))
        self.form.set({"flight_no": f.flight_no, "airline": f.airline, "origin": f.origin,
                       "destination": f.destination, "departure": fmt_dt(f.departure),
                       "arrival": fmt_dt(f.arrival), "rows": f.rows, "fare": f.fare, "gate": f.gate})
        self.gate_var.set(f.gate or "")
        self.status_var.set(f.status.value)

    def _done(self, message, flight_id=None):
        def callback(_result):
            self.refresh()
            if flight_id is not None:
                self.table.select(flight_id)
            messagebox.showinfo("Done", message, parent=self)
        return callback

    # ----- actions -----
    def add(self):
        d = self.form.get()
        run_action(self, lambda: self.ctx.flights.add_flight(self.ctx.user, now=self.ctx.now(), **d),
                   lambda f: (self.refresh(), self.table.select(f.flight_id),
                              messagebox.showinfo("Done", f"Flight {f.flight_no} added.", parent=self)))

    def update(self):
        fid = self.selected()
        if fid is not None:
            d = self.form.get()
            run_action(self, lambda: self.ctx.flights.update_flight(self.ctx.user, fid, now=self.ctx.now(), **d),
                       self._done("Flight updated.", fid))

    def assign_gate(self):
        fid = self.selected()
        if fid is not None:
            run_action(self, lambda: self.ctx.flights.assign_gate(self.ctx.user, fid, self.gate_var.get()),
                       self._done("Gate assigned.", fid))

    def set_status(self):
        fid = self.selected()
        if fid is not None:
            run_action(self, lambda: self.ctx.flights.change_status(self.ctx.user, fid, self.status_var.get()),
                       self._done("Status updated.", fid))

    def cancel(self):
        fid = self.selected()
        if fid is None:
            return
        f = self.ctx.flights.get_flight(fid)
        if messagebox.askyesno("Cancel flight", f"Cancel flight {f.flight_no}? All its bookings will be "
                               "cancelled too.", parent=self):
            run_action(self, lambda: self.ctx.flights.cancel_flight(self.ctx.user, fid),
                       lambda n: (self.refresh(), messagebox.showinfo(
                           "Done", f"Flight {f.flight_no} cancelled; {n} booking(s) cancelled.", parent=self)))

    def clear(self):
        self.form.clear()
        self.gate_var.set("")
        self.table.tree.selection_remove(self.table.tree.selection())
