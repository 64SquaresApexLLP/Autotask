-- ==============================================================================
-- ONT TRUCK ROLL — PHASE 5: CORTEX SUMMARY PERSISTENCE TABLE
-- Database: TEST_DB
-- Schema:   ANALYTICS (existing, reused)
-- ==============================================================================
-- Applied by scripts/generate_cortex_summaries.py.
--
-- Does not touch RAW.ONT_TRUCK_ROLL, RAW.SERVICE_ADDRESS_GEOCODE,
-- RAW.WEATHER_OBSERVATIONS_OPENMETEO, RAW.LOCATION_CENTROIDS, or any existing
-- ANALYTICS view. This is the only new object in Phase 5 — no new aggregation
-- views are created; the generation script queries the existing validated
-- views (VW_TRUCK_ROLL_KPI_SUMMARY, VW_TRUCK_ROLL_BY_SOLUTION,
-- VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED, VW_TRUCK_ROLL_DATA_QUALITY_ISSUES)
-- directly.
--
-- Append-only / historical: each generation run INSERTs new rows rather than
-- replacing the table, so every past summary + the exact facts it was
-- generated from remain available for audit. Consumers wanting only the
-- current summary should filter to the latest GENERATED_AT per SUMMARY_TYPE.
-- ==============================================================================

USE DATABASE TEST_DB;
USE SCHEMA ANALYTICS;

CREATE TABLE IF NOT EXISTS ANALYTICS.CORTEX_SUMMARIES (
    SUMMARY_ID          NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    SUMMARY_TYPE         VARCHAR(64) NOT NULL,    -- OVERALL / SOLUTION_BREAKDOWN / WEATHER_DURING_INCIDENTS / DATA_QUALITY
    SUMMARY_TEXT         VARCHAR(4000),
    MODEL_USED           VARCHAR(64),             -- the model that actually produced SUMMARY_TEXT
    MODEL_ATTEMPT_LOG    VARCHAR(1000),           -- e.g. "llama3.3-70b: FAILED (...); llama3.1-70b: SUCCESS"
    SOURCE_VIEWS         VARCHAR(512),             -- comma-separated list of views the input facts came from
    INPUT_FACTS          VARIANT,                  -- exact aggregate JSON supplied to Cortex, for independent verification
    GENERATION_STATUS    VARCHAR(16) NOT NULL,     -- SUCCESS / FAILED
    GENERATION_ERROR     VARCHAR(2000),
    GENERATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
