#!/usr/bin/env python3
"""Check COMPANY_4130_DATA for historical Outlook/VPN/Screen filtering tickets."""

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
    print("CHECKING COMPANY_4130_DATA FOR HISTORICAL DATA")
    print("=" * 60)

    # Search for specific terms
    terms = ['outlook', 'vpn', 'screen', 'filter', 'password', 'printer', 'email']
    
    for term in terms:
        query = f"""
        SELECT COUNT(*) as cnt 
        FROM TEST_DB.PUBLIC.COMPANY_4130_DATA 
        WHERE TITLE ILIKE '%{term}%' OR DESCRIPTION ILIKE '%{term}%'
        """
        r = conn.execute_query(query)
        count = r[0]['CNT'] if r else 0
        if count > 0:
            print(f"\n{term.upper()}: {count} tickets")
            # Get samples
            sample_query = f"""
            SELECT TICKETNUMBER, TITLE, ISSUETYPE, STATUS 
            FROM TEST_DB.PUBLIC.COMPANY_4130_DATA 
            WHERE TITLE ILIKE '%{term}%' OR DESCRIPTION ILIKE '%{term}%'
            LIMIT 5
            """
            samples = conn.execute_query(sample_query)
            for row in samples:
                print(f"  {row['TICKETNUMBER']} | {row['TITLE'][:70]} | Type:{row['ISSUETYPE']} | Status:{row['STATUS']}")

    # Check total unique tickets
    r = conn.execute_query("SELECT COUNT(DISTINCT TICKETNUMBER) as cnt FROM TEST_DB.PUBLIC.COMPANY_4130_DATA")
    print(f"\n\nUnique ticket numbers in COMPANY_4130_DATA: {r[0]['CNT']}")

    # Check current TICKETS table for non-standard formats
    r = conn.execute_query("""
        SELECT TICKETNUMBER, TITLE, ISSUETYPE, STATUS 
        FROM TEST_DB.PUBLIC.TICKETS 
        WHERE TICKETNUMBER NOT LIKE 'T%' 
        AND TICKETNUMBER NOT LIKE '10013%' 
        AND TICKETNUMBER NOT LIKE 'CAT%'
        ORDER BY TICKETNUMBER
    """)
    print(f"\nOther tickets currently in TICKETS table: {len(r)}")
    for row in r:
        print(f"  {row['TICKETNUMBER']} | {row['TITLE'][:70]} | Type:{row['ISSUETYPE']} | Status:{row['STATUS']}")

    # Check if there are any tickets with Outlook/VPN in TICKETS table currently
    for term in ['outlook', 'vpn', 'screen']:
        r = conn.execute_query(f"""
            SELECT COUNT(*) as cnt 
            FROM TEST_DB.PUBLIC.TICKETS 
            WHERE TITLE ILIKE '%{term}%' OR DESCRIPTION ILIKE '%{term}%'
        """)
        print(f"\n{term.upper()} in current TICKETS table: {r[0]['CNT']}")

    conn.close_connection()


if __name__ == "__main__":
    main()