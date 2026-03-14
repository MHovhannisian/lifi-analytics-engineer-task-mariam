import duckdb
import json

conn = duckdb.connect()

print("=== UNIQUE CHAINS ===")
df = conn.execute("""
    SELECT chain, COUNT(*) as transfer_count
    FROM read_csv_auto('data/lifi_transfers_raw.csv')
    GROUP BY chain
    ORDER BY transfer_count DESC
""").fetchdf()
print(df.to_string())

print("\n=== DATE RANGE ===")
df2 = conn.execute("""
    SELECT
        MIN(evt_block_date) as earliest,
        MAX(evt_block_date) as latest,
        COUNT(*) as total_rows
    FROM read_csv_auto('data/lifi_transfers_raw.csv')
""").fetchdf()
print(df2.to_string())

print("\n=== UNIQUE TOKENS (sendingAssetId) ===")
df3 = conn.execute("""
    SELECT
        chain,
        json_extract_string(bridgeData, '$.sendingAssetId') as token_address,
        COUNT(*) as count
    FROM read_csv_auto('data/lifi_transfers_raw.csv')
    GROUP BY chain, token_address
    ORDER BY chain, count DESC
""").fetchdf()
print(df3.to_string())

print("\n=== ZERO-ADDRESS COUNT (native tokens) ===")
df4 = conn.execute("""
    SELECT
        chain,
        COUNT(*) as native_token_transfers
    FROM read_csv_auto('data/lifi_transfers_raw.csv')
    WHERE json_extract_string(bridgeData, '$.sendingAssetId') = '0x0000000000000000000000000000000000000000'
    GROUP BY chain
    ORDER BY native_token_transfers DESC
""").fetchdf()
print(df4.to_string())

print("\n=== UNIQUE BRIDGES ===")
df5 = conn.execute("""
    SELECT
        json_extract_string(bridgeData, '$.bridge') as bridge_name,
        COUNT(*) as count
    FROM read_csv_auto('data/lifi_transfers_raw.csv')
    GROUP BY bridge_name
    ORDER BY count DESC
""").fetchdf()
print(df5.to_string())

print("\n=== UNIQUE INTEGRATORS ===")
df6 = conn.execute("""
    SELECT
        json_extract_string(bridgeData, '$.integrator') as integrator,
        COUNT(*) as count
    FROM read_csv_auto('data/lifi_transfers_raw.csv')
    GROUP BY integrator
    ORDER BY count DESC
    LIMIT 15
""").fetchdf()
print(df6.to_string())
