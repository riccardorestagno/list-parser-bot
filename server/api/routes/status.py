from fastapi import APIRouter

from schemas.status import Status
from services.status import bot_status

router = APIRouter(prefix="/status", tags=["status"])


@router.get("", response_model=Status)
async def get_status():
    """Where the bot posts, the sites it reads, and when it next sweeps."""
    return Status(**bot_status())
