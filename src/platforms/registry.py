"""
Platform adapter registry.

Discovers, registers, and provides access to all platform adapters.
"""

from typing import Optional

from src.core.config import Config
from src.platforms.base import BasePlatformAdapter


# Import all adapters
from src.platforms.linkedin import LinkedInAdapter
from src.platforms.naukri import NaukriAdapter
from src.platforms.hirist import HiristAdapter
from src.platforms.indeed import IndeedAdapter


# Registry of all available adapters
_ADAPTER_CLASSES: dict[str, type[BasePlatformAdapter]] = {
    "linkedin": LinkedInAdapter,
    "naukri": NaukriAdapter,
    "hirist": HiristAdapter,
    "indeed": IndeedAdapter,
}


def get_adapter(platform_name: str, config: Config) -> BasePlatformAdapter:
    """
    Get an adapter instance for the specified platform.

    Args:
        platform_name: Platform name (e.g., 'linkedin').
        config: Application configuration.

    Returns:
        Instantiated adapter for the platform.

    Raises:
        ValueError: If platform is not registered.
    """
    platform_name = platform_name.lower()
    if platform_name not in _ADAPTER_CLASSES:
        available = ", ".join(_ADAPTER_CLASSES.keys())
        raise ValueError(
            f"Unknown platform: '{platform_name}'. Available: {available}"
        )
    return _ADAPTER_CLASSES[platform_name](config)


def get_all_adapters(config: Config) -> list[BasePlatformAdapter]:
    """
    Get adapter instances for all registered platforms.

    Args:
        config: Application configuration.

    Returns:
        List of all adapter instances.
    """
    return [cls(config) for cls in _ADAPTER_CLASSES.values()]


def get_available_platforms() -> list[str]:
    """Get a list of all registered platform names."""
    return list(_ADAPTER_CLASSES.keys())
