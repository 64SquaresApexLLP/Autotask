# ONT Truck Roll — Phase 5: Cortex Summary Generation

Scope: **only** the four summaries below. No Admin dashboard, no additional
summary types, no changes to RAW tables, existing analytics views, geocoding,
or weather-matching logic.

## Architecture

```
Validated analytics/weather views (existing, unmodified)
        ↓
SQL aggregation (scripts/generate_cortex_summaries.py — plain GROUP BY/COUNT/AVG)
        ↓
Small structured JSON fact set (never row-level data, never all 3,040 records)
        ↓
SNOWFLAKE.CORTEX.COMPLETE  (llama3.3-70b, fallback llama3.1-70b)
        ↓
ANALYTICS.CORTEX_SUMMARIES (persisted, append-only, one row per generation)
        ↓
Future Admin dashboard (not built in this phase)
```

Cortex is never given row-level access to `VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED`
or any other view. Every number it can reference is pre-computed in SQL first
and handed to it as a small JSON object — Cortex's only job is to phrase real
numbers in plain English, not to compute or invent them.

## Cortex model

`SNOWFLAKE.CORTEX.COMPLETE`, primary model **`llama3.3-70b`**, fallback
**`llama3.1-70b`** if the primary call fails for any reason (both models were
directly tested and confirmed working in this Snowflake account/region before
being chosen; `mistral-large`/`mistral-large2` were tested and found
deprecated/legacy in this account, so were excluded). All four summaries
succeeded on the primary model on the initial run — no fallback was needed in
practice, but the fallback path exists and is exercised automatically on any
future failure.

`SNOWFLAKE.CORTEX.COMPLETE` is called via a direct cursor on the existing
`SnowflakeConnection` (same connection class used project-wide), rather than
through `SnowflakeConnection.call_cortex_llm()`. Reason: `call_cortex_llm()`
swallows exceptions internally and returns `None` on failure, which would
discard the exact error message needed for the audit trail
(`MODEL_ATTEMPT_LOG` / `GENERATION_ERROR` columns below). This still calls the
same underlying `SNOWFLAKE.CORTEX.COMPLETE` SQL function through the same
connection — not a second Cortex integration.

## The four summaries

| Summary type | Source view(s) | What it covers |
|---|---|---|
| `OVERALL` | `ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY` | total truck rolls, date range, resolution-time stats |
| `SOLUTION_BREAKDOWN` | `ANALYTICS.VW_TRUCK_ROLL_BY_SOLUTION` | ONT/Wall Wart/Controller counts, %, avg resolution time |
| `WEATHER_DURING_INCIDENTS` | `ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED` | exact vs. approximate weather split, precipitation co-occurrence |
| `DATA_QUALITY` | `ANALYTICS.VW_TRUCK_ROLL_DATA_QUALITY_ISSUES` | duplicate order number, date anomalies, weather coverage split |

No new SQL aggregation views were created — all four summaries query the
existing, already-validated views directly.

## Exact vs. approximate weather handling

`WEATHER_DURING_INCIDENTS` is built from `LOCATION_MATCH_TYPE`/`WEATHER_MATCH_STATUS`
on the enriched view, bucketed as:
- **EXACT** (`LOCATION_MATCH_TYPE = 'EXACT'`) — weather measured at the real geocoded service address.
- **APPROXIMATE** (`AREA_CENTROID` or `CITY_CENTROID`) — weather from a same-area or same-city average location, not the actual address.

The prompt explicitly requires the two figures to be stated **separately**
(never blended into one "weather coverage" number) and explicitly states that
approximate weather "is NOT the same as weather measured at the exact service
address" — verified present in the generated text on every run so far.

## No-causation rule

Every prompt includes a hard instruction: state co-occurrence
("occurred during periods with precipitation"), never causation ("caused by",
"triggered by", etc.). This is enforced two ways:
1. Explicit instruction text in every prompt (`NO_INVENTION_RULE` constant in the script).
2. A post-generation keyword scan (`check_causal_language()`) against a list of
   causal phrases, logged in the console output for manual review — all four
   generated summaries passed clean on the first run.

## Persisted table: `ANALYTICS.CORTEX_SUMMARIES`

Append-only — each run of `generate_cortex_summaries.py` adds new rows rather
than replacing old ones, so past summaries and the exact facts behind them
stay available for audit. Columns: `SUMMARY_TYPE`, `SUMMARY_TEXT`,
`MODEL_USED`, `MODEL_ATTEMPT_LOG` (full retry history), `SOURCE_VIEWS`,
`INPUT_FACTS` (the exact JSON given to Cortex, as `VARIANT`),
`GENERATION_STATUS`, `GENERATION_ERROR`, `GENERATED_AT`.

To get only the current summary of each type:
```sql
SELECT *
FROM ANALYTICS.CORTEX_SUMMARIES
QUALIFY ROW_NUMBER() OVER (PARTITION BY SUMMARY_TYPE ORDER BY GENERATED_AT DESC) = 1;
```

## Regeneration process

```
python scripts/generate_cortex_summaries.py
```
Safe to rerun any time (e.g. after a RAW/weather reload) — it recomputes all
facts fresh from the current views and inserts new rows; it never modifies
RAW tables, geocoding, weather, or the enriched view, and never deletes prior
summary rows.

## Verification performed on every run

- **Causal-language check** — scans generated text for a list of causal
  phrases ("caused", "due to the weather", "triggered by", …). All four
  summaries: clean.
- **Number-traceability check** — extracts every number in the generated text
  and confirms it appears in the JSON facts that were given to Cortex. All
  four summaries: 100% of numbers traced, 0 untraced.

Both checks are printed to console on every generation run for manual review
alongside the full input facts and generated text, so any future run can be
independently verified the same way this initial run was.
