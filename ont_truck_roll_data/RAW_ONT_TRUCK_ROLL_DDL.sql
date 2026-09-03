-- ==============================================================================
-- ONT TRUCK ROLL — PHASE 1 RAW LANDING TABLE DDL
-- Database: TEST_DB
-- Schema:   RAW   (new schema — no RAW schema/prefix convention existed in this
--                   repo before Phase 1; every other table lives in TEST_DB.PUBLIC.
--                   Introduced here per the client requirement to land this data
--                   in a RAW layer ahead of later transformation phases.)
-- Table:    RAW.ONT_TRUCK_ROLL
-- Stage:    RAW.ONT_TRUCK_ROLL_STAGE (internal named stage)
-- ==============================================================================
-- This file is applied automatically by scripts/ingest_ont_truck_roll.py.
-- It is also kept here, standalone, so it can be reviewed/run manually in a
-- Snowflake worksheet if needed.
-- ==============================================================================

USE DATABASE TEST_DB;
CREATE SCHEMA IF NOT EXISTS RAW;
USE SCHEMA RAW;

-- 1. File format for the exported CSV (data/ont_truck_roll/ont_truck_roll.csv).
--    Mirrors the CSV_ONTOLOGY_FORMAT convention already used in
--    snowflake_ontology_data/SNOWFLAKE_SCHEMA_DDL.sql.
CREATE OR REPLACE FILE FORMAT RAW.CSV_ONT_TRUCK_ROLL_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('NULL', 'null', '')
    EMPTY_FIELD_AS_NULL = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

-- 2. Internal named stage to PUT the CSV to before COPY INTO.
CREATE STAGE IF NOT EXISTS RAW.ONT_TRUCK_ROLL_STAGE
    FILE_FORMAT = RAW.CSV_ONT_TRUCK_ROLL_FORMAT;

-- 3. RAW table — one column per source CSV column (same order, same meaning),
--    plus a small set of ingestion-lineage columns (row id, source file name,
--    load timestamp). No business/derived columns are added in Phase 1.
--
--    ENTERED_DATE / SOLUTION_DATE are parsed to TIMESTAMP_NTZ (source values are
--    like "1/2/2023 4:53 PM" — M/D/YYYY H:MI AM/PM). Every other source column
--    is kept as VARCHAR, matching "keep RAW as close to the source as possible".
CREATE OR REPLACE TABLE RAW.ONT_TRUCK_ROLL (
    ONT_TRUCK_ROLL_ID     NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    ACCOUNT               VARCHAR(256),
    ACCOUNT_NUMBER        VARCHAR(64),
    ENTERED_DATE          TIMESTAMP_NTZ,
    SOLUTION_DATE         TIMESTAMP_NTZ,
    SOLUTION_ENTRY_USER   VARCHAR(128),
    ORDER_NUMBER          VARCHAR(64),
    PROBLEM               VARCHAR(512),
    SOLUTION              VARCHAR(256),
    SERVICE_ADDRESS       VARCHAR(512),
    SERVICE_CITY          VARCHAR(128),
    SERVICE_REVENUE_AREA  VARCHAR(128),
    ORDER_STATUS          VARCHAR(64),
    SOURCE_FILE_NAME      VARCHAR(256),
    LOADED_AT             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- No PRIMARY KEY on ORDER_NUMBER: the source data contains one legitimate
-- duplicate ORDER_NUMBER (586374, two different Account Numbers, same
-- Entered/Solution Date — a real source anomaly, not an ingestion bug). See
-- ont_truck_roll_data/README.md for details. RAW loads every source row as-is.

-- ==============================================================================
-- INGESTION COMMANDS (run by scripts/ingest_ont_truck_roll.py; kept here for
-- reference / manual reload)
-- ==============================================================================
-- PUT file://<repo>/data/ont_truck_roll/ont_truck_roll.csv @RAW.ONT_TRUCK_ROLL_STAGE
--     AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
--
-- TRUNCATE TABLE RAW.ONT_TRUCK_ROLL;
--
-- COPY INTO RAW.ONT_TRUCK_ROLL
--     (ACCOUNT, ACCOUNT_NUMBER, ENTERED_DATE, SOLUTION_DATE, SOLUTION_ENTRY_USER,
--      ORDER_NUMBER, PROBLEM, SOLUTION, SERVICE_ADDRESS, SERVICE_CITY,
--      SERVICE_REVENUE_AREA, ORDER_STATUS, SOURCE_FILE_NAME)
-- FROM (
--     SELECT
--         $1, $2,
--         TO_TIMESTAMP_NTZ($3, 'MM/DD/YYYY HH12:MI AM'),
--         TO_TIMESTAMP_NTZ($4, 'MM/DD/YYYY HH12:MI AM'),
--         $5, $6, $7, $8, $9, $10, $11, $12,
--         'ont_truck_roll.csv'
--     FROM @RAW.ONT_TRUCK_ROLL_STAGE
-- )
-- FILE_FORMAT = (FORMAT_NAME = RAW.CSV_ONT_TRUCK_ROLL_FORMAT)
-- ON_ERROR = 'ABORT_STATEMENT';
