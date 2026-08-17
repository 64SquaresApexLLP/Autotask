#!/usr/bin/env python3
"""Check for old CTTC tickets in both TICKETS and CLOSED_TICKETS tables."""

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
    print("CHECKING FOR OLD CTTC TICKETS (10013xxx format)")
    print("=" * 60)

    # 1. Check TICKETS table for 10013% pattern
    print("\n1. TICKETS table - 10013xxx pattern:")
    t1 = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE '10013%'")
    print(f"   Count: {t1[0]['CNT'] if t1 else 0}")

    if t1 and t1[0]['CNT'] > 0:
        sample = conn.execute_query("SELECT TICKETNUMBER, TITLE, STATUS, PRIORITY, ISSUETYPE, DUEDATETIME FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE '10013%' LIMIT 10")
        for r in sample:
            print(f"   {r['TICKETNUMBER']} | {r['TITLE'][:50]} | Status:{r['STATUS']} | Priority:{r['PRIORITY']} | Type:{r['ISSUETYPE']}")

    # 2. Check CLOSED_TICKETS table for 10013% pattern
    print("\n2. CLOSED_TICKETS table - 10013xxx pattern:")
    try:
        t2 = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.CLOSED_TICKETS WHERE TICKETNUMBER LIKE '10013%'")
        print(f"   Count: {t2[0]['CNT'] if t2 else 0}")

        if t2 and t2[0]['CNT'] > 0:
            sample = conn.execute_query("SELECT TICKETNUMBER, TITLE, STATUS, PRIORITY, ISSUETYPE, CLOSED_AT FROM TEST_DB.PUBLIC.CLOSED_TICKETS WHERE TICKETNUMBER LIKE '10013%' LIMIT 10")
            for r in sample:
                print(f"   {r['TICKETNUMBER']} | {r['TITLE'][:50]} | Status:{r['STATUS']} | Closed:{r['CLOSED_AT']}")
    except Exception as e:
        print(f"   CLOSED_TICKETS table not accessible or doesn't exist: {e}")

    # 3. Check all tables for any 10013 pattern
    print("\n3. Search across both tables for 10013 pattern:")
    try:
        query = """
        SELECT 'TICKETS' as table_name, TICKETNUMBER, TITLE, STATUS FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE '10013%'
        UNION ALL
        SELECT 'CLOSED_TICKETS' as table_name, TICKETNUMBER, TITLE, STATUS FROM TEST_DB.PUBLIC.CLOSED_TICKETS WHERE TICKETNUMBER LIKE '10013%'
        ORDER BY TICKETNUMBER
        """
        all_old = conn.execute_query(query)
        print(f"   Total old tickets found: {len(all_old)}")
        for r in all_old[:20]:
            print(f"   [{r['TABLE_NAME']}] {r['TICKETNUMBER']} | {r['TITLE'][:50]} | Status:{r['STATUS']}")
    except Exception as e:
        print(f"   Cross-table search failed: {e}")

    # 4. Check COMPANY_4130_DATA for reference data
    print("\n4. COMPANY_4130_DATA table (reference/historical):")
    try:
        c4 = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.COMPANY_4130_DATA WHERE TICKETNUMBER LIKE '10013%'")
        print(f"   10013xxx count: {c4[0]['CNT'] if c4 else 0}")
        
        total_c4 = conn.execute_query("SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.COMPANY_4130_DATA")
        print(f"   Total rows in COMPANY_4130_DATA: {total_c4[0]['CNT'] if total_c4 else 0}")
        
        sample_c4 = conn.execute_query("SELECT TICKETNUMBER, TITLE, ISSUETYPE, STATUS FROM TEST_DB.PUBLIC.COMPANY_4130_DATA WHERE TICKETNUMBER LIKE '10013%' LIMIT 5")
        for r in sample_c4:
            print(f"   {r['TICKETNUMBER']} | {r['TITLE'][:50]} | Type:{r['ISSUETYPE']} | Status:{r['STATUS']}")
    except Exception as e:
        print(f"   COMPANY_4130_DATA check failed: {e}")

    # 5. Show all distinct ticket number prefixes
    print("\n5. All ticket number prefixes in TICKETS table:")
    prefixes = conn.execute_query("""
        SELECT 
            CASE 
                WHEN TICKETNUMBER LIKE 'T%' THEN 'T-format (AutoTask)'
                WHEN TICKETNUMBER LIKE '10013%' THEN '10013xxx (CTTC)'
                ELSE 'Other'
            END as prefix_type,
            COUNT(*) as cnt
        FROM TEST_DB.PUBLIC.TICKETS
        GROUP BY prefix_type
        ORDER BY cnt DESC
    """)
    for r in prefixes:
        print(f"   {r['PREFIX_TYPE']}: {r['CNT']}")

    conn.close_connection()


if __name__ == "__main__":
    main()