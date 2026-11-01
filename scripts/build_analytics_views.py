
import duckdb
import argparse
import re
from pathlib import Path

# ---------------------------------
# STEP 1: PROJECT PATHS
# ---------------------------------

ROOT = Path(__file__).resolve().parents[1]

DB = ROOT / "database" / "nyc_taxi.duckdb"

SQL = ROOT / "sql" / "05_analytics_views.sql"


# ---------------------------------
# STEP 2: ACCEPT MONTH FROM TERMINAL
# ---------------------------------

parser = argparse.ArgumentParser(
    description="Build monthly NYC Taxi analytics views"
)

parser.add_argument(
    "--month",
    required=True,
    help="Example: 2024-01"
)

args = parser.parse_args()


# ---------------------------------
# STEP 3: VALIDATE MONTH
# ---------------------------------

if not re.fullmatch(
    r"\d{4}-(0[1-9]|1[0-2])",
    args.month
):
    parser.error("Month must be YYYY-MM")


# ---------------------------------
# STEP 4: CHECK REQUIRED FILES
# ---------------------------------

if not DB.is_file():
    parser.error(f"Database not found: {DB}")

if not SQL.is_file():
    parser.error(f"SQL file not found: {SQL}")


# ---------------------------------
# STEP 5: DEFINE MONTHLY VIEW NAMES
# ---------------------------------

suffix = args.month.replace("-", "_")

enriched_view = f"enriched_{suffix}"

demand_view = f"demand_{suffix}"

revenue_view = f"revenue_{suffix}"


# ---------------------------------
# STEP 6: CONNECT TO DUCKDB
# ---------------------------------

con = duckdb.connect(str(DB))

try:

    print("\nStarting analytics pipeline...")
    print("Processing month:", args.month)

    # ---------------------------------
    # STEP 7: VERIFY SOURCE VIEW
    # ---------------------------------

    existing = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.views
        WHERE table_schema = 'main'
          AND table_name = ?
    """, [enriched_view]).fetchone()[0]

    if existing == 0:
        raise ValueError(
            f"Missing view: {enriched_view}. "
            "Run enrich_monthly_data.py first."
        )

    # ---------------------------------
    # STEP 8: READ SQL TEMPLATE
    # ---------------------------------

    sql_template = SQL.read_text(
        encoding="utf-8"
    )

    # ---------------------------------
    # STEP 9: INSERT MONTHLY VIEW NAMES
    # ---------------------------------

    sql_query = sql_template.format(
        enriched_view=enriched_view,
        demand_view=demand_view,
        revenue_view=revenue_view
    )

    # ---------------------------------
    # STEP 10: EXECUTE SQL
    # ---------------------------------

    con.execute(sql_query)

    print("\nAnalytics views created successfully!")

    # ---------------------------------
    # STEP 11: COUNT RECORDS
    # ---------------------------------

    enriched_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {enriched_view}
    """).fetchone()[0]

    demand_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {demand_view}
    """).fetchone()[0]

    revenue_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {revenue_view}
    """).fetchone()[0]

    print("\n--- ANALYTICS VIEW VALIDATION ---")

    print("Enriched records:", enriched_count)
    print("Demand records:", demand_count)
    print("Revenue records:", revenue_count)

    # ---------------------------------
    # STEP 12: VALIDATE RECORD COUNTS
    # ---------------------------------

    if enriched_count != demand_count:
        raise ValueError(
            "Demand view count mismatch!"
        )

    if enriched_count != revenue_count:
        raise ValueError(
            "Revenue view count mismatch!"
        )

    print("\nRow count validation PASSED")

    print("\nCreated views:")
    print(demand_view)
    print(revenue_view)

except Exception as error:
    print("\nPipeline failed:", error)
    raise

finally:
    con.close()
