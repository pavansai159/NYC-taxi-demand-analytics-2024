
import argparse
import re
import logging
import time
from pathlib import Path

import duckdb


# ============================================
# 1. PROJECT PATHS
# ============================================

ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "database" / "nyc_taxi.duckdb"
OUTPUT_DIR = ROOT / "reports" / "dashboard"
LOG_DIR = ROOT / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# 2. ACCEPT MONTH FROM TERMINAL
# ============================================

parser = argparse.ArgumentParser(
    description="Export monthly NYC Taxi dashboard data"
)

parser.add_argument(
    "--month",
    required=True,
    help="Month in YYYY-MM format, e.g. 2024-01"
)

args = parser.parse_args()
month = args.month

if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
    parser.error("Use YYYY-MM format, e.g. 2024-01")

month_id = month.replace("-", "_")


# ============================================
# 3. DATABASE VIEW NAMES
# ============================================

demand = f"demand_trips_{month_id}"
revenue = f"revenue_trips_{month_id}"
quality = f"quality_trips_{month_id}"


# ============================================
# 4. CONFIGURE LOGGING
# ============================================

logging.basicConfig(
    filename=str(LOG_DIR / "pipeline.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

if not DB_PATH.is_file():
    raise FileNotFoundError(
        f"DuckDB database not found: {DB_PATH}"
    )

start_time = time.perf_counter()


# ============================================
# 5. DASHBOARD SQL QUERIES
# ============================================

queries = {

    # ----------------------------------------
    # A. DAILY DEMAND
    # ----------------------------------------
    "daily_demand": f"""
        SELECT
            pickup_date,
            COUNT(*) AS total_trips,
            COUNT(DISTINCT PULocationID)
                AS active_pickup_location_ids,
            ROUND(
                AVG(
                    CASE
                        WHEN trip_distance > 0
                        THEN trip_distance
                    END
                ), 2
            ) AS avg_positive_distance_miles
        FROM {demand}
        GROUP BY pickup_date
        ORDER BY pickup_date
    """,

    # ----------------------------------------
    # B. HOURLY DEMAND BY DAY TYPE
    # ----------------------------------------
    "hourly_demand": f"""
        SELECT
            pickup_hour,
            day_type,
            COUNT(*) AS total_trips
        FROM {demand}
        GROUP BY pickup_hour, day_type
        ORDER BY day_type, pickup_hour
    """,

    # ----------------------------------------
    # C. BOROUGH PERFORMANCE
    # ----------------------------------------
    "borough_performance": f"""
        SELECT
            d.pickup_borough,
            COUNT(*) AS total_trips,
            COUNT(DISTINCT d.PULocationID)
                AS active_pickup_location_ids
        FROM {demand} AS d
        GROUP BY d.pickup_borough
        ORDER BY total_trips DESC
    """,

    # ----------------------------------------
    # D. PAYMENT ANALYSIS
    # ----------------------------------------
    "payment_analysis": f"""
        SELECT
            payment_type,
            transaction_category,
            COUNT(*) AS total_trips,
            ROUND(SUM(total_amount), 2)
                AS recorded_total_amount,
            ROUND(SUM(positive_trip_amount), 2)
                AS positive_amount,
            ROUND(SUM(negative_adjustment_amount), 2)
                AS negative_amount,
            ROUND(SUM(tip_amount), 2)
                AS recorded_tips
        FROM {revenue}
        GROUP BY
            payment_type,
            transaction_category
        ORDER BY
            payment_type,
            transaction_category
    """,

    # ----------------------------------------
    # E. TRIP EFFICIENCY BY HOUR
    # ----------------------------------------
    "trip_efficiency": f"""
        SELECT
            pickup_hour,
            day_type,
            COUNT(*) AS total_trips,
            COUNT(speed_for_analysis)
                AS trips_with_valid_speed,
            ROUND(AVG(speed_for_analysis), 2)
                AS avg_speed_mph,
            ROUND(MEDIAN(speed_for_analysis), 2)
                AS median_speed_mph,
            ROUND(AVG(valid_trip_duration), 2)
                AS avg_valid_duration_minutes
        FROM {demand}
        GROUP BY pickup_hour, day_type
        ORDER BY day_type, pickup_hour
    """,

    # ----------------------------------------
    # F. MONTHLY DATA QUALITY SUMMARY
    # ----------------------------------------
    "quality_summary": f"""
        SELECT
            COUNT(*) AS total_trips,

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
                WHERE COALESCE(flag_speed_above_80, FALSE)
            ) AS speed_above_80,

            COUNT(*) FILTER (
                WHERE flag_missing_passengers
                   OR flag_zero_passengers
                   OR flag_invalid_distance
                   OR flag_non_positive_fare
                   OR flag_invalid_duration
                   OR flag_negative_or_missing_total
                   OR COALESCE(flag_speed_above_80, FALSE)
            ) AS flagged_trips

        FROM {quality}
    """
}


# ============================================
# 6. EXECUTE AND EXPORT
# ============================================

con = None

try:
    con = duckdb.connect(
        str(DB_PATH),
        read_only=True
    )

    # Verify required views exist before export.
    existing = {
        row[0]
        for row in con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()
    }

    required = {demand, revenue, quality}
    missing = required - existing

    if missing:
        raise ValueError(
            "Missing database views: "
            + ", ".join(sorted(missing))
            + ". Run build_clean_data.py first."
        )

    # Confirm the source month contains records.
    source_count = con.execute(
        f"SELECT COUNT(*) FROM {demand}"
    ).fetchone()[0]

    if source_count == 0:
        raise ValueError(
            f"No demand records found for {month}"
        )

    print(f"\nExporting dashboard data for {month}")
    print(f"Source demand records: {source_count}")

    for name, sql in queries.items():

        df = con.execute(sql).df()

        # Make each exported row identify its month.
        df.insert(0, "month", month)

        output_file = (
            OUTPUT_DIR / f"{name}_{month}.csv"
        )

        df.to_csv(
            output_file,
            index=False,
            encoding="utf-8"
        )

        print(
            f"Created: {output_file.name} "
            f"| Rows: {len(df)}"
        )

        logging.info(
            "Dashboard export | month=%s | "
            "file=%s | rows=%s",
            month,
            output_file.name,
            len(df)
        )

    elapsed = time.perf_counter() - start_time

    logging.info(
        "Dashboard export completed | "
        "month=%s | elapsed=%.2fs",
        month,
        elapsed
    )

    print("\nDASHBOARD EXPORT COMPLETED!")
    print(f"Files saved to: {OUTPUT_DIR}")
    print(f"Execution time: {elapsed:.2f} seconds")

except Exception:
    logging.exception(
        "Dashboard export failed | month=%s",
        month
    )
    raise

finally:
    if con is not None:
        con.close()
