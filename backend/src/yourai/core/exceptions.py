"""Custom HTTP exceptions for the YourAI API.

Each exception maps to a specific HTTP status code and error code.
Global exception handlers in api/main.py convert these to ErrorResponse.
"""


class YourAIError(Exception):
    """Base exception for all YourAI errors."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, detail: dict[str, object] | None = None):
        self.message = message or self.__class__.message
        self.detail = detail
        super().__init__(self.message)


class NotFoundError(YourAIError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class UnauthorisedError(YourAIError):
    status_code = 401
    code = "unauthorised"
    message = "Authentication required."


class PermissionDeniedError(YourAIError):
    status_code = 403
    code = "permission_denied"
    message = "You do not have permission to perform this action."


class UserNotActiveError(YourAIError):
    status_code = 423
    code = "user_not_active"
    message = "User account is not active."


class ConflictError(YourAIError):
    status_code = 409
    code = "conflict"
    message = "Resource already exists."


class ValidationError(YourAIError):
    status_code = 422
    code = "unprocessable_entity"
    message = "Request could not be processed."
