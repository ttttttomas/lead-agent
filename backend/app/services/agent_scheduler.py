import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.services.scheduled_agent import run_daily_agent

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def start_agent_scheduler() -> None:
    global _scheduler

    if not settings.agent_scheduler_enabled:
        logger.info("Automatic lead agent scheduler is disabled")
        return

    if _scheduler and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler(timezone=settings.agent_timezone)
    _scheduler.add_job(
        run_daily_agent,
        trigger=CronTrigger(
            hour=settings.agent_schedule_hour,
            minute=settings.agent_schedule_minute,
            timezone=settings.agent_timezone,
        ),
        id="daily_lead_agent",
        name="Daily iWEB lead generation report",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "Automatic lead agent scheduled daily at %02d:%02d (%s)",
        settings.agent_schedule_hour,
        settings.agent_schedule_minute,
        settings.agent_timezone,
    )


def stop_agent_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def get_scheduler_status() -> dict:
    if not _scheduler or not _scheduler.running:
        return {
            "enabled": settings.agent_scheduler_enabled,
            "running": False,
            "timezone": settings.agent_timezone,
            "hour": settings.agent_schedule_hour,
            "minute": settings.agent_schedule_minute,
            "next_run": None,
        }

    job = _scheduler.get_job("daily_lead_agent")
    return {
        "enabled": settings.agent_scheduler_enabled,
        "running": True,
        "timezone": settings.agent_timezone,
        "hour": settings.agent_schedule_hour,
        "minute": settings.agent_schedule_minute,
        "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }
