"""
Google Sheets Export - gspread

Exports trend analysis to Google Sheets for easy access and sharing.
Creates a formatted weekly report spreadsheet.
Uses OAuth flow for web credentials (not service account).
"""
import json
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from rich.console import Console

from config import TMP_DIR, get_env, TrendReport, get_reports_dir

console = Console()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TOKEN_PATH = Path(__file__).parent.parent / ".tmp" / "token.json"


def get_sheets_client() -> gspread.Client:
    """Get authenticated Google Sheets client using OAuth flow."""
    creds_path = Path(get_env("GOOGLE_SHEETS_CREDENTIALS", "./credentials.json"))
    
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google credentials not found at {creds_path}. "
            "Download from Google Cloud Console."
        )
    
    creds = None
    
    # Check for cached token
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception:
            pass
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            console.print("[dim]Refreshing Google credentials...[/]")
            creds.refresh(Request())
        else:
            console.print("[bold yellow]Opening browser for Google authentication...[/]")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token for next time
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        console.print("[green]✓ Credentials saved for future use[/]")
    
    return gspread.authorize(creds)


def get_or_create_spreadsheet(client: gspread.Client, name: str) -> gspread.Spreadsheet:
    """Get existing spreadsheet or create new one."""
    try:
        return client.open(name)
    except gspread.SpreadsheetNotFound:
        sheet = client.create(name)
        console.print(f"[green]Created new spreadsheet: {name}[/]")
        return sheet


def export_to_sheets(report: TrendReport, analysis: dict) -> str:
    """
    Export trend report to Google Sheets.
    
    Args:
        report: TrendReport object
        analysis: Raw analysis dict from AI
        
    Returns:
        URL of the spreadsheet
    """
    console.print("[bold blue]📊 Exporting to Google Sheets...[/]")
    
    client = get_sheets_client()
    
    # Create/get spreadsheet
    sheet_name = "Vibe-Coding Trend Reports"
    spreadsheet = get_or_create_spreadsheet(client, sheet_name)
    
    # Create worksheet for this week
    week_str = report.week_end.strftime("%Y-%m-%d")
    worksheet_name = f"Week of {week_str}"
    
    try:
        worksheet = spreadsheet.add_worksheet(worksheet_name, rows=100, cols=10)
    except gspread.exceptions.APIError:
        # Worksheet exists, get it
        worksheet = spreadsheet.worksheet(worksheet_name)
        worksheet.clear()
    
    # Prepare data rows
    rows = []
    
    # Header section
    rows.append(["🚀 Vibe-Coding Trend Report", "", "", "", ""])
    rows.append([f"Week: {report.week_start.strftime('%Y-%m-%d')} to {week_str}", "", "", "", ""])
    rows.append([f"Total items analyzed: {report.total_items}", "", "", "", ""])
    rows.append(["", "", "", "", ""])
    
    # Summary
    rows.append(["📝 Summary", "", "", "", ""])
    rows.append([analysis.get("summary", ""), "", "", "", ""])
    rows.append(["", "", "", "", ""])
    
    # Trending Categories
    rows.append(["🔥 Trending Categories", "", "", "", ""])
    categories = ", ".join(report.trending_categories[:10])
    rows.append([categories, "", "", "", ""])
    rows.append(["", "", "", "", ""])
    
    # Top Opportunities header
    rows.append([
        "Rank", "Name", "Vibe Score", "Build Time", 
        "Why Vibe-Codeable", "Source", "URL"
    ])
    
    # Top Opportunities data
    for opp in report.top_opportunities:
        rows.append([
            opp.get("rank", ""),
            opp.get("name", ""),
            opp.get("vibe_score", ""),
            opp.get("estimated_build_time", ""),
            opp.get("why_vibe_codeable", "")[:100],
            opp.get("source", ""),
            opp.get("url", ""),
        ])
    
    rows.append(["", "", "", "", ""])
    
    # Service as Software Ideas
    service_ideas = analysis.get("service_as_software_ideas", [])
    if service_ideas:
        rows.append(["💡 Service-as-Software Opportunities", "", "", "", ""])
        rows.append(["Traditional Service", "AI Opportunity", "Complexity", "", ""])
        for idea in service_ideas:
            rows.append([
                idea.get("service", ""),
                idea.get("software_opportunity", ""),
                idea.get("complexity", ""),
                "",
                "",
            ])
    
    rows.append(["", "", "", "", ""])
    
    # Emerging Patterns
    patterns = analysis.get("emerging_patterns", [])
    if patterns:
        rows.append(["📈 Emerging Patterns", "", "", "", ""])
        rows.append(["Pattern", "Description", "Opportunity", "", ""])
        for pattern in patterns:
            rows.append([
                pattern.get("pattern", ""),
                pattern.get("description", "")[:100],
                pattern.get("opportunity", "")[:100],
                "",
                "",
            ])
    
    # Update all at once
    worksheet.update(rows, "A1")
    
    # Format header row
    worksheet.format("A1:G1", {"textFormat": {"bold": True, "fontSize": 14}})
    worksheet.format("A11:G11", {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}})
    
    console.print(f"[green]✓ Exported to Google Sheets[/]")
    console.print(f"[dim]URL: {spreadsheet.url}[/]")
    
    return spreadsheet.url


def main():
    """Run the export."""
    # Load latest report
    today = datetime.now().strftime("%Y%m%d")
    report_path = get_reports_dir() / f"trend_report_{today}.json"
    analysis_path = get_reports_dir() / f"analysis_{today}.json"
    
    if not report_path.exists():
        console.print("[yellow]No report found. Run analyzer first.[/]")
        return None
    
    with open(report_path, "r") as f:
        report_data = json.load(f)
        report = TrendReport(**report_data)
    
    with open(analysis_path, "r") as f:
        analysis = json.load(f)
    
    url = export_to_sheets(report, analysis)
    return url


if __name__ == "__main__":
    main()
