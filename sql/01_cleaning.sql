
-- NYC TAXI ANALYTICS
-- PHASE 5 - TASK 3
-- REUSABLE MONTHLY DATA CLEANING


-- ----------------------------------------
-- 1. CREATE MONTHLY RAW VIEW
-- ----------------------------------------

CREATE OR REPLACE VIEW __RAW_VIEW__ AS
SELECT *
FROM read_parquet('__RAW_PATH__');


-- ----------------------------------------
-- 2. CREATE MONTHLY QUALITY VIEW
-- ----------------------------------------

CREATE OR REPLACE VIEW __QUALITY_VIEW__ AS

WITH monthly_trips AS (

    SELECT *
    FROM __RAW_VIEW__

    WHERE tpep_pickup_datetime >=
          TIMESTAMP '__START_DATE__'

      AND tpep_pickup_datetime <
          TIMESTAMP '__END_DATE__'

),

calculated AS (

    SELECT
        *,

        DATE_DIFF(
            'second',
            tpep_pickup_datetime,
            tpep_dropoff_datetime
        ) / 60.0 AS duration_minutes

    FROM monthly_trips

),

quality_flags AS (

    SELECT
        *,

        (passenger_count IS NULL)
            AS flag_missing_passengers,

        (passenger_count = 0)
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

    FROM calculated

)

SELECT
    *,

    (speed_mph > 80)
        AS flag_speed_above_80

FROM quality_flags;

-- ----------------------------------------
-- PHASE 5 - TASK 4
-- GEOGRAPHIC ENRICHMENT
-- ----------------------------------------

CREATE OR REPLACE VIEW __ENRICHED_VIEW__ AS

SELECT
    t.*,

    -- Pickup location details
    pu.Borough AS pickup_borough,
    pu.Zone AS pickup_zone,

    -- Drop-off location details
    dz.Borough AS dropoff_borough,
    dz.Zone AS dropoff_zone,

    -- Geographic quality flags
    (pu.LocationID IS NULL)
        AS flag_unknown_pickup_zone,

    (dz.LocationID IS NULL)
        AS flag_unknown_dropoff_zone

FROM __QUALITY_VIEW__ AS t

LEFT JOIN read_csv_auto(
    '__ZONE_PATH__'
) AS pu
    ON t.PULocationID = pu.LocationID

LEFT JOIN read_csv_auto(
    '__ZONE_PATH__'
) AS dz
    ON t.DOLocationID = dz.LocationID;

-- ================================================
-- PHASE 5 - TASK 5
-- DEMAND AND REVENUE ANALYTICS VIEWS
-- ================================================


-- 1. DEMAND ANALYTICS VIEW

CREATE OR REPLACE VIEW __DEMAND_VIEW__ AS

SELECT
    tpep_pickup_datetime,
    tpep_dropoff_datetime,

    CAST(tpep_pickup_datetime AS DATE)
        AS pickup_date,

    EXTRACT(
        HOUR FROM tpep_pickup_datetime
    ) AS pickup_hour,

    EXTRACT(
        DOW FROM tpep_pickup_datetime
    ) AS pickup_day_of_week,

    CASE
        WHEN EXTRACT(
            DOW FROM tpep_pickup_datetime
        ) IN (0, 6)
        THEN 'Weekend'
        ELSE 'Weekday'
    END AS day_type,

    PULocationID,
    pickup_borough,
    pickup_zone,

    DOLocationID,
    dropoff_borough,
    dropoff_zone,

    passenger_count,
    trip_distance,
    duration_minutes,

    flag_missing_passengers,
    flag_zero_passengers,
    flag_invalid_distance,
    flag_invalid_duration,
    flag_speed_above_80,

    CASE
        WHEN flag_invalid_duration = FALSE
         AND flag_invalid_distance = FALSE
        THEN duration_minutes
        ELSE NULL
    END AS valid_trip_duration,

    CASE
        WHEN flag_invalid_distance = FALSE
         AND flag_invalid_duration = FALSE
         AND COALESCE(flag_speed_above_80, FALSE) = FALSE
        THEN speed_mph
        ELSE NULL
    END AS speed_for_analysis

FROM __ENRICHED_VIEW__;



-- 2. REVENUE ANALYTICS VIEW

CREATE OR REPLACE VIEW __REVENUE_VIEW__ AS

SELECT
    tpep_pickup_datetime,

    CAST(tpep_pickup_datetime AS DATE)
        AS pickup_date,

    EXTRACT(
        HOUR FROM tpep_pickup_datetime
    ) AS pickup_hour,

    PULocationID,
    pickup_borough,
    pickup_zone,

    payment_type,

    fare_amount,
    tip_amount,
    tolls_amount,
    total_amount,

    flag_non_positive_fare,
    flag_negative_or_missing_total,

    CASE
        WHEN total_amount > 0 THEN 'Positive'
        WHEN total_amount < 0 THEN 'Negative'
        WHEN total_amount = 0 THEN 'Zero'
        ELSE 'Missing'
    END AS transaction_category,

    CASE
        WHEN total_amount > 0
        THEN total_amount
        ELSE 0
    END AS positive_trip_amount,

    CASE
        WHEN total_amount < 0
        THEN total_amount
        ELSE 0
    END AS negative_adjustment_amount

FROM __ENRICHED_VIEW__;
