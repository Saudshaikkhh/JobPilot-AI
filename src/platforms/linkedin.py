"""
LinkedIn platform adapter.

Handles:
- Session validation on LinkedIn
- Job searching with Easy Apply filter
- Multi-step Easy Apply application filling and submission
"""

import logging
from typing import List
import urllib.parse

from playwright.async_api import Page, Locator

from src.core.config import Config
from src.platforms.base import BasePlatformAdapter, JobListing, ApplicationResult, ApplicationStatus
from src.browser.anti_detect import random_delay, human_click, human_fill, human_type, short_delay, scroll_into_view

logger = logging.getLogger("job_bot")

class LinkedInAdapter(BasePlatformAdapter):
    """LinkedIn platform adapter for automating job applications."""

    @property
    def platform_name(self) -> str:
        return "linkedin"

    async def validate_session(self, page: Page) -> bool:
        """Verify if the user is authenticated by navigating to feed."""
        try:
            logger.info("Validating LinkedIn session...")
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            await random_delay(1500, 3000)
            
            current_url = page.url
            page_title = await page.title()
            logger.info(f"Loaded page URL: {current_url} | Title: {page_title}")
            
            # If the URL contains "feed", the session is active and we are logged in!
            if "/feed" in current_url:
                logger.info("LinkedIn session validated successfully (URL contains '/feed').")
                return True
                
            # If redirected to login, signup, or challenge checkpoints
            if "login" in current_url or "signup" in current_url or "checkpoint" in current_url:
                logger.warning("LinkedIn session validation failed: redirected to login/signup/checkpoint.")
                return False
                
            logger.warning("LinkedIn session validation status uncertain.")
            return False
        except Exception as e:
            logger.error(f"Error validating LinkedIn session: {e}", exc_info=True)
            return False

    def get_search_url(self, keyword: str, location: str) -> str:
        """Build search URL for LinkedIn jobs with Easy Apply filter."""
        base_url = "https://www.linkedin.com/jobs/search/?"
        params = {
            "keywords": keyword,
            "location": location,
            "f_AL": "true",  # Easy Apply filter
            "f_TPR": f"r{self.config.posted_within_days * 86400}",  # Convert days to seconds
            "sortBy": "DD",  # Sort by date
            "start": 0
        }
        return base_url + urllib.parse.urlencode(params)

    async def search_jobs(self, page: Page, keyword: str, location: str) -> List[JobListing]:
        """Search jobs and extract listing metadata."""
        jobs: List[JobListing] = []
        try:
            search_url = self.get_search_url(keyword, location)
            logger.info(f"Searching LinkedIn jobs: {keyword} in {location}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
            await random_delay(2000, 4000)

            # Paginate through top 2 pages
            for page_num in range(2):
                logger.info(f"Processing search results page {page_num + 1}...")
                
                # Scroll search panel to trigger lazy-loading of job cards
                search_panel = page.locator(".jobs-search-results-list")
                if await search_panel.count() > 0:
                    await human_scroll(page, direction="down", distance=400, smooth=True)
                    await random_delay(1000, 2000)
                    await human_scroll(page, direction="down", distance=400, smooth=True)
                    await random_delay(1000, 2000)
                
                # Locate job cards
                job_cards = page.locator(".job-card-container--clickable, [data-job-id]")
                card_count = await job_cards.count()
                logger.info(f"Found {card_count} job cards on page {page_num + 1}")
                
                for i in range(card_count):
                    card = job_cards.nth(i)
                    try:
                        # Extract basic info from the card
                        title_elem = card.locator(".job-card-list__title, .disabled.ember-view")
                        company_elem = card.locator(".job-card-container__primary-description, .job-card-container__company-name")
                        location_elem = card.locator(".job-card-container__metadata-item")
                        
                        title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else ""
                        company = (await company_elem.inner_text()).strip() if await company_elem.count() > 0 else ""
                        loc = (await location_elem.first.inner_text()).strip() if await location_elem.count() > 0 else ""
                        
                        # Get URL or job ID
                        job_id = await card.get_attribute("data-job-id")
                        if job_id:
                            url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                        else:
                            link_elem = card.locator("a.job-card-list__title, a.job-card-container__link")
                            if await link_elem.count() > 0:
                                raw_url = await link_elem.first.get_attribute("href")
                                url = urllib.parse.urljoin("https://www.linkedin.com", raw_url)
                            else:
                                continue

                        if title and url:
                            jobs.append(JobListing(
                                title=title,
                                company=company,
                                url=url,
                                location=loc,
                                platform="linkedin"
                            ))
                    except Exception as card_err:
                        logger.warning(f"Error parsing job card {i}: {card_err}")
                        continue

                # Go to next page if possible
                if page_num < 1:
                    next_button = page.locator(f"button[aria-label='Page {page_num + 2}']")
                    if await next_button.count() > 0 and await next_button.is_visible():
                        await human_click(page, f"button[aria-label='Page {page_num + 2}']")
                        await random_delay(2000, 4000)
                    else:
                        logger.info("No next page button found or not visible. Ending search pagination.")
                        break
                        
            return jobs
        except Exception as e:
            logger.error(f"Error searching LinkedIn jobs: {e}", exc_info=True)
            return jobs

    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Handle LinkedIn Easy Apply process."""
        try:
            logger.info(f"Navigating to job details: {job.url}")
            await page.goto(job.url, wait_until="domcontentloaded", timeout=40000)
            await random_delay(2000, 4000)

            # Look for Easy Apply button
            apply_button = page.get_by_role("button", name="Easy Apply", exact=False).first
            if not await apply_button.count() > 0 or not await apply_button.is_visible():
                # Try locating by class or selector if get_by_role fails
                apply_button = page.locator("button.jobs-apply-button").first
                if not await apply_button.count() > 0 or not await apply_button.is_visible():
                    return ApplicationResult(
                        status=ApplicationStatus.FAILED,
                        job=job,
                        message="Easy Apply button not found or already applied."
                    )

            logger.info("Easy Apply button found. Clicking to open application modal...")
            await apply_button.click()
            await random_delay(1500, 3000)

            # Process modal pages
            modal = page.locator("[role='dialog'], .artdeco-modal")
            if not await modal.count() > 0:
                return ApplicationResult(
                    status=ApplicationStatus.FAILED,
                    job=job,
                    message="Easy Apply modal did not open."
                )

            max_steps = 10
            step = 0
            
            while step < max_steps:
                step += 1
                logger.info(f"Processing application step {step}...")
                
                # Check for error messages displayed
                errors = modal.locator(".artdeco-inline-feedback--error")
                if await errors.count() > 0:
                    err_msg = await errors.first.inner_text()
                    logger.warning(f"Validation error encountered on step {step}: {err_msg.strip()}")
                    # Since it requires manual resolution, we cancel
                    await self._dismiss_modal(page, modal)
                    return ApplicationResult(
                        status=ApplicationStatus.FAILED,
                        job=job,
                        message=f"Form validation failed: {err_msg.strip()}"
                    )

                # Attempt to fill standard form fields on current screen
                await self._fill_form_fields(page, modal)
                await random_delay(1000, 2000)

                # Check if "Submit application" is available
                submit_button = modal.get_by_role("button", name="Submit application", exact=False).first
                if await submit_button.count() > 0 and await submit_button.is_visible():
                    logger.info("Submit application button found. Submitting...")
                    await submit_button.click()
                    await random_delay(3000, 5000)
                    
                    # Confirm submission
                    done_button = modal.get_by_role("button", name="Done", exact=False).first
                    if await done_button.count() > 0:
                        await done_button.click()
                        await random_delay(1000, 2000)
                    else:
                        # Sometimes modal auto-closes or has close button
                        await self._dismiss_modal(page, modal)

                    return ApplicationResult(
                        status=ApplicationStatus.APPLIED,
                        job=job,
                        message="Application submitted successfully."
                    )

                # Check for "Next" or "Review" button
                next_button = modal.get_by_role("button", name="Next", exact=False).first
                if not (await next_button.count() > 0 and await next_button.is_visible()):
                    next_button = modal.get_by_role("button", name="Review", exact=False).first
                    
                if await next_button.count() > 0 and await next_button.is_visible():
                    logger.info("Clicking Next/Review button to proceed...")
                    await next_button.click()
                    await random_delay(1500, 2500)
                else:
                    logger.warning("Neither Next nor Submit button was found/visible.")
                    await self._dismiss_modal(page, modal)
                    return ApplicationResult(
                        status=ApplicationStatus.FAILED,
                        job=job,
                        message="Stuck on form wizard: No next button."
                    )

            await self._dismiss_modal(page, modal)
            return ApplicationResult(
                status=ApplicationStatus.FAILED,
                job=job,
                message="Exceeded max steps in form wizard."
            )

        except Exception as e:
            logger.error(f"Error applying to LinkedIn job {job.title}: {e}", exc_info=True)
            return ApplicationResult(
                status=ApplicationStatus.FAILED,
                job=job,
                message=f"Exception: {str(e)}"
            )

    async def _dismiss_modal(self, page: Page, modal: Locator) -> None:
        """Close modal and discard draft if needed."""
        try:
            close_btn = modal.locator("button[aria-label='Dismiss'], button[data-test-modal-close-btn]").first
            if await close_btn.count() > 0:
                await close_btn.click()
                await random_delay(800, 1500)
                
                # Check for "Discard" button confirmation dialog
                discard_btn = page.locator("button[data-test-dialog-secondary-btn], button:has-text('Discard')").first
                if await discard_btn.count() > 0 and await discard_btn.is_visible():
                    await discard_btn.click()
                    await random_delay(800, 1500)
        except Exception as e:
            logger.debug(f"Non-critical: Error dismissing modal: {e}")

    async def _fill_form_fields(self, page: Page, modal: Locator) -> None:
        """Detect and fill inputs in the modal."""
        # 1. Handle file inputs (resume)
        file_inputs = modal.locator("input[type='file']")
        file_count = await file_inputs.count()
        for i in range(file_count):
            inp = file_inputs.nth(i)
            if await inp.is_visible():
                resume_abs = self.config.resume_absolute_path
                if resume_abs.exists():
                    logger.info(f"Uploading resume from {resume_abs}")
                    await inp.set_input_files(resume_abs)
                    await random_delay(2000, 4000)
                else:
                    logger.warning(f"Resume file not found at path: {resume_abs}")

        # 2. Handle text inputs
        text_inputs = modal.locator("input[type='text'], textarea")
        text_count = await text_inputs.count()
        for i in range(text_count):
            inp = text_inputs.nth(i)
            if not await inp.is_visible() or await inp.is_disabled():
                continue
            
            # Check if input is already filled
            val = await inp.input_value()
            if val.strip():
                continue

            # Read label to guess field type
            label_text = ""
            # Try finding label by matching ID/for or parent
            inp_id = await inp.get_attribute("id")
            if inp_id:
                label = modal.locator(f"label[for='{inp_id}']")
                if await label.count() > 0:
                    label_text = await label.inner_text()
            if not label_text:
                # Try finding label via parent element text
                parent = inp.locator("..")
                label_text = await parent.inner_text()

            label_clean = label_text.lower()
            
            # Answer heuristic based on labels
            if "experience" in label_clean or "years" in label_clean:
                await human_fill(page, f"input[id='{inp_id}']" if inp_id else inp, str(self.config.profile.experience_years))
            elif "phone" in label_clean or "mobile" in label_clean:
                if self.config.profile.phone:
                    await human_fill(page, f"input[id='{inp_id}']" if inp_id else inp, self.config.profile.phone)
            elif "notice" in label_clean or "days" in label_clean:
                await human_fill(page, f"input[id='{inp_id}']" if inp_id else inp, self.config.profile.notice_period)
            else:
                # Default fallback
                await human_fill(page, f"input[id='{inp_id}']" if inp_id else inp, "0")

        # 3. Handle radio buttons/checkboxes (simple selection of first option if not chosen)
        radios = modal.locator("input[type='radio']")
        radios_count = await radios.count()
        if radios_count > 0:
            # Group radios by name
            radio_groups = {}
            for i in range(radios_count):
                r = radios.nth(i)
                name = await r.get_attribute("name")
                if name:
                    radio_groups.setdefault(name, []).append(r)
            
            for group_name, buttons in radio_groups.items():
                # Check if any button in the group is checked
                checked = False
                for btn in buttons:
                    if await btn.is_checked():
                        checked = True
                        break
                if not checked and buttons:
                    # Select the first option (often 'Yes')
                    logger.debug(f"Selecting default option for radio group '{group_name}'")
                    await buttons[0].click()
                    await random_delay(500, 1000)
