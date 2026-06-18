"""
Standalone script to check session cookies connectivity.

Usage:
  python tests/run_connectivity_check.py
"""

import asyncio
import logging
import sys
import warnings
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Suppress warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

from src.core.config import load_config
from src.core.database import Database
from src.browser.browser_manager import BrowserManager
from src.platforms.registry import get_adapter, get_available_platforms

# Configure console logging for diagnostics
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("job_bot")

async def check_connectivity():
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Run in headed mode so we can see what causes redirects (e.g. security challenges)
    config.headless = False
    
    db = Database(config.db_path)
    
    print("\n" + "="*50)
    print("   LAUNCHING BROWSER DIAGNOSTICS...")
    print("="*50)
    
    async with BrowserManager(config) as browser_manager:
        platforms = get_available_platforms()
        results = {}
        
        for platform in platforms:
            print(f"Checking {platform.upper()} session status...")
            try:
                # Open isolated page context
                page = await browser_manager.get_page(platform)
                
                # Retrieve platform adapter
                adapter = get_adapter(platform, config)
                
                # Check session login status
                is_logged_in = await adapter.validate_session(page)
                results[platform] = is_logged_in
                
                # Update health database registry
                db.update_session_health(platform, is_logged_in)
                
            except Exception as e:
                logger.error(f"Error checking {platform}: {e}", exc_info=True)
                results[platform] = False
            finally:
                # Clean up this platform's context
                await browser_manager.close_context(platform)
        
        print("\n" + "="*50)
        print("         SESSION HEALTH & CONNECTIVITY SUMMARY")
        print("="*50)
        for platform, success in results.items():
            status = "AUTHENTICATED (OK)" if success else "EXPIRED / INVALID"
            print(f"  {platform.capitalize():12s} : {status}")
        print("="*50)
        print("Tip: If a platform status is EXPIRED, extract fresh cookies and update .env.\n")

if __name__ == "__main__":
    import io
    import gc
    from contextlib import redirect_stderr
    
    # Suppress stderr during cleanup to hide ResourceWarnings
    with redirect_stderr(io.StringIO()):
        asyncio.run(check_connectivity())
        gc.collect()  # Force garbage collection while stderr is redirected
