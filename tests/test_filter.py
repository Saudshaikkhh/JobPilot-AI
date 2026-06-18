"""
Unit tests for the job filtering engine.
"""

from src.platforms.base import JobListing
from src.engine.filter import (
    filter_by_keywords,
    filter_by_salary,
    filter_by_location,
    filter_by_blocklist,
    parse_salary_string,
)

def test_parse_salary_string():
    """Verify salary string parsers extract numbers accurately."""
    # LPA format
    assert parse_salary_string("10-15 LPA") == (1000000.0, 1500000.0)
    assert parse_salary_string("8L - 12L") == (800000.0, 1200000.0)
    assert parse_salary_string("12 LPA") == (1200000.0, 1200000.0)
    
    # Direct Numeric formatting
    assert parse_salary_string("₹8,00,000 - ₹12,00,000") == (800000.0, 1200000.0)
    assert parse_salary_string("600000 - 900000") == (600000.0, 900000.0)

    # Fallback/unknown
    assert parse_salary_string("Not Disclosed") == (0.0, 0.0)

def test_filter_by_keywords():
    """Test keyword title filtering."""
    job = JobListing(title="Full Stack Developer", company="Test", url="http://x.com")
    assert filter_by_keywords(job, ["Stack", "Node.js"]) is True
    assert filter_by_keywords(job, ["Python", "Rust"]) is False

def test_filter_by_location():
    """Test location keyword matching."""
    job = JobListing(title="Dev", company="Test", url="http://x.com", location="Bengaluru, Hybrid")
    assert filter_by_location(job, ["Bengaluru"]) is True
    assert filter_by_location(job, ["Remote"]) is False
    assert filter_by_location(job, ["Hybrid"]) is True

    # Remote heuristic check
    job_remote = JobListing(title="Dev", company="Test", url="http://x.com", location="Work from home")
    assert filter_by_location(job_remote, ["Remote"]) is True

def test_filter_by_blocklist():
    """Test company blocklist."""
    job = JobListing(title="Dev", company="SpamCorp Ltd", url="http://x.com")
    assert filter_by_blocklist(job, ["SpamCorp"]) is False
    assert filter_by_blocklist(job, ["GoodCorp"]) is True
