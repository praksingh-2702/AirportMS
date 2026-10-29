"""Module 2 GUI - Passenger booking: search, seat map, book, my bookings, cancel."""
import tkinter as tk
from tkinter import messagebox, ttk

from ..config import SEAT_COLUMNS
from ..models import BookingStatus, Role, fmt_dt
from .widgets import COLORS, DataTable, run_action

RESULT_COLUMNS = [("flight_no", "Flight", 80), ("airline", "Airline", 130), ("route", "Route", 90),
                  ("departure", "Departure", 130), ("arrival", "Arrival", 130),
                  ("fare", "Fare (Rs)", 80), ("left", "Seats left", 80), ("status", "Status", 90)]
BOOKING_COLUMNS = [("pnr", "PNR", 75), ("passenger", "Passenger", 130), ("flight", "Flight", 70),
                   ("route", "Route", 90), ("departure", "Departure", 130), ("seat", "Seat", 50),
                   ("fare", "Fare (Rs)", 75), ("status", "Status", 95), ("flight_status", "Flight status", 100)]


class SeatMap(tk.Toplevel):
    """Clickable seat grid; returns the selected seat through `on_pick`."""

    def __init__(self, parent, flight, taken, on_pick):
        super().__init__(parent)
        self.title(f"Select seat - {flight.flight_no}")
        self.configure(bg=COLORS["card"], padx=14, pady=12)
        self.on_pick, self.choice = on_pick, tk.StringVar()
        ttk.Label(self, text=f"{flight.flight_no}  {flight.origin} -> {flight.destination}  "
                  f"{fmt_dt(flight.departure)}", style="Heading.TLabel", background=COLORS["card"]).pack(anchor="w")
        legend = tk.Frame(self, bg=COLORS["card"])
        legend.pack(anchor="w", pady=6)
        for text, color in (("Free", COLORS["seat_free"]), ("Taken", COLORS["seat_taken"]),
                            ("Selected", COLORS["seat_selected"])):
            tk.Label(legend, text="  ", bg=color, relief="solid", bd=1).pack(side="left")
            tk.Label(legend, text=f" {text}   ", bg=COLORS["card"]).pack(side="left")

        outer = tk.Frame(self, bg=COLORS["card"])
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=COLORS["card"], highlightthickness=0, width=330,
                           height=min(420, flight.rows * 30 + 30))
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        grid = tk.Frame(canvas, bg=COLORS["card"])
        grid.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        for c, letter in enumerate(SEAT_COLUMNS):
            col = c + 1 if c < 3 else c + 2
            tk.Label(grid, text=letter, bg=COLORS["card"]).grid(row=0, column=col)
        self.buttons = {}
        for r in range(1, flight.rows + 1):
            tk.Label(grid, text=str(r), width=3, bg=COLORS["card"]).grid(row=r, column=0)
            tk.Label(grid, text="", width=2, bg=COLORS["card"]).grid(row=r, column=4)
            for c, letter in enumerate(SEAT_COLUMNS):
                seat = f"{r}{letter}"
                is_taken = seat in taken
                b = tk.Button(grid, text=seat, width=4, relief="solid", bd=1,
                              bg=COLORS["seat_taken"] if is_taken else COLORS["seat_free"],
                              state="disabled" if is_taken else "normal",
                              command=lambda s=seat: self.pick(s))
                b.grid(row=r, column=c + 1 if c < 3 else c + 2, padx=2, pady=2)
                self.buttons[seat] = b

        row = tk.Frame(self, bg=COLORS["card"])
        row.pack(fill="x", pady=(10, 0))
        tk.Label(row, textvariable=self.choice, bg=COLORS["card"]).pack(side="left")
        ttk.Button(row, text="Confirm seat", style="Accent.TButton", command=self.confirm).pack(side="right")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

    def pick(self, seat):
        old = self.choice.get().replace("Selected: ", "")
        if old in self.buttons:
            self.buttons[old].configure(bg=COLORS["seat_free"])
        self.buttons[seat].configure(bg=COLORS["seat_selected"])
        self.choice.set(f"Selected: {seat}")

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

        if self.is_passenger:
            search = ttk.LabelFrame(self, text="Search flights", padding=10)
            search.pack(fill="x")
            airports = [""] + self.ctx.flights.list_airports()
            self.origin, self.dest, self.date = tk.StringVar(), tk.StringVar(), tk.StringVar()
            for label, var in (("From", self.origin), ("To", self.dest)):
                ttk.Label(search, text=label).pack(side="left", padx=(0, 4))
                ttk.Combobox(search, textvariable=var, values=airports, width=6).pack(side="left", padx=(0, 12))
            ttk.Label(search, text="Date (YYYY-MM-DD, optional)").pack(side="left", padx=(0, 4))
            ttk.Entry(search, textvariable=self.date, width=12).pack(side="left")
            ttk.Button(search, text="Search", style="Accent.TButton", command=self.search).pack(side="left", padx=10)
            ttk.Button(search, text="Book selected flight…", command=self.book).pack(side="right")
            self.results = DataTable(self, RESULT_COLUMNS, height=7)
            self.results.pack(fill="both", expand=True, pady=8)

        title = "My bookings" if self.is_passenger else "All bookings"
        head = ttk.Frame(self)
        head.pack(fill="x", pady=(6, 0))
        ttk.Label(head, text=title, style="Heading.TLabel").pack(side="left")
        if ctx.user.role in (Role.PASSENGER, Role.ADMIN):
            ttk.Button(head, text="Cancel selected booking", style="Danger.TButton",
                       command=self.cancel).pack(side="right")
        ttk.Button(head, text="Refresh", command=self.refresh_bookings).pack(side="right", padx=6)
        self.bookings = DataTable(self, BOOKING_COLUMNS, height=8)
        self.bookings.pack(fill="both", expand=True, pady=8)
        if self.is_passenger:
            self.search()
        self.refresh_bookings()

    def search(self):
        def show(results):
            self.results.load([(f.flight_id, (f.flight_no, f.airline, f"{f.origin} -> {f.destination}",
                                              fmt_dt(f.departure), fmt_dt(f.arrival), f.fare, left,
                                              f.status.value), "warn" if f.status.value == "DELAYED" else "")
                               for f, left in results])
        run_action(self, lambda: self.ctx.bookings.search_flights(
            self.origin.get(), self.dest.get(), self.date.get(), now=self.ctx.now()), show)

    def refresh_bookings(self):
        rows = []
        for d in self.ctx.bookings.list_bookings(self.ctx.user):
            b = d.booking
            tag = {"CANCELLED": "cancelled", "CHECKED_IN": "ok"}.get(b.status.value, "")
            rows.append((b.booking_id, (b.pnr, d.passenger_name, d.flight_no, f"{d.origin} -> {d.destination}",
                                        fmt_dt(d.departure), b.seat, b.fare, b.status.value,
                                        d.flight_status.value), tag))
        self.bookings.load(rows)

    def book(self):
        iid = self.results.selected_id()
        if iid is None:
            messagebox.showwarning("No flight selected", "Search and select a flight first.", parent=self)
            return
        flight = self.ctx.flights.get_flight(int(iid))
        taken = self.ctx.bookings.get_taken_seats(flight.flight_id)
        SeatMap(self, flight, taken, lambda seat: self._confirm_booking(flight, seat))

    def _confirm_booking(self, flight, seat):
        if not messagebox.askyesno("Confirm booking", f"Book seat {seat} on {flight.flight_no} "
                                   f"({flight.origin} -> {flight.destination}) for Rs {flight.fare}?", parent=self):
            return
        run_action(self, lambda: self.ctx.bookings.book_ticket(self.ctx.user, flight.flight_id, seat,
                                                               now=self.ctx.now()),
                   lambda b: (self.search(), self.refresh_bookings(), self.bookings.select(b.booking_id),
                              messagebox.showinfo("Booked", f"Booking confirmed.\nPNR: {b.pnr}\nSeat: {b.seat}",
                                                  parent=self)))

    def cancel(self):
        iid = self.bookings.selected_id()
        if iid is None:
            messagebox.showwarning("No booking selected", "Select a booking first.", parent=self)
            return
        b = self.ctx.bookings.get_booking(int(iid))
        if b.status == BookingStatus.CANCELLED:
            messagebox.showinfo("Already cancelled", f"Booking {b.pnr} is already cancelled.", parent=self)
            return
        if messagebox.askyesno("Cancel booking", f"Cancel booking {b.pnr} (seat {b.seat})?", parent=self):
            run_action(self, lambda: self.ctx.bookings.cancel_booking(self.ctx.user, b.booking_id,
                                                                      now=self.ctx.now()),
                       lambda _r: (self.refresh_bookings(), self.search() if self.is_passenger else None,
                                   messagebox.showinfo("Cancelled", f"Booking {b.pnr} cancelled.", parent=self)))
