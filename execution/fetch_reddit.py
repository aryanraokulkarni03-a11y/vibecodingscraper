"""
Reddit Scraper - API

Fetches trending posts from startup-related subreddits using Reddit API.
Replaces X/Twitter as a source for startup discussions.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from rich.console import Console

from config import ScrapedItem, get_env, get_week_range, CONFIG, get_scraped_data_dir

console = Console()

# Subreddits focused on indie hackers and SaaS
TARGET_SUBREDDITS = [
    "SaaS",
    "indiehackers",
    "startups",
    "SideProject",
    "microsaas",
    "Entrepreneur",
    "nocode",
    "webdev",
]

REDDIT_API_BASE = "https://oauth.reddit.com"
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"


async def get_reddit_token() -> str | None:
    """Get Reddit OAuth token."""
    client_id = get_env("REDDIT_CLIENT_ID")
    client_secret = get_env("REDDIT_CLIENT_SECRET")
    user_agent = get_env("REDDIT_USER_AGENT", "VibeCodingTrendScraper/1.0")
    
    if not client_id or not client_secret:
        console.print("[yellow]⚠ Reddit API credentials not set, using public API[/]")
        return None
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            REDDIT_AUTH_URL,
            auth=(client_id, client_secret),
            headers={"User-Agent": user_agent},
            data={"grant_type": "client_credentials"}
        )
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            console.print(f"[red]Failed to get Reddit token: {response.status_code}[/]")
            return None


async def fetch_subreddit_posts(
    subreddit: str,
    token: str | None,
    limit: int = 25
) -> list[ScrapedItem]:
    """Fetch top posts from a subreddit."""
    items: list[ScrapedItem] = []
    user_agent = get_env("REDDIT_USER_AGENT", "VibeCodingTrendScraper/1.0")
    
    headers = {"User-Agent": user_agent}
    
    if token:
        base_url = REDDIT_API_BASE
        headers["Authorization"] = f"Bearer {token}"
    else:
        base_url = "https://www.reddit.com"
    
    url = f"{base_url}/r/{subreddit}/top.json"
    params = {"t": "week", "limit": limit}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            
        except httpx.HTTPError as e:
            console.print(f"[dim red]Error fetching r/{subreddit}: {e}[/]")
            return items
        
        posts = data.get("data", {}).get("children", [])
        
        for post in posts:
            post_data = post.get("data", {})
            
            # Skip stickied/mod posts
            if post_data.get("stickied"):
                continue
            
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")[:500]
            
            item = ScrapedItem(
                source="reddit",
                name=title,
                description=selftext if selftext else None,
                url=f"https://reddit.com{post_data.get('permalink', '')}",
                category=f"r/{subreddit}",
                score=post_data.get("score", 0),
                metadata={
                    "subreddit": subreddit,
                    "author": post_data.get("author"),
                    "num_comments": post_data.get("num_comments", 0),
                    "upvote_ratio": post_data.get("upvote_ratio", 0),
                    "created_utc": post_data.get("created_utc"),
                    "link_flair_text": post_data.get("link_flair_text"),
                }
            )
            items.append(item)
    
    return items


async def fetch_reddit_posts(max_per_sub: int = 25) -> list[ScrapedItem]:
    """
    Fetch trending posts from all target subreddits.
    
    Args:
        max_per_sub: Maximum posts per subreddit
        
    Returns:
        List of ScrapedItem objects
    """
    console.print("[bold blue]📱 Fetching Reddit posts...[/]")
    
    token = await get_reddit_token()
    all_items: list[ScrapedItem] = []
    
    # Get subreddits from config
    subreddits = CONFIG.get("reddit", {}).get("subreddits", [])
    if not subreddits:
        console.print("[yellow]⚠ No subreddits found in config, using defaults[/]")
        subreddits = ["SaaS", "indiehackers"]

    for subreddit in subreddits:
        console.print(f"[dim]  → r/{subreddit}[/]")
        items = await fetch_subreddit_posts(subreddit, token, max_per_sub)
        all_items.extend(items)
        await asyncio.sleep(1)  # Rate limiting
    
    # Sort by score
    all_items.sort(key=lambda x: x.score, reverse=True)
    
    console.print(f"[green]✓ Fetched {len(all_items)} posts from Reddit[/]")
    return all_items


async def save_results(items: list[ScrapedItem]) -> Path:
    """Save scraped items to JSON file."""
    output_path = get_scraped_data_dir() / f"reddit_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, indent=2, default=str)
    
    console.print(f"[dim]Saved to {output_path}[/]")
    return output_path


async def main():
    """Run the Reddit scraper."""
    items = await fetch_reddit_posts()
    await save_results(items)
    return items


if __name__ == "__main__":
    asyncio.run(main())
