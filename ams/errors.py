"""Exception hierarchy. The GUI catches AMSError and shows its message to the user."""


class AMSError(Exception):
    """Base class for all expected (user-facing) errors."""


class ValidationError(AMSError):
    """Input has the wrong format or is out of range."""


class AuthenticationError(AMSError):
    """Wrong username or password."""


class AuthorizationError(AMSError):
    """The logged-in user's role is not allowed to perform the action."""


class NotFoundError(AMSError):
    """A flight, booking, bag or user that was referenced does not exist."""


class BusinessRuleError(AMSError):
    """Input is well-formed but violates a business rule (seat taken, gate busy, ...)."""
