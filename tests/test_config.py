"""
Unit tests for the config loader.
"""

from pathlib import Path
from src.core.config import load_config, Config

def test_load_default_config():
    """Verify that we can load the default configuration without issues."""
    config = load_config()
    assert isinstance(config, Config)
    assert len(config.keywords) > 0
    assert config.salary.min == 800000
    assert config.salary.max == 2500000
    assert config.salary.currency == "INR"
    assert config.dry_run is True  # Should default to True for safety
