"""Module 2 GUI - Passenger booking: search, seat map, book, my bookings, cancel."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..config import LIST_LIMIT, SEAT_COLUMNS
from ..errors import AMSError
from ..models import BookingStatus, Role, fmt_dt
from ..network import AIRPORTS
from .payment_dialog import PaymentDialog, rs
from .widgets import (COLORS, Button, DataTable, DateEntry, animate, center_on, fade_in, mix, run_action,
                      save_file)

RESULT_COLUMNS = [("flight_no", "Flight", 80), ("airline", "Airline", 130), ("route", "Route", 90),
                  ("departure", "Departure", 130), ("arrival", "Arrival", 130),
                  ("fare", "Fare (Rs)", 80), ("left", "Seats left", 80), ("status", "Status", 90),
                  ("mine", "Your booking", 100)]
BOOKING_COLUMNS = [("pnr", "PNR", 75), ("passenger", "Passenger", 130), ("flight", "Flight", 70),
                   ("route", "Route", 90), ("departure", "Departure", 130), ("seat", "Seat", 50),
                   ("fare", "Fare (Rs)", 75), ("status", "Status", 95), ("payment", "Payment", 130),
                   ("flight_status", "Flight status", 100)]


class SeatMap(tk.Toplevel):
    """Clickable seat grid; returns the selected seat through `on_pick`."""

    def __init__(self, parent, flight, taken, on_pick):
        super().__init__(parent)
        self.title(f"Select seat - {flight.flight_no}")
        self.configure(bg=COLORS["card"], padx=16, pady=14)
        self.on_pick, self.choice = on_pick, tk.StringVar()
        tk.Label(self, text=f"{flight.flight_no}   {flight.origin} -> {flight.destination}   "
                 f"{fmt_dt(flight.departure)}", font="AMSHeading", bg=COLORS["card"]).pack(anchor="w")
        legend = tk.Frame(self, bg=COLORS["card"])
        legend.pack(anchor="w", pady=6)
        for text, color in (("Free", COLORS["seat_free"]), ("Taken", COLORS["seat_taken"]),
                            ("Selected", COLORS["seat_selected"])):
            tk.Label(legend, text="  ", bg=color, relief="solid", bd=1).pack(side="left")
            tk.Label(legend, text=f" {text}   ", bg=COLORS["card"], fg=COLORS["muted"]).pack(side="left")

        outer = tk.Frame(self, bg=COLORS["card"])
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=COLORS["card"], highlightthickness=0, width=340,
                           height=min(420, flight.rows * 32 + 30))
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        grid = tk.Frame(canvas, bg=COLORS["card"])
        grid.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        for c, letter in enumerate(SEAT_COLUMNS):
            col = c + 1 if c < 3 else c + 2
            tk.Label(grid, text=letter, bg=COLORS["card"], fg=COLORS["muted"], font="AMSBold").grid(row=0, column=col)
        self.buttons, self.taken, self._row_widgets = {}, set(taken), {}
        for r in range(1, flight.rows + 1):
            widgets = [tk.Label(grid, text=str(r), width=3, bg=COLORS["card"], fg=COLORS["muted"])]
            widgets[0].grid(row=r, column=0)
            gap = tk.Label(grid, text="", width=2, bg=COLORS["card"])
            gap.grid(row=r, column=4)
            for c, letter in enumerate(SEAT_COLUMNS):
                seat = f"{r}{letter}"
                is_taken = seat in self.taken
                b = tk.Button(grid, text=seat, width=4, relief="flat", bd=0, cursor="arrow" if is_taken else "hand2",
                              bg=COLORS["seat_taken"] if is_taken else COLORS["seat_free"],
                              highlightthickness=1, highlightbackground=COLORS["border"],
                              activebackground=COLORS["seat_hover"], state="disabled" if is_taken else "normal",
                              command=lambda s=seat: self.pick(s))
                b.grid(row=r, column=c + 1 if c < 3 else c + 2, padx=2, pady=2)
                if not is_taken:
                    b.bind("<Enter>", lambda _e, s=seat: self._hover(s, True))
                    b.bind("<Leave>", lambda _e, s=seat: self._hover(s, False))
                self.buttons[seat] = b
                widgets.append(b)
            widgets.append(gap)
            self._row_widgets[r] = widgets

        row = tk.Frame(self, bg=COLORS["card"])
        row.pack(fill="x", pady=(12, 0))
        tk.Label(row, textvariable=self.choice, bg=COLORS["card"], font="AMSBold").pack(side="left")
        Button(row, text="Confirm seat", style="Accent.TButton", command=self.confirm).pack(side="right")
        Button(row, text="Cancel", command=self.destroy).pack(side="right", padx=8)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.transient(parent.winfo_toplevel())
        center_on(self, parent)
        self.grab_set()
        fade_in(self, 220)
        self._reveal(flight.rows)

    def _reveal(self, rows):
        """Rows appear one after another from the front of the cabin."""
        for r in range(1, rows + 1):
            for w in self._row_widgets[r]:
                w.grid_remove()
        for r in range(1, rows + 1):
            self.after(min(r, 40) * 16, lambda rr=r: [w.grid() for w in self._row_widgets[rr]])

    def _hover(self, seat, inside):
        if self.choice.get() != f"Selected: {seat}":
            self.buttons[seat].configure(bg=COLORS["seat_hover"] if inside else COLORS["seat_free"])

    def pick(self, seat):
        old = self.choice.get().replace("Selected: ", "")
        if old in self.buttons:
            self.buttons[old].configure(bg=COLORS["seat_free"])
        self.choice.set(f"Selected: {seat}")
        button = self.buttons[seat]
        animate(button, 280, lambda t: button.configure(bg=mix("#BFE3C2", COLORS["seat_selected"], t)),
                key="pick")

    def confirm(self):
        seat = self.choice.get().replace("Selected: ", "")
        if not seat:
            messagebox.showwarning("No seat", "Click a free seat first.", parent=self)
            return
        self.destroy()
        self.on_pick(seat)


class BookingView(ttk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        self.is_passenger = ctx.user.role == Role.PASSENGER

        title = "My bookings" if self.is_passenger else "All bookings"
        if self.is_passenger:
            search = ttk.LabelFrame(self, text="Search flights", padding=6)
            search.pack(fill="x")
            airports = [""] + [f"{c} - {AIRPORTS[c]}" if c in AIRPORTS else c
                               for c in self.ctx.flights.list_airports()]
            self.origin, self.dest, self.date = tk.StringVar(), tk.StringVar(), tk.StringVar()
            for label, var in (("From", self.origin), ("To", self.dest)):
                ttk.Label(search, text=label).pack(side="left", padx=(0, 4))
                ttk.Combobox(search, textvariable=var, values=airports, width=20).pack(side="left", padx=(0, 12))
            ttk.Label(search, text="Date").pack(side="left", padx=(0, 4))
            DateEntry(search, textvariable=self.date, width=11).pack(side="left")
            Button(search, text="Search", style="Accent.TButton", command=self.search).pack(side="left", padx=10)
            Button(search, text="Book selected flight…", command=self.book).pack(side="right")
            self.hint = tk.StringVar()
            ttk.Label(self, textvariable=self.hint, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
            self.results = DataTable(self, RESULT_COLUMNS, height=4,
                                     empty_text="No flights match your search. Try other airports or clear the date.")
            self.results.pack(fill="both", expand=True, pady=(2, 8))

        head = ttk.Frame(self)
        head.pack(fill="x", pady=(6, 0))
        ttk.Label(head, text=title, style="Heading.TLabel", font="AMSHeading").pack(side="left")
        if ctx.user.role in (Role.PASSENGER, Role.ADMIN):
            Button(head, text="Cancel selected booking", style="Danger.TButton",
                   command=self.cancel).pack(side="right")
        Button(head, text="Refresh", command=self.refresh_bookings).pack(side="right", padx=6)
        Button(head, text="Download receipt", command=self.download_receipt).pack(side="right")
        if self.is_passenger:
            Button(head, text="Pay now", style="Accent.TButton", command=self.pay_selected).pack(side="right", padx=6)
        self.bookings = DataTable(self, BOOKING_COLUMNS, height=3,
                                  empty_text="You have no bookings yet." if self.is_passenger else "No bookings found.")
        self.bookings.pack(fill="both", expand=True, pady=8)
        if self.is_passenger:
            self.search()
        self.refresh_bookings()

    # ----- data -----
    def _held(self):
        """flight_no -> PNR for the passenger's active bookings."""
        return {d.flight_no: d.booking.pnr for d in self.ctx.bookings.list_bookings(self.ctx.user)
                if d.booking.status != BookingStatus.CANCELLED}

    def search(self, quiet: bool = False):
        def show(results):
            held = self._held()
            self.results.load([(f.flight_id, (f.flight_no, f.airline, f"{f.origin} -> {f.destination}",
                                              fmt_dt(f.departure), fmt_dt(f.arrival), f.fare, left,
                                              f.status.value, held.get(f.flight_no, "—")),
                                "ok" if f.flight_no in held else ("warn" if f.status.value == "DELAYED" else ""))
                               for f, left in results])
            self.hint.set(f"{len(results):,} flight(s) found" + (
                f" (showing the first {LIST_LIMIT}; choose From, To or a date to narrow down)"
                if len(results) >= LIST_LIMIT else ""))

        def query():
            return self.ctx.bookings.search_flights(self._code(self.origin.get()), self._code(self.dest.get()),
                                                    self.date.get(), now=self.ctx.now())
        if quiet:
            try:
                show(query())
            except AMSError:
                pass     # half-typed filters are not worth a pop-up when the tab is merely re-opened
        else:
            run_action(self, query, show)

    @staticmethod
    def _code(value: str) -> str:
        """'DEL - Delhi' -> 'DEL' (typed codes such as 'del' pass through)."""
        parts = value.split()
        return parts[0] if parts else ""

    def refresh_bookings(self):
        rows = []
        details = self.ctx.bookings.list_bookings(self.ctx.user)
        payments = self.ctx.payments.payments_for(d.booking.booking_id for d in details)
        for d in details:
            b = d.booking
            tag = {"CANCELLED": "cancelled", "CHECKED_IN": "ok"}.get(b.status.value, "")
            pay = payments.get(b.booking_id)
            if pay is None:
                label = "-" if b.status == BookingStatus.CANCELLED else "UNPAID"
                tag = tag or "warn"
            elif pay.status.value == "REFUNDED":
                label = f"Refunded {rs(pay.refund_amount)}"
            else:
                label = f"Paid {rs(pay.amount)}"
            rows.append((b.booking_id, (b.pnr, d.passenger_name, d.flight_no, f"{d.origin} -> {d.destination}",
                                        fmt_dt(d.departure), b.seat, b.fare, b.status.value, label,
                                        d.flight_status.value), tag))
        self.bookings.load(rows)

    def on_show(self):
        if self.is_passenger:
            self.search(quiet=True)
        self.refresh_bookings()

    # ----- actions -----
    def book(self):
        iid = self.results.selected_id()
        if iid is None:
            messagebox.showwarning("No flight selected", "Search and select a flight first.", parent=self)
            return
        flight = self.ctx.flights.get_flight(int(iid))
        held = self._held()
        if flight.flight_no in held:
            messagebox.showwarning("Already booked", f"You already hold booking {held[flight.flight_no]} on "
                                   f"{flight.flight_no}. Cancel it first if you want a different seat.", parent=self)
            return
        taken = self.ctx.bookings.get_taken_seats(flight.flight_id)
        SeatMap(self, flight, taken, lambda seat: self._confirm_booking(flight, seat))

    def _confirm_booking(self, flight, seat):
        """Seat chosen: open the payment window. The booking is created only if the payment goes through."""
        PaymentDialog(
            self, self.ctx, (f"{flight.flight_no}   {flight.origin} -> {flight.destination}",
                             f"{flight.departure:%a %d %b %Y, %H:%M}   |   Seat {seat}"),
            self.ctx.payments.quote(flight.fare),
            submit=lambda method, details: self.ctx.payments.book_and_pay(
                self.ctx.user, flight.flight_id, seat, method, details, now=self.ctx.now()),
            on_done=lambda result: (self.search(), self.refresh_bookings(), self.bookings.select(result[0].booking_id)))

    def pay_selected(self):
        iid = self.bookings.selected_id()
        if iid is None:
            messagebox.showwarning("No booking selected", "Select an unpaid booking first.", parent=self)
            return
        booking = self.ctx.bookings.get_booking(int(iid))
        if booking.status == BookingStatus.CANCELLED:
            messagebox.showinfo("Cancelled", f"Booking {booking.pnr} is cancelled.", parent=self)
            return
        if self.ctx.payments.get_payment(booking.booking_id):
            messagebox.showinfo("Already paid", f"Booking {booking.pnr} is already paid. "
                                "Use 'Download receipt' to get the invoice.", parent=self)
            return
        d = next(x for x in self.ctx.bookings.list_bookings(self.ctx.user) if x.booking.booking_id == booking.booking_id)
        PaymentDialog(
            self, self.ctx, (f"{d.flight_no}   {d.origin} -> {d.destination}",
                             f"{d.departure:%a %d %b %Y, %H:%M}   |   Seat {booking.seat}   |   PNR {booking.pnr}"),
            self.ctx.payments.quote(booking.fare),
            submit=lambda method, details: (booking, self.ctx.payments.pay_booking(
                self.ctx.user, booking.booking_id, method, details, now=self.ctx.now())),
            on_done=lambda result: (self.refresh_bookings(), self.bookings.select(booking.booking_id)))

    def download_receipt(self):
        iid = self.bookings.selected_id()
        if iid is None:
            messagebox.showwarning("No booking selected", "Select a paid booking first.", parent=self)
            return
        run_action(self, lambda: self.ctx.payments.receipt_file(self.ctx.user, int(iid)),
                   lambda f: save_file(self, f[1], f[0], "Save receipt"))

    def cancel(self):
        iid = self.bookings.selected_id()
        if iid is None:
            messagebox.showwarning("No booking selected", "Select a booking first.", parent=self)
            return
        b = self.ctx.bookings.get_booking(int(iid))
        if b.status == BookingStatus.CANCELLED:
            messagebox.showinfo("Already cancelled", f"Booking {b.pnr} is already cancelled.", parent=self)
            return
        quote = self.ctx.payments.refund_quote(b.booking_id, now=self.ctx.now())
        paid = self.ctx.payments.get_payment(b.booking_id)
        if paid is None:
            money = "This booking is unpaid, so nothing will be refunded."
        else:
            money = (f"Refund: {rs(quote.refund)} of {rs(paid.amount)} paid.\n"
                     f"Kept: cancellation charge {rs(quote.charge)} ({quote.percent}% of the base fare) "
                     f"+ convenience fee {rs(quote.convenience_fee)}.")
        if messagebox.askyesno("Cancel booking", f"Cancel booking {b.pnr} (seat {b.seat})?\n\n{money}", parent=self):
            def done(_r):
                self.refresh_bookings()
                if self.is_passenger:
                    self.search()
                after = self.ctx.payments.get_payment(b.booking_id)
                text = f"Booking {b.pnr} cancelled."
                if after is not None and after.status.value == "REFUNDED":
                    text += f"\n{rs(after.refund_amount)} refunded to {after.instrument} (demo)."
                messagebox.showinfo("Cancelled", text, parent=self)
            run_action(self, lambda: self.ctx.bookings.cancel_booking(self.ctx.user, b.booking_id,
                                                                      now=self.ctx.now()), done)
