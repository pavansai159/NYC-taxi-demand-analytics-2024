
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPORT_DIR = ROOT / "reports" / "dashboard ready csvs"

MONTHS = [f"2024-{m:02d}" for m in range(1, 13)]

DATASETS = [
    "daily_demand",
    "hourly_demand",
    "borough_performance",
    "payment_analysis",
    "trip_efficiency",
    "quality_summary",
]


def load_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"Empty export: {path.name}")

    return rows


def sum_trips(rows, column="total_trips"):
    return sum(int(row[column]) for row in rows)


grand_total = 0
errors = []

print("\nNYC TAXI 2024 - FULL YEAR VALIDATION")
print("=" * 65)

for month in MONTHS:
    try:
        data = {}

        for name in DATASETS:
            path = REPORT_DIR / f"{name}_{month}.csv"
            data[name] = load_csv(path)

            # Check the month identifier in exported rows.
            if any(row.get("month") != month for row in data[name]):
                raise ValueError(
                    f"Incorrect month in {path.name}"
                )

        daily = sum_trips(data["daily_demand"])
        hourly = sum_trips(data["hourly_demand"])
        borough = sum_trips(data["borough_performance"])
        payment = sum_trips(data["payment_analysis"])
        efficiency = sum_trips(data["trip_efficiency"])

        quality = int(
            data["quality_summary"][0]["total_trips"]
        )

        counts = {
            "daily": daily,
            "hourly": hourly,
            "borough": borough,
            "payment": payment,
            "efficiency": efficiency,
            "quality": quality,
        }

        if len(data["quality_summary"]) != 1:
            raise ValueError(
                "Expected one quality-summary row"
            )

        if len(set(counts.values())) != 1:
            raise ValueError(
                f"Trip counts do not match: {counts}"
            )

        if daily <= 0:
            raise ValueError("Month has zero trips")

        grand_total += daily

        print(f"{month} | {daily:>10,} trips | PASS")

    except Exception as error:
        errors.append(f"{month}: {error}")
        print(f"{month} | FAIL | {error}")


print("=" * 65)
print(f"Validated months: {12 - len(errors)}/12")

if errors:
    print("\nVALIDATION FAILED")
    for error in errors:
        print(error)
    raise SystemExit(1)

print(f"FULL-YEAR TRIPS: {grand_total:,}")
print("ALL 12 MONTHS VALIDATED SUCCESSFULLY!")
