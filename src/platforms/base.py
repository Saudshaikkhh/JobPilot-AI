"""
Abstract base adapter and shared data classes for platform adapters.

All platform adapters (LinkedIn, Naukri, Indeed, Hirist) MUST inherit from
BasePlatformAdapter and implement its abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from playwright.async_api import Page

from src.core.config import Config


class ApplicationStatus(str, Enum):
    """Status of a job application attempt."""
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"


@dataclass
class JobListing:
    """
    Represents a single job listing extracted from a platform.

    This is the universal format used across all platform adapters.
    """
    title: str
    company: str
    url: str
    location: str = ""
    salary: str = ""
    posted_date: str = ""
    platform: str = ""
    job_type: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<Job: '{self.title}' @ {self.company} [{self.platform}]>"


@dataclass
class ApplicationResult:
    """
    Result of attempting to apply to a job.

    Returned by each platform adapter's apply_to_job() method.
    """
    status: ApplicationStatus
    job: JobListing
    message: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == ApplicationStatus.APPLIED

    def __repr__(self) -> str:
        return (
            f"<Result: {self.status.value} for '{self.job.title}' "
            f"@ {self.job.company}>"
        )


class BasePlatformAdapter(ABC):
    """
    Abstract base class for all platform adapters.

    Every platform adapter must implement:
    - platform_name: Unique identifier for the platform
    - validate_session(): Check if the session cookies are still valid
    - search_jobs(): Search for jobs matching the configured criteria
    - apply_to_job(): Apply to a specific job listing

    Optional overrides:
    - get_search_url(): Build the search URL for this platform
    """

    def __init__(self, config: Config):
        """
        Initialize the adapter with configuration.

        Args:
            config: Application configuration.
        """
        self.config = config

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Unique name identifier for this platform (e.g., 'linkedin')."""
        ...

    @property
    def daily_limit(self) -> int:
        """Get the daily application limit for this platform."""
        return self.config.daily_limits.get(self.platform_name, 20)

    @abstractmethod
    async def validate_session(self, page: Page) -> bool:
        """
        Validate that the session cookies are still active.

        Navigate to a logged-in page and verify the user is authenticated.
        If the session is expired (redirected to login), return False.

        Args:
            page: Playwright page with cookies already loaded.

        Returns:
            True if session is valid, False if expired.
        """
        ...

    @abstractmethod
    async def search_jobs(
        self,
        page: Page,
        keyword: str,
        location: str,
    ) -> list[JobListing]:
        """
        Search for job listings on this platform.

        Args:
            page: Playwright page with cookies loaded.
            keyword: Search keyword (job title or skill).
            location: Location filter.

        Returns:
            List of JobListing objects found.
        """
        ...

    @abstractmethod
    async def apply_to_job(
        self,
        page: Page,
        job: JobListing,
    ) -> ApplicationResult:
        """
        Apply to a specific job listing.

        Args:
            page: Playwright page with cookies loaded.
            job: The job listing to apply to.

        Returns:
            ApplicationResult with the status of the attempt.
        """
        ...

    def get_search_url(self, keyword: str, location: str) -> str:
        """
        Build the search URL for this platform.

        Override this method in subclasses for platform-specific URL construction.

        Args:
            keyword: Search keyword.
            location: Location filter.

        Returns:
            Fully constructed search URL string.
        """
        raise NotImplementedError(
            f"{self.platform_name} adapter must implement get_search_url()"
        )
