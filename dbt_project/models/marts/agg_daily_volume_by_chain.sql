/*
agg_daily_volume_by_chain.sql

Daily bridging volume aggregated by source chain.
Answers: "Which chains drive the most bridging activity, and how does
          this change over time?"

Grain: one row per (source_chain, block_date)
*/

WITH base AS (
    SELECT * FROM {{ ref('fct_transfers_enriched') }}
)

SELECT
    source_chain,
    block_date,

    -- Volume
    SUM(volume_usd)                             AS total_volume_usd,
    SUM(volume_eur)                             AS total_volume_eur,

    -- Transfer counts
    COUNT(*)                                    AS transfer_count,
    COUNT(CASE WHEN volume_usd IS NOT NULL
               THEN 1 END)                      AS priced_transfer_count,
    COUNT(CASE WHEN volume_usd IS NULL
               THEN 1 END)                      AS unpriced_transfer_count,

    -- Average transfer size
    AVG(volume_usd)                             AS avg_volume_usd,

    -- Native token breakdown
    SUM(CASE WHEN is_native_token THEN 1 ELSE 0
        END)                                    AS native_token_transfers,
    SUM(CASE WHEN NOT is_native_token THEN 1
             ELSE 0 END)                        AS erc20_transfers,

    -- Market sentiment on this day (same for all rows on a date)
    MAX(fear_greed_score)                       AS fear_greed_score,
    MAX(fear_greed_label)                       AS fear_greed_label

FROM base
GROUP BY source_chain, block_date
ORDER BY block_date, total_volume_usd DESC NULLS LAST
