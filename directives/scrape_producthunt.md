# Scrape Product Hunt

## Goal
Fetch trending products from Product Hunt relevant to vibe-coding opportunities.

## Inputs
- Optional: `PRODUCTHUNT_API_KEY` and `PRODUCTHUNT_API_SECRET` in `.env` (increases rate limit)

## Execution
```bash
python execution/fetch_producthunt.py
```

## Output
- JSON file in `.tmp/producthunt_YYYYMMDD.json`
- Items include: name, tagline, description, votes, topics, URL

## Target Topics
- artificial-intelligence
- saas
- developer-tools
- productivity
- no-code
- automation
- open-source

## Notes
- Uses GraphQL API (free, no auth required for basic access)
- Rate limit: ~100 requests/hour without auth
- Fetches last 7 days by default
