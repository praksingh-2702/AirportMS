"""Module 3 GUI - Check-in counter: PNR lookup, check-in, boarding pass, baggage tags/status."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..models import BagStatus, BookingStatus, Role, fmt_dt
from .widgets import COLORS, Button, DataTable, animate, mix, run_action, save_file

BAG_COLUMNS = [("tag", "Tag no.", 110), ("weight", "Weight (kg)", 90), ("status", "Status", 110),
               ("updated", "Last updated", 140)]


class CheckInView(ttk.Frame):
    EMPTY_TEXT = "Enter a PNR above and press Find booking (or Enter)."

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
        Button(bar, text="Find booking", command=self.lookup).pack(side="left")
        self.checkin_btn = Button(bar, text="Check in passenger", style="Accent.TButton",
                                      command=self.check_in)
        self.checkin_btn.pack(side="left", padx=8)
        self.download_btn = Button(bar, text="Download boarding pass (PDF)", command=self.download)
        self.download_btn.pack(side="left")
        self.download_btn.configure(state="disabled")
        ttk.Label(bar, text="Check-in window: 48 h to 45 min before departure",
                  style="Muted.TLabel").pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=10)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Booking / boarding pass", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.info = tk.Text(left, height=9, width=52, font="AMSMono", relief="flat", bd=0, wrap="word",
                            bg=COLORS["header"], fg="#E2E8F0", padx=14, pady=12, state="disabled",
                            highlightthickness=0)
        self.info.pack(fill="both", expand=True)
        self._write(self.EMPTY_TEXT)

        right = ttk.LabelFrame(body, text="Baggage", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        add = ttk.Frame(right)
        add.pack(fill="x")
        ttk.Label(add, text="Weight (kg)").pack(side="left")
        self.weight = tk.StringVar()
        ttk.Entry(add, textvariable=self.weight, width=8).pack(side="left", padx=6)
        Button(add, text="Add bag & print tag", command=self.add_bag).pack(side="left")
        self.bags = DataTable(right, BAG_COLUMNS, height=4, empty_text="No bags checked in.")
        self.bags.pack(fill="both", expand=True, pady=8)
        upd = ttk.Frame(right)
        upd.pack(fill="x")
        self.bag_status = tk.StringVar(value=BagStatus.LOADED.value)
        ttk.Combobox(upd, textvariable=self.bag_status, state="readonly", width=12,
                     values=[s.value for s in BagStatus if s != BagStatus.CHECKED_IN]).pack(side="left")
        Button(upd, text="Update bag status", command=self.update_bag).pack(side="left", padx=6)
        self.summary = tk.StringVar()
        ttk.Label(right, textvariable=self.summary, style="Heading.TLabel", font="AMSHeading").pack(anchor="w", pady=(8, 0))

    def _write(self, text, flash=None):
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", text)
        self.info.configure(state="disabled")
        if flash:   # brief colour pulse so the change is noticeable
            animate(self.info, 600, lambda t: self.info.configure(bg=mix(flash, COLORS["header"], t)), key="flash")

    def _clear_booking(self):
        """Forget the current booking so the screen never shows stale data."""
        self.current_pnr = None
        self.download_btn.configure(state="disabled")
        self._write(self.EMPTY_TEXT)
        self.bags.load([])
        self.summary.set("")

    def lookup(self):
        if run_action(self, lambda: self.ctx.checkin.find_booking(self.pnr.get()), self._show) is None:
            self._clear_booking()

    def on_show(self):
        """Re-read the booking when the tab is re-opened (status may have changed elsewhere)."""
        if self.current_pnr:
            try:
                self._show(self.ctx.checkin.find_booking(self.current_pnr), flash=False)
            except Exception:   # noqa: BLE001
                self._clear_booking()

    def _show(self, d, flash=True):
        b = d.booking
        self.current_pnr = b.pnr
        self.download_btn.configure(state="normal" if b.status == BookingStatus.CHECKED_IN else "disabled")
        if b.status == BookingStatus.CHECKED_IN:
            text = self.ctx.checkin.get_boarding_pass(self.ctx.user, b.pnr).as_text()
        else:
            pay = self.ctx.payments.get_payment(b.booking_id)
            if pay is None:
                pay_text = "UNPAID - passenger must pay before check-in"
            elif pay.status.value == "REFUNDED":
                pay_text = f"REFUNDED Rs {pay.refund_amount:,}"
            else:
                pay_text = f"PAID Rs {pay.amount:,} ({pay.invoice_no})"
            text = (f"BOOKING {b.pnr}\nPassenger : {d.passenger_name}\nFlight    : {d.flight_no}   "
                    f"{d.origin} -> {d.destination}\nDeparture : {fmt_dt(d.departure)}\n"
                    f"Gate      : {d.gate or 'TBA'}    Seat: {b.seat}\n"
                    f"Booking   : {b.status.value}\nFlight    : {d.flight_status.value}\nPayment   : {pay_text}")
        self._write(text, flash="#1D4ED8" if flash and b.status != BookingStatus.CHECKED_IN
                    else "#15803D" if flash else None)
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

    def download(self):
        """Save the boarding pass of the booking on screen as a PDF."""
        if not self._need_booking():
            return
        run_action(self, lambda: self.ctx.checkin.boarding_pass_file(self.ctx.user, self.current_pnr),
                   lambda f: save_file(self, f[1], f[0], "Save boarding pass"))

    def _need_booking(self):
        """True when the booking on screen is the PNR typed in the box (re-looks it up if they differ)."""
        typed = self.pnr.get().strip().upper()
        if typed and typed != self.current_pnr:
            self.lookup()
        if not self.current_pnr:
            if not typed:
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
    """Passenger tab: own boarding passes for checked-in bookings, with PDF download."""
    COLUMNS = [("pnr", "PNR", 80), ("flight", "Flight", 80), ("route", "Route", 100),
               ("departure", "Departure", 140), ("gate", "Gate", 60), ("seat", "Seat", 60)]

    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        self.passes = {}
        head = ttk.Frame(self)
        head.pack(fill="x")
        ttk.Label(head, text="My boarding passes", style="Heading.TLabel", font="AMSHeading").pack(side="left")
        self.download_btn = Button(head, text="Download PDF", style="Accent.TButton", command=self.download)
        self.download_btn.pack(side="right")
        Button(head, text="Refresh", command=self.refresh).pack(side="right", padx=8)
        ttk.Label(self, text="Check-in is done at the airport counter by staff. "
                  "Once checked in, your boarding pass appears here and can be downloaded.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
        self.table = DataTable(self, self.COLUMNS, height=3, empty_text="No checked-in bookings yet.")
        self.table.pack(fill="x", pady=8)
        self.table.on_select(self._preview)
        self.text = tk.Text(self, font="AMSMono", relief="flat", bd=0, bg=COLORS["header"], fg="#E2E8F0",
                            padx=16, pady=14, state="disabled", height=7, highlightthickness=0)
        self.text.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        self.passes = {}
        for d in self.ctx.bookings.list_bookings(self.ctx.user):
            if d.booking.status == BookingStatus.CHECKED_IN:
                self.passes[d.booking.pnr] = self.ctx.checkin.get_boarding_pass(self.ctx.user, d.booking.pnr)
        self.table.load([(pnr, (pnr, p.flight_no, f"{p.origin} -> {p.destination}", fmt_dt(p.departure),
                                p.gate or "TBA", p.seat), "ok") for pnr, p in self.passes.items()])
        if self.passes and self.table.selected_id() is None:
            self.table.select(next(iter(self.passes)))
        self._show(self.table.selected_id())

    def _preview(self):
        self._show(self.table.selected_id())

    def _show(self, pnr):
        self.download_btn.configure(state="normal" if pnr in self.passes else "disabled")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.passes[pnr].as_text() if pnr in self.passes else "No checked-in bookings yet.")
        self.text.configure(state="disabled")
        animate(self.text, 500, lambda t: self.text.configure(bg=mix("#15803D", COLORS["header"], t)), key="flash")

    def download(self):
        pnr = self.table.selected_id()
        if pnr is None:
            messagebox.showwarning("No boarding pass", "Select a boarding pass in the list first.", parent=self)
            return
        run_action(self, lambda: self.ctx.checkin.boarding_pass_file(self.ctx.user, pnr),
                   lambda f: save_file(self, f[1], f[0], "Save boarding pass"))

    def on_show(self):
        self.refresh()
