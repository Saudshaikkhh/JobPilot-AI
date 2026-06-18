"""
APScheduler-based job runner for automation.

Sets up background or foreground blocking schedules for daily runs.
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from src.core.config import Config
from src.core.database import Database
from src.browser.browser_manager import BrowserManager
from src.engine.applier import run_all_platforms

logger = logging.getLogger("job_bot")

def run_job_flow(config: Config) -> None:
    """Execution callback for scheduler."""
    logger.info("Executing scheduled automated run...")
    db = Database(config.db_path)
    browser_mgr = BrowserManager(config)
    
    # Run async function in standard synchronous scheduler wrapper
    import asyncio
    asyncio.run(run_all_platforms(config, db, browser_mgr))

def start_scheduled_runs(config: Config) -> None:
    """
    Start BlockingScheduler to wait and run tasks according to config.yaml.
    """
    if not config.schedule.enabled:
        logger.warning("Scheduling is disabled in config.yaml. Running foreground schedule instead.")

    # We use BlockingScheduler so the CLI command hangs appropriately
    scheduler = BlockingScheduler(timezone=config.schedule.timezone)
    
    # Configure trigger parameters
    # mon-fri, mon,tue,wed,etc.
    day_of_week = config.schedule.days
    hour = config.schedule.cron_hour
    minute = config.schedule.cron_minute

    logger.info(
        f"Starting scheduler: trigger at {hour:02d}:{minute:02d} on {day_of_week} "
        f"({config.schedule.timezone})"
    )

    scheduler.add_job(
        run_job_flow,
        "cron",
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
        args=[config],
        id="automated_apply_job"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by keyboard interrupt.")
        scheduler.shutdown()
