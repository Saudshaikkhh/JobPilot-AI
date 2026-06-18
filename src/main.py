"""
AI Job Application Bot CLI Entry Point.

Provides Click subcommands for running, auditing history, viewing health,
managing blocklists, and setting schedulers.
"""

import asyncio
import click
import logging
from pathlib import Path

from src.core.config import load_config
from src.core.database import Database
from src.core.logger import setup_logger, console
from src.browser.browser_manager import BrowserManager
from src.engine.applier import run_all_platforms
from src.dashboard.cli_dashboard import (
    display_run_header,
    display_status,
    display_history,
    display_sessions,
)
from src.scheduler.scheduler import start_scheduled_runs

logger = logging.getLogger("job_bot")

async def _run_async(platform, dry_run, verbose):
    """Internal async runner for the run command."""
    try:
        config = load_config()
    except FileNotFoundError as e:
        click.echo(click.style(str(e), fg="red"))
        return
        
    # Overrides
    if dry_run is not None:
        config.dry_run = dry_run
        
    setup_logger(config.logs_dir, verbose)
    
    # Display start header
    display_run_header(config)
    
    # Initialize DB & Browser
    db = Database(config.db_path)
    browser_manager = BrowserManager(config)
    
    platforms_to_run = [platform] if platform else None
    
    await run_all_platforms(config, db, browser_manager, platforms=platforms_to_run)
    
    # Display end statistics
    console.print()
    display_status(db, platform)


@click.group()
def cli():
    """🤖 AI Job Application Bot — Automate your job hunt on auto-pilot."""
    pass


@cli.command()
@click.option("--platform", "-p", default=None, help="Run single platform only (linkedin/naukri/hirist/indeed).")
@click.option("--dry-run/--live", default=None, is_flag=True, help="Override dry-run flag from config.")
@click.option("--verbose", "-v", is_flag=True, help="Show debug browser logs.")
def run(platform, dry_run, verbose):
    """Run the job automation loops search-and-apply pipeline."""
    asyncio.run(_run_async(platform, dry_run, verbose))


@cli.command()
@click.option("--platform", "-p", default=None, help="Filter by platform.")
def status(platform):
    """Show today's application statistics from SQLite."""
    config = load_config()
    db = Database(config.db_path)
    display_status(db, platform)


@cli.command()
@click.option("--platform", "-p", default=None, help="Filter applications by platform.")
@click.option("--status", "-s", "filter_status", default=None, help="Filter by status (applied/skipped/failed).")
@click.option("--limit", "-n", default=25, help="Number of records to show.")
def history(platform, filter_status, limit):
    """Show recent applications log history."""
    config = load_config()
    db = Database(config.db_path)
    apps = db.get_applications(platform=platform, status=filter_status, limit=limit)
    display_history(apps)


@cli.command()
def sessions():
    """Verify session cookie expiration checks stored in DB."""
    config = load_config()
    db = Database(config.db_path)
    health = db.get_session_health()
    display_sessions(health)


@cli.group()
def blocklist():
    """Manage blocked company listings."""
    pass


@blocklist.command("add")
@click.argument("company")
def blocklist_add(company):
    """Add a company name to block (case-insensitive substring)."""
    config = load_config()
    db = Database(config.db_path)
    try:
        db.add_to_blocklist("company", company)
        click.echo(click.style(f"Added '{company}' to company blocklist.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error adding: {e}", fg="red"))


@blocklist.command("list")
def blocklist_list():
    """List all blocked companies."""
    config = load_config()
    db = Database(config.db_path)
    blocked = db.get_blocklist("company")
    if not blocked:
        click.echo("Blocklist is currently empty.")
        return
    
    click.echo(click.style("=== Blocked Companies ===", fg="yellow"))
    for item in blocked:
        click.echo(f"- {item.value} (Blocked: {item.created_at.strftime('%Y-%m-%d')})")


@blocklist.command("remove")
@click.argument("company")
def blocklist_remove(company):
    """Remove a company from the blocklist."""
    config = load_config()
    db = Database(config.db_path)
    removed = db.remove_from_blocklist("company", company)
    if removed:
        click.echo(click.style(f"Removed '{company}' from blocklist.", fg="green"))
    else:
        click.echo(click.style(f"Could not find company '{company}' in blocklist.", fg="red"))


@cli.command()
def schedule():
    """Start blocking daemon for background cron schedules."""
    config = load_config()
    setup_logger(config.logs_dir, verbose=False)
    
    # Enable schedule force if starting daemon
    config.schedule.enabled = True
    start_scheduled_runs(config)


if __name__ == "__main__":
    cli()
