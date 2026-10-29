"""Service layer: one class per functional module (high cohesion).

Services depend only on a sqlite3 connection, the models, the validators and
access control - never on the GUI - so they can be unit-tested in isolation.
"""
from .auth_service import AuthService
from .booking_service import BookingService
from .checkin_service import CheckInService, compute_excess_fee
from .flight_service import FlightService

__all__ = ["AuthService", "FlightService", "BookingService", "CheckInService", "compute_excess_fee"]
