#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 3/4: fetch historical hourly weather from Open-Meteo for
every (resolved location, incident day) actually needed by a truck roll, and
cache it in RAW.WEATHER_OBSERVATIONS_OPENMETEO. "Resolved location" follows
the same exact -> area centroid -> city centroid fallback as the enriched view
(Phase 4), so reruns after the fallback layer exists will fetch weather for
centroid coordinates too, reusing whatever is already cached from Phase 3.

Does NOT blindly backfill a full multi-year hourly series per location (that
would be ~64M rows for ~2,038 locations x ~3.6 years). Instead, groups truck
rolls by (ROUND(LATITUDE,4), ROUND(LONGITUDE,4), DATE(ENTERED_DATE)) and fetches
one calendar day of hourly data (24 rows) per group — enough to cover the
matched hour plus immediate neighbors for context.

Incremental/resumable: never truncates RAW.WEATHER_OBSERVATIONS_OPENMETEO.
Skips (lat, long, day) groups that are already cached, so reruns only fetch
what's missing (e.g. after a partial run, a rate limit, or new truck rolls).

Does not touch RAW.ONT_TRUCK_ROLL.

Usage:
    python scripts/fetch_open_meteo_weather.py
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_FIELDS = "temperature_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,relative_humidity_2m,weather_code"
WEATHER_SOURCE = "Open-Meteo ERA5 Archive"
MAX_WORKERS = 8
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3


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


def get_needed_groups(conn):
    """
    (lat, long, day) groups actually required by a truck roll's RESOLVED
    location — exact geocode, else a reliable AREA centroid, else a reliable
    CITY centroid (mirrors the same fallback priority and rounding rule as
    ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED in
    ont_truck_roll_data/WEATHER_FALLBACK_DDL.sql — kept in sync by hand).

    Grouped by the *post-rounding* WEATHER_HOUR_UTC's calendar date, not the
    raw ENTERED_DATE's date — an incident at e.g. 23:59 rounds forward to the
    next day's 00:00, so the day that needs to be fetched is sometimes the
    day after ENTERED_DATE.
    """
    rows = conn.execute_query("""
        WITH resolved AS (
            SELECT
                t.ONT_TRUCK_ROLL_ID,
                t.ENTERED_DATE,
                CASE
                    WHEN g.GEOCODING_STATUS = 'SUCCESS' THEN g.LATITUDE
                    WHEN area_c.IS_RELIABLE THEN area_c.LATITUDE
                    WHEN city_c.IS_RELIABLE THEN city_c.LATITUDE
                    ELSE NULL
                END AS LATITUDE,
                CASE
                    WHEN g.GEOCODING_STATUS = 'SUCCESS' THEN g.LONGITUDE
                    WHEN area_c.IS_RELIABLE THEN area_c.LONGITUDE
                    WHEN city_c.IS_RELIABLE THEN city_c.LONGITUDE
                    ELSE NULL
                END AS LONGITUDE
            FROM RAW.ONT_TRUCK_ROLL t
            LEFT JOIN RAW.SERVICE_ADDRESS_GEOCODE g
                ON t.SERVICE_ADDRESS = g.SERVICE_ADDRESS AND t.SERVICE_CITY = g.SERVICE_CITY
            LEFT JOIN RAW.LOCATION_CENTROIDS area_c
                ON area_c.CENTROID_LEVEL = 'AREA' AND area_c.CENTROID_KEY = t.SERVICE_REVENUE_AREA
            LEFT JOIN RAW.LOCATION_CENTROIDS city_c
                ON city_c.CENTROID_LEVEL = 'CITY' AND city_c.CENTROID_KEY = t.SERVICE_CITY
        )
        SELECT DISTINCT LATITUDE, LONGITUDE,
            TO_DATE(
                IFF(MINUTE(ENTERED_DATE) < 30,
                    DATE_TRUNC('HOUR', ENTERED_DATE),
                    DATEADD('HOUR', 1, DATE_TRUNC('HOUR', ENTERED_DATE)))
            ) AS INCIDENT_DATE
        FROM resolved
        WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL
    """)
    groups = {(r["LATITUDE"], r["LONGITUDE"], r["INCIDENT_DATE"]) for r in rows}
    print(f"[*] {len(groups)} distinct (location, day) groups needed (from geocoded truck rolls).")
    return groups


def get_already_cached(conn):
    rows = conn.execute_query("""
        SELECT DISTINCT LATITUDE, LONGITUDE, TO_DATE(WEATHER_TIMESTAMP_UTC) AS DAY
        FROM RAW.WEATHER_OBSERVATIONS_OPENMETEO
    """)
    cached = {(r["LATITUDE"], r["LONGITUDE"], r["DAY"]) for r in rows}
    print(f"[*] {len(cached)} (location, day) groups already cached in RAW.WEATHER_OBSERVATIONS_OPENMETEO.")
    return cached


def fetch_one_day(lat, lon, day):
    """Fetch one day's hourly weather for one location. Returns (rows, error)."""
    params = {
        "latitude": float(lat),
        "longitude": float(lon),
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
        "hourly": HOURLY_FIELDS,
        "timezone": "UTC",
    }
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                time.sleep(2 * attempt)
                last_err = "rate_limited"
                continue
            if resp.status_code != 200:
                last_err = f"http_{resp.status_code}: {resp.text[:200]}"
                time.sleep(1 * attempt)
                continue
            data = resp.json()
            hourly = data.get("hourly")
            if not hourly or "time" not in hourly:
                return [], "no_hourly_data_in_response"
            rows = []
            times = hourly["time"]
            for i, t in enumerate(times):
                rows.append({
                    "LATITUDE": lat,
                    "LONGITUDE": lon,
                    "WEATHER_TIMESTAMP_UTC": t.replace("T", " ") + ":00",
                    "TEMPERATURE_C": hourly.get("temperature_2m", [None] * len(times))[i],
                    "PRECIPITATION_MM": hourly.get("precipitation", [None] * len(times))[i],
                    "RAIN_MM": hourly.get("rain", [None] * len(times))[i],
                    "SNOWFALL_CM": hourly.get("snowfall", [None] * len(times))[i],
                    "WIND_SPEED_KMH": hourly.get("wind_speed_10m", [None] * len(times))[i],
                    "WIND_GUST_KMH": hourly.get("wind_gusts_10m", [None] * len(times))[i],
                    "RELATIVE_HUMIDITY_PCT": hourly.get("relative_humidity_2m", [None] * len(times))[i],
                    "WEATHER_CODE": hourly.get("weather_code", [None] * len(times))[i],
                })
            return rows, None
        except requests.RequestException as e:
            last_err = f"request_exception: {e}"
            time.sleep(1 * attempt)
    return [], last_err or "unknown_error"


def load_rows(conn, rows):
    if not rows:
        return
    cursor = conn.conn.cursor()
    insert_sql = """
        INSERT INTO RAW.WEATHER_OBSERVATIONS_OPENMETEO
            (LATITUDE, LONGITUDE, WEATHER_TIMESTAMP_UTC, TEMPERATURE_C, PRECIPITATION_MM,
             RAIN_MM, SNOWFALL_CM, WIND_SPEED_KMH, WIND_GUST_KMH, RELATIVE_HUMIDITY_PCT,
             WEATHER_CODE, WEATHER_SOURCE)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = [
        (r["LATITUDE"], r["LONGITUDE"], r["WEATHER_TIMESTAMP_UTC"], r["TEMPERATURE_C"],
         r["PRECIPITATION_MM"], r["RAIN_MM"], r["SNOWFALL_CM"], r["WIND_SPEED_KMH"],
         r["WIND_GUST_KMH"], r["RELATIVE_HUMIDITY_PCT"], r["WEATHER_CODE"], WEATHER_SOURCE)
        for r in rows
    ]
    cursor.executemany(insert_sql, values)
    cursor.close()


if __name__ == "__main__":
    conn = connect()
    try:
        needed = get_needed_groups(conn)
        cached = get_already_cached(conn)
        to_fetch = sorted(needed - cached, key=lambda g: (g[0], g[1], g[2]))
        print(f"[*] {len(to_fetch)} groups remaining to fetch (skipping {len(needed & cached)} already cached).")

        if not to_fetch:
            print("[OK] Nothing to fetch — all needed weather already cached.")
            sys.exit(0)

        requests_attempted = 0
        requests_succeeded = 0
        requests_failed = 0
        rows_retrieved = 0
        rows_loaded = 0
        failures = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_group = {
                executor.submit(fetch_one_day, lat, lon, day): (lat, lon, day)
                for (lat, lon, day) in to_fetch
            }
            done = 0
            for future in as_completed(future_to_group):
                group = future_to_group[future]
                requests_attempted += 1
                rows, err = future.result()
                if err:
                    requests_failed += 1
                    failures.append((group, err))
                else:
                    requests_succeeded += 1
                    rows_retrieved += len(rows)
                    load_rows(conn, rows)
                    rows_loaded += len(rows)
                done += 1
                if done % 100 == 0 or done == len(to_fetch):
                    print(f"  -> {done}/{len(to_fetch)} groups processed "
                          f"({requests_succeeded} ok, {requests_failed} failed, {rows_loaded} rows loaded so far)")

        print("\n" + "=" * 78)
        print(" OPEN-METEO FETCH SUMMARY")
        print("=" * 78)
        print(f" Groups needed:              {len(needed)}")
        print(f" Groups already cached:      {len(needed & cached)}")
        print(f" Groups fetched this run:    {len(to_fetch)}")
        print(f" Requests attempted:         {requests_attempted}")
        print(f" Requests succeeded:         {requests_succeeded}")
        print(f" Requests failed:            {requests_failed}")
        print(f" Weather observations retrieved: {rows_retrieved}")
        print(f" Weather observations loaded:    {rows_loaded}")
        print("=" * 78)

        if failures:
            print("\n Sample failures (up to 10):")
            for (lat, lon, day), err in failures[:10]:
                print(f"   lat={lat} lon={lon} day={day}: {err}")
    finally:
        conn.close_connection()
