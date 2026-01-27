"""
Database module for Vibe-Coding Scraper.
Tracks scraped items to prevent duplicates in weekly reports.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from config import PROJECT_ROOT, ScrapedItem

DB_PATH = PROJECT_ROOT / "scraper.db"


def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS scrap_history (
            url TEXT PRIMARY KEY,
            source TEXT,
            scraped_at TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def is_item_seen(url: str) -> bool:
    """Check if an item URL has been seen before."""
    if not url:
        return False
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM scrap_history WHERE url = ?', (url,))
    result = c.fetchone()
    conn.close()
    
    return result is not None


def add_item_to_history(item: ScrapedItem):
    """Add an item to the history."""
    if not item.url:
        return
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            'INSERT OR REPLACE INTO scrap_history (url, source, scraped_at) VALUES (?, ?, ?)',
            (item.url, item.source, datetime.now())
        )
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()


# Initialize on import
init_db()
