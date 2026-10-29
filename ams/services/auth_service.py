"""Module 4 - Admin and staff login: authentication and account management."""
import sqlite3
from datetime import datetime
from typing import List, Optional

from ..access import require_role
from ..errors import AuthenticationError, BusinessRuleError, NotFoundError, ValidationError
from ..models import Role, User, fmt_dt
from ..security import hash_password, verify_password
from .. import validators as v


class AuthService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ----- authentication -----
    def login(self, username: str, password: str) -> User:
        """Return the User on success. The same message is used for an unknown
        username and a wrong password so that usernames cannot be probed."""
        if not (username or "").strip() or not password:
            raise ValidationError("Enter both username and password.")
        row = self.conn.execute("SELECT * FROM users WHERE username = ?",
                                ((username or "").strip().lower(),)).fetchone()
        if row is None or not verify_password(password, row["password_hash"], row["salt"]):
            raise AuthenticationError("Invalid username or password.")
        return User.from_row(row)

    # ----- account creation -----
    def register_passenger(self, username, password, full_name, email, phone,
                           now: Optional[datetime] = None) -> User:
        """Self-registration; always creates a PASSENGER account."""
        return self._create_user(username, password, Role.PASSENGER, full_name, email, phone, now)

    def create_staff_account(self, actor: User, username, password, full_name, email, phone,
                             role: Role = Role.STAFF, now: Optional[datetime] = None) -> User:
        """Only an ADMIN may create STAFF or ADMIN accounts."""
        require_role(actor, Role.ADMIN)
        role = Role(role)
        if role not in (Role.STAFF, Role.ADMIN):
            raise ValidationError("Staff accounts must have role STAFF or ADMIN.")
        return self._create_user(username, password, role, full_name, email, phone, now)

    def create_initial_admin(self, username, password, full_name, email, phone,
                             now: Optional[datetime] = None) -> User:
        """Bootstrap the first administrator; refused once any admin exists."""
        if self.conn.execute("SELECT 1 FROM users WHERE role = 'ADMIN'").fetchone():
            raise BusinessRuleError("An administrator already exists.")
        return self._create_user(username, password, Role.ADMIN, full_name, email, phone, now)

    def _create_user(self, username, password, role: Role, full_name, email, phone, now) -> User:
        username = v.validate_username(username)
        password = v.validate_password(password)
        full_name = v.validate_full_name(full_name)
        email = v.validate_email(email)
        phone = v.validate_phone(phone)
        if self.conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise BusinessRuleError(f"Username '{username}' is already taken.")
        pw_hash, salt = hash_password(password)
        cur = self.conn.execute(
            "INSERT INTO users (username, password_hash, salt, role, full_name, email, phone, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (username, pw_hash, salt, role.value, full_name, email, phone,
             fmt_dt(now or datetime.now())))
        self.conn.commit()
        return self.get_user(cur.lastrowid)

    # ----- queries -----
    def get_user(self, user_id: int) -> User:
        row = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"User {user_id} not found.")
        return User.from_row(row)

    def list_users(self, actor: User) -> List[User]:
        require_role(actor, Role.ADMIN)
        rows = self.conn.execute("SELECT * FROM users ORDER BY role, username").fetchall()
        return [User.from_row(r) for r in rows]
