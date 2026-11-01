#import duckdb is used to load the DuckDB Python package, which allows you to interact with DuckDB databases and perform SQL queries on various data formats, including Parquet files.
'''
DuckDB is an analytical SQL database engine 
that can directly query files such as CSV and Parquet without importing them into database tables
first.
'''
import duckdb
#duckdb.connect() establishes a connection to a DuckDB database. If no database file is specified, it creates an in-memory database that exists only for the duration of the connection.
con = duckdb.connect()

file = "data/raw/yellow_tripdata_2024-01.parquet"

# Check column names and types
print("\nDATASET SCHEMA")

#Executes SQL
''' 
Here 
1.con.execute() - Executes th SQL query provided through DuckDb.
2.DESCRIBE SELECT * - Retrive the column names and data types of the dataset.
3. .df() - Converts the result of the query into a pandas DataFrame for easier manipulation and display.
4. to_string(index=False) - Converts the DataFrame to a string representation without including the index column, making it more readable when printed.
5. print() - Displays the schema information in the console.
'''
print(con.execute(f"""
    DESCRIBE SELECT *
    FROM read_parquet('{file}')
""").df().to_string(index=False))
#read_parquet('{file}') reads the Parquet file directly.
# Count total records
print("\nTOTAL RECORDS")
print(con.execute(f"""
    SELECT COUNT(*) AS total_records
    FROM read_parquet('{file}')
""").fetchall())

# Identify the date range
print("\nPICKUP DATE RANGE")
print(con.execute(f"""
    SELECT
        MIN(tpep_pickup_datetime) AS first_pickup,
        MAX(tpep_pickup_datetime) AS last_pickup
    FROM read_parquet('{file}')
""").fetchall())

#Phase 2 - 
#checking missing values

print("\n--- MISSING VALUES ---", flush=True)

result = con.execute(f"""
    SELECT
        COUNT(*) FILTER (
            WHERE passenger_count IS NULL
        ) AS missing_passenger_count,

        COUNT(*) FILTER (
            WHERE trip_distance IS NULL
        ) AS missing_trip_distance,

        COUNT(*) FILTER (
            WHERE fare_amount IS NULL
        ) AS missing_fare_amount,

        COUNT(*) FILTER (
            WHERE PULocationID IS NULL
        ) AS missing_pickup_location,

        COUNT(*) FILTER (
            WHERE DOLocationID IS NULL
        ) AS missing_dropoff_location

    FROM read_parquet('{file}')
""").df()

print(result.T.to_string(), flush=True)

# COUNT(*) FILTER (WHERE passenger_count IS NULL) - This counts only records where passenger_count is missing

#checking invalid values 


print("\n--- INVALID VALUES ---", flush=True)

result = con.execute(f"""
    SELECT
        COUNT(*) FILTER (
            WHERE trip_distance <= 0
        ) AS non_positive_distance,

        COUNT(*) FILTER (
            WHERE fare_amount <= 0
        ) AS non_positive_fare,

        COUNT(*) FILTER (
            WHERE passenger_count = 0
        ) AS zero_passengers,

        COUNT(*) FILTER (
            WHERE total_amount < 0
        ) AS negative_total_amount,

        COUNT(*) FILTER (
            WHERE tpep_dropoff_datetime
               <= tpep_pickup_datetime
        ) AS invalid_trip_duration

    FROM read_parquet('{file}')
""").df()

print(result.T.to_string(), flush=True)


print("\n--- PICKUP DATE VALIDATION ---", flush=True)

result = con.execute(f"""
    SELECT
        COUNT(*) AS total_records,

        COUNT(*) FILTER (
            WHERE tpep_pickup_datetime >=
                  TIMESTAMP '2024-01-01'
              AND tpep_pickup_datetime <
                  TIMESTAMP '2024-02-01'
        ) AS inside_january,

        COUNT(*) FILTER (
            WHERE tpep_pickup_datetime <
                  TIMESTAMP '2024-01-01'
               OR tpep_pickup_datetime >=
                  TIMESTAMP '2024-02-01'
        ) AS outside_january,

        COUNT(*) FILTER (
            WHERE tpep_pickup_datetime IS NULL
        ) AS missing_pickup_datetime

    FROM read_parquet('{file}')
""").df()

print(result.T.to_string(), flush=True)
''' 
Data-quality issue                   Records
                                   
Missing passenger counts	         140,162
Non-positive distances	             60,371
Non-positive fares	                 38,341
Zero passengers	                     31,465
Negative total amounts	             35,504
Invalid trip durations	             870
Pickup dates outside January	     18
'''

#Stage 3

#Analyze numerical distributions


print("\n--- NUMERICAL DISTRIBUTION ---")

result = con.execute(f"""
    SELECT
        MIN(trip_distance) AS min_distance,
        MAX(trip_distance) AS max_distance,
        ROUND(AVG(trip_distance), 2) AS avg_distance,
        ROUND(MEDIAN(trip_distance), 2) AS median_distance,

        MIN(fare_amount) AS min_fare,
        MAX(fare_amount) AS max_fare,
        ROUND(AVG(fare_amount), 2) AS avg_fare,
        ROUND(MEDIAN(fare_amount), 2) AS median_fare,

        MIN(total_amount) AS min_total,
        MAX(total_amount) AS max_total

    FROM read_parquet('{file}')
""").df()

print(result.T.to_string())

#task 2 -Investigate trip durations

result_1=con.execute(f"""SELECT
    DATE_DIFF(
        'minute',
        tpep_pickup_datetime,
        tpep_dropoff_datetime
    ) AS duration_minutes
FROM read_parquet('{file}')
""").df();

print(result_1)

#Percentile analysis - p50 , p90,p95,p99


print("\n--- DISTANCE AND FARE PERCENTILES ---")

result = con.execute(f"""
    SELECT
        QUANTILE_CONT(trip_distance, 0.50) AS distance_p50,
        QUANTILE_CONT(trip_distance, 0.90) AS distance_p90,
        QUANTILE_CONT(trip_distance, 0.95) AS distance_p95,
        QUANTILE_CONT(trip_distance, 0.99) AS distance_p99,

        QUANTILE_CONT(fare_amount, 0.50) AS fare_p50,
        QUANTILE_CONT(fare_amount, 0.90) AS fare_p90,
        QUANTILE_CONT(fare_amount, 0.95) AS fare_p95,
        QUANTILE_CONT(fare_amount, 0.99) AS fare_p99

    FROM read_parquet('{file}')
""").df()

print(result.T.to_string())

'''
P50: The median, or central value.



P90: The value around which 90% of observations are at or below.



P95: Approximately 95% of observations are at or below.
P99: Approximately 99% of observations are at or below.
'''
#Inspect the 10 longest trips in the dataset

print("\n--- TOP 10 LONGEST TRIPS ---")

result = con.execute(f"""
    SELECT
        tpep_pickup_datetime,
        tpep_dropoff_datetime,
        PULocationID,
        DOLocationID,
        trip_distance,
        fare_amount,
        total_amount,

        ROUND(
            DATE_DIFF(
                'second',
                tpep_pickup_datetime,
                tpep_dropoff_datetime
            ) / 60.0, 2
        ) AS duration_minutes

    FROM read_parquet('{file}')

    ORDER BY trip_distance DESC NULLS LAST

    LIMIT 10
""").df()

print(result.to_string(index=False))



print("\n--- TRIP SPEED ANALYSIS ---")

speed_an = con.execute(f"""
    WITH trip_details AS (
        SELECT
            tpep_pickup_datetime,
            tpep_dropoff_datetime,
            trip_distance,

            DATE_DIFF(
                'second',
                tpep_pickup_datetime,
                tpep_dropoff_datetime
            ) / 3600.0 AS duration_hours

        FROM read_parquet('{file}')
    )

    SELECT
        tpep_pickup_datetime,
        tpep_dropoff_datetime,
        trip_distance,
        ROUND(duration_hours, 2) AS duration_hours,

        ROUND(
            trip_distance / NULLIF(duration_hours, 0),
            2
        ) AS speed_mph

    FROM trip_details

    WHERE duration_hours > 0
      AND trip_distance > 0

    LIMIT 10
""").df().to_string(index=False)

print(speed_an)

#Phase 4: Taxi Zone Validation and Geographic Data Understanding.


print("\n--- TAXI ZONE LOOKUP INSPECTION ---")

zones = con.execute("""
    SELECT *
    FROM read_csv_auto(
        'data/raw/taxi_zone_lookup.csv'
    )
    LIMIT 10
""").df()

print(zones.to_string(index=False))

#validate the lookup table

print("\n--- DUPLICATE LOCATION IDS ---")

result = con.execute("""
    SELECT
        LocationID,
        COUNT(*) AS occurrences

    FROM read_csv_auto(
        'data/raw/taxi_zone_lookup.csv'
    )

    GROUP BY LocationID
    HAVING COUNT(*) > 1
""").df()

print(result.to_string(index=False))


print("\n--- TOP 10 PICKUP ZONES ---")

result = con.execute(f"""
    SELECT
        z.Borough,
        z.Zone,
        COUNT(*) AS total_trips

    FROM read_parquet('{file}') AS t

    LEFT JOIN read_csv_auto(
        'data/raw/taxi_zone_lookup.csv'
    ) AS z

    ON t.PULocationID = z.LocationID

    WHERE t.tpep_pickup_datetime >=
          TIMESTAMP '2024-01-01'
      AND t.tpep_pickup_datetime <
          TIMESTAMP '2024-02-01'

    GROUP BY
        z.Borough,
        z.Zone

    ORDER BY total_trips DESC

    LIMIT 10
""").df()

print(result.to_string(index=False))


print("\n--- UNMATCHED PICKUP LOCATIONS ---")

result = con.execute(f"""
    SELECT
        t.PULocationID,
        COUNT(*) AS affected_trips

    FROM read_parquet('{file}') AS t

    LEFT JOIN read_csv_auto(
        'data/raw/taxi_zone_lookup.csv'
    ) AS z

    ON t.PULocationID = z.LocationID

    WHERE z.LocationID IS NULL

    GROUP BY t.PULocationID
    ORDER BY affected_trips DESC
""").df()

print(result.to_string(index=False))

print("\n--- TOP 5 PICKUP TO DROP-OFF ROUTES ---")

result = con.execute(f"""
    SELECT
        pu.Borough AS pickup_borough,
        pu.Zone AS pickup_zone,
        do_zone.Borough AS dropoff_borough,
        do_zone.Zone AS dropoff_zone,
        COUNT(*) AS total_trips

    FROM read_parquet('{file}') AS t

    LEFT JOIN read_csv_auto(
        'data/raw/taxi_zone_lookup.csv'
    ) AS pu
        ON t.PULocationID = pu.LocationID

    LEFT JOIN read_csv_auto(
        'data/raw/taxi_zone_lookup.csv'
    ) AS do_zone
        ON t.DOLocationID = do_zone.LocationID

    WHERE t.tpep_pickup_datetime >=
          TIMESTAMP '2024-01-01'
      AND t.tpep_pickup_datetime <
          TIMESTAMP '2024-02-01'

    GROUP BY
        pu.Borough,
        pu.Zone,
        do_zone.Borough,
        do_zone.Zone

    ORDER BY total_trips DESC
    LIMIT 5
""").df()

print(result.to_string(index=False))

''' 
Why two LEFT JOIN operations?
The first one translates PULocationID into a pickup zone. The second translates DOLocationID into a drop-off zone.
'''

