"""
Adds 6 new demo technicians (2 each for Network Administrator, Cybersecurity
Specialist, and IT Support) to TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA, to cover
the ticket volume seen in the CTTC ticket tracker analysis:

    Network Administrator    -> Internet not working / going on-off / slow  (72 tickets)
    Cybersecurity Specialist -> Email trouble & phishing                    (42 tickets)
    IT Support                -> Device setup / buffering                    (25 tickets)

Run modes:
    python add_demo_technicians.py --inspect   # read-only: print current roster + schema
    python add_demo_technicians.py --insert    # insert the 6 new technicians
"""

import argparse

from config import SF_ACCOUNT, SF_USER, SF_PASSWORD, SF_AUTHENTICATOR, SF_DATABASE, SF_SCHEMA, SF_WAREHOUSE, SF_ROLE
from src.database.snowflake_db import SnowflakeConnection

TABLE = "TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA"

# Matches the exact conventions of the existing 6 rows (T001-T006):
# ROLE is always "Technician", SKILLS/SPECIALIZATIONS are plain comma-separated
# strings (not JSON), email is firstname.tech@gmail.com, password is Tech@0XX.
NEW_TECHNICIANS = [
    {
        "technician_id": "T007",
        "name": "Rohan",
        "email": "rohan.tech@gmail.com",
        "role": "Technician",
        "skills": "General IT Support, Networking, Router Configuration, ISP Escalation",
        "specializations": "Network Administration",
        "password": "Tech@007",
    },
    {
        "technician_id": "T008",
        "name": "Ananya",
        "email": "ananya.tech@gmail.com",
        "role": "Technician",
        "skills": "General IT Support, Networking, Wi-Fi, DNS",
        "specializations": "Network Administration",
        "password": "Tech@008",
    },
    {
        "technician_id": "T009",
        "name": "Karan",
        "email": "karan.tech@gmail.com",
        "role": "Technician",
        "skills": "General IT Support, Security, Phishing Response, Account Compromise",
        "specializations": "Cybersecurity Support",
        "password": "Tech@009",
    },
    {
        "technician_id": "T010",
        "name": "Ishita",
        "email": "ishita.tech@gmail.com",
        "role": "Technician",
        "skills": "General IT Support, Security, Email Security, Threat Detection",
        "specializations": "Cybersecurity Support",
        "password": "Tech@010",
    },
    {
        "technician_id": "T011",
        "name": "Devansh",
        "email": "devansh.tech@gmail.com",
        "role": "Technician",
        "skills": "General IT Support, Hardware, Device Setup, User Training",
        "specializations": "IT Support",
        "password": "Tech@011",
    },
    {
        "technician_id": "T012",
        "name": "Simran",
        "email": "simran.tech@gmail.com",
        "role": "Technician",
        "skills": "General IT Support, Hardware, Software, Streaming/Buffering Troubleshooting",
        "specializations": "IT Support",
        "password": "Tech@012",
    },
]


def connect() -> SnowflakeConnection:
    return SnowflakeConnection(
        sf_account=SF_ACCOUNT,
        sf_user=SF_USER,
        sf_warehouse=SF_WAREHOUSE,
        sf_database=SF_DATABASE,
        sf_schema=SF_SCHEMA,
        sf_role=SF_ROLE,
        sf_password=SF_PASSWORD,
        sf_authenticator=SF_AUTHENTICATOR,
    )


def inspect(conn: SnowflakeConnection):
    cur = conn.conn.cursor()
    cur.execute(f"SELECT * FROM {TABLE} ORDER BY TECHNICIAN_ID")
    cols = [c[0] for c in cur.description]
    print("Columns:", cols)
    rows = cur.fetchall()
    print(f"\n{len(rows)} existing technicians:")
    for row in rows:
        print(dict(zip(cols, row)))
    cur.close()


def insert(conn: SnowflakeConnection):
    cur = conn.conn.cursor()

    cur.execute(f"SELECT TECHNICIAN_ID FROM {TABLE}")
    existing_ids = {r[0] for r in cur.fetchall()}

    insert_sql = f"""
        INSERT INTO {TABLE}
            (TECHNICIAN_ID, NAME, EMAIL, ROLE, SKILLS, CURRENT_WORKLOAD, SPECIALIZATIONS, TECHNICIAN_PASSWORD)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    inserted = []
    for tech in NEW_TECHNICIANS:
        if tech["technician_id"] in existing_ids:
            print(f"Skipping {tech['technician_id']} ({tech['name']}) - already exists")
            continue
        cur.execute(
            insert_sql,
            (
                tech["technician_id"],
                tech["name"],
                tech["email"],
                tech["role"],
                tech["skills"],
                0,
                tech["specializations"],
                tech["password"],
            ),
        )
        inserted.append(tech)
        print(f"Inserted {tech['technician_id']} - {tech['name']} ({tech['role']})")

    conn.conn.commit()
    cur.close()
    print(f"\nDone. Inserted {len(inserted)}/{len(NEW_TECHNICIANS)} technicians.")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true", help="Read-only: print current roster and schema")
    group.add_argument("--insert", action="store_true", help="Insert the 6 new demo technicians")
    args = parser.parse_args()

    conn = connect()
    if not conn.conn:
        print("Failed to connect to Snowflake.")
        return

    try:
        if args.inspect:
            inspect(conn)
        elif args.insert:
            insert(conn)
    finally:
        conn.conn.close()


if __name__ == "__main__":
    main()
