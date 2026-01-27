"""
AI Trend Analyzer - Gemini API

Analyzes aggregated scraper data to identify:
- Trending patterns and themes
- "Vibe-code-ability" scores
- Top opportunities for solo developers
- Category clustering
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_client import MultiModelClient
from rich.console import Console

from config import TrendReport, TMP_DIR, get_env, get_week_range, get_scraped_data_dir, get_reports_dir

console = Console()

ANALYSIS_PROMPT = """You are an AI trend analyst specializing in startup opportunities for solo developers who use "vibe coding" (AI-assisted development).

Analyze the following scraped data from multiple startup platforms and provide insights.

**Your Task:**
1. Identify the TOP 10 most promising opportunities for a solo developer to build with AI code generation
2. Look for patterns and recurring themes across platforms
3. Score each opportunity's "vibe-code-ability" (1-10) based on:
   - Technical complexity (simpler = higher score)
   - Potential for MVP in a weekend
   - Market validation (upvotes, engagement)
   - Alignment with AI/automation trends
4. Categorize opportunities into niches

**Focus Areas:**
- "Service as a Software" (AI replacing human services)
- Automation tools
- Developer productivity
- AI wrappers and integrations
- No-code/low-code adjacent tools
- Micro-SaaS opportunities

**Scraped Data:**
{data}

**Response Format (JSON):**
{{
  "summary": "2-3 sentence overview of this week's trends",
  "trending_categories": ["category1", "category2", ...],
  "top_opportunities": [
    {{
      "rank": 1,
      "name": "Opportunity name",
      "source": "where it came from",
      "description": "what it is",
      "why_vibe_codeable": "why this is good for AI-assisted dev",
      "vibe_score": 8,
      "estimated_build_time": "1 weekend",
      "similar_examples": ["example1", "example2"],
      "url": "link to source"
    }}
  ],
  "emerging_patterns": [
    {{
      "pattern": "Pattern name",
      "description": "What this pattern is",
      "examples": ["example1", "example2"],
      "opportunity": "How to capitalize on this"
    }}
  ],
  "service_as_software_ideas": [
    {{
      "service": "Traditional service being replaced",
      "software_opportunity": "How AI can replace it",
      "complexity": "low/medium/high"
    }}
  ]
}}
"""


def load_scraped_data() -> list[dict]:
    """Load all scraped JSON files from .tmp directory."""
    all_data = []
    
    today = datetime.now().strftime("%Y%m%d")
    
    for json_file in get_scraped_data_dir().glob("*.json"):
        # Only load today's files
        if today not in json_file.name:
            continue
            
        # Skip output files
        if json_file.name.startswith("analysis_") or json_file.name.startswith("trend_report_"):
            continue
            
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.extend(data)
                console.print(f"[dim]  Loaded {len(data)} items from {json_file.name}[/]")
        except Exception as e:
            console.print(f"[dim red]Error loading {json_file}: {e}[/]")
    
    return all_data


def prepare_data_for_analysis(data: list[dict], max_items: int = 200) -> str:
    """Prepare data for AI analysis, respecting token limits."""
    # Sort by score
    sorted_data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)
    
    # Take top items
    top_items = sorted_data[:max_items]
    
    # Simplify data structure
    simplified = []
    for item in top_items:
        simplified.append({
            "source": item.get("source"),
            "name": item.get("name"),
            "description": item.get("description", "")[:200] if item.get("description") else None,
            "category": item.get("category"),
            "score": item.get("score"),
            "url": item.get("url"),
        })
    
    return json.dumps(simplified, indent=2)


async def analyze_trends(data: list[dict]) -> dict[str, Any]:
    """
    Use Gemini to analyze trends in scraped data.
    
    Args:
        data: List of scraped items
        
    Returns:
        Analysis results dictionary
    """
    console.print("[bold blue]🧠 Analyzing trends with AI...[/]")
    
    # api_key check handled in MultiModelClient
    
    # Prepare data
    data_str = prepare_data_for_analysis(data)
    console.print(f"[dim]  Analyzing {len(data)} items[/]")
    
    # Create model and generate
    client = MultiModelClient()
    
    prompt = ANALYSIS_PROMPT.format(data=data_str)
    
    try:
        response_text = await client.generate_content(prompt)
        
        # Parse JSON response
        result = json.loads(response_text)
        console.print("[green]✓ Analysis complete[/]")
        return result
        
    except json.JSONDecodeError:
        # Try to extract JSON from response
        text = response_text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            return result
        raise
    except Exception as e:
        console.print(f"[red]AI analysis failed: {e}[/]")
        raise


def create_trend_report(analysis: dict[str, Any], raw_data: list[dict]) -> TrendReport:
    """Create a structured trend report from analysis."""
    start_date, end_date = get_week_range()
    
    return TrendReport(
        week_start=start_date,
        week_end=end_date,
        total_items=len(raw_data),
        top_opportunities=analysis.get("top_opportunities", []),
        trending_categories=analysis.get("trending_categories", []),
        ai_summary=analysis.get("summary", ""),
        vibe_code_picks=[
            opp for opp in analysis.get("top_opportunities", [])
            if opp.get("vibe_score", 0) >= 7
        ]
    )


async def save_analysis(report: TrendReport, analysis: dict) -> tuple[Path, Path]:
    """Save analysis results."""
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Save full analysis
    analysis_path = get_reports_dir() / f"analysis_{date_str}.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, default=str)
    
    # Save trend report
    report_path = get_reports_dir() / f"trend_report_{date_str}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2, default=str)
    
    console.print(f"[dim]Saved analysis to {analysis_path}[/]")
    console.print(f"[dim]Saved report to {report_path}[/]")
    
    return analysis_path, report_path


async def main():
    """Run the trend analyzer."""
    console.print("[bold]Loading scraped data...[/]")
    data = load_scraped_data()
    
    if not data:
        console.print("[yellow]No scraped data found. Run scrapers first.[/]")
        return None
    
    console.print(f"[dim]Loaded {len(data)} total items[/]")
    
    analysis = await analyze_trends(data)
    report = create_trend_report(analysis, data)
    await save_analysis(report, analysis)
    
    # Print summary
    console.print("\n[bold green]📊 Weekly Trend Summary[/]")
    console.print(f"[cyan]{analysis.get('summary', 'No summary generated')}[/]")
    
    console.print("\n[bold]🔥 Top Vibe-Coding Opportunities:[/]")
    for opp in analysis.get("top_opportunities", [])[:5]:
        console.print(f"  {opp.get('rank', '?')}. [bold]{opp.get('name')}[/] "
                     f"(Score: {opp.get('vibe_score', '?')}/10)")
        console.print(f"     [dim]{opp.get('why_vibe_codeable', '')}[/]")
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
