"""APScheduler setup for daily data refresh and RS computation."""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from jobs.daily_refresh import (
    run_stooq_daily_refresh,
    run_yfinance_gap_fill,
    run_stooq_bulk_download,
    run_rs_computation,
)

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Schedule:
        - Daily at 02:00 UTC: Stooq daily data refresh + RS computation
        - Daily at 10:30 UTC (16:00 IST): yfinance gap-fill + RS computation
        - Sunday 06:00 UTC: Full Stooq bulk download + RS computation
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # Daily Stooq refresh at 02:00 UTC
    scheduler.add_job(
        run_stooq_daily_refresh,
        trigger=CronTrigger(hour=2, minute=0),
        id="stooq_daily_refresh",
        name="Stooq daily data refresh",
        misfire_grace_time=3600,
        max_instances=1,
    )

    # RS computation after Stooq daily refresh at 02:30 UTC
    scheduler.add_job(
        run_rs_computation,
        trigger=CronTrigger(hour=2, minute=30),
        id="rs_computation_stooq",
        name="RS computation after Stooq refresh",
        misfire_grace_time=3600,
        max_instances=1,
    )

    # yfinance gap-fill at 10:30 UTC (16:00 IST — after Indian market close)
    scheduler.add_job(
        run_yfinance_gap_fill,
        trigger=CronTrigger(hour=10, minute=30),
        id="yfinance_gap_fill",
        name="yfinance gap-fill for India/Korea/others",
        misfire_grace_time=3600,
        max_instances=1,
    )

    # RS computation after yfinance gap-fill at 11:00 UTC
    scheduler.add_job(
        run_rs_computation,
        trigger=CronTrigger(hour=11, minute=0),
        id="rs_computation_yfinance",
        name="RS computation after yfinance gap-fill",
        misfire_grace_time=3600,
        max_instances=1,
    )

    # Weekly full Stooq bulk download on Sunday at 06:00 UTC
    scheduler.add_job(
        run_stooq_bulk_download,
        trigger=CronTrigger(day_of_week="sun", hour=6, minute=0),
        id="stooq_bulk_download",
        name="Weekly Stooq bulk download",
        misfire_grace_time=7200,
        max_instances=1,
    )

    # RS computation after bulk download on Sunday at 07:00 UTC
    scheduler.add_job(
        run_rs_computation,
        trigger=CronTrigger(day_of_week="sun", hour=7, minute=0),
        id="rs_computation_bulk",
        name="RS computation after bulk download",
        misfire_grace_time=3600,
        max_instances=1,
    )

    logger.info("Scheduler configured with %d jobs", len(scheduler.get_jobs()))
    return scheduler


async def start_scheduler() -> AsyncIOScheduler:
    """Start the scheduler and return it for lifecycle management."""
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler


async def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Gracefully shut down the scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
