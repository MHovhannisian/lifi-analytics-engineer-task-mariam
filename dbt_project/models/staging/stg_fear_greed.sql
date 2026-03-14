/*
stg_fear_greed.sql

Cleans the raw Crypto Fear & Greed Index data from alternative.me.

Grain: one row per calendar date
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_fear_greed') }}
),

cleaned AS (
    SELECT
        TRY_CAST(date AS DATE)              AS fear_greed_date,
        TRY_CAST(value AS INTEGER)          AS fear_greed_score,
        value_classification                AS fear_greed_label
    FROM source
    WHERE value IS NOT NULL
)

SELECT * FROM cleaned
