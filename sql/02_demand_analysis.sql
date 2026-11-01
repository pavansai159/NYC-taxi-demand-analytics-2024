
-- PHASE 6 - TASK 1
-- JANUARY 2024 TAXI DEMAND ANALYSIS


-- 1. OVERALL DEMAND KPIS

SELECT
    COUNT(*) AS total_trips,
    COUNT(DISTINCT pickup_date) AS active_days,

    ROUND(
        COUNT(*) * 1.0 /
        NULLIF(COUNT(DISTINCT pickup_date), 0),
        2
    ) AS avg_trips_per_day

FROM demand_trips_2024_01;


-- 2. DAILY TRIP DEMAND

SELECT
    pickup_date,
    COUNT(*) AS total_trips

FROM demand_trips_2024_01

GROUP BY pickup_date
ORDER BY pickup_date;


-- 3. HOURLY TRIP DEMAND

SELECT
    pickup_hour,
    COUNT(*) AS total_trips

FROM demand_trips_2024_01

GROUP BY pickup_hour
ORDER BY pickup_hour;


-- 4. WEEKDAY VS WEEKEND DEMAND

SELECT
    day_type,
    COUNT(*) AS total_trips,
    ROUND(
        COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct

FROM demand_trips_2024_01

GROUP BY day_type
ORDER BY total_trips DESC;
