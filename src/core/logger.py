"""
Structured logging setup for the Job Application Bot.

Provides:
- Rich console output with colors and formatting
- File logging with daily rotation
- A structured log format matching the PRD spec:
  [timestamp] Platform → "Job Title" @ Company → STATUS
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Custom theme for the bot's console output
BOT_THEME = Theme({
    "applied": "bold green",
    "skipped": "bold yellow",
    "failed": "bold red",
    "dry_run": "bold cyan",
    "info": "bold blue",
    "platform": "bold magenta",
    "job_title": "bold white",
    "company": "dim white",
})

# Global console instance
console = Console(theme=BOT_THEME)


def setup_logger(logs_dir: Path, verbose: bool = False) -> logging.Logger:
    """
    Set up the application logger with both console and file handlers.

    Args:
        logs_dir: Directory to store log files.
        verbose: If True, set log level to DEBUG.

    Returns:
        Configured logger instance.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("job_bot")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Prevent duplicate handlers on re-init
    logger.handlers.clear()

    # --- Console handler (Rich) ---
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=verbose,
    )
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)

    # --- File handler (daily log file) ---
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"bot_{today}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """Get the application logger instance."""
    return logging.getLogger("job_bot")


# ------------------------------------------------------------------
# Convenience logging functions for structured application events
# ------------------------------------------------------------------

STATUS_EMOJI = {
    "applied": "✅",
    "failed": "❌",
    "skipped": "⏭️",
    "dry_run": "👁️",
}

STATUS_STYLE = {
    "applied": "[applied]APPLIED[/applied]",
    "failed": "[failed]FAILED[/failed]",
    "skipped": "[skipped]SKIPPED[/skipped]",
    "dry_run": "[dry_run]DRY RUN[/dry_run]",
}


def log_application_event(
    platform: str,
    job_title: str,
    company: str,
    status: str,
    reason: str = "",
) -> None:
    """
    Log a formatted application event to both console and file.

    Produces output like:
    [2026-06-18 09:01:23] LinkedIn → "Senior Full Stack Dev" @ Razorpay → APPLIED ✅

    Args:
        platform: Platform name.
        job_title: Job title.
        company: Company name.
        status: Application status.
        reason: Optional reason for skip/failure.
    """
    logger = get_logger()
    emoji = STATUS_EMOJI.get(status, "❓")
    styled_status = STATUS_STYLE.get(status, status.upper())

    # Rich console output
    reason_str = f" ({reason})" if reason else ""
    console.print(
        f"  [platform]{platform.capitalize():10s}[/platform] → "
        f"[job_title]\"{job_title}\"[/job_title] @ "
        f"[company]{company}[/company] → "
        f"{styled_status} {emoji}{reason_str}"
    )

    # Plain file log
    reason_file = f" ({reason})" if reason else ""
    logger.debug(
        f"{platform.capitalize()} → \"{job_title}\" @ {company} → "
        f"{status.upper()} {emoji}{reason_file}"
    )


def log_summary(stats: dict) -> None:
    """
    Log a summary of today's application run.

    Args:
        stats: Dict with keys 'applied', 'skipped', 'failed', 'dry_run'.
    """
    console.print()
    console.rule("[bold]Run Summary[/bold]")
    console.print(
        f"  [applied]{stats.get('applied', 0)} applied[/applied] | "
        f"[skipped]{stats.get('skipped', 0)} skipped[/skipped] | "
        f"[failed]{stats.get('failed', 0)} failed[/failed] | "
        f"[dry_run]{stats.get('dry_run', 0)} dry run[/dry_run]"
    )
    console.rule()
