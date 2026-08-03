class UserNotFound(Exception):
    """Raised when a user is not found in the database."""


class UserAlreadyExists(Exception):
    """Raised when trying to create a user that already exists in the database."""


class PlanNotFound(Exception):
    """Raised when a plan is not found in the database."""
