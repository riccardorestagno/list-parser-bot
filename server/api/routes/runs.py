from fastapi import APIRouter, Query

from schemas.run import RunList
from services import runs

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunList)
async def get_runs(limit: int = Query(20, ge=1, le=100)):
    """The latest sweeps, newest first."""
    return RunList(runs=runs.list_runs(limit))
