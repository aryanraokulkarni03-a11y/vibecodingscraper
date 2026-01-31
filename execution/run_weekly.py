"""
Weekly Trend Scraper - Main Orchestrator

Runs the complete weekly pipeline:
1. Scrape all data sources
2. Analyze trends with AI
3. Export to Google Sheets
4. Send email digest

Usage:
    python run_weekly.py           # Run full pipeline
    python run_weekly.py --scrape  # Only scrape data
    python run_weekly.py --analyze # Only analyze (assumes data exists)
    python run_weekly.py --export  # Only export (assumes analysis exists)
"""
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import all components
from fetch_producthunt import fetch_producthunt_posts, save_results as save_ph
from fetch_indiehackers import fetch_indiehackers_posts, save_results as save_ih
from fetch_acquire import fetch_acquire_listings, save_results as save_acquire
from fetch_reddit import fetch_reddit_posts, save_results as save_reddit
from fetch_hackernews import fetch_hackernews_posts, save_results as save_hn
from fetch_bluesky import fetch_bluesky_posts, save_results as save_bsky

from fetch_trending_ai import fetch_trending_ai
from analyze_trends import (
    load_scraped_data, 
    analyze_trends, 
    create_trend_report, 
    save_analysis,
    load_trending_data,
    analyze_trending_tools
)

from generate_report import main as generate_report

from export_sheets import export_to_sheets

from send_email import send_email
from config import TrendReport, get_scraped_data_dir, get_date_str

console = Console()


import database

async def run_source_wrapper(fetch_func, save_func, name: str) -> int:
    """Run a single scraper source with deduplication and saving."""
    try:
        items = await fetch_func()
        
        # Deduplication against DB
        new_items = []
        for item in items:
            if not database.is_item_seen(item.url):
                new_items.append(item)
        
        if not new_items:
            console.print(f"[dim]{name}: No new items found (scraped {len(items)})[/]")
            return 0
            
        # Save results
        await save_func(new_items)
        
        # Update history
        for item in new_items:
            database.add_item_to_history(item)
            
        console.print(f"[green]✓ {name}: {len(new_items)} new items[/] (scraped {len(items)})")
        return len(new_items)
        
    except Exception as e:
        console.print(f"[red]{name} failed: {e}[/]")
        return 0


async def run_scrapers() -> int:
    """Run all scrapers in parallel and return total items collected."""
    console.print(Panel.fit("🔄 [bold]Phase 1: Data Collection (Parallel)[/]", style="blue"))
    
    tasks = [
        run_source_wrapper(fetch_producthunt_posts, save_ph, "Product Hunt"),
        run_source_wrapper(fetch_indiehackers_posts, save_ih, "Indie Hackers"),
        run_source_wrapper(fetch_acquire_listings, save_acquire, "Acquire"),
        run_source_wrapper(fetch_reddit_posts, save_reddit, "Reddit"),
        run_source_wrapper(fetch_hackernews_posts, save_hn, "Hacker News"),
        run_source_wrapper(fetch_bluesky_posts, save_bsky, "Bluesky"),
        run_source_wrapper(fetch_trending_ai, lambda x: None, "Trending AI"), # Trending AI saves its own file
    ]

    
    results = await asyncio.gather(*tasks)
    total_items = sum(results)
    
    console.print(f"\n[green]✓ Data collection complete: {total_items} new items[/]\n")
    return total_items


async def run_analysis() -> tuple[TrendReport, dict]:
    """Run AI analysis on collected data."""
    console.print(Panel.fit("🧠 [bold]Phase 2: AI Analysis[/]", style="blue"))
    
    data = load_scraped_data()
    if not data:
        raise ValueError("No scraped data found. Run scrapers first.")
    
    analysis = await analyze_trends(data)
    
    # Analyze trending tools
    trending_data = load_trending_data()
    trending_analysis = await analyze_trending_tools(trending_data)
    
    # Merge analyses
    if trending_analysis:
        analysis["trending_tools_analysis"] = trending_analysis.get("trending_tools_analysis", [])
        
    report = create_trend_report(analysis, data)
    await save_analysis(report, analysis)
    
    console.print(f"\n[green]✓ Analysis complete[/]\n")
    return report, analysis


async def run_export(report: TrendReport, analysis: dict) -> str | None:
    """Export to Google Sheets."""
    console.print(Panel.fit("📊 [bold]Phase 3: Google Sheets Export[/]", style="blue"))
    
    try:
        url = export_to_sheets(report, analysis)
        console.print(f"\n[green]✓ Exported to Sheets[/]\n")
        return url
    except Exception as e:
        console.print(f"[yellow]Sheets export failed: {e}[/]")
        console.print("[dim]Continuing without Sheets export...[/]\n")
        return None


async def run_email(report: TrendReport, analysis: dict, sheet_url: str | None):
    """Send email digest."""
    console.print(Panel.fit("📧 [bold]Phase 4: Email Delivery[/]", style="blue"))
    
    try:
        success = await send_email(report, analysis, sheet_url)
        if success:
            console.print(f"\n[green]✓ Email sent[/]\n")
        else:
            console.print(f"\n[yellow]Email sending failed[/]\n")
    except Exception as e:
        console.print(f"[yellow]Email failed: {e}[/]")


async def run_full_pipeline(args):
    """Run the complete weekly pipeline."""
    start_time = datetime.now()
    
    console.print(Panel.fit(
        "🚀 [bold cyan]Vibe-Coding Trend Scraper[/]\n"
        f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        style="cyan"
    ))
    
    # Daily Skip Check
    today = datetime.now().strftime("%Y%m%d")
    output_dir = get_scraped_data_dir()
    existing_files = list(output_dir.glob(f"*_{today}.json"))
    scraped_files = existing_files

    if scraped_files and not args.force:
        console.print(f"[yellow]⚠ Scrapers already ran today ({len(scraped_files)} files found).[/]")
        console.print("[dim]Skipping scrape to save API calls. Use --force to run anyway.[/]")
        
        # Determine total items from existing files for reporting
        total_items = 0
        import json
        for f in scraped_files:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    total_items += len(json.load(file))
            except: pass
    else:
        # Phase 1: Scrape
        total_items = await run_scrapers()
    
    if total_items == 0:
        console.print("[red]No data collected. Check your internet connection and API keys.[/]")
        return
    
    # Phase 2: Analyze
    report, analysis = await run_analysis()
    
    # Phase 3: Export to Sheets
    sheet_url = await run_export(report, analysis)
    
    # Phase 3.5: Generate HTML Report
    from generate_report import generate_html_report
    html_path = generate_html_report(report, analysis)
    
    # Phase 4: Send Email
    await run_email(report, analysis, sheet_url)
    
    # Summary
    elapsed = datetime.now() - start_time
    console.print(Panel.fit(
        f"[bold green]✅ Pipeline Complete![/]\n\n"
        f"📊 Items collected: {total_items}\n"
        f"🎯 Top opportunities: {len(report.top_opportunities)}\n"
        f"⏱️  Time elapsed: {elapsed.total_seconds():.1f}s\n"
        f"{'📄 Sheet: ' + sheet_url if sheet_url else ''}\n"
        f"🌐 Report: {html_path}",
        style="green"
    ))
    
    # Print top 3 opportunities
    console.print("\n[bold]🔥 Top 3 Vibe-Coding Opportunities:[/]")
    for opp in analysis.get("top_opportunities", [])[:3]:
        console.print(f"  {opp.get('rank')}. [bold]{opp.get('name')}[/] "
                     f"(Score: {opp.get('vibe_score')}/10)")


def main():
    parser = argparse.ArgumentParser(description="Vibe-Coding Trend Scraper")
    parser.add_argument("--scrape", action="store_true", help="Only run scrapers")
    parser.add_argument("--analyze", action="store_true", help="Only run analysis")
    parser.add_argument("--export", action="store_true", help="Only run export")
    parser.add_argument("--email", action="store_true", help="Only send email")
    
    parser.add_argument("--force", action="store_true", help="Force re-scrape even if data exists")
    args = parser.parse_args()
    
    if args.scrape:
        asyncio.run(run_scrapers())
    elif args.analyze:
        asyncio.run(run_analysis())
    elif args.export:
        # Load existing report
        import json
        from config import get_reports_dir
        today = get_date_str()
        with open(get_reports_dir() / f"trend_report_{today}.json") as f:
            report = TrendReport(**json.load(f))
        with open(get_reports_dir() / f"analysis_{today}.json") as f:
            analysis = json.load(f)
        asyncio.run(run_export(report, analysis))
    elif args.email:
        # Load existing report
        import json
        from config import get_reports_dir
        today = get_date_str()
        with open(get_reports_dir() / f"trend_report_{today}.json") as f:
            report = TrendReport(**json.load(f))
        with open(get_reports_dir() / f"analysis_{today}.json") as f:
            analysis = json.load(f)
        asyncio.run(run_email(report, analysis, None))
    else:
        asyncio.run(run_full_pipeline(args))


if __name__ == "__main__":
    main()
