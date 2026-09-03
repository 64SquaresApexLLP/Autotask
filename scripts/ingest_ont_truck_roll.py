#!/usr/bin/env python3
"""
ONT Truck Roll — Phase 1 ingestion: CSV -> Snowflake stage -> COPY INTO RAW.ONT_TRUCK_ROLL.

Phase 1 scope ONLY: load + validate the raw source data. No dashboard, weather,
Cortex, or ontology work happens here (see ont_truck_roll_data/README.md).

Usage:
    python scripts/export_ont_truck_roll_csv.py   # regenerate the CSV (optional,
                                                    # this script will do it too
                                                    # if the CSV is missing)
    python scripts/ingest_ont_truck_roll.py        # load + validate
    python scripts/ingest_ont_truck_roll.py --validate-only   # skip load, just
                                                                # re-run checks
"""

import os
import sys
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                     SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                     SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DDL_FILE = os.path.join(PROJECT_ROOT, "ont_truck_roll_data", "RAW_ONT_TRUCK_ROLL_DDL.sql")
CSV_FILE = os.path.join(PROJECT_ROOT, "data", "ont_truck_roll", "ont_truck_roll.csv")
CSV_FILE_URI = "file://" + CSV_FILE.replace("\\", "/")

STAGE = "RAW.ONT_TRUCK_ROLL_STAGE"
FILE_FORMAT = "RAW.CSV_ONT_TRUCK_ROLL_FORMAT"
TABLE = "RAW.ONT_TRUCK_ROLL"

BASELINE = {
    "total": 3040,
    "Replaced Ont": 1694,
    "Replaced Wall Wart": 1214,
    "Replaced Controller": 132,
    "unique_addresses": 2038,
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


def run_ddl(conn):
    if not os.path.exists(DDL_FILE):
        print(f"[ERROR] DDL file not found: {DDL_FILE}")
        sys.exit(1)
    print(f"[*] Applying DDL from {DDL_FILE} ...")
    with open(DDL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    # Strip full-line comments FIRST (a comment can legally contain a ';'),
    # then split the remaining SQL into statements. The ingestion itself
    # (PUT/COPY) is executed explicitly below, not from this file.
    import re
    code = re.sub(r"--[^\n]*", "", sql)  # strip full-line AND trailing inline comments
    statements = [s.strip() for s in code.split(";") if s.strip()]

    cursor = conn.conn.cursor()
    for stmt in statements:
        cursor.execute(stmt)
    cursor.close()
    print(f"[OK] DDL applied ({len(statements)} statements).")


def load_csv(conn):
    if not os.path.exists(CSV_FILE):
        print(f"[*] {CSV_FILE} not found — generating it first.")
        from export_ont_truck_roll_csv import export
        export()

    cursor = conn.conn.cursor()

    print(f"[*] PUT {CSV_FILE_URI} -> @{STAGE}")
    put_sql = f"PUT '{CSV_FILE_URI}' @{STAGE} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    for row in cursor.execute(put_sql):
        print("   ", row)

    print(f"[*] TRUNCATE TABLE {TABLE} (idempotent reload — RAW is a full refresh, not append)")
    cursor.execute(f"TRUNCATE TABLE {TABLE}")

    print(f"[*] COPY INTO {TABLE} ...")
    copy_sql = f"""
        COPY INTO {TABLE}
            (ACCOUNT, ACCOUNT_NUMBER, ENTERED_DATE, SOLUTION_DATE, SOLUTION_ENTRY_USER,
             ORDER_NUMBER, PROBLEM, SOLUTION, SERVICE_ADDRESS, SERVICE_CITY,
             SERVICE_REVENUE_AREA, ORDER_STATUS, SOURCE_FILE_NAME)
        FROM (
            SELECT
                $1, $2,
                TO_TIMESTAMP_NTZ($3, 'MM/DD/YYYY HH12:MI AM'),
                TO_TIMESTAMP_NTZ($4, 'MM/DD/YYYY HH12:MI AM'),
                $5, $6, $7, $8, $9, $10, $11, $12,
                'ont_truck_roll.csv'
            FROM @{STAGE}
        )
        FILE_FORMAT = (FORMAT_NAME = {FILE_FORMAT})
        ON_ERROR = 'ABORT_STATEMENT'
    """
    result = cursor.execute(copy_sql).fetchall()
    cols = [d[0] for d in cursor.description]
    for row in result:
        print("   ", dict(zip(cols, row)))
    cursor.close()
    print("[OK] COPY INTO complete.")


def validate(conn):
    print("\n" + "=" * 78)
    print(" VALIDATION")
    print("=" * 78)

    def q(sql):
        return conn.execute_query(sql)

    total = q(f"SELECT COUNT(*) AS N FROM {TABLE}")[0]["N"]
    print(f"A. Total row count: {total}")

    dates = q(f"SELECT MIN(ENTERED_DATE) AS MIN_D, MAX(ENTERED_DATE) AS MAX_D FROM {TABLE}")[0]
    print(f"B. Entered Date range: {dates['MIN_D']}  to  {dates['MAX_D']}")

    solutions = q(f"SELECT SOLUTION, COUNT(*) AS N FROM {TABLE} GROUP BY SOLUTION ORDER BY N DESC")
    print("C/D. Distinct Solution values and counts:")
    solution_counts = {}
    for r in solutions:
        print(f"     {r['SOLUTION']!r}: {r['N']}")
        solution_counts[r["SOLUTION"]] = r["N"]

    addr = q(f"SELECT COUNT(DISTINCT SERVICE_ADDRESS) AS N FROM {TABLE}")[0]["N"]
    print(f"E. Distinct Service Address values: {addr}")

    dupes = q(f"""
        SELECT ORDER_NUMBER, COUNT(*) AS N
        FROM {TABLE}
        GROUP BY ORDER_NUMBER
        HAVING COUNT(*) > 1
        ORDER BY N DESC
    """)
    print(f"F. Duplicate ORDER_NUMBER groups: {len(dupes)}")
    for r in dupes:
        rows = q(f"SELECT * FROM {TABLE} WHERE ORDER_NUMBER = '{r['ORDER_NUMBER']}'")
        print(f"     ORDER_NUMBER={r['ORDER_NUMBER']} appears {r['N']}x")
        for row in rows:
            print(f"       ACCOUNT={row['ACCOUNT']!r} ACCOUNT_NUMBER={row['ACCOUNT_NUMBER']!r} "
                  f"ENTERED_DATE={row['ENTERED_DATE']}")

    print("G. NULLs in important fields:")
    for col in ["ACCOUNT", "ACCOUNT_NUMBER", "ENTERED_DATE", "SOLUTION_DATE",
                "ORDER_NUMBER", "SOLUTION", "SERVICE_ADDRESS"]:
        n = q(f"SELECT COUNT(*) AS N FROM {TABLE} WHERE {col} IS NULL")[0]["N"]
        print(f"     {col}: {n} NULL(s)")

    exact_dupes = q(f"""
        SELECT COUNT(*) AS N FROM (
            SELECT ACCOUNT, ACCOUNT_NUMBER, ENTERED_DATE, SOLUTION_DATE, ORDER_NUMBER,
                   PROBLEM, SOLUTION, SERVICE_ADDRESS, COUNT(*) AS C
            FROM {TABLE}
            GROUP BY 1,2,3,4,5,6,7,8
            HAVING COUNT(*) > 1
        )
    """)[0]["N"]
    print(f"H. Fully-duplicate rows (all key fields identical): {exact_dupes}")

    bad_dates = q(f"""
        SELECT COUNT(*) AS N FROM {TABLE}
        WHERE ENTERED_DATE IS NULL OR SOLUTION_DATE IS NULL
           OR SOLUTION_DATE < ENTERED_DATE
    """)[0]["N"]
    print(f"H. Rows with missing/inverted dates (Solution before Entered): {bad_dates}")

    print("\n" + "=" * 78)
    print(" COMPARISON AGAINST CLIENT BASELINE")
    print("=" * 78)
    checks = [
        ("Total truck rolls", total, BASELINE["total"]),
        ("ONT replaced (Replaced Ont)", solution_counts.get("Replaced Ont", 0), BASELINE["Replaced Ont"]),
        ("Wall Wart replaced (Replaced Wall Wart)", solution_counts.get("Replaced Wall Wart", 0), BASELINE["Replaced Wall Wart"]),
        ("Controller replaced (Replaced Controller)", solution_counts.get("Replaced Controller", 0), BASELINE["Replaced Controller"]),
        ("Unique service addresses", addr, BASELINE["unique_addresses"]),
    ]
    all_match = True
    for label, actual, expected in checks:
        match = "MATCH" if actual == expected else "DIFFERS"
        if actual != expected:
            all_match = False
        print(f"  {label:45s} actual={actual:<6} expected={expected:<6} [{match}]")
    print("=" * 78)
    print("ALL BASELINE FIGURES MATCH." if all_match else "SOME FIGURES DIFFER — see report above.")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load ONT Truck Roll CSV into Snowflake RAW.ONT_TRUCK_ROLL and validate.")
    parser.add_argument("--validate-only", action="store_true", help="Skip DDL/load, just run validation queries against the existing table.")
    args = parser.parse_args()

    conn = connect()
    try:
        if not args.validate_only:
            run_ddl(conn)
            load_csv(conn)
        validate(conn)
    finally:
        conn.close_connection()
