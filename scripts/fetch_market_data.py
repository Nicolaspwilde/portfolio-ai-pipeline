"""
Fetch current price/volume data for holdings + watchlist tickers.

TODO:
- Read tickers from sheets/holdings.csv and sheets/watchlist.csv
- Pull prices via yfinance (append .NS for NSE tickers)
- Write results to data/market_data_{date}.json
"""

import csv
import json
from datetime import date
from pathlib import Path

HOLDINGS_PATH = Path("sheets/holdings.csv")
OUTPUT_DIR = Path("data")


def read_tickers(path: Path) -> list[str]:
    with open(path, newline="") as f:
        return [row["ticker"] for row in csv.DictReader(f)]


def main():
    tickers = read_tickers(HOLDINGS_PATH)
    print(f"Would fetch market data for: {tickers}")
    # import yfinance as yf
    # data = {t: yf.Ticker(f"{t}.NS").info for t in tickers}
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"market_data_{date.today()}.json"
    print(f"Would write output to: {out_path}")


if __name__ == "__main__":
    main()
