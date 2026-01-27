"""
Indie Hackers Scraper - Playwright

Scrapes the Indie Hackers community for trending posts and product launches.
Focus: Build in public, product launches, revenue discussions
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from rich.console import Console

from config import ScrapedItem, rate_limit, CONFIG, get_scraped_data_dir

console = Console()

INDIE_HACKERS_URL = "https://www.indiehackers.com"


async def fetch_indiehackers_posts(max_items: int = 50) -> list[ScrapedItem]:
    """
    Scrape trending posts from Indie Hackers.
    
    Args:
        max_items: Maximum number of posts to scrape (default from config)
        
    Returns:
        List of ScrapedItem objects
    """
    if max_items == 50 and CONFIG:
         max_items = CONFIG.get("search", {}).get("max_items_per_source", 50)
    console.print("[bold blue]🚀 Scraping Indie Hackers...[/]")
    items: list[ScrapedItem] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            # Main feed
            await page.goto(f"{INDIE_HACKERS_URL}/feed", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)  # Let dynamic content load
            
            # Scroll to load more content
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1.5)
            
            # Get post elements
            posts = await page.query_selector_all("article, .feed-item, [data-test='feed-item']")
            
            if not posts:
                # Fallback selectors
                posts = await page.query_selector_all(".post, .content-item, a[href*='/post/']")
            
            console.print(f"[dim]Found {len(posts)} post elements[/]")
            
            for post in posts[:max_items]:
                try:
                    # Extract title
                    title_el = await post.query_selector("h2, h3, .title, [class*='title']")
                    title = await title_el.inner_text() if title_el else None
                    
                    if not title:
                        continue
                    
                    # Extract link
                    link_el = await post.query_selector("a[href*='/post/']")
                    href = await link_el.get_attribute("href") if link_el else None
                    url = f"{INDIE_HACKERS_URL}{href}" if href and href.startswith("/") else href
                    
                    # Extract description/snippet
                    desc_el = await post.query_selector("p, .description, .excerpt, [class*='body']")
                    description = await desc_el.inner_text() if desc_el else ""
                    
                    # Extract upvotes/score
                    score_el = await post.query_selector("[class*='vote'], [class*='upvote'], .score")
                    score_text = await score_el.inner_text() if score_el else "0"
                    score = int("".join(filter(str.isdigit, score_text)) or "0")
                    
                    # Extract author
                    author_el = await post.query_selector("[class*='author'], [class*='user'], .username")
                    author = await author_el.inner_text() if author_el else None
                    
                    item = ScrapedItem(
                        source="indiehackers",
                        name=title.strip(),
                        description=description.strip()[:500] if description else None,
                        url=url,
                        category="indie-hackers",
                        score=score,
                        metadata={
                            "author": author,
                        }
                    )
                    items.append(item)
                    
                except Exception as e:
                    console.print(f"[dim red]Error parsing post: {e}[/]")
                    continue
            
            # Also try to get "Show IH" / product launch posts
            await page.goto(f"{INDIE_HACKERS_URL}/products", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            products = await page.query_selector_all(".product-card, [data-test='product'], article")
            
            for product in products[:20]:
                try:
                    name_el = await product.query_selector("h2, h3, .name, [class*='name']")
                    name = await name_el.inner_text() if name_el else None
                    
                    if not name:
                        continue
                    
                    desc_el = await product.query_selector("p, .tagline, .description")
                    description = await desc_el.inner_text() if desc_el else ""
                    
                    link_el = await product.query_selector("a")
                    href = await link_el.get_attribute("href") if link_el else None
                    
                    item = ScrapedItem(
                        source="indiehackers",
                        name=name.strip(),
                        description=description.strip()[:500] if description else None,
                        url=f"{INDIE_HACKERS_URL}{href}" if href and href.startswith("/") else href,
                        category="product-launch",
                        score=0,
                    )
                    items.append(item)
                    
                except Exception:
                    continue
                    
        except PlaywrightTimeout:
            console.print("[red]Timeout loading Indie Hackers[/]")
        except Exception as e:
            console.print(f"[red]Error scraping Indie Hackers: {e}[/]")
        finally:
            await browser.close()
    
    # Deduplicate by name
    seen = set()
    unique_items = []
    for item in items:
        if item.name not in seen:
            seen.add(item.name)
            unique_items.append(item)
    
    console.print(f"[green]✓ Scraped {len(unique_items)} items from Indie Hackers[/]")
    return unique_items


async def save_results(items: list[ScrapedItem]) -> Path:
    """Save scraped items to JSON file."""
    output_path = get_scraped_data_dir() / f"indiehackers_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, indent=2, default=str)
    
    console.print(f"[dim]Saved to {output_path}[/]")
    return output_path


async def main():
    """Run the Indie Hackers scraper."""
    items = await fetch_indiehackers_posts()
    await save_results(items)
    return items


if __name__ == "__main__":
    asyncio.run(main())
