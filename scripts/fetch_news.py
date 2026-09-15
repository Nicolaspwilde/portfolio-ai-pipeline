"""
Fetch news and policy signals relevant to tracked tickers/sectors.

Two sources:
1. Google News RSS — per-ticker/company-name search, free, reliable, no API key.
2. PIB (Press Information Bureau) RSS — government policy releases, filtered
   by keyword relevance to your sectors (e.g. "defence", "railways").

Design choice: this does NOT try to summarize or judge news — it just pulls
and filters candidates by keyword relevance to your holding's thesis. The
AI analyst step (next) is what actually reads and interprets these.

Usage:
    python scripts/fetch_news.py
    python scripts/fetch_news.py --dry-run   # skip network, use sample data

Reads:
    sheets/holdings.csv   — for ticker + company name + thesis keywords
    sheets/watchlist.csv  — same

Writes:
    data/news_{date}.json
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

try:
    import feedparser
except ImportError:
    feedparser = None  # allows --dry-run to work without the dependency installed

HOLDINGS_PATH = Path("sheets/holdings.csv")
WATCHLIST_PATH = Path("sheets/watchlist.csv")
OUTPUT_DIR = Path("data")

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
PIB_RSS = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"  # English press releases

MAX_ARTICLES_PER_TICKER = 5


@dataclass
class NewsItem:
    ticker: str
    title: str
    link: str
    published: str
    source: str  # "google_news" | "pib"


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fetch_google_news(ticker: str, company_query: str, dry_run: bool = False) -> list[NewsItem]:
    if dry_run:
        return [
            NewsItem(ticker=ticker, title=f"Sample headline about {company_query}",
                     link="https://example.com/sample", published=str(date.today()),
                     source="google_news"),
        ]
    if feedparser is None:
        raise RuntimeError("feedparser not installed — run: pip install -r requirements.txt")
    url = GOOGLE_NEWS_RSS.format(query=quote(company_query))
    try:
        feed = feedparser.parse(url)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Google News fetch failed for {ticker}: {exc}", file=sys.stderr)
        return []

    items = []
    for entry in feed.entries[:MAX_ARTICLES_PER_TICKER]:
        items.append(NewsItem(
            ticker=ticker,
            title=entry.get("title", ""),
            link=entry.get("link", ""),
            published=entry.get("published", ""),
            source="google_news",
        ))
    return items


def fetch_pib_releases(keywords: list[str], dry_run: bool = False) -> list[dict]:
    """Pull recent PIB releases and keep only ones matching a keyword.

    keywords should be thesis-relevant terms, e.g. ["defence", "naval",
    "railways"] — set these per-sector in your holdings' thesis, not here.
    """
    if dry_run:
        return [{"title": "Sample: Cabinet approves defence procurement", "link": "https://pib.gov.in/sample",
                 "published": str(date.today()), "matched_keyword": keywords[0] if keywords else ""}]

    if feedparser is None:
        raise RuntimeError("feedparser not installed — run: pip install -r requirements.txt")
    try:
        feed = feedparser.parse(PIB_RSS)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! PIB fetch failed: {exc}", file=sys.stderr)
        return []

    matched = []
    for entry in feed.entries:
        title = entry.get("title", "")
        for kw in keywords:
            if kw.lower() in title.lower():
                matched.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "matched_keyword": kw,
                })
                break
    return matched


def main(dry_run: bool = False):
    holdings = read_csv_rows(HOLDINGS_PATH)
    watchlist = read_csv_rows(WATCHLIST_PATH)
    all_rows = holdings + watchlist

    if not all_rows:
        print("No holdings or watchlist found. Copy the *_template.csv files first.")
        return

    all_news: list[NewsItem] = []
    print("Fetching per-ticker news...")
    for row in all_rows:
        ticker = row["ticker"]
        items = fetch_google_news(ticker, ticker, dry_run=dry_run)
        all_news.extend(items)
        print(f"  {ticker}: {len(items)} articles")

    # PIB keywords: hardcoded starter set for defence/industrial themes.
    # Edit this list to match your actual holdings' sectors.
    pib_keywords = ["defence", "defense", "naval", "railways", "manufacturing"]
    print(f"\nFetching PIB releases matching: {pib_keywords}")
    pib_items = fetch_pib_releases(pib_keywords, dry_run=dry_run)
    for item in pib_items:
        print(f"  [{item['matched_keyword']}] {item['title']}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"news_{date.today()}.json"
    with open(out_path, "w") as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "ticker_news": [asdict(n) for n in all_news],
            "pib_releases": pib_items,
        }, f, indent=2)
    print(f"\nWrote output to {out_path}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)