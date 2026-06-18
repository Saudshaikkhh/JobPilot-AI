"""
Rich-based CLI dashboard for the Job Application Bot.

Provides clean, formatted visual status components for:
- Current session cookie health status
- Today's performance statistics (applied/skipped/failed)
- Search history tables
- Job run configurations headers
"""

from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from src.core.config import Config
from src.core.database import Database
from src.core.models import Application, SessionHealth

# Console helper using the global theme
from src.core.logger import console

def display_run_header(config: Config) -> None:
    """Show a beautiful start header panel in CLI."""
    mode_text = "[bold cyan]DRY RUN[/bold cyan] (Simulated)" if config.dry_run else "[bold red]LIVE APPLY[/bold red] (Real Submission)"
    
    header_info = (
        f"[bold]Mode:[/bold] {mode_text}\n"
        f"[bold]Keywords:[/bold] {', '.join(config.keywords[:5])}...\n"
        f"[bold]Locations:[/bold] {', '.join(config.locations) if config.locations else 'Any'}\n"
        f"[bold]Resume:[/bold] [dim]{config.resume_path}[/dim]\n"
        f"[bold]Browser:[/bold] {config.browser} (headless={config.headless})"
    )
    
    panel = Panel(
        Align.center(header_info),
        title="🤖 [bold white]AI Job Application Bot[/bold white] 🤖",
        subtitle="v1.0.0",
        border_style="blue",
    )
    console.print(panel)
    console.print()

def display_status(db: Database, platform: Optional[str] = None) -> None:
    """Render a table displaying today's application statistics."""
    console.print(Panel("[bold white]Today's Statistics[/bold white]", border_style="green", expand=False))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Platform", style="dim", width=12)
    table.add_column("Applied ✅", justify="right", style="green")
    table.add_column("Dry Run 👁️", justify="right", style="cyan")
    table.add_column("Skipped ⏭️", justify="right", style="yellow")
    table.add_column("Failed ❌", justify="right", style="red")
    table.add_column("Total", justify="right", style="bold white")

    # If platform specified, show just that, otherwise all
    from src.platforms.registry import get_available_platforms
    platforms = [platform] if platform else get_available_platforms()

    totals = {"applied": 0, "dry_run": 0, "skipped": 0, "failed": 0, "total": 0}

    for plat in platforms:
        stats = db.get_stats(plat)
        table.add_row(
            plat.capitalize(),
            str(stats.get("applied", 0)),
            str(stats.get("dry_run", 0)),
            str(stats.get("skipped", 0)),
            str(stats.get("failed", 0)),
            str(stats.get("total", 0))
        )
        totals["applied"] += stats.get("applied", 0)
        totals["dry_run"] += stats.get("dry_run", 0)
        totals["skipped"] += stats.get("skipped", 0)
        totals["failed"] += stats.get("failed", 0)
        totals["total"] += stats.get("total", 0)

    if not platform:
        table.add_section()
        table.add_row(
            "[bold]Total[/bold]",
            str(totals["applied"]),
            str(totals["dry_run"]),
            str(totals["skipped"]),
            str(totals["failed"]),
            str(totals["total"])
        )

    console.print(table)
    console.print()

def display_history(applications: List[Application]) -> None:
    """Render a table of application history."""
    if not applications:
        console.print("[yellow]No applications found in history.[/yellow]")
        return

    table = Table(title="Recent Application History", show_header=True, header_style="bold blue")
    table.add_column("Date/Time", width=19)
    table.add_column("Platform", width=10)
    table.add_column("Job Title", width=30, overflow="ellipsis")
    table.add_column("Company", width=20, overflow="ellipsis")
    table.add_column("Status", width=12)
    table.add_column("Details", width=30, overflow="ellipsis")

    for app in applications:
        # Format date
        date_str = app.applied_at.strftime("%Y-%m-%d %H:%M:%S")
        
        # Format status badge
        status_badges = {
            "applied": "[bold green]APPLIED[/bold green]",
            "failed": "[bold red]FAILED[/bold red]",
            "skipped": "[bold yellow]SKIPPED[/bold yellow]",
            "dry_run": "[bold cyan]DRY RUN[/bold cyan]"
        }
        status_styled = status_badges.get(app.status, app.status.upper())
        
        detail_msg = app.failure_reason if app.status in ["failed", "skipped"] else "Success"

        table.add_row(
            date_str,
            app.platform.capitalize(),
            app.job_title,
            app.company,
            status_styled,
            detail_msg
        )

    console.print(table)
    console.print()

def display_sessions(health_records: List[SessionHealth]) -> None:
    """Show session credentials health status."""
    console.print(Panel("[bold white]Session Health Status[/bold white]", border_style="blue", expand=False))
    
    if not health_records:
        console.print("[yellow]No platform session checks recorded yet. Run the bot to populate health metrics.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Platform", width=15)
    table.add_column("Status", width=12)
    table.add_column("Last Valid Session", width=25)

    for record in health_records:
        status_badge = "[bold red]EXPIRED ❌[/bold red]" if record.is_expired else "[bold green]ACTIVE  ✅[/bold green]"
        last_valid_str = record.last_valid.strftime("%Y-%m-%d %H:%M:%S") if record.last_valid else "Never"
        
        table.add_row(
            record.platform.capitalize(),
            status_badge,
            last_valid_str
        )

    console.print(table)
    console.print()
