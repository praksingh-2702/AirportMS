"""Role-based access control check used by every service operation that changes data."""
from typing import Optional

from .errors import AuthorizationError
from .models import Role, User


def require_role(actor: Optional[User], *roles: Role) -> User:
    """Raise AuthorizationError unless `actor` is logged in with one of `roles`."""
    if actor is None:
        raise AuthorizationError("Please log in first.")
    if actor.role not in roles:
        allowed = ", ".join(r.value for r in roles)
        raise AuthorizationError(f"Access denied: this action requires role {allowed}.")
    return actor
