"""Module 3 GUI - Check-in counter: PNR lookup, check-in, boarding pass, baggage tags/status."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..models import BagStatus, BookingStatus, Role, fmt_dt
from .widgets import COLORS, DataTable, run_action

BAG_COLUMNS = [("tag", "Tag no.", 110), ("weight", "Weight (kg)", 90), ("status", "Status", 110),
               ("updated", "Last updated", 140)]


class CheckInView(ttk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        self.current_pnr = None

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="PNR").pack(side="left")
        self.pnr = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.pnr, width=12)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda _e: self.lookup())
        ttk.Button(bar, text="Find booking", command=self.lookup).pack(side="left")
        self.checkin_btn = ttk.Button(bar, text="Check in passenger", style="Accent.TButton",
                                      command=self.check_in)
        self.checkin_btn.pack(side="left", padx=8)
        ttk.Label(bar, text="Check-in window: 48 h to 45 min before departure",
                  style="Muted.TLabel").pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=10)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Booking / boarding pass", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.info = tk.Text(left, height=12, width=52, font="AMSMono", relief="flat",
                            bg=COLORS["card"], padx=10, pady=10, state="disabled")
        self.info.pack(fill="both", expand=True)

        right = ttk.LabelFrame(body, text="Baggage", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        add = ttk.Frame(right)
        add.pack(fill="x")
        ttk.Label(add, text="Weight (kg)").pack(side="left")
        self.weight = tk.StringVar()
        ttk.Entry(add, textvariable=self.weight, width=8).pack(side="left", padx=6)
        ttk.Button(add, text="Add bag & print tag", command=self.add_bag).pack(side="left")
        self.bags = DataTable(right, BAG_COLUMNS, height=6)
        self.bags.pack(fill="both", expand=True, pady=8)
        upd = ttk.Frame(right)
        upd.pack(fill="x")
        self.bag_status = tk.StringVar(value=BagStatus.LOADED.value)
        ttk.Combobox(upd, textvariable=self.bag_status, state="readonly", width=12,
                     values=[s.value for s in BagStatus if s != BagStatus.CHECKED_IN]).pack(side="left")
        ttk.Button(upd, text="Update bag status", command=self.update_bag).pack(side="left", padx=6)
        self.summary = tk.StringVar()
        ttk.Label(right, textvariable=self.summary, style="Heading.TLabel").pack(anchor="w", pady=(8, 0))

    def _write(self, text):
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", text)
        self.info.configure(state="disabled")

    def lookup(self):
        run_action(self, lambda: self.ctx.checkin.find_booking(self.pnr.get()), self._show)

    def _show(self, d):
        b = d.booking
        self.current_pnr = b.pnr
        if b.status == BookingStatus.CHECKED_IN:
            text = self.ctx.checkin.get_boarding_pass(self.ctx.user, b.pnr).as_text()
        else:
            text = (f"BOOKING {b.pnr}\nPassenger : {d.passenger_name}\nFlight    : {d.flight_no}   "
                    f"{d.origin} -> {d.destination}\nDeparture : {fmt_dt(d.departure)}\n"
                    f"Gate      : {d.gate or 'TBA'}    Seat: {b.seat}\n"
                    f"Booking   : {b.status.value}\nFlight    : {d.flight_status.value}")
        self._write(text)
        self.refresh_bags()

    def refresh_bags(self):
        if not self.current_pnr:
            return
        bags = self.ctx.checkin.list_bags(self.current_pnr)
        self.bags.load([(g.bag_id, (g.tag_no, f"{g.weight_kg:.1f}", g.status.value, fmt_dt(g.updated_at)),
                         "warn" if g.status == BagStatus.MISHANDLED else "") for g in bags])
        total, fee = self.ctx.checkin.baggage_summary(self.current_pnr)
        self.summary.set(f"{len(bags)} bag(s), {total:.1f} kg   Excess fee: Rs {fee}")

    def check_in(self):
        run_action(self, lambda: self.ctx.checkin.check_in(self.ctx.user, self.pnr.get(), now=self.ctx.now()),
                   lambda bp: (self.lookup(), messagebox.showinfo("Checked in", bp.as_text(), parent=self)))

    def _need_booking(self):
        if not self.current_pnr:
            messagebox.showwarning("No booking", "Find a booking by PNR first.", parent=self)
            return False
        return True

    def add_bag(self):
        if self._need_booking():
            run_action(self, lambda: self.ctx.checkin.add_bag(self.ctx.user, self.current_pnr,
                                                             self.weight.get(), now=self.ctx.now()),
                       lambda g: (self.weight.set(""), self.refresh_bags(),
                                  messagebox.showinfo("Bag tag", f"Tag {g.tag_no} printed for "
                                                      f"{g.weight_kg:.1f} kg bag.", parent=self)))

    def update_bag(self):
        iid = self.bags.selected_id()
        if iid is None:
            messagebox.showwarning("No bag selected", "Select a bag in the list first.", parent=self)
            return
        run_action(self, lambda: self.ctx.checkin.update_bag_status(self.ctx.user, int(iid), self.bag_status.get(),
                                                                    now=self.ctx.now()),
                   lambda _g: (self.refresh_bags(), self.bags.select(iid)))


class BoardingPassView(ttk.Frame):
    """Passenger tab: view own boarding passes for checked-in bookings."""

    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        ttk.Label(self, text="My boarding passes", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self, text="Check-in is done at the airport counter by staff. "
                  "Once checked in, your boarding pass appears here.", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(self, text="Refresh", command=self.refresh).pack(anchor="w", pady=6)
        self.text = tk.Text(self, font="AMSMono", relief="flat", bg=COLORS["card"], padx=12, pady=12,
                            state="disabled", height=16)
        self.text.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        passes = [self.ctx.checkin.get_boarding_pass(self.ctx.user, d.booking.pnr)
                  for d in self.ctx.bookings.list_bookings(self.ctx.user)
                  if d.booking.status == BookingStatus.CHECKED_IN]
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n\n".join(p.as_text() for p in passes) or "No checked-in bookings yet.")
        self.text.configure(state="disabled")
