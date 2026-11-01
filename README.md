# NYC Yellow Taxi Analysis | 2024

I built this project to answer a fairly simple question: **what can a year of NYC yellow-taxi trips tell us about when people travel, where rides start, and how trip charges and travel times vary?**

The data comes from the [NYC Taxi & Limousine Commission (TLC)](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). I worked with the January–December 2024 yellow-taxi trip files and TLC's taxi-zone lookup table.

The project started as a few SQL checks on January's data. I eventually turned those checks into a repeatable monthly process: inspect the files, flag questionable records, join location names, build analysis views, and export smaller tables for Power BI.

## What I looked at

- **Demand:** daily and hourly trip counts, including weekday/weekend patterns.
- **Locations:** the busiest pickup boroughs and zones, plus common pickup-to-drop-off routes.
- **Trip charges:** recorded totals, payment methods and tips.
- **Trip efficiency:** distance, duration and calculated average speed.
- **Data quality:** missing passenger counts, non-positive fares/distances, invalid durations and unusually high calculated speeds.

The Power BI report is saved in `dashboards/`. Its source tables are monthly CSV summaries in `reports/dashboard/`.

## Tools I used

| Tool | What I used it for |
| --- | --- |
| Python | Running the monthly scripts, validating inputs, logging and exporting reports |
| DuckDB + SQL | Querying Parquet files, creating reusable views, joining taxi zones and aggregating trips |
| Parquet | Keeping the original trip records in their downloaded format |
| Power BI / Power Query | Combining monthly reports and building the interactive dashboard |
| Git | Tracking the project code and documentation |

## How the data moves through the project

```text
NYC TLC Parquet files + taxi_zone_lookup.csv
                |
                v
       monthly_quality.py
       (checks + quality report)
                |
                v
       build_clean_data.py
        + SQL transformations
                |
                v
     nyc_taxi.duckdb (views)
                |
                v
     export_dashboard_data.py
                |
                v
     reports/dashboard/*.csv
                |
                v
          Power BI report
```

I use **DuckDB views**, rather than storing another full copy of every month's trips in the database. The views point back to the raw Parquet files, so those source files need to stay in place for queries to work.

A separate monthly quality script creates a CSV of quality metrics and writes run information to `logs/pipeline.log`. The quality report and the dashboard exports serve different purposes: one helps monitor the input data, while the others support analysis and visualization.

## A couple of checks that mattered

January's source file had **2,964,624 rows**, but **18 pickup timestamps were outside January**. After filtering to January pickup dates, the analysis view contained **2,964,606 trips**.

For January, **241,742 trips** had at least one of the quality flags used by the cleaning pipeline. For February, the corresponding figure was **288,635 out of 3,007,511 trips**. These are *flagged*, not automatically deleted, records.

I also checked for duplicate location IDs before joining the taxi-zone lookup, and verified that the joins didn't change the number of trip rows. In the January and February runs I checked, all pickup and drop-off IDs matched the lookup.

These checks helped catch problems that could otherwise quietly distort the dashboard totals.

## Project files

```text
scripts/
  inspect_data.py              # initial dataset exploration
  monthly_quality.py           # monthly quality checks and logging
  build_clean_data.py          # creates and validates DuckDB views
  run_analysis.py              # runs saved SQL analysis queries
  export_dashboard_data.py     # exports summary CSVs for Power BI
sql/                            # cleaning and analysis queries
reports/
  monthly_quality.csv          # monthly quality summary
  dashboard/                   # exported demand, payment, efficiency, etc. CSVs
database/
  nyc_taxi.duckdb              # local database; generated, not committed
data/raw/                       # downloaded Parquet files and zone lookup
dashboards/                     # Power BI .pbix report
docs/                           # assumptions and supporting notes
```

Some additional scripts and SQL files in the repository reflect earlier iterations of the monthly pipeline. The files listed above describe the main workflow.

## Running it locally

Install the Python packages:

```bash
pip install duckdb pandas pyarrow
```

Download the **2024 Yellow Taxi** Parquet files and `taxi_zone_lookup.csv` from the [TLC source page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), then put them in `data/raw/` using filenames such as `yellow_tripdata_2024-01.parquet`.

Run the following from the project root, changing the month as needed:

```bash
python scripts/monthly_quality.py --month 2024-01
python scripts/build_clean_data.py --month 2024-01
python scripts/export_dashboard_data.py --month 2024-01
```

The scripts write local run logs and monthly report files. To use the Power BI report on another machine, point its Folder data source to that machine's `reports/dashboard/` directory and refresh it.

The raw Parquet files and local DuckDB database are not meant to be committed to GitHub; the source data is available from TLC and the database views can be recreated by running the scripts.

## Things to keep in mind

- The dataset records **yellow-taxi trips**, not every journey or every request for transportation in NYC.
- A flagged fare, duration or speed isn't automatically a bad record; flags are prompts for investigation.
- `total_amount` is a recorded trip charge. It is **not taxi-operator profit**.
- Cash tips are not fully captured by the tip field, so comparisons of recorded tips by payment type need care.
- The dashboard CSVs are aggregated at different levels. Their trip counts shouldn't be added together across report types.
- Calculated speed can be affected by unusual timestamps, distance values and route characteristics; it is not a direct congestion measure.

## What I'd improve next

I'd like to add automated tests for the financial metrics, reduce overlap between early and final scripts, and make the Power BI data-source path easier to configure when someone else clones the repository.

---

**Data credit:** NYC Taxi & Limousine Commission, [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
