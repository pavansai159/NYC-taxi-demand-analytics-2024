
import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "database" / "nyc_taxi.duckdb"
SQL_FILE = ROOT / "sql" / "02_demand_analysis.sql"

if not DB_PATH.exists():
    raise FileNotFoundError(DB_PATH)

if not SQL_FILE.exists():
    raise FileNotFoundError(SQL_FILE)

con = duckdb.connect(
    str(DB_PATH),
    read_only=True
)

try:
    sql_text = SQL_FILE.read_text(
        encoding="utf-8"
    )

    # Queries in this file do not contain
    # semicolons inside SQL strings.
    queries = [
        q.strip()
        for q in sql_text.split(";")
        if q.strip()
    ]

    for index, query in enumerate(queries, start=1):
        result = con.execute(query).df()

        print(f"\n{'=' * 45}")
        print(f"ANALYSIS {index}")
        print(f"{'=' * 45}")

        print(result.to_string(index=False))

finally:
    con.close()
