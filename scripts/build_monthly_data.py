
import duckdb
import argparse
import logging
import re
from pathlib import Path

# 1. Define project locations
ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data" / "raw"
DB = ROOT / "database" / "nyc_taxi.duckdb"
SQL = ROOT / "sql" / "03_monthly_cleaning.sql"
LOGS = ROOT / "logs"

# 2. Accept month from terminal
parser = argparse.ArgumentParser()

parser.add_argument(
    "--month",
    required=True,
    help="Example: 2024-01"
)

args = parser.parse_args()

# 3. Validate month format
if not re.fullmatch(
    r"\d{4}-(0[1-9]|1[0-2])",
    args.month
):
    parser.error("Month must be YYYY-MM")

# 4. Identify the month's data
source = RAW / f"yellow_tripdata_{args.month}.parquet"

if not source.exists():
    parser.error(f"File not found: {source}")

# 5. Prepare view names
suffix = args.month.replace("-", "_")

raw_view = f"raw_{suffix}"
quality_view = f"quality_{suffix}"

# 6. Create database and log folders
DB.parent.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOGS / "pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

con = duckdb.connect(str(DB))

try:
    logging.info(
        "Starting monthly build: %s",
        args.month
    )

    # 7. Read reusable SQL file
    sql_template = SQL.read_text(
        encoding="utf-8"
    )

    # 8. Substitute month-specific values
    sql_query = sql_template.format(
        raw_view=raw_view,
        quality_view=quality_view,
        parquet_path=source.as_posix().replace("'", "''"),
        start_date=args.month + "-01"
    )

    # 9. Execute SQL transformations
    con.execute(sql_query)

    # 10. Validate the created views
    result = con.execute(f"""
        SELECT
            (SELECT COUNT(*) FROM {raw_view})
                AS raw_records,

            (SELECT COUNT(*) FROM {quality_view})
                AS monthly_records,

            (SELECT COUNT(*) FILTER (
                WHERE flag_invalid_distance
            ) FROM {quality_view})
                AS invalid_distance,

            (SELECT COUNT(*) FILTER (
                WHERE flag_invalid_duration
            ) FROM {quality_view})
                AS invalid_duration
    """).df()

    print("\n--- MONTHLY BUILD RESULTS ---")
    print("Month:", args.month)
    print(result.T.to_string())

    logging.info(
        "Monthly build completed: %s",
        args.month
    )

finally:
    con.close()
