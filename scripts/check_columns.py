#!/usr/bin/env python3
"""Check column names and copy all historical data properly."""

import sys
import os
sys.path.insert(0, os.getcwd())

from src.database.snowflake_db import SnowflakeConnection
from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, SF_AUTHENTICATOR


def main():
    conn = SnowflakeConnection(
        SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
        sf_authenticator=SF_AUTHENTICATOR
    )

    if not conn.conn:
        print("Failed to connect")
        return

    # Check COMPANY_4130_DATA columns
    print("COMPANY_4130_DATA columns:")
    r = conn.execute_query("DESCRIBE TABLE TEST_DB.PUBLIC.COMPANY_4130_DATA")
    for row in r:
        print(f"  {row['name']}")

    # Check TICKETS columns
    print("\nTICKETS columns:")
    r = conn.execute_query("DESCRIBE TABLE TEST_DB.PUBLIC.TICKETS")
    for row in r:
        print(f"  {row['name']}")

    conn.close_connection()


if __name__ == "__main__":
    main()