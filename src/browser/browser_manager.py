"""
Playwright browser lifecycle manager with stealth and session support.

Handles:
- Browser launch with stealth plugin
- Browser context creation with platform-specific cookies
- Session validation and health tracking
- Graceful shutdown
"""

import asyncio
import logging
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

from src.core.config import Config
from src.browser.anti_detect import get_random_user_agent, get_random_viewport

logger = logging.getLogger("job_bot")


def _get_linkedin_cookies(config: Config) -> list[dict]:
    """Build LinkedIn cookie list from config."""
    cookies = []

    def clean_val(val: str) -> str:
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        return val

    if config.cookies.li_at:
        cookies.append({
            "name": "li_at",
            "value": clean_val(config.cookies.li_at),
            "domain": ".linkedin.com",
            "path": "/",
        })
    if config.cookies.li_jsessionid:
        # JSESSIONID value is special - it MUST have double quotes in the cookie value itself
        val = clean_val(config.cookies.li_jsessionid)
        cookies.append({
            "name": "JSESSIONID",
            "value": f'"{val}"',
            "domain": ".linkedin.com",
            "path": "/",
        })
    return cookies


def _get_naukri_cookies(config: Config) -> list[dict]:
    """Build Naukri cookie list from config."""
    cookies = []
    if config.cookies.nauk_at:
        cookies.append({
            "name": "nauk_at",
            "value": config.cookies.nauk_at,
            "domain": ".naukri.com",
            "path": "/",
        })
    return cookies


def _get_indeed_cookies(config: Config) -> list[dict]:
    """Build Indeed cookie list from config."""
    cookies = []
    if config.cookies.indeed_jsessionid:
        cookies.append({
            "name": "JSESSIONID",
            "value": config.cookies.indeed_jsessionid,
            "domain": ".indeed.com",
            "path": "/",
        })
    if config.cookies.indeed_csrf_token:
        cookies.append({
            "name": "INDEED_CSRF_TOKEN",
            "value": config.cookies.indeed_csrf_token,
            "domain": ".indeed.com",
            "path": "/",
        })
    return cookies


def _get_hirist_cookies(config: Config) -> list[dict]:
    """Build Hirist cookie list from config."""
    cookies = []
    if config.cookies.hirist_jsessionid:
        cookies.append({
            "name": "JSESSIONID",
            "value": config.cookies.hirist_jsessionid,
            "domain": ".hirist.tech",
            "path": "/",
        })
    return cookies


# Map platform names to their cookie builders
PLATFORM_COOKIES = {
    "linkedin": _get_linkedin_cookies,
    "naukri": _get_naukri_cookies,
    "indeed": _get_indeed_cookies,
    "hirist": _get_hirist_cookies,
}


class BrowserManager:
    """
    Manages the Playwright browser lifecycle.

    Provides methods to launch the browser, create contexts with
    platform-specific cookies, and handle graceful shutdown.
    """

    def __init__(self, config: Config):
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._contexts: dict[str, BrowserContext] = {}

    async def launch(self) -> None:
        """
        Launch the Playwright browser with stealth plugin.

        Uses the browser type specified in config (chromium/firefox/webkit).
        Applies stealth patches to avoid bot detection.
        """
        logger.info("Launching browser (headless=%s)...", self.config.headless)

        if HAS_STEALTH:
            # Use stealth-patched playwright
            stealth = Stealth()
            self._playwright = await stealth.use_async(async_playwright()).__aenter__()
        else:
            logger.warning(
                "playwright-stealth not installed. Running without stealth patches. "
                "Install with: pip install playwright-stealth"
            )
            self._playwright = await async_playwright().__aenter__()

        # Select browser type
        browser_type = getattr(self._playwright, self.config.browser, self._playwright.chromium)

        # Launch with anti-detection args
        self._browser = await browser_type.launch(
            headless=self.config.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--window-size=1920,1080",
            ],
        )

        logger.info("Browser launched successfully (%s)", self.config.browser)

    async def create_context(self, platform: str) -> BrowserContext:
        """
        Create a browser context with platform-specific session cookies.

        Each platform gets its own isolated context (separate cookies, storage).

        Args:
            platform: Platform name ('linkedin', 'naukri', 'indeed', 'hirist').

        Returns:
            BrowserContext with session cookies injected.

        Raises:
            RuntimeError: If browser hasn't been launched.
            ValueError: If platform is not supported.
        """
        if not self._browser:
            raise RuntimeError("Browser not launched. Call launch() first.")

        if platform not in PLATFORM_COOKIES:
            raise ValueError(
                f"Unknown platform: '{platform}'. "
                f"Supported: {list(PLATFORM_COOKIES.keys())}"
            )

        # Create context with realistic browser fingerprint
        viewport = get_random_viewport()
        user_agent = get_random_user_agent()

        context = await self._browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            color_scheme="light",
            java_script_enabled=True,
            accept_downloads=True,
        )

        # Inject platform-specific cookies
        cookie_builder = PLATFORM_COOKIES[platform]
        cookies = cookie_builder(self.config)

        if cookies:
            await context.add_cookies(cookies)
            logger.debug(
                "Injected %d cookies for %s", len(cookies), platform
            )
        else:
            logger.warning(
                "No session cookies found for %s. "
                "Check your .env file.", platform
            )

        # Store context reference
        self._contexts[platform] = context
        return context

    async def get_page(self, platform: str) -> Page:
        """
        Get a new page in the platform's browser context.

        Creates the context if it doesn't exist yet.

        Args:
            platform: Platform name.

        Returns:
            A new Page in the platform's context.
        """
        if platform not in self._contexts:
            await self.create_context(platform)

        context = self._contexts[platform]
        page = await context.new_page()

        # Block unnecessary resource types to speed things up
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", lambda route: route.abort())

        return page

    async def close_context(self, platform: str) -> None:
        """Close a specific platform's browser context."""
        if platform in self._contexts:
            try:
                await self._contexts[platform].close()
                del self._contexts[platform]
                logger.debug("Closed context for %s", platform)
            except Exception as e:
                logger.warning("Error closing context for %s: %s", platform, e)

    async def close(self) -> None:
        """Gracefully close all contexts and the browser."""
        # Close all contexts
        for platform in list(self._contexts.keys()):
            await self.close_context(platform)

        # Close browser
        if self._browser:
            try:
                await self._browser.close()
                logger.debug("Browser closed")
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
            self._browser = None

        # Stop playwright
        if self._playwright:
            try:
                await self._playwright.__aexit__(None, None, None)
            except Exception:
                pass
            self._playwright = None

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
