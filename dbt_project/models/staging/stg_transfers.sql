/*
stg_transfers.sql

Cleans and unpacks raw transfer events into a structured, typed model.

Key transformations:
  - Unpacks the bridgeData JSON column into individual columns
  - Normalizes sendingAssetId: replaces the zero-address (used for native
    tokens like ETH, xDAI) with the chain's wrapped token address so that
    price joins work downstream
  - Adds is_native_token flag for transparency
  - Lowercases all addresses for consistent joining
  - Uses TRY_CAST throughout to handle any malformed values gracefully
    (returns NULL instead of failing the entire model)

Grain: one row per transfer event (evt_tx_hash + evt_index)
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_transfers') }}
),

-- Seed that maps chain name → wrapped native token address
-- Used to resolve the zero-address to a priceable token
native_tokens AS (
    SELECT * FROM {{ ref('chain_native_tokens') }}
),

unpacked AS (
    SELECT
        -- Event identifiers
        evt_tx_hash                                                         AS tx_hash,
        evt_index                                                           AS log_index,
        evt_block_time                                                      AS block_time,
        evt_block_date                                                      AS block_date,
        evt_block_number                                                    AS block_number,
        evt_tx_from                                                         AS tx_from,
        evt_tx_to                                                           AS tx_to,
        evt_tx_index                                                        AS tx_index,
        LOWER(contract_address)                                             AS contract_address,
        chain                                                               AS source_chain,

        -- Unpack bridgeData JSON
        json_extract_string(bridgeData, '$.transactionId')                  AS lifi_transaction_id,
        json_extract_string(bridgeData, '$.bridge')                         AS bridge_name,
        json_extract_string(bridgeData, '$.integrator')                     AS integrator,
        json_extract_string(bridgeData, '$.referrer')                       AS referrer,
        LOWER(json_extract_string(bridgeData, '$.sendingAssetId'))          AS sending_asset_id_raw,
        LOWER(json_extract_string(bridgeData, '$.receiver'))                AS receiver,
        TRY_CAST(
            json_extract_string(bridgeData, '$.minAmount') AS DOUBLE
        )                                                                   AS amount_raw,
        TRY_CAST(
            json_extract_string(bridgeData, '$.destinationChainId') AS INTEGER
        )                                                                   AS destination_chain_id,
        TRY_CAST(
            json_extract_string(bridgeData, '$.hasSourceSwaps') AS BOOLEAN
        )                                                                   AS has_source_swaps,
        TRY_CAST(
            json_extract_string(bridgeData, '$.hasDestinationCall') AS BOOLEAN
        )                                                                   AS has_destination_call

    FROM source
),

-- Resolve zero-address to wrapped native token for price joins
with_normalized_address AS (
    SELECT
        u.*,

        -- Flag native token transfers for transparency
        CASE
            WHEN u.sending_asset_id_raw = '0x0000000000000000000000000000000000000000'
            THEN TRUE
            ELSE FALSE
        END                                                                 AS is_native_token,

        -- Replace zero-address with wrapped native token address
        -- Falls back to raw address if no mapping exists for this chain
        CASE
            WHEN u.sending_asset_id_raw = '0x0000000000000000000000000000000000000000'
            THEN COALESCE(n.wrapped_native_token_address, u.sending_asset_id_raw)
            ELSE u.sending_asset_id_raw
        END                                                                 AS sending_asset_id

    FROM unpacked u
    LEFT JOIN native_tokens n
        ON u.source_chain = n.chain_name
)

SELECT
    -- Identifiers
    tx_hash,
    log_index,
    lifi_transaction_id,

    -- Time
    block_time,
    block_date,
    block_number,

    -- Chain
    source_chain,
    contract_address,
    destination_chain_id,

    -- Token
    sending_asset_id,           -- normalized (zero-address replaced with wrapped)
    sending_asset_id_raw,       -- original from bridgeData, for auditability
    is_native_token,

    -- Amount (raw integer — divided by 10^decimals in the mart)
    amount_raw,

    -- Bridge metadata
    bridge_name,
    integrator,
    referrer,
    receiver,
    has_source_swaps,
    has_destination_call,

    -- Transaction
    tx_from,
    tx_to,
    tx_index

FROM with_normalized_address
