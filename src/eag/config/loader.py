"""Configuration loading for EAG."""

from functools import lru_cache

from eag.config.settings import Settings


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load and validate EAG settings."""
    return Settings()
