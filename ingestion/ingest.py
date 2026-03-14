"""
ingest.py

Master ingestion script. Runs all ingestion steps in order:
  1. Load raw transfer events from CSV into DuckDB
  2. Fetch token prices from CoinGecko API
  3. Fetch USD/EUR exchange rates from ECB API
  4. Fetch Crypto Fear & Greed Index (bonus)

Run from the repo root:
    python ingestion/ingest.py

Or run individual steps:
    python ingestion/load_transfers.py
    python ingestion/fetch_prices.py
    python ingestion/fetch_eur_rates.py
    python ingestion/fetch_fear_greed.py
"""

import sys
import os

# Allow importing sibling scripts
sys.path.insert(0, os.path.dirname(__file__))

from load_transfers import load_transfers
from fetch_prices import fetch_all_prices
from fetch_eur_rates import fetch_eur_rates
from fetch_fear_greed import fetch_fear_greed


def main():
    print("=" * 55)
    print("  LI.FI Analytics — Data Ingestion Pipeline")
    print("=" * 55)

    print("\n[1/4] Loading transfer events from CSV...")
    print("-" * 55)
    load_transfers()

    print("\n[2/4] Fetching token prices from CoinGecko...")
    print("-" * 55)
    fetch_all_prices()

    print("\n[3/4] Fetching EUR exchange rates from ECB...")
    print("-" * 55)
    fetch_eur_rates()

    print("\n[4/4] Fetching Fear & Greed Index (bonus)...")
    print("-" * 55)
    fetch_fear_greed()

    print("\n" + "=" * 55)
    print("  ✅ Ingestion complete. Database: lifi.duckdb")
    print("=" * 55)


if __name__ == "__main__":
    main()
