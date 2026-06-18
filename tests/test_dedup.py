"""
Unit tests for duplicate checks and URL normalization.
"""

from pathlib import Path
from src.core.database import Database
from src.engine.dedup import normalize_url, is_duplicate

def test_normalize_url():
    """Verify URL normalizations trim tracking parameters."""
    url1 = "https://www.linkedin.com/jobs/view/12345/?refId=abcdef&trackingId=xyz"
    url2 = "https://www.linkedin.com/jobs/view/12345"
    assert normalize_url(url1) == url2

def test_database_deduplication(tmp_path):
    """Verify logging application marks url as duplicate in sqlite database."""
    db_file = tmp_path / "test.db"
    db = Database(db_file)
    
    url = "https://www.linkedin.com/jobs/view/12345/?refId=abcdef"
    normalized = normalize_url(url)
    
    assert db.is_duplicate(url) is False
    
    # Log application
    db.log_application(
        platform="linkedin",
        job_title="Python Developer",
        company="Razorpay",
        job_url=url
    )
    
    # Check deduplication
    assert db.is_duplicate(url) is True
    assert db.is_duplicate(normalized) is True
