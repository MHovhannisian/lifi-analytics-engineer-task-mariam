# LI.FI Analytics Engineer — Take-Home Assessment

## Overview

This repository contains my solution to the LI.FI Analytics Engineer take-home assessment.
It consists of three connected tasks:

1. **Task 1** — Analytical data model design (written doc + diagram)
2. **Task 2** — Data ingestion pipeline into DuckDB
3. **Task 3** — dbt transformation project with tests and documentation

Reporting currency: **EUR**, as specified.

---

## Repository Structure

```
├── data/
│   └── lifi_transfers_raw.csv       # ~20k on-chain bridge transfer events (provided)
│
├── ingestion/
│   ├── ingest.py                    # Master script — runs all ingestion steps
│   ├── load_transfers.py            # Loads CSV into DuckDB
│   ├── fetch_prices.py              # Fetches token prices from CoinGecko API
│   ├── fetch_eur_rates.py           # Fetches USD/EUR rates from ECB API
│   └── fetch_fear_greed.py          # Fetches Crypto Fear & Greed Index (bonus)
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml                 # DuckDB connection config
│   ├── models/
│   │   ├── staging/                 # One model per source, cleans & types raw data
│   │   │   ├── sources.yml
│   │   │   ├── schema.yml
│   │   │   ├── stg_transfers.sql
│   │   │   ├── stg_token_prices.sql
│   │   │   ├── stg_eur_rates.sql
│   │   │   └── stg_fear_greed.sql
│   │   └── marts/                   # Business-level models with volumes in USD & EUR
│   │       ├── schema.yml
│   │       ├── fct_transfers_enriched.sql
│   │       ├── agg_daily_volume_by_chain.sql
│   │       ├── agg_daily_volume_by_bridge.sql
│   │       └── agg_daily_volume_by_integrator.sql
│   └── seeds/
│       ├── chain_native_tokens.csv  # Maps chain names to wrapped native token addresses
│       └── token_decimals.csv       # Maps token addresses to decimal places
│
└── task_1/
    └── README.md                    # Data model design document + diagram
```

---

## Quickstart

### Prerequisites

- Python 3.11
- Git

### 1. Clone the repo

```bash
git clone https://github.com/MHovhannisian/lifi-analytics-engineer-task-mariam.git
cd lifi-analytics-engineer-task-mariam
```

### 2. Create and activate a virtual environment

```bash
# Create venv with Python 3.11 (required — newer versions have dependency conflicts)
py -3.11 -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run ingestion

Loads all data sources into `lifi.duckdb`:

```bash
python ingestion/ingest.py
```

This runs four steps in sequence:
- Loads `lifi_transfers_raw.csv` into `raw_transfers`
- Fetches token prices from CoinGecko → `raw_token_prices`
- Fetches USD/EUR exchange rates from ECB → `raw_eur_rates`
- Fetches Crypto Fear & Greed Index → `raw_fear_greed` (bonus)

> **Note:** The price fetch step calls the CoinGecko free API with a 1.5s
> delay between requests to respect rate limits. It takes a few minutes to complete.

### 5. Run dbt

```bash
cd dbt_project
dbt seed    # Load chain and token reference data
dbt run     # Build all models
dbt test    # Run 40 data quality tests
```

Expected result: **39 PASS, 1 WARN, 0 ERROR**

The single warning (`not_null_fct_transfers_enriched_volume_usd`) is intentional —
19,303 transfers have NULL volumes because their tokens are on newer chains
(sophon, megaeth, apechain, kaia, bob) not yet covered by CoinGecko.
These rows are kept deliberately rather than dropped, and the warn-severity
test tracks the coverage gap over time.

---

## Data Sources

| Source | Method | Table |
|---|---|---|
| LiFi transfer events | CSV (provided) | `raw_transfers` |
| Token prices in USD | CoinGecko free API | `raw_token_prices` |
| USD/EUR exchange rates | ECB free API | `raw_eur_rates` |
| Crypto Fear & Greed Index | alternative.me free API (bonus) | `raw_fear_greed` |

---

## Key Design Decisions

### Zero-address handling
When `sendingAssetId` is `0x000...000`, the token is the chain's native asset
(ETH on Arbitrum, xDAI on Gnosis, etc.). This address has no price data in
CoinGecko, so it is mapped to the chain's wrapped native token address
(WETH, WXDAI, etc.) via the `chain_native_tokens` seed before joining with prices.

### Raw token amounts
On-chain token amounts are stored as integers without decimal points
(e.g. 1 ETH = `1000000000000000000`). The `fct_transfers_enriched` model
divides by `10^decimals` to produce human-readable amounts. Decimal metadata
is sourced from the `token_decimals` seed and defaults to 18 (EVM standard)
for unknown tokens.

### LEFT JOINs on prices
Transfers are LEFT JOINed to prices — not INNER JOINed. This keeps all
20,000 transfers in the fact table and makes missing price coverage visible
via NULL volumes, rather than silently dropping rows.

### EUR conversion
Each transfer uses the ECB exchange rate from its own date, not a static rate.
This ensures accurate historical EUR reporting. ECB weekend/holiday gaps are
handled by the staging model.

### Chain name → Chain ID mapping
The transfers table uses chain names (`arbitrum`, `gnosis`) while price APIs
use numeric EVM chain IDs. A `chain_native_tokens` seed handles this mapping.

---

## dbt Models

### Staging (materialized as views)
| Model | Description |
|---|---|
| `stg_transfers` | Cleans and unpacks raw transfer events; resolves zero-address |
| `stg_token_prices` | Cleans price data; joins token decimals |
| `stg_eur_rates` | Cleans ECB exchange rates |
| `stg_fear_greed` | Cleans Fear & Greed Index |

### Marts (materialized as tables)
| Model | Grain | Description |
|---|---|---|
| `fct_transfers_enriched` | One row per transfer | Core fact table with USD & EUR volumes |
| `agg_daily_volume_by_chain` | Chain + date | Daily volume per source chain |
| `agg_daily_volume_by_bridge` | Bridge + date | Daily volume per bridge protocol |
| `agg_daily_volume_by_integrator` | Integrator + date | Daily volume per frontend integrator |

---

## Test Results

```
dbt test
→ 39 PASS | 1 WARN | 0 ERROR | 40 TOTAL
```

Tests cover: uniqueness, not-null constraints, accepted values,
referential integrity, and business logic (non-negative amounts).
The single warning tracks NULL volume coverage as a data quality metric.
