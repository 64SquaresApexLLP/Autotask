-- ==============================================================================
-- ONT TRUCK ROLL — PHASE 2 ANALYTICS LAYER (views only, read-only over RAW)
-- Database: TEST_DB
-- Schema:   ANALYTICS (new — same pattern as the RAW schema introduced in Phase 1)
-- Source:   TEST_DB.RAW.ONT_TRUCK_ROLL  (never modified — no INSERT/UPDATE/DDL
--           against RAW happens here, and none of these objects write back to it)
-- ==============================================================================
-- Applied by scripts/create_ont_truck_roll_analytics.py. Kept here standalone
-- too, for manual review/run in a Snowflake worksheet.
--
-- All objects here are VIEWs, not tables: RAW.ONT_TRUCK_ROLL is truncated and
-- reloaded on every ingestion run (see RAW_ONT_TRUCK_ROLL_DDL.sql), so a view
-- always reflects the latest load with no separate refresh step to remember.
--
-- Scope: KPI/reporting metrics only, for a future Admin dashboard to query.
-- No weather data, no Cortex summaries, no dashboard UI are built here.
-- ==============================================================================

USE DATABASE TEST_DB;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;
USE SCHEMA ANALYTICS;

-- ------------------------------------------------------------------------------
-- 1. VW_ONT_TRUCK_ROLL_ENRICHED
--    One row per RAW row, passthrough plus derived fields every other view
--    builds on: resolution duration, calendar buckets, and two data-quality
--    flags (duplicate ORDER_NUMBER, inverted Solution/Entered dates) so the
--    dashboard can surface or exclude them without re-deriving this logic.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED AS
SELECT
    ONT_TRUCK_ROLL_ID,
    ACCOUNT,
    ACCOUNT_NUMBER,
    ENTERED_DATE,
    SOLUTION_DATE,
    SOLUTION_ENTRY_USER,
    ORDER_NUMBER,
    PROBLEM,
    SOLUTION,
    SERVICE_ADDRESS,
    SERVICE_CITY,
    SERVICE_REVENUE_AREA,
    ORDER_STATUS,
    DATEDIFF('minute', ENTERED_DATE, SOLUTION_DATE)                AS RESOLUTION_MINUTES,
    DATEDIFF('minute', ENTERED_DATE, SOLUTION_DATE) / 60.0         AS RESOLUTION_HOURS,
    DATE_TRUNC('MONTH', ENTERED_DATE)::DATE                        AS ENTERED_YEAR_MONTH,
    YEAR(ENTERED_DATE)                                              AS ENTERED_YEAR,
    MONTH(ENTERED_DATE)                                             AS ENTERED_MONTH,
    (COUNT(*) OVER (PARTITION BY ORDER_NUMBER) > 1)                 AS IS_DUPLICATE_ORDER_NUMBER,
    (SOLUTION_DATE < ENTERED_DATE)                                  AS IS_DATE_ANOMALY
FROM RAW.ONT_TRUCK_ROLL;

-- ------------------------------------------------------------------------------
-- 2. VW_TRUCK_ROLL_KPI_SUMMARY
--    Single-row headline KPI card for the dashboard: totals, resolution-time
--    stats, and data-quality counts (so a "3,040 total, 2 flagged" style
--    caption can be shown without a separate query).
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY AS
SELECT
    COUNT(*)                                                        AS TOTAL_TRUCK_ROLLS,
    COUNT(DISTINCT SERVICE_ADDRESS)                                 AS UNIQUE_SERVICE_ADDRESSES,
    COUNT(DISTINCT ORDER_NUMBER)                                    AS UNIQUE_ORDER_NUMBERS,
    COUNT(DISTINCT ACCOUNT_NUMBER)                                  AS UNIQUE_ACCOUNTS,
    MIN(ENTERED_DATE)                                               AS EARLIEST_ENTERED_DATE,
    MAX(ENTERED_DATE)                                               AS LATEST_ENTERED_DATE,
    SUM(IFF(SOLUTION = 'Replaced Ont', 1, 0))                       AS ONT_REPLACED_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Wall Wart', 1, 0))                 AS WALL_WART_REPLACED_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Controller', 1, 0))                AS CONTROLLER_REPLACED_COUNT,
    ROUND(AVG(RESOLUTION_HOURS), 2)                                 AS AVG_RESOLUTION_HOURS,
    ROUND(MEDIAN(RESOLUTION_HOURS), 2)                              AS MEDIAN_RESOLUTION_HOURS,
    SUM(IFF(IS_DUPLICATE_ORDER_NUMBER, 1, 0))                       AS DUPLICATE_ORDER_NUMBER_ROW_COUNT,
    SUM(IFF(IS_DATE_ANOMALY, 1, 0))                                 AS DATE_ANOMALY_ROW_COUNT
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED;

-- ------------------------------------------------------------------------------
-- 3. VW_TRUCK_ROLL_BY_SOLUTION
--    Breakdown + average resolution time by Solution type (ONT / Wall Wart /
--    Controller) — feeds a pie/bar chart.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_BY_SOLUTION AS
SELECT
    SOLUTION,
    COUNT(*)                                                        AS TRUCK_ROLL_COUNT,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)              AS PCT_OF_TOTAL,
    ROUND(AVG(RESOLUTION_HOURS), 2)                                 AS AVG_RESOLUTION_HOURS
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED
GROUP BY SOLUTION
ORDER BY TRUCK_ROLL_COUNT DESC;

-- ------------------------------------------------------------------------------
-- 4. VW_TRUCK_ROLL_MONTHLY_TREND
--    Truck rolls per calendar month, split by Solution type — feeds a
--    time-series chart (Jan 2023 through the latest month in the data).
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_MONTHLY_TREND AS
SELECT
    ENTERED_YEAR_MONTH,
    ENTERED_YEAR,
    ENTERED_MONTH,
    COUNT(*)                                                        AS TRUCK_ROLL_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Ont', 1, 0))                       AS ONT_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Wall Wart', 1, 0))                 AS WALL_WART_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Controller', 1, 0))                AS CONTROLLER_COUNT,
    ROUND(AVG(RESOLUTION_HOURS), 2)                                 AS AVG_RESOLUTION_HOURS
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED
GROUP BY ENTERED_YEAR_MONTH, ENTERED_YEAR, ENTERED_MONTH
ORDER BY ENTERED_YEAR_MONTH;

-- ------------------------------------------------------------------------------
-- 5. VW_TRUCK_ROLL_BY_SERVICE_AREA
--    Truck roll volume + average resolution time by Service Revenue Area —
--    feeds a "hot spots" table/map on the dashboard.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_BY_SERVICE_AREA AS
SELECT
    SERVICE_REVENUE_AREA,
    SERVICE_CITY,
    COUNT(*)                                                        AS TRUCK_ROLL_COUNT,
    ROUND(AVG(RESOLUTION_HOURS), 2)                                 AS AVG_RESOLUTION_HOURS
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED
GROUP BY SERVICE_REVENUE_AREA, SERVICE_CITY
ORDER BY TRUCK_ROLL_COUNT DESC;

-- ------------------------------------------------------------------------------
-- 6. VW_TRUCK_ROLL_BY_TECHNICIAN
--    Workload + average resolution time by the technician who logged the
--    solution — feeds a technician workload panel.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_BY_TECHNICIAN AS
SELECT
    SOLUTION_ENTRY_USER,
    COUNT(*)                                                        AS TRUCK_ROLL_COUNT,
    ROUND(AVG(RESOLUTION_HOURS), 2)                                 AS AVG_RESOLUTION_HOURS
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED
GROUP BY SOLUTION_ENTRY_USER
ORDER BY TRUCK_ROLL_COUNT DESC;

-- ------------------------------------------------------------------------------
-- 7. VW_TRUCK_ROLL_BY_ADDRESS
--    Repeat-truck-roll analysis per Service Address — the client's Word
--    analysis calls out 221 addresses with 3+ truck rolls covering 772 total
--    truck rolls; this view is what a dashboard "repeat visits" panel queries
--    (e.g. WHERE TRUCK_ROLL_COUNT >= 3) instead of re-deriving that grouping.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_BY_ADDRESS AS
SELECT
    SERVICE_ADDRESS,
    SERVICE_CITY,
    SERVICE_REVENUE_AREA,
    COUNT(*)                                                        AS TRUCK_ROLL_COUNT,
    MIN(ENTERED_DATE)                                               AS FIRST_TRUCK_ROLL_DATE,
    MAX(ENTERED_DATE)                                               AS LAST_TRUCK_ROLL_DATE,
    SUM(IFF(SOLUTION = 'Replaced Ont', 1, 0))                       AS ONT_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Wall Wart', 1, 0))                 AS WALL_WART_COUNT,
    SUM(IFF(SOLUTION = 'Replaced Controller', 1, 0))                AS CONTROLLER_COUNT,
    ROUND(AVG(RESOLUTION_HOURS), 2)                                 AS AVG_RESOLUTION_HOURS,
    (COUNT(*) >= 3)                                                 AS IS_REPEAT_ADDRESS_3PLUS
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED
GROUP BY SERVICE_ADDRESS, SERVICE_CITY, SERVICE_REVENUE_AREA
ORDER BY TRUCK_ROLL_COUNT DESC;

-- ------------------------------------------------------------------------------
-- 8. VW_TRUCK_ROLL_DATA_QUALITY_ISSUES
--    Row-level list of every flagged record (duplicate ORDER_NUMBER and/or
--    inverted dates) for an admin-facing data-quality panel — so issues are
--    visible instead of silently dropped from KPI totals.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW ANALYTICS.VW_TRUCK_ROLL_DATA_QUALITY_ISSUES AS
SELECT
    ONT_TRUCK_ROLL_ID,
    ACCOUNT,
    ACCOUNT_NUMBER,
    ORDER_NUMBER,
    ENTERED_DATE,
    SOLUTION_DATE,
    IS_DUPLICATE_ORDER_NUMBER,
    IS_DATE_ANOMALY
FROM ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED
WHERE IS_DUPLICATE_ORDER_NUMBER OR IS_DATE_ANOMALY
ORDER BY ONT_TRUCK_ROLL_ID;
