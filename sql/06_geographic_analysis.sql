
-- ===========================================
-- PHASE 6 - TASK 3
-- NYC TAXI GEOGRAPHIC DEMAND ANALYSIS
-- ===========================================


-- QUERY 1: TRIP DEMAND BY PICKUP BOROUGH

SELECT
    COALESCE(pickup_borough, 'Unknown')
        AS pickup_borough,

    COUNT(*) AS total_trips,

    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (),
        2
    ) AS demand_share_pct

FROM demand_trips_2024_01

GROUP BY pickup_borough
ORDER BY total_trips DESC;


-- QUERY 2: TOP 10 BUSIEST PICKUP ZONES

SELECT
    pickup_borough,
    pickup_zone,
    COUNT(*) AS total_trips

FROM demand_trips_2024_01

GROUP BY
    pickup_borough,
    pickup_zone

ORDER BY total_trips DESC
LIMIT 10;


-- QUERY 3: TOP 10 BUSIEST DROPOFF ZONES

SELECT
    dropoff_borough,
    dropoff_zone,
    COUNT(*) AS total_trips

FROM demand_trips_2024_01

GROUP BY
    dropoff_borough,
    dropoff_zone

ORDER BY total_trips DESC
LIMIT 10;


-- QUERY 4: TOP 10 BOROUGH-TO-BOROUGH ROUTES

SELECT
    pickup_borough,
    dropoff_borough,

    COUNT(*) AS total_trips

FROM demand_trips_2024_01

GROUP BY
    pickup_borough,
    dropoff_borough

ORDER BY total_trips DESC
LIMIT 10;


-- QUERY 5: TOP 3 PICKUP ZONES IN EACH BOROUGH

WITH zone_demand AS (

    SELECT
        pickup_borough,
        pickup_zone,
        COUNT(*) AS total_trips

    FROM demand_trips_2024_01

    GROUP BY
        pickup_borough,
        pickup_zone

),

ranked_zones AS (

    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY pickup_borough
            ORDER BY total_trips DESC, pickup_zone
        ) AS zone_rank

    FROM zone_demand

)

SELECT
    pickup_borough,
    pickup_zone,
    total_trips,
    zone_rank

FROM ranked_zones

WHERE zone_rank <= 3

ORDER BY
    pickup_borough,
    zone_rank;
