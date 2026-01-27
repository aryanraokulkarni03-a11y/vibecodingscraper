# 🚀 Vibe-Coding Trend Scraper

> **Your automated intelligence for discovering "vibe-code-able" SaaS opportunities.**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

This tool scrapes Reddit, Hacker News, Bluesky, Product Hunt, and Indie Hackers to find trending topics, analyzes them using AI (Gemini/Groq), and generates a "Vibe Score" for each opportunity.

## ✨ Features (2026 Update)

- **🏎️ Parallel Execution**: Scrapes 6+ sources simultaneously.
- **🧠 Multi-Model AI**: Auto-fallback from Gemini 2.5 Flash to Groq (Llama 3).
- **📚 Smart Deduplication**: SQLite database prevents finding the same lead twice.
- **📂 Organized Output**: Daily folders (`.tmp/YYYYMMDD/reports/`) with HTML reports and raw JSON.
- **📊 Google Sheets Export**: Auto-uploads trends to your spreadsheet.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/vibe-coding-scraper.git
    cd vibe-coding-scraper
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Configuration**:
    - Copy `.env.example` to `.env` and fill in your API keys (Gemini, Reddit, etc.).
    - (Optional) Customize search terms in `config.yaml`.

## 🚀 Usage

Run the full pipeline (Scrape -> Analyze -> Report -> Email):
```bash
python execution/run_weekly.py
```

### Options:
- `--scrape`: Only run scrapers (skip analysis).
- `--analyze`: Re-run analysis on existing data.
- `--export`: Re-run Google Sheets export.
- `--email`: Re-send email digest.
- `--force`: Force re-scrape even if data was already collected today.

## 📁 Output Structure

The scraper creates a `.tmp` directory with daily folders:

```
.tmp/
└── 20260127/
    ├── reports/
    │   ├── report_20260127.html  (Printable PDF Report)
    │   └── analysis_20260127.json
    └── scraped_data/
        ├── reddit_20260127.json
        └── producthunt_20260127.json
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
