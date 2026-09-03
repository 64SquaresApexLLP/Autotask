#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 3: geocode every distinct SERVICE_ADDRESS via the
US Census Bureau batch geocoder, load results into RAW.SERVICE_ADDRESS_GEOCODE.

Does not touch RAW.ONT_TRUCK_ROLL. Full-refresh: this script recreates
RAW.SERVICE_ADDRESS_GEOCODE from scratch each run (cheap — one batch API call
for ~2,038 addresses), so it's always safe to rerun.

Assumption (documented): STATE is not present in the source data. All observed
SERVICE_CITY/SERVICE_REVENUE_AREA values are Central Texas municipalities, so
'TX' is used as the state for every geocoding request. This is recorded in the
STATE_ASSUMED column for audit, not silently assumed.

Usage:
    python scripts/geocode_ont_truck_roll_addresses.py
"""

import os
import sys
import csv
import io

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

CENSUS_BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
CENSUS_BENCHMARK = "Public_AR_Current"
STATE_ASSUMED = "TX"
GEOCODING_SOURCE = "US Census Bureau Geocoder"


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


def get_distinct_addresses(conn):
    rows = conn.execute_query(
        "SELECT DISTINCT SERVICE_ADDRESS, SERVICE_CITY FROM RAW.ONT_TRUCK_ROLL "
        "ORDER BY SERVICE_ADDRESS, SERVICE_CITY"
    )
    print(f"[*] Found {len(rows)} distinct (SERVICE_ADDRESS, SERVICE_CITY) pairs in RAW.ONT_TRUCK_ROLL.")
    return rows


def build_batch_csv(addresses):
    """Census batch format: id,street,city,state,zip  (no header row)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for i, row in enumerate(addresses):
        writer.writerow([i, row["SERVICE_ADDRESS"], row["SERVICE_CITY"], STATE_ASSUMED, ""])
    return buf.getvalue()


def call_census_batch(csv_content):
    print(f"[*] Submitting batch geocode request to Census Bureau ({CENSUS_BATCH_URL}) ...")
    files = {"addressFile": ("addresses.csv", csv_content, "text/csv")}
    data = {"benchmark": CENSUS_BENCHMARK}
    try:
        resp = requests.post(CENSUS_BATCH_URL, files=files, data=data, timeout=120)
    except requests.RequestException as e:
        print(f"[ERROR] Census batch request failed: {e}")
        sys.exit(1)
    if resp.status_code != 200:
        print(f"[ERROR] Census batch request returned HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    print(f"[OK] Received Census response ({len(resp.text)} bytes).")
    return resp.text


def parse_census_response(csv_text, addresses):
    """
    Census batch CSV columns (no header):
      ID, Input Address, Match, Match Type, Matched Address, Coordinates, TigerLineID, Side
    Coordinates field is "longitude,latitude" when Match == 'Match'.
    """
    by_id = {i: row for i, row in enumerate(addresses)}
    results = {}
    reader = csv.reader(io.StringIO(csv_text))
    for fields in reader:
        if not fields:
            continue
        rec_id = int(fields[0])
        match = fields[2] if len(fields) > 2 else ""
        matched_address = fields[4] if len(fields) > 4 else ""
        coords = fields[5] if len(fields) > 5 else ""

        if match == "Match":
            status = "SUCCESS"
        elif match == "Tie":
            status = "AMBIGUOUS"
        else:
            status = "FAILED"

        lat, lon = None, None
        if status == "SUCCESS" and coords:
            try:
                lon_str, lat_str = coords.split(",")
                lon, lat = round(float(lon_str), 4), round(float(lat_str), 4)
            except ValueError:
                status = "FAILED"  # malformed coordinates — do not silently accept

        src = by_id.get(rec_id)
        if src is None:
            continue
        results[rec_id] = {
            "SERVICE_ADDRESS": src["SERVICE_ADDRESS"],
            "SERVICE_CITY": src["SERVICE_CITY"],
            "STATE_ASSUMED": STATE_ASSUMED,
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "MATCHED_ADDRESS": matched_address or None,
            "GEOCODING_STATUS": status,
            "GEOCODING_SOURCE": GEOCODING_SOURCE,
        }

    # Any address the Census response never returned a row for at all —
    # do not silently drop it, record as FAILED with no coordinates.
    for i, src in by_id.items():
        if i not in results:
            results[i] = {
                "SERVICE_ADDRESS": src["SERVICE_ADDRESS"],
                "SERVICE_CITY": src["SERVICE_CITY"],
                "STATE_ASSUMED": STATE_ASSUMED,
                "LATITUDE": None,
                "LONGITUDE": None,
                "MATCHED_ADDRESS": None,
                "GEOCODING_STATUS": "FAILED",
                "GEOCODING_SOURCE": GEOCODING_SOURCE,
            }

    return list(results.values())


def load_to_snowflake(conn, records):
    cursor = conn.conn.cursor()
    print("[*] CREATE OR REPLACE TABLE RAW.SERVICE_ADDRESS_GEOCODE (full refresh) ...")
    cursor.execute("""
        CREATE OR REPLACE TABLE RAW.SERVICE_ADDRESS_GEOCODE (
            SERVICE_ADDRESS     VARCHAR(512) NOT NULL,
            SERVICE_CITY        VARCHAR(128) NOT NULL,
            STATE_ASSUMED       VARCHAR(2),
            LATITUDE            NUMBER(9,4),
            LONGITUDE           NUMBER(9,4),
            MATCHED_ADDRESS     VARCHAR(512),
            GEOCODING_STATUS    VARCHAR(32) NOT NULL,
            GEOCODING_SOURCE    VARCHAR(64) NOT NULL,
            GEOCODED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    insert_sql = """
        INSERT INTO RAW.SERVICE_ADDRESS_GEOCODE
            (SERVICE_ADDRESS, SERVICE_CITY, STATE_ASSUMED, LATITUDE, LONGITUDE,
             MATCHED_ADDRESS, GEOCODING_STATUS, GEOCODING_SOURCE)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows = [
        (r["SERVICE_ADDRESS"], r["SERVICE_CITY"], r["STATE_ASSUMED"], r["LATITUDE"], r["LONGITUDE"],
         r["MATCHED_ADDRESS"], r["GEOCODING_STATUS"], r["GEOCODING_SOURCE"])
        for r in records
    ]
    cursor.executemany(insert_sql, rows)
    cursor.close()
    print(f"[OK] Loaded {len(rows)} rows into RAW.SERVICE_ADDRESS_GEOCODE.")


def report(records):
    total = len(records)
    success = sum(1 for r in records if r["GEOCODING_STATUS"] == "SUCCESS")
    failed = sum(1 for r in records if r["GEOCODING_STATUS"] == "FAILED")
    ambiguous = sum(1 for r in records if r["GEOCODING_STATUS"] == "AMBIGUOUS")
    missing_coords = sum(1 for r in records if r["LATITUDE"] is None or r["LONGITUDE"] is None)

    print("\n" + "=" * 78)
    print(" GEOCODING RESULTS")
    print("=" * 78)
    print(f" Total unique addresses:      {total}")
    print(f" Successfully geocoded:       {success}")
    print(f" Failed:                      {failed}")
    print(f" Ambiguous/partial (Tie):     {ambiguous}")
    print(f" Missing coordinates:         {missing_coords}")
    print("=" * 78)

    if failed or ambiguous:
        print("\n Sample FAILED/AMBIGUOUS addresses (up to 10):")
        shown = 0
        for r in records:
            if r["GEOCODING_STATUS"] in ("FAILED", "AMBIGUOUS") and shown < 10:
                print(f"   [{r['GEOCODING_STATUS']}] {r['SERVICE_ADDRESS']}, {r['SERVICE_CITY']}")
                shown += 1
    print()


if __name__ == "__main__":
    conn = connect()
    try:
        addresses = get_distinct_addresses(conn)
        csv_content = build_batch_csv(addresses)
        census_response = call_census_batch(csv_content)
        records = parse_census_response(census_response, addresses)
        load_to_snowflake(conn, records)
        report(records)
    finally:
        conn.close_connection()
