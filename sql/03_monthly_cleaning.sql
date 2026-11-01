
-- PHASE 5: REUSABLE MONTHLY CLEANING
-- Placeholders are filled by Python.

-- Step 1: Register the month's raw data
CREATE OR REPLACE VIEW {raw_view} AS
SELECT *
FROM read_parquet('{parquet_path}');


-- Step 2: Calculate quality flags
CREATE OR REPLACE VIEW {quality_view} AS

WITH calculated AS (
    SELECT
        *,
        DATE_DIFF(
            'second',
            tpep_pickup_datetime,
            tpep_dropoff_datetime
        ) / 60.0 AS duration_minutes

    FROM {raw_view}

    WHERE tpep_pickup_datetime >=
          TIMESTAMP '{start_date}'
      AND tpep_pickup_datetime <
          TIMESTAMP '{start_date}' + INTERVAL '1 month'
)

SELECT
    *,

    passenger_count IS NULL
        AS flag_missing_passengers,

    passenger_count = 0
        AS flag_zero_passengers,

    (trip_distance IS NULL OR trip_distance <= 0)
        AS flag_invalid_distance,

    (fare_amount IS NULL OR fare_amount <= 0)
        AS flag_non_positive_fare,

    (total_amount IS NULL OR total_amount < 0)
        AS flag_negative_or_missing_total,

    (duration_minutes IS NULL OR duration_minutes <= 0)
        AS flag_invalid_duration,

    CASE
        WHEN duration_minutes > 0
             AND trip_distance > 0
        THEN ROUND(
            trip_distance * 60.0 / duration_minutes,
            2
        )
        ELSE NULL
    END AS speed_mph

FROM calculated;
