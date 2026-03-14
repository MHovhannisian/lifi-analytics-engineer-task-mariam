"""
fetch_eur_rates.py

Fetches daily USD → EUR exchange rates from the European Central Bank (ECB)
free public API. No API key required.

The ECB API returns EUR/USD rates (how many USD per 1 EUR).
We store usd_to_eur = 1 / eur_usd_rate so it can be directly multiplied
against USD volumes to get EUR volumes.

Date range: covers the full span of transfers in the data (Feb 1–9 2026),
with a buffer of a few extra days on each side for safety.
"""

import duckdb
import requests
import pandas as pd
from datetime import date

DB_PATH = "lifi.duckdb"

# ECB free API — returns daily EUR/USD rates
# USD per 1 EUR (e.g. 1.08 means 1 EUR = 1.08 USD)
ECB_URL = (
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "D.USD.EUR.SP00.A"
    "?format=csvdata&startPeriod=2026-01-25&endPeriod=2026-02-15"
)


def fetch_eur_rates():
    conn = duckdb.connect(DB_PATH)

    print("Fetching EUR/USD rates from ECB...")

    try:
        response = requests.get(ECB_URL, timeout=15)
        response.raise_for_status()

        # ECB returns CSV — parse it
        from io import StringIO
        df_raw = pd.read_csv(StringIO(response.text))

        # ECB CSV columns include TIME_PERIOD and OBS_VALUE
        df = df_raw[["TIME_PERIOD", "OBS_VALUE"]].copy()
        df.columns = ["rate_date", "eur_usd_rate"]
        df["rate_date"] = pd.to_datetime(df["rate_date"]).dt.date

        # ECB rate is USD per 1 EUR — invert to get EUR per 1 USD
        df["usd_to_eur"] = 1.0 / df["eur_usd_rate"]
        df = df.dropna(subset=["usd_to_eur"])

        conn.execute("""
            CREATE OR REPLACE TABLE raw_eur_rates AS
            SELECT * FROM df
        """)

        print(f"✅ Loaded {len(df)} EUR rate rows into raw_eur_rates")
        print(f"   Date range: {df['rate_date'].min()} → {df['rate_date'].max()}")
        print(f"   Sample rate: 1 USD = {df['usd_to_eur'].iloc[-1]:.4f} EUR")

    except Exception as e:
        print(f"✗ ECB API failed: {e}")
        print("  Falling back to static approximate rate (1 USD = 0.924 EUR)...")

        # Fallback: static rate covering our data's date range
        dates = pd.date_range("2026-01-25", "2026-02-15", freq="D")
        df = pd.DataFrame({
            "rate_date":    [d.date() for d in dates],
            "eur_usd_rate": [1.082] * len(dates),   # approximate Feb 2026 rate
            "usd_to_eur":   [1 / 1.082] * len(dates),
        })

        conn.execute("""
            CREATE OR REPLACE TABLE raw_eur_rates AS
            SELECT * FROM df
        """)
        print(f"✅ Loaded {len(df)} static fallback EUR rate rows into raw_eur_rates")

    conn.close()


if __name__ == "__main__":
    fetch_eur_rates()
