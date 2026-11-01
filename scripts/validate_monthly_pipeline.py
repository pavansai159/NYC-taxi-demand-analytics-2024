
import argparse
import csv
import math
import re
from pathlib import Path

import duckdb


# 1. Project paths
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "nyc_taxi.duckdb"
REPORTS = ROOT / "reports"


# 2. Receive and validate the month
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
    parser.error("Use YYYY-MM format")

if not DB.is_file():
    parser.error(f"Database missing: {DB}")


# 3. Define all monthly views
suffix = args.month.replace("-", "_")

raw_view = f"raw_{suffix}"
quality_view = f"quality_{suffix}"
enriched_view = f"enriched_{suffix}"
demand_view = f"demand_{suffix}"
revenue_view = f"revenue_{suffix}"

views = [
    raw_view,
    quality_view,
    enriched_view,
    demand_view,
    revenue_view
]

checks = []


# 4. Store validation results
def add_check(name, actual, expected, passed):
    checks.append({
        "month": args.month,
        "check": name,
        "actual": actual,
        "expected": expected,
        "status": "PASS" if passed else "FAIL"
    })


# 5. Read data from existing DuckDB
with duckdb.connect(str(DB), read_only=True) as con:

    existing = {
        row[0]
        for row in con.execute("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'main'
        """).fetchall()
    }

    for view in views:
        if view not in existing:
            parser.error(
                f"Missing view: {view}. "
                "Run the preceding pipeline scripts first."
            )

    # Count records in each view
    counts = {}

    for view in views:
        counts[view] = con.execute(
            f"SELECT COUNT(*) FROM {view}"
        ).fetchone()[0]

    # Count only in-month records from raw data
    start_date = args.month + "-01"

    expected_monthly = con.execute(f"""
        SELECT COUNT(*)
        FROM {raw_view}
        WHERE tpep_pickup_datetime >=
              CAST(? AS TIMESTAMP)
          AND tpep_pickup_datetime <
              CAST(? AS TIMESTAMP)
              + INTERVAL '1 month'
    """, [start_date, start_date]).fetchone()[0]

    # Check 1: January date filtering
    add_check(
        "Monthly filtering",
        counts[quality_view],
        expected_monthly,
        counts[quality_view] == expected_monthly
    )

    # Check 2: Geographic join record count
    add_check(
        "Geographic enrichment count",
        counts[enriched_view],
        counts[quality_view],
        counts[enriched_view] == counts[quality_view]
    )

    # Check 3: Demand record count
    add_check(
        "Demand view count",
        counts[demand_view],
        counts[enriched_view],
        counts[demand_view] == counts[enriched_view]
    )

    # Check 4: Revenue record count
    add_check(
        "Revenue view count",
        counts[revenue_view],
        counts[enriched_view],
        counts[revenue_view] == counts[enriched_view]
    )

    # Check 5: Total amount reconciliation
    source_total = con.execute(f"""
        SELECT SUM(total_amount)
        FROM {enriched_view}
    """).fetchone()[0]

    revenue_total = con.execute(f"""
        SELECT SUM(total_amount)
        FROM {revenue_view}
    """).fetchone()[0]

    source_total = float(source_total or 0)
    revenue_total = float(revenue_total or 0)

    money_matches = math.isclose(
        source_total,
        revenue_total,
        rel_tol=0,
        abs_tol=0.01
    )

    add_check(
        "Recorded total reconciliation",
        round(revenue_total, 2),
        round(source_total, 2),
        money_matches
    )

    # Check 6: Demand eligibility reconciliation
    expected_eligible = con.execute(f"""
        SELECT COUNT(*)
        FROM {enriched_view}
        WHERE COALESCE(NOT flag_invalid_distance, FALSE)
          AND COALESCE(NOT flag_invalid_duration, FALSE)
    """).fetchone()[0]

    actual_eligible = con.execute(f"""
        SELECT COUNT(*)
        FROM {demand_view}
        WHERE eligible_trip_activity
    """).fetchone()[0]

    add_check(
        "Eligible demand trips",
        actual_eligible,
        expected_eligible,
        actual_eligible == expected_eligible
    )


# 6. Save the results
REPORTS.mkdir(parents=True, exist_ok=True)

output = REPORTS / f"validation_{args.month.replace('-', '_')}.csv"

with output.open(
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "month",
            "check",
            "actual",
            "expected",
            "status"
        ]
    )

    writer.writeheader()
    writer.writerows(checks)


# 7. Print validation results
print("\n--- MONTHLY VALIDATION ---")
print("Month:", args.month)

print("\nRaw records:", counts[raw_view])
print("Monthly records:", counts[quality_view])

print(
    "Records excluded by month filter:",
    counts[raw_view] - expected_monthly
)

print("\n--- CHECK RESULTS ---")

for item in checks:
    print(
        f"{item['status']}: {item['check']}"
    )

print("\nReport saved:", output)

passed = sum(
    item["status"] == "PASS"
    for item in checks
)

print(f"\nValidation: {passed}/{len(checks)} passed")

if passed != len(checks):
    raise SystemExit("Validation failed!")

'''
Check	Why it matters
Monthly filtering	Confirms that the cleaning stage uses the correct reporting period
Geographic enrichment count	Detects record multiplication or loss during geographic joins
Demand view count	Ensures the demand view preserves its source records
Revenue view count	Ensures the revenue view preserves its source records
Recorded total reconciliation	Detects differences in recorded financial totals between views
Eligible demand trips	Checks whether the demand eligibility rule is consistently applied
'''
