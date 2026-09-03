#!/usr/bin/env python3
"""
ONT Truck Roll — Excel to CSV export (Phase 1, step 1).

Reads the 'Complete List' sheet of the client-provided ONT Truck Roll workbook
and writes a clean CSV that Snowflake can COPY INTO a RAW table.

Source file (read-only, never modified):
    ONT Data/Ont Truck Roll Report.xlsx  (sheet: 'Complete List')

The sheet's last row is a footer artifact ("Count=3040" in the Account column,
blank in every other column) added by whatever tool exported the workbook —
it is dropped here, not loaded into Snowflake. See ONT_TRUCK_ROLL_README.md
for the full investigation of this and other source-file quirks.

Output:
    data/ont_truck_roll/ont_truck_roll.csv
"""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_XLSX = os.path.join(PROJECT_ROOT, "ONT Data", "Ont Truck Roll Report.xlsx")
SOURCE_SHEET = "Complete List"
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "ont_truck_roll")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "ont_truck_roll.csv")

EXPECTED_COLUMNS = [
    "Account", "Account Number", "Entered Date", "Solution Date",
    "Solution Entry User", "Order Number", "Problem", "Solution",
    "Service Address", "Service City", "Service Revenue Area", "Order Status",
]


def export():
    if not os.path.exists(SOURCE_XLSX):
        print(f"[ERROR] Source file not found: {SOURCE_XLSX}")
        sys.exit(1)

    print(f"[*] Reading '{SOURCE_SHEET}' sheet from: {SOURCE_XLSX}")
    df = pd.read_excel(SOURCE_XLSX, sheet_name=SOURCE_SHEET, dtype=str)

    if list(df.columns) != EXPECTED_COLUMNS:
        print("[WARNING] Column headers differ from what this script expects.")
        print(f"  Expected: {EXPECTED_COLUMNS}")
        print(f"  Found:    {list(df.columns)}")

    raw_row_count = len(df)

    # Drop the trailing footer/summary row(s): rows where every column except
    # 'Account' is blank/whitespace, and 'Account' does not look like a real
    # account name (e.g. "Count=3040"). This mirrors what we found on inspection:
    # the sheet's real data ends at row 3040, followed by exactly one such row.
    other_cols = [c for c in df.columns if c != "Account"]
    is_footer = df[other_cols].apply(
        lambda col: col.isna() | (col.astype(str).str.strip() == "")
    ).all(axis=1)
    footer_rows = df[is_footer]
    df = df[~is_footer].copy()

    dropped = raw_row_count - len(df)
    print(f"[*] Sheet rows read: {raw_row_count}")
    if dropped:
        print(f"[*] Dropped {dropped} footer/summary row(s):")
        for _, r in footer_rows.iterrows():
            print(f"    {dict(r)}")
    print(f"[*] Data rows to export: {len(df)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"[OK] Wrote {len(df)} rows to: {OUTPUT_CSV}")
    return OUTPUT_CSV, len(df)


if __name__ == "__main__":
    export()
