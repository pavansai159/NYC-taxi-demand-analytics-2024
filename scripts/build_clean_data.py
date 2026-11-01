
import argparse
import logging
import re
import time
from datetime import date
from pathlib import Path

import duckdb


# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = ROOT / "data" / "raw"
ZONE_FILE = RAW_DIR / "taxi_zone_lookup.csv"

DB_PATH = ROOT / "database" / "nyc_taxi.duckdb"
SQL_FILE = ROOT / "sql" / "01_cleaning.sql"
LOG_DIR = ROOT / "logs"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. ACCEPT MONTH FROM TERMINAL
# ==================================================

parser = argparse.ArgumentParser(
    description="NYC Taxi monthly cleaning pipeline"
)

parser.add_argument(
    "--month",
    required=True,
    help="Month in YYYY-MM format, e.g. 2024-01"
)

args = parser.parse_args()
month = args.month

if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
    parser.error("Invalid month format. Use YYYY-MM.")

year, month_number = map(int, month.split("-"))

start_date = date(year, month_number, 1)

if month_number == 12:
    end_date = date(year + 1, 1, 1)
else:
    end_date = date(year, month_number + 1, 1)


# ==================================================
# 3. VERIFY REQUIRED FILES
# ==================================================

RAW_FILE = RAW_DIR / f"yellow_tripdata_{month}.parquet"

if not RAW_FILE.is_file():
    raise FileNotFoundError(
        f"Monthly Parquet file not found: {RAW_FILE}"
    )

if not ZONE_FILE.is_file():
    raise FileNotFoundError(
        f"Taxi zone lookup not found: {ZONE_FILE}"
    )

if not SQL_FILE.is_file():
    raise FileNotFoundError(
        f"Cleaning SQL file not found: {SQL_FILE}"
    )


# ==================================================
# 4. CONFIGURE LOGGING
# ==================================================

logging.basicConfig(
    filename=str(LOG_DIR / "pipeline.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

start_time = time.perf_counter()

logging.info(
    "Pipeline started | month=%s",
    month
)


# ==================================================
# 5. PREPARE MONTHLY VIEW NAMES
# ==================================================

month_id = month.replace("-", "_")

raw_view = f"raw_trips_{month_id}"
quality_view = f"quality_trips_{month_id}"
enriched_view = f"enriched_trips_{month_id}"

demand_view = f"demand_trips_{month_id}"
revenue_view = f"revenue_trips_{month_id}"

raw_path = RAW_FILE.as_posix().replace("'", "''")
zone_path = ZONE_FILE.as_posix().replace("'", "''")


# ==================================================
# 6. READ AND PREPARE SQL
# ==================================================

sql_template = SQL_FILE.read_text(
    encoding="utf-8"
)

replacements = {
    "__RAW_VIEW__": raw_view,
    "__QUALITY_VIEW__": quality_view,
    "__ENRICHED_VIEW__": enriched_view,
    "__DEMAND_VIEW__": demand_view,
    "__REVENUE_VIEW__": revenue_view,
    "__RAW_PATH__": raw_path,
    "__ZONE_PATH__": zone_path,
    "__START_DATE__": start_date.isoformat(),
    "__END_DATE__": end_date.isoformat()
}

cleaning_sql = sql_template

for placeholder, value in replacements.items():
    cleaning_sql = cleaning_sql.replace(
        placeholder,
        value
    )

remaining = re.findall(
    r"__[A-Z][A-Z0-9_]*__",
    cleaning_sql
)

if remaining:
    raise ValueError(
        f"Unresolved SQL placeholders: {remaining}"
    )


# ==================================================
# 7. CONNECT TO DUCKDB
# ==================================================

con = None

try:
    con = duckdb.connect(str(DB_PATH))

    # ----------------------------------------------
    # 8. VALIDATE TAXI ZONE LOOKUP
    # ----------------------------------------------

    duplicate_zones = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT LocationID
            FROM read_csv_auto(?)
            GROUP BY LocationID
            HAVING COUNT(*) > 1
        )
    """, [str(ZONE_FILE)]).fetchone()[0]

    print("\n--- TAXI ZONE VALIDATION ---")
    print(f"Duplicate LocationIDs: {duplicate_zones}")

    if duplicate_zones > 0:
        raise ValueError(
            f"Found {duplicate_zones} duplicate LocationIDs"
        )

    # ----------------------------------------------
    # 9. EXECUTE SQL TRANSFORMATIONS
    # ----------------------------------------------

    con.execute(cleaning_sql)

    print("\nCleaning views created successfully!")
    print(f"Month: {month}")
    print(f"Raw view: {raw_view}")
    print(f"Quality view: {quality_view}")
    print(f"Enriched view: {enriched_view}")
    print(f"Demand view: {demand_view}")
    print(f"Revenue view: {revenue_view}")

    # ----------------------------------------------
    # 10. DATA QUALITY VALIDATION
    # ----------------------------------------------

    quality_result = con.execute(f"""
        SELECT
            COUNT(*) AS total_records,

            COUNT(*) FILTER (
                WHERE flag_missing_passengers
            ) AS missing_passengers,

            COUNT(*) FILTER (
                WHERE flag_zero_passengers
            ) AS zero_passengers,

            COUNT(*) FILTER (
                WHERE flag_invalid_distance
            ) AS invalid_distance,

            COUNT(*) FILTER (
                WHERE flag_non_positive_fare
            ) AS non_positive_fare,

            COUNT(*) FILTER (
                WHERE flag_invalid_duration
            ) AS invalid_duration,

            COUNT(*) FILTER (
                WHERE flag_negative_or_missing_total
            ) AS negative_or_missing_total,

            COUNT(*) FILTER (
                WHERE flag_speed_above_80
            ) AS speed_above_80,

            COUNT(*) FILTER (
                WHERE flag_missing_passengers
                   OR flag_zero_passengers
                   OR flag_invalid_distance
                   OR flag_non_positive_fare
                   OR flag_invalid_duration
                   OR flag_negative_or_missing_total
                   OR COALESCE(flag_speed_above_80, FALSE)
            ) AS records_with_flags

        FROM {quality_view}
    """).df()

    print("\n--- MONTHLY QUALITY VALIDATION ---")
    print(quality_result.T.to_string())

    actual = int(
        quality_result.iloc[0]["total_records"]
    )

    # ----------------------------------------------
    # 11. VERIFY MONTHLY ROW COUNT
    # ----------------------------------------------

    expected = con.execute(
        f"""
        SELECT COUNT(*)
        FROM {raw_view}
        WHERE tpep_pickup_datetime >= ?
          AND tpep_pickup_datetime < ?
        """,
        [start_date, end_date]
    ).fetchone()[0]

    if actual != expected:
        raise ValueError(
            f"Monthly row count mismatch: "
            f"expected={expected}, actual={actual}"
        )

    print("\nMonthly row count validation passed!")

    # ----------------------------------------------
    # 12. GEOGRAPHIC VALIDATION
    # ----------------------------------------------

    geo_result = con.execute(f"""
        SELECT
            COUNT(*) AS enriched_records,

            COUNT(*) FILTER (
                WHERE flag_unknown_pickup_zone
            ) AS unknown_pickups,

            COUNT(*) FILTER (
                WHERE flag_unknown_dropoff_zone
            ) AS unknown_dropoffs,

            COUNT(*) FILTER (
                WHERE pickup_borough IS NOT NULL
            ) AS known_pickup_boroughs,

            COUNT(*) FILTER (
                WHERE dropoff_borough IS NOT NULL
            ) AS known_dropoff_boroughs

        FROM {enriched_view}
    """).df()

    print("\n--- GEOGRAPHIC VALIDATION ---")
    print(geo_result.T.to_string())

    enriched_count = int(
        geo_result.iloc[0]["enriched_records"]
    )

    if enriched_count != actual:
        raise ValueError(
            f"Geographic JOIN changed row count: "
            f"before={actual}, after={enriched_count}"
        )

    print("\nGeographic validation passed!")

    # ----------------------------------------------
    # 13. TASK 6 - FINAL VIEW VALIDATION
    # ----------------------------------------------

    print("\n--- FINAL ANALYTICS VALIDATION ---")

    counts = con.execute(f"""
        SELECT
            (SELECT COUNT(*) FROM {quality_view})
                AS quality_records,

            (SELECT COUNT(*) FROM {enriched_view})
                AS enriched_records,

            (SELECT COUNT(*) FROM {demand_view})
                AS demand_records,

            (SELECT COUNT(*) FROM {revenue_view})
                AS revenue_records
    """).fetchone()

    (
        quality_count,
        enriched_count,
        demand_count,
        revenue_count
    ) = counts

    print(f"Quality records  : {quality_count}")
    print(f"Enriched records : {enriched_count}")
    print(f"Demand records   : {demand_count}")
    print(f"Revenue records  : {revenue_count}")

    if len(set(counts)) != 1:
        raise ValueError(
            "Row counts differ across analytical views."
        )

    if quality_count != actual:
        raise ValueError(
            "Unexpected analytical record count."
        )

    print("PASS: All analytical views preserve row counts.")

    # ----------------------------------------------
    # 14. REVENUE VALIDATION
    # ----------------------------------------------

    revenue_result = con.execute(f"""
        SELECT
            COUNT(*) AS total_transactions,

            COUNT(*) FILTER (
                WHERE transaction_category = 'Positive'
            ) AS positive_transactions,

            COUNT(*) FILTER (
                WHERE transaction_category = 'Negative'
            ) AS negative_transactions,

            COUNT(*) FILTER (
                WHERE transaction_category = 'Zero'
            ) AS zero_transactions,

            COUNT(*) FILTER (
                WHERE transaction_category = 'Missing'
            ) AS missing_transactions,

            ROUND(SUM(total_amount), 2)
                AS net_recorded_total,

            ROUND(SUM(positive_trip_amount), 2)
                AS positive_amount_total,

            ROUND(SUM(negative_adjustment_amount), 2)
                AS negative_amount_total

        FROM {revenue_view}
    """).df()

    print("\n--- REVENUE VALIDATION ---")
    print(revenue_result.T.to_string())

    r = revenue_result.iloc[0]

    categorized_total = (
        int(r["positive_transactions"])
        + int(r["negative_transactions"])
        + int(r["zero_transactions"])
        + int(r["missing_transactions"])
    )

    if categorized_total != revenue_count:
        raise ValueError(
            "Revenue categories do not reconcile."
        )

    print("PASS: Revenue categories reconcile.")

    # ----------------------------------------------
    # 15. DEMAND VALIDATION
    # ----------------------------------------------

    demand_result = con.execute(f"""
        SELECT
            MIN(pickup_date) AS first_pickup_date,
            MAX(pickup_date) AS last_pickup_date,

            COUNT(*) FILTER (
                WHERE pickup_hour NOT BETWEEN 0 AND 23
                   OR pickup_hour IS NULL
            ) AS invalid_pickup_hours,

            COUNT(*) FILTER (
                WHERE pickup_date < ?
                   OR pickup_date >= ?
            ) AS outside_requested_month

        FROM {demand_view}
    """, [start_date, end_date]).df()

    print("\n--- DEMAND VALIDATION ---")
    print(demand_result.T.to_string())

    d = demand_result.iloc[0]

    if (
        int(d["invalid_pickup_hours"]) != 0
        or int(d["outside_requested_month"]) != 0
    ):
        raise ValueError(
            "Invalid pickup dates or hours detected."
        )

    print("PASS: Demand dates and hours are valid.")

    # ----------------------------------------------
    # 16. LOG SUCCESS
    # ----------------------------------------------

    elapsed = time.perf_counter() - start_time

    flagged_records = int(
        quality_result.iloc[0]["records_with_flags"]
    )

    logging.info(
        "Pipeline completed | month=%s | "
        "rows=%s | flagged=%s | "
        "unknown_pickups=%s | "
        "unknown_dropoffs=%s | "
        "demand=%s | revenue=%s | "
        "elapsed=%.2fs",
        month,
        actual,
        flagged_records,
        int(geo_result.iloc[0]["unknown_pickups"]),
        int(geo_result.iloc[0]["unknown_dropoffs"]),
        demand_count,
        revenue_count,
        elapsed
    )

    print("\n================================")
    print("ALL PHASE 5 VALIDATIONS PASSED!")
    print("================================")
    print(f"Month: {month}")
    print(f"Records processed: {actual}")
    print(f"Flagged records: {flagged_records}")
    print(f"Execution time: {elapsed:.2f} seconds")

except Exception:
    logging.exception(
        "Pipeline failed | month=%s",
        month
    )
    raise

finally:
    if con is not None:
        con.close()
