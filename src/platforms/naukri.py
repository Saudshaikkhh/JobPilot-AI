"""
Naukri platform adapter.

Handles:
- Session validation on Naukri
- Job searching on Naukri
- Internal quick apply automation
"""

import logging
from typing import List
import urllib.parse

from playwright.async_api import Page

from src.core.config import Config
from src.platforms.base import BasePlatformAdapter, JobListing, ApplicationResult, ApplicationStatus
from src.browser.anti_detect import random_delay, human_click, short_delay

logger = logging.getLogger("job_bot")

class NaukriAdapter(BasePlatformAdapter):
    """Naukri platform adapter for automating applications."""

    @property
    def platform_name(self) -> str:
        return "naukri"

    async def validate_session(self, page: Page) -> bool:
        """Verify Naukri login status using mnjuser homepage."""
        try:
            logger.info("Validating Naukri session...")
            await page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=30000)
            await random_delay(1500, 3000)

            current_url = page.url
            if "login" in current_url or "register" in current_url:
                logger.warning("Naukri session validation failed: Redirected to login/register page.")
                return False

            # Check if profile elements exist
            profile_elem = page.locator(".profile-summary, .userName, .profile-percent")
            if await profile_elem.count() > 0:
                logger.info("Naukri session validated successfully.")
                return True

            # Alternatively, check page title or url for redirect from profile page
            if "naukri.com/mnjuser" in current_url or "naukri.com/profile" in current_url:
                logger.info("Naukri session validated successfully (profile URL match).")
                return True

            logger.warning("Naukri session validation failed: Logged-in markers not found.")
            return False
        except Exception as e:
            logger.error(f"Error validating Naukri session: {e}", exc_info=True)
            return False

    def get_search_url(self, keyword: str, location: str) -> str:
        """Build search URL for Naukri."""
        # Convert keyword and location to URL-friendly slugs if needed,
        # or use standard query parameters.
        clean_kw = keyword.lower().replace(" ", "-")
        clean_loc = location.lower().replace(" ", "-")
        
        # Naukri URL pattern: https://www.naukri.com/python-developer-jobs-in-bangalore
        base_url = f"https://www.naukri.com/{clean_kw}-jobs-in-{clean_loc}?"
        params = {
            "k": keyword,
            "l": location,
            "experience": self.config.profile.experience_years
        }
        return base_url + urllib.parse.urlencode(params)

    async def search_jobs(self, page: Page, keyword: str, location: str) -> List[JobListing]:
        """Search jobs and extract listing cards on Naukri."""
        jobs: List[JobListing] = []
        try:
            search_url = self.get_search_url(keyword, location)
            logger.info(f"Searching Naukri jobs: {keyword} in {location}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
            await random_delay(2000, 4000)

            # Paginate through top 2 pages
            for page_num in range(2):
                logger.info(f"Processing Naukri page {page_num + 1}...")
                
                # Locate job article cards
                job_cards = page.locator("article.jobTuple, [class*='srp-jobtuple']")
                card_count = await job_cards.count()
                logger.info(f"Found {card_count} job cards on page {page_num + 1}")
                
                for i in range(card_count):
                    card = job_cards.nth(i)
                    try:
                        title_elem = card.locator("a.title, [class*='title']")
                        company_elem = card.locator("a.subTitle, [class*='company-name']")
                        location_elem = card.locator(".locWdth, [class*='loc']")
                        salary_elem = card.locator(".salary, [class*='sal']")

                        title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else ""
                        company = (await company_elem.inner_text()).strip() if await company_elem.count() > 0 else ""
                        loc = (await location_elem.inner_text()).strip() if await location_elem.count() > 0 else ""
                        sal = (await salary_elem.inner_text()).strip() if await salary_elem.count() > 0 else ""
                        
                        link_elem = card.locator("a.title, a[class*='title']").first
                        if await link_elem.count() > 0:
                            raw_url = await link_elem.get_attribute("href")
                            url = urllib.parse.urljoin("https://www.naukri.com", raw_url)
                        else:
                            continue

                        if title and url:
                            jobs.append(JobListing(
                                title=title,
                                company=company,
                                url=url,
                                location=loc,
                                salary=sal,
                                platform="naukri"
                            ))
                    except Exception as card_err:
                        logger.warning(f"Error parsing Naukri job card {i}: {card_err}")
                        continue

                # Go to next page if possible
                if page_num < 1:
                    next_button = page.locator(".styles_btn-group-container__25c5Z button:has-text('Next')").first
                    # Alternate selectors
                    if not (await next_button.count() > 0 and await next_button.is_visible()):
                        next_button = page.locator("a.next, a:has-text('Next')").first

                    if await next_button.count() > 0 and await next_button.is_visible():
                        await next_button.click()
                        await random_delay(2000, 4000)
                    else:
                        logger.info("Naukri next page button not found or visible. Ending search pagination.")
                        break
                        
            return jobs
        except Exception as e:
            logger.error(f"Error searching Naukri jobs: {e}", exc_info=True)
            return jobs

    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Apply to a Naukri job."""
        try:
            logger.info(f"Navigating to Naukri job detail: {job.url}")
            await page.goto(job.url, wait_until="domcontentloaded", timeout=40000)
            await random_delay(2000, 4000)

            # Check if we are already applied or need external redirection
            apply_button = page.locator("button.apply-button, button#apply-button, .apply-button-container button").first
            if not await apply_button.count() > 0:
                # Try finding button by text
                apply_button = page.locator("button:has-text('Apply'), button:has-text('Apply Now')").first

            if not await apply_button.count() > 0 or not await apply_button.is_visible():
                # Check if it displays "Applied" already
                already_applied = page.locator(".applied-status, button:has-text('Applied')").first
                if await already_applied.count() > 0:
                    return ApplicationResult(
                        status=ApplicationStatus.SKIPPED,
                        job=job,
                        message="Already applied."
                    )
                return ApplicationResult(
                    status=ApplicationStatus.FAILED,
                    job=job,
                    message="Apply button not found or visible."
                )

            button_text = await apply_button.inner_text()
            if "apply on company site" in button_text.lower():
                logger.info("External company site apply found. Skipping external redirect for now.")
                return ApplicationResult(
                    status=ApplicationStatus.SKIPPED,
                    job=job,
                    message="Requires applying externally on company site."
                )

            logger.info("Clicking Naukri Apply button...")
            await apply_button.click()
            await random_delay(3000, 5000)

            # Check for chatbot/chat overlay popups or question forms
            chatbot_close = page.locator(".chatbot-header .close, .chat-close, .modal-close").first
            if await chatbot_close.count() > 0 and await chatbot_close.is_visible():
                logger.info("Closing Naukri apply chatbot/modal popup...")
                await chatbot_close.click()
                await random_delay(500, 1000)

            # Confirm if quick apply went through
            # Usually the apply button text changes to "Applied" or a success banner appears
            # Let's re-locate the button to see if it changed
            try:
                apply_button_updated = page.locator("button.apply-button, .apply-button-container button").first
                if await apply_button_updated.count() > 0:
                    updated_text = await apply_button_updated.inner_text()
                    if "applied" in updated_text.lower():
                        return ApplicationResult(
                            status=ApplicationStatus.APPLIED,
                            job=job,
                            message="Applied successfully (button text updated to Applied)."
                        )
            except Exception:
                pass

            # Check if there is an error message on the page
            error_selector = page.locator(".error-msg, .error-message").first
            if await error_selector.count() > 0 and await error_selector.is_visible():
                err_text = await error_selector.inner_text()
                return ApplicationResult(
                    status=ApplicationStatus.FAILED,
                    job=job,
                    message=f"Error message visible after click: {err_text.strip()}"
                )

            # Assume success if no error is obvious and we successfully clicked
            return ApplicationResult(
                status=ApplicationStatus.APPLIED,
                job=job,
                message="Applied successfully (clicked Apply and closed overlay)."
            )

        except Exception as e:
            logger.error(f"Error applying to Naukri job {job.title}: {e}", exc_info=True)
            return ApplicationResult(
                status=ApplicationStatus.FAILED,
                job=job,
                message=f"Exception: {str(e)}"
            )
