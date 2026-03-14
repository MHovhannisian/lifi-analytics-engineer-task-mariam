import duckdb

conn = duckdb.connect("lifi.duckdb")

print("=== TABLES IN DATABASE ===")
tables = conn.execute("SHOW TABLES").fetchdf()
print(tables.to_string(index=False))

print("\n=== ROW COUNTS ===")
for t in ["raw_transfers", "raw_token_prices", "raw_eur_rates", "raw_fear_greed"]:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  ✅ {t}: {n} rows")
    except Exception as e:
        print(f"  ❌ {t}: {e}")

conn.close()
