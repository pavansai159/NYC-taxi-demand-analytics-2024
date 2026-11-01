from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import logging
import re
import time
import duckdb

ROOT = Path(__file__).resolve().parent.parent
# __file__ :it refers to the python file currently being executed
# .resolve() : it returns the absolute path of the file 
# .parent : refers to the main folder and the file in which the script is located
# .parent.parent : refers to the projects root directory 
RAW = ROOT / 'data' / 'raw'
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports'
FIELDS = ['month','source_file','processed_at_utc','total_records','missing_passengers','non_positive_distance','non_positive_fare','negative_total','non_positive_duration','outside_month','missing_pickup_datetime','flagged_any','flagged_pct','elapsed_seconds']

def main():
    parser = argparse.ArgumentParser(description='Monthly NYC Yellow Taxi quality profiling')
    #this creates an object that knows how to read and validate command line arguements.
    parser.add_argument('--month', required=True, help='YYYY-MM, e.g. 2024-01')
    #"My script expects a named argument called --month, and the user must provide it."
    args = parser.parse_args()
    ''' 
    when we execute python scripts/monthly_quality.py --month 2024-01
    python makes the supplied value available as args.month, which we can use in our code.
    so for this execution args.month=="2024-01"
    '''
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', args.month):
        parser.error('--month must be YYYY-MM')
    source = RAW / f'yellow_tripdata_{args.month}.parquet'
    if not source.is_file():
        parser.error(f'File not found: {source}')
    LOGS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOGS / 'pipeline.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    start = time.perf_counter()
    logging.info('Started month=%s file=%s', args.month, source.name)
    try:
        con = duckdb.connect()
        # The path is passed as a parameter rather than interpolated into SQL.
        row = con.execute('''
            WITH flags AS (
              SELECT
                passenger_count IS NULL AS missing_passengers,
                trip_distance <= 0 AS non_positive_distance,
                fare_amount <= 0 AS non_positive_fare,
                total_amount < 0 AS negative_total,
                tpep_dropoff_datetime <= tpep_pickup_datetime AS non_positive_duration,
                tpep_pickup_datetime IS NULL AS missing_pickup_datetime,
                (tpep_pickup_datetime < CAST(? AS TIMESTAMP)
                 OR tpep_pickup_datetime >= CAST(? AS TIMESTAMP) + INTERVAL '1 month') AS outside_month
              FROM read_parquet(?)
            )
            SELECT COUNT(*) AS total_records,
              COUNT(*) FILTER (WHERE missing_passengers) AS missing_passengers,
              COUNT(*) FILTER (WHERE non_positive_distance) AS non_positive_distance,
              COUNT(*) FILTER (WHERE non_positive_fare) AS non_positive_fare,
              COUNT(*) FILTER (WHERE negative_total) AS negative_total,
              COUNT(*) FILTER (WHERE non_positive_duration) AS non_positive_duration,
              COUNT(*) FILTER (WHERE outside_month) AS outside_month,
              COUNT(*) FILTER (WHERE missing_pickup_datetime) AS missing_pickup_datetime,
              COUNT(*) FILTER (WHERE COALESCE(missing_passengers, FALSE)
                 OR COALESCE(non_positive_distance, FALSE)
                 OR COALESCE(non_positive_fare, FALSE)
                 OR COALESCE(negative_total, FALSE)
                 OR COALESCE(non_positive_duration, FALSE)
                 OR COALESCE(outside_month, FALSE)
                 OR COALESCE(missing_pickup_datetime, FALSE)) AS flagged_any
            FROM flags
        ''', [args.month + '-01', args.month + '-01', str(source)]).fetchone()
        con.close()
        metrics = dict(zip(FIELDS[3:12], row))
        metrics['flagged_pct'] = round(100 * metrics['flagged_any'] / metrics['total_records'], 2) if metrics['total_records'] else 0.0
        record = {'month': args.month, 'source_file': source.name,
                  'processed_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  **metrics, 'elapsed_seconds': round(time.perf_counter()-start, 2)}
        out = REPORTS / 'monthly_quality.csv'
        previous = []
        if out.exists():
            with out.open(newline='', encoding='utf-8') as f:
                previous = list(csv.DictReader(f))
        # Keep one latest result per month rather than duplicate rows on reruns.
        previous = [r for r in previous if r.get('month') != args.month]
        previous.append(record)
        previous.sort(key=lambda r: r['month'])
        with out.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(previous)
        logging.info('Completed month=%s rows=%s flagged=%s elapsed=%.2fs',
                     args.month, metrics['total_records'], metrics['flagged_any'], record['elapsed_seconds'])
        for key, value in record.items():
            print(f'{key}: {value}')
        print(f'\nReport saved to: {out}')
    except Exception:
        logging.exception('Failed month=%s', args.month)
        raise

if __name__ == '__main__':
    main()
#runs main() when this python file is executed directly.