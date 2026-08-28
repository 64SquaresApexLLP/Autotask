#!/usr/bin/env python3
"""
Snowflake Database Setup & Data Uploader for TeamLogic AutoTask System.
Executes DDL to create tables and loads the generated dummy data into Snowflake.
Supports 'externalbrowser' SSO authentication.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, SF_AUTHENTICATOR

def run_setup(sql_file="data/dummy_data.sql"):
    """Execute SQL script against Snowflake database."""
    print("=" * 70)
    print(" Snowflake Setup & Data Upload - TeamLogic AutoTask")
    print("=" * 70)
    print(f" Account:       {SF_ACCOUNT}")
    print(f" User:          {SF_USER}")
    print(f" Authenticator: {SF_AUTHENTICATOR}")
    print(f" Role:          {SF_ROLE}")
    print(f" Warehouse:     {SF_WAREHOUSE}")
    print(f" Database:      {SF_DATABASE}")
    print(f" Schema:        {SF_SCHEMA}")
    print("=" * 70)
    print("\n[*] Initializing Snowflake connection (a browser window may open for SSO)...")

    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT,
        sf_user=SF_USER,
        sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE,
        sf_schema=SF_SCHEMA,
        sf_role=SF_ROLE,
        sf_authenticator=SF_AUTHENTICATOR
    )

    if not conn.is_connected():
        print("\n[ERROR] Failed to connect to Snowflake. Please verify your credentials and network.")
        return False

    print("[OK] Successfully connected to Snowflake!\n")

    if not os.path.exists(sql_file):
        print(f"[ERROR] SQL seed file '{sql_file}' not found.")
        conn.close_connection()
        return False

    print(f"[*] Reading SQL statements from {sql_file}...")
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split SQL script into individual statements
    statements = [s.strip() for s in sql_content.split(";\n") if s.strip()]
    total = len(statements)
    print(f"[*] Executing {total} SQL statements...")

    cursor = conn.conn.cursor()
    success_count = 0
    error_count = 0

    for i, stmt in enumerate(statements, 1):
        if not stmt or stmt.startswith("--"):
            continue
        try:
            cursor.execute(stmt)
            success_count += 1
            if i % 50 == 0 or i == total:
                print(f"  -> Progress: {i}/{total} statements executed...")
        except Exception as e:
            error_count += 1
            print(f"\n[WARNING] Error on statement #{i}: {e}")
            print(f"Statement preview: {stmt[:100]}...\n")

    cursor.close()
    conn.close_connection()

    print("\n" + "=" * 70)
    print(f" [COMPLETE] Setup finished! Successful: {success_count}, Errors: {error_count}")
    print("=" * 70)
    return error_count == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload dummy data & schema to Snowflake")
    parser.add_argument("--sql-file", default="data/dummy_data.sql", help="Path to SQL seed file")
    args = parser.parse_args()

    run_setup(sql_file=args.sql_file)
