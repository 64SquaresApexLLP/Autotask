"""
Seed realistic closed tickets for the MTTR report.

Every generated ticket has a consistent lifecycle:
    created -> assigned (MTTA) -> arrived on site (travel) -> resolved (on-site work) -> closed
so MTTR (= resolved - created), SLA compliance and the assign/travel/on-site
breakdown can all be checked against known values.

Ticket numbers use the T{YYYYMMDD}.8NNN range so seeded rows are easy to
recognise and remove; the live ticket generator never reaches sequence 8000.

Usage:
    python scripts/seed_mttr_mock_tickets.py              # dry run: print rows + expected MTTR
    python scripts/seed_mttr_mock_tickets.py --apply      # insert into CTTC_MOCK_CLOSED_TICKETS
    python scripts/seed_mttr_mock_tickets.py --delete     # remove all seeded rows
"""

import os
import sys
import random
import argparse
import statistics
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.snowflake_db import SnowflakeConnection
from config import (SF_ACCOUNT, SF_USER, SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA, SF_ROLE,
                    SF_AUTHENTICATOR, SF_PASSWORD, SF_PASSCODE,
                    SF_PRIVATE_KEY_PATH, SF_PRIVATE_KEY_PWD)

TABLE = f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_CLOSED_TICKETS"
SEED_PATTERN = r'^T[0-9]{8}[.]8[0-9]{3}$'
SLA_TARGET_HOURS = {"Critical": 2.0, "High": 8.0, "Medium": 24.0, "Low": 48.0}
BREACH_RATE = 0.15  # ~85% of tickets meet SLA

# Lifecycle ranges in minutes per priority: (assign, travel, on-site work)
STAGE_MINUTES = {
    "Critical": ((5, 15), (20, 45), (25, 60)),
    "High": ((15, 60), (30, 90), (45, 150)),
    "Medium": ((60, 360), (30, 90), (30, 120)),
    "Low": ((240, 1200), (30, 90), (20, 90)),
}

# Technician groups: field techs travel to site, remote techs work from the NOC/CO.
FIELD_TECHS = {"TECH-TR-01", "TECH-TR-02", "TECH-TR-03", "TECH-TR-04", "TECH-ONT-01", "TECH-ENG-01"}

# (title, description, priority, category, issue type, sub-issue, ticket type)
TEMPLATES = {
    "truck_roll": [
        ("ONT showing red LOS light - no internet",
         "Customer reports total loss of internet. ONT LOS indicator is solid red since this morning; router has no WAN.",
         "High", "Hardware", "Incident", "Connectivity/Outages", "Incident"),
        ("Fiber drop cable cut by landscaping crew",
         "Drop cable between pedestal and house was cut during yard work. Customer completely offline.",
         "High", "Hardware", "Incident", "Connectivity/Outages", "Incident"),
        ("Low optical power at ONT (-29 dBm)",
         "Intermittent drops every evening. Remote check shows receive power at -29 dBm, below the -27 dBm threshold.",
         "Medium", "Network", "Incident", "Performance", "Incident"),
        ("Router failed after power surge",
         "Router will not power on after storm. ONT is green. Needs router replacement on site.",
         "Medium", "Hardware", "Incident", "Device Failure", "Incident"),
        ("Relocate ONT to new utility room",
         "Customer renovating and requests the ONT be moved to the new utility room. Service is working.",
         "Low", "Hardware", "Service Request", "Installation", "Service Request"),
        ("Neighborhood splitter cabinet damaged - 18 homes offline",
         "Vehicle hit the fiber splitter cabinet on Oak Street. 18 subscribers report loss of service.",
         "Critical", "Network", "Incident", "Connectivity/Outages", "Incident"),
    ],
    "ont": [
        ("ONT stuck in reboot loop after firmware update",
         "ONT restarts every 2-3 minutes since last night's firmware push. Customer has no stable service.",
         "High", "Hardware", "Incident", "Device Failure", "Incident"),
        ("ONT provisioning mismatch after replacement",
         "New ONT installed but serial not provisioned on OLT; internet and voice not working.",
         "Medium", "Network", "Incident", "Provisioning", "Incident"),
        ("Voice line has no dial tone on ONT POTS port",
         "Internet works but the phone connected to the ONT POTS port has no dial tone.",
         "Medium", "Hardware", "Incident", "Voice", "Incident"),
        ("Install ONT battery backup unit",
         "Customer requests a battery backup unit for the ONT for power outages.",
         "Low", "Hardware", "Service Request", "Installation", "Service Request"),
    ],
    "noc": [
        ("Customer VLAN misconfigured - no DHCP lease",
         "Router not receiving an IP address. Service VLAN on the subscriber profile appears wrong.",
         "High", "Network", "Incident", "Provisioning", "Incident"),
        ("Intermittent packet loss on EVPN path",
         "Business customer reports 3-5% packet loss to their branch office over the EVPN service.",
         "Medium", "Network", "Incident", "Performance", "Incident"),
        ("Static IP not routing after migration",
         "Static IP block assigned last week is not reachable from the internet.",
         "Medium", "Network", "Incident", "Connectivity/Outages", "Incident"),
        ("Request reverse DNS for static IP",
         "Customer requests PTR record for their static IP for their mail server.",
         "Low", "Network", "Service Request", "Configuration", "Service Request"),
        ("Core BGP session flapping - regional slowdown",
         "Upstream BGP session to transit provider flapping; many subscribers report slow speeds.",
         "Critical", "Network", "Incident", "Connectivity/Outages", "Incident"),
    ],
    "olt": [
        ("OLT PON port 1/1/4 down - 32 subscribers offline",
         "Alarm: PON port 1/1/4 link down. All 32 subscribers on this port are offline.",
         "Critical", "Network", "Incident", "Connectivity/Outages", "Incident"),
        ("OLT line card high temperature alarm",
         "OLT line card 3 reports temperature above threshold. Service still up, fan tray suspected.",
         "High", "Hardware", "Incident", "Device Failure", "Incident"),
        ("Scheduled OLT firmware upgrade",
         "Apply vendor firmware update to OLT in maintenance window.",
         "Low", "Network", "Change Request", "Maintenance", "Change Request"),
    ],
}
TECH_TEMPLATES = {
    "TECH-TR-01": "truck_roll", "TECH-TR-02": "truck_roll", "TECH-TR-03": "truck_roll",
    "TECH-TR-04": "truck_roll", "TECH-ONT-01": "ont", "Ruchir": "noc", "TECH-ENG-01": "olt",
}


def connect() -> SnowflakeConnection:
    conn = SnowflakeConnection(
        sf_account=SF_ACCOUNT, sf_user=SF_USER, sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE, sf_schema=SF_SCHEMA, sf_role=SF_ROLE,
        sf_authenticator=SF_AUTHENTICATOR, sf_password=SF_PASSWORD, sf_passcode=SF_PASSCODE,
        sf_private_key_file=SF_PRIVATE_KEY_PATH, sf_private_key_pwd=SF_PRIVATE_KEY_PWD,
    )
    if not conn.is_connected():
        sys.exit("[ERROR] Could not connect to Snowflake.")
    return conn


def db_now(conn):
    # Same clock as CURRENT_TIMESTAMP() writes made by the backend
    return conn.execute_query("SELECT CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS NOW_TS")[0]["NOW_TS"]


def generate(conn, count: int, seed: int):
    rng = random.Random(seed)
    now = db_now(conn).replace(microsecond=0)

    techs = {r["TECHNICIAN_ID"]: r for r in conn.execute_query(
        f"SELECT TECHNICIAN_ID, NAME, EMAIL FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA")}
    users = conn.execute_query(
        f"SELECT USER_ID, NAME, USER_EMAIL, USER_PHONENUMBER FROM {SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_USER_DATA")
    tech_ids = [t for t in TECH_TEMPLATES if t in techs]
    if not tech_ids or not users:
        sys.exit("[ERROR] Technician or user tables are empty.")

    rows, seq_by_date = [], {}
    for i in range(count):
        # 1/6 in the last 7 days, 1/3 in days 8-30, the rest in days 31-90
        bucket = i % 6
        days_ago = rng.uniform(0.5, 7) if bucket == 0 else rng.uniform(7, 30) if bucket < 3 else rng.uniform(30, 90)
        created = (now - timedelta(days=days_ago)).replace(hour=rng.randint(7, 19), minute=rng.randint(0, 59), second=rng.randint(0, 59))

        tech_id = tech_ids[i % len(tech_ids)]
        title, desc, priority, category, issue, sub_issue, ticket_type = rng.choice(TEMPLATES[TECH_TEMPLATES[tech_id]])
        (a_lo, a_hi), (t_lo, t_hi), (w_lo, w_hi) = STAGE_MINUTES[priority]
        assign_m = rng.uniform(a_lo, a_hi)
        travel_m = rng.uniform(t_lo, t_hi) if tech_id in FIELD_TECHS else 0.0
        work_m = rng.uniform(w_lo, w_hi)

        target_m = SLA_TARGET_HOURS[priority] * 60
        if rng.random() < BREACH_RATE:
            # Breach: the ticket waited in the queue too long before assignment
            assign_m = target_m * rng.uniform(1.1, 1.6) - travel_m - work_m
        else:
            # Keep within SLA
            overflow = assign_m + travel_m + work_m - target_m * 0.95
            if overflow > 0:
                assign_m = max(a_lo, assign_m - overflow)

        assigned = created + timedelta(minutes=assign_m)
        arrived = assigned + timedelta(minutes=travel_m) if tech_id in FIELD_TECHS else None
        resolved = (arrived or assigned) + timedelta(minutes=work_m)
        if resolved >= now:  # never resolve in the future
            shift = resolved - now + timedelta(hours=1)
            created, assigned, resolved = created - shift, assigned - shift, resolved - shift
            arrived = arrived - shift if arrived else None
        closed = resolved + timedelta(minutes=rng.uniform(5, 30))

        date_key = created.strftime("%Y%m%d")
        seq_by_date[date_key] = seq_by_date.get(date_key, 8000) + 1
        user = users[i % len(users)]
        tech = techs[tech_id]
        work_minutes = int(round(work_m))
        rows.append({
            "TICKETNUMBER": f"T{date_key}.{seq_by_date[date_key]}",
            "TITLE": title,
            "DESCRIPTION": desc,
            "TICKETTYPE": ticket_type,
            "TICKETCATEGORY": category,
            "ISSUETYPE": issue,
            "SUBISSUETYPE": sub_issue,
            "DUEDATETIME": (created + timedelta(hours=SLA_TARGET_HOURS[priority])).strftime("%Y-%m-%d %H:%M:%S"),
            "PRIORITY": priority,
            "STATUS": "Closed",
            "RESOLUTION": f"Issue resolved by {tech['NAME']}. Root cause identified and fixed; service verified with customer. Time Spent: {work_minutes} mins",
            "TECHNICIANEMAIL": tech["EMAIL"],
            "TECHNICIAN_ID": tech_id,
            "USEREMAIL": user["USER_EMAIL"],
            "USERID": user["USER_ID"],
            "PHONENUMBER": user["USER_PHONENUMBER"],
            "CLOSED_AT": closed,
            "ORIGINAL_CREATED_AT": created,
            "RESOLVED_AT": resolved,
            "TIME_SPENT_MINUTES": work_minutes,
            "TIME_SPENT_HOURS": round(work_minutes / 60.0, 2),
            "ASSIGNED_AT": assigned,
            "ARRIVED_AT": arrived,
        })
    return rows, now


def print_expected(rows, now):
    def hours(r):
        return (r["RESOLVED_AT"] - r["ORIGINAL_CREATED_AT"]).total_seconds() / 3600.0

    def line(label, subset):
        hs = [hours(r) for r in subset]
        met = sum(1 for r in subset if hours(r) <= SLA_TARGET_HOURS[r["PRIORITY"]])
        print(f"  {label:<14} n={len(hs):>3}  MTTR={statistics.mean(hs):6.2f}h  median={statistics.median(hs):6.2f}h  SLA={met / len(hs) * 100:5.1f}%")

    for days in (30, 90):
        window = [r for r in rows if r["RESOLVED_AT"] >= now - timedelta(days=days)]
        print(f"\nExpected MTTR for these seeded tickets, last {days} days:")
        line("ALL", window)
        for p in SLA_TARGET_HOURS:
            subset = [r for r in window if r["PRIORITY"] == p]
            if subset:
                line(p, subset)
        for t in TECH_TEMPLATES:
            subset = [r for r in window if r["TECHNICIAN_ID"] == t]
            if subset:
                line(t, subset)


def apply(conn, rows):
    cols = list(rows[0].keys())
    sql = f"INSERT INTO {TABLE} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})"
    cur = conn.conn.cursor()
    try:
        cur.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
        print(f"[OK] Inserted {cur.rowcount} rows into {TABLE}")
    finally:
        cur.close()


def delete(conn):
    cur = conn.conn.cursor()
    try:
        cur.execute(f"DELETE FROM {TABLE} WHERE REGEXP_LIKE(TICKETNUMBER, %s)", (SEED_PATTERN,))
        print(f"[OK] Deleted {cur.rowcount} seeded rows from {TABLE}")
    finally:
        cur.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="insert the generated rows")
    parser.add_argument("--delete", action="store_true", help="delete all previously seeded rows")
    parser.add_argument("--count", type=int, default=72, help="number of tickets to generate")
    parser.add_argument("--seed", type=int, default=42, help="random seed (same seed -> same data)")
    args = parser.parse_args()

    conn = connect()
    try:
        if args.delete:
            delete(conn)
            return
        existing = conn.execute_query(f"SELECT COUNT(*) AS N FROM {TABLE} WHERE REGEXP_LIKE(TICKETNUMBER, %s)", (SEED_PATTERN,))
        if existing and existing[0]["N"] and args.apply:
            sys.exit(f"[ERROR] {existing[0]['N']} seeded rows already exist. Run --delete first.")

        rows, now = generate(conn, args.count, args.seed)
        print(f"Generated {len(rows)} tickets (Snowflake now = {now})")
        for r in rows[:8]:
            print(f"  {r['TICKETNUMBER']}  {r['PRIORITY']:<8} {r['TECHNICIAN_ID']:<12} "
                  f"created {r['ORIGINAL_CREATED_AT']}  resolved {r['RESOLVED_AT']}  work {r['TIME_SPENT_MINUTES']}m  {r['TITLE'][:40]}")
        print("  ...")
        print_expected(rows, now)
        if args.apply:
            apply(conn, rows)
        else:
            print("\nDry run only. Re-run with --apply to insert.")
    finally:
        conn.close_connection()


if __name__ == "__main__":
    main()
