# Weekly Pipeline - Main Directive

## Goal
Generate weekly trend report for vibe-coding opportunities.

## Schedule
Run every Sunday at 9:00 AM (or manually when needed).

## Full Pipeline
```bash
python execution/run_weekly.py
```

## Individual Phases

### 1. Scrape Only
```bash
python execution/run_weekly.py --scrape
```

### 2. Analyze Only (requires scraped data)
```bash
python execution/run_weekly.py --analyze
```

### 3. Export to Sheets Only
```bash
python execution/run_weekly.py --export
```

### 4. Send Email Only
```bash
python execution/run_weekly.py --email
```

## Required Environment Variables

### Minimum Required
- `GEMINI_API_KEY` - For AI analysis

### For Full Features
- `GOOGLE_SHEETS_CREDENTIALS` - Service account JSON path
- `SMTP_USER` + `SMTP_PASSWORD` - For email delivery
- `EMAIL_RECIPIENT` - Who receives the digest

### Optional (Improves Quality)
- `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET`
- `BLUESKY_HANDLE` + `BLUESKY_APP_PASSWORD`
- `PRODUCTHUNT_API_KEY` + `PRODUCTHUNT_API_SECRET`

## Output
1. Raw data in `.tmp/*.json`
2. Analysis in `.tmp/analysis_YYYYMMDD.json`
3. Report in `.tmp/trend_report_YYYYMMDD.json`
4. Google Sheet (if configured)
5. Email digest (if configured)

## Troubleshooting

### "No scraped data found"
Run scrapers first: `python execution/run_weekly.py --scrape`

### Playwright errors
Install browsers: `playwright install chromium`

### Google Sheets auth error
Ensure `credentials.json` exists and has correct permissions.

### Email fails
Check SMTP credentials. For Gmail, use App Password (not regular password).
