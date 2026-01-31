"""
Bluesky Scraper - AT Protocol API

Fetches posts from Bluesky related to #buildinpublic and startup hashtags.
Uses the public AT Protocol API.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
from rich.console import Console

from config import ScrapedItem, get_week_range, get_env, get_scraped_data_dir, get_date_str, CONFIG

console = Console()

BLUESKY_API_URL = "https://bsky.social/xrpc"


async def get_bluesky_session() -> dict | None:
    """Authenticate with Bluesky and get session token."""
    handle = get_env("BLUESKY_HANDLE")
    password = get_env("BLUESKY_APP_PASSWORD")
    
    if not handle or not password:
        console.print("[yellow]⚠ Bluesky credentials not set, skipping[/]")
        return None
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BLUESKY_API_URL}/com.atproto.server.createSession",
                json={"identifier": handle, "password": password}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            console.print(f"[red]Bluesky auth failed: {e}[/]")
            return None


async def search_bluesky_posts(
    session: dict,
    query: str,
    limit: int = 25
) -> list[ScrapedItem]:
    """Search for posts on Bluesky."""
    items: list[ScrapedItem] = []
    
    headers = {"Authorization": f"Bearer {session.get('accessJwt', '')}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Use public search endpoint
            response = await client.get(
                f"{BLUESKY_API_URL}/app.bsky.feed.searchPosts",
                headers=headers,
                params={"q": query, "limit": limit},
                timeout=15.0
            )
            
            if response.status_code == 400:
                # Search might not be available, try actor feed
                console.print(f"[dim]Search not available for '{query}'[/]")
                return items
            
            response.raise_for_status()
            data = response.json()
            
        except httpx.HTTPError as e:
            console.print(f"[dim red]Error searching Bluesky for '{query}': {e}[/]")
            return items
        
        posts = data.get("posts", [])
        
        for post in posts:
            record = post.get("record", {})
            text = record.get("text", "")
            
            # Extract author
            author = post.get("author", {})
            handle = author.get("handle", "")
            display_name = author.get("displayName", handle)
            
            # Get engagement metrics
            like_count = post.get("likeCount", 0)
            repost_count = post.get("repostCount", 0)
            reply_count = post.get("replyCount", 0)
            
            item = ScrapedItem(
                source="bluesky",
                name=f"{display_name}: {text[:100]}..." if len(text) > 100 else f"{display_name}: {text}",
                description=text,
                url=f"https://bsky.app/profile/{handle}/post/{post.get('uri', '').split('/')[-1]}",
                category="buildinpublic",
                score=like_count + repost_count,
                metadata={
                    "author_handle": handle,
                    "author_name": display_name,
                    "likes": like_count,
                    "reposts": repost_count,
                    "replies": reply_count,
                    "created_at": record.get("createdAt"),
                }
            )
            items.append(item)
    
    return items


async def fetch_bluesky_posts(max_items: int = 100) -> list[ScrapedItem]:
    """
    Fetch relevant posts from Bluesky.
    
    Args:
        max_items: Maximum items to fetch
        
    Returns:
        List of ScrapedItem objects
    """
    console.print("[bold blue]🦋 Fetching Bluesky posts...[/]")
    
    session = await get_bluesky_session()
    if not session:
        return []
    
    # Search terms relevant to indie hackers
    # Search terms from config
    search_terms = CONFIG.get("bluesky", {}).get("hashtags", [])
    if not search_terms:
         search_terms = ["#buildinpublic", "#saas"]
    
    all_items: list[ScrapedItem] = []
    
    for term in search_terms:
        console.print(f"[dim]  → Searching: {term}[/]")
        items = await search_bluesky_posts(session, term, max_items // len(search_terms))
        all_items.extend(items)
        await asyncio.sleep(0.5)
    
    # Deduplicate by URL
    seen = set()
    unique_items = []
    for item in all_items:
        if item.url not in seen:
            seen.add(item.url)
            unique_items.append(item)
    
    # Sort by engagement
    unique_items.sort(key=lambda x: x.score, reverse=True)
    
    console.print(f"[green]✓ Fetched {len(unique_items)} posts from Bluesky[/]")
    return unique_items[:max_items]


async def save_results(items: list[ScrapedItem]) -> Path:
    """Save scraped items to JSON file."""
    output_path = get_scraped_data_dir() / f"bluesky_{get_date_str()}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, indent=2, default=str)
    
    console.print(f"[dim]Saved to {output_path}[/]")
    return output_path


async def main():
    """Run the Bluesky scraper."""
    items = await fetch_bluesky_posts()
    if items:
        await save_results(items)
    return items


if __name__ == "__main__":
    asyncio.run(main())
