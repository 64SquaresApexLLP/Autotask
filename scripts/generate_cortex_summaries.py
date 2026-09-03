#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 5: generate the four initial Cortex summaries.

Architecture:
    validated analytics/weather views -> SQL aggregation (this script)
    -> small structured JSON fact set -> SNOWFLAKE.CORTEX.COMPLETE
    -> persisted in ANALYTICS.CORTEX_SUMMARIES

Cortex is given ONLY pre-computed aggregate numbers (never row-level data,
never all 3,040 records) and is explicitly instructed not to invent figures
and not to claim causation between weather and truck rolls.

Does not touch RAW.ONT_TRUCK_ROLL, RAW.SERVICE_ADDRESS_GEOCODE,
RAW.WEATHER_OBSERVATIONS_OPENMETEO, RAW.LOCATION_CENTROIDS, or any existing
ANALYTICS view — only reads them, and writes new rows to
ANALYTICS.CORTEX_SUMMARIES.

Model calling: SNOWFLAKE.CORTEX.COMPLETE is called via a direct cursor
(same SnowflakeConnection already used project-wide), not through
SnowflakeConnection.call_cortex_llm(), specifically so a model failure's
exact error text can be captured and persisted for audit (call_cortex_llm()
swallows exceptions internally and returns None on failure, which would
lose the failure reason). This is the same underlying SNOWFLAKE.CORTEX.COMPLETE
call the project already uses elsewhere — not a second Cortex mechanism.

Usage:
    python scripts/generate_cortex_summaries.py
"""

import os
import re
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DDL_FILE = os.path.join(PROJECT_ROOT, "ont_truck_roll_data", "CORTEX_SUMMARIES_DDL.sql")

PRIMARY_MODEL = "llama3.3-70b"
FALLBACK_MODEL = "llama3.1-70b"

NO_INVENTION_RULE = (
    "You are writing a factual summary for an internal operations report. "
    "You MUST use ONLY the numbers given to you below in the FACTS block. "
    "Do NOT invent, estimate, or round to a different number than given. "
    "Do NOT state or imply that weather caused, triggered, or was responsible for "
    "any truck roll — only that truck rolls occurred during certain weather "
    "conditions (correlation/co-occurrence language only, never causal language). "
    "Write 2 to 4 plain sentences, no bullet points, no headers."
)


def connect():
    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT, sf_user=SF_USER, sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE, sf_schema=SF_SCHEMA, sf_role=SF_ROLE,
        sf_authenticator=SF_AUTHENTICATOR, sf_password=SF_PASSWORD, sf_passcode=SF_PASSCODE,
        sf_private_key_file=SF_PRIVATE_KEY_PATH, sf_private_key_pwd=SF_PRIVATE_KEY_PWD,
    )
    if not conn.is_connected():
        print("[ERROR] Failed to connect to Snowflake. Check credentials/network.")
        sys.exit(1)
    print(f"[OK] Connected to Snowflake ({SF_ACCOUNT}, db={SF_DATABASE}, role={SF_ROLE}).")
    return conn


def run_ddl(conn):
    with open(DDL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    code = re.sub(r"--[^\n]*", "", sql)
    statements = [s.strip() for s in code.split(";") if s.strip()]
    cursor = conn.conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    cursor.close()
    print(f"[OK] ANALYTICS.CORTEX_SUMMARIES ready ({len(statements)} DDL statements applied).")


def call_cortex(conn, prompt, model):
    """Call SNOWFLAKE.CORTEX.COMPLETE directly via cursor to preserve the exact error on failure."""
    escaped = prompt.replace("'", "''")
    query = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{escaped}') AS RESP"
    cursor = conn.conn.cursor()
    try:
        cursor.execute(query)
        row = cursor.fetchone()
        return (row[0] if row else None), None
    except Exception as e:
        return None, str(e)
    finally:
        cursor.close()


def generate_summary(conn, prompt):
    """Try PRIMARY_MODEL, fall back to FALLBACK_MODEL on failure. Returns dict with full audit trail."""
    attempt_log = []
    text, err = call_cortex(conn, prompt, PRIMARY_MODEL)
    if text:
        attempt_log.append(f"{PRIMARY_MODEL}: SUCCESS")
        return {"text": text.strip(), "model_used": PRIMARY_MODEL, "attempt_log": "; ".join(attempt_log),
                "status": "SUCCESS", "error": None}
    attempt_log.append(f"{PRIMARY_MODEL}: FAILED ({err})")

    text, err = call_cortex(conn, prompt, FALLBACK_MODEL)
    if text:
        attempt_log.append(f"{FALLBACK_MODEL}: SUCCESS")
        return {"text": text.strip(), "model_used": FALLBACK_MODEL, "attempt_log": "; ".join(attempt_log),
                "status": "SUCCESS", "error": None}
    attempt_log.append(f"{FALLBACK_MODEL}: FAILED ({err})")

    return {"text": None, "model_used": None, "attempt_log": "; ".join(attempt_log),
            "status": "FAILED", "error": err}


def persist(conn, summary_type, result, source_views, facts):
    cursor = conn.conn.cursor()
    cursor.execute("""
        INSERT INTO ANALYTICS.CORTEX_SUMMARIES
            (SUMMARY_TYPE, SUMMARY_TEXT, MODEL_USED, MODEL_ATTEMPT_LOG, SOURCE_VIEWS,
             INPUT_FACTS, GENERATION_STATUS, GENERATION_ERROR)
        SELECT %s, %s, %s, %s, %s, PARSE_JSON(%s), %s, %s
    """, (summary_type, result["text"], result["model_used"], result["attempt_log"],
          source_views, json.dumps(facts, default=str), result["status"], result["error"]))
    cursor.close()


CAUSAL_PHRASES = [
    "caused by", "caused", "due to the weather", "because of the weather",
    "resulted from the weather", "led to the truck roll", "triggered by",
    "weather caused", "storms caused", "precipitation caused", "rain caused",
]


def check_causal_language(text):
    if not text:
        return []
    lower = text.lower()
    return [p for p in CAUSAL_PHRASES if p in lower]


def check_numbers_traceable(text, facts):
    """Lightweight check: every standalone number in the summary should appear
    somewhere in the facts JSON (as a substring match on stringified values)."""
    if not text:
        return [], []
    fact_str = json.dumps(facts, default=str)
    numbers_in_text = set(re.findall(r"\d+\.?\d*", text))
    traced, untraced = [], []
    for n in numbers_in_text:
        if n in fact_str:
            traced.append(n)
        else:
            # tolerate trivial formatting diffs (e.g. "3040" vs "3,040", trailing .0)
            n_nodot = n.rstrip("0").rstrip(".") if "." in n else n
            if n in fact_str.replace(",", "") or n_nodot in fact_str:
                traced.append(n)
            else:
                untraced.append(n)
    return traced, untraced


if __name__ == "__main__":
    conn = connect()
    try:
        run_ddl(conn)

        def q(sql):
            return conn.execute_query(sql)

        # ------------------------------------------------------------------
        # SUMMARY 1 — OVERALL  (source: VW_TRUCK_ROLL_KPI_SUMMARY)
        # ------------------------------------------------------------------
        kpi = q("SELECT * FROM ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY")[0]
        facts_overall = {
            "total_truck_rolls": kpi["TOTAL_TRUCK_ROLLS"],
            "date_range_start": str(kpi["EARLIEST_ENTERED_DATE"]),
            "date_range_end": str(kpi["LATEST_ENTERED_DATE"]),
            "unique_service_addresses": kpi["UNIQUE_SERVICE_ADDRESSES"],
            "unique_accounts": kpi["UNIQUE_ACCOUNTS"],
            "avg_resolution_hours": float(kpi["AVG_RESOLUTION_HOURS"]),
            "median_resolution_hours": float(kpi["MEDIAN_RESOLUTION_HOURS"]),
        }
        prompt_overall = (
            f"{NO_INVENTION_RULE}\n\nFACTS:\n{json.dumps(facts_overall, indent=2)}\n\n"
            "Write an overall summary of this ONT truck-roll dataset covering the total "
            "count, the date range, and the resolution-time statistics."
        )

        # ------------------------------------------------------------------
        # SUMMARY 2 — SOLUTION BREAKDOWN  (source: VW_TRUCK_ROLL_BY_SOLUTION)
        # ------------------------------------------------------------------
        by_solution = q("SELECT * FROM ANALYTICS.VW_TRUCK_ROLL_BY_SOLUTION ORDER BY TRUCK_ROLL_COUNT DESC")
        facts_solution = {
            "total_truck_rolls": kpi["TOTAL_TRUCK_ROLLS"],
            "solutions": [
                {"solution": r["SOLUTION"], "count": r["TRUCK_ROLL_COUNT"],
                 "pct_of_total": float(r["PCT_OF_TOTAL"]), "avg_resolution_hours": float(r["AVG_RESOLUTION_HOURS"])}
                for r in by_solution
            ],
        }
        prompt_solution = (
            f"{NO_INVENTION_RULE}\n\nFACTS:\n{json.dumps(facts_solution, indent=2)}\n\n"
            "Write a summary of the breakdown of truck rolls by solution type "
            "(Replaced Ont, Replaced Wall Wart, Replaced Controller), including counts, "
            "percentages, and any notable difference in average resolution time between them."
        )

        # ------------------------------------------------------------------
        # SUMMARY 3 — WEATHER DURING INCIDENTS  (source: VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED)
        # ------------------------------------------------------------------
        weather_rows = q("""
            SELECT
                CASE WHEN LOCATION_MATCH_TYPE='EXACT' THEN 'EXACT' ELSE 'APPROXIMATE' END AS BUCKET,
                LOCATION_MATCH_TYPE,
                COUNT(*) AS N,
                SUM(IFF(PRECIPITATION_MM > 0, 1, 0)) AS WITH_PRECIP,
                ROUND(AVG(TEMPERATURE_C), 1) AS AVG_TEMP_C,
                ROUND(AVG(WIND_SPEED_KMH), 1) AS AVG_WIND_KMH,
                SUM(IFF(IS_SEVERE_WEATHER, 1, 0)) AS SEVERE_COUNT
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            GROUP BY BUCKET, LOCATION_MATCH_TYPE
        """)
        total_weather = q("SELECT COUNT(*) N FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED")[0]["N"]
        exact_n = sum(r["N"] for r in weather_rows if r["BUCKET"] == "EXACT")
        approx_n = sum(r["N"] for r in weather_rows if r["BUCKET"] == "APPROXIMATE")
        exact_precip = sum(r["WITH_PRECIP"] for r in weather_rows if r["BUCKET"] == "EXACT")
        approx_precip = sum(r["WITH_PRECIP"] for r in weather_rows if r["BUCKET"] == "APPROXIMATE")
        facts_weather = {
            "total_truck_rolls": total_weather,
            "exact_weather": {
                "count": exact_n,
                "pct_of_total": round(100 * exact_n / total_weather, 1),
                "truck_rolls_with_measurable_precipitation": exact_precip,
                "pct_with_precipitation": round(100 * exact_precip / exact_n, 1) if exact_n else 0,
            },
            "approximate_weather": {
                "count": approx_n,
                "pct_of_total": round(100 * approx_n / total_weather, 1),
                "breakdown": [
                    {"type": r["LOCATION_MATCH_TYPE"], "count": r["N"]}
                    for r in weather_rows if r["BUCKET"] == "APPROXIMATE"
                ],
                "truck_rolls_with_measurable_precipitation": approx_precip,
                "pct_with_precipitation": round(100 * approx_precip / approx_n, 1) if approx_n else 0,
            },
            "severe_weather_thunderstorm_code_count": sum(r["SEVERE_COUNT"] for r in weather_rows),
            "note": "APPROXIMATE means weather from a SERVICE_REVENUE_AREA or SERVICE_CITY centroid, "
                    "not the exact service address, because the address could not be geocoded.",
        }
        prompt_weather = (
            f"{NO_INVENTION_RULE}\n\nFACTS:\n{json.dumps(facts_weather, indent=2)}\n\n"
            "Write a summary of weather conditions during these truck-roll incidents. "
            "You MUST clearly state the exact_weather count/percentage and the approximate_weather "
            "count/percentage as SEPARATE figures, and explicitly say that approximate weather is "
            "NOT the same as weather measured at the exact service address. Mention the percentage "
            "of exact-location truck rolls that occurred during measurable precipitation, using "
            "language like 'occurred during periods with precipitation' — never causal language."
        )

        # ------------------------------------------------------------------
        # SUMMARY 4 — DATA QUALITY  (source: VW_TRUCK_ROLL_DATA_QUALITY_ISSUES + KPI + weather facts)
        # ------------------------------------------------------------------
        dq_rows = q("SELECT * FROM ANALYTICS.VW_TRUCK_ROLL_DATA_QUALITY_ISSUES")
        dup_order_rows = [r for r in dq_rows if r["IS_DUPLICATE_ORDER_NUMBER"]]
        date_anomaly_rows = [r for r in dq_rows if r["IS_DATE_ANOMALY"]]
        facts_dq = {
            "total_source_rows": kpi["TOTAL_TRUCK_ROLLS"],
            "duplicate_order_number_count": len(dup_order_rows),
            "duplicate_order_numbers": sorted({r["ORDER_NUMBER"] for r in dup_order_rows}),
            "date_anomaly_row_count": len(date_anomaly_rows),
            "date_anomaly_description": "rows where the recorded solution timestamp is earlier than the recorded entry timestamp",
            "exact_weather_coverage_pct": facts_weather["exact_weather"]["pct_of_total"],
            "approximate_weather_coverage_pct": facts_weather["approximate_weather"]["pct_of_total"],
        }
        prompt_dq = (
            f"{NO_INVENTION_RULE}\n\nFACTS:\n{json.dumps(facts_dq, indent=2)}\n\n"
            "Write a neutral data-quality note for an admin dashboard footnote covering: the total "
            "row count, the duplicate order number issue, the date anomaly rows, and the exact vs "
            "approximate weather coverage split. Do NOT speculate about why these issues occurred — "
            "state only that they exist."
        )

        # ------------------------------------------------------------------
        # Generate all four
        # ------------------------------------------------------------------
        jobs = [
            ("OVERALL", prompt_overall, "ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY", facts_overall),
            ("SOLUTION_BREAKDOWN", prompt_solution, "ANALYTICS.VW_TRUCK_ROLL_BY_SOLUTION, ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY", facts_solution),
            ("WEATHER_DURING_INCIDENTS", prompt_weather, "ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED", facts_weather),
            ("DATA_QUALITY", prompt_dq, "ANALYTICS.VW_TRUCK_ROLL_DATA_QUALITY_ISSUES, ANALYTICS.VW_TRUCK_ROLL_KPI_SUMMARY", facts_dq),
        ]

        results = {}
        for summary_type, prompt, source_views, facts in jobs:
            print(f"\n[*] Generating {summary_type} summary ...")
            result = generate_summary(conn, prompt)
            persist(conn, summary_type, result, source_views, facts)
            results[summary_type] = {"result": result, "facts": facts, "source_views": source_views}
            print(f"    status={result['status']} model={result['model_used']} attempts=[{result['attempt_log']}]")

        # ------------------------------------------------------------------
        # Print full report: text + facts + causal-language + traceability check
        # ------------------------------------------------------------------
        print("\n" + "=" * 78)
        print(" GENERATED SUMMARIES + GROUNDING FACTS")
        print("=" * 78)
        for summary_type, data in results.items():
            r = data["result"]
            print(f"\n--- {summary_type} ---")
            print(f"Model used: {r['model_used']}   Status: {r['status']}   Attempts: {r['attempt_log']}")
            print(f"Source views: {data['source_views']}")
            print(f"Input facts:\n{json.dumps(data['facts'], indent=2)}")
            print(f"\nGenerated text:\n{r['text']}")
            causal_hits = check_causal_language(r["text"])
            traced, untraced = check_numbers_traceable(r["text"], data["facts"])
            print(f"\nCausal-language check: {'FLAGGED: ' + str(causal_hits) if causal_hits else 'clean'}")
            print(f"Number traceability check: {len(traced)} traced, {len(untraced)} NOT found in facts: {untraced}")
    finally:
        conn.close_connection()
