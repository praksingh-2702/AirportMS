"""Application window: holds the service context and switches between login and dashboard.

The tabs shown on the dashboard depend on the logged-in user's role:
    ADMIN     - Flights (edit), Bookings (all), Check-in & Baggage, Users
    STAFF     - Check-in & Baggage, Flights (view), Bookings (all, view)
    PASSENGER - Book Flights, Boarding Pass, Flight Schedule (view)
"""
import math
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import ttk

from ..models import Role
from ..services import (AuthService, BookingService, CheckInService, FlightService, PaymentService,
                        ScheduleService)
from .booking_view import BookingView
from .checkin_view import BoardingPassView, CheckInView
from .flight_view import FlightView
from .login_view import LoginView
from .schedule_view import ScheduleView
from .users_view import UsersView
from .widgets import COLORS, Button, StatCard, TabHost, animate, apply_style, draw_plane, fade_in

ROLE_TABS = {
    Role.ADMIN: [("Flights", FlightView), ("Schedule", ScheduleView), ("Bookings", BookingView),
                 ("Check-in & Baggage", CheckInView), ("Users", UsersView)],
    Role.STAFF: [("Check-in & Baggage", CheckInView), ("Flights", FlightView), ("Bookings", BookingView)],
    Role.PASSENGER: [("Book Flights", BookingView), ("Boarding Pass", BoardingPassView),
                     ("Flight Schedule", FlightView)],
}

STAT_ACCENTS = ["#2563EB", "#0EA5A4", "#F59E0B", "#8B5CF6"]


class AppContext:
    """Shared objects passed to every view (the only coupling between views and services)."""

    def __init__(self, conn):
        self.conn = conn
        self.auth = AuthService(conn)
        self.flights = FlightService(conn)
        self.bookings = BookingService(conn)
        self.checkin = CheckInService(conn)
        self.schedule = ScheduleService(conn)
        self.payments = PaymentService(conn)
        self.user = None

    @staticmethod
    def now() -> datetime:
        return datetime.now().replace(second=0, microsecond=0)

    def stats(self):
        """(label, value) pairs for the dashboard tiles of the logged-in user."""
        q = lambda sql, *p: self.conn.execute(sql, p).fetchone()[0]   # noqa: E731
        if self.user.role == Role.PASSENGER:
            uid = self.user.user_id
            return [("My active bookings", q("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status<>'CANCELLED'", uid)),
                    ("Checked in", q("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status='CHECKED_IN'", uid)),
                    ("Flights open for booking", q("SELECT COUNT(*) FROM flights WHERE status IN ('SCHEDULED','DELAYED') AND departure > ?",
                                           self.now().strftime("%Y-%m-%d %H:%M")))]
        return [("Upcoming flights", q("SELECT COUNT(*) FROM flights WHERE status IN ('SCHEDULED','DELAYED','BOARDING')")),
                ("Active bookings", q("SELECT COUNT(*) FROM bookings WHERE status<>'CANCELLED'")),
                ("Passengers checked in", q("SELECT COUNT(*) FROM bookings WHERE status='CHECKED_IN'")),
                ("Revenue (Rs)", self.payments.revenue()) if self.user.role == Role.ADMIN
                else ("Bags handled", q("SELECT COUNT(*) FROM baggage"))]


class Header(tk.Canvas):
    """Navy title bar: logo, drifting plane, live clock, user chip and logout button."""

    def __init__(self, parent, user, on_logout):
        super().__init__(parent, height=64, bg=COLORS["header"], highlightthickness=0)
        self.user = user
        self._t = 0.0
        self._plane_x, self._plane_y = -80.0, 32.0
        # background plane + contrail
        for k in range(7):
            self.create_line(-110 - k * 30, 32, -90 - k * 30, 32, fill="#16345E", width=2, tags="fly")
        draw_plane(self, -80, 32, 0.8, "#2A4C80", "fly")
        # logo + title
        self.create_oval(14, 12, 54, 52, fill=COLORS["accent"], outline="")
        draw_plane(self, 34, 32, 0.55, "white", "logo")
        self.create_text(68, 24, text="Airport Management System", anchor="w", fill="white", font="AMSHeading")
        self.create_text(68, 43, text="Operations console", anchor="w", fill="#8FB0DE", font="AMSSmall")
        # right-hand side
        initials = "".join(p[0] for p in user.full_name.split()[:2]).upper()
        self.avatar = self.create_oval(0, 0, 0, 0, fill="#1D4ED8", outline="#60A5FA", width=2)
        self.avatar_text = self.create_text(0, 0, text=initials, fill="white", font="AMSBold")
        self.name = self.create_text(0, 23, text=user.full_name, anchor="e", fill="white", font="AMSBold")
        self.role = self.create_text(0, 43, text=user.role.value.title(), anchor="e", fill="#8FB0DE",
                                     font="AMSSmall")
        self.clock = self.create_text(0, 23, anchor="e", fill="white", font="AMSBold")
        self.date = self.create_text(0, 43, anchor="e", fill="#8FB0DE", font="AMSSmall")
        self.logout = Button(self, text="Logout", command=on_logout)
        self.logout_win = self.create_window(0, 32, window=self.logout, anchor="e")
        self.bind("<Configure>", lambda _e: self._layout())
        self._tick_clock()
        self._fly()

    def _layout(self):
        w = self.winfo_width()
        self.coords(self.logout_win, w - 16, 32)
        right = w - 16 - self.logout.winfo_reqwidth() - 20
        self.coords(self.avatar, right - 32, 16, right, 48)
        self.coords(self.avatar_text, right - 16, 32)
        text_x = right - 42
        self.coords(self.name, text_x, 23)
        self.coords(self.role, text_x, 43)
        f = tkfont.nametofont("AMSBold")
        clock_x = text_x - max(f.measure(self.user.full_name), 60) - 34
        self.coords(self.clock, clock_x, 23)
        self.coords(self.date, clock_x, 43)
        self.tag_raise("logo")

    def _tick_clock(self):
        try:
            if not self.winfo_exists():
                return
            now = datetime.now()
            self.itemconfigure(self.clock, text=now.strftime("%H:%M:%S"))
            self.itemconfigure(self.date, text=now.strftime("%a, %d %b %Y"))
            self.after(1000, self._tick_clock)
        except tk.TclError:
            pass

    def _fly(self):
        try:
            if not self.winfo_exists():
                return
            w = max(self.winfo_width(), 800)
            self._t += 0.035
            y = 32 + math.sin(self._t) * 9
            dx = 1.7
            self.move("fly", dx, y - self._plane_y)
            self._plane_x += dx
            self._plane_y = y
            if self._plane_x > w + 260:
                self.move("fly", -(w + 420), 0)
                self._plane_x -= w + 420
            self.after(33, self._fly)
        except tk.TclError:
            pass


class AirportApp(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.title("Airport Management System")
        self.geometry("1240x780")
        self.minsize(1100, 700)
        apply_style(self)
        self.ctx = AppContext(conn)
        self.current = None
        self.show_login()

    def _swap(self, frame):
        if self.current is not None:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)
        fade_in(self, 300)

    def show_login(self):
        self.ctx.user = None
        self._swap(LoginView(self, self.ctx, self.show_dashboard))

    def show_dashboard(self, user):
        self.ctx.user = user
        frame = ttk.Frame(self)
        Header(frame, user, self.show_login).pack(fill="x")

        tiles = ttk.Frame(frame)
        tiles.pack(fill="x", padx=12, pady=(10, 0))
        self.cards = []
        for i, (label, _value) in enumerate(self.ctx.stats()):
            card = StatCard(tiles, label, STAT_ACCENTS[i % len(STAT_ACCENTS)])
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            tiles.columnconfigure(i, weight=1, uniform="stat")
            self.cards.append(card)

        self.notebook = TabHost(frame, on_change=self._on_tab)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(6, 10))
        self.tabs = {}
        for title, view_cls in ROLE_TABS[user.role]:
            view = view_cls(self.notebook.body, self.ctx)
            self.notebook.add(view, text=title)
            self.tabs[title] = view
        self._swap(frame)
        self.refresh_stats()
        self._stats_loop(frame)

    def _on_tab(self, view):
        on_show = getattr(view, "on_show", None)
        if on_show:
            on_show()
        self.refresh_stats()

    def refresh_stats(self):
        if self.ctx.user is None:
            return
        for card, (_label, value) in zip(self.cards, self.ctx.stats()):
            card.set(value)

    def _stats_loop(self, frame):
        try:
            if frame.winfo_exists() and self.current is frame:
                self.refresh_stats()
                self.after(2000, lambda: self._stats_loop(frame))
        except tk.TclError:
            pass
