"""
Fetch current price data for holdings + watchlist tickers, and flag
anyone near their stop-loss or target level.

Usage:
    python scripts/fetch_market_data.py
    python scripts/fetch_market_data.py --dry-run   # test logic without network/yfinance

Requires: yfinance, pandas  (see requirements.txt)

Reads:
    sheets/holdings.csv   (ticker, entry_price, base_target, bull_target, stop_loss, ...)
    sheets/watchlist.csv  (ticker, ...)

Writes:
    data/market_data_{date}.json   — raw pull, for the AI analyst step
    Also prints a human-readable summary to stdout.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None  # allows --dry-run to work without the dependency installed

HOLDINGS_PATH = Path("sheets/holdings.csv")
WATCHLIST_PATH = Path("sheets/watchlist.csv")
OUTPUT_DIR = Path("data")

# How close (as a %) price needs to be to a target/stop before we flag it
PROXIMITY_THRESHOLD_PCT = 3.0


@dataclass
class TickerResult:
    ticker: str
    current_price: float | None
    entry_price: float | None = None
    stop_loss: float | None = None
    base_target: float | None = None
    bull_target: float | None = None
    gain_pct: float | None = None
    flag: str = "ok"  # ok | near_stop | near_base_target | near_bull_target | data_error


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fetch_price(ticker: str, dry_run_price: float | None = None) -> float | None:
    """Fetch last close price for an NSE-listed ticker via yfinance."""
    if dry_run_price is not None:
        return dry_run_price
    if yf is None:
        raise RuntimeError("yfinance not installed — run: pip install -r requirements.txt")
    try:
        hist = yf.Ticker(f"{ticker}.NS").history(period="1d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception as exc:  # noqa: BLE001 — surface any fetch failure as None, not a crash
        print(f"  ! failed to fetch {ticker}: {exc}", file=sys.stderr)
        return None


def pct_distance(price: float, level: float) -> float:
    return abs(price - level) / level * 100


def evaluate_holding(row: dict, price: float | None) -> TickerResult:
    ticker = row["ticker"]
    if price is None:
        return TickerResult(ticker=ticker, current_price=None, flag="data_error")

    entry = float(row["entry_price"]) if row.get("entry_price") else None
    stop = float(row["stop_loss"]) if row.get("stop_loss") else None
    base_t = float(row["base_target"]) if row.get("base_target") else None
    bull_t = float(row["bull_target"]) if row.get("bull_target") else None

    gain_pct = round((price - entry) / entry * 100, 2) if entry else None

    flag = "ok"
    if stop and pct_distance(price, stop) <= PROXIMITY_THRESHOLD_PCT:
        flag = "near_stop"
    elif bull_t and pct_distance(price, bull_t) <= PROXIMITY_THRESHOLD_PCT:
        flag = "near_bull_target"
    elif base_t and pct_distance(price, base_t) <= PROXIMITY_THRESHOLD_PCT:
        flag = "near_base_target"

    return TickerResult(
        ticker=ticker,
        current_price=price,
        entry_price=entry,
        stop_loss=stop,
        base_target=base_t,
        bull_target=bull_t,
        gain_pct=gain_pct,
        flag=flag,
    )


def main(dry_run: bool = False):
    holdings = read_csv_rows(HOLDINGS_PATH)
    watchlist = read_csv_rows(WATCHLIST_PATH)

    if not holdings and not watchlist:
        print("No holdings or watchlist found. Copy the *_template.csv files first.")
        return

    results: list[TickerResult] = []

    print("Fetching holdings...")
    for row in holdings:
        # dry-run uses the current_price already in the CSV so this is testable offline
        price = fetch_price(row["ticker"], dry_run_price=float(row["current_price"]) if dry_run else None)
        result = evaluate_holding(row, price)
        results.append(result)
        _print_result(result)

    print("\nFetching watchlist...")
    for row in watchlist:
        dry_price = float(row["current_price"]) if dry_run and row.get("current_price") else None
        price = fetch_price(row["ticker"], dry_run_price=dry_price)
        results.append(TickerResult(ticker=row["ticker"], current_price=price))
        print(f"  {row['ticker']}: {price if price is not None else 'no data'}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"market_data_{date.today()}.json"
    with open(out_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nWrote {len(results)} records to {out_path}")

    flagged = [r for r in results if r.flag != "ok"]
    if flagged:
        print("\n⚠️  Flags this run:")
        for r in flagged:
            print(f"  - {r.ticker}: {r.flag} (price {r.current_price})")


def _print_result(r: TickerResult):
    gain = f"{r.gain_pct:+.2f}%" if r.gain_pct is not None else "n/a"
    print(f"  {r.ticker}: price={r.current_price} gain={gain} flag={r.flag}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
