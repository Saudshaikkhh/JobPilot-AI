"""
Job filtering engine.

Applies user configurations (keywords, salary range, locations, blocklist)
to decide whether to apply for a job or skip it.
"""

import logging
import re
from typing import Tuple

from src.core.config import Config
from src.platforms.base import JobListing

logger = logging.getLogger("job_bot")

def filter_by_keywords(job: JobListing, keywords: list[str]) -> bool:
    """
    Check if the job title matches any of the configured keywords.

    Case-insensitive match. Returns True if there's a match.
    If keywords list is empty, returns True.
    """
    if not keywords:
        return True
    
    title_lower = job.title.lower()
    for kw in keywords:
        # Check for substring match or word boundaries
        if kw.lower() in title_lower:
            return True
            
    return False

def parse_salary_string(salary_str: str) -> Tuple[float, float]:
    """
    Parse various salary string formats to numeric values (annualized).

    Supports formats like:
    - "10-15 LPA" or "10L - 15L" (Lakhs Per Annum)
    - "₹8,00,000 - ₹12,00,000" (INR numerals)
    - "800000 - 1500000"
    - "$80,000 - $120,000" (USD, assumes converted value or keeps raw numeric)

    Returns:
        Tuple of (min_salary, max_salary). (0.0, 0.0) if parsing fails.
    """
    if not salary_str:
        return 0.0, 0.0

    # Clean the string
    cleaned = salary_str.lower().replace(",", "").replace(" ", "")
    
    # Check for LPA format (e.g., "10-15lpa", "10l-15l")
    lpa_match = re.search(r"(\d+(?:\.\d+)?)(?:l|lpa)?-(\d+(?:\.\d+)?)(?:l|lpa)", cleaned)
    if lpa_match:
        try:
            min_val = float(lpa_match.group(1)) * 100000
            max_val = float(lpa_match.group(2)) * 100000
            return min_val, max_val
        except ValueError:
            pass

    # Check for numeric range (e.g., "800000-1200000", "₹800000-₹1200000")
    num_range_match = re.search(r"(?:[^\d]*?)(\d+)-(?:[^\d]*?)(\d+)", cleaned)
    if num_range_match:
        try:
            min_val = float(num_range_match.group(1))
            max_val = float(num_range_match.group(2))
            return min_val, max_val
        except ValueError:
            pass

    # Single value check (e.g. "12 LPA" or "800000")
    single_val_match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if single_val_match:
        try:
            val = float(single_val_match.group(1))
            # If it's small (e.g., 5-50), assume LPA
            if val < 100:
                val *= 100000
            return val, val
        except ValueError:
            pass

    return 0.0, 0.0

def filter_by_salary(job: JobListing, min_sal: int, max_sal: int) -> bool:
    """
    Check if the job salary range overlaps with the configured limits.

    If job has no salary specified, we return True (give benefit of doubt).
    If min_sal or max_sal is not set, returns True.
    """
    if not job.salary:
        # Give benefit of doubt if salary is not specified on the card
        return True

    if min_sal <= 0 and max_sal <= 0:
        return True

    job_min, job_max = parse_salary_string(job.salary)
    
    # If we couldn't parse the salary, don't block the job
    if job_min == 0.0 and job_max == 0.0:
        return True

    # Check for overlap:
    # Config: [min_sal, max_sal]
    # Job: [job_min, job_max]
    # Overlaps if job_max >= min_sal and (max_sal == 0 or job_min <= max_sal)
    if max_sal > 0:
        if job_max < min_sal or job_min > max_sal:
            return False
    else:
        if job_max < min_sal:
            return False

    return True

def filter_by_location(job: JobListing, locations: list[str]) -> bool:
    """
    Check if the job location matches the configured preferences.

    Matches cities, Remote, Hybrid, WFH.
    Case-insensitive substring match. If locations list is empty, returns True.
    """
    if not locations:
        return True

    job_loc_lower = job.location.lower()
    for loc in locations:
        loc_clean = loc.lower()
        if loc_clean in job_loc_lower:
            return True
            
        # Remote heuristics
        if loc_clean in ["remote", "work from home", "wfh"] and any(x in job_loc_lower for x in ["remote", "wfh", "home"]):
            return True

        # Hybrid heuristics
        if loc_clean == "hybrid" and "hybrid" in job_loc_lower:
            return True

    return False

def filter_by_blocklist(job: JobListing, blocked_companies: list[str]) -> bool:
    """
    Check if the job's company is in the blocklist.

    Case-insensitive substring match. Returns True if NOT blocked.
    """
    if not blocked_companies:
        return True

    company_lower = job.company.lower()
    for blocked in blocked_companies:
        if blocked.lower() in company_lower:
            return False
            
    return True

def apply_all_filters(job: JobListing, config: Config) -> Tuple[bool, str]:
    """
    Apply all filters to a job listing.

    Returns:
        Tuple of (passed, skip_reason).
    """
    # 1. Filter by company blocklist
    if not filter_by_blocklist(job, config.blocked_companies):
        return False, "company_blocked"

    # 2. Filter by keywords
    if not filter_by_keywords(job, config.keywords):
        return False, "keyword_mismatch"

    # 3. Filter by location
    if not filter_by_location(job, config.locations):
        return False, "location_mismatch"

    # 4. Filter by salary
    if not filter_by_salary(job, config.salary.min, config.salary.max):
        return False, "salary_out_of_range"

    return True, ""
