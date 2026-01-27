"""
Shared configuration and utilities for all scrapers.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import TypeVar, Generic
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Paths
# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def get_output_dir() -> Path:
    """Get the directory for today's output (YYYYMMDD)."""
    today = datetime.now().strftime("%Y%m%d")
    output_dir = TMP_DIR / today
    output_dir.mkdir(exist_ok=True)
    return output_dir

def get_scraped_data_dir() -> Path:
    """Get the directory for raw scraped data (browser reports)."""
    d = get_output_dir() / "scraped_data"
    d.mkdir(exist_ok=True)
    return d

def get_reports_dir() -> Path:
    """Get the directory for generated reports."""
    d = get_output_dir() / "reports"
    d.mkdir(exist_ok=True)
    return d

# Load Config
import yaml

def load_config() -> dict:
    """Load configuration from config.yaml."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Global Config Object
try:
    CONFIG = load_config()
except Exception as e:
    print(f"Warning: Could not load config.yaml: {e}")
    CONFIG = {}

# Time range for weekly scraping
def get_week_range() -> tuple[datetime, datetime]:
    """Get the date range for the past week."""
    end = datetime.now()
    start = end - timedelta(days=7)
    return start, end


class ScrapedItem(BaseModel):
    """Base model for all scraped items."""
    source: str
    name: str
    description: str | None = None
    url: str | None = None
    category: str | None = None
    score: int = 0  # Upvotes, points, etc.
    scraped_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class TrendReport(BaseModel):
    """Aggregated trend report from AI analysis."""
    generated_at: datetime = Field(default_factory=datetime.now)
    week_start: datetime
    week_end: datetime
    total_items: int
    top_opportunities: list[dict] = Field(default_factory=list)
    trending_categories: list[str] = Field(default_factory=list)
    ai_summary: str = ""
    vibe_code_picks: list[dict] = Field(default_factory=list)


# Environment helpers
def get_env(key: str, default: str | None = None, required: bool = False) -> str | None:
    """Get environment variable with optional requirement check."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


# Rate limiting helper
import asyncio
from functools import wraps

def rate_limit(seconds: float = 2.0):
    """Decorator to add delay between calls for respectful scraping."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await asyncio.sleep(seconds)
            return result
        return wrapper
    return decorator
