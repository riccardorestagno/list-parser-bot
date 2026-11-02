import settings  # noqa: F401  (first: loads server/.env before the modules below read it)

from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import require_signed_in
from api.errors import app_error_response
from api.routes import runs, status
from db.migrations import init_db
from services.errors import AppError
from services.scheduler import scheduler
from settings import ALLOWED_ORIGINS, API_DOCS, APP_VERSION, SCHEDULE_ENABLED


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the tables, then start sweeping on the schedule (when it's turned on)."""
    init_db()
    if SCHEDULE_ENABLED:
        scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(
    title="List Parser Bot API",
    version=APP_VERSION,
    docs_url="/docs" if API_DOCS else None,
    redoc_url="/redoc" if API_DOCS else None,
    openapi_url="/openapi.json" if API_DOCS else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_response)

# Everything but / and /health needs someone signed in on the tools dashboard (services/auth.py)
signed_in = [Depends(require_signed_in)]
app.include_router(runs.router, dependencies=signed_in)
app.include_router(status.router, dependencies=signed_in)


@app.get("/")
async def root():
    return {
        "message": "List Parser Bot API",
        "endpoints": {
            "/runs": "The latest sweeps: what each searched, and what it posted or why it failed",
            "/status": "Where the bot posts, the sites it reads, and when it next sweeps",
            "/health": "Whether the API is up, and the release it runs",
        }
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": APP_VERSION}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
