
-- ============================================
-- PHASE 6 - TASK 4
-- NYC TAXI REVENUE AND PAYMENT ANALYSIS
-- JANUARY 2024
-- ============================================


-- QUERY 1: OVERALL FINANCIAL KPIs

SELECT
    COUNT(*) AS total_trips,

    ROUND(SUM(total_amount), 2)
        AS net_recorded_trip_amount,

    ROUND(SUM(positive_trip_amount), 2)
        AS gross_positive_trip_amount,

    ROUND(SUM(negative_adjustment_amount), 2)
        AS negative_amount_total,

    ROUND(AVG(total_amount), 2)
        AS avg_recorded_trip_amount,

    ROUND(MEDIAN(total_amount), 2)
        AS median_recorded_trip_amount

FROM revenue_trips_2024_01;



-- QUERY 2: RECORDED AMOUNTS BY PICKUP BOROUGH

SELECT
    COALESCE(pickup_borough, 'Unknown')
        AS pickup_borough,

    COUNT(*) AS total_trips,

    ROUND(SUM(total_amount), 2)
        AS recorded_trip_amount,

    ROUND(AVG(total_amount), 2)
        AS avg_trip_amount,

    ROUND(
        100.0 * SUM(total_amount)
        / NULLIF(
            SUM(SUM(total_amount)) OVER (), 0
        ),
        2
    ) AS amount_share_pct

FROM revenue_trips_2024_01

GROUP BY pickup_borough

ORDER BY recorded_trip_amount DESC;



-- QUERY 3: PAYMENT TYPE DISTRIBUTION

SELECT
    payment_type,

    CASE payment_type
        WHEN 0 THEN 'Flex Fare'
        WHEN 1 THEN 'Credit Card'
        WHEN 2 THEN 'Cash'
        WHEN 3 THEN 'No Charge'
        WHEN 4 THEN 'Dispute'
        WHEN 5 THEN 'Unknown'
        WHEN 6 THEN 'Voided Trip'
        ELSE 'Other / Missing'
    END AS payment_method,

    COUNT(*) AS total_trips,

    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct,

    ROUND(SUM(total_amount), 2)
        AS recorded_trip_amount

FROM revenue_trips_2024_01

GROUP BY payment_type

ORDER BY total_trips DESC;



-- QUERY 4: TIPS BY PAYMENT TYPE

SELECT
    payment_type,

    COUNT(*) AS total_trips,

    COUNT(*) FILTER (
        WHERE tip_amount > 0
    ) AS trips_with_recorded_tips,

    ROUND(SUM(tip_amount), 2)
        AS total_recorded_tips,

    ROUND(AVG(tip_amount), 2)
        AS avg_recorded_tip,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE tip_amount > 0
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS recorded_tip_rate_pct

FROM revenue_trips_2024_01

GROUP BY payment_type

ORDER BY total_trips DESC;



-- QUERY 5: TRANSACTION CATEGORY ANALYSIS

SELECT
    transaction_category,

    COUNT(*) AS total_trips,

    ROUND(SUM(total_amount), 2)
        AS recorded_amount,

    ROUND(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER (),
        2
    ) AS trip_share_pct

FROM revenue_trips_2024_01

GROUP BY transaction_category

ORDER BY total_trips DESC;



-- QUERY 6: TOP 10 PICKUP ZONES BY AMOUNT

SELECT
    pickup_borough,
    pickup_zone,

    COUNT(*) AS total_trips,

    ROUND(SUM(total_amount), 2)
        AS recorded_trip_amount,

    ROUND(AVG(total_amount), 2)
        AS avg_trip_amount

FROM revenue_trips_2024_01

GROUP BY
    pickup_borough,
    pickup_zone

ORDER BY recorded_trip_amount DESC

LIMIT 10;



-- QUERY 7: DAILY RECORDED TRIP AMOUNTS

SELECT
    pickup_date,

    COUNT(*) AS total_trips,

    ROUND(SUM(total_amount), 2)
        AS daily_recorded_amount,

    ROUND(AVG(total_amount), 2)
        AS avg_trip_amount

FROM revenue_trips_2024_01

GROUP BY pickup_date

ORDER BY pickup_date;
