#!/usr/bin/env python3
"""
Import CTTC Telecom Ticket Tracker into AutoTask Snowflake Database.
Run from project root: .venv\Scripts\python.exe scripts/import_cttc_tickets.py
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database.snowflake_db import SnowflakeConnection
from config import SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE, SF_AUTHENTICATOR

EXCEL_PATH = "data/CTTC_Support_Ticket_Tracker_1.xlsx"


def read_ticket_log():
    """Parse the Ticket Log sheet with proper headers."""
    df = pd.read_excel(EXCEL_PATH, sheet_name="Ticket Log", skiprows=3)
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Filter valid tickets (has API ticket #)
    df = df[df['API ticket #'].notna() & (df['API ticket #'] != '')]
    df = df[df['API ticket #'].astype(str).str.strip() != 'nan']

    print(f"Parsed {len(df)} valid tickets")
    return df


def map_category_to_autotask(category: str) -> dict:
    """Map CTTC categories to AutoTask classification values."""
    mapping = {
        'Internet not working':      {'issuetype': '4', 'subissuetype': '64', 'tickettype': '2', 'ticketcategory': '3'},
        'Internet going on/off':     {'issuetype': '4', 'subissuetype': '64', 'tickettype': '2', 'ticketcategory': '3'},
        'Internet slow':             {'issuetype': '4', 'subissuetype': '64', 'tickettype': '2', 'ticketcategory': '3'},
        'Wifi ext not working':      {'issuetype': '4', 'subissuetype': '21', 'tickettype': '2', 'ticketcategory': '3'},
        'Email trouble':             {'issuetype': '15', 'subissuetype': '102', 'tickettype': '2', 'ticketcategory': '3'},
        'Need help setting up device': {'issuetype': '4', 'subissuetype': '14', 'tickettype': '2', 'ticketcategory': '3'},
        'Device buffering':          {'issuetype': '4', 'subissuetype': '48', 'tickettype': '2', 'ticketcategory': '3'},
    }
    return mapping.get(category, {'issuetype': '17', 'subissuetype': '25', 'tickettype': '2', 'ticketcategory': '3'})


def map_priority(priority: str) -> str:
    """Map recommended priority to AutoTask priority values."""
    pmap = {'Critical': '4', 'High': '1', 'Medium': '2', 'Low': '3'}
    return pmap.get(str(priority).strip(), '2')


def map_status(status: str) -> str:
    """Map CTTC status to AutoTask status values."""
    smap = {'Resolved': '52', 'Escalated': '24', 'Logged': '1', 'Open': '1'}
    return smap.get(str(status).strip(), '1')


def generate_ticket_number(api_ticket: str) -> str:
    """Convert CTTC API ticket # to AutoTask TYYYYMMDD.NNNN format."""
    # Use date from ticket or current date
    today = datetime.now().strftime("%Y%m%d")
    # Extract last 4 digits of API ticket as sequence
    seq = str(api_ticket)[-4:].zfill(4)
    return f"T{today}.{seq}"


def import_to_snowflake(df: pd.DataFrame, conn: SnowflakeConnection):
    """Insert tickets into Snowflake TICKETS table."""

    inserted = 0
    errors = 0

    for _, row in df.iterrows():
        try:
            api_ticket = str(row['API ticket #']).strip()
            ticket_number = generate_ticket_number(api_ticket)

            # Get classification mapping
            cat_map = map_category_to_autotask(row['Category'])
            priority_val = map_priority(row['Recommended\npriority'])
            status_val = map_status(row['Status'])

            # Build insert data
            ticket_data = {
                'TICKETNUMBER': ticket_number,
                'TITLE': f"[{row['Town']}] {row['Category']} - {row['Customer']}",
                'DESCRIPTION': f"Customer: {row['Customer']} ({row['Town']}). Issue: {row['Category']}. Notes: {row.get('Notes', '')}",
                'TICKETTYPE': cat_map['tickettype'],
                'TICKETCATEGORY': cat_map['ticketcategory'],
                'ISSUETYPE': cat_map['issuetype'],
                'SUBISSUETYPE': cat_map['subissuetype'],
                'DUEDATETIME': datetime.now().strftime("%Y-%m-%d"),
                'PRIORITY': priority_val,
                'STATUS': status_val,
                'RESOLUTION': str(row.get('Resolution / outcome', '')) if pd.notna(row.get('Resolution / outcome')) else '',
                'TECHNICIANEMAIL': '',  # Will be assigned by assignment agent
                'USEREMAIL': 'cttc_customer@cttc.com',
                'USERID': f"CTTC-{row['Town']}",
                'PHONENUMBER': ''
            }

            # Check if exists
            check_query = "SELECT COUNT(*) as cnt FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER = %s"
            result = conn.execute_query(check_query, (ticket_number,))
            if result and result[0]['CNT'] > 0:
                print(f"  Skipping existing: {ticket_number}")
                continue

            # Insert
            cols = list(ticket_data.keys())
            vals = [ticket_data[c] for c in cols]
            placeholders = ", ".join(["%s"] * len(cols))
            cols_str = ", ".join(cols)

            insert_query = f"INSERT INTO TEST_DB.PUBLIC.TICKETS ({cols_str}) VALUES ({placeholders})"
            conn.execute_query(insert_query, tuple(vals))
            inserted += 1

            if inserted % 20 == 0:
                print(f"  Inserted {inserted} tickets...")

        except Exception as e:
            errors += 1
            print(f"  Error inserting {row.get('API ticket #', 'unknown')}: {e}")

    print(f"\nImport complete: {inserted} inserted, {errors} errors")
    return inserted, errors


def main():
    print("=" * 60)
    print("CTTC Telecom Ticket Import to AutoTask")
    print("=" * 60)

    # 1. Read Excel
    print("\nReading Excel file...")
    df = read_ticket_log()
    print(f"   Categories: {df['Category'].unique().tolist()}")
    print(f"   Statuses: {df['Status'].unique().tolist()}")
    print(f"   Date range: {df['Date reported'].min()} to {df['Date reported'].max()}")

    # 2. Connect to Snowflake
    print("\nConnecting to Snowflake (SSO - browser will open)...")
    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT,
        sf_user=SF_USER,
        sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE,
        sf_schema=SF_SCHEMA,
        sf_role=SF_ROLE,
        sf_authenticator=SF_AUTHENTICATOR
    )

    if not conn.conn:
        print("Failed to connect to Snowflake")
        return

    print("Connected to Snowflake")

    # 3. Import tickets
    print("\nImporting tickets to Snowflake...")
    import_to_snowflake(df, conn)

    # 4. Verify
    print("\nVerifying import...")
    count_query = "SELECT COUNT(*) as total FROM TEST_DB.PUBLIC.TICKETS WHERE TICKETNUMBER LIKE 'T%'"
    result = conn.execute_query(count_query)
    print(f"   Total T-format tickets in DB: {result[0]['TOTAL'] if result else 0}")

    conn.close_connection()
    print("\nDone!")


if __name__ == "__main__":
    main()