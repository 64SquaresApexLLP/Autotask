#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 3: create the weather enrichment layer objects.

Applies ont_truck_roll_data/WEATHER_ENRICHMENT_DDL.sql:
  - RAW.SERVICE_ADDRESS_GEOCODE      (created if missing, not populated here)
  - RAW.WEATHER_OBSERVATIONS_OPENMETEO (created if missing, not populated here)
  - ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED (CREATE OR REPLACE VIEW)

Does not touch RAW.ONT_TRUCK_ROLL or ANALYTICS.VW_ONT_TRUCK_ROLL_ENRICHED.

Usage:
    python scripts/create_weather_enrichment.py
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DDL_FILE = os.path.join(PROJECT_ROOT, "ont_truck_roll_data", "WEATHER_ENRICHMENT_DDL.sql")


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
    if not os.path.exists(DDL_FILE):
        print(f"[ERROR] DDL file not found: {DDL_FILE}")
        sys.exit(1)
    print(f"[*] Applying DDL from {DDL_FILE} ...")
    with open(DDL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    import re
    code = re.sub(r"--[^\n]*", "", sql)  # strip full-line AND trailing inline comments
    statements = [s.strip() for s in code.split(";") if s.strip()]

    cursor = conn.conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    cursor.close()
    print(f"[OK] DDL applied ({len(statements)} statements).")


if __name__ == "__main__":
    conn = connect()
    try:
        run_ddl(conn)
        print("\nObjects ready:")
        print("  RAW.SERVICE_ADDRESS_GEOCODE (empty until scripts/geocode_ont_truck_roll_addresses.py runs)")
        print("  RAW.WEATHER_OBSERVATIONS_OPENMETEO (empty until scripts/fetch_open_meteo_weather.py runs)")
        print("  ANALYTICS.VW_ONT_TRUCK_ROLL_WEATHER_ENRICHED (will show all NO_GEOCODE until the above run)")
    finally:
        conn.close_connection()
