"""
Prepare ticket data for a demo.

1. Closes the open test tickets with a realistic lifecycle (acknowledged ->
   arrived on site -> resolved -> closed), timed from each ticket's own
   creation time, so MTTR and SLA stay realistic. Closing them through the
   app instead would stamp "now" as the resolved time and turn days-old test
   tickets into multi-day resolutions.
2. Inserts a handful of fresh open tickets created in the last hours, so the
   open-ticket SLA view shows a realistic mix (on track / approaching / one
   overdue) and technicians have live work for the demo.
3. Recomputes CURRENT_WORKLOAD for every technician from the open tickets.

Everything changed is recorded in scripts/demo_prep_manifest.json; --undo
restores the closed tickets to their previous state and deletes the fresh ones.

Usage:
    python scripts/prepare_demo_tickets.py            # dry run: show the plan
    python scripts/prepare_demo_tickets.py --apply    # make the changes
    python scripts/prepare_demo_tickets.py --undo     # revert using the manifest
"""

import os
import sys
import json
import random
import argparse
from datetime import timedelta, datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SF_DATABASE, SF_SCHEMA
from seed_mttr_mock_tickets import connect, db_now, SLA_TARGET_HOURS, STAGE_MINUTES, FIELD_TECHS, BREACH_RATE

ACTIVE = f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TICKETS"
CLOSED = f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_CLOSED_TICKETS"
TECHS = f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_TECHNICIAN_DATA"
USERS = f"{SF_DATABASE}.{SF_SCHEMA}.CTTC_MOCK_USER_DATA"
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_prep_manifest.json")
OPEN_FILTER = "LOWER(TRIM(STATUS)) NOT IN ('resolved', 'closed', 'complete', 'completed')"
LIFECYCLE_COLS = ["STATUS", "ACKNOWLEDGED_AT", "ARRIVED_AT", "RESOLVED_AT", "CLOSED_AT",
                  "TIME_SPENT", "TIME_SPENT_MINUTES", "TIME_SPENT_HOURS", "RESOLUTION"]

# Fresh open tickets: (hours ago, priority, technician, status, title, description, category, issue, sub-issue)
FRESH_TICKETS = [
    (0.6, "Critical", "TECH-ENG-01", "In Progress", "OLT PON port 1/2/6 down - 28 subscribers offline",
     "Monitoring alarm: PON port 1/2/6 link down on OLT-XG02. 28 subscribers on this port report no service.",
     "Network", "Incident", "Connectivity/Outages"),
    (1.2, "High", "TECH-TR-01", "Assigned", "No internet - ONT red LOS light",
     "Customer reports no internet since this morning. ONT LOS light is solid red. Only this home affected.",
     "Hardware", "Incident", "Connectivity/Outages"),
    (6.2, "High", "TECH-TR-02", "On Site", "Fiber drop cut by contractor",
     "Utility contractor cut the fiber drop to the house while trenching. Customer has no internet or phone.",
     "Hardware", "Incident", "Connectivity/Outages"),
    (3.0, "Medium", "TECH-TR-03", "Assigned", "Slow speeds every evening",
     "Speed drops to about 20 Mbps between 7 and 10 pm every evening. Fine during the day.",
     "Network", "Incident", "Performance"),
    (5.0, "Medium", "TECH-ONT-01", "In Progress", "No dial tone on ONT phone port",
     "Internet works, but the landline connected to the ONT phone port has no dial tone.",
     "Hardware", "Incident", "Voice"),
    (2.0, "Low", "TECH-TR-04", "Assigned", "Relocate ONT to garage",
     "Customer is renovating and wants the ONT moved to the garage next week. Service is working.",
     "Hardware", "Service Request", "Installation"),
    (20.0, "Medium", "Ruchir", "In Progress", "Intermittent packet loss on EVPN service",
     "Business customer reports 3-5% packet loss to the branch office over the EVPN service.",
     "Network", "Incident", "Performance"),
    (9.5, "High", "TECH-ENG-01", "In Progress", "OLT line card high temperature alarm",
     "OLT-XG01 line card 3 temperature above threshold. Service still up; fan tray suspected.",
     "Hardware", "Incident", "Device Failure"),
]


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "-"


def plan_closures(conn, now, rng):
    rows = conn.execute_query(
        f"SELECT TICKETNUMBER, PRIORITY, TECHNICIAN_ID, TITLE, CREATED_AT, ASSIGNED_AT, "
        f"{', '.join(LIFECYCLE_COLS)} FROM {ACTIVE} WHERE {OPEN_FILTER} ORDER BY CREATED_AT")
    plans = []
    for r in rows:
        priority = r["PRIORITY"] if r["PRIORITY"] in SLA_TARGET_HOURS else "Medium"
        created = r["CREATED_AT"]
        assigned = r["ASSIGNED_AT"] if r["ASSIGNED_AT"] and r["ASSIGNED_AT"] >= created else created
        (_, _), (t_lo, t_hi), (w_lo, w_hi) = STAGE_MINUTES[priority]
        field = r["TECHNICIAN_ID"] in FIELD_TECHS
        ack_m = rng.uniform(5, 30)
        travel_m = rng.uniform(t_lo, t_hi) if field else 0.0
        work_m = rng.uniform(w_lo, w_hi)
        elapsed_before = (assigned - created).total_seconds() / 60
        target_m = SLA_TARGET_HOURS[priority] * 60
        if rng.random() < BREACH_RATE:
            ack_m = max(ack_m, target_m * rng.uniform(1.1, 1.5) - elapsed_before - travel_m - work_m)
        acknowledged = assigned + timedelta(minutes=ack_m)
        arrived = acknowledged + timedelta(minutes=travel_m) if field else None
        resolved = (arrived or acknowledged) + timedelta(minutes=work_m)
        if resolved >= now:
            continue  # too recent to have been resolved yet; leave open
        work = int(round(work_m))
        plans.append({
            "ticket": r["TICKETNUMBER"], "priority": priority, "tech": r["TECHNICIAN_ID"], "title": r["TITLE"],
            "created": created, "assigned": assigned, "acknowledged": acknowledged, "arrived": arrived,
            "resolved": resolved, "closed": resolved + timedelta(minutes=rng.uniform(5, 30)),
            "work_minutes": work,
            "resolution": ((r["RESOLUTION"] or "").rstrip() + "\n\n" if r["RESOLUTION"] else "")
                          + f"Service restored and verified with the customer. Time Spent: {work} mins",
            "original": {c: (r[c].isoformat() if isinstance(r[c], datetime) else r[c]) for c in LIFECYCLE_COLS},
        })
    return plans


def plan_fresh(conn, now):
    techs = {t["TECHNICIAN_ID"]: t for t in conn.execute_query(f"SELECT TECHNICIAN_ID, EMAIL FROM {TECHS}")}
    users = conn.execute_query(f"SELECT USER_ID, USER_EMAIL, USER_PHONENUMBER FROM {USERS} WHERE USER_ID LIKE 'USR-%' ORDER BY USER_ID")
    next_seq = {}
    fresh = []
    # Oldest first, so ticket numbers increase with creation time like real tickets
    ordered = sorted(FRESH_TICKETS, key=lambda t: -t[0])
    for i, (hours_ago, priority, tech_id, status, title, desc, category, issue, sub_issue) in enumerate(ordered):
        created = now - timedelta(hours=hours_ago)
        date_key = created.strftime("%Y%m%d")
        if date_key not in next_seq:
            res = conn.execute_query(
                f"SELECT MAX(TRY_TO_NUMBER(SPLIT_PART(TICKETNUMBER, '.', 2))) AS M FROM ("
                f"SELECT TICKETNUMBER FROM {ACTIVE} WHERE TICKETNUMBER LIKE %s UNION ALL "
                f"SELECT TICKETNUMBER FROM {CLOSED} WHERE TICKETNUMBER LIKE %s) "
                f"WHERE TRY_TO_NUMBER(SPLIT_PART(TICKETNUMBER, '.', 2)) < 8000",
                (f"T{date_key}.%", f"T{date_key}.%"))
            next_seq[date_key] = int(res[0]["M"] or 0) if res else 0
        next_seq[date_key] += 1
        assigned = created + timedelta(minutes=2)
        acknowledged = created + timedelta(minutes=15) if status in ("In Progress", "On Site") else None
        arrived = created + timedelta(minutes=70) if status == "On Site" else None
        user = users[i % len(users)]
        fresh.append({
            "TICKETNUMBER": f"T{date_key}.{next_seq[date_key]:04d}", "TITLE": title, "DESCRIPTION": desc,
            "TICKETTYPE": "Service Request" if issue == "Service Request" else "Incident",
            "TICKETCATEGORY": category, "ISSUETYPE": issue, "SUBISSUETYPE": sub_issue,
            "DUEDATETIME": (created + timedelta(hours=SLA_TARGET_HOURS[priority])).strftime("%Y-%m-%d %H:%M:%S"),
            "PRIORITY": priority, "STATUS": status, "RESOLUTION": "",
            "TECHNICIANEMAIL": techs.get(tech_id, {}).get("EMAIL", ""), "TECHNICIAN_ID": tech_id,
            "USEREMAIL": user["USER_EMAIL"], "USERID": user["USER_ID"], "PHONENUMBER": user["USER_PHONENUMBER"],
            "CREATED_AT": created, "ASSIGNED_AT": assigned, "ACKNOWLEDGED_AT": acknowledged, "ARRIVED_AT": arrived,
        })
    return fresh


def sla_state(priority, created, now):
    pct = (now - created).total_seconds() / 3600 / SLA_TARGET_HOURS[priority]
    return "on track" if pct < 0.7 else "approaching" if pct <= 1 else "OVERDUE"


def merge_to_closed(cur, numbers):
    placeholders = ", ".join(["%s"] * len(numbers))
    cur.execute(f"""
        MERGE INTO {CLOSED} target
        USING (
            SELECT TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY, ISSUETYPE, SUBISSUETYPE,
                   DUEDATETIME, PRIORITY, STATUS, RESOLUTION, TECHNICIANEMAIL, TECHNICIAN_ID, USEREMAIL,
                   USERID, PHONENUMBER, CREATED_AT AS ORIGINAL_CREATED_AT, RESOLVED_AT, CLOSED_AT,
                   TIME_SPENT_MINUTES, TIME_SPENT_HOURS, ASSIGNED_AT, ACKNOWLEDGED_AT, ARRIVED_AT
            FROM {ACTIVE} WHERE TICKETNUMBER IN ({placeholders})
        ) source
        ON target.TICKETNUMBER = source.TICKETNUMBER
        WHEN MATCHED THEN UPDATE SET
            target.STATUS = source.STATUS, target.RESOLUTION = source.RESOLUTION,
            target.ORIGINAL_CREATED_AT = source.ORIGINAL_CREATED_AT, target.RESOLVED_AT = source.RESOLVED_AT,
            target.CLOSED_AT = source.CLOSED_AT, target.TIME_SPENT_MINUTES = source.TIME_SPENT_MINUTES,
            target.TIME_SPENT_HOURS = source.TIME_SPENT_HOURS, target.ASSIGNED_AT = source.ASSIGNED_AT,
            target.ACKNOWLEDGED_AT = source.ACKNOWLEDGED_AT, target.ARRIVED_AT = source.ARRIVED_AT
        WHEN NOT MATCHED THEN INSERT (
            TICKETNUMBER, TITLE, DESCRIPTION, TICKETTYPE, TICKETCATEGORY, ISSUETYPE, SUBISSUETYPE, DUEDATETIME,
            PRIORITY, STATUS, RESOLUTION, TECHNICIANEMAIL, TECHNICIAN_ID, USEREMAIL, USERID, PHONENUMBER,
            ORIGINAL_CREATED_AT, RESOLVED_AT, CLOSED_AT, TIME_SPENT_MINUTES, TIME_SPENT_HOURS,
            ASSIGNED_AT, ACKNOWLEDGED_AT, ARRIVED_AT
        ) VALUES (
            source.TICKETNUMBER, source.TITLE, source.DESCRIPTION, source.TICKETTYPE, source.TICKETCATEGORY,
            source.ISSUETYPE, source.SUBISSUETYPE, source.DUEDATETIME, source.PRIORITY, source.STATUS,
            source.RESOLUTION, source.TECHNICIANEMAIL, source.TECHNICIAN_ID, source.USEREMAIL, source.USERID,
            source.PHONENUMBER, source.ORIGINAL_CREATED_AT, source.RESOLVED_AT, source.CLOSED_AT,
            source.TIME_SPENT_MINUTES, source.TIME_SPENT_HOURS, source.ASSIGNED_AT, source.ACKNOWLEDGED_AT,
            source.ARRIVED_AT
        )""", tuple(numbers))


def recompute_workloads(cur):
    cur.execute(f"""
        UPDATE {TECHS} d SET CURRENT_WORKLOAD = c.N
        FROM (
            SELECT tech.TECHNICIAN_ID, COUNT(t.TICKETNUMBER) AS N
            FROM {TECHS} tech
            LEFT JOIN {ACTIVE} t ON t.TECHNICIAN_ID = tech.TECHNICIAN_ID AND LOWER(TRIM(t.STATUS))
                 NOT IN ('resolved', 'closed', 'complete', 'completed')
            GROUP BY tech.TECHNICIAN_ID
        ) c
        WHERE d.TECHNICIAN_ID = c.TECHNICIAN_ID""")


def apply(conn, plans, fresh):
    cur = conn.conn.cursor()
    try:
        for p in plans:
            cur.execute(
                f"UPDATE {ACTIVE} SET STATUS = 'Closed', ASSIGNED_AT = %s, ACKNOWLEDGED_AT = %s, ARRIVED_AT = %s, "
                f"RESOLVED_AT = %s, CLOSED_AT = %s, TIME_SPENT = %s, TIME_SPENT_MINUTES = %s, "
                f"TIME_SPENT_HOURS = %s, RESOLUTION = %s WHERE TICKETNUMBER = %s",
                (p["assigned"], p["acknowledged"], p["arrived"], p["resolved"], p["closed"],
                 f"{p['work_minutes']} mins", p["work_minutes"], round(p["work_minutes"] / 60.0, 2),
                 p["resolution"], p["ticket"]))
        if plans:
            merge_to_closed(cur, [p["ticket"] for p in plans])
        if fresh:
            cols = list(fresh[0].keys())
            cur.executemany(f"INSERT INTO {ACTIVE} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                            [tuple(t[c] for c in cols) for t in fresh])
        recompute_workloads(cur)
    finally:
        cur.close()
    with open(MANIFEST, "w") as f:
        json.dump({"closed": [{"ticket": p["ticket"], "original": p["original"]} for p in plans],
                   "fresh": [t["TICKETNUMBER"] for t in fresh]}, f, indent=2)
    print(f"[OK] Closed {len(plans)} tickets, added {len(fresh)} fresh open tickets, recomputed workloads.")
    print(f"     Undo information saved to {MANIFEST}")


def undo(conn):
    if not os.path.exists(MANIFEST):
        sys.exit("[ERROR] No manifest found; nothing to undo.")
    data = json.load(open(MANIFEST))
    cur = conn.conn.cursor()
    try:
        for item in data["closed"]:
            o = item["original"]
            cur.execute(f"UPDATE {ACTIVE} SET {', '.join(c + ' = %s' for c in LIFECYCLE_COLS)} WHERE TICKETNUMBER = %s",
                        tuple(o[c] for c in LIFECYCLE_COLS) + (item["ticket"],))
            cur.execute(f"DELETE FROM {CLOSED} WHERE TICKETNUMBER = %s", (item["ticket"],))
        for number in data["fresh"]:
            cur.execute(f"DELETE FROM {ACTIVE} WHERE TICKETNUMBER = %s", (number,))
        recompute_workloads(cur)
    finally:
        cur.close()
    os.rename(MANIFEST, MANIFEST + ".undone")
    print(f"[OK] Reopened {len(data['closed'])} tickets and removed {len(data['fresh'])} fresh tickets.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--undo", action="store_true")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    conn = connect()
    try:
        if args.undo:
            undo(conn)
            return
        if args.apply and os.path.exists(MANIFEST):
            sys.exit(f"[ERROR] {MANIFEST} exists: demo prep was already applied. Run --undo first.")
        now = db_now(conn)
        plans = plan_closures(conn, now, random.Random(args.seed))
        fresh = plan_fresh(conn, now)

        print(f"Close {len(plans)} open test tickets with a realistic lifecycle:")
        met = 0
        for p in plans:
            hours = (p["resolved"] - p["created"]).total_seconds() / 3600
            ok = hours <= SLA_TARGET_HOURS[p["priority"]]
            met += ok
            print(f"  {p['ticket']}  {p['priority']:<8} {p['tech']:<12} created {fmt(p['created'])}  "
                  f"resolved {fmt(p['resolved'])}  ({hours:4.1f} h, {'SLA met' if ok else 'SLA missed'})")
        if plans:
            print(f"  -> {met}/{len(plans)} within SLA")
        print(f"\nAdd {len(fresh)} fresh open tickets:")
        for t in fresh:
            print(f"  {t['TICKETNUMBER']}  {t['PRIORITY']:<8} {t['TECHNICIAN_ID']:<12} {t['STATUS']:<12} "
                  f"created {fmt(t['CREATED_AT'])}  SLA: {sla_state(t['PRIORITY'], t['CREATED_AT'], now):<11} {t['TITLE']}")
        if args.apply:
            apply(conn, plans, fresh)
        else:
            print("\nDry run only. Re-run with --apply to make these changes.")
    finally:
        conn.close_connection()


if __name__ == "__main__":
    main()
