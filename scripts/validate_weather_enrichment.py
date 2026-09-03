#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 3: validate the weather enrichment layer.

Read-only. Does not modify RAW.ONT_TRUCK_ROLL, existing analytics views, or
any weather-layer objects.

Usage:
    python scripts/validate_weather_enrichment.py
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

BASELINE = {
    "TOTAL_TRUCK_ROLLS": 3040,
    "UNIQUE_SERVICE_ADDRESSES": 2038,
    "ONT_REPLACED_COUNT": 1694,
    "WALL_WART_REPLACED_COUNT": 1214,
    "CONTROLLER_REPLACED_COUNT": 132,
}


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


if __name__ == "__main__":
    conn = connect()
    try:
        def q(sql):
            return conn.execute_query(sql)

        print("\n" + "=" * 78)
        print(" A-C. RAW UNCHANGED / EXISTING KPI CHECK")
        print("=" * 78)
        raw_total = q("SELECT COUNT(*) N FROM RAW.ONT_TRUCK_ROLL")[0]["N"]
        addr = q("SELECT COUNT(DISTINCT SERVICE_ADDRESS) N FROM RAW.ONT_TRUCK_ROLL")[0]["N"]
        ont = q("SELECT COUNT(*) N FROM RAW.ONT_TRUCK_ROLL WHERE SOLUTION='Replaced Ont'")[0]["N"]
        ww = q("SELECT COUNT(*) N FROM RAW.ONT_TRUCK_ROLL WHERE SOLUTION='Replaced Wall Wart'")[0]["N"]
        ctl = q("SELECT COUNT(*) N FROM RAW.ONT_TRUCK_ROLL WHERE SOLUTION='Replaced Controller'")[0]["N"]
        actual = {
            "TOTAL_TRUCK_ROLLS": raw_total, "UNIQUE_SERVICE_ADDRESSES": addr,
            "ONT_REPLACED_COUNT": ont, "WALL_WART_REPLACED_COUNT": ww, "CONTROLLER_REPLACED_COUNT": ctl,
        }
        for k, expected in BASELINE.items():
            got = actual[k]
            print(f"   {k}: expected={expected} actual={got} [{'MATCH' if got == expected else 'MISMATCH'}]")

        print("\n" + "=" * 78)
        print(" D. WEATHER DATA COVERAGE")
        print("=" * 78)
        wrange = q("SELECT MIN(WEATHER_TIMESTAMP_UTC) MN, MAX(WEATHER_TIMESTAMP_UTC) MX, COUNT(*) N FROM RAW.WEATHER_OBSERVATIONS_OPENMETEO")[0]
        erange = q("SELECT MIN(ENTERED_DATE) MN, MAX(ENTERED_DATE) MX FROM RAW.ONT_TRUCK_ROLL")[0]
        print(f"   RAW.ONT_TRUCK_ROLL ENTERED_DATE range:        {erange['MN']} -> {erange['MX']}")
        print(f"   RAW.WEATHER_OBSERVATIONS_OPENMETEO range:      {wrange['MN']} -> {wrange['MX']} ({wrange['N']} rows)")

        print("\n" + "=" * 78)
        print(" H. ROW MULTIPLICATION CHECK")
        print("=" * 78)
        enriched_total = q("SELECT COUNT(*) N FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED")[0]["N"]
        print(f"   Input RAW.ONT_TRUCK_ROLL rows:                 {raw_total}")
        print(f"   ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED rows: {enriched_total}")
        print(f"   Match: {'YES - no row multiplication' if enriched_total == raw_total else 'NO - MISMATCH, investigate join'}")

        dup_ids = q("""
            SELECT ONT_TRUCK_ROLL_ID, COUNT(*) N
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            GROUP BY ONT_TRUCK_ROLL_ID HAVING COUNT(*) > 1
        """)
        print(f"   ONT_TRUCK_ROLL_ID appearing more than once in enriched view: {len(dup_ids)}")

        print("\n" + "=" * 78)
        print(" WEATHER_MATCH_STATUS BREAKDOWN")
        print("=" * 78)
        statuses = q("""
            SELECT WEATHER_MATCH_STATUS, COUNT(*) N
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            GROUP BY WEATHER_MATCH_STATUS ORDER BY N DESC
        """)
        for r in statuses:
            print(f"   {r['WEATHER_MATCH_STATUS']}: {r['N']}")

        print("\n" + "=" * 78)
        print(" E/F. UTC INTERPRETATION SANITY CHECK (spot check one row)")
        print("=" * 78)
        spot = q("""
            SELECT ORDER_NUMBER, ENTERED_DATE, INCIDENT_TIMESTAMP_UTC, WEATHER_HOUR_UTC, WEATHER_TIMESTAMP_UTC
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            WHERE WEATHER_MATCH_STATUS = 'MATCHED'
            LIMIT 1
        """)
        for r in spot:
            print(f"   {r}")

        print("\n" + "=" * 78)
        print(" GEOCODING SUMMARY (from RAW.SERVICE_ADDRESS_GEOCODE)")
        print("=" * 78)
        geo = q("""
            SELECT GEOCODING_STATUS, COUNT(*) N
            FROM RAW.SERVICE_ADDRESS_GEOCODE
            GROUP BY GEOCODING_STATUS ORDER BY N DESC
        """)
        for r in geo:
            print(f"   {r['GEOCODING_STATUS']}: {r['N']}")

        print("\n" + "=" * 78)
        print(" N. SAMPLE ENRICHED RECORDS (10, varied dates/locations)")
        print("=" * 78)
        samples = q("""
            SELECT ORDER_NUMBER, ENTERED_DATE, SERVICE_ADDRESS, SERVICE_CITY, SERVICE_REVENUE_AREA,
                   LATITUDE, LONGITUDE, LOCATION_MATCH_TYPE, INCIDENT_TIMESTAMP_UTC, WEATHER_TIMESTAMP_UTC,
                   TEMPERATURE_C, PRECIPITATION_MM, WIND_SPEED_KMH, WEATHER_CONDITION,
                   WEATHER_MATCH_STATUS
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            WHERE WEATHER_MATCH_STATUS IN ('MATCHED','AREA_CENTROID_APPROXIMATE','CITY_CENTROID_APPROXIMATE')
            QUALIFY ROW_NUMBER() OVER (PARTITION BY WEATHER_MATCH_STATUS ORDER BY ENTERED_DATE) <= 4
            LIMIT 12
        """)
        for r in samples:
            print(f"   {r}")

        print("\n" + "=" * 78)
        print(" LOCATION_MATCH_TYPE BREAKDOWN (unique addresses per type)")
        print("=" * 78)
        loc = q("""
            SELECT LOCATION_MATCH_TYPE, COUNT(*) TRUCK_ROLLS,
                   COUNT(DISTINCT SERVICE_ADDRESS) UNIQUE_ADDRESSES
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            GROUP BY LOCATION_MATCH_TYPE ORDER BY TRUCK_ROLLS DESC
        """)
        for r in loc:
            print(f"   {r}")

        print("\n" + "=" * 78)
        print(" SAMPLE UNMATCHED RECORDS (up to 5, for each failure reason)")
        print("=" * 78)
        for status in ("NO_GEOCODE", "GEOCODE_FAILED", "NO_WEATHER_DATA"):
            rows = q(f"""
                SELECT ORDER_NUMBER, SERVICE_ADDRESS, SERVICE_CITY, ENTERED_DATE
                FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
                WHERE WEATHER_MATCH_STATUS = '{status}'
                LIMIT 5
            """)
            print(f"  -- {status} ({len(rows)} shown) --")
            for r in rows:
                print(f"     {r}")

        print("\n" + "=" * 78)
        print(" DUPLICATE ORDER_NUMBER / DATE ANOMALY ROWS STILL PRESENT (not removed)")
        print("=" * 78)
        dq = q("""
            SELECT ONT_TRUCK_ROLL_ID, ORDER_NUMBER, IS_DUPLICATE_ORDER_NUMBER, IS_DATE_ANOMALY, WEATHER_MATCH_STATUS
            FROM ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED
            WHERE IS_DUPLICATE_ORDER_NUMBER OR IS_DATE_ANOMALY
        """)
        for r in dq:
            print(f"   {r}")
    finally:
        conn.close_connection()
