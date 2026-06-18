"""
Application orchestrator and platform runner.

Coordinates the main flow of searching jobs, filtering, deduplicating,
applying (or dry-running), logging status to SQLite, and showing logs.
"""

import logging
from typing import List, Optional

from src.core.config import Config
from src.core.database import Database
from src.core.logger import log_application_event
from src.browser.browser_manager import BrowserManager
from src.platforms.registry import get_adapter, get_available_platforms
from src.platforms.base import JobListing, ApplicationStatus, ApplicationResult
from src.engine.filter import apply_all_filters
from src.engine.dedup import is_duplicate

logger = logging.getLogger("job_bot")

async def run_platform(
    platform_name: str,
    config: Config,
    db: Database,
    browser_manager: BrowserManager,
) -> dict:
    """
    Run the application pipeline for a single platform.

    Args:
        platform_name: Platform name (e.g., 'linkedin').
        config: Application configuration.
        db: Database manager.
        browser_manager: Launched browser manager.

    Returns:
        Dict containing counts of applied, skipped, failed, and dry_run jobs.
    """
    stats = {"applied": 0, "failed": 0, "skipped": 0, "dry_run": 0, "total": 0}

    try:
        adapter = get_adapter(platform_name, config)
    except ValueError as e:
        logger.error(f"Failed to find adapter: {e}")
        return stats

    logger.info(f"Starting pipeline for platform: {platform_name.upper()}")
    
    # Check daily limit remaining
    today_applied = db.get_today_count(platform_name)
    limit = adapter.daily_limit
    if today_applied >= limit:
        logger.warning(
            f"Daily limit reached for {platform_name} ({today_applied}/{limit}). "
            "Skipping platform run."
        )
        return stats

    # Get page context
    try:
        page = await browser_manager.get_page(platform_name)
    except Exception as e:
        logger.error(f"Failed to open browser page for {platform_name}: {e}", exc_info=True)
        return stats

    # Validate session
    is_session_valid = await adapter.validate_session(page)
    db.update_session_health(platform_name, is_session_valid)

    if not is_session_valid:
        logger.error(
            f"Session expired or invalid for {platform_name}. "
            "Please update cookies in .env."
        )
        await browser_manager.close_context(platform_name)
        return stats

    # Search and process jobs
    jobs_found: List[JobListing] = []
    
    # We loop through keywords and locations
    # LinkedIn / Naukri searches are run with combined pairs
    # Note: If locations is empty, run with empty location
    locations = config.locations if config.locations else [""]
    
    for kw in config.keywords:
        for loc in locations:
            # Check limits before running a new search
            current_today = db.get_today_count(platform_name) + stats["applied"] + stats["dry_run"]
            if current_today >= limit:
                logger.info(f"Daily limit reached during search loop for {platform_name}.")
                break
                
            try:
                found = await adapter.search_jobs(page, kw, loc)
                logger.info(f"Found {len(found)} jobs for '{kw}' in '{loc}' on {platform_name}")
                jobs_found.extend(found)
            except Exception as search_err:
                logger.error(f"Error searching '{kw}' in '{loc}' on {platform_name}: {search_err}")
                continue

    # Deduplicate matching results from multiple keyword searches
    unique_jobs: dict[str, JobListing] = {}
    for j in jobs_found:
        unique_jobs[j.url] = j

    logger.info(f"Extracted {len(unique_jobs)} unique job listings to process.")

    # Process each job
    for url, job in unique_jobs.items():
        # Re-check daily limits
        current_today = db.get_today_count(platform_name) + stats["applied"] + stats["dry_run"]
        if current_today >= limit:
            logger.warning(f"Daily limit {limit} reached for {platform_name}. Stopping processing.")
            break

        stats["total"] += 1

        # 1. Deduplication check
        if is_duplicate(job.url, db):
            stats["skipped"] += 1
            log_application_event(platform_name, job.title, job.company, "skipped", "duplicate")
            continue

        # 2. Config filtering
        passed, skip_reason = apply_all_filters(job, config)
        if not passed:
            stats["skipped"] += 1
            # Log skipped attempt in DB
            db.log_application(
                platform=platform_name,
                job_title=job.title,
                company=job.company,
                job_url=job.url,
                salary_range=job.salary,
                location=job.location,
                status="skipped",
                failure_reason=skip_reason,
            )
            log_application_event(platform_name, job.title, job.company, "skipped", skip_reason)
            continue

        # 3. Apply flow (dry-run or live apply)
        if config.dry_run:
            stats["dry_run"] += 1
            db.log_application(
                platform=platform_name,
                job_title=job.title,
                company=job.company,
                job_url=job.url,
                salary_range=job.salary,
                location=job.location,
                status="dry_run",
            )
            log_application_event(platform_name, job.title, job.company, "dry_run")
        else:
            logger.info(f"Submitting live application for: {job.title} @ {job.company}")
            result = await adapter.apply_to_job(page, job)
            
            # Log response
            db.log_application(
                platform=platform_name,
                job_title=job.title,
                company=job.company,
                job_url=job.url,
                salary_range=job.salary,
                location=job.location,
                status=result.status.value,
                failure_reason=result.message if result.status == ApplicationStatus.FAILED else "",
            )
            
            log_application_event(
                platform=platform_name,
                job_title=job.title,
                company=job.company,
                status=result.status.value,
                reason=result.message if result.status != ApplicationStatus.APPLIED else "",
            )

            if result.status == ApplicationStatus.APPLIED:
                stats["applied"] += 1
            elif result.status == ApplicationStatus.FAILED:
                stats["failed"] += 1
            elif result.status == ApplicationStatus.SKIPPED:
                stats["skipped"] += 1

    # Cleanup context
    await browser_manager.close_context(platform_name)
    logger.info(f"Finished platform run for {platform_name.upper()}. Stats: {stats}")
    return stats

async def run_all_platforms(
    config: Config,
    db: Database,
    browser_manager: BrowserManager,
    platforms: Optional[List[str]] = None,
) -> dict:
    """
    Run pipeline for all or a subset of platforms.

    Args:
        config: Application configuration.
        db: Database manager.
        browser_manager: Browser manager.
        platforms: Optional list of platform names. Defaults to all available.

    Returns:
        Combined stats summary dict.
    """
    target_platforms = platforms if platforms else get_available_platforms()
    combined_stats = {"applied": 0, "failed": 0, "skipped": 0, "dry_run": 0, "total": 0}

    # Launch browser
    await browser_manager.launch()

    try:
        for platform in target_platforms:
            platform_stats = await run_platform(platform, config, db, browser_manager)
            for k in combined_stats:
                combined_stats[k] += platform_stats.get(k, 0)
    finally:
        # Ensure browser is closed
        await browser_manager.close()

    return combined_stats
