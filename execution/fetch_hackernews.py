"""
Hacker News Scraper - Algolia API

Fetches "Show HN" and startup-related posts from Hacker News.
Uses the free Algolia API for reliable, fast access.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from rich.console import Console

from config import ScrapedItem, get_week_range, CONFIG, get_scraped_data_dir

console = Console()

ALGOLIA_API_URL = "https://hn.algolia.com/api/v1"


async def fetch_hackernews_posts(
    days_back: int = 7,
    max_items: int = 100
) -> list[ScrapedItem]:
    """
    Fetch Show HN and Launch HN posts from Hacker News.
    
    Args:
        days_back: Number of days to look back
        max_items: Maximum items to fetch
        
    Returns:
        List of ScrapedItem objects
    """
    console.print("[bold blue]📰 Fetching Hacker News posts...[/]")
    
    start_date, _ = get_week_range()
    timestamp = int(start_date.timestamp())
    
    items: list[ScrapedItem] = []
    
    # Search queries from config
    queries = CONFIG.get("hackernews", {}).get("queries", [])
    if not queries:
        queries = ["Show HN", "SaaS"]
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        for query in queries:
            try:
                response = await client.get(
                    f"{ALGOLIA_API_URL}/search",
                    params={
                        "query": query,
                        "tags": "story",
                        "numericFilters": f"created_at_i>{timestamp}",
                        "hitsPerPage": min(50, max_items // len(queries)),
                    }
                )
                response.raise_for_status()
                data = response.json()
                
            except httpx.HTTPError as e:
                console.print(f"[dim red]Error searching HN for '{query}': {e}[/]")
                continue
            
            hits = data.get("hits", [])
            console.print(f"[dim]  → '{query}': {len(hits)} hits[/]")
            
            for hit in hits:
                # Skip if too low points
                points = hit.get("points", 0)
                if points < 10:
                    continue
                
                title = hit.get("title", "")
                
                item = ScrapedItem(
                    source="hackernews",
                    name=title,
                    description=None,  # HN stories don't have descriptions
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    category="show-hn" if "show hn" in title.lower() else "hackernews",
                    score=points,
                    metadata={
                        "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                        "author": hit.get("author"),
                        "num_comments": hit.get("num_comments", 0),
                        "created_at": hit.get("created_at"),
                        "story_id": hit.get("objectID"),
                    }
                )
                items.append(item)
            
            await asyncio.sleep(0.5)  # Be nice to the API
    
    # Deduplicate by story_id
    seen = set()
    unique_items = []
    for item in items:
        story_id = item.metadata.get("story_id")
        if story_id and story_id not in seen:
            seen.add(story_id)
            unique_items.append(item)
    
    # Sort by score
    unique_items.sort(key=lambda x: x.score, reverse=True)
    
    console.print(f"[green]✓ Fetched {len(unique_items)} posts from Hacker News[/]")
    return unique_items[:max_items]


async def save_results(items: list[ScrapedItem]) -> Path:
    """Save scraped items to JSON file."""
    output_path = get_scraped_data_dir() / f"hackernews_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, indent=2, default=str)
    
    console.print(f"[dim]Saved to {output_path}[/]")
    return output_path


async def main():
    """Run the Hacker News scraper."""
    items = await fetch_hackernews_posts()
    await save_results(items)
    return items


if __name__ == "__main__":
    asyncio.run(main())
