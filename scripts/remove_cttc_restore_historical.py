#!/usr/bin/env python3
"""Remove CTTC tickets and restore historical data to TICKETS table."""

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

    print("=" * 60)
    print("REMOVING CTTC DATA & RESTORING HISTORICAL DATA")
    print("=" * 60)

    # 1. DELETE all CTTC tickets (T20260817 format)
    print("\n1. Deleting CTTC tickets (T20260817%)...")
    result = conn.execute_query("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'T20260817%'")
    print("   Done.")

    # 2. DELETE the 6 CAT playbooks
    print("\n2. Deleting CAT playbooks...")
    conn.execute_query("DELETE FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'CAT%'")
    print("   Done.")

    # 3. COPY historical data from COMPANY_4130_DATA to TICKETS
    print("\n3. Copying historical data from COMPANY_4130_DATA to TICKETS...")
    copy_query = """
    INSERT INTO TEST_DB.PUBLIC.TICKETS (
        TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY, 
        ISSUETYPE, SUBISSUETYPE, DUEDATETIME, PRIORITY, STATUS, 
        RESOLUTION, TECHNICIANEMAIL, USEREMAIL, USERID, PHONENUMBER
    )
    SELECT 
        TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY, 
        ISSUETYPE, SUBISSUETYPE, DUEDATETIME, PRIORITY, STATUS, 
        RESOLUTION, TECHNICIANEMAIL, USEREMAIL, USERID, PHONENUMBER
    FROM TEST_DB.PUBLIC.COMPANY_4130_DATA
    WHERE TICKETNUMBER NOT IN (SELECT TICKETNUMBER FROM TEST_DB.PUBLIC.TICKETS)
    """
    conn.execute_query(copy_query)
    print("   Done copying historical data.")

    # 4. Verify
    print("\n4. Verification:")
    r = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS")
    print(f"   Total tickets in TICKETS table now: {r[0]['CNT']}")

    # Show sample of restored data
    r = conn.execute_query("""
        SELECT TICKETNUMBER, TITLE, ISSUETYPE, STATUS, PRIORITY 
        FROM TEST_DB.PUBLIC.TICKETS 
        ORDER BY TICKETNUMBER DESC 
        LIMIT 15
    """)
    print("\n   Latest 15 tickets (should be historical data):")
    for row in r:
        title = row['TITLE'][:60] if row['TITLE'] else 'N/A'
        print(f"     {row['TICKETNUMBER']} | {title} | Type:{row['ISSUETYPE']} | Status:{row['STATUS']} | Priority:{row['PRIORITY']}")

    # Count by issue type
    r = conn.execute_query("""
        SELECT ISSUETYPE, COUNT(*) as cnt 
        FROM TEST_DB.PUBLIC.TICKETS 
        GROUP BY ISSUETYPE 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    print("\n   Top 10 Issue Types:")
    for row in r:
        print(f"     {row['ISSUETYPE']}: {row['CNT']} tickets")

    conn.close_connection()
    print("\n" + "=" * 60)
    print("COMPLETE: CTTC data removed, historical data restored")
    print("=" * 60)


if __name__ == "__main__":
    main()