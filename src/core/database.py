"""
Database setup and session management for the Job Application Bot.

Uses SQLite via SQLAlchemy. The database file is stored at data/job_bot.db
and is automatically created on first run.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Application, Base, Blocklist, SessionHealth


class Database:
    """
    SQLite database manager using SQLAlchemy.

    Handles database creation, session management, and provides
    convenience methods for common queries.
    """

    def __init__(self, db_path: Path):
        """
        Initialize the database.

        Args:
            db_path: Path to the SQLite database file.
        """
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self.SessionFactory = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionFactory()

    # ------------------------------------------------------------------
    # Application queries
    # ------------------------------------------------------------------

    def is_duplicate(self, job_url: str) -> bool:
        """
        Check if a job URL has already been applied to.

        Args:
            job_url: The job listing URL to check.

        Returns:
            True if the URL exists in the database.
        """
        normalized_url = self._normalize_url(job_url)
        with self.get_session() as session:
            exists = session.query(
                session.query(Application)
                .filter(Application.job_url == normalized_url)
                .exists()
            ).scalar()
            return exists

    def log_application(
        self,
        platform: str,
        job_title: str,
        company: str,
        job_url: str,
        salary_range: str = "",
        location: str = "",
        status: str = "applied",
        failure_reason: str = "",
    ) -> Application:
        """
        Log a job application attempt to the database.

        Args:
            platform: Platform name (e.g., 'linkedin', 'naukri')
            job_title: Title of the job listing
            company: Company name
            job_url: URL of the job listing (must be unique)
            salary_range: Salary range string
            location: Job location
            status: Application status ('applied', 'failed', 'skipped', 'dry_run')
            failure_reason: Reason for failure/skip (if applicable)

        Returns:
            The created Application record.
        """
        normalized_url = self._normalize_url(job_url)
        with self.get_session() as session:
            app = Application(
                platform=platform,
                job_title=job_title,
                company=company,
                job_url=normalized_url,
                salary_range=salary_range,
                location=location,
                status=status,
                failure_reason=failure_reason,
            )
            session.add(app)
            session.commit()
            session.refresh(app)
            return app

    def get_today_count(self, platform: str) -> int:
        """
        Get the number of applications submitted today for a given platform.

        Args:
            platform: Platform name to count.

        Returns:
            Number of 'applied' or 'dry_run' applications today.
        """
        today = datetime.now(timezone.utc).date()
        with self.get_session() as session:
            count = session.query(func.count(Application.id)).filter(
                Application.platform == platform,
                Application.status.in_(["applied", "dry_run"]),
                func.date(Application.applied_at) == today,
            ).scalar()
            return count or 0

    def get_applications(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[Application]:
        """
        Get recent applications with optional filtering.

        Args:
            platform: Filter by platform name (optional)
            status: Filter by status (optional)
            limit: Maximum number of results (default 50)

        Returns:
            List of Application records, newest first.
        """
        with self.get_session() as session:
            query = session.query(Application)
            if platform:
                query = query.filter(Application.platform == platform)
            if status:
                query = query.filter(Application.status == status)
            query = query.order_by(Application.applied_at.desc()).limit(limit)
            return query.all()

    def get_stats(self, platform: Optional[str] = None) -> dict:
        """
        Get application statistics.

        Args:
            platform: Optional platform filter.

        Returns:
            Dict with counts per status and total.
        """
        today = datetime.now(timezone.utc).date()
        with self.get_session() as session:
            query = session.query(
                Application.status,
                func.count(Application.id),
            )
            if platform:
                query = query.filter(Application.platform == platform)
            query = query.filter(
                func.date(Application.applied_at) == today,
            )
            query = query.group_by(Application.status)
            results = query.all()

            stats = {
                "applied": 0,
                "failed": 0,
                "skipped": 0,
                "dry_run": 0,
                "total": 0,
            }
            for status, count in results:
                stats[status] = count
                stats["total"] += count
            return stats

    # ------------------------------------------------------------------
    # Blocklist queries
    # ------------------------------------------------------------------

    def add_to_blocklist(self, block_type: str, value: str) -> Blocklist:
        """
        Add an entry to the blocklist.

        Args:
            block_type: 'company' or 'keyword'
            value: The company name or keyword to block.

        Returns:
            The created Blocklist record.
        """
        with self.get_session() as session:
            entry = Blocklist(type=block_type, value=value)
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    def remove_from_blocklist(self, block_type: str, value: str) -> bool:
        """Remove an entry from the blocklist. Returns True if removed."""
        with self.get_session() as session:
            deleted = session.query(Blocklist).filter(
                Blocklist.type == block_type,
                Blocklist.value == value,
            ).delete()
            session.commit()
            return deleted > 0

    def get_blocklist(self, block_type: Optional[str] = None) -> list[Blocklist]:
        """Get all blocklist entries, optionally filtered by type."""
        with self.get_session() as session:
            query = session.query(Blocklist)
            if block_type:
                query = query.filter(Blocklist.type == block_type)
            return query.order_by(Blocklist.created_at.desc()).all()

    def get_blocked_companies(self) -> list[str]:
        """Get a list of all blocked company names (lowercased)."""
        with self.get_session() as session:
            entries = session.query(Blocklist.value).filter(
                Blocklist.type == "company"
            ).all()
            return [e.value.lower() for e in entries]

    # ------------------------------------------------------------------
    # Session health queries
    # ------------------------------------------------------------------

    def update_session_health(self, platform: str, is_valid: bool) -> None:
        """
        Update session health for a platform.

        Args:
            platform: Platform name.
            is_valid: Whether the session is currently valid.
        """
        with self.get_session() as session:
            health = session.query(SessionHealth).filter(
                SessionHealth.platform == platform
            ).first()

            now = datetime.now(timezone.utc)

            if health:
                health.is_expired = not is_valid
                if is_valid:
                    health.last_valid = now
            else:
                health = SessionHealth(
                    platform=platform,
                    last_valid=now if is_valid else None,
                    is_expired=not is_valid,
                )
                session.add(health)

            session.commit()

    def get_session_health(self) -> list[SessionHealth]:
        """Get session health status for all platforms."""
        with self.get_session() as session:
            return session.query(SessionHealth).all()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize a job URL by stripping tracking parameters.

        Removes common tracking params like utm_*, refId, trackingId, etc.
        """
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Remove tracking parameters
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_content",
            "utm_term", "refId", "trackingId", "trk", "ref", "origin",
            "currentJobId", "position", "pageNum",
        }
        cleaned = {k: v for k, v in params.items() if k not in tracking_params}

        cleaned_query = urlencode(cleaned, doseq=True)
        normalized = urlunparse(parsed._replace(query=cleaned_query))
        return normalized.rstrip("/")
