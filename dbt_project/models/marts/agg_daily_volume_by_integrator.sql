/*
agg_daily_volume_by_integrator.sql

Daily bridging volume aggregated by integrator (frontend application).
Answers: "Which partner integrators drive the most volume through LI.FI?"

Grain: one row per (integrator, block_date)
*/

WITH base AS (
    SELECT * FROM {{ ref('fct_transfers_enriched') }}
)

SELECT
    integrator,
    block_date,

    -- Volume
    SUM(volume_usd)                             AS total_volume_usd,
    SUM(volume_eur)                             AS total_volume_eur,

    -- Transfer counts
    COUNT(*)                                    AS transfer_count,

    -- Diversity metrics
    COUNT(DISTINCT source_chain)                AS chains_used,
    COUNT(DISTINCT bridge_name)                 AS bridges_used,

    -- Average transfer size
    AVG(volume_usd)                             AS avg_volume_usd,

    -- Market sentiment
    MAX(fear_greed_score)                       AS fear_greed_score,
    MAX(fear_greed_label)                       AS fear_greed_label

FROM base
GROUP BY integrator, block_date
ORDER BY block_date, total_volume_usd DESC NULLS LAST
