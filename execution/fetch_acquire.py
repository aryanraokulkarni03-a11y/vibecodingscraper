"""
Acquire.com Scraper - Playwright

Scrapes startup listings from Acquire.com marketplace.
Focus: SaaS businesses, tech startups, revenue-generating products
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from rich.console import Console

from config import ScrapedItem, get_week_range, get_scraped_data_dir, get_date_str, CONFIG

console = Console()

ACQUIRE_URL = "https://acquire.com"


def parse_revenue(text: str) -> int:
    """Parse revenue/price text to integer."""
    if not text:
        return 0
    # Remove non-numeric except for k, m
    text = text.lower().strip()
    multiplier = 1
    if "k" in text:
        multiplier = 1000
    elif "m" in text:
        multiplier = 1000000
    
    numbers = re.findall(r"[\d,]+", text.replace(",", ""))
    if numbers:
        return int(float(numbers[0]) * multiplier)
    return 0


async def fetch_acquire_listings(max_items: int = 50) -> list[ScrapedItem]:
    """
    Scrape startup listings from Acquire.com.
    
    Args:
        max_items: Maximum number of listings to scrape
        
    Returns:
        List of ScrapedItem objects
    """
    console.print("[bold blue]💰 Scraping Acquire.com listings...[/]")
    items: list[ScrapedItem] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            # Browse startups for sale - filter for SaaS/Tech
            await page.goto(
                f"{ACQUIRE_URL}/explore?categories=saas,technology,software",
                wait_until="networkidle",
                timeout=45000
            )
            await asyncio.sleep(3)
            
            # Scroll to load more
            for _ in range(4):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
            
            # Get listing cards
            listings = await page.query_selector_all(
                "[data-testid='startup-card'], .startup-card, .listing-card, article"
            )
            
            if not listings:
                # Fallback: try getting any card-like elements
                listings = await page.query_selector_all(
                    "a[href*='/startup/'], .card, [class*='listing']"
                )
            
            console.print(f"[dim]Found {len(listings)} listing elements[/]")
            
            for listing in listings[:max_items]:
                try:
                    # Extract name
                    name_el = await listing.query_selector(
                        "h2, h3, [class*='title'], [class*='name']"
                    )
                    name = await name_el.inner_text() if name_el else None
                    
                    if not name or len(name) < 3:
                        continue
                    
                    # Extract description
                    desc_el = await listing.query_selector(
                        "p, [class*='description'], [class*='tagline']"
                    )
                    description = await desc_el.inner_text() if desc_el else ""
                    
                    # Extract link
                    link = await listing.get_attribute("href")
                    if not link:
                        link_el = await listing.query_selector("a")
                        link = await link_el.get_attribute("href") if link_el else None
                    
                    url = f"{ACQUIRE_URL}{link}" if link and link.startswith("/") else link
                    
                    # Extract category/type
                    category_el = await listing.query_selector(
                        "[class*='category'], [class*='tag'], .badge"
                    )
                    category = await category_el.inner_text() if category_el else "saas"
                    
                    # Extract revenue (if shown)
                    revenue_el = await listing.query_selector(
                        "[class*='revenue'], [class*='mrr'], [class*='arr']"
                    )
                    revenue_text = await revenue_el.inner_text() if revenue_el else ""
                    revenue = parse_revenue(revenue_text)
                    
                    # Extract asking price
                    price_el = await listing.query_selector(
                        "[class*='price'], [class*='asking']"
                    )
                    price_text = await price_el.inner_text() if price_el else ""
                    price = parse_revenue(price_text)
                    
                    item = ScrapedItem(
                        source="acquire",
                        name=name.strip(),
                        description=description.strip()[:500] if description else None,
                        url=url,
                        category=category.lower().strip() if category else "saas",
                        score=revenue,  # Use revenue as "score" for ranking
                        metadata={
                            "revenue": revenue,
                            "asking_price": price,
                            "revenue_text": revenue_text,
                            "price_text": price_text,
                        }
                    )
                    items.append(item)
                    
                except Exception as e:
                    console.print(f"[dim red]Error parsing listing: {e}[/]")
                    continue
                    
        except PlaywrightTimeout:
            console.print("[red]Timeout loading Acquire.com[/]")
        except Exception as e:
            console.print(f"[red]Error scraping Acquire.com: {e}[/]")
        finally:
            await browser.close()
    
    console.print(f"[green]✓ Scraped {len(items)} listings from Acquire.com[/]")
    return items


async def save_results(items: list[ScrapedItem]) -> Path:
    """Save scraped items to JSON file."""
    output_path = get_scraped_data_dir() / f"acquire_{get_date_str()}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump(mode="json") for item in items], f, indent=2, default=str)
    
    console.print(f"[dim]Saved to {output_path}[/]")
    return output_path


async def main():
    """Run the Acquire.com scraper."""
    items = await fetch_acquire_listings()
    await save_results(items)
    return items


if __name__ == "__main__":
    asyncio.run(main())
