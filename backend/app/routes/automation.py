from fastapi import APIRouter, HTTPException

from app.services.agent_scheduler import get_scheduler_status
from app.services.scheduled_agent import run_daily_agent

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.get("/status")
def automation_status():
    return get_scheduler_status()


@router.post("/run-now")
async def run_automatic_agent_now():
    try:
        return await run_daily_agent()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Automatic agent failed: {exc}") from exc
