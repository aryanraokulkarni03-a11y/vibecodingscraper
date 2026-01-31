# Research Top 10 Trending AI Tools

## Goal
Identify the top 10 trending AI tools of the week, validate their legitimacy, and provide a deep analysis including functionality, reviews, and revenue potential.

## Inputs
- **Source**: Futurepedia.io (Trending Section) or similar AI directory.
- **Count**: Top 10 tools.

## Procedure
1.  **Scrape Trending List**:
    - Use `execution/fetch_trending_ai.py`.
    - Target `https://www.futurepedia.io/trending` (or efficient alternative).
    - Extract: Tool Name, URL, Category, Short Description.

2.  **Analyze & Validate (AI Layer)**:
    - Use `execution/analyze_trends.py`.
    - For each tool:
        - **Validation**: Check if the URL is accessible and the site looks professional.
        - **Deep Dive**:
            - **What it does**: Clear, non-technical explanation.
            - **Critique/Review**: Pros and Cons based on features.
            - **Revenue Potential**: Generate 3 specific business ideas using this tool.

3.  **Output**:
    - JSON file: `.tmp/YYYYMMDD/trending_ai_detailed_YYYYMMDD.json`
    - HTML Section: Append to the weekly report.

## Edge Cases
- **Site Structure Change**: If selectors fail, fallback to a "General AI Trends" search on Google or use Product Hunt 'Artificial Intelligence' category.
- **Rate Limits**: Implement delays between page visits if scraping deep details.
