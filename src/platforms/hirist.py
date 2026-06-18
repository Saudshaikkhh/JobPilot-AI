"""
Hirist platform adapter.

Handles:
- Session validation on Hirist (hirist.tech)
- Job searching on Hirist
- Easy click-to-apply process
"""

import logging
from typing import List
import urllib.parse

from playwright.async_api import Page

from src.core.config import Config
from src.platforms.base import BasePlatformAdapter, JobListing, ApplicationResult, ApplicationStatus
from src.browser.anti_detect import random_delay, human_click

logger = logging.getLogger("job_bot")

class HiristAdapter(BasePlatformAdapter):
    """Hirist platform adapter for automating applications."""

    @property
    def platform_name(self) -> str:
        return "hirist"

    async def validate_session(self, page: Page) -> bool:
        """Verify login status on Hirist."""
        try:
            logger.info("Validating Hirist session...")
            await page.goto("https://www.hirist.tech/", wait_until="domcontentloaded", timeout=30000)
            await random_delay(1500, 3000)

            current_url = page.url
            if "login" in current_url:
                logger.warning("Hirist session validation failed: Redirected to login page.")
                return False

            # Check if user profile initials, logout or dashboard navigation is visible
            profile_elem = page.locator(".profile-icon, .avatar, a[href*='dashboard'], a:has-text('Logout')").first
            if await profile_elem.count() > 0:
                logger.info("Hirist session validated successfully.")
                return True

            # Alternatively, evaluate cookies
            cookies = await page.context.cookies("https://www.hirist.tech")
            session_cookie = [c for c in cookies if c["name"] == "JSESSIONID"]
            if session_cookie:
                logger.info("Hirist session validated successfully (JSESSIONID present).")
                return True

            logger.warning("Hirist session validation failed: Logged-in markers not found.")
            return False
        except Exception as e:
            logger.error(f"Error validating Hirist session: {e}", exc_info=True)
            return False

    def get_search_url(self, keyword: str, location: str) -> str:
        """Build search URL for Hirist."""
        # Clean inputs for Hirist URL structure
        clean_kw = keyword.lower().replace(" ", "-")
        # e.g., https://www.hirist.tech/python-jobs.html
        base_url = f"https://www.hirist.tech/{clean_kw}-jobs.html"
        if location:
            # Add location filter as query parameter if URL path is not sufficient
            params = {"location": location}
            return base_url + "?" + urllib.parse.urlencode(params)
        return base_url

    async def search_jobs(self, page: Page, keyword: str, location: str) -> List[JobListing]:
        """Search jobs and extract listings on Hirist."""
        jobs: List[JobListing] = []
        try:
            search_url = self.get_search_url(keyword, location)
            logger.info(f"Searching Hirist jobs: {keyword}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
            await random_delay(2000, 4000)

            # Locate job cards
            job_cards = page.locator(".job-box, .job-listing, .jobTuple")
            card_count = await job_cards.count()
            logger.info(f"Found {card_count} job cards on Hirist")

            for i in range(card_count):
                card = job_cards.nth(i)
                try:
                    title_elem = card.locator(".job-title, .title, a[href*='view']").first
                    company_elem = card.locator(".company-name, .company, .subTitle").first
                    location_elem = card.locator(".location, .loc").first
                    salary_elem = card.locator(".salary, .sal").first

                    title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else ""
                    company = (await company_elem.inner_text()).strip() if await company_elem.count() > 0 else ""
                    loc = (await location_elem.inner_text()).strip() if await location_elem.count() > 0 else ""
                    sal = (await salary_elem.inner_text()).strip() if await salary_elem.count() > 0 else ""

                    # Get URL
                    link_elem = card.locator("a[href*='view']").first
                    if not await link_elem.count() > 0:
                        link_elem = card.locator("a").first
                        
                    if await link_elem.count() > 0:
                        raw_url = await link_elem.get_attribute("href")
                        url = urllib.parse.urljoin("https://www.hirist.tech", raw_url)
                    else:
                        continue

                    # Filter by location if specified and not matched
                    if location and location.lower() not in loc.lower():
                        continue

                    if title and url:
                        jobs.append(JobListing(
                            title=title,
                            company=company,
                            url=url,
                            location=loc,
                            salary=sal,
                            platform="hirist"
                        ))
                except Exception as card_err:
                    logger.warning(f"Error parsing Hirist job card {i}: {card_err}")
                    continue

            return jobs
        except Exception as e:
            logger.error(f"Error searching Hirist jobs: {e}", exc_info=True)
            return jobs

    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Apply to a job listing on Hirist."""
        try:
            logger.info(f"Navigating to Hirist job detail: {job.url}")
            await page.goto(job.url, wait_until="domcontentloaded", timeout=40000)
            await random_delay(2000, 4000)

            # Look for Apply button
            apply_button = page.locator("button:has-text('Apply'), a:has-text('Apply'), .apply-btn").first
            if not await apply_button.count() > 0 or not await apply_button.is_visible():
                return ApplicationResult(
                    status=ApplicationStatus.FAILED,
                    job=job,
                    message="Apply button not found or already applied."
                )

            button_text = await apply_button.inner_text()
            if "applied" in button_text.lower():
                return ApplicationResult(
                    status=ApplicationStatus.SKIPPED,
                    job=job,
                    message="Already applied."
                )

            logger.info("Clicking Hirist Apply button...")
            await apply_button.click()
            await random_delay(3000, 5000)

            # Check if there's any follow-up question modal
            modal = page.locator(".modal-dialog, .popup").first
            if await modal.count() > 0 and await modal.is_visible():
                # Try to submit the follow-up form if any
                submit_modal = modal.locator("button[type='submit'], button:has-text('Submit'), button:has-text('Apply')").first
                if await submit_modal.count() > 0:
                    await submit_modal.click()
                    await random_delay(2000, 3000)

            return ApplicationResult(
                status=ApplicationStatus.APPLIED,
                job=job,
                message="Applied successfully on Hirist."
            )

        except Exception as e:
            logger.error(f"Error applying to Hirist job {job.title}: {e}", exc_info=True)
            return ApplicationResult(
                status=ApplicationStatus.FAILED,
                job=job,
                message=f"Exception: {str(e)}"
            )
