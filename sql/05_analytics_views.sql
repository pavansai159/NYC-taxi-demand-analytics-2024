
-- ========================================
-- PHASE 5 - TASK 5
-- NYC TAXI DEMAND AND REVENUE ANALYTICS
-- ========================================


-- ========================================
-- VIEW 1: DEMAND ANALYTICS
-- ========================================

CREATE OR REPLACE VIEW {demand_view} AS

SELECT

    -- Original timestamps
    tpep_pickup_datetime,
    tpep_dropoff_datetime,

    -- Date information
    CAST(tpep_pickup_datetime AS DATE)
        AS pickup_date,

    -- Pickup hour (0 to 23)
    EXTRACT(
        HOUR FROM tpep_pickup_datetime
    ) AS pickup_hour,

    -- Day of the week
    STRFTIME(
        tpep_pickup_datetime,
        '%A'
    ) AS pickup_day_name,

    -- Pickup location
    PULocationID,
    pickup_borough,
    pickup_zone,

    -- Dropoff location
    DOLocationID,
    dropoff_borough,
    dropoff_zone,

    -- Trip details
    passenger_count,
    trip_distance,
    duration_minutes,
    speed_mph,

    -- Quality flags
    flag_missing_passengers,
    flag_zero_passengers,
    flag_invalid_distance,
    flag_invalid_duration,
    flag_unknown_pickup_zone,
    flag_unknown_dropoff_zone,

    -- Preliminary demand eligibility
    (
        COALESCE(
            NOT flag_invalid_distance,
            FALSE
        )
        AND
        COALESCE(
            NOT flag_invalid_duration,
            FALSE
        )
    ) AS eligible_trip_activity

FROM {enriched_view};



-- ========================================
-- VIEW 2: REVENUE ANALYTICS
-- ========================================

CREATE OR REPLACE VIEW {revenue_view} AS

SELECT

    -- Timestamps
    tpep_pickup_datetime,

    CAST(tpep_pickup_datetime AS DATE)
        AS pickup_date,

    -- Pickup location
    PULocationID,
    pickup_borough,
    pickup_zone,

    -- Dropoff location
    DOLocationID,
    dropoff_borough,
    dropoff_zone,

    -- Payment details
    payment_type,

    -- Financial information
    fare_amount,
    tip_amount,
    tolls_amount,
    total_amount,

    -- Quality flags
    flag_non_positive_fare,
    flag_negative_or_missing_total,

    -- Transaction classification
    CASE

        WHEN total_amount > 0
            THEN 'Positive'

        WHEN total_amount < 0
            THEN 'Negative'

        WHEN total_amount = 0
            THEN 'Zero'

        ELSE 'Missing'

    END AS transaction_category

FROM {enriched_view};
