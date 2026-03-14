"""
fetch_fear_greed.py  [BONUS]

Fetches the full Crypto Fear & Greed Index history from the
alternative.me public API. No API key required.

This bonus dataset enables downstream analysis like:
  "Does bridging volume increase during Fear periods (buying dips)?"
  "Which bridges are preferred during high-Fear vs high-Greed markets?"

Joined to transfers on evt_block_date in the mart layer.
"""

import duckdb
import requests
import pandas as pd

DB_PATH = "lifi.duckdb"
FNG_URL = "https://api.alternative.me/fng/?limit=0"  # limit=0 returns full history


def fetch_fear_greed():
    conn = duckdb.connect(DB_PATH)

    print("Fetching Crypto Fear & Greed Index from alternative.me...")

    try:
        response = requests.get(FNG_URL, timeout=15)
        response.raise_for_status()

        data = response.json().get("data", [])

        df = pd.DataFrame(data)

        # Convert Unix timestamp to date
        df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date
        df["value"] = df["value"].astype(int)
        df = df[["date", "value", "value_classification"]].copy()
        df = df.sort_values("date").reset_index(drop=True)

        conn.execute("""
            CREATE OR REPLACE TABLE raw_fear_greed AS
            SELECT * FROM df
        """)

        print(f"✅ Loaded {len(df)} rows into raw_fear_greed")
        print(f"   Date range: {df['date'].min()} → {df['date'].max()}")
        print(f"\n   Score distribution:")
        print(df["value_classification"].value_counts().to_string())

    except Exception as e:
        print(f"✗ Fear & Greed API failed: {e}")

    conn.close()


if __name__ == "__main__":
    fetch_fear_greed()
