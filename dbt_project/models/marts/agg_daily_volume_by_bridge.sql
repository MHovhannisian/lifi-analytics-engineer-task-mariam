/*
agg_daily_volume_by_bridge.sql

Daily bridging volume aggregated by bridge protocol.
Answers: "Which bridge protocols handle the most volume, and how is
          market share shifting over time?"

Grain: one row per (bridge_name, block_date)
*/

WITH base AS (
    SELECT * FROM {{ ref('fct_transfers_enriched') }}
)

SELECT
    bridge_name,
    block_date,

    -- Volume
    SUM(volume_usd)                             AS total_volume_usd,
    SUM(volume_eur)                             AS total_volume_eur,

    -- Transfer counts
    COUNT(*)                                    AS transfer_count,

    -- Chain breakdown within this bridge
    COUNT(DISTINCT source_chain)                AS source_chain_count,

    -- Average transfer size — useful for comparing retail vs institutional bridges
    AVG(volume_usd)                             AS avg_volume_usd,
    MEDIAN(volume_usd)                          AS median_volume_usd,

    -- Market sentiment
    MAX(fear_greed_score)                       AS fear_greed_score,
    MAX(fear_greed_label)                       AS fear_greed_label

FROM base
GROUP BY bridge_name, block_date
ORDER BY block_date, total_volume_usd DESC NULLS LAST
