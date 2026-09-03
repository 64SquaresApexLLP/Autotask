# ONT Truck Roll — Phase 1 (RAW) + Phase 2 (Analytics views)

Phase 1: land the client's ONT Truck Roll data in Snowflake and validate it.
Phase 2: a read-only KPI/analytics view layer on top of RAW, for a future Admin
dashboard to query. **No dashboard UI, weather integration, Cortex summaries,
ontology changes, or ticket reconciliation are implemented here** — those are
future phases.

## 1. Source file

`ONT Data/Ont Truck Roll Report.xlsx` — an Excel workbook (not a CSV), with 5 sheets:
`Complete List`, `2023`, `2024`, `2025`, `2026`. The per-year sheets are a breakdown
of the same data; `Complete List` is the full dataset and is the one used here.

**The workbook is never modified.** All original files stay untouched.

Source columns (`Complete List` sheet, in order):

```
Account, Account Number, Entered Date, Solution Date, Solution Entry User,
Order Number, Problem, Solution, Service Address, Service City,
Service Revenue Area, Order Status
```

### Footer row

`Complete List` has 3,041 data rows on disk. The **last row is a footer artifact**,
not a data row — `Account = "Count=3040"`, every other column blank:

```
Account=Count=3040, Account Number=' ', Entered Date=' ', ... (all blank)
```

`scripts/export_ont_truck_roll_csv.py` detects and drops this row (any row where
every column except `Account` is blank). The per-year sheets have the same pattern
(2 trailing blank rows each) and their real row counts sum to 3,040 as well,
independently confirming the same total.

## 2. CSV export

```
python scripts/export_ont_truck_roll_csv.py
```

Reads `Complete List`, drops the footer row, writes:

```
data/ont_truck_roll/ont_truck_roll.csv
```

3,040 data rows, UTF-8, standard CSV quoting (34 `Account` values contain commas,
e.g. `"Smith, John"` — pandas' default `QUOTE_MINIMAL` handles this; Snowflake's
`FIELD_OPTIONALLY_ENCLOSED_BY = '"'` file format reads it back correctly).

## 3. Snowflake objects

No `RAW` schema/prefix convention existed anywhere in this repo before Phase 1
(the only schema previously used was `TEST_DB.PUBLIC`; the closest existing
convention is `DIM_*`/`FACT_*` table prefixes in `snowflake_ontology_data/`).
Per the client's stated preference, this phase introduces a `RAW` schema in the
existing `TEST_DB` database.

| Object | Name |
|---|---|
| Database | `TEST_DB` (existing — reused from `config.py` / `.env`) |
| Schema | `TEST_DB.RAW` (new) |
| Table | `RAW.ONT_TRUCK_ROLL` |
| File format | `RAW.CSV_ONT_TRUCK_ROLL_FORMAT` |
| Stage | `RAW.ONT_TRUCK_ROLL_STAGE` (internal named stage) |

Full DDL: [`RAW_ONT_TRUCK_ROLL_DDL.sql`](RAW_ONT_TRUCK_ROLL_DDL.sql).

### Column mapping

RAW is kept as close to the source as possible — one column per source column,
same order, no invented business columns. Only addition: a small ingestion-lineage
set (`ONT_TRUCK_ROLL_ID`, `SOURCE_FILE_NAME`, `LOADED_AT`).

| Source column | Snowflake column | Type | Notes |
|---|---|---|---|
| — | `ONT_TRUCK_ROLL_ID` | `NUMBER AUTOINCREMENT` | surrogate key (source has no unique row id) |
| Account | `ACCOUNT` | `VARCHAR(256)` | |
| Account Number | `ACCOUNT_NUMBER` | `VARCHAR(64)` | |
| Entered Date | `ENTERED_DATE` | `TIMESTAMP_NTZ` | parsed from `M/D/YYYY H:MI AM/PM` |
| Solution Date | `SOLUTION_DATE` | `TIMESTAMP_NTZ` | parsed from `M/D/YYYY H:MI AM/PM` |
| Solution Entry User | `SOLUTION_ENTRY_USER` | `VARCHAR(128)` | |
| Order Number | `ORDER_NUMBER` | `VARCHAR(64)` | kept as text — see duplicate note below |
| Problem | `PROBLEM` | `VARCHAR(512)` | |
| Solution | `SOLUTION` | `VARCHAR(256)` | |
| Service Address | `SERVICE_ADDRESS` | `VARCHAR(512)` | |
| Service City | `SERVICE_CITY` | `VARCHAR(128)` | |
| Service Revenue Area | `SERVICE_REVENUE_AREA` | `VARCHAR(128)` | |
| Order Status | `ORDER_STATUS` | `VARCHAR(64)` | all 3,040 rows = `Updated` |
| — | `SOURCE_FILE_NAME` | `VARCHAR(256)` | literal `'ont_truck_roll.csv'` |
| — | `LOADED_AT` | `TIMESTAMP_NTZ` | `CURRENT_TIMESTAMP()` at load time |

No `PRIMARY KEY` on `ORDER_NUMBER` — see duplicate-handling note below.

## 4. Loading process

```
python scripts/ingest_ont_truck_roll.py
```

This reuses the existing project's Snowflake plumbing — `SnowflakeConnection`
(`src/database/snowflake_db.py`) and the `SF_*`/`.env` credentials already used by
`scripts/upload_to_snowflake.py` — no new connection or secret-management code
was introduced. Steps:

1. Connect to Snowflake (key-pair auth, per `.env`).
2. Apply `RAW_ONT_TRUCK_ROLL_DDL.sql` (schema, file format, stage, table —
   all `CREATE ... IF NOT EXISTS` / `CREATE OR REPLACE`, safe to re-run).
3. `PUT` the local CSV to `@RAW.ONT_TRUCK_ROLL_STAGE` (`OVERWRITE=TRUE`).
4. `TRUNCATE TABLE RAW.ONT_TRUCK_ROLL` — **RAW reload is full-refresh, not
   append**, so re-running never accumulates duplicate loads.
5. `COPY INTO RAW.ONT_TRUCK_ROLL` from the stage, with `TO_TIMESTAMP_NTZ(..., 'MM/DD/YYYY HH12:MI AM')`
   parsing on the two date columns and `ON_ERROR = 'ABORT_STATEMENT'` (fail loud
   on any bad row rather than silently skipping data).
6. Run validation queries (below) and print a pass/fail comparison against the
   client's baseline numbers.

Run `python scripts/ingest_ont_truck_roll.py --validate-only` to re-run just the
validation queries against whatever is already loaded, without reloading.

## 5. Validation SQL

```sql
-- A. Total row count
SELECT COUNT(*) FROM RAW.ONT_TRUCK_ROLL;

-- B. Entered Date range
SELECT MIN(ENTERED_DATE), MAX(ENTERED_DATE) FROM RAW.ONT_TRUCK_ROLL;

-- C/D. Distinct Solution values and counts
SELECT SOLUTION, COUNT(*) FROM RAW.ONT_TRUCK_ROLL GROUP BY SOLUTION ORDER BY COUNT(*) DESC;

-- E. Distinct service addresses
SELECT COUNT(DISTINCT SERVICE_ADDRESS) FROM RAW.ONT_TRUCK_ROLL;

-- F. Duplicate ORDER_NUMBERs
SELECT ORDER_NUMBER, COUNT(*) FROM RAW.ONT_TRUCK_ROLL
GROUP BY ORDER_NUMBER HAVING COUNT(*) > 1;

-- G. NULLs in important fields
SELECT
  SUM(IFF(ACCOUNT IS NULL,1,0))        AS NULL_ACCOUNT,
  SUM(IFF(ENTERED_DATE IS NULL,1,0))   AS NULL_ENTERED_DATE,
  SUM(IFF(SOLUTION_DATE IS NULL,1,0))  AS NULL_SOLUTION_DATE,
  SUM(IFF(ORDER_NUMBER IS NULL,1,0))   AS NULL_ORDER_NUMBER,
  SUM(IFF(SOLUTION IS NULL,1,0))       AS NULL_SOLUTION,
  SUM(IFF(SERVICE_ADDRESS IS NULL,1,0)) AS NULL_SERVICE_ADDRESS
FROM RAW.ONT_TRUCK_ROLL;

-- H. Fully-duplicate rows (all key fields identical)
SELECT COUNT(*) FROM (
  SELECT ACCOUNT, ACCOUNT_NUMBER, ENTERED_DATE, SOLUTION_DATE, ORDER_NUMBER,
         PROBLEM, SOLUTION, SERVICE_ADDRESS, COUNT(*) AS C
  FROM RAW.ONT_TRUCK_ROLL
  GROUP BY 1,2,3,4,5,6,7,8
  HAVING COUNT(*) > 1
);

-- H. Rows with inverted dates (Solution before Entered)
SELECT COUNT(*) FROM RAW.ONT_TRUCK_ROLL
WHERE SOLUTION_DATE < ENTERED_DATE;
```

## 6. Results (last run 2026-09-03)

| Check | Result |
|---|---|
| Total row count | **3,040** |
| Entered Date range | 2023-01-02 16:53 → 2026-08-10 10:14 |
| Replaced Ont | **1,694** |
| Replaced Wall Wart | **1,214** |
| Replaced Controller | **132** |
| Distinct Service Address | **2,038** |
| Duplicate ORDER_NUMBER groups | 1 (see below) |
| Fully-duplicate rows | 0 |
| NULLs in any important field | 0 |
| Order Status | 100% `Updated` |
| Rows with Solution Date before Entered Date | 2 (see below) |

**All five client-baseline figures match exactly**: 3,040 total / 1,694 ONT /
1,214 Wall Wart / 132 Controller / 2,038 unique addresses. No adjustment was
needed or made to hit these numbers — they fall out directly from excluding the
one footer row.

### Data-quality notes (informational, not fixed — RAW preserves source as-is)

- **One duplicate `ORDER_NUMBER` (586374)**: two rows, both `Dennis Sheldon`,
  same Entered/Solution Date, but two different Account Numbers
  (`00015403-8` vs `00075580-8`) and the same Service Address. This looks like
  one truck roll logged against two account records, not a load error — the CSV
  itself has both rows. Left as-is in RAW; worth a business decision in a later
  phase on how to treat it in aggregate reporting.
- **2 rows with Solution Date earlier than Entered Date** (`Wayne L Knight` /
  order 511795: entered 20:01, solved 17:02 same day; `Janita Evans` / order
  561777: entered 08:25, solved 17:20 the *previous* day). Both are small
  (~3h and ~15h) source-data timestamp inconsistencies, not ingestion bugs —
  loaded as-is.
- No NULLs anywhere, no exact duplicate rows, `Order Status` is uniformly
  `Updated` across all 3,040 rows — otherwise a clean dataset.

## 7. Reload instructions

To reload from scratch (e.g. after the client sends an updated workbook):

```bash
python scripts/export_ont_truck_roll_csv.py    # regenerate the CSV from the .xlsx
python scripts/ingest_ont_truck_roll.py         # PUT + TRUNCATE + COPY INTO + validate
```

`ingest_ont_truck_roll.py` regenerates the CSV itself if it's missing, so a plain
`python scripts/ingest_ont_truck_roll.py` is enough for a routine reload. The
`TRUNCATE TABLE` before `COPY INTO` means reloads always fully replace the table
contents — safe to re-run any number of times without accumulating duplicates.

## 8. Phase 2 — Analytics view layer

A read-only KPI/reporting layer sits on top of `RAW.ONT_TRUCK_ROLL`, in a new
`TEST_DB.ANALYTICS` schema (same "introduce the layer fresh, no prior convention
existed" situation as `RAW` in Phase 1). Every object is a **view**, not a table:

- `RAW.ONT_TRUCK_ROLL` is never modified by anything in this layer (no INSERT/UPDATE/DDL against RAW).
- Views are `CREATE OR REPLACE`, re-derived from RAW on every query — so a
  RAW reload (full truncate + COPY INTO) is picked up automatically with no
  separate refresh step to remember or forget.

Apply/refresh with:

```
python scripts/create_ont_truck_roll_analytics.py
```

Full DDL: [`ANALYTICS_ONT_TRUCK_ROLL_DDL.sql`](ANALYTICS_ONT_TRUCK_ROLL_DDL.sql).

| View | Purpose | Grain |
|---|---|---|
| `ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED` | Base view every other view builds on: passthrough of RAW plus `RESOLUTION_MINUTES`/`RESOLUTION_HOURS` (`SOLUTION_DATE − ENTERED_DATE`), `ENTERED_YEAR_MONTH`/`ENTERED_YEAR`/`ENTERED_MONTH`, and two flags — `IS_DUPLICATE_ORDER_NUMBER`, `IS_DATE_ANOMALY` | 1 row per RAW row (3,040) |
| `ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY` | Headline KPI card: totals, unique addresses/orders/accounts, date range, counts by Solution, avg/median resolution hours, data-quality counts | 1 row |
| `ANALYTICS.VW_TRUCK_ROLL_BY_SOLUTION` | Breakdown + % of total + avg resolution hours per Solution type | 1 row per Solution (3) |
| `ANALYTICS.VW_TRUCK_ROLL_MONTHLY_TREND` | Truck rolls per calendar month, split by Solution type, for a time-series chart | 1 row per month (44) |
| `ANALYTICS.VW_TRUCK_ROLL_BY_SERVICE_AREA` | Volume + avg resolution hours per Service Revenue Area / City | 1 row per area/city (70) |
| `ANALYTICS.VW_TRUCK_ROLL_BY_TECHNICIAN` | Workload + avg resolution hours per `SOLUTION_ENTRY_USER` | 1 row per technician (25) |
| `ANALYTICS.VW_TRUCK_ROLL_BY_ADDRESS` | Repeat-visit analysis per Service Address: truck roll count, first/last visit date, solution breakdown, `IS_REPEAT_ADDRESS_3PLUS` flag. `WHERE IS_REPEAT_ADDRESS_3PLUS` reproduces the client's Word-analysis figure exactly: **221 addresses, 772 truck rolls** | 1 row per address (2,038) |
| `ANALYTICS.VW_TRUCK_ROLL_DATA_QUALITY_ISSUES` | Row-level list of every flagged record (duplicate `ORDER_NUMBER` and/or inverted dates), for an admin data-quality panel — issues are surfaced, not silently dropped from the KPI totals | 4 rows currently |

**Design choice — flag, don't drop:** the known duplicate `ORDER_NUMBER`
(586374) and the 2 inverted-date rows are *included* in every KPI/aggregate
view (so `VW_TRUCK_ROLL_KPI_SUMMARY.TOTAL_TRUCK_ROLLS` still reads 3,040) but
flagged via `IS_DUPLICATE_ORDER_NUMBER`/`IS_DATE_ANOMALY` and separately listed
in `VW_TRUCK_ROLL_DATA_QUALITY_ISSUES`. Whether to exclude/de-duplicate them
from specific dashboard metrics is a business decision for the dashboard phase,
not something silently baked into this layer.

## 9. Phase 3 — Weather enrichment layer

Weather provider: **Open-Meteo** (Historical Weather / ERA5-ERA5-Land archive),
approved by manager. Geocoder: **US Census Bureau batch geocoder**. Both free,
neither requires an API key at this project's volume.

**Project decisions (fixed, not re-derived per run):**
- **Incident timestamp = `ENTERED_DATE`** (report/onset time). `SOLUTION_DATE`
  remains the completion timestamp and is not used for weather matching.
- **`ENTERED_DATE` is interpreted as UTC** for weather matching purposes only.
  The RAW column is `TIMESTAMP_NTZ` and its stored values are never modified —
  this is an interpretation applied only inside the weather layer's view logic.
- **`SERVICE_ADDRESS` (+ `SERVICE_CITY`)** is the geocoding key.

**Apply/refresh, in order:**
```
python scripts/create_weather_enrichment.py       # creates the 2 RAW tables + the enriched view
python scripts/geocode_ont_truck_roll_addresses.py # full-refresh geocode of all distinct addresses
python scripts/fetch_open_meteo_weather.py         # incremental/resumable weather cache
python scripts/validate_weather_enrichment.py      # read-only validation report
```
`fetch_open_meteo_weather.py` is safe to rerun any time (e.g. after new truck
rolls are ingested) — it only fetches `(location, day)` groups not already
cached, so a rerun after RAW is reloaded costs API calls only for genuinely new
locations/dates.

**Snowflake objects:**

| Object | Type | Refresh behavior |
|---|---|---|
| `RAW.SERVICE_ADDRESS_GEOCODE` | table | full-refresh (`CREATE OR REPLACE`) every geocode run — cheap, one Census batch call |
| `RAW.WEATHER_OBSERVATIONS_OPENMETEO` | table | incremental cache — never truncated, only appended to for missing `(lat, long, day)` groups |
| `ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED` | view | `CREATE OR REPLACE`, always reflects current RAW/geocode/weather state |

**Geocoding scope decision:** weather is fetched **only for the specific
`(location, day)` combinations a truck roll actually needs** — not a blind
multi-year backfill per location, which would have produced roughly 64 million
rows across ~2,038 locations × ~3.6 years. This kept the actual load to 1,951
API calls / ~46,872 cached hourly rows.

**Weather matching rule (exact, deterministic):**
```
WEATHER_HOUR_UTC =
    IF MINUTE(ENTERED_DATE) < 30 THEN DATE_TRUNC('HOUR', ENTERED_DATE)
    ELSE DATE_TRUNC('HOUR', ENTERED_DATE) + 1 hour
```
Joined to `RAW.WEATHER_OBSERVATIONS_OPENMETEO` on exact
`(LATITUDE, LONGITUDE, WEATHER_TIMESTAMP_UTC)` equality. `LATITUDE`/`LONGITUDE`
are stored as fixed `NUMBER(9,4)` (not `FLOAT`) in both the geocode and weather
tables specifically so this join is exact, never subject to floating-point
comparison drift — this is what guarantees the enriched view never multiplies
or drops truck-roll rows (verified: 3,040 in, 3,040 out, every run).

**Weather fields in `RAW.WEATHER_OBSERVATIONS_OPENMETEO` / the enriched view:**

| Column | Type | Source |
|---|---|---|
| `TEMPERATURE_C`, `PRECIPITATION_MM`, `RAIN_MM`, `SNOWFALL_CM`, `WIND_SPEED_KMH`, `WIND_GUST_KMH`, `RELATIVE_HUMIDITY_PCT`, `WEATHER_CODE` | DIRECT PROVIDER FIELD | Open-Meteo hourly variables, verbatim |
| `WEATHER_CONDITION` | DERIVED FIELD | WMO `WEATHER_CODE` mapped to a plain-language label (Clear sky / Partly cloudy / Fog / Drizzle / Rain / Snow / Rain showers / Snow showers / Thunderstorm / Other) |
| `IS_SEVERE_WEATHER` | DERIVED FIELD | `TRUE` when `WEATHER_CODE` is a WMO thunderstorm code (95–99), else `FALSE` |
| `WEATHER_MATCH_STATUS` | DERIVED FIELD | `MATCHED` / `GEOCODE_FAILED` / `NO_GEOCODE` / `NO_WEATHER_DATA` — see below |

### Results (last run 2026-09-03)

| Metric | Value |
|---|---|
| Distinct addresses geocoded | 2,038 |
| Geocoding SUCCESS | 1,375 (67.5%) |
| Geocoding FAILED | 635 (31.2%) |
| Geocoding AMBIGUOUS (Tie) | 28 (1.4%) |
| Open-Meteo `(location, day)` groups needed | 1,951 |
| Open-Meteo requests — succeeded / failed | 1,951 / 0 |
| Weather rows cached | 46,872 |
| Truck rolls with `WEATHER_MATCH_STATUS = MATCHED` | 1,962 (64.5%) |
| Truck rolls with `WEATHER_MATCH_STATUS = GEOCODE_FAILED` | 1,078 (35.5%) |
| Truck rolls with `WEATHER_MATCH_STATUS = NO_WEATHER_DATA` | 0 |
| `ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED` row count | 3,040 (exactly matches RAW — no multiplication, no drops) |

**Known limitation — geocoding coverage:** ~31% of addresses failed to
geocode via the US Census Bureau geocoder, almost entirely rural county roads
and private roads (e.g. `"51 County Road 196"`, `"512 Private Road 669"`) —
this is the exact risk flagged in the earlier weather-integration design
review. These truck rolls are **not silently dropped**: they remain in the
enriched view with `WEATHER_MATCH_STATUS = 'GEOCODE_FAILED'` and no weather
fields populated. A city/service-area-centroid fallback geocode was discussed
as an option in the design review but was **not implemented** in this phase —
it would be a deliberate follow-on decision, not something to add silently.

**Assumption documented in data:** source data has no `STATE` column: `'TX'`
was assumed for every geocoding request (all observed cities are Central Texas
municipalities) and is recorded per-row in `RAW.SERVICE_ADDRESS_GEOCODE.STATE_ASSUMED`
for audit — not hidden.

## 10. Phase 4 — Controlled geocoding fallback

Phase 3 left 35.5% of truck rolls (1,078 of 3,040) without weather because the
US Census geocoder failed on rural county/private/FM roads (confirmed via a
read-only investigation — tested address-format normalization on a sample and
recovered 0/25, meaning this is a geocoder *coverage* gap, not a formatting
fix). Phase 4 adds a controlled, transparent fallback — it never invents
coordinates and never hides that a result is approximate.

**`RAW.SERVICE_ADDRESS_GEOCODE` is untouched.** Its exact results from Phase 3
remain exactly as they were; nothing here overwrites or deletes them.

**Fallback priority (deterministic, documented):**
1. **EXACT** — `RAW.SERVICE_ADDRESS_GEOCODE.GEOCODING_STATUS = 'SUCCESS'` → `WEATHER_MATCH_STATUS = 'MATCHED'`
2. **AREA_CENTROID** — average lat/long of all exact-geocoded addresses sharing the same `SERVICE_REVENUE_AREA`, only used if at least 2 such addresses exist (`RAW.LOCATION_CENTROIDS.IS_RELIABLE`) → `WEATHER_MATCH_STATUS = 'AREA_CENTROID_APPROXIMATE'`
3. **CITY_CENTROID** — same, grouped by `SERVICE_CITY`, same reliability threshold → `WEATHER_MATCH_STATUS = 'CITY_CENTROID_APPROXIMATE'`
4. **FAILED** — neither exact nor a reliable centroid exists → `WEATHER_MATCH_STATUS = 'GEOCODE_FAILED'`

Every centroid is a plain `AVG()` of real, already-geocoded exact points from
this same dataset — **no external geocoding/estimation service, no invented
coordinates.** `RAW.LOCATION_CENTROIDS` is fully re-derivable, pure-SQL, and
safe to rebuild any time.

**Apply/refresh, in order (after Phase 3 has already run):**
```
python scripts/create_weather_fallback.py    # builds RAW.LOCATION_CENTROIDS, rebuilds the enriched view
python scripts/fetch_open_meteo_weather.py   # fetches weather for new centroid (location, day) groups only — reuses existing cache
python scripts/validate_weather_enrichment.py
```

**New/changed Snowflake objects:**

| Object | Type | Notes |
|---|---|---|
| `RAW.LOCATION_CENTROIDS` | table | full-refresh, pure SQL aggregation, no external calls |
| `ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED` | view | rebuilt (same name) — adds `ORIGINAL_GEOCODING_STATUS` (untouched Phase 3 audit value), `LOCATION_MATCH_TYPE` (`EXACT`/`AREA_CENTROID`/`CITY_CENTROID`/`FAILED`), and the 4-value `WEATHER_MATCH_STATUS` |

**⚠️ Approximate weather is not the same as weather measured at the actual
service address.** `AREA_CENTROID_APPROXIMATE` and `CITY_CENTROID_APPROXIMATE`
rows report the historical weather at the *average location of other,
successfully-geocoded addresses in the same area/city* — a reasonable regional
proxy, not a measurement at the truck roll's own address. Any consumer of this
view (dashboard, Cortex, reporting) must treat `WEATHER_MATCH_STATUS` as a
required field to show or filter on, never assume `MATCHED` accuracy for
`_APPROXIMATE` rows.

### Results (last run 2026-09-03)

| WEATHER_MATCH_STATUS | Truck rolls | % of 3,040 | Unique addresses |
|---|---|---|---|
| MATCHED (exact) | 1,962 | 64.5% | 1,375 |
| AREA_CENTROID_APPROXIMATE | 1,076 | 35.4% | 661 |
| CITY_CENTROID_APPROXIMATE | 2 | 0.1% | 2 |
| GEOCODE_FAILED | 0 | 0% | 0 |
| **Total** | **3,040** | **100%** | — |

Centroid reliability: 18 of 19 `SERVICE_REVENUE_AREA` values and 28 of 32
`SERVICE_CITY` values had a reliable (≥2-point) centroid; the 2 rows that
needed a city-level fallback are cases where the area-level centroid wasn't
reliable but the city-level one was.

Weather fetch for this phase: 965 new `(location, day)` groups needed (2,916
total needed − 1,951 already cached from Phase 3), all 965 succeeded, 23,160
new weather rows loaded — bringing the cache to 70,032 total rows.

**Validation — all pass:**
- RAW row count: 3,040 (unchanged)
- Existing KPIs unchanged: 1,694 / 1,214 / 132 / 2,038 (all match)
- Enriched view row count: 3,040 (no multiplication, no drops)
- 0 `ONT_TRUCK_ROLL_ID` duplicated in the enriched view
- Both known date-anomaly rows and both duplicate-`ORDER_NUMBER` rows still present, unmodified, correctly weather-matched

## 11. Phase 5 — Cortex summaries

See [`CORTEX_SUMMARIES.md`](CORTEX_SUMMARIES.md) for the full design: four
persisted natural-language summaries (Overall, Solution Breakdown, Weather
During Incidents, Data Quality) generated by `SNOWFLAKE.CORTEX.COMPLETE` from
pre-computed SQL aggregates only (never row-level data), stored in
`ANALYTICS.CORTEX_SUMMARIES`. Regenerate with
`python scripts/generate_cortex_summaries.py`.

## 12. Configuration required

Uses the existing project credentials — nothing new to configure. Reads from
root `.env` via `config.py` (`SF_ACCOUNT`, `SF_USER`, `SF_WAREHOUSE`, `SF_DATABASE`,
`SF_ROLE`, `SF_AUTHENTICATOR=keypair`, `SF_PRIVATE_KEY_PATH`, etc.) and connects
via `src/database/snowflake_db.py`. The role in `.env` (`ACCOUNTADMIN`) has
rights to create the `RAW` schema, stage, file format, and table; a narrower
role would need `CREATE SCHEMA` on `TEST_DB` plus the usual object-creation
grants within it.
