#!/usr/bin/env python3
"""Copy ALL historical data from COMPANY_4130_DATA to TICKETS with correct column mapping."""

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

    print("=" * 60)
    print("COPYING ALL HISTORICAL DATA (10,000 tickets)")
    print("=" * 60)

    # First, clear any remaining non-historical tickets
    print("\n1. Cleaning TICKETS table...")
    conn.execute_query("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'T20260817%'")
    conn.execute_query("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'CAT%'")
    conn.execute_query("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'T20260816%'")
    print("   Cleaned.")

    # Map COMPANY_4130_DATA columns to TICKETS columns
    copy_query = """
    INSERT INTO TEST_DB.PUBLIC.TICKETS (
        TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY,
        ISSUETYPE, SUBISSUETYPE, DUEDATETIME, PRIORITY, STATUS,
        RESOLUTION, TECHNICIANEMAIL, USEREMAIL, USERID, PHONENUMBER
    )
    SELECT 
        TICKETNUMBER,
        TITLE,
        DESCRIPTION,
        TICKETTYPE,
        TICKETCATEGORY,
        ISSUETYPE,
        SUBISSUETYPE,
        DUEDATETIME,
        PRIORITY,
        STATUS,
        RESOLUTION,
        '' as TECHNICIANEMAIL,
        '' as USEREMAIL,
        '' as USERID,
        '' as PHONENUMBER
    FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
    WHERE TICKETNUMBER NOT IN (SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.TICKETS)
    """

    print("\n2. Copying all 10,000 historical tickets...")
    print("   This may take a minute...")
    try:
        conn.execute_query(copy_query)
        print("   Copy complete!")
    except Exception as e:
        print(f"   Error: {e}")

    # Verify
    print("\n3. Verification:")
    r = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS")
    print(f"   Total tickets in TICKETS table: {r[0]['CNT']}")

    # Show sample
    r = conn.execute_query("""
        SELECT TICKETNUMBER, TITLE, ISSUETYPE, STATUS, PRIORITY 
        FROM TEST_DB.PUBLIC.TICKETS 
        ORDER BY TICKETNUMBER DESC 
        LIMIT 10
    """)
    print("\n   Latest 10 tickets:")
    for row in r:
        title = row['TITLE'][:60] if row['TITLE'] else 'N/A'
        print(f"     {row['TICKETNUMBER']} | {title} | Type:{row['ISSUETYPE']} | Status:{row['STATUS']} | Priority:{row['PRIORITY']}")

    # Count by issue type
    r = conn.execute_query("""
        SELECT ISSUETYPE, COUNT(*) as cnt 
        FROM TEST_DB.PUBLIC.TICKETS 
        GROUP BY ISSUETYPE 
        ORDER BY cnt DESC
    """)
    print("\n   All Issue Types:")
    for row in r:
        print(f"     {row['ISSUETYPE']}: {row['CNT']} tickets")

    conn.close_connection()
    print("\n" + "=" * 60)
    print("COMPLETE: Historical data restored to TICKETS table")
    print("=" * 60)


if __name__ == "__main__":
    main()