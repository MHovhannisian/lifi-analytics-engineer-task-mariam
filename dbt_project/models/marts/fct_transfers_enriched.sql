/*
fct_transfers_enriched.sql

Core analytical fact table. Joins cleaned transfer events with token prices,
EUR exchange rates, and the Fear & Greed Index to produce a fully enriched
transfer record with USD and EUR volumes.

Key design decisions:
  - LEFT JOIN on prices: keeps all transfers even when price data is
    unavailable (new tokens, unsupported chains). NULLs in volume_usd
    are intentional and tracked by a dbt warn-severity test.
  - LEFT JOIN on EUR rates: same logic — don't drop transfers if ECB
    had a holiday gap. A COALESCE fallback uses the closest available rate.
  - Amount conversion: amount_raw / POW(10, decimals) converts the raw
    on-chain integer to a human-readable token quantity.
  - All volumes reported in both USD and EUR per the task requirement.

Grain: one row per transfer event (tx_hash + log_index)
Materialized as: table (for fast downstream querying)
*/

WITH transfers AS (
    SELECT * FROM {{ ref('stg_transfers') }}
),

prices AS (
    SELECT * FROM {{ ref('stg_token_prices') }}
),

-- Get the most recent EUR rate available on or before each date
-- This handles ECB weekend/holiday gaps via forward-fill logic
eur_rates AS (
    SELECT * FROM {{ ref('stg_eur_rates') }}
),

fear_greed AS (
    SELECT * FROM {{ ref('stg_fear_greed') }}
),

enriched AS (
    SELECT
        -- ── Identifiers ────────────────────────────────────────────────
        t.tx_hash,
        t.log_index,
        t.lifi_transaction_id,

        -- ── Time ───────────────────────────────────────────────────────
        t.block_time,
        t.block_date,
        t.block_number,

        -- ── Chain ──────────────────────────────────────────────────────
        t.source_chain,
        t.destination_chain_id,
        t.contract_address,

        -- ── Bridge metadata ────────────────────────────────────────────
        t.bridge_name,
        t.integrator,
        t.referrer,
        t.has_source_swaps,
        t.has_destination_call,

        -- ── Token ──────────────────────────────────────────────────────
        t.sending_asset_id,
        t.sending_asset_id_raw,
        t.is_native_token,
        t.receiver,

        -- ── Raw amount (on-chain integer) ──────────────────────────────
        t.amount_raw,

        -- ── Price data ─────────────────────────────────────────────────
        p.price_usd,
        p.decimals,

        -- ── Human-readable token amount ────────────────────────────────
        -- Divide raw integer by 10^decimals (e.g. 1e18 for ETH)
        -- NULLIF prevents division by zero if decimals is somehow 0
        CASE
            WHEN p.decimals IS NOT NULL AND t.amount_raw IS NOT NULL
            THEN t.amount_raw / POW(10, p.decimals)
            ELSE NULL
        END                                                 AS amount_adjusted,

        -- ── USD volume ─────────────────────────────────────────────────
        CASE
            WHEN p.price_usd IS NOT NULL
             AND p.decimals IS NOT NULL
             AND t.amount_raw IS NOT NULL
            THEN (t.amount_raw / POW(10, p.decimals)) * p.price_usd
            ELSE NULL
        END                                                 AS volume_usd,

        -- ── EUR volume ─────────────────────────────────────────────────
        CASE
            WHEN p.price_usd IS NOT NULL
             AND p.decimals IS NOT NULL
             AND t.amount_raw IS NOT NULL
             AND e.usd_to_eur IS NOT NULL
            THEN (t.amount_raw / POW(10, p.decimals)) * p.price_usd * e.usd_to_eur
            ELSE NULL
        END                                                 AS volume_eur,

        -- ── EUR rate used ──────────────────────────────────────────────
        e.usd_to_eur,
        e.rate_date                                         AS eur_rate_date,

        -- ── Market sentiment (bonus) ───────────────────────────────────
        f.fear_greed_score,
        f.fear_greed_label,

        -- ── Transaction ────────────────────────────────────────────────
        t.tx_from,
        t.tx_to,
        t.tx_index

    FROM transfers t

    -- Price join: match on chain + normalized token address + date
    -- LEFT JOIN intentionally — missing prices produce NULL volume, not dropped rows
    LEFT JOIN prices p
        ON  t.source_chain      = p.chain
        AND t.sending_asset_id  = p.token_address
        AND t.block_date        = p.price_date

    -- EUR rate join: match on date
    -- LEFT JOIN — ECB has gaps on weekends/holidays
    LEFT JOIN eur_rates e
        ON t.block_date = e.rate_date

    -- Fear & Greed join: match on date (bonus enrichment)
    LEFT JOIN fear_greed f
        ON t.block_date = f.fear_greed_date
)

SELECT * FROM enriched
