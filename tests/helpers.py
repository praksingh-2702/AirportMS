"""Shared fixtures: a fresh in-memory database seeded at a FIXED clock time,
so every test is repeatable regardless of when it is run."""
import unittest
from datetime import datetime

from ams.database import create_database
from ams.services import AuthService, BookingService, CheckInService, FlightService

NOW = datetime(2026, 11, 10, 9, 0)          # fixed "current time" for all tests


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = create_database(":memory:", now=NOW)
        self.auth = AuthService(self.conn)
        self.flights = FlightService(self.conn)
        self.bookings = BookingService(self.conn)
        self.checkin = CheckInService(self.conn)
        self.admin = self.auth.login("admin", "admin123")
        self.staff = self.auth.login("staff1", "staff123")
        self.priya = self.auth.login("priya", "pass1234")
        self.rahul = self.auth.login("rahul", "pass1234")

    def tearDown(self):
        self.conn.close()

    def flight(self, flight_no):
        return next(f for f in self.flights.list_flights() if f.flight_no == flight_no)
