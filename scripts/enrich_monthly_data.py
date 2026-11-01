
import duckdb
import argparse
import re
from pathlib import Path

# Project locations
ROOT = Path(__file__).resolve().parents[1]

DB = ROOT / "database" / "nyc_taxi.duckdb"
ZONE_FILE = ROOT / "data" / "raw" / "taxi_zone_lookup.csv"

GEO_SQL = ROOT / "sql" / "04_geographic_enrichment.sql"

# Receive month
parser = argparse.ArgumentParser()

parser.add_argument(
    "--month",
    required=True,
    help="Example: 2024-01"
)

args = parser.parse_args()

if not re.fullmatch(
    r"\d{4}-(0[1-9]|1[0-2])",
    args.month
):
    parser.error("Month must be YYYY-MM")

# Validate required files
for path in [DB, ZONE_FILE, GEO_SQL]:
    if not path.is_file():
        parser.error(f"Required file missing: {path}")

# Define monthly view names
suffix = args.month.replace("-", "_")

quality_view = f"quality_{suffix}"
enriched_view = f"enriched_{suffix}"

# Open existing DuckDB database
con = duckdb.connect(str(DB))

try:
    # Confirm monthly cleaning view exists
    existing = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.views
        WHERE table_name = ?
          AND table_schema = 'main'
    """, [quality_view]).fetchone()[0]

    if existing == 0:
        raise ValueError(
            f"{quality_view} does not exist. "
            "Run build_monthly_data.py first."
        )

    # Register taxi zone lookup
    zone_path = ZONE_FILE.as_posix().replace("'", "''")

    con.execute(f"""
        CREATE OR REPLACE VIEW taxi_zones AS
        SELECT
            CAST(LocationID AS INTEGER) AS LocationID,
            Borough,
            Zone,
            service_zone
        FROM read_csv_auto('{zone_path}')
    """)

    # Verify unique location IDs
    duplicates = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT LocationID
            FROM taxi_zones
            GROUP BY LocationID
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    if duplicates > 0:
        raise ValueError(
            f"Found {duplicates} duplicate location IDs"
        )

    # Read SQL file
    geo_template = GEO_SQL.read_text(
        encoding="utf-8"
    )

    # Replace placeholders
    geo_query = geo_template.format(
        enriched_view=enriched_view,
        quality_view=quality_view
    )

    # Execute enrichment SQL
    con.execute(geo_query)

    # Validate record counts
    original_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {quality_view}
    """).fetchone()[0]

    enriched_count = con.execute(f"""
        SELECT COUNT(*)
        FROM {enriched_view}
    """).fetchone()[0]

    if original_count != enriched_count:
        raise ValueError(
            "Row count mismatch after geographic join!"
        )

    print("\nGeographic enrichment successful!")
    print("Month:", args.month)
    print("View:", enriched_view)
    print("Original records:", original_count)
    print("Enriched records:", enriched_count)
    print("Row count validation PASSED")

finally:
    con.close()
