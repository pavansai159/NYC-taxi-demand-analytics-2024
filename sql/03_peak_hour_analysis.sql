
import argparse
from pathlib import Path

import duckdb


# 1. Project paths
ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "database" / "nyc_taxi.duckdb"
SQL_DIR = ROOT / "sql"


# 2. Accept SQL filename
parser = argparse.ArgumentParser(
    description="Run NYC Taxi SQL analytics"
)

parser.add_argument(
    "--file",
    required=True,
    help="SQL filename, e.g. 03_peak_hour_analysis.sql"
)

args = parser.parse_args()

# Allow only a filename inside our SQL folder
sql_name = Path(args.file).name

if sql_name != args.file or not sql_name.endswith(".sql"):
    parser.error("Provide a .sql filename only.")

SQL_FILE = SQL_DIR / sql_name


# 3. Check required files
if not DB_PATH.is_file():
    raise FileNotFoundError(DB_PATH)

if not SQL_FILE.is_file():
    raise FileNotFoundError(SQL_FILE)


# 4. Connect to DuckDB
con = duckdb.connect(
    str(DB_PATH),
    read_only=True
)

try:
    sql_text = SQL_FILE.read_text(
        encoding="utf-8"
    )

    # Simple splitting for our current SQL files.
    queries = [
        query.strip()
        for query in sql_text.split(";")
        if query.strip()
    ]

    # 5. Execute and display results
    for index, query in enumerate(queries, start=1):

        result = con.execute(query).df()

        print("\n" + "=" * 50)
        print(f"QUERY {index}")
        print("=" * 50)

        print(result.to_string(index=False))

finally:
    con.close()

print("\nAnalysis completed successfully!")
