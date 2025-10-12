# core/config.py

"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Google Search API"
    app_version: str = "1.0.0"
    debug: bool = False

    # API Settings
    api_prefix: str = "/api"
    host: str = "0.0.0.0"
    port: int = 8000

    # Scraper Settings
    default_max_results: int = 20
    default_headless: bool = True
    default_profile_name: str = "api_google_profile"

    # Delay Settings
    min_delay_seconds: int = 5
    max_delay_seconds: int = 10

    # Directory Settings
    results_dir: str = "results"
    screenshots_dir: str = "results/screenshots"
    errors_dir: str = "results/errors"
    debug_dir: str = "results/debug"
    profiles_dir: str = "browser_profiles"

    class Config:
        env_prefix = "SEARCH_API_"
        case_sensitive = False


settings = Settings()