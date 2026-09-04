#!/usr/bin/env python3
"""
Seed SLA comparison data for the MTTR / SLA leaderboard.

Purpose
-------
The MTTR & SLA analytics (backend/main.py -> /analytics/mttr and
/admin/reports/wider-mttr) read ONLY from Snowflake:
    * CTTC_MOCK_TECHNICIAN_DATA  (technician roster for the leaderboard)
    * CTTC_MOCK_TICKETS          (resolved tickets that drive SLA %)

A technician only appears on the leaderboard / comparison if they have
at least one RESOLVED ticket with both CREATED_AT and RESOLVED_AT set.

SLA definition (backend/main.py:824-829):
    wall-clock duration = RESOLVED_AT - CREATED_AT
    ticket meets SLA  <=>  duration <= target hours for its priority
        Critical = 2h | High = 8h | Medium = 24h | Low = 48h
    technician SLA % = (# tickets that met SLA) / (# resolved tickets) * 100

This script inserts a technician roster and resolved tickets so the
leaderboard "lights up" with a spread of in-SLA and out-of-SLA results:
    Ruchir    ~83%   TECH-101  100%   TECH-102  75%
    TECH-103  50%    TECH-104  33%    TECH-105  0%

Usage
-----
    python scripts/seed_sla_comparison.py

Safe to re-run (idempotent): it deletes the seeded technicians and their
tickets first, then re-inserts them.
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

# Ensure project root is importable (same pattern as other scripts)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA,
                    SF_ROLE, SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                    SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Priority SLA targets in hours (must mirror backend/main.py)
SLA_TARGETS = {"Critical": 2.0, "High": 8.0, "Medium": 24.0, "Low": 48.0}

# The technicians to seed: (id, display name, email, shift, shift_start, shift_end)
TECHNICIANS = [
    ("TECH-101", "Tech 101", "tech-101@example.com", "Morning (08:00 - 16:00)", "08:00", "16:00"),
    ("TECH-102", "Tech 102", "tech-102@example.com", "Morning (08:00 - 16:00)", "08:00", "16:00"),
    ("TECH-103", "Tech 103", "tech-103@example.com", "Afternoon (14:00 - 22:00)", "14:00", "22:00"),
    ("TECH-104", "Tech 104", "tech-104@example.com", "Afternoon (14:00 - 22:00)", "14:00", "22:00"),
    ("TECH-105", "Tech 105", "tech-105@example.com", "Overnight (22:00 - 06:00)", "22:00", "06:00"),
    ("RUCHIR", "Ruchir", "ruchir@example.com", "Morning (08:00 - 16:00)", "08:00", "16:00"),
]

# Each technician -> list of (priority, duration_hours). The duration drives
# the SLA outcome automatically against SLA_TARGETS.
TICKET_PLAN: Dict[str, List[tuple]] = {
    "RUCHIR":   [("High", 4), ("High", 7), ("Critical", 1.5), ("Critical", 1.9), ("Medium", 20), ("Medium", 30)],
    "TECH-101": [("Critical", 1), ("High", 5), ("Medium", 10), ("Low", 30)],
    "TECH-102": [("High", 6), ("Medium", 40), ("Critical", 1.2), ("Medium", 15)],
    "TECH-103": [("High", 12), ("Critical", 3), ("Low", 20), ("Medium", 18)],
    "TECH-104": [("Critical", 3), ("High", 10), ("Low", 5)],
    "TECH-105": [("Critical", 5), ("High", 20), ("Medium", 48)],
}

# Fixed "past" base so results are deterministic regardless of run time.
BASE_TIME = datetime(2026, 8, 3, 8, 0, 0)


def expect_sla(priority: str, duration_h: float) -> bool:
    """Return True if a ticket of the given priority/duration meets SLA."""
    return duration_h <= SLA_TARGETS.get(priority, 24.0)


# ---------------------------------------------------------------------------
# Snowflake helpers
# ---------------------------------------------------------------------------

def connect() -> SnowflakeConnection:
    print("=" * 78)
    print(" SLA Comparison Seed - TeamLogic AutoTask")
    print("=" * 78)
    print(f" Account: {SF_ACCOUNT} | Database: {SF_DATABASE}.{SF_SCHEMA}")
    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT, sf_user=SF_USER, sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE, sf_schema=SF_SCHEMA, sf_role=SF_ROLE,
        sf_authenticator=SF_AUTHENTICATOR, sf_password=SF_PASSWORD,
        sf_passcode=SF_PASSCODE, sf_private_key_file=SF_PRIVATE_KEY_PATH,
        sf_private_key_pwd=SF_PRIVATE_KEY_PWD,
    )
    if not conn.is_connected():
        raise SystemExit("\n[ERROR] Could not connect to Snowflake. Check credentials/network.\n")
    print("[OK] Connected to Snowflake.\n")
    return conn


def run(sql: str, params: tuple = None) -> List[Dict]:
    """Execute SQL and return rows (wraps execute_query + explicit commit)."""
    rows = conn.execute_query(sql, params)
    if conn.conn:
        try:
            conn.conn.commit()
        except Exception:
            pass
    return rows


def ensure_columns() -> None:
    """Idempotently add any MTTR / schedule columns the seed needs."""
    print("[1/3] Ensuring MTTR & technician-schedule columns exist...")
    stmts = [
        # Ticket MTTR columns (mirrors backend ensure_mttr_columns)
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS ADD COLUMN IF NOT EXISTS RESOLVED_AT TIMESTAMP_NTZ",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS ADD COLUMN IF NOT EXISTS CLOSED_AT TIMESTAMP_NTZ",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS ADD COLUMN IF NOT EXISTS ASSIGNED_AT TIMESTAMP_NTZ",
        # Technician schedule/skills columns (mirrors ensure_technician_schedule_columns)
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS SHIFT VARCHAR(64)",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS SHIFT_START VARCHAR(32)",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS SHIFT_END VARCHAR(32)",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS SKILLS VARCHAR(1024)",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS SPECIALIZATIONS VARCHAR(1024)",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS ROLE VARCHAR(64)",
        f"ALTER TABLE {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA ADD COLUMN IF NOT EXISTS PHONE VARCHAR(64)",
    ]
    for s in stmts:
        try:
            run(s)
        except Exception as e:
            print(f"   Notice: skipped statement: {e}")
    print("[OK] Columns ensured.\n")


def cleanup(tech_ids: List[str]) -> None:
    """Remove any previously-seeded rows by technician id (re-run safe)."""
    print("[2/3] Cleaning up prior seeded rows for idempotency...")
    id_list = ", ".join(f"'{i}'" for i in tech_ids)
    run(f"DELETE FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS "
        f"WHERE TECHNICIAN_ID IN ({id_list}) OR TECHNICIANEMAIL ILIKE '%example.com%'")
    run(f"DELETE FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA "
        f"WHERE TECHNICIAN_ID IN ({id_list})")
    print("[OK] Cleanup done.\n")


def seed_technicians() -> None:
    print("[3/3] Seeding technicians...")
    sql = (
        f"INSERT INTO {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA "
        f"(TECHNICIAN_ID, NAME, EMAIL, ROLE, PHONE, SHIFT, SHIFT_START, SHIFT_END, "
        f"STATUS, SKILLS, SPECIALIZATIONS) "
        f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s)"
    )
    for t_id, name, email, shift, s_start, s_end in TECHNICIANS:
        run(sql, (t_id, name, email, "Technician", "555-0100", shift, s_start, s_end,
                  "Network & Diagnostics", "Routing, Fiber, Hardware"))
        print(f"   + Technician {t_id} ({name})")


def seed_tickets() -> None:
    print("\nSeeding resolved tickets...")
    tech_lookup = {t_id: (name, email) for (t_id, name, email, *_rest) in TECHNICIANS}

    ticket_counter = 1
    base_dt = BASE_TIME

    sql = (
        f"INSERT INTO {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS "
        f"(TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY, "
        f"ISSUETYPE, SUBISSUETYPE, PRIORITY, STATUS, RESOLUTION, "
        f"TECHNICIANEMAIL, TECHNICIAN_ID, "
        f"USEREMAIL, USERID, PHONENUMBER, CREATED_AT, ASSIGNED_AT, RESOLVED_AT, CLOSED_AT) "
        f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    summary = []
    for t_id, plan in TICKET_PLAN.items():
        name, email = tech_lookup[t_id]
        for priority, duration_h in plan:
            created = base_dt + timedelta(hours=ticket_counter * 5)
            resolved = created + timedelta(hours=duration_h)
            meets = expect_sla(priority, duration_h)

            ticket_number = f"TSLA-{t_id}-{ticket_counter:03d}"
            run(sql, (
                ticket_number,
                f"{priority} {ticket_number}",
                f"Seed ticket for {name} ({priority}, {duration_h}h resolution)",
                "Incident", "Network",
                "Connectivity", "Outage",
                priority, "Resolved",
                "Resolved by technician.",  # RESOLUTION
                email, t_id,          # TECHNICIANEMAIL / TECHNICIAN_ID
                "seed@example.com", "Seed User", "555-0000",
                created, created, resolved, resolved,
            ))
            print(f"   + {ticket_number:20s} {priority:9s} {duration_h:5.1f}h "
                  f"| {created:%m-%d %H:%M} -> {resolved:%m-%d %H:%M} "
                  f"| {'IN SLA' if meets else 'BREACHED'}")
            summary.append((t_id, name, email, priority, duration_h, meets))
            ticket_counter += 1

    # Print expected aggregate SLA % so you can verify the dashboard matches.
    print("\n" + "=" * 78)
    print(" Expected SLA compliance per technician (what the dashboard should show)")
    print("=" * 78)
    by_tech: Dict[str, List[bool]] = defaultdict(list)
    for t_id, _name, _email, _prio, _dur, meets in summary:
        by_tech[t_id].append(meets)
    for t_id, name, *_ in TECHNICIANS:
        hits = by_tech.get(t_id, [])
        rate = round(sum(hits) / len(hits) * 100, 1) if hits else 0.0
        bar = "=" * int(rate // 10) if rate else ""
        print(f"   {t_id:10s} {name:10s} {rate:6.1f}%  "
              f"{'IN SLA' if rate >= 50 else 'OUT OF SLA'}  [{bar}]")
    print("\n[COMPLETE] Seeding done.")


if __name__ == "__main__":
    conn = None
    try:
        conn = connect()
        ensure_columns()
        tech_ids = [t[0] for t in TECHNICIANS]
        cleanup(tech_ids)
        seed_technicians()
        seed_tickets()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any failure plainly
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] Seeding failed: {exc}")
    finally:
        if conn:
            conn.close_connection()