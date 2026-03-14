"""
fetch_prices.py

Fetches historical daily USD prices for every token that appears in the
transfers data, using the CoinGecko free API (no key required).

Strategy:
  1. Read unique (chain, token_address) pairs from raw_transfers in DuckDB
  2. Map chain names to CoinGecko platform IDs
  3. For each token, call the CoinGecko contract address endpoint
  4. Load all prices into DuckDB as raw_token_prices

Native tokens (zero-address) are mapped to their wrapped equivalents
per chain so the price join works downstream.

Rate limiting: CoinGecko free tier allows ~10-30 req/min.
We sleep 1.5s between calls to stay safely under the limit.
"""

import time
import duckdb
import requests
import pandas as pd

DB_PATH = "lifi.duckdb"

# Map from chain name in our data → CoinGecko platform ID
# Source: https://api.coingecko.com/api/v3/asset_platforms
CHAIN_TO_PLATFORM = {
    "arbitrum":  "arbitrum-one",
    "gnosis":    "xdai",
    "mantle":    "mantle",
    "kaia":      "kaia",
    "bob":       "bob",
    "apechain":  "apechain",
    "sophon":    "sophon",
    "megaeth":   "megaeth",  # very new chain, may not be on CoinGecko yet
    "stable":    None,       # unknown/test chain, skip
}

# Map zero-address native tokens to their wrapped token address per chain.
# These are the addresses CoinGecko has price data for.
NATIVE_TOKEN_MAP = {
    "arbitrum": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",  # WETH on Arbitrum
    "gnosis":   "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d",  # WXDAI on Gnosis
    "mantle":   "0x78c1b0c915c4faa5fffa6cabf0219da63d7f4cb8",  # WMNT on Mantle
    "kaia":     "0x19aac5f612f524b754ca7e7c41cbfa2e981a4432",  # WKAIA on Kaia
    "bob":      "0x4200000000000000000000000000000000000006",  # WETH on BOB
    "apechain": "0x48b62137edfa95a428d35c09e44256a739f6b557",  # WAPE on ApeChain
    "sophon":   None,  # Sophon is a ZK chain — native token pricing may not exist yet
    "megaeth":  "0x4200000000000000000000000000000000000006",  # WETH on MegaETH
}

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"


def get_token_list(conn):
    """Extract unique (chain, token_address) pairs from raw_transfers."""
    df = conn.execute("""
        SELECT DISTINCT
            chain,
            LOWER(json_extract_string(bridgeData, '$.sendingAssetId')) AS token_address
        FROM raw_transfers
        WHERE json_extract_string(bridgeData, '$.sendingAssetId') IS NOT NULL
    """).fetchdf()
    return df


def normalize_token_address(chain, address):
    """
    Replace zero-address with the chain's wrapped native token address.
    Returns None if the chain has no mapping (skip it).
    """
    if address == ZERO_ADDRESS:
        return NATIVE_TOKEN_MAP.get(chain)
    return address


def fetch_price_history(platform_id, token_address, days=30):
    """
    Call CoinGecko's contract address market chart endpoint.
    Returns list of (date, price_usd) tuples, or empty list on failure.
    """
    url = f"{COINGECKO_BASE}/coins/{platform_id}/contract/{token_address}/market_chart"
    params = {"vs_currency": "usd", "days": days}

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            prices = response.json().get("prices", [])
            return [
                (
                    pd.to_datetime(ts, unit="ms").date(),
                    price
                )
                for ts, price in prices
            ]
        elif response.status_code == 429:
            print("    ⚠️  Rate limited — waiting 60 seconds...")
            time.sleep(60)
            return fetch_price_history(platform_id, token_address, days)
        else:
            print(f"    ✗ HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"    ✗ Request failed: {e}")
        return []


def fetch_all_prices():
    conn = duckdb.connect(DB_PATH)
    tokens_df = get_token_list(conn)

    print(f"Found {len(tokens_df)} unique (chain, token) pairs in raw_transfers\n")

    all_prices = []
    skipped = []

    for _, row in tokens_df.iterrows():
        chain = row["chain"]
        raw_address = row["token_address"]

        # Normalize zero-address to wrapped native token
        address = normalize_token_address(chain, raw_address)

        platform_id = CHAIN_TO_PLATFORM.get(chain)

        if platform_id is None:
            print(f"⏭️  Skipping {chain} — no CoinGecko platform mapping")
            skipped.append((chain, raw_address, "no platform mapping"))
            continue

        if address is None:
            print(f"⏭️  Skipping native token on {chain} — no wrapped token mapping")
            skipped.append((chain, raw_address, "no native token mapping"))
            continue

        label = "native→wrapped" if raw_address == ZERO_ADDRESS else address[:10] + "..."
        print(f"Fetching {chain} / {label}")

        prices = fetch_price_history(platform_id, address, days=30)

        if prices:
            for date, price_usd in prices:
                all_prices.append({
                    "chain":          chain,
                    "token_address":  address,
                    "raw_address":    raw_address,   # keep original for traceability
                    "price_date":     date,
                    "price_usd":      price_usd,
                })
            print(f"    ✓ {len(prices)} price points")
        else:
            print(f"    ✗ No prices returned")
            skipped.append((chain, address, "no price data returned"))

        time.sleep(1.5)  # Stay under CoinGecko free tier rate limit

    # Load into DuckDB
    if all_prices:
        df = pd.DataFrame(all_prices)
        conn.execute("CREATE OR REPLACE TABLE raw_token_prices AS SELECT * FROM df")
        print(f"\n✅ Loaded {len(df)} price rows into raw_token_prices")
        print(f"   Covering {df['chain'].nunique()} chains and {df['token_address'].nunique()} tokens")
    else:
        print("\n⚠️  No prices were fetched — raw_token_prices table not created")

    # Report skipped tokens
    if skipped:
        print(f"\n⏭️  Skipped {len(skipped)} tokens:")
        for chain, addr, reason in skipped:
            print(f"   {chain} / {addr[:20]}... → {reason}")

    conn.close()


if __name__ == "__main__":
    fetch_all_prices()
