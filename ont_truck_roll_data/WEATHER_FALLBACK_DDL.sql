-- ==============================================================================
-- ONT TRUCK ROLL — PHASE 4: CONTROLLED GEOCODING FALLBACK
-- Database: TEST_DB
-- Schemas:  RAW (existing, reused), ANALYTICS (existing, reused)
-- ==============================================================================
-- Applied by scripts/create_weather_fallback.py.
--
-- Does NOT modify RAW.ONT_TRUCK_ROLL or RAW.SERVICE_ADDRESS_GEOCODE — the exact
-- geocoding results from Phase 3 remain exactly as they were, untouched, and
-- are exposed unchanged via ORIGINAL_GEOCODING_STATUS in the enriched view for
-- full auditability.
--
-- Fallback priority (documented, deterministic):
--   1. EXACT            RAW.SERVICE_ADDRESS_GEOCODE.GEOCODING_STATUS = 'SUCCESS'
--   2. AREA_CENTROID     AVG(lat/long) of all SUCCESS-geocoded addresses sharing
--                        the same SERVICE_REVENUE_AREA, only if >= 2 such
--                        addresses exist (RELIABLE threshold — documented, not
--                        a single arbitrary point)
--   3. CITY_CENTROID     same, grouped by SERVICE_CITY instead
--   4. FAILED            neither exact nor a reliable centroid exists
--
-- No coordinates are invented: every centroid is a plain average of real,
-- already-geocoded exact points from this same dataset. No external
-- geocoding/estimation service is used for the fallback tiers.
-- ==============================================================================

USE DATABASE TEST_DB;
USE SCHEMA RAW;

-- ------------------------------------------------------------------------------
-- 1. RAW.LOCATION_CENTROIDS
--    Full-refresh table (CREATE OR REPLACE ... AS SELECT): cheap, pure SQL
--    aggregation over RAW.ONT_TRUCK_ROLL + RAW.SERVICE_ADDRESS_GEOCODE, no
--    external calls. Safe to rerun any time (e.g. after a fresh geocode run).
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW.LOCATION_CENTROIDS AS
SELECT
    'AREA' AS CENTROID_LEVEL,
    t.SERVICE_REVENUE_AREA AS CENTROID_KEY,
    ROUND(AVG(g.LATITUDE), 4) AS LATITUDE,
    ROUND(AVG(g.LONGITUDE), 4) AS LONGITUDE,
    COUNT(*) AS SAMPLE_SIZE,
    (COUNT(*) >= 2) AS IS_RELIABLE,
    CURRENT_TIMESTAMP() AS COMPUTED_AT
FROM RAW.ONT_TRUCK_ROLL t
JOIN RAW.SERVICE_ADDRESS_GEOCODE g
  ON t.SERVICE_ADDRESS = g.SERVICE_ADDRESS AND t.SERVICE_CITY = g.SERVICE_CITY
WHERE g.GEOCODING_STATUS = 'SUCCESS'
GROUP BY t.SERVICE_REVENUE_AREA

UNION ALL

SELECT
    'CITY' AS CENTROID_LEVEL,
    t.SERVICE_CITY AS CENTROID_KEY,
    ROUND(AVG(g.LATITUDE), 4) AS LATITUDE,
    ROUND(AVG(g.LONGITUDE), 4) AS LONGITUDE,
    COUNT(*) AS SAMPLE_SIZE,
    (COUNT(*) >= 2) AS IS_RELIABLE,
    CURRENT_TIMESTAMP() AS COMPUTED_AT
FROM RAW.ONT_TRUCK_ROLL t
JOIN RAW.SERVICE_ADDRESS_GEOCODE g
  ON t.SERVICE_ADDRESS = g.SERVICE_ADDRESS AND t.SERVICE_CITY = g.SERVICE_CITY
WHERE g.GEOCODING_STATUS = 'SUCCESS'
GROUP BY t.SERVICE_CITY;

-- ------------------------------------------------------------------------------
-- 2. ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED (rebuilt, same name)
--    Adds the 4-tier fallback. LOCATION_MATCH_TYPE and ORIGINAL_GEOCODING_STATUS
--    together give full transparency: which tier actually supplied the
--    coordinates used for weather, and what the original exact-geocode result
--    was (even when a fallback tier was used instead).
-- ------------------------------------------------------------------------------
USE SCHEMA ANALYTICS;

CREATE OR REPLACE VIEW ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED AS
WITH base AS (
    SELECT
        e.*,
        e.ENTERED_DATE AS INCIDENT_TIMESTAMP_UTC,
        IFF(
            MINUTE(e.ENTERED_DATE) < 30,
            DATE_TRUNC('HOUR', e.ENTERED_DATE),
            DATEADD('HOUR', 1, DATE_TRUNC('HOUR', e.ENTERED_DATE))
        ) AS WEATHER_HOUR_UTC
    FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED e
),
resolved AS (
    SELECT
        b.*,
        g.GEOCODING_STATUS AS ORIGINAL_GEOCODING_STATUS,
        g.LATITUDE AS EXACT_LATITUDE,
        g.LONGITUDE AS EXACT_LONGITUDE,
        area_c.LATITUDE AS AREA_LATITUDE,
        area_c.LONGITUDE AS AREA_LONGITUDE,
        area_c.IS_RELIABLE AS AREA_RELIABLE,
        city_c.LATITUDE AS CITY_LATITUDE,
        city_c.LONGITUDE AS CITY_LONGITUDE,
        city_c.IS_RELIABLE AS CITY_RELIABLE,
        CASE
            WHEN g.GEOCODING_STATUS = 'SUCCESS' THEN 'EXACT'
            WHEN area_c.IS_RELIABLE THEN 'AREA_CENTROID'
            WHEN city_c.IS_RELIABLE THEN 'CITY_CENTROID'
            ELSE 'FAILED'
        END AS LOCATION_MATCH_TYPE
    FROM base b
    LEFT JOIN RAW.SERVICE_ADDRESS_GEOCODE g
        ON b.SERVICE_ADDRESS = g.SERVICE_ADDRESS AND b.SERVICE_CITY = g.SERVICE_CITY
    LEFT JOIN RAW.LOCATION_CENTROIDS area_c
        ON area_c.CENTROID_LEVEL = 'AREA' AND area_c.CENTROID_KEY = b.SERVICE_REVENUE_AREA
    LEFT JOIN RAW.LOCATION_CENTROIDS city_c
        ON city_c.CENTROID_LEVEL = 'CITY' AND city_c.CENTROID_KEY = b.SERVICE_CITY
),
final_location AS (
    SELECT
        r.*,
        CASE r.LOCATION_MATCH_TYPE
            WHEN 'EXACT' THEN r.EXACT_LATITUDE
            WHEN 'AREA_CENTROID' THEN r.AREA_LATITUDE
            WHEN 'CITY_CENTROID' THEN r.CITY_LATITUDE
            ELSE NULL
        END AS LATITUDE,
        CASE r.LOCATION_MATCH_TYPE
            WHEN 'EXACT' THEN r.EXACT_LONGITUDE
            WHEN 'AREA_CENTROID' THEN r.AREA_LONGITUDE
            WHEN 'CITY_CENTROID' THEN r.CITY_LONGITUDE
            ELSE NULL
        END AS LONGITUDE
    FROM resolved r
)
SELECT
    f.ONT_TRUCK_ROLL_ID,
    f.ACCOUNT,
    f.ACCOUNT_NUMBER,
    f.ENTERED_DATE,
    f.SOLUTION_DATE,
    f.SOLUTION_ENTRY_USER,
    f.ORDER_NUMBER,
    f.PROBLEM,
    f.SOLUTION,
    f.SERVICE_ADDRESS,
    f.SERVICE_CITY,
    f.SERVICE_REVENUE_AREA,
    f.ORDER_STATUS,
    f.RESOLUTION_MINUTES,
    f.RESOLUTION_HOURS,
    f.IS_DUPLICATE_ORDER_NUMBER,
    f.IS_DATE_ANOMALY,
    f.INCIDENT_TIMESTAMP_UTC,
    f.ORIGINAL_GEOCODING_STATUS,
    f.LOCATION_MATCH_TYPE,
    f.LATITUDE,
    f.LONGITUDE,
    f.WEATHER_HOUR_UTC,
    w.WEATHER_TIMESTAMP_UTC,
    w.TEMPERATURE_C,
    w.PRECIPITATION_MM,
    w.RAIN_MM,
    w.SNOWFALL_CM,
    w.WIND_SPEED_KMH,
    w.WIND_GUST_KMH,
    w.RELATIVE_HUMIDITY_PCT,
    w.WEATHER_CODE,
    CASE
        WHEN w.WEATHER_CODE IS NULL THEN NULL
        WHEN w.WEATHER_CODE = 0 THEN 'Clear sky'
        WHEN w.WEATHER_CODE IN (1,2,3) THEN 'Partly cloudy'
        WHEN w.WEATHER_CODE IN (45,48) THEN 'Fog'
        WHEN w.WEATHER_CODE IN (51,53,55,56,57) THEN 'Drizzle'
        WHEN w.WEATHER_CODE IN (61,63,65,66,67) THEN 'Rain'
        WHEN w.WEATHER_CODE IN (71,73,75,77) THEN 'Snow'
        WHEN w.WEATHER_CODE IN (80,81,82) THEN 'Rain showers'
        WHEN w.WEATHER_CODE IN (85,86) THEN 'Snow showers'
        WHEN w.WEATHER_CODE IN (95,96,97,98,99) THEN 'Thunderstorm'
        ELSE 'Other (code ' || w.WEATHER_CODE || ')'
    END AS WEATHER_CONDITION,
    IFF(w.WEATHER_CODE IN (95,96,97,98,99), TRUE, FALSE) AS IS_SEVERE_WEATHER,
    CASE
        WHEN f.LOCATION_MATCH_TYPE = 'FAILED' THEN 'GEOCODE_FAILED'
        WHEN w.WEATHER_TIMESTAMP_UTC IS NULL THEN 'NO_WEATHER_DATA'
        WHEN f.LOCATION_MATCH_TYPE = 'EXACT' THEN 'MATCHED'
        WHEN f.LOCATION_MATCH_TYPE = 'AREA_CENTROID' THEN 'AREA_CENTROID_APPROXIMATE'
        WHEN f.LOCATION_MATCH_TYPE = 'CITY_CENTROID' THEN 'CITY_CENTROID_APPROXIMATE'
    END AS WEATHER_MATCH_STATUS
FROM final_location f
LEFT JOIN RAW.WEATHER_OBSERVATIONS_OPENMETEO w
    ON w.LATITUDE = f.LATITUDE
   AND w.LONGITUDE = f.LONGITUDE
   AND w.WEATHER_TIMESTAMP_UTC = f.WEATHER_HOUR_UTC;
