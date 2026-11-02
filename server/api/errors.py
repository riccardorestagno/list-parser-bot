from fastapi import Request
from fastapi.responses import JSONResponse

from services.errors import AppError


def app_error_response(_: Request, error: AppError) -> JSONResponse:
    """A service's error, shaped like an HTTPException's so the client handles one form."""
    return JSONResponse(status_code=error.status, content={"detail": error.message})
