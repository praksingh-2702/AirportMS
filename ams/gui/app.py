"""Application window: holds the service context and switches between login and dashboard.

The tabs shown on the dashboard depend on the logged-in user's role:
    ADMIN     - Flights (edit), Bookings (all), Check-in & Baggage, Users
    STAFF     - Flights (view), Bookings (all, view), Check-in & Baggage
    PASSENGER - Book Flights, Boarding Pass, Flights (view)
"""
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ..models import Role
from ..services import AuthService, BookingService, CheckInService, FlightService
from .booking_view import BookingView
from .checkin_view import BoardingPassView, CheckInView
from .flight_view import FlightView
from .login_view import LoginView
from .users_view import UsersView
from .widgets import apply_style

ROLE_TABS = {
    Role.ADMIN: [("Flights", FlightView), ("Bookings", BookingView),
                 ("Check-in & Baggage", CheckInView), ("Users", UsersView)],
    Role.STAFF: [("Check-in & Baggage", CheckInView), ("Flights", FlightView), ("Bookings", BookingView)],
    Role.PASSENGER: [("Book Flights", BookingView), ("Boarding Pass", BoardingPassView),
                     ("Flight Schedule", FlightView)],
}


class AppContext:
    """Shared objects passed to every view (the only coupling between views and services)."""

    def __init__(self, conn):
        self.conn = conn
        self.auth = AuthService(conn)
        self.flights = FlightService(conn)
        self.bookings = BookingService(conn)
        self.checkin = CheckInService(conn)
        self.user = None

    @staticmethod
    def now() -> datetime:
        return datetime.now().replace(second=0, microsecond=0)


class AirportApp(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.title("Airport Management System")
        self.geometry("1100x700")
        self.minsize(980, 620)
        apply_style(self)
        self.ctx = AppContext(conn)
        self.current = None
        self.show_login()

    def _swap(self, frame):
        if self.current is not None:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)

    def show_login(self):
        self.ctx.user = None
        self._swap(LoginView(self, self.ctx, self.show_dashboard))

    def show_dashboard(self, user):
        self.ctx.user = user
        frame = ttk.Frame(self)
        header = ttk.Frame(frame, style="Header.TFrame", padding=(16, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Airport Management System", style="Header.TLabel",
                  font="AMSHeading").pack(side="left")
        ttk.Button(header, text="Logout", command=self.show_login).pack(side="right")
        ttk.Label(header, text=f"{user.full_name}  ·  {user.role.value}", style="Header.TLabel").pack(
            side="right", padx=12)
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.tabs = {}
        for title, view_cls in ROLE_TABS[user.role]:
            view = view_cls(self.notebook, self.ctx)
            self.notebook.add(view, text=title)
            self.tabs[title] = view
        self._swap(frame)
