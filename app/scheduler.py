"""APScheduler setup for automated pull-list generation."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import async_session
from app.services.pulllist import PullListService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_pulllist_job():
    """Job function that runs on schedule to generate the weekly pull-list."""
    logger.info("Starting scheduled pull-list generation")

    try:
        async with async_session() as db:
            service = PullListService(db)
            result = await service.generate_pulllist(
                run_type="scheduled",
                days_back=7,
                create_readlist=True,
            )

            if result.success:
                logger.info(
                    f"Scheduled pull-list completed: {len(result.items)} items, "
                    f"readlist_id={result.readlist_id}"
                )
            else:
                logger.error(f"Scheduled pull-list failed: {result.error}")

    except Exception as e:
        logger.exception(f"Error in scheduled pull-list job: {e}")


def setup_scheduler():
    """Configure and start the scheduler."""
    settings = get_settings()

    # Create cron trigger from settings
    trigger = CronTrigger(
        day_of_week=settings.schedule_day_of_week,
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        timezone=settings.timezone,
    )

    # Add the job
    scheduler.add_job(
        scheduled_pulllist_job,
        trigger=trigger,
        id="weekly_pulllist",
        name="Weekly Pull-List Generation",
        replace_existing=True,
    )

    logger.info(
        f"Scheduler configured: {settings.schedule_day_of_week} at "
        f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d} "
        f"({settings.timezone})"
    )


def start_scheduler():
    """Start the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_next_run_time() -> str | None:
    """Get the next scheduled run time as a formatted string."""
    job = scheduler.get_job("weekly_pulllist")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return None
