#!/usr/bin/env python3
"""
One-time data repair for tickets whose PRIORITY was persisted as an invalid
value ("Unknown", NULL, empty, "N/A", or a bare numeric Value ID).

Root cause: the AI classification fallback looked up similar-ticket PRIORITY
values (stored as Labels such as "High") against the Value-keyed reference map
and fell back to the literal label "Unknown", which was then written to the
CTTC_MOCK_TICKETS table and rendered as UNKNOWN on every ticket page.
The classification code now resolves both Value IDs and Labels and honors the
user-set priority, so this script only fixes rows already stored with bad data.

Repair logic (mirrors AIProcessor._resolve_priority order):
  1. If data/knowledgebase.json has the ticket and its `new_ticket.priority`
     (the priority the user chose at creation) is a valid reference label,
     restore that.
  2. Otherwise default to "Medium".

Also repairs knowledgebase.json entries whose classified_data.PRIORITY label
is invalid, so KB-based readers stop surfacing "Unknown".

Usage:
  python scripts/fix_unknown_priority.py            # dry run (default, no writes)
  python scripts/fix_unknown_priority.py --apply    # perform the repairs
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

from src.database.snowflake_db import SnowflakeConnection
from src.data.data_manager import DataManager
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA,
                    SF_ROLE, SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                    SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KB_PATH = os.path.join(PROJECT_ROOT, 'data', 'knowledgebase.json')

# Values considered invalid for the PRIORITY column (case-insensitive).
INVALID_PRIORITY_STRINGS = {'', 'unknown', 'n/a', 'none', 'null'}


def load_reference_priority_map():
    """Return the reference priority map, e.g. {'1': 'High', '2': 'Medium', ...}."""
    dm = DataManager(
        data_ref_file=os.path.join(PROJECT_ROOT, 'data', 'reference_data.txt'),
        knowledgebase_file=os.path.join(PROJECT_ROOT, 'data', 'knowledgebase.json'),
    )
    return dm.reference_data.get('priority', {}) or {}


def resolve_priority_label(raw, priority_map):
    """
    Resolve a raw priority (Label string or numeric Value) to the canonical
    reference Label, or None when it cannot be matched. Same behavior as
    AIProcessor._resolve_reference but standalone so this script stays simple.
    """
    if raw is None:
        return None
    raw_str = str(raw).strip()
    if not raw_str:
        return None
    if raw_str in priority_map:  # numeric reference Value, e.g. "2"
        return priority_map[raw_str]
    raw_lower = raw_str.lower()
    for value, label in priority_map.items():
        if str(label).strip().lower() == raw_lower:
            return label
    return None


def normalize_ticket_number(t_num):
    return str(t_num or '').strip().replace('-', '.')


def load_kb_user_priorities(priority_map):
    """
    Scan knowledgebase.json and map ticket_number -> user-requested priority
    (from new_ticket.priority, which stores priority_initial at creation time).
    Only values that resolve to a valid reference Label are kept.
    """
    user_priorities = {}
    if not os.path.exists(KB_PATH):
        print(f"Notice: knowledge base not found at {KB_PATH}; repairs will default to Medium.")
        return user_priorities
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        for entry in kb_data or []:
            nt = entry.get('new_ticket', {}) if isinstance(entry, dict) else {}
            t_num = str(nt.get('ticket_number') or '').strip()
            if not t_num:
                continue
            label = resolve_priority_label(nt.get('priority'), priority_map)
            if label:
                user_priorities[t_num] = label
    except Exception as e_kb:
        print(f"Notice: could not read knowledge base ({e_kb}); repairs will default to Medium.")
    return user_priorities


def build_kb_repair_plan(priority_map):
    """
    Identify knowledgebase.json entries whose classified_data.PRIORITY label is
    invalid, and compute the corrected {"Value", "Label"} pair for each.
    Returns (plan, kb_data); kb_data is None when the file is missing/unreadable.
    """
    if not os.path.exists(KB_PATH):
        return [], None
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
    except Exception as e_kb:
        print(f"Notice: could not read knowledge base ({e_kb})")
        return [], None

    plan = []
    for idx, entry in enumerate(kb_data):
        if not isinstance(entry, dict):
            continue
        nt = entry.get('new_ticket', {})
        cd = nt.get('classified_data', {}) or {}
        current = cd.get('PRIORITY')
        current_label = current.get('Label') if isinstance(current, dict) else current
        if resolve_priority_label(current_label, priority_map):
            continue  # already valid
        # Resolution order: user-set priority -> Medium default.
        label = resolve_priority_label(nt.get('priority'), priority_map) or priority_map.get('2', 'Medium')
        value = next((v for v, l in priority_map.items() if l == label), '2')
        plan.append({
            'index': idx,
            'ticket_number': str(nt.get('ticket_number') or f'<entry #{idx}>'),
            'current': current_label,
            'new_label': label,
            'new_value': value,
        })
    return plan, kb_data


def apply_kb_repairs(kb_data, plan):
    """Write the corrected PRIORITY pairs back to knowledgebase.json (with backup)."""
    for item in plan:
        entry = kb_data[item['index']]
        cd = entry.setdefault('new_ticket', {}).setdefault('classified_data', {})
        cd['PRIORITY'] = {"Value": item['new_value'], "Label": item['new_label']}

    backup = f"{KB_PATH}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(KB_PATH, backup)
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] knowledgebase.json repaired (backup: {os.path.basename(backup)})")


def main():
    parser = argparse.ArgumentParser(
        description="Repair invalid ticket PRIORITY values in Snowflake and knowledgebase.json")
    parser.add_argument('--apply', action='store_true',
                        help='Actually perform the repairs (default: dry run)')
    parser.add_argument('--skip-snowflake', action='store_true', help='Skip the Snowflake repair')
    parser.add_argument('--skip-kb', action='store_true', help='Skip the knowledgebase.json repair')
    args = parser.parse_args()

    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    priority_map = load_reference_priority_map()
    if not priority_map:
        print("[ERROR] No priority reference data loaded - aborting.")
        return 1

    print("=" * 70)
    print(" PRIORITY data repair - TeamLogic AutoTask")
    print("=" * 70)
    print(f" Reference priorities : {priority_map}")
    print(f" Mode                 : {'APPLY (writes)' if args.apply else 'DRY RUN (no writes)'}")
    print("=" * 70)

    exit_code = 0

    # ------------------------------------------------------------------ #
    # 1) Snowflake: CTTC_MOCK_TICKETS rows with NULL/Unknown/numeric priority
    # ------------------------------------------------------------------ #
    if not args.skip_snowflake:
        print("\n[*] Connecting to Snowflake...")
        conn = SnowflakeConnection(
            sf_account=SF_ACCOUNT, sf_user=SF_USER, sf_warehouse=SF_WAREHOUSE,
            sf_database=SF_DATABASE, sf_schema=SF_SCHEMA, sf_role=SF_ROLE,
            sf_authenticator=SF_AUTHENTICATOR, sf_password=SF_PASSWORD,
            sf_passcode=SF_PASSCODE, sf_private_key_file=SF_PRIVATE_KEY_PATH,
            sf_private_key_pwd=SF_PRIVATE_KEY_PWD
        )
        if not conn.is_connected():
            print("[ERROR] Failed to connect to Snowflake. Run the manual SQL below instead:")
            print(f"""
    UPDATE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
    SET PRIORITY = 'Medium'
    WHERE PRIORITY IS NULL OR UPPER(TRIM(PRIORITY)) IN ('UNKNOWN', 'N/A', 'NONE', 'NULL')
       OR PRIORITY REGEXP '^[0-9]+$';
""")
            exit_code = 1
        else:
            try:
                bad_query = f"""
                    SELECT TICKETNUMBER, PRIORITY, USERID
                    FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS
                    WHERE PRIORITY IS NULL
                       OR UPPER(TRIM(PRIORITY)) IN ('UNKNOWN', 'N/A', 'NONE', 'NULL')
                       OR PRIORITY REGEXP '^[0-9]+$'
                """
                rows = conn.execute_query(bad_query) or []
                kb_priorities = load_kb_user_priorities(priority_map)

                print(f"\n[*] Found {len(rows)} ticket(s) with invalid PRIORITY:")
                update_statements = []
                for row in rows:
                    t_num = str(row.get('TICKETNUMBER') or '').strip()
                    if not t_num:
                        continue
                    current = row.get('PRIORITY')
                    # Prefer the priority the user originally requested.
                    label = (kb_priorities.get(t_num)
                             or kb_priorities.get(normalize_ticket_number(t_num))
                             or 'Medium')
                    source = ('knowledgebase (user-set)'
                              if (t_num in kb_priorities
                                  or normalize_ticket_number(t_num) in kb_priorities)
                              else 'default')
                    print(f"    - {t_num}: '{current}' -> '{label}'  ({source})")
                    update_statements.append((t_num, label))

                if not update_statements:
                    print("[OK] No invalid PRIORITY values found in Snowflake - nothing to repair.")
                elif args.apply:
                    for t_num, label in update_statements:
                        upd = (f"UPDATE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS "
                               f"SET PRIORITY = %s WHERE TICKETNUMBER = %s")
                        conn.execute_query(upd, (label, t_num))
                        print(f"    [OK] {t_num}: PRIORITY -> {label}")
                    print(f"[OK] Snowflake repair complete: {len(update_statements)} ticket(s) updated.")
                else:
                    print("\n[i] Dry run only - re-run with --apply to write these changes to Snowflake.")
            finally:
                conn.close_connection()

    # ------------------------------------------------------------------ #
    # 2) knowledgebase.json entries with invalid classified PRIORITY labels
    # ------------------------------------------------------------------ #
    if not args.skip_kb:
        kb_plan, kb_data = build_kb_repair_plan(priority_map)
        if not kb_plan:
            print("\n[OK] knowledgebase.json has no invalid PRIORITY labels - nothing to repair.")
        else:
            print(f"\n[*] knowledgebase.json: {len(kb_plan)} entr(ies) with invalid PRIORITY label:")
            for item in kb_plan:
                print(f"    {item['ticket_number']}: '{item['current']}' -> '{item['new_label']}'")
            if args.apply and kb_data is not None:
                apply_kb_repairs(kb_data, kb_plan)
            else:
                print("[i] Dry run only - re-run with --apply to write these repairs.")

    print("\nDone.")
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
