"""APScheduler setup for automated pull-list generation."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session
from app.models import NotificationLog
from app.services.email import send_pulllist_notification_email
from app.services.pulllist import PullListService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def was_notification_sent_for_week(db: AsyncSession, week_id: str) -> bool:
    """Check if a notification was already sent for the given week."""
    result = await db.execute(
        select(NotificationLog).where(NotificationLog.week_id == week_id)
    )
    return result.scalar_one_or_none() is not None


async def record_notification_sent(db: AsyncSession, week_id: str, items_count: int) -> None:
    """Record that a notification was sent for the given week."""
    log_entry = NotificationLog(week_id=week_id, items_count=items_count)
    db.add(log_entry)
    await db.commit()


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

                # Send notification email if items were found and we haven't notified yet
                if len(result.items) > 0:
                    already_notified = await was_notification_sent_for_week(db, result.week_id)
                    if not already_notified:
                        items_data = [
                            {"series_name": item.series_name, "book_number": item.book_number}
                            for item in result.items
                        ]
                        email_sent = await send_pulllist_notification_email(
                            week_id=result.week_id,
                            items_count=len(result.items),
                            items=items_data,
                        )
                        if email_sent:
                            await record_notification_sent(db, result.week_id, len(result.items))
                            logger.info(f"Notification sent for week {result.week_id}")
                    else:
                        logger.debug(f"Notification already sent for week {result.week_id}, skipping")
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
        id="pulllist_job",
        name="Wednesday Generation",
        replace_existing=True,
    )

    day_desc = "daily" if settings.schedule_day_of_week == "*" else settings.schedule_day_of_week
    logger.info(
        f"Scheduler configured: {day_desc} at "
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
    job = scheduler.get_job("pulllist_job")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return None
