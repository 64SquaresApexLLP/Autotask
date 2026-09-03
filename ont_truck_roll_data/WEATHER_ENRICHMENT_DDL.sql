-- ==============================================================================
-- ONT TRUCK ROLL — PHASE 3: WEATHER ENRICHMENT LAYER
-- Database: TEST_DB
-- Schemas:  RAW (existing, reused), ANALYTICS (existing, reused)
-- Source:   RAW.ONT_TRUCK_ROLL (read-only — never modified by anything here)
--           ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED (read-only — never modified)
-- ==============================================================================
-- Applied by scripts/create_weather_enrichment.py.
--
-- Provider: Open-Meteo Historical Weather API (ERA5/ERA5-Land archive),
-- approved by manager. No API key required for this volume.
-- Geocoder: US Census Bureau batch geocoder (free, no API key).
--
-- Project decisions (see ont_truck_roll_data/README.md Phase 3 section):
--   - ENTERED_DATE is the incident timestamp (SOLUTION_DATE is completion time).
--   - ENTERED_DATE is interpreted as UTC (source is TIMESTAMP_NTZ, no tz stored;
--     RAW values are NOT modified — interpretation happens only in this layer).
--   - SERVICE_ADDRESS (+ SERVICE_CITY) is the geocoding key.
-- ==============================================================================

USE DATABASE TEST_DB;
USE SCHEMA RAW;

-- ------------------------------------------------------------------------------
-- 1. RAW.SERVICE_ADDRESS_GEOCODE
--    One row per distinct (SERVICE_ADDRESS, SERVICE_CITY) pair from
--    RAW.ONT_TRUCK_ROLL (~2,038 rows). Full-refresh table: the geocoding script
--    does CREATE OR REPLACE and repopulates it entirely on each run (cheap —
--    one batch API call), so this DDL only ensures the table exists with the
--    right shape if it's ever missing.
--
--    LATITUDE/LONGITUDE are fixed-precision NUMBER (not FLOAT) specifically so
--    that equality joins against RAW.WEATHER_OBSERVATIONS_OPENMETEO are exact,
--    not subject to floating-point comparison drift.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS RAW.SERVICE_ADDRESS_GEOCODE (
    SERVICE_ADDRESS     VARCHAR(512) NOT NULL,
    SERVICE_CITY        VARCHAR(128) NOT NULL,
    STATE_ASSUMED       VARCHAR(2),               -- 'TX' — assumed; source has no state column
    LATITUDE            NUMBER(9,4),
    LONGITUDE           NUMBER(9,4),
    MATCHED_ADDRESS     VARCHAR(512),             -- as returned by the geocoder, for audit
    GEOCODING_STATUS    VARCHAR(32) NOT NULL,     -- SUCCESS / FAILED / AMBIGUOUS
    GEOCODING_SOURCE    VARCHAR(64) NOT NULL,     -- 'US Census Bureau Geocoder'
    GEOCODED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ------------------------------------------------------------------------------
-- 2. RAW.WEATHER_OBSERVATIONS_OPENMETEO
--    One row per (LATITUDE, LONGITUDE, WEATHER_TIMESTAMP_UTC) hourly weather
--    observation, fetched ONLY for the location+day combinations actually
--    needed by a truck roll's ENTERED_DATE (not a blind multi-year backfill —
--    see scripts/fetch_open_meteo_weather.py). This table is INCREMENTAL /
--    append-and-cache: it is never truncated or replaced by the fetch script,
--    so reruns skip already-cached (location, day) groups and simply add
--    whatever is still missing. Acts as a permanent cache — the dashboard
--    layer queries this table, never Open-Meteo directly.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS RAW.WEATHER_OBSERVATIONS_OPENMETEO (
    LATITUDE                NUMBER(9,4) NOT NULL,
    LONGITUDE               NUMBER(9,4) NOT NULL,
    WEATHER_TIMESTAMP_UTC    TIMESTAMP_NTZ NOT NULL,
    TEMPERATURE_C            FLOAT,               -- direct provider field: temperature_2m
    PRECIPITATION_MM         FLOAT,               -- direct provider field: precipitation
    RAIN_MM                  FLOAT,               -- direct provider field: rain
    SNOWFALL_CM              FLOAT,               -- direct provider field: snowfall
    WIND_SPEED_KMH           FLOAT,               -- direct provider field: wind_speed_10m
    WIND_GUST_KMH            FLOAT,               -- direct provider field: wind_gusts_10m
    RELATIVE_HUMIDITY_PCT    FLOAT,               -- direct provider field: relative_humidity_2m
    WEATHER_CODE             NUMBER,              -- direct provider field: weather_code (WMO code)
    WEATHER_SOURCE           VARCHAR(64) DEFAULT 'Open-Meteo ERA5 Archive',
    LOADED_AT                TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
-- Natural key (LATITUDE, LONGITUDE, WEATHER_TIMESTAMP_UTC) is enforced at the
-- application layer (fetch script checks before inserting) — not a DB constraint.

-- ------------------------------------------------------------------------------
-- 3. ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
--    LEFT JOINs throughout, by design, so the output row count always equals
--    ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED's row count (3,040) — a truck roll
--    with no geocode or no weather match still appears exactly once, flagged
--    via WEATHER_MATCH_STATUS, never dropped and never duplicated.
--
--    Matching rule (documented, deterministic):
--      WEATHER_HOUR_UTC = nearest hour to ENTERED_DATE, round-half-up:
--        MINUTE(ENTERED_DATE) < 30  -> DATE_TRUNC('HOUR', ENTERED_DATE)
--        MINUTE(ENTERED_DATE) >= 30 -> DATE_TRUNC('HOUR', ENTERED_DATE) + 1 hour
--      Joined on exact (LATITUDE, LONGITUDE, WEATHER_TIMESTAMP_UTC) equality.
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
geocoded AS (
    SELECT
        b.*,
        g.LATITUDE,
        g.LONGITUDE,
        g.GEOCODING_STATUS
    FROM base b
    LEFT JOIN RAW.SERVICE_ADDRESS_GEOCODE g
        ON b.SERVICE_ADDRESS = g.SERVICE_ADDRESS
       AND b.SERVICE_CITY = g.SERVICE_CITY
)
SELECT
    g.ONT_TRUCK_ROLL_ID,
    g.ACCOUNT,
    g.ACCOUNT_NUMBER,
    g.ENTERED_DATE,
    g.SOLUTION_DATE,
    g.SOLUTION_ENTRY_USER,
    g.ORDER_NUMBER,
    g.PROBLEM,
    g.SOLUTION,
    g.SERVICE_ADDRESS,
    g.SERVICE_CITY,
    g.SERVICE_REVENUE_AREA,
    g.ORDER_STATUS,
    g.RESOLUTION_MINUTES,
    g.RESOLUTION_HOURS,
    g.IS_DUPLICATE_ORDER_NUMBER,
    g.IS_DATE_ANOMALY,
    g.INCIDENT_TIMESTAMP_UTC,
    g.LATITUDE,
    g.LONGITUDE,
    g.WEATHER_HOUR_UTC,
    w.WEATHER_TIMESTAMP_UTC,
    w.TEMPERATURE_C,
    w.PRECIPITATION_MM,
    w.RAIN_MM,
    w.SNOWFALL_CM,
    w.WIND_SPEED_KMH,
    w.WIND_GUST_KMH,
    w.RELATIVE_HUMIDITY_PCT,
    w.WEATHER_CODE,
    -- DERIVED FIELD: plain-language condition from the WMO weather_code
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
    -- DERIVED FIELD: severe-weather flag from WMO thunderstorm codes
    IFF(w.WEATHER_CODE IN (95,96,97,98,99), TRUE, FALSE) AS IS_SEVERE_WEATHER,
    -- Match status: distinguishes why a row may have no weather data
    CASE
        WHEN g.GEOCODING_STATUS IS NULL THEN 'NO_GEOCODE'
        WHEN g.GEOCODING_STATUS != 'SUCCESS' THEN 'GEOCODE_FAILED'
        WHEN w.WEATHER_TIMESTAMP_UTC IS NULL THEN 'NO_WEATHER_DATA'
        ELSE 'MATCHED'
    END AS WEATHER_MATCH_STATUS
FROM geocoded g
LEFT JOIN RAW.WEATHER_OBSERVATIONS_OPENMETEO w
    ON w.LATITUDE = g.LATITUDE
   AND w.LONGITUDE = g.LONGITUDE
   AND w.WEATHER_TIMESTAMP_UTC = g.WEATHER_HOUR_UTC;
