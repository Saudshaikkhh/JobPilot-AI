"""
Configuration loader for the Job Application Bot.

Loads settings from config.yaml and environment variables from .env file.
Provides a typed Config dataclass for clean access throughout the application.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


# Project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class SalaryConfig:
    """Salary range configuration."""
    min: int = 0
    max: int = 0
    currency: str = "INR"


@dataclass
class DelayConfig:
    """Human-like delay configuration."""
    min_ms: int = 1500
    max_ms: int = 4000


@dataclass
class ProfileConfig:
    """User profile for form filling."""
    full_name: str = ""
    email: str = ""
    phone: str = ""
    experience_years: int = 0
    current_company: str = ""
    current_title: str = ""
    notice_period: str = "Immediate"
    linkedin_url: str = ""


@dataclass
class ScheduleConfig:
    """Scheduler configuration."""
    enabled: bool = False
    cron_hour: int = 9
    cron_minute: int = 0
    days: str = "mon-fri"
    timezone: str = "Asia/Kolkata"


@dataclass
class SessionCookies:
    """All platform session cookies loaded from .env."""
    # LinkedIn
    li_at: str = ""
    li_jsessionid: str = ""
    li_bcookie: str = ""
    li_bscookie: str = ""

    # Naukri
    nauk_at: str = ""

    # Indeed
    indeed_jsessionid: str = ""
    indeed_csrf_token: str = ""

    # Hirist
    hirist_jsessionid: str = ""


@dataclass
class Config:
    """Main configuration for the Job Application Bot."""
    # Search parameters
    keywords: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    job_types: list[str] = field(default_factory=lambda: ["Full-time"])
    posted_within_days: int = 7

    # Salary
    salary: SalaryConfig = field(default_factory=SalaryConfig)

    # Limits
    daily_limits: dict[str, int] = field(default_factory=lambda: {
        "linkedin": 20,
        "naukri": 25,
        "hirist": 15,
        "indeed": 10,
    })

    # Blocklist
    blocked_companies: list[str] = field(default_factory=list)

    # Bot behavior
    dry_run: bool = True
    headless: bool = False
    browser: str = "chromium"
    delay: DelayConfig = field(default_factory=DelayConfig)

    # Resume
    resume_path: str = "resume/saud-resume.pdf"

    # Profile
    profile: ProfileConfig = field(default_factory=ProfileConfig)

    # Schedule
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)

    # Session cookies (loaded from .env)
    cookies: SessionCookies = field(default_factory=SessionCookies)

    @property
    def resume_absolute_path(self) -> Path:
        """Get absolute path to resume file."""
        path = Path(self.resume_path)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    @property
    def db_path(self) -> Path:
        """Get absolute path to SQLite database."""
        return PROJECT_ROOT / "data" / "job_bot.db"

    @property
    def logs_dir(self) -> Path:
        """Get absolute path to logs directory."""
        return PROJECT_ROOT / "logs"


def _load_env_cookies() -> SessionCookies:
    """Load session cookies from environment variables."""
    return SessionCookies(
        li_at=os.getenv("LI_AT", ""),
        li_jsessionid=os.getenv("LI_JSESSIONID", ""),
        li_bcookie=os.getenv("LI_BCOOKIE", ""),
        li_bscookie=os.getenv("LI_BSCOOKIE", ""),
        nauk_at=os.getenv("NAUK_AT", ""),
        indeed_jsessionid=os.getenv("INDEED_JSESSIONID", ""),
        indeed_csrf_token=os.getenv("INDEED_CSRF_TOKEN", ""),
        hirist_jsessionid=os.getenv("HIRIST_JSESSIONID", ""),
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from config.yaml and .env file.

    Args:
        config_path: Optional path to config.yaml. Defaults to PROJECT_ROOT/config.yaml.

    Returns:
        Config: Fully loaded configuration object.

    Raises:
        FileNotFoundError: If config.yaml doesn't exist.
        yaml.YAMLError: If config.yaml is malformed.
    """
    # Load .env file
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Determine config file path
    if config_path is None:
        config_path = str(PROJECT_ROOT / "config.yaml")

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_file}\n"
            f"Please create config.yaml in the project root."
        )

    # Load YAML
    with open(config_file, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # Build Config object
    salary_raw = raw.get("salary", {})
    delay_raw = raw.get("delay", {})
    profile_raw = raw.get("profile", {})
    schedule_raw = raw.get("schedule", {})

    config = Config(
        keywords=raw.get("keywords", []),
        locations=raw.get("locations", []),
        job_types=raw.get("job_types", ["Full-time"]),
        posted_within_days=raw.get("posted_within_days", 7),
        salary=SalaryConfig(
            min=salary_raw.get("min", 0),
            max=salary_raw.get("max", 0),
            currency=salary_raw.get("currency", "INR"),
        ),
        daily_limits=raw.get("daily_limits", {
            "linkedin": 20,
            "naukri": 25,
            "hirist": 15,
            "indeed": 10,
        }),
        blocked_companies=raw.get("blocked_companies", []),
        dry_run=raw.get("dry_run", True),
        headless=raw.get("headless", False),
        browser=raw.get("browser", "chromium"),
        delay=DelayConfig(
            min_ms=delay_raw.get("min_ms", 1500),
            max_ms=delay_raw.get("max_ms", 4000),
        ),
        resume_path=raw.get("resume_path", "resume/saud-resume.pdf"),
        profile=ProfileConfig(
            full_name=profile_raw.get("full_name", ""),
            email=profile_raw.get("email", ""),
            phone=profile_raw.get("phone", ""),
            experience_years=profile_raw.get("experience_years", 0),
            current_company=profile_raw.get("current_company", ""),
            current_title=profile_raw.get("current_title", ""),
            notice_period=profile_raw.get("notice_period", "Immediate"),
            linkedin_url=profile_raw.get("linkedin_url", ""),
        ),
        schedule=ScheduleConfig(
            enabled=schedule_raw.get("enabled", False),
            cron_hour=schedule_raw.get("cron_hour", 9),
            cron_minute=schedule_raw.get("cron_minute", 0),
            days=schedule_raw.get("days", "mon-fri"),
            timezone=schedule_raw.get("timezone", "Asia/Kolkata"),
        ),
        cookies=_load_env_cookies(),
    )

    # Ensure required directories exist
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    config.logs_dir.mkdir(parents=True, exist_ok=True)

    return config
