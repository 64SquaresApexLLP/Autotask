#!/usr/bin/env python3
"""Check current tickets in Snowflake TICKETS table."""

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
        print("Failed to connect to Snowflake")
        return

    # Total count
    total = conn.execute_query('SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS')
    print(f"Total tickets: {total[0]['CNT'] if total else 0}")

    # By status
    status = conn.execute_query('SELECT STATUS, COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS GROUP BY STATUS ORDER BY cnt DESC')
    print("\nBy Status:")
    for r in status:
        print(f"  {r['STATUS']}: {r['CNT']}")

    # By priority
    priority = conn.execute_query('SELECT PRIORITY, COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS GROUP BY PRIORITY ORDER BY cnt DESC')
    print("\nBy Priority:")
    for r in priority:
        print(f"  {r['PRIORITY']}: {r['CNT']}")

    # By issue type
    itype = conn.execute_query('SELECT ISSUETYPE, COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS GROUP BY ISSUETYPE ORDER BY cnt DESC')
    print("\nBy Issue Type:")
    for r in itype:
        print(f"  {r['ISSUETYPE']}: {r['CNT']}")

    # Sample tickets
    sample = conn.execute_query('SELECT TICKETNUMBER, TITLE, STATUS, PRIORITY, ISSUETYPE, TECHNICIANEMAIL, DUEDATETIME FROM TEST_DB.PUBLIC.TICKETS ORDER BY TICKETNUMBER DESC LIMIT 10')
    print("\nLatest 10 tickets:")
    for r in sample:
        title = r['TITLE'][:50] + "..." if r['TITLE'] and len(r['TITLE']) > 50 else r['TITLE']
        print(f"  {r['TICKETNUMBER']} | {title} | Status:{r['STATUS']} | Priority:{r['PRIORITY']} | Type:{r['ISSUETYPE']} | Tech:{r['TECHNICIANEMAIL']}")

    # T-format vs CTTC format
    t_format = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'T%'")
    cttc_format = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE '10013%'")
    print(f"\nT-format (AutoTask): {t_format[0]['CNT'] if t_format else 0}")
    print(f"CTTC-format (10013xxx): {cttc_format[0]['CNT'] if cttc_format else 0}")

    conn.close_connection()


if __name__ == "__main__":
    main()