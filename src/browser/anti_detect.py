"""
Human-like behavior simulation for anti-detection.

Provides utilities to make Playwright automation look like real human interaction:
- Random delays between actions
- Smooth mouse movements with natural curves
- Human-like scrolling patterns
- Realistic typing with variable speed
"""

import asyncio
import math
import random
from typing import Optional

from playwright.async_api import Page


async def random_delay(min_ms: int = 1500, max_ms: int = 4000) -> None:
    """
    Wait for a random duration to simulate human thinking/reading time.

    Args:
        min_ms: Minimum delay in milliseconds.
        max_ms: Maximum delay in milliseconds.
    """
    delay = random.randint(min_ms, max_ms)
    await asyncio.sleep(delay / 1000.0)


async def short_delay() -> None:
    """Quick delay for between rapid human actions (300-800ms)."""
    await asyncio.sleep(random.uniform(0.3, 0.8))


async def micro_delay() -> None:
    """Tiny delay for between keystrokes (50-200ms)."""
    await asyncio.sleep(random.uniform(0.05, 0.2))


async def human_scroll(
    page: Page,
    direction: str = "down",
    distance: Optional[int] = None,
    smooth: bool = True,
) -> None:
    """
    Scroll the page with human-like behavior.

    Args:
        page: Playwright page object.
        direction: 'down' or 'up'.
        distance: Pixels to scroll. Random if None.
        smooth: Whether to scroll in small increments.
    """
    if distance is None:
        distance = random.randint(200, 600)

    if direction == "up":
        distance = -distance

    if smooth:
        # Scroll in small increments for natural feel
        steps = random.randint(3, 7)
        step_size = distance // steps
        for i in range(steps):
            await page.mouse.wheel(0, step_size)
            await asyncio.sleep(random.uniform(0.05, 0.15))
    else:
        await page.mouse.wheel(0, distance)

    await short_delay()


async def human_click(page: Page, selector: str, timeout: int = 10000) -> None:
    """
    Click an element with human-like mouse movement.

    Moves the mouse to the element location with a slight offset,
    waits briefly, then clicks.

    Args:
        page: Playwright page object.
        selector: CSS selector or Playwright selector for the element.
        timeout: Maximum wait time for element to be visible (ms).
    """
    element = page.locator(selector).first
    await element.wait_for(state="visible", timeout=timeout)

    # Get element bounding box
    box = await element.bounding_box()
    if box:
        # Click slightly off-center (humans don't click perfect center)
        offset_x = random.uniform(-box["width"] * 0.2, box["width"] * 0.2)
        offset_y = random.uniform(-box["height"] * 0.2, box["height"] * 0.2)

        target_x = box["x"] + box["width"] / 2 + offset_x
        target_y = box["y"] + box["height"] / 2 + offset_y

        # Move mouse with natural curve
        await _move_mouse_naturally(page, target_x, target_y)
        await micro_delay()
        await page.mouse.click(target_x, target_y)
    else:
        # Fallback: direct click
        await element.click()

    await short_delay()


async def human_type(
    page: Page,
    selector: str,
    text: str,
    clear_first: bool = True,
) -> None:
    """
    Type text into an input field with human-like speed variations.

    Args:
        page: Playwright page object.
        selector: CSS selector for the input element.
        text: Text to type.
        clear_first: Whether to clear the field before typing.
    """
    element = page.locator(selector).first
    await element.wait_for(state="visible")

    if clear_first:
        await element.click()
        await page.keyboard.press("Control+A")
        await micro_delay()
        await page.keyboard.press("Backspace")
        await micro_delay()

    # Type character by character with variable delays
    for char in text:
        await element.type(char, delay=random.randint(50, 150))

    await short_delay()


async def human_fill(page: Page, selector: str, value: str) -> None:
    """
    Fill an input field (faster than human_type, for non-critical fields).

    Args:
        page: Playwright page object.
        selector: CSS selector for the input element.
        value: Value to fill.
    """
    element = page.locator(selector).first
    await element.wait_for(state="visible")
    await element.click()
    await micro_delay()
    await element.fill(value)
    await short_delay()


async def scroll_into_view(page: Page, selector: str) -> None:
    """
    Scroll an element into view with natural scrolling.

    Args:
        page: Playwright page object.
        selector: CSS selector for the target element.
    """
    element = page.locator(selector).first
    await element.scroll_into_view_if_needed()
    await short_delay()


async def random_mouse_movement(page: Page) -> None:
    """
    Perform a random mouse movement to simulate idle human behavior.

    Args:
        page: Playwright page object.
    """
    viewport = page.viewport_size
    if viewport:
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await _move_mouse_naturally(page, x, y)


async def _move_mouse_naturally(
    page: Page,
    target_x: float,
    target_y: float,
    steps: int = 0,
) -> None:
    """
    Move the mouse in a natural curve to the target position.

    Uses Bézier-like interpolation for smooth, human-like movement.

    Args:
        page: Playwright page object.
        target_x: Target X coordinate.
        target_y: Target Y coordinate.
        steps: Number of intermediate steps. 0 = auto-calculate.
    """
    # Get current mouse position (approximate via viewport center if unknown)
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    current_x = random.uniform(viewport["width"] * 0.3, viewport["width"] * 0.7)
    current_y = random.uniform(viewport["height"] * 0.3, viewport["height"] * 0.7)

    # Calculate distance and auto-determine steps
    dist = math.sqrt((target_x - current_x) ** 2 + (target_y - current_y) ** 2)
    if steps == 0:
        steps = max(5, int(dist / 50))

    # Generate control point for Bézier curve (adds natural wobble)
    ctrl_x = (current_x + target_x) / 2 + random.uniform(-100, 100)
    ctrl_y = (current_y + target_y) / 2 + random.uniform(-50, 50)

    for i in range(steps + 1):
        t = i / steps
        # Quadratic Bézier interpolation
        x = (1 - t) ** 2 * current_x + 2 * (1 - t) * t * ctrl_x + t ** 2 * target_x
        y = (1 - t) ** 2 * current_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * target_y

        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.02))


def get_random_viewport() -> dict:
    """
    Get a random but realistic viewport size.

    Returns:
        Dict with 'width' and 'height' keys.
    """
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720},
        {"width": 1600, "height": 900},
    ]
    return random.choice(viewports)


def get_random_user_agent() -> str:
    """
    Get a random but realistic Chrome user agent string.

    Returns:
        User agent string.
    """
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)
