"""The error services raise when a request can't be done, without knowing about HTTP.

``api/errors.py`` turns it into the JSON FastAPI gives an HTTPException, so the
client reads ``detail`` the same way for both.
"""


class AppError(Exception):
    """A problem worth reporting back to the caller, with the HTTP status it maps to."""

    status = 400

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.message = message
        if status is not None:
            self.status = status
