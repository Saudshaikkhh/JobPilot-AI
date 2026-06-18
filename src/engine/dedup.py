"""
Deduplication engine.

Checks if a job URL has already been processed or applied to.
Normalizes URLs to remove dynamic tracking tokens to ensure accurate lookups.
"""

from src.core.database import Database

def normalize_url(url: str) -> str:
    """
    Delegate URL normalization to Database's utility method.
    Strips tracking queries such as utm_*, refId, etc.
    """
    return Database._normalize_url(url)

def is_duplicate(job_url: str, db: Database) -> bool:
    """
    Check if a job URL is already present in the database.

    Args:
        job_url: The raw job listing URL.
        db: Database manager instance.

    Returns:
        True if the normalized URL is found in the database.
    """
    return db.is_duplicate(job_url)
