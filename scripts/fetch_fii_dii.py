"""
Fetch FII/DII net flow data.

Two parts, with different reliability:

1. MARKET-WIDE aggregate FII/DII net buy/sell (cash market) — pulled live
   from NSE's public JSON endpoint. This part is real and working.

2. PER-STOCK institutional shareholding trend — NSE only publishes this
   quarterly, buried in shareholding-pattern filings (PDF/XBRL), and isn't
   cleanly scrapable for free. Rather than fake a scraper that will silently
   break, this script reads it from a manually-maintained CSV
   (sheets/institutional_holding.csv) until a solid free source is found.
   Update it once a quarter from screener.in or the company's investor page.

Usage:
    python scripts/fetch_fii_dii.py
    python scripts/fetch_fii_dii.py --dry-run   # skip the live NSE call

Writes:
    data/fii_dii_{date}.json
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path

import requests

NSE_HOME = "https://www.nseindia.com"
NSE_FII_DII_API = "https://www.nseindia.com/api/fiidiiTradeReact"

HOLDING_TREND_PATH = Path("sheets/institutional_holding.csv")
OUTPUT_DIR = Path("data")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


@dataclass
class FiiDiiDay:
    date: str
    category: str  # "FII" or "DII"
    buy_value_cr: float
    sell_value_cr: float
    net_value_cr: float


def fetch_market_fii_dii(dry_run: bool = False) -> list[FiiDiiDay]:
    """Pull the latest published FII/DII cash-market net flow from NSE.

    NSE requires a 'warm-up' request to the homepage first to obtain
    session cookies before the API will respond — a raw request to the
    API endpoint alone will be rejected.
    """
    if dry_run:
        return [
            FiiDiiDay(date=str(date.today()), category="FII",
                      buy_value_cr=12500.0, sell_value_cr=13100.0, net_value_cr=-600.0),
            FiiDiiDay(date=str(date.today()), category="DII",
                      buy_value_cr=9800.0, sell_value_cr=8700.0, net_value_cr=1100.0),
        ]

    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        session.get(NSE_HOME, timeout=10)  # warm up cookies
        resp = session.get(NSE_FII_DII_API, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! FII/DII fetch failed: {exc}", file=sys.stderr)
        print("  (NSE's endpoint/headers change occasionally — check for an updated path)", file=sys.stderr)
        return []

    results = []
    for row in raw:
        try:
            results.append(FiiDiiDay(
                date=row.get("date", str(date.today())),
                category=row.get("category", "?"),
                buy_value_cr=float(row.get("buyValue", 0)),
                sell_value_cr=float(row.get("sellValue", 0)),
                net_value_cr=float(row.get("netValue", 0)),
            ))
        except (TypeError, ValueError):
            continue
    return results


def read_holding_trend(path: Path) -> list[dict]:
    """Manually-maintained per-stock institutional holding % by quarter.

    Expected columns: ticker, quarter, fii_holding_pct
    Update this once a quarter from screener.in's shareholding-pattern tab
    or the company's investor-relations page.
    """
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def compute_trend(rows: list[dict], ticker: str) -> str:
    """rising / falling / flat / insufficient_data, based on last 3 quarters."""
    ticker_rows = sorted(
        (r for r in rows if r["ticker"] == ticker),
        key=lambda r: r["quarter"],
    )[-3:]
    if len(ticker_rows) < 2:
        return "insufficient_data"
    values = [float(r["fii_holding_pct"]) for r in ticker_rows]
    if values[-1] > values[0]:
        return "rising"
    if values[-1] < values[0]:
        return "falling"
    return "flat"


def main(dry_run: bool = False):
    print("Fetching market-wide FII/DII flow...")
    market_flow = fetch_market_fii_dii(dry_run=dry_run)
    for row in market_flow:
        print(f"  {row.category}: net {row.net_value_cr:+.1f} Cr (buy {row.buy_value_cr}, sell {row.sell_value_cr})")

    print("\nReading per-stock institutional holding trend (manual CSV)...")
    holding_rows = read_holding_trend(HOLDING_TREND_PATH)
    tickers = sorted({r["ticker"] for r in holding_rows})
    trends = {}
    if not tickers:
        print(f"  No data found. Create {HOLDING_TREND_PATH} with columns: ticker, quarter, fii_holding_pct")
    for ticker in tickers:
        trend = compute_trend(holding_rows, ticker)
        trends[ticker] = trend
        print(f"  {ticker}: {trend}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"fii_dii_{date.today()}.json"
    with open(out_path, "w") as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "market_flow": [asdict(r) for r in market_flow],
            "per_stock_holding_trend": trends,
        }, f, indent=2)
    print(f"\nWrote output to {out_path}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)