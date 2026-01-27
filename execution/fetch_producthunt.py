"""
Product Hunt Scraper - GraphQL API

Fetches trending products from Product Hunt using their public GraphQL API.
Focus: AI tools, SaaS, Developer Tools, Productivity
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

import httpx
from rich.console import Console

from config import ScrapedItem, get_week_range, get_env, CONFIG, get_scraped_data_dir

console = Console()

PRODUCTHUNT_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

# Categories we care about for vibe-coding
# Categories we care about for vibe-coding
# Loaded from config
TARGET_TOPICS = CONFIG.get("producthunt", {}).get("categories", [])
if not TARGET_TOPICS:
    TARGET_TOPICS = ["artificial-intelligence", "developer-tools"]

QUERY_POSTS = """
query GetPosts($first: Int!, $after: String, $postedAfter: DateTime) {
  posts(first: $first, after: $after, postedAfter: $postedAfter, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        website
        votesCount
        commentsCount
        createdAt
        topics {
          edges {
            node {
              slug
              name
            }
          }
        }
        thumbnail {
          url
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


async def fetch_producthunt_posts(
    days_back: int = 7,
    max_items: int = 100
) -> list[ScrapedItem]:
    """
    Fetch top posts from Product Hunt for the past week.
    
    Args:
        days_back: Number of days to look back
        max_items: Maximum number of items to fetch
        
    Returns:
        List of ScrapedItem objects
    """
    console.print("[bold blue]📦 Fetching Product Hunt posts...[/]")
    
    start_date, _ = get_week_range()
    posted_after = start_date.isoformat()
    
    # Get API token if available (increases rate limit)
    api_key = get_env("PRODUCTHUNT_API_KEY")
    api_secret = get_env("PRODUCTHUNT_API_SECRET")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    # If we have credentials, get an access token
    if api_key and api_secret:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://api.producthunt.com/v2/oauth/token",
                json={
                    "client_id": api_key,
                    "client_secret": api_secret,
                    "grant_type": "client_credentials",
                }
            )
            if token_resp.status_code == 200:
                token = token_resp.json().get("access_token")
                headers["Authorization"] = f"Bearer {token}"
    
    items: list[ScrapedItem] = []
    cursor = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(items) < max_items:
            variables = {
                "first": min(50, max_items - len(items)),
                "after": cursor,
                "postedAfter": posted_after,
            }
            
            try:
                response = await client.post(
                    PRODUCTHUNT_GRAPHQL_URL,
                    headers=headers,
                    json={"query": QUERY_POSTS, "variables": variables}
                )
                response.raise_for_status()
                data = response.json()
                
            except httpx.HTTPError as e:
                console.print(f"[red]Error fetching Product Hunt: {e}[/]")
                break
            
            posts = data.get("data", {}).get("posts", {})
            edges = posts.get("edges", [])
            
            if not edges:
                break
            
            for edge in edges:
                node = edge["node"]
                topics = [t["node"]["slug"] for t in node.get("topics", {}).get("edges", [])]
                
                # Filter for relevant topics
                relevant_topics = [t for t in topics if t in TARGET_TOPICS]
                if not relevant_topics and topics:
                    # Skip if no relevant topics and has other topics
                    continue
                
                item = ScrapedItem(
                    source="producthunt",
                    name=node["name"],
                    description=f"{node['tagline']}\n\n{node.get('description', '')}".strip(),
                    url=node.get("website") or node["url"],
                    category=relevant_topics[0] if relevant_topics else "general",
                    score=node["votesCount"],
                    metadata={
                        "ph_url": node["url"],
                        "comments": node["commentsCount"],
                        "topics": topics,
                        "created_at": node["createdAt"],
                        "thumbnail": node.get("thumbnail", {}).get("url"),
                    }
                )
                items.append(item)
            
            # Pagination
            page_info = posts.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            
            # Rate limiting
            await asyncio.sleep(1)
    
    console.print(f"[green]✓ Fetched {len(items)} items from Product Hunt[/]")
    return items


async def save_results(items: list[ScrapedItem]) -> Path:
    """Save scraped items to JSON file."""
    output_path = get_scraped_data_dir() / f"producthunt_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, indent=2, default=str)
    
    console.print(f"[dim]Saved to {output_path}[/]")
    return output_path


async def main():
    """Run the Product Hunt scraper."""
    items = await fetch_producthunt_posts()
    await save_results(items)
    return items


if __name__ == "__main__":
    asyncio.run(main())
