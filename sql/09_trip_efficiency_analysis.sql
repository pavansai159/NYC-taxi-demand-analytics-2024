
-- ================================================
-- PHASE 6 - TASK 5
-- NYC TAXI TRIP EFFICIENCY ANALYSIS
-- JANUARY 2024
-- ================================================


-- QUERY 1: OVERALL TRIP EFFICIENCY KPIs

SELECT
    COUNT(*) AS total_trips,

    COUNT(valid_trip_duration)
        AS valid_duration_trips,

    ROUND(
        AVG(
            CASE
                WHEN trip_distance > 0
                 AND valid_trip_duration IS NOT NULL
                THEN trip_distance
            END
        ), 2
    ) AS avg_distance_miles,

    ROUND(
        MEDIAN(valid_trip_duration), 2
    ) AS median_duration_minutes,

    ROUND(
        AVG(valid_trip_duration), 2
    ) AS avg_duration_minutes,

    ROUND(
        AVG(speed_for_analysis), 2
    ) AS avg_speed_mph,

    ROUND(
        MEDIAN(speed_for_analysis), 2
    ) AS median_speed_mph

FROM demand_trips_2024_01;



-- QUERY 2: EFFICIENCY BY PICKUP BOROUGH

SELECT
    pickup_borough,

    COUNT(*) AS total_trips,

    COUNT(speed_for_analysis)
        AS trips_with_valid_speed,

    ROUND(
        AVG(
            CASE
                WHEN trip_distance > 0
                 AND valid_trip_duration IS NOT NULL
                THEN trip_distance
            END
        ), 2
    ) AS avg_distance_miles,

    ROUND(
        AVG(valid_trip_duration), 2
    ) AS avg_duration_minutes,

    ROUND(
        AVG(speed_for_analysis), 2
    ) AS avg_speed_mph

FROM demand_trips_2024_01

GROUP BY pickup_borough

ORDER BY total_trips DESC;



-- QUERY 3: AVERAGE SPEED BY PICKUP HOUR

SELECT
    pickup_hour,

    COUNT(*) AS total_trips,

    COUNT(speed_for_analysis)
        AS valid_speed_trips,

    ROUND(
        AVG(speed_for_analysis), 2
    ) AS avg_speed_mph,

    ROUND(
        MEDIAN(speed_for_analysis), 2
    ) AS median_speed_mph

FROM demand_trips_2024_01

GROUP BY pickup_hour

ORDER BY pickup_hour;



-- QUERY 4: TRIP DISTANCE CATEGORIES

WITH categorized AS (

    SELECT
        CASE
            WHEN trip_distance IS NULL
              OR trip_distance <= 0
                THEN 'Invalid / Missing'

            WHEN trip_distance < 2
                THEN 'Short (<2 miles)'

            WHEN trip_distance < 5
                THEN 'Medium (2-5 miles)'

            WHEN trip_distance < 10
                THEN 'Long (5-10 miles)'

            ELSE 'Very Long (10+ miles)'
        END AS distance_category

    FROM demand_trips_2024_01
)

SELECT
    distance_category,

    COUNT(*) AS total_trips,

    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (), 2
    ) AS trip_share_pct

FROM categorized

GROUP BY distance_category

ORDER BY total_trips DESC;



-- QUERY 5: WEEKDAY VS WEEKEND SPEED

SELECT
    day_type,

    COUNT(*) AS total_trips,

    COUNT(speed_for_analysis)
        AS valid_speed_trips,

    ROUND(
        AVG(speed_for_analysis), 2
    ) AS avg_speed_mph,

    ROUND(
        MEDIAN(speed_for_analysis), 2
    ) AS median_speed_mph,

    ROUND(
        AVG(valid_trip_duration), 2
    ) AS avg_duration_minutes

FROM demand_trips_2024_01

GROUP BY day_type

ORDER BY day_type;



-- QUERY 6: TOP 10 BUSIEST ZONES WITH SPEED

SELECT
    pickup_borough,
    pickup_zone,

    COUNT(*) AS total_trips,

    ROUND(
        AVG(speed_for_analysis), 2
    ) AS avg_speed_mph,

    ROUND(
        AVG(valid_trip_duration), 2
    ) AS avg_duration_minutes

FROM demand_trips_2024_01

GROUP BY
    pickup_borough,
    pickup_zone

ORDER BY total_trips DESC

LIMIT 10;



-- QUERY 7: SPEED DISTRIBUTION PERCENTILES

SELECT
    COUNT(speed_for_analysis)
        AS valid_speed_trips,

    ROUND(
        QUANTILE_CONT(
            speed_for_analysis, 0.50
        ), 2
    ) AS speed_p50,

    ROUND(
        QUANTILE_CONT(
            speed_for_analysis, 0.90
        ), 2
    ) AS speed_p90,

    ROUND(
        QUANTILE_CONT(
            speed_for_analysis, 0.95
        ), 2
    ) AS speed_p95,

    ROUND(
        QUANTILE_CONT(
            speed_for_analysis, 0.99
        ), 2
    ) AS speed_p99

FROM demand_trips_2024_01;
