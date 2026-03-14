import duckdb

conn = duckdb.connect()

print("=== COLUMNS ===")
df = conn.execute("DESCRIBE SELECT * FROM read_csv_auto('data/lifi_transfers_raw.csv')").fetchdf()
print(df.to_string())

print("\n=== SAMPLE ROWS (transposed) ===")
df2 = conn.execute("SELECT * FROM read_csv_auto('data/lifi_transfers_raw.csv') LIMIT 3").fetchdf()
print(df2.T.to_string())
