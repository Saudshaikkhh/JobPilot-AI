"""
SQLAlchemy ORM models for the Job Application Bot.

Defines the database schema for:
- Application: Tracks every job application attempt
- Blocklist: Companies/keywords to skip
- SessionHealth: Tracks session validity per platform
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class Application(Base):
    """
    Tracks every job application attempt across all platforms.

    The job_url column has a UNIQUE constraint to prevent duplicate applications.
    """

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, index=True)       # 'linkedin', 'naukri', etc.
    job_title = Column(String(255), nullable=False)
    company = Column(String(255), default="")
    job_url = Column(Text, nullable=False, unique=True)             # prevents duplicates
    salary_range = Column(String(100), default="")
    location = Column(String(100), default="")
    status = Column(String(50), default="applied", index=True)      # applied | failed | skipped | dry_run
    failure_reason = Column(Text, default="")
    applied_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Application(id={self.id}, platform='{self.platform}', "
            f"title='{self.job_title}', company='{self.company}', "
            f"status='{self.status}')>"
        )


class Blocklist(Base):
    """
    Blocklist for companies or keywords to skip during job search.

    type: 'company' or 'keyword'
    value: The company name or keyword to block (case-insensitive matching)
    """

    __tablename__ = "blocklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)                        # 'company' | 'keyword'
    value = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("type", "value", name="uq_blocklist_type_value"),
    )

    def __repr__(self) -> str:
        return f"<Blocklist(type='{self.type}', value='{self.value}')>"


class SessionHealth(Base):
    """
    Tracks the health/validity of session cookies per platform.

    Updated each time a platform adapter validates its session.
    """

    __tablename__ = "session_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), unique=True, nullable=False)
    last_valid = Column(DateTime, nullable=True)
    is_expired = Column(Boolean, default=False)

    def __repr__(self) -> str:
        status = "EXPIRED" if self.is_expired else "VALID"
        return f"<SessionHealth(platform='{self.platform}', status={status})>"
