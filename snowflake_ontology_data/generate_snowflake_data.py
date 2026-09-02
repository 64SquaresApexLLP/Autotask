import os
import sys
import json
import csv
from datetime import datetime

# Windows console encoding fix
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTTC_DATA_DIR = os.path.join(BASE_DIR, "CTTC Data", "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "snowflake_ontology_data")

os.makedirs(OUTPUT_DIR, exist_ok=True)

CTTC_JSON_PATH = os.path.join(CTTC_DATA_DIR, "cttc.json")
VIZ_JSON_PATH = os.path.join(CTTC_DATA_DIR, "viz.json")

print(f"[+] Reading data from {CTTC_DATA_DIR}...")

with open(CTTC_JSON_PATH, "r", encoding="utf-8") as f:
    cttc_data = json.load(f)

with open(VIZ_JSON_PATH, "r", encoding="utf-8") as f:
    viz_data = json.load(f)

nodes = cttc_data.get("nodes", [])
rels = cttc_data.get("relationships", []) or cttc_data.get("rels", [])
viz_devices = {d["id"]: d for d in viz_data.get("devices", [])}
viz_sites = viz_data.get("sites", {})
findings = viz_data.get("findings", {})
incident = viz_data.get("incident", {})

print(f"📊 Loaded {len(nodes)} nodes, {len(rels)} relationships, {len(viz_devices)} devices, {len(viz_sites)} sites.")

# ----------------------------------------------------
# 1. DIM_SITES
# ----------------------------------------------------
sites_rows = []
for s_id, s_info in viz_sites.items():
    sites_rows.append({
        "SITE_ID": s_id,
        "SITE_NAME": s_info.get("name", ""),
        "SITE_TYPE": s_info.get("type", "central_office"),
        "COUNTY": s_info.get("county", "Mills County"),
        "STATE": s_info.get("state", "Texas"),
        "LATITUDE": s_info.get("lat"),
        "LONGITUDE": s_info.get("lon"),
        "ALTITUDE_METERS": s_info.get("alt_m") or s_info.get("altitude_meters"),
        "ALTITUDE_FEET": s_info.get("alt_ft") or s_info.get("altitude_feet"),
        "REGION": "Texas, USA",
        "STATUS": "ACTIVE",
        "CREATED_AT": datetime.utcnow().isoformat()
    })

# Add any sites from cttc.json nodes
for n in nodes:
    if "Site" in n.get("labels", []) or n.get("id", "").startswith("site:"):
        s_id = n.get("id")
        if not any(r["SITE_ID"] == s_id for r in sites_rows):
            p = n.get("props", {})
            sites_rows.append({
                "SITE_ID": s_id,
                "SITE_NAME": p.get("name", s_id.replace("site:", "").upper()),
                "SITE_TYPE": p.get("type", "aggregation_site"),
                "COUNTY": p.get("county", "Mills County"),
                "STATE": p.get("state", "Texas"),
                "LATITUDE": p.get("lat"),
                "LONGITUDE": p.get("lon"),
                "ALTITUDE_METERS": p.get("alt_m") or p.get("altitude_meters"),
                "ALTITUDE_FEET": p.get("alt_ft") or p.get("altitude_feet"),
                "REGION": "Texas, USA",
                "STATUS": "ACTIVE",
                "CREATED_AT": datetime.utcnow().isoformat()
            })

# ----------------------------------------------------
# 2. DIM_NETWORK_DEVICES
# ----------------------------------------------------
devices_rows = []
for n in nodes:
    labels = n.get("labels", [])
    n_id = n.get("id", "")
    p = n.get("props", {})

    if any(l in ["Device", "Router", "Switch", "OLT", "ONT", "Splitter"] for l in labels) or n_id.startswith("dev:"):
        v_dev = viz_devices.get(n_id, {})
        role = p.get("role") or v_dev.get("role") or ("core" if "mx960" in n_id else "aggregation" if "mx304" in n_id else "access")
        vendor = p.get("vendor") or v_dev.get("vendor") or ("Juniper" if "mx" in n_id or "acx" in n_id else "Calix" if "olt" in n_id else "Cisco")
        model = p.get("model") or v_dev.get("model") or ("MX960" if "mx960" in n_id else "MX304" if "mx304" in n_id else "ACX7100" if "acx" in n_id else "E7-2")
        site_id = p.get("site") or v_dev.get("site") or ("site:gldt" if "gldt" in n_id else "site:sang" if "sang" in n_id else "site:austin")
        release = p.get("release") or v_dev.get("release") or ("24.4R1-S3.6" if role == "core" else "22.4R3-S7.5")
        
        is_approved = v_dev.get("approved", True) if v_dev else (release != "23.4R2" and release != "22.3R3")
        is_outlier = v_dev.get("outlier", False) if v_dev else (release in ["22.3R3", "21.4R3"])
        
        defects = v_dev.get("defects", []) if v_dev else ([{"id": "def:evpn-qinq", "severity": "critical"}] if release == "23.4R2" else [])
        
        devices_rows.append({
            "DEVICE_ID": n_id,
            "DEVICE_NAME": p.get("name") or v_dev.get("name") or n_id.replace("dev:", "").upper(),
            "VENDOR": vendor,
            "MODEL": model,
            "ROLE": role,
            "SITE_ID": site_id,
            "MANAGEMENT_IP": p.get("mgmt_ip") or v_dev.get("mgmt_ip") or f"10.54.{len(devices_rows)+1}.1",
            "SOFTWARE_RELEASE": release,
            "IS_APPROVED_TRAIN": is_approved,
            "IS_VERSION_DRIFT_OUTLIER": is_outlier,
            "ACTIVE_DEFECTS_COUNT": len(defects),
            "DEFECTS_JSON": json.dumps(defects),
            "SERVICES_COUNT": v_dev.get("services", p.get("services_count", 8)),
            "SUBSCRIBERS_COUNT": v_dev.get("subscribers", p.get("subscribers_count", 24)),
            "OPER_STATUS": "WARNING" if len(defects) > 0 or is_outlier else "ONLINE",
            "LAST_AUDITED_AT": datetime.utcnow().isoformat()
        })

# ----------------------------------------------------
# 3. DIM_PORTS
# ----------------------------------------------------
ports_rows = []
for n in nodes:
    if "Port" in n.get("labels", []) or n.get("id", "").startswith("port:"):
        p_id = n.get("id", "")
        props = n.get("props", {})
        # Extract device id from port id (port:mx304-01:et-0/0/0)
        parts = p_id.replace("port:", "").split(":")
        dev_id = f"dev:{parts[0]}" if len(parts) > 1 else ""
        port_name = parts[1] if len(parts) > 1 else parts[0]

        speed = props.get("speed_gbps") or (100 if "et-" in port_name else 10 if "xe-" in port_name else 1)
        ports_rows.append({
            "PORT_ID": p_id,
            "DEVICE_ID": dev_id,
            "PORT_NAME": props.get("name", port_name),
            "SPEED_GBPS": speed,
            "OPER_STATE": props.get("oper_state", "up"),
            "ADMIN_STATE": props.get("admin_state", "up"),
            "OPTIC_TYPE": props.get("optic_type", "100G-LR4" if speed == 100 else "10G-SR"),
            "OPTIC_TEMP_C": props.get("optic_temp_c", 38.5)
        })

# ----------------------------------------------------
# 4. FACT_TOPOLOGY_LINKS
# ----------------------------------------------------
links_rows = []
for idx, r in enumerate(rels):
    r_type = r.get("type", "CONNECTED_TO")
    s_id = r.get("start") or r.get("source") or ""
    t_id = r.get("end") or r.get("target") or ""
    p = r.get("props") or r.get("properties") or {}

    prot_role = p.get("protection_role") or p.get("prot") or ("unprotected" if "sang" in s_id or "sang" in t_id else "protected")
    speed = p.get("speed_gbps") or (100 if "100g" in str(r).lower() or "et-" in s_id else 10)

    links_rows.append({
        "LINK_ID": r.get("id") or f"link-{idx+1}",
        "SOURCE_NODE_ID": s_id,
        "TARGET_NODE_ID": t_id,
        "RELATIONSHIP_TYPE": r_type,
        "SPEED_GBPS": speed,
        "PROTECTION_ROLE": prot_role,
        "IS_SPOF_RISK": True if prot_role == "unprotected" and "sang" in s_id else False,
        "LINK_STATUS": "UP",
        "PROPERTIES_JSON": json.dumps(p)
    })

# ----------------------------------------------------
# 5. DIM_SERVICES & CIRCUITS
# ----------------------------------------------------
services_rows = []
for n in nodes:
    if "Service" in n.get("labels", []) or "Circuit" in n.get("labels", []) or n.get("id", "").startswith("srv:"):
        p = n.get("props", {})
        s_id = n.get("id")
        services_rows.append({
            "SERVICE_ID": s_id,
            "SERVICE_NAME": p.get("name", s_id.replace("srv:", "").upper()),
            "SERVICE_TYPE": p.get("type", "Cell-Backhaul EVPN" if "cell" in s_id else "Enterprise DIA 10G"),
            "BANDWIDTH_MBPS": p.get("bandwidth_mbps", 10000),
            "SLA_TIER": p.get("sla_tier", "Gold (99.99%)"),
            "DELIVERED_SUBSCRIBER_ID": p.get("subscriber_id", f"sub:cust-{len(services_rows)+1:03d}"),
            "STATUS": "DEGRADED" if "23.4r2" in str(n).lower() else "HEALTHY",
            "CREATED_AT": datetime.utcnow().isoformat()
        })

# ----------------------------------------------------
# 6. DIM_SUBSCRIBERS
# ----------------------------------------------------
subscribers_rows = []
for n in nodes:
    if "Subscriber" in n.get("labels", []) or n.get("id", "").startswith("sub:"):
        p = n.get("props", {})
        sub_id = n.get("id")
        subscribers_rows.append({
            "SUBSCRIBER_ID": sub_id,
            "SUBSCRIBER_NAME": p.get("name", f"Account #{sub_id.replace('sub:', '')}"),
            "ACCOUNT_TYPE": p.get("account_type", "Wholesale Carrier" if "cell" in sub_id else "Commercial Enterprise"),
            "PRIMARY_SITE_ID": p.get("site_id", "site:gldt"),
            "ACTIVE_CIRCUITS_COUNT": p.get("circuits_count", 1),
            "MONTHLY_RECURRING_REVENUE_USD": p.get("mrr", 3500.00),
            "STATUS": "ACTIVE"
        })

# ----------------------------------------------------
# 7. DIM_KNOWN_DEFECTS
# ----------------------------------------------------
defects_rows = [
    {
        "DEFECT_ID": "def:evpn-qinq",
        "TITLE": "EVPN QinQ VLAN-in-VLAN Drop Under Load",
        "VENDOR": "Juniper Networks",
        "AFFECTED_RELEASES": "23.4R2, 23.4R2-S1",
        "SEVERITY": "CRITICAL (P1)",
        "JIRA_CASE_NUMBER": "case:jnpr-evpn-qinq",
        "SYMPTOM_DESCRIPTION": "VLAN-in-VLAN over EVPN drops packets when aggregation gateway encounters microburst traffic.",
        "RECOMMENDED_REMEDY": "Upgrade fleet to Junos 24.4R1-S3.6 or apply temporary QinQ encapsulation filter policy.",
        "TOTAL_AFFECTED_DEVICES": 8,
        "TOTAL_IMPACTED_SERVICES": 8
    },
    {
        "DEFECT_ID": "spof:sang-100g",
        "TITLE": "Single Point of Failure (SPOF) - Unprotected San Angelo Trunk",
        "VENDOR": "CTTC Network Architecture",
        "AFFECTED_RELEASES": "All (Physical Topology)",
        "SEVERITY": "HIGH (P2)",
        "JIRA_CASE_NUMBER": "N/A (Topology Risk)",
        "SYMPTOM_DESCRIPTION": "San Angelo CO is connected via a single 100G link without ERPS protection ring.",
        "RECOMMENDED_REMEDY": "Deploy secondary 100G fiber trunk via Brady to complete ERPS ring.",
        "TOTAL_AFFECTED_DEVICES": 3,
        "TOTAL_IMPACTED_SERVICES": 12
    },
    {
        "DEFECT_ID": "drift:fleet-outliers",
        "TITLE": "Software Train Outliers (Version Drift)",
        "VENDOR": "Juniper Networks / Fleet Baseline",
        "AFFECTED_RELEASES": "22.3R3, 21.4R3",
        "SEVERITY": "MEDIUM (P3)",
        "JIRA_CASE_NUMBER": "N/A (Fleet Hygiene)",
        "SYMPTOM_DESCRIPTION": "2 devices run deprecated Junos releases (22.3R3 / 21.4R3) that miss critical security patches.",
        "RECOMMENDED_REMEDY": "Schedule maintenance window to align to approved 22.4R3-S7.5 baseline.",
        "TOTAL_AFFECTED_DEVICES": 2,
        "TOTAL_IMPACTED_SERVICES": 4
    },
    {
        "DEFECT_ID": "alarm:gldt-optical",
        "TITLE": "Goldthwaite Central Office 400G ZR Optic Temp Cascade",
        "VENDOR": "Optics / Coherent Transceiver",
        "AFFECTED_RELEASES": "Hardware ZR+",
        "SEVERITY": "HIGH (P2)",
        "JIRA_CASE_NUMBER": "ticket:alm-4902",
        "SYMPTOM_DESCRIPTION": "400G ZR optic temp reached 60.2°C causing optical power degradation and BGP neighbor flapping.",
        "RECOMMENDED_REMEDY": "Replace optic transceiver and verify fan tray airflow.",
        "TOTAL_AFFECTED_DEVICES": 3,
        "TOTAL_IMPACTED_SERVICES": 24
    }
]

# ----------------------------------------------------
# 8. FACT_INCIDENTS_TICKETS (AutoTask Integration)
# ----------------------------------------------------
incidents_rows = [
    {
        "TICKET_NUMBER": "INC-2026-0941",
        "TITLE": "Cell-Tower Backhaul Packet Drops on AGG-02",
        "CATEGORY": "Hardware",
        "PRIORITY": "Critical",
        "STATUS": "Open",
        "AFFECTED_DEVICE_ID": "dev:mx304-02",
        "ASSOCIATED_DEFECT_ID": "def:evpn-qinq",
        "BLAST_RADIUS_DEVICES_COUNT": 8,
        "IMPACTED_SERVICES_COUNT": 8,
        "ASSIGNED_TECHNICIAN": "Ruchir Chincholkar",
        "CREATED_AT": datetime.utcnow().isoformat(),
        "RESOLUTION_SUMMARY": "Identified Junos 23.4R2 EVPN QinQ defect. Scheduled software upgrade to 24.4R1-S3.6."
    },
    {
        "TICKET_NUMBER": "INC-2026-0942",
        "TITLE": "Unprotected 100G Trunk Risk - San Angelo Aggregation",
        "CATEGORY": "Network",
        "PRIORITY": "High",
        "STATUS": "In Progress",
        "AFFECTED_DEVICE_ID": "dev:mx304-sang",
        "ASSOCIATED_DEFECT_ID": "spof:sang-100g",
        "BLAST_RADIUS_DEVICES_COUNT": 3,
        "IMPACTED_SERVICES_COUNT": 12,
        "ASSIGNED_TECHNICIAN": "Anant Lad",
        "CREATED_AT": datetime.utcnow().isoformat(),
        "RESOLUTION_SUMMARY": "Engineering ticket submitted for secondary diverse fiber path."
    },
    {
        "TICKET_NUMBER": "INC-2026-0943",
        "TITLE": "Version Drift Remediation - SANG-AGG-01 & ACX-19",
        "CATEGORY": "Software",
        "PRIORITY": "Medium",
        "STATUS": "Open",
        "AFFECTED_DEVICE_ID": "dev:mx304-sang",
        "ASSOCIATED_DEFECT_ID": "drift:fleet-outliers",
        "BLAST_RADIUS_DEVICES_COUNT": 2,
        "IMPACTED_SERVICES_COUNT": 4,
        "ASSIGNED_TECHNICIAN": "Support Technician",
        "CREATED_AT": datetime.utcnow().isoformat(),
        "RESOLUTION_SUMMARY": "Staging 22.4R3-S7.5 golden image for scheduled maintenance."
    },
    {
        "TICKET_NUMBER": "INC-2026-0944",
        "TITLE": "High Temp Alarm on 400G ZR Optic - GLDT-CORE-01",
        "CATEGORY": "Hardware",
        "PRIORITY": "High",
        "STATUS": "Open",
        "AFFECTED_DEVICE_ID": "dev:mx960-gldt",
        "ASSOCIATED_DEFECT_ID": "alarm:gldt-optical",
        "BLAST_RADIUS_DEVICES_COUNT": 3,
        "IMPACTED_SERVICES_COUNT": 24,
        "ASSIGNED_TECHNICIAN": "Ruchir Chincholkar",
        "CREATED_AT": datetime.utcnow().isoformat(),
        "RESOLUTION_SUMMARY": "Technician dispatched to replace optic transceiver."
    }
]

# ----------------------------------------------------
# 9. FACT_GRAPH_KNOWLEDGE_EDGES (Full Graph in VARIANT)
# ----------------------------------------------------
graph_edges_rows = []
for idx, r in enumerate(rels):
    graph_edges_rows.append({
        "EDGE_ID": r.get("id", f"edge-{idx+1}"),
        "SOURCE_ID": r.get("start") or r.get("source") or "",
        "TARGET_ID": r.get("end") or r.get("target") or "",
        "REL_TYPE": r.get("type", "CONNECTED"),
        "PROPERTIES_VARIANT": json.dumps(r.get("props") or r.get("properties") or {}),
        "INGESTED_AT": datetime.utcnow().isoformat()
    })

# ----------------------------------------------------
# 10. ADMIN_USERS (Enterprise Administrator Accounts)
# ----------------------------------------------------
admin_users_rows = [
    {
        "ADMIN_ID": "adm-001",
        "USERNAME": "admin",
        "EMAIL": "admin@64-squares.com",
        "FULL_NAME": "System Administrator",
        "ROLE": "super_admin",
        "PERMISSIONS_SCOPE": "ALL_SYSTEMS,USER_MGMT,TECH_SCHEDULES,REPORTS,ONTOLOGY",
        "STATUS": "ACTIVE",
        "CREATED_AT": datetime.now().isoformat()
    },
    {
        "ADMIN_ID": "adm-002",
        "USERNAME": "noc_lead",
        "EMAIL": "noc.lead@teamlogic.com",
        "FULL_NAME": "NOC Operations Lead",
        "ROLE": "admin",
        "PERMISSIONS_SCOPE": "TECH_SCHEDULES,REPORTS,ONTOLOGY,TICKET_MGMT",
        "STATUS": "ACTIVE",
        "CREATED_AT": datetime.now().isoformat()
    }
]

# ----------------------------------------------------
# 11. DIM_TECHNICIAN_SHIFTS_SKILLS (Technician Roster, Shifts & Skills)
# ----------------------------------------------------
technician_shifts_rows = [
    {
        "TECHNICIAN_ID": "tech-001",
        "USERNAME": "tech",
        "FULL_NAME": "Demo Technician",
        "EMAIL": "tech@example.com",
        "PHONE_NUMBER": "+1-555-0199",
        "PRIMARY_SHIFT": "Morning (08:00 - 16:00)",
        "ON_CALL_STATUS": "Active",
        "SKILL_SETS": "Network Routing & EVPN, Optical & Fiber Trunks, Hardware Diagnostics",
        "EXPERIENCE_LEVEL": "Senior L2",
        "STATUS": "ACTIVE",
        "CURRENT_TICKETS_LOAD": 4,
        "MAX_CAPACITY": 10
    },
    {
        "TECHNICIAN_ID": "tech-002",
        "USERNAME": "tech1",
        "FULL_NAME": "Alex Smith",
        "EMAIL": "tech1@example.com",
        "PHONE_NUMBER": "+1-555-0248",
        "PRIMARY_SHIFT": "Afternoon (14:00 - 22:00)",
        "ON_CALL_STATUS": "Standby",
        "SKILL_SETS": "Software & OS Drift, Active Directory, Server Infrastructure",
        "EXPERIENCE_LEVEL": "L2 Specialist",
        "STATUS": "ACTIVE",
        "CURRENT_TICKETS_LOAD": 3,
        "MAX_CAPACITY": 10
    },
    {
        "TECHNICIAN_ID": "tech-003",
        "USERNAME": "technician",
        "FULL_NAME": "Support Technician",
        "EMAIL": "technician@example.com",
        "PHONE_NUMBER": "+1-555-0312",
        "PRIMARY_SHIFT": "Night (22:00 - 06:00)",
        "ON_CALL_STATUS": "Active",
        "SKILL_SETS": "VoIP & Central Office AP, Optical Transceivers, Emergency Triage",
        "EXPERIENCE_LEVEL": "Senior L3",
        "STATUS": "ACTIVE",
        "CURRENT_TICKETS_LOAD": 5,
        "MAX_CAPACITY": 12
    },
    {
        "TECHNICIAN_ID": "tech-004",
        "USERNAME": "tech_anant",
        "FULL_NAME": "Anant Lad (Technician)",
        "EMAIL": "anant.lad@64-squares.com",
        "PHONE_NUMBER": "+1-555-0450",
        "PRIMARY_SHIFT": "Morning (08:00 - 16:00)",
        "ON_CALL_STATUS": "Standby",
        "SKILL_SETS": "Network Routing & EVPN, Core MX960 Architecture, Cloud Infrastructure",
        "EXPERIENCE_LEVEL": "Principal Architect",
        "STATUS": "ACTIVE",
        "CURRENT_TICKETS_LOAD": 2,
        "MAX_CAPACITY": 8
    }
]

# Helper function to write CSV
def write_csv(filename, fieldnames, data):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ Generated {filename} ({len(data)} rows)")

write_csv("DIM_SITES.csv", ["SITE_ID", "SITE_NAME", "SITE_TYPE", "COUNTY", "STATE", "LATITUDE", "LONGITUDE", "ALTITUDE_METERS", "ALTITUDE_FEET", "REGION", "STATUS", "CREATED_AT"], sites_rows)
write_csv("DIM_NETWORK_DEVICES.csv", ["DEVICE_ID", "DEVICE_NAME", "VENDOR", "MODEL", "ROLE", "SITE_ID", "MANAGEMENT_IP", "SOFTWARE_RELEASE", "IS_APPROVED_TRAIN", "IS_VERSION_DRIFT_OUTLIER", "ACTIVE_DEFECTS_COUNT", "DEFECTS_JSON", "SERVICES_COUNT", "SUBSCRIBERS_COUNT", "OPER_STATUS", "LAST_AUDITED_AT"], devices_rows)
write_csv("DIM_PORTS.csv", ["PORT_ID", "DEVICE_ID", "PORT_NAME", "SPEED_GBPS", "OPER_STATE", "ADMIN_STATE", "OPTIC_TYPE", "OPTIC_TEMP_C"], ports_rows)
write_csv("FACT_TOPOLOGY_LINKS.csv", ["LINK_ID", "SOURCE_NODE_ID", "TARGET_NODE_ID", "RELATIONSHIP_TYPE", "SPEED_GBPS", "PROTECTION_ROLE", "IS_SPOF_RISK", "LINK_STATUS", "PROPERTIES_JSON"], links_rows)
write_csv("DIM_SERVICES.csv", ["SERVICE_ID", "SERVICE_NAME", "SERVICE_TYPE", "BANDWIDTH_MBPS", "SLA_TIER", "DELIVERED_SUBSCRIBER_ID", "STATUS", "CREATED_AT"], services_rows)
write_csv("DIM_SUBSCRIBERS.csv", ["SUBSCRIBER_ID", "SUBSCRIBER_NAME", "ACCOUNT_TYPE", "PRIMARY_SITE_ID", "ACTIVE_CIRCUITS_COUNT", "MONTHLY_RECURRING_REVENUE_USD", "STATUS"], subscribers_rows)
write_csv("DIM_KNOWN_DEFECTS.csv", ["DEFECT_ID", "TITLE", "VENDOR", "AFFECTED_RELEASES", "SEVERITY", "JIRA_CASE_NUMBER", "SYMPTOM_DESCRIPTION", "RECOMMENDED_REMEDY", "TOTAL_AFFECTED_DEVICES", "TOTAL_IMPACTED_SERVICES"], defects_rows)
write_csv("FACT_INCIDENTS_TICKETS.csv", ["TICKET_NUMBER", "TITLE", "CATEGORY", "PRIORITY", "STATUS", "AFFECTED_DEVICE_ID", "ASSOCIATED_DEFECT_ID", "BLAST_RADIUS_DEVICES_COUNT", "IMPACTED_SERVICES_COUNT", "ASSIGNED_TECHNICIAN", "CREATED_AT", "RESOLUTION_SUMMARY"], incidents_rows)
write_csv("FACT_GRAPH_EDGES.csv", ["EDGE_ID", "SOURCE_ID", "TARGET_ID", "REL_TYPE", "PROPERTIES_VARIANT", "INGESTED_AT"], graph_edges_rows)
write_csv("ADMIN_USERS.csv", ["ADMIN_ID", "USERNAME", "EMAIL", "FULL_NAME", "ROLE", "PERMISSIONS_SCOPE", "STATUS", "CREATED_AT"], admin_users_rows)
write_csv("DIM_TECHNICIAN_SHIFTS_SKILLS.csv", ["TECHNICIAN_ID", "USERNAME", "FULL_NAME", "EMAIL", "PHONE_NUMBER", "PRIMARY_SHIFT", "ON_CALL_STATUS", "SKILL_SETS", "EXPERIENCE_LEVEL", "STATUS", "CURRENT_TICKETS_LOAD", "MAX_CAPACITY"], technician_shifts_rows)

# ----------------------------------------------------
# 10. GENERATE SNOWFLAKE DDL SCRIPT
# ----------------------------------------------------
ddl_content = """-- ==============================================================================
-- TEAMLOGIC AUTOTASK & CTTC NETWORK ONTOLOGY SNOWFLAKE DDL & INGESTION SCRIPT
-- Database: TEST_DB / AUTOTASK_DB
-- Schema: PUBLIC / NETWORK_ONTOLOGY
-- ==============================================================================

USE DATABASE TEST_DB;
USE SCHEMA PUBLIC;

-- 1. Create File Format for CSV Ingestion
CREATE OR REPLACE FILE FORMAT CSV_ONTOLOGY_FORMAT
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\\n'
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('NULL', 'null', '')
    EMPTY_FIELD_AS_NULL = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

-- 2. DIM_SITES (Central Offices & Aggregation Sites)
CREATE OR REPLACE TABLE DIM_SITES (
    SITE_ID VARCHAR(64) PRIMARY KEY,
    SITE_NAME VARCHAR(128) NOT NULL,
    SITE_TYPE VARCHAR(64),
    COUNTY VARCHAR(64),
    STATE VARCHAR(32) DEFAULT 'Texas',
    LATITUDE FLOAT,
    LONGITUDE FLOAT,
    ALTITUDE_METERS FLOAT,
    ALTITUDE_FEET FLOAT,
    REGION VARCHAR(64),
    STATUS VARCHAR(32) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 3. DIM_NETWORK_DEVICES (Routers, Switches, OLTs)
CREATE OR REPLACE TABLE DIM_NETWORK_DEVICES (
    DEVICE_ID VARCHAR(64) PRIMARY KEY,
    DEVICE_NAME VARCHAR(128) NOT NULL,
    VENDOR VARCHAR(64),
    MODEL VARCHAR(64),
    ROLE VARCHAR(64),
    SITE_ID VARCHAR(64) REFERENCES DIM_SITES(SITE_ID),
    MANAGEMENT_IP VARCHAR(64),
    SOFTWARE_RELEASE VARCHAR(64),
    IS_APPROVED_TRAIN BOOLEAN DEFAULT TRUE,
    IS_VERSION_DRIFT_OUTLIER BOOLEAN DEFAULT FALSE,
    ACTIVE_DEFECTS_COUNT NUMBER(4,0) DEFAULT 0,
    DEFECTS_JSON VARIANT,
    SERVICES_COUNT NUMBER(8,0) DEFAULT 0,
    SUBSCRIBERS_COUNT NUMBER(8,0) DEFAULT 0,
    OPER_STATUS VARCHAR(32) DEFAULT 'ONLINE',
    LAST_AUDITED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 4. DIM_PORTS (Physical Interfaces)
CREATE OR REPLACE TABLE DIM_PORTS (
    PORT_ID VARCHAR(128) PRIMARY KEY,
    DEVICE_ID VARCHAR(64) REFERENCES DIM_NETWORK_DEVICES(DEVICE_ID),
    PORT_NAME VARCHAR(64) NOT NULL,
    SPEED_GBPS NUMBER(8,2),
    OPER_STATE VARCHAR(32),
    ADMIN_STATE VARCHAR(32),
    OPTIC_TYPE VARCHAR(64),
    OPTIC_TEMP_C FLOAT
);

-- 5. FACT_TOPOLOGY_LINKS (Physical Trunks, Protected/Unprotected Links)
CREATE OR REPLACE TABLE FACT_TOPOLOGY_LINKS (
    LINK_ID VARCHAR(128) PRIMARY KEY,
    SOURCE_NODE_ID VARCHAR(128) NOT NULL,
    TARGET_NODE_ID VARCHAR(128) NOT NULL,
    RELATIONSHIP_TYPE VARCHAR(64) NOT NULL,
    SPEED_GBPS NUMBER(8,2),
    PROTECTION_ROLE VARCHAR(32) DEFAULT 'protected',
    IS_SPOF_RISK BOOLEAN DEFAULT FALSE,
    LINK_STATUS VARCHAR(32) DEFAULT 'UP',
    PROPERTIES_JSON VARIANT
);

-- 6. DIM_SERVICES (Customer Circuits & EVPN Paths)
CREATE OR REPLACE TABLE DIM_SERVICES (
    SERVICE_ID VARCHAR(128) PRIMARY KEY,
    SERVICE_NAME VARCHAR(128) NOT NULL,
    SERVICE_TYPE VARCHAR(64),
    BANDWIDTH_MBPS NUMBER(12,2),
    SLA_TIER VARCHAR(64),
    DELIVERED_SUBSCRIBER_ID VARCHAR(128),
    STATUS VARCHAR(32) DEFAULT 'HEALTHY',
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 7. DIM_SUBSCRIBERS (Accounts, Enterprises, Mobile Carriers)
CREATE OR REPLACE TABLE DIM_SUBSCRIBERS (
    SUBSCRIBER_ID VARCHAR(128) PRIMARY KEY,
    SUBSCRIBER_NAME VARCHAR(128) NOT NULL,
    ACCOUNT_TYPE VARCHAR(64),
    PRIMARY_SITE_ID VARCHAR(64),
    ACTIVE_CIRCUITS_COUNT NUMBER(6,0) DEFAULT 1,
    MONTHLY_RECURRING_REVENUE_USD NUMBER(12,2),
    STATUS VARCHAR(32) DEFAULT 'ACTIVE'
);

-- 8. DIM_KNOWN_DEFECTS (Vulnerabilities, CVEs, JIRA Cases)
CREATE OR REPLACE TABLE DIM_KNOWN_DEFECTS (
    DEFECT_ID VARCHAR(64) PRIMARY KEY,
    TITLE VARCHAR(256) NOT NULL,
    VENDOR VARCHAR(64),
    AFFECTED_RELEASES VARCHAR(128),
    SEVERITY VARCHAR(32),
    JIRA_CASE_NUMBER VARCHAR(64),
    SYMPTOM_DESCRIPTION VARCHAR(1024),
    RECOMMENDED_REMEDY VARCHAR(1024),
    TOTAL_AFFECTED_DEVICES NUMBER(6,0),
    TOTAL_IMPACTED_SERVICES NUMBER(6,0)
);

-- 9. FACT_INCIDENTS_TICKETS (AutoTask Operational Tickets)
CREATE OR REPLACE TABLE FACT_INCIDENTS_TICKETS (
    TICKET_NUMBER VARCHAR(64) PRIMARY KEY,
    TITLE VARCHAR(256) NOT NULL,
    CATEGORY VARCHAR(64),
    PRIORITY VARCHAR(32),
    STATUS VARCHAR(32),
    AFFECTED_DEVICE_ID VARCHAR(64) REFERENCES DIM_NETWORK_DEVICES(DEVICE_ID),
    ASSOCIATED_DEFECT_ID VARCHAR(64) REFERENCES DIM_KNOWN_DEFECTS(DEFECT_ID),
    BLAST_RADIUS_DEVICES_COUNT NUMBER(6,0) DEFAULT 0,
    IMPACTED_SERVICES_COUNT NUMBER(6,0) DEFAULT 0,
    ASSIGNED_TECHNICIAN VARCHAR(128),
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    RESOLUTION_SUMMARY VARCHAR(1024)
);

-- 10. FACT_GRAPH_EDGES (Knowledge Graph Store with VARIANT)
CREATE OR REPLACE TABLE FACT_GRAPH_EDGES (
    EDGE_ID VARCHAR(128) PRIMARY KEY,
    SOURCE_ID VARCHAR(128) NOT NULL,
    TARGET_ID VARCHAR(128) NOT NULL,
    REL_TYPE VARCHAR(64) NOT NULL,
    PROPERTIES_VARIANT VARIANT,
    INGESTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 11. ADMIN_USERS (Enterprise Administrator Accounts)
CREATE OR REPLACE TABLE ADMIN_USERS (
    ADMIN_ID VARCHAR(64) PRIMARY KEY,
    USERNAME VARCHAR(64) NOT NULL UNIQUE,
    EMAIL VARCHAR(128) NOT NULL,
    FULL_NAME VARCHAR(128),
    ROLE VARCHAR(32) DEFAULT 'admin',
    PERMISSIONS_SCOPE VARCHAR(512),
    STATUS VARCHAR(32) DEFAULT 'ACTIVE',
    CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 12. DIM_TECHNICIAN_SHIFTS_SKILLS (Technician Roster, Shifts & Skills)
CREATE OR REPLACE TABLE DIM_TECHNICIAN_SHIFTS_SKILLS (
    TECHNICIAN_ID VARCHAR(64) PRIMARY KEY,
    USERNAME VARCHAR(64) NOT NULL UNIQUE,
    FULL_NAME VARCHAR(128) NOT NULL,
    EMAIL VARCHAR(128),
    PHONE_NUMBER VARCHAR(64),
    PRIMARY_SHIFT VARCHAR(64) DEFAULT 'Morning (08:00 - 16:00)',
    ON_CALL_STATUS VARCHAR(32) DEFAULT 'Standby',
    SKILL_SETS VARCHAR(512),
    EXPERIENCE_LEVEL VARCHAR(64) DEFAULT 'L2 Specialist',
    STATUS VARCHAR(32) DEFAULT 'ACTIVE',
    CURRENT_TICKETS_LOAD NUMBER(4,0) DEFAULT 0,
    MAX_CAPACITY NUMBER(4,0) DEFAULT 10
);

-- ==============================================================================
-- INGESTION COMMANDS (Run after uploading CSV files to Snowflake Stage)
-- Example Stage: @ONTOLOGY_STAGE
-- ==============================================================================
-- COPY INTO DIM_SITES FROM @ONTOLOGY_STAGE/DIM_SITES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO DIM_NETWORK_DEVICES FROM @ONTOLOGY_STAGE/DIM_NETWORK_DEVICES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO DIM_PORTS FROM @ONTOLOGY_STAGE/DIM_PORTS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO FACT_TOPOLOGY_LINKS FROM @ONTOLOGY_STAGE/FACT_TOPOLOGY_LINKS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO DIM_SERVICES FROM @ONTOLOGY_STAGE/DIM_SERVICES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO DIM_SUBSCRIBERS FROM @ONTOLOGY_STAGE/DIM_SUBSCRIBERS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO DIM_KNOWN_DEFECTS FROM @ONTOLOGY_STAGE/DIM_KNOWN_DEFECTS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO FACT_INCIDENTS_TICKETS FROM @ONTOLOGY_STAGE/FACT_INCIDENTS_TICKETS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO FACT_GRAPH_EDGES FROM @ONTOLOGY_STAGE/FACT_GRAPH_EDGES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO ADMIN_USERS FROM @ONTOLOGY_STAGE/ADMIN_USERS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
-- COPY INTO DIM_TECHNICIAN_SHIFTS_SKILLS FROM @ONTOLOGY_STAGE/DIM_TECHNICIAN_SHIFTS_SKILLS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
"""

with open(os.path.join(OUTPUT_DIR, "SNOWFLAKE_SCHEMA_DDL.sql"), "w", encoding="utf-8") as f:
    f.write(ddl_content)
print("✅ Generated SNOWFLAKE_SCHEMA_DDL.sql")

# Generate README.md
readme_content = """# Snowflake Data Schema & Pipeline for AutoTask Network Ontology

This folder contains relational table exports and SQL DDL scripts generated from the **CTTC Network Ontology** datasets (`cttc.json` and `viz.json`), structured for **Snowflake Database** analytics and AutoTask integration.

---

## 📁 Included Files

| File | Description | Rows / Records |
| :--- | :--- | :--- |
| **`DIM_SITES.csv`** | Central offices, aggregation sites, coordinates, and operational status. | 5+ Sites |
| **`DIM_NETWORK_DEVICES.csv`** | Core, Aggregation, and Access routers with firmware release, defect count, and services delivered. | 83+ Devices |
| **`DIM_PORTS.csv`** | Physical interfaces, port speeds (10G/100G), optics, and operational state. | 1,000+ Ports |
| **`FACT_TOPOLOGY_LINKS.csv`** | Physical link trunks, protected/unprotected rings, and SPOF risk markers. | 1,511+ Links |
| **`DIM_SERVICES.csv`** | End-to-end customer circuits (Cell-Backhaul EVPN, DIA Enterprise). | 100+ Services |
| **`DIM_SUBSCRIBERS.csv`** | Enterprise accounts, wholesale mobile carriers, and delivered bandwidth. | 100+ Subscribers |
| **`DIM_KNOWN_DEFECTS.csv`** | Vendor bugs (EVPN QinQ), SPOF topology findings, and version drift outliers. | 4 Critical Findings |
| **`FACT_INCIDENTS_TICKETS.csv`**| Operational AutoTask incident tickets mapped to blast radius and affected devices. | Pre-linked Tickets |
| **`FACT_GRAPH_EDGES.csv`** | General knowledge graph edges with native Snowflake `VARIANT` properties. | 1,511 Edges |
| **`SNOWFLAKE_SCHEMA_DDL.sql`**| Complete SQL script with `CREATE TABLE`, Primary/Foreign keys, and `COPY INTO` commands. | Full Schema |
| **`generate_snowflake_data.py`**| Python pipeline script to regenerate or update CSVs from raw JSON anytime. | Pipeline Tool |

---

## 🚀 How to Ingest into Snowflake

1. **Run DDL**:
   Open Snowflake Worksheets and execute `SNOWFLAKE_SCHEMA_DDL.sql` to create all tables and file formats.

2. **Upload CSVs to Snowflake Stage**:
   ```sql
   PUT file://c:/Autotask/snowflake_ontology_data/*.csv @ONTOLOGY_STAGE AUTO_COMPRESS=FALSE;
   ```

3. **Copy into Tables**:
   ```sql
   COPY INTO DIM_SITES FROM @ONTOLOGY_STAGE/DIM_SITES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_NETWORK_DEVICES FROM @ONTOLOGY_STAGE/DIM_NETWORK_DEVICES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_PORTS FROM @ONTOLOGY_STAGE/DIM_PORTS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO FACT_TOPOLOGY_LINKS FROM @ONTOLOGY_STAGE/FACT_TOPOLOGY_LINKS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_SERVICES FROM @ONTOLOGY_STAGE/DIM_SERVICES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_SUBSCRIBERS FROM @ONTOLOGY_STAGE/DIM_SUBSCRIBERS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO DIM_KNOWN_DEFECTS FROM @ONTOLOGY_STAGE/DIM_KNOWN_DEFECTS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO FACT_INCIDENTS_TICKETS FROM @ONTOLOGY_STAGE/FACT_INCIDENTS_TICKETS.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   COPY INTO FACT_GRAPH_EDGES FROM @ONTOLOGY_STAGE/FACT_GRAPH_EDGES.csv FILE_FORMAT = (FORMAT_NAME = CSV_ONTOLOGY_FORMAT);
   ```

---

## 🔄 Re-generating Data
To re-extract or update the CSVs from fresh JSON source files:
```powershell
python c:\Autotask\snowflake_ontology_data\generate_snowflake_data.py
```
"""

with open(os.path.join(OUTPUT_DIR, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme_content)
print("✅ Generated README.md")

print(f"🎉 Successfully created all Snowflake tables and files in: {OUTPUT_DIR}")
