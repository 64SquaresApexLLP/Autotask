#!/usr/bin/env python3
"""Check the 6 'Other' format tickets."""

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

    # Check the 'Other' 6 tickets (not T-format, not 10013-format)
    other = conn.execute_query("""
        SELECT TICKETNUMBER, TITLE, STATUS, PRIORITY, ISSUETYPE 
        FROM TEST_DB.PUBLIC.TICKETS 
        WHERE TICKETNUMBER NOT LIKE 'T%' 
        AND TICKETNUMBER NOT LIKE '10013%'
        ORDER BY TICKETNUMBER
    """)
    print("Other format tickets (6 total):")
    for r in other:
        print(f"  {r['TICKETNUMBER']} | {r['TITLE'][:60]} | Status:{r['STATUS']} | Priority:{r['PRIORITY']} | Type:{r['ISSUETYPE']}")

    conn.close_connection()


if __name__ == "__main__":
    main()