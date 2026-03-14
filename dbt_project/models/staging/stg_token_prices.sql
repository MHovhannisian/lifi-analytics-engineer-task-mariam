/*
stg_token_prices.sql

Cleans and types the raw token price data fetched from CoinGecko.

Note on decimals: CoinGecko's market chart endpoint does not return token
decimals. We default to 18 (the EVM standard) for unknown tokens. Well-known
stablecoins (USDC, USDT) use 6 decimals and are handled via the
token_decimals seed. This is used in the mart to convert raw integer amounts
to human-readable values.

Grain: one row per (chain, token_address, price_date)
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_token_prices') }}
),

decimals AS (
    SELECT * FROM {{ ref('token_decimals') }}
),

cleaned AS (
    SELECT
        p.chain                                         AS chain,
        LOWER(p.token_address)                          AS token_address,
        LOWER(p.raw_address)                            AS raw_address,
        TRY_CAST(p.price_date AS DATE)                  AS price_date,
        TRY_CAST(p.price_usd AS DOUBLE)                 AS price_usd,
        COALESCE(d.decimals, 18)                        AS decimals

    FROM source p
    LEFT JOIN decimals d
        ON LOWER(p.token_address) = LOWER(d.token_address)

    WHERE p.price_usd IS NOT NULL
      AND p.price_usd > 0
)

SELECT * FROM cleaned
