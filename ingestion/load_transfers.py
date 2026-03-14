"""
load_transfers.py
Loads lifi_transfers_raw.csv into DuckDB as the raw_transfers table.
"""

import duckdb

DB_PATH = "lifi.duckdb"
CSV_PATH = "data/lifi_transfers_raw.csv"


def load_transfers():
    conn = duckdb.connect(DB_PATH)

    conn.execute(f"""
        CREATE OR REPLACE TABLE raw_transfers AS
        SELECT * FROM read_csv_auto('{CSV_PATH}', header=True)
    """)

    count = conn.execute("SELECT COUNT(*) FROM raw_transfers").fetchone()[0]
    chains = conn.execute(
        "SELECT chain, COUNT(*) as n FROM raw_transfers GROUP BY chain ORDER BY n DESC"
    ).fetchdf()

    print(f"✅ Loaded {count} rows into raw_transfers")
    print("\nRows per chain:")
    print(chains.to_string(index=False))

    conn.close()


if __name__ == "__main__":
    load_transfers()
