
-- PHASE 5: TASK 4
-- GEOGRAPHIC ENRICHMENT

CREATE OR REPLACE VIEW {enriched_view} AS

SELECT
    t.*,

    pu.Borough AS pickup_borough,
    pu.Zone AS pickup_zone,

    dz.Borough AS dropoff_borough,
    dz.Zone AS dropoff_zone,

    (pu.LocationID IS NULL)
        AS flag_unknown_pickup_zone,

    (dz.LocationID IS NULL)
        AS flag_unknown_dropoff_zone

FROM {quality_view} AS t

LEFT JOIN taxi_zones AS pu
    ON t.PULocationID = pu.LocationID

LEFT JOIN taxi_zones AS dz
    ON t.DOLocationID = dz.LocationID;
