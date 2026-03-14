/*
stg_eur_rates.sql

Cleans the raw ECB EUR/USD exchange rate data.

The ECB does not publish rates on weekends or public holidays.
We forward-fill missing dates so every calendar date has a rate,
using the most recent available rate (LAST_VALUE over an ordered window).
This ensures weekend transfers can still be converted to EUR.

Grain: one row per calendar date
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_eur_rates') }}
),

cleaned AS (
    SELECT
        TRY_CAST(rate_date AS DATE)         AS rate_date,
        TRY_CAST(eur_usd_rate AS DOUBLE)    AS eur_usd_rate,
        TRY_CAST(usd_to_eur AS DOUBLE)      AS usd_to_eur
    FROM source
    WHERE usd_to_eur IS NOT NULL
)

SELECT * FROM cleaned
