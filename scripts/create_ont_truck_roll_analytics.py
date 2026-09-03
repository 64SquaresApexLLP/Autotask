#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 2: create the ANALYTICS view layer on top of RAW.ONT_TRUCK_ROLL.

Applies ont_truck_roll_data/ANALYTICS_ONT_TRUCK_ROLL_DDL.sql — all objects are
CREATE OR REPLACE VIEW, read-only over RAW.ONT_TRUCK_ROLL. This script never
writes to RAW.

Usage:
    python scripts/create_ont_truck_roll_analytics.py
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DDL_FILE = os.path.join(PROJECT_ROOT, "ont_truck_roll_data", "ANALYTICS_ONT_TRUCK_ROLL_DDL.sql")

VIEWS = [
    "VW_ONT_TRUCK_ROLL_ENRICHED",
    "VW_TRUCK_ROLL_KPI_SUMMARY",
    "VW_TRUCK_ROLL_BY_SOLUTION",
    "VW_TRUCK_ROLL_MONTHLY_TREND",
    "VW_TRUCK_ROLL_BY_SERVICE_AREA",
    "VW_TRUCK_ROLL_BY_TECHNICIAN",
    "VW_TRUCK_ROLL_BY_ADDRESS",
    "VW_TRUCK_ROLL_DATA_QUALITY_ISSUES",
]


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

    # Strip full-line comments first (they can legally contain ';'), then split.
    import re
    code = re.sub(r"--[^\n]*", "", sql)  # strip full-line AND trailing inline comments
    statements = [s.strip() for s in code.split(";") if s.strip()]

    cursor = conn.conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    cursor.close()
    print(f"[OK] DDL applied ({len(statements)} statements, {len(VIEWS)} views).")


def smoke_test(conn):
    print("\n" + "=" * 78)
    print(" SMOKE TEST — one row from each view")
    print("=" * 78)
    for view in VIEWS:
        rows = conn.execute_query(f"SELECT * FROM ANALYTICS.{view} LIMIT 1")
        count = conn.execute_query(f"SELECT COUNT(*) AS N FROM ANALYTICS.{view}")[0]["N"]
        print(f"\n{view}  ({count} row(s))")
        if rows:
            for k, v in rows[0].items():
                print(f"   {k}: {v}")
        else:
            print("   (empty)")
    print("\n" + "=" * 78)


if __name__ == "__main__":
    conn = connect()
    try:
        run_ddl(conn)
        smoke_test(conn)
    finally:
        conn.close_connection()
