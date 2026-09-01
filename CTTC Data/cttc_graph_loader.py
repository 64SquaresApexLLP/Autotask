#!/usr/bin/env python3
"""
cttc_graph_loader.py — build and load the CTTC network ontology into Neo4j.

Two modes:

  --demo          Generate a synthetic-but-faithful CTTC topology from the facts
                  recorded in the Wavsys assessment (device models, counts,
                  software releases, named defects) and load it. Identifiers,
                  port names, circuit IDs and subscriber records are placeholders.

  --csv-dir DIR   Load real exports instead. Expects devices.csv, ports.csv,
                  links.csv, pon.csv, onts.csv, services.csv, subscribers.csv.
                  Column names are documented in CSV_SCHEMA below.

Either mode can also write the dataset to JSON (--export-json) for the
standalone HTML explorer, with no database involved.

Usage:
  python cttc_graph_loader.py --demo --export-json cttc.json
  python cttc_graph_loader.py --demo --uri bolt://localhost:7687 --user neo4j --password secret --wipe
  python cttc_graph_loader.py --csv-dir ./exports --uri neo4j+s://xxx.databases.neo4j.io --user neo4j --password secret

Requires: neo4j>=5.0  (only when actually loading; JSON export has no deps)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --------------------------------------------------------------------------
# Facts taken from the Wavsys CTTC standing review, 18 May 2026.
# Everything else in this file is placeholder data shaped to match.
# --------------------------------------------------------------------------

OBSERVED = datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc)
INCIDENT_AT = datetime(2026, 5, 14, 3, 12, tzinfo=timezone.utc)

SOFTWARE = [
    # id,                      vendor,    train,      release,        approved
    ("sw:junos-24.4R1-S3.6", "Juniper", "24.4", "24.4R1-S3.6", True),
    ("sw:junos-23.4R2", "Juniper", "23.4", "23.4R2", True),
    ("sw:junos-22.4R3-S7.5", "Juniper", "22.4", "22.4R3-S7.5", True),
    ("sw:junos-22.3R3", "Juniper", "22.3", "22.3R3", False),
    ("sw:junos-21.4R3", "Juniper", "21.4", "21.4R3", False),
    ("sw:exa-3.4.70.88", "Calix", "EXA 3.4", "3.4.70.88", True),
    ("sw:axos-R26.1.0", "Calix", "AXOS R26", "R26.1.0", True),
    ("sw:ont-25.4.0.0.39", "Calix", "ONT 25.4", "25.4.0.0.39", True),
]

DEFECTS = [
    ("def:evpn-qinq", "VLAN-in-VLAN over EVPN affects cell-tower circuits",
     "high", None, "case:jnpr-evpn-qinq", "Juniper", "open"),
    ("def:acx-234-locker", "Junos 23.4 breaks Locker and CO AP services on ACX 5448D",
     "high", None, None, None, None),
    ("def:zr-thermal", "400G ZR optic thermal behaviour; vendor-mandated image response",
     "medium", "24.4R1-S3.6", None, None, None),
]

# defect -> the software releases that CONTAIN it. Note the direction: the ACX
# regression lives in 23.4, which is why the fleet is still on 22.4; and the
# EVPN defect lives in 23.4R2, which San Angelo was downgraded away from — but
# which the rest of the MX304 fleet is still running.
DEFECT_AFFECTS = {
    "def:evpn-qinq": ["sw:junos-23.4R2"],
    "def:acx-234-locker": ["sw:junos-23.4R2"],
    "def:zr-thermal": [],                # fixed in the release the core now runs
}

# Counts straight from the assessment
N_MX304 = 9
N_ACX = 40
N_XG801 = 29
N_EXA = 4                                # "mature EXA fleet" — count not stated
STRAGGLER_ACX = ["dev:acx-gldt-a", "dev:acx-sang-a"]

CSV_SCHEMA = """
devices.csv     id,name,vendor,model,role,serial,mgmt_ip,site_id,software_release,aliases
ports.csv       id,name,device_id,speed_gbps,role,admin_state,oper_state
links.csv       id,a_port_id,z_port_id,type,capacity_gbps,protection_role
pon.csv         id,olt_port_id,split_ratio,ont_count,technology
onts.csv        id,serial,model,firmware,pon_id,rx_dbm,subscriber_id
services.csv    id,circuit_id,class,bandwidth_mbps,state,subscriber_id,path_ports
subscribers.csv id,account,premise_id,service_area,criticality
""".strip()


# --------------------------------------------------------------------------
# Dataset container
# --------------------------------------------------------------------------

class Dataset:
    def __init__(self):
        self.nodes: list[dict] = []
        self.rels: list[dict] = []
        self._seen: set[str] = set()

    def node(self, node_id: str, labels: list[str], **props):
        if node_id in self._seen:
            return node_id
        self._seen.add(node_id)
        self.nodes.append({"id": node_id, "labels": labels, "props": props})
        return node_id

    def rel(self, start: str, rtype: str, end: str, *, source="inventory_review",
            method="vendor_export", observed_at=None, valid_from=None,
            valid_to=None, confidence=1.0, **props):
        props.update({
            "source": source,
            "method": method,
            "observed_at": (observed_at or OBSERVED).isoformat(),
            "valid_from": (valid_from or OBSERVED).isoformat(),
            "valid_to": valid_to.isoformat() if valid_to else None,
            "confidence": confidence,
        })
        self.rels.append({"start": start, "type": rtype, "end": end, "props": props})

    def summary(self) -> dict:
        by_label = defaultdict(int)
        for n in self.nodes:
            by_label[n["labels"][0]] += 1
        by_type = defaultdict(int)
        for r in self.rels:
            by_type[r["type"]] += 1
        return {"nodes": len(self.nodes), "relationships": len(self.rels),
                "by_label": dict(sorted(by_label.items())),
                "by_type": dict(sorted(by_type.items()))}


# --------------------------------------------------------------------------
# Demo topology generator
# --------------------------------------------------------------------------

def build_demo(seed: int = 518) -> Dataset:
    rnd = random.Random(seed)
    d = Dataset()

    # --- software, defects, vendor cases -----------------------------------
    for sid, vendor, train, release, approved in SOFTWARE:
        d.node(sid, ["SoftwareVersion"], vendor=vendor, train=train,
               release=release, approved=approved)

    for did, symptom, severity, fixed_in, case_id, case_vendor, case_status in DEFECTS:
        d.node(did, ["KnownDefect"], symptom=symptom, severity=severity,
               fixed_in=fixed_in)
        if case_id:
            d.node(case_id, ["VendorCase"], vendor=case_vendor, status=case_status,
                   note="lab testing in progress", case_number="<pending>")
            d.rel(did, "TRACKED_BY", case_id, source="vendor_portal")
        for sw in DEFECT_AFFECTS[did]:
            d.rel(sw, "AFFECTED_BY", did, source="vendor_bulletin", method="manual")

    # --- sites --------------------------------------------------------------
    sites = [("site:gldt", "Goldthwaite", "central_office"),
             ("site:sang", "San Angelo", "aggregation_site")]
    for i in range(3, 11):
        sites.append((f"site:{i:02d}", f"Service Area {i:02d}", "remote_site"))
    for sid, name, stype in sites:
        d.node(sid, ["Site"], name=name, type=stype,
               aliases=[name, sid.split(":")[1].upper()])

    site_ids = [s[0] for s in sites]

    def add_device(dev_id, name, model, vendor, role, site, sw, extra_labels=(),
                   aliases=None):
        d.node(dev_id, ["Device", *extra_labels], name=name, model=model,
               vendor=vendor, role=role, serial=f"SN{rnd.randrange(10**7, 10**8)}",
               mgmt_ip=f"10.{rnd.randrange(40, 60)}.{rnd.randrange(1, 250)}.{rnd.randrange(2, 250)}",
               aliases=aliases or [name])
        d.rel(site, "CONTAINS", dev_id)
        d.rel(dev_id, "RUNS", sw, method="vendor_export")
        return dev_id

    def add_ports(dev_id, prefix, count, speed, role):
        out = []
        for i in range(count):
            pid = f"port:{dev_id.split(':')[1]}:{prefix}{i}"
            d.node(pid, ["Port"], name=f"{prefix}{i}", speed_gbps=speed, role=role,
                   admin_state="up", oper_state="up")
            d.rel(dev_id, "HAS_PORT", pid, method="config_parse", source="config_backup")
            out.append(pid)
        return out

    def add_link(a, z, ltype, capacity, protection="none"):
        lid = f"link:{a.split(':',1)[1]}--{z.split(':',1)[1]}"
        d.node(lid, ["Link"], type=ltype, capacity_gbps=capacity,
               protection_role=protection)
        d.rel(a, "TERMINATES", lid, link_end="a", method="lldp", source="nms")
        d.rel(z, "TERMINATES", lid, link_end="z", method="lldp", source="nms")
        return lid

    # --- the core -----------------------------------------------------------
    core = add_device("dev:mx960-gldt", "GLDT-CORE-01", "MX960", "Juniper", "core",
                      "site:gldt", "sw:junos-24.4R1-S3.6",
                      extra_labels=["Router", "Juniper"],
                      aliases=["MX960", "Goldthwaite core", "GLDT-CORE-01"])
    core_ports = add_ports(core, "et-0/0/", 12, 400, "aggregation_facing")
    for p in core_ports[:2]:
        oid = f"opt:{p.split(':',1)[1]}"
        d.node(oid, ["Optic"], form_factor="QSFP-DD", part_number="400G-ZR",
               wavelength_nm=1550, rx_dbm=round(rnd.uniform(-9, -6), 1),
               temp_c=round(rnd.uniform(52, 68), 1))
        d.rel(p, "HOSTS", oid, source="telemetry", method="snmp")

    # --- aggregation: 9 x MX304, San Angelo on the downgraded release -------
    mx304 = []
    for i in range(1, N_MX304 + 1):
        is_sang = (i == 1)
        dev_id = "dev:mx304-sang" if is_sang else f"dev:mx304-{i:02d}"
        name = "SANG-AGG-01" if is_sang else f"AGG-{i:02d}"
        site = "site:sang" if is_sang else site_ids[(i % 8) + 2]
        sw = "sw:junos-22.3R3" if is_sang else "sw:junos-23.4R2"
        dev = add_device(dev_id, name, "MX304", "Juniper", "aggregation", site, sw,
                         extra_labels=["Router", "Juniper"],
                         aliases=[name, "San Angelo MX304"] if is_sang else [name])
        ports = add_ports(dev, "et-0/0/", 4, 100, "uplink")
        ports += add_ports(dev, "xe-0/1/", 8, 10, "access_facing")
        add_link(ports[0], core_ports[(i - 1) % len(core_ports)], "fiber", 100,
                 "protected" if not is_sang else "unprotected")
        mx304.append((dev, ports))

    # the San Angelo downgrade, recorded as a change motivated by the defect
    d.node("chg:sang-downgrade", ["Change"], method="software_downgrade",
           outcome="completed", window_start=(OBSERVED - timedelta(days=40)).isoformat(),
           window_end=(OBSERVED - timedelta(days=40, hours=-4)).isoformat())
    d.rel("chg:sang-downgrade", "TARGETS", "dev:mx304-sang", source="change_record")
    d.rel("chg:sang-downgrade", "MOTIVATED_BY", "def:evpn-qinq", source="change_record")

    # the fleet-wide ACX upgrade attempt that was rolled back
    d.node("chg:acx-234-attempt", ["Change"], method="software_upgrade",
           outcome="rolled_back",
           window_start=(OBSERVED - timedelta(days=61)).isoformat(),
           window_end=(OBSERVED - timedelta(days=61, hours=-6)).isoformat())
    d.rel("chg:acx-234-attempt", "MOTIVATED_BY", "def:acx-234-locker",
          source="change_record")

    # --- access: 40 x ACX 5448D, two of them two trains back ----------------
    acx = []
    for i in range(1, N_ACX + 1):
        if i == 1:
            dev_id, name, site = "dev:acx-gldt-a", "GLDT-A", "site:gldt"
        elif i == 2:
            dev_id, name, site = "dev:acx-sang-a", "San Angelo-A", "site:sang"
        else:
            dev_id, name = f"dev:acx-{i:02d}", f"ACX-{i:02d}"
            site = site_ids[(i % 8) + 2]
        sw = "sw:junos-21.4R3" if dev_id in STRAGGLER_ACX else "sw:junos-22.4R3-S7.5"
        dev = add_device(dev_id, name, "ACX 5448D", "Juniper", "access", site, sw,
                         extra_labels=["AccessNode", "Juniper"],
                         aliases=[name, dev_id.split(":")[1].upper()])
        ports = add_ports(dev, "et-0/0/", 2, 100, "uplink")
        ports += add_ports(dev, "xe-0/0/", 4, 10, "access_facing")
        parent = mx304[(i - 1) % N_MX304] if dev_id != "dev:acx-sang-a" else mx304[0]
        add_link(ports[0], parent[1][4 + (i % 8)], "fiber", 10, "unprotected")
        d.rel("chg:acx-234-attempt", "TARGETS", dev, source="change_record")
        acx.append((dev, ports, site))

    # --- Calix access: XGS-PON plus the legacy EXA estate -------------------
    olts, pons = [], []
    for i in range(1, N_XG801 + 1):
        parent_acx = acx[(i * 3) % len(acx)]
        dev = add_device(f"dev:olt-xg{i:02d}", f"OLT-XG-{i:02d}", "E7-2 XG801",
                         "Calix", "olt", parent_acx[2], "sw:axos-R26.1.0",
                         extra_labels=["OLT", "Calix"])
        up = add_ports(dev, "x1/", 2, 10, "uplink")
        pon_ports = add_ports(dev, "p1/", 4, 10, "pon")
        add_link(up[0], parent_acx[1][2 + (i % 4)], "fiber", 10, "unprotected")
        for j, pp in enumerate(pon_ports):
            pid = f"pon:{dev.split(':')[1]}-{j}"
            ont_count = rnd.randrange(18, 60)
            d.node(pid, ["PONTree"], split_ratio=64, ont_count=ont_count,
                   utilization_pct=round(100 * ont_count / 64, 1),
                   technology="XGS-PON")
            d.rel(pp, "SERVES", pid, source="calix_export")
            sp = f"spl:{pid.split(':')[1]}"
            d.node(sp, ["Splitter"], ratio="1:64", location="distribution")
            d.rel(pid, "FEEDS", sp, source="osp_records", method="manual",
                  confidence=0.8)
            pons.append((pid, sp, dev, pp, ont_count))
        olts.append(dev)

    for i in range(1, N_EXA + 1):
        parent_acx = acx[(i * 7) % len(acx)]
        add_device(f"dev:olt-exa{i:02d}", f"OLT-EXA-{i:02d}",
                   "E7-2" if i % 2 else "E7-20", "Calix", "olt",
                   parent_acx[2], "sw:exa-3.4.70.88",
                   extra_labels=["OLT", "Calix"])

    # --- the Calix ERPS management ring -------------------------------------
    d.node("prot:erps-mgmt", ["ProtectionGroup"], type="ERPS", ring_speed_gbps=10,
           last_validated=None, note="dedicated 10G management ring")
    for i, o in enumerate(olts):
        d.rel("prot:erps-mgmt", "PROTECTS", o, source="config_backup",
              method="config_parse")

    # --- ONTs: individually modelled for two PONs only ----------------------
    incident_pon = next(p for p in pons if p[2] == "dev:olt-xg01")
    sample_pon = pons[7]
    detailed_onts = []
    for pon_tuple, n_detail in ((incident_pon, 28), (sample_pon, 32)):
        pid, sp, dev, pp, _ = pon_tuple
        for k in range(n_detail):
            oid = f"ont:{pid.split(':')[1]}-{k:02d}"
            d.node(oid, ["ONT"], serial=f"CXNK{rnd.randrange(10**7, 10**8)}",
                   model="GP1100X", firmware="25.4.0.0.39",
                   rx_dbm=round(rnd.uniform(-24.5, -17.0), 1))
            d.rel(sp, "FEEDS", oid, splitter_port=k, source="calix_export")
            sub = f"sub:{oid.split(':')[1]}"
            d.node(sub, ["Subscriber"], account=f"ACCT-{rnd.randrange(10000, 99999)}",
                   premise_id=f"PR-{rnd.randrange(1000, 9999)}",
                   service_area="San Angelo" if pon_tuple is incident_pon else "Area 04",
                   criticality="standard")
            d.rel(oid, "SERVES", sub, source="billing", method="export")
            detailed_onts.append((oid, sub, pid))

    # --- services: cell backhaul, business, residential ---------------------
    def add_service(svc_id, circuit, sclass, bw, path_ports, sub_id,
                    drifted=False, drift_port=None):
        d.node(svc_id, ["Service"], circuit_id=circuit, **{"class": sclass},
               bandwidth_mbps=bw, state="active")
        d.rel(svc_id, "DELIVERED_TO", sub_id, source="billing")
        for kind in ("intended", "current"):
            path_id = f"path:{svc_id.split(':')[1]}-{kind}"
            hops = list(path_ports)
            protected = True
            if kind == "current" and drifted and drift_port:
                # the service has failed over onto a different, unprotected uplink
                hops[1] = drift_port
                protected = False
            d.node(path_id, ["ServicePath"], kind=kind, hop_count=len(hops),
                   computed_at=OBSERVED.isoformat(), protected=protected)
            d.rel(svc_id, "REALIZED_BY", path_id, source="derived", method="computed")
            for seq, port in enumerate(hops):
                d.rel(path_id, "TRAVERSES", port, seq=seq, direction="a_to_z",
                      source="derived", method="computed")

    sang_dev, sang_ports = mx304[0]
    for i in range(6):
        sub = f"sub:tower-{i:02d}"
        d.node(sub, ["Subscriber"], account=f"TOWER-{i:02d}", premise_id=f"TWR-{i:02d}",
               service_area="San Angelo", criticality="critical")
        add_service(f"svc:cell-{i:02d}", f"CTTC-CELL-{1000 + i}", "cell_backhaul",
                    10000, [sang_ports[4 + i], sang_ports[0],
                            core_ports[i % len(core_ports)]], sub,
                    drifted=(i in (1, 4)), drift_port=sang_ports[2])

    for i in range(8):
        dev, ports = mx304[(i % (N_MX304 - 1)) + 1]
        sub = f"sub:biz-{i:02d}"
        d.node(sub, ["Subscriber"], account=f"BIZ-{i:02d}", premise_id=f"BZ-{i:02d}",
               service_area=f"Area {(i % 8) + 3:02d}", criticality="high")
        add_service(f"svc:biz-{i:02d}", f"CTTC-EVPL-{2000 + i}", "business_ethernet",
                    1000, [ports[4 + (i % 8)], ports[0],
                           core_ports[(i + 3) % len(core_ports)]], sub,
                    drifted=(i == 2), drift_port=ports[2])

    for k, (oid, sub, pid) in enumerate(detailed_onts[:10]):
        olt_dev = next(p[2] for p in pons if p[0] == pid)
        olt_up = f"port:{olt_dev.split(':')[1]}:x1/0"
        add_service(f"svc:res-{k:02d}", f"CTTC-RES-{3000 + k}", "residential",
                    1000, [olt_up, core_ports[k % len(core_ports)]], sub)

    # --- the incident: 28 ONTs down, uplink errors 90 seconds earlier -------
    inc_pid = incident_pon[0]
    inc_olt = incident_pon[2]
    uplink = f"port:{inc_olt.split(':')[1]}:x1/0"
    d.node("alm:uplink-fec", ["Alarm"], type="FEC_ERRORS_HIGH", severity="minor",
           raised_at=(INCIDENT_AT - timedelta(seconds=90)).isoformat(),
           cleared_at=None, raw_text="Uplink FEC corrected-error rate above threshold")
    d.rel("alm:uplink-fec", "RAISED_BY", uplink, source="nms", method="snmp_trap")

    for oid, sub, pid in detailed_onts:
        if pid != inc_pid:
            continue
        aid = f"alm:{oid.split(':')[1]}"
        d.node(aid, ["Alarm"], type="ONT_UNREACHABLE", severity="major",
               raised_at=(INCIDENT_AT + timedelta(seconds=rnd.randrange(0, 240))).isoformat(),
               cleared_at=None, raw_text="ONT lost management connectivity")
        d.rel(aid, "RAISED_BY", oid, source="nms", method="snmp_trap")

    d.node("tkt:inc-2026-0514", ["Ticket"], severity="major",
           opened_at=(INCIDENT_AT + timedelta(minutes=6)).isoformat(),
           summary="Multiple ONT outages, San Angelo footprint", root_cause=None)
    d.rel("alm:uplink-fec", "OPENED_AS", "tkt:inc-2026-0514", source="ticketing")

    return d


# --------------------------------------------------------------------------
# CSV loader (for when the real exports arrive)
# --------------------------------------------------------------------------

def build_from_csv(path: str) -> Dataset:
    d = Dataset()

    def read(name):
        f = os.path.join(path, name)
        if not os.path.exists(f):
            print(f"  ! {name} not found — skipping", file=sys.stderr)
            return []
        with open(f, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    for row in read("devices.csv"):
        aliases = [a.strip() for a in (row.get("aliases") or "").split("|") if a.strip()]
        d.node(row["id"], ["Device"], name=row["name"], vendor=row.get("vendor"),
               model=row.get("model"), role=row.get("role"), serial=row.get("serial"),
               mgmt_ip=row.get("mgmt_ip"), aliases=aliases or [row["name"]])
        if row.get("site_id"):
            d.rel(row["site_id"], "CONTAINS", row["id"], source="inventory_csv")
        if row.get("software_release"):
            sw = f"sw:{row['software_release']}"
            d.node(sw, ["SoftwareVersion"], release=row["software_release"],
                   vendor=row.get("vendor"))
            d.rel(row["id"], "RUNS", sw, source="inventory_csv")

    for row in read("ports.csv"):
        d.node(row["id"], ["Port"], name=row["name"],
               speed_gbps=_num(row.get("speed_gbps")), role=row.get("role"),
               admin_state=row.get("admin_state"), oper_state=row.get("oper_state"))
        d.rel(row["device_id"], "HAS_PORT", row["id"], source="config_csv")

    for row in read("links.csv"):
        d.node(row["id"], ["Link"], type=row.get("type"),
               capacity_gbps=_num(row.get("capacity_gbps")),
               protection_role=row.get("protection_role"))
        d.rel(row["a_port_id"], "TERMINATES", row["id"], link_end="a", source="config_csv")
        d.rel(row["z_port_id"], "TERMINATES", row["id"], link_end="z", source="config_csv")

    for row in read("pon.csv"):
        d.node(row["id"], ["PONTree"], split_ratio=_num(row.get("split_ratio")),
               ont_count=_num(row.get("ont_count")), technology=row.get("technology"))
        d.rel(row["olt_port_id"], "SERVES", row["id"], source="calix_csv")

    for row in read("onts.csv"):
        d.node(row["id"], ["ONT"], serial=row.get("serial"), model=row.get("model"),
               firmware=row.get("firmware"), rx_dbm=_num(row.get("rx_dbm")))
        d.rel(row["pon_id"], "FEEDS", row["id"], source="calix_csv")
        if row.get("subscriber_id"):
            d.rel(row["id"], "SERVES", row["subscriber_id"], source="billing_csv")

    for row in read("subscribers.csv"):
        d.node(row["id"], ["Subscriber"], account=row.get("account"),
               premise_id=row.get("premise_id"), service_area=row.get("service_area"),
               criticality=row.get("criticality"))

    for row in read("services.csv"):
        d.node(row["id"], ["Service"], circuit_id=row.get("circuit_id"),
               **{"class": row.get("class")},
               bandwidth_mbps=_num(row.get("bandwidth_mbps")), state=row.get("state"))
        if row.get("subscriber_id"):
            d.rel(row["id"], "DELIVERED_TO", row["subscriber_id"], source="billing_csv")
        ports = [p for p in (row.get("path_ports") or "").split("|") if p]
        if ports:
            pid = f"path:{row['id'].split(':')[-1]}-current"
            d.node(pid, ["ServicePath"], kind="current", hop_count=len(ports),
                   computed_at=OBSERVED.isoformat())
            d.rel(row["id"], "REALIZED_BY", pid, source="derived")
            for seq, port in enumerate(ports):
                d.rel(pid, "TRAVERSES", port, seq=seq, source="derived")

    return d


def _num(v):
    if v in (None, ""):
        return None
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


# --------------------------------------------------------------------------
# Neo4j load
# --------------------------------------------------------------------------

CONSTRAINTS = [
    "CREATE CONSTRAINT site_id IF NOT EXISTS FOR (n:Site) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (n:Device) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT port_id IF NOT EXISTS FOR (n:Port) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT link_id IF NOT EXISTS FOR (n:Link) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT pon_id IF NOT EXISTS FOR (n:PONTree) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ont_id IF NOT EXISTS FOR (n:ONT) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT svc_id IF NOT EXISTS FOR (n:Service) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT path_id IF NOT EXISTS FOR (n:ServicePath) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT sub_id IF NOT EXISTS FOR (n:Subscriber) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT sw_id IF NOT EXISTS FOR (n:SoftwareVersion) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT def_id IF NOT EXISTS FOR (n:KnownDefect) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT case_id IF NOT EXISTS FOR (n:VendorCase) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT chg_id IF NOT EXISTS FOR (n:Change) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT alm_id IF NOT EXISTS FOR (n:Alarm) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT tkt_id IF NOT EXISTS FOR (n:Ticket) REQUIRE n.id IS UNIQUE",
    "CREATE INDEX device_model IF NOT EXISTS FOR (n:Device) ON (n.model)",
    "CREATE INDEX device_role IF NOT EXISTS FOR (n:Device) ON (n.role)",
    "CREATE INDEX port_role IF NOT EXISTS FOR (n:Port) ON (n.role)",
    "CREATE INDEX alarm_raised IF NOT EXISTS FOR (n:Alarm) ON (n.raised_at)",
    "CREATE FULLTEXT INDEX entity_alias IF NOT EXISTS "
    "FOR (n:Device|Site|Service|Subscriber|ONT) ON EACH [n.name, n.aliases]",
]

VERIFY = [
    ("Node counts by label",
     "MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS n "
     "ORDER BY n DESC LIMIT 15"),
    ("Version drift — devices off their model's dominant release",
     """MATCH (d:Device)-[run:RUNS]->(v:SoftwareVersion)
        WHERE run.valid_to IS NULL
        WITH d.model AS model, v.release AS release, collect(d.name) AS devices
        ORDER BY size(devices) DESC
        WITH model, collect({release: release, devices: devices}) AS byRelease
        WITH model, byRelease, head(byRelease).release AS dominant
        UNWIND byRelease AS entry
        WITH model, dominant, entry WHERE entry.release <> dominant
        RETURN model, dominant, entry.release AS outlier, entry.devices AS devices"""),
    ("Defect blast radius — services on hardware with an open defect",
     """MATCH (d:Device)-[run:RUNS]->(v:SoftwareVersion)-[:AFFECTED_BY]->(k:KnownDefect)
        WHERE run.valid_to IS NULL
        MATCH (d)-[:HAS_PORT]->(p:Port)<-[:TRAVERSES]-(path:ServicePath {kind:'current'})
        MATCH (svc:Service)-[:REALIZED_BY]->(path)
        OPTIONAL MATCH (svc)-[:DELIVERED_TO]->(sub:Subscriber)
        RETURN d.name AS device, v.release AS running, k.symptom AS defect,
               count(DISTINCT svc) AS services, count(DISTINCT sub) AS subscribers
        ORDER BY subscribers DESC"""),
    ("Fault-domain candidate — PONs with an alarm cluster in the window",
     """MATCH (a:Alarm)-[:RAISED_BY]->(o:ONT)
        WHERE a.cleared_at IS NULL
        MATCH (pon:PONTree)-[:FEEDS*1..2]->(o)
        MATCH (pp:Port)-[:SERVES]->(pon)<-[:SERVES]-(pp)
        WITH pon, count(DISTINCT o) AS onts_down
        WHERE onts_down >= 5
        RETURN pon.id AS pon, onts_down ORDER BY onts_down DESC"""),
]


def load_neo4j(ds: Dataset, uri: str, user: str, password: str,
               database: str = "neo4j", wipe: bool = False, batch: int = 5000):
    try:
        from neo4j import GraphDatabase
    except ImportError:
        sys.exit("neo4j driver not installed:  pip install neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session(database=database) as s:
        if wipe:
            print("· wiping database")
            s.run("MATCH (n) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS")

        print("· applying constraints and indexes")
        for stmt in CONSTRAINTS:
            s.run(stmt)

        by_labels = defaultdict(list)
        for n in ds.nodes:
            by_labels[tuple(n["labels"])].append({"id": n["id"], "props": n["props"]})
        for labels, rows in by_labels.items():
            lbl = ":".join(labels)
            for i in range(0, len(rows), batch):
                s.run(f"UNWIND $rows AS row MERGE (n:{lbl} {{id: row.id}}) "
                      f"SET n += row.props", rows=rows[i:i + batch])
            print(f"· {len(rows):>6} :{lbl}")

        by_type = defaultdict(list)
        for r in ds.rels:
            by_type[r["type"]].append(r)
        for rtype, rows in by_type.items():
            payload = [{"s": r["start"], "e": r["end"], "props": r["props"]} for r in rows]
            for i in range(0, len(payload), batch):
                s.run(f"UNWIND $rows AS row "
                      f"MATCH (a {{id: row.s}}), (b {{id: row.e}}) "
                      f"MERGE (a)-[r:{rtype}]->(b) SET r += row.props",
                      rows=payload[i:i + batch])
            print(f"· {len(rows):>6} -[:{rtype}]->")

    driver.close()
    print("· load complete")


def verify_neo4j(uri, user, password, database="neo4j"):
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session(database=database) as s:
        for title, q in VERIFY:
            print(f"\n─── {title} " + "─" * max(0, 60 - len(title)))
            try:
                for rec in s.run(q):
                    print("   ", dict(rec))
            except Exception as exc:                      # noqa: BLE001
                print("    query failed:", exc)
    driver.close()


# --------------------------------------------------------------------------
# JSON export for the HTML explorer
# --------------------------------------------------------------------------

def export_json(ds: Dataset, path: str):
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Wavsys CTTC standing review 18 May 2026 (facts); "
                  "identifiers and counts below device level are placeholders",
        "summary": ds.summary(),
        "nodes": ds.nodes,
        "rels": ds.rels,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    size = os.path.getsize(path) / 1024
    print(f"· wrote {path} ({size:.0f} KB)")


def build_from_json(path: str) -> Dataset:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    ds = Dataset()
    ds.nodes = data.get("nodes", [])
    ds.rels = data.get("rels", [])
    ds._seen = {n["id"] for n in ds.nodes}
    return ds


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=False)
    src.add_argument("--demo", action="store_true",
                     help="generate the synthetic CTTC topology")
    src.add_argument("--csv-dir", help="directory of real exports (see --csv-schema)")
    src.add_argument("--json-file", help="path to JSON export to load (e.g. data/cttc.json)")
    ap.add_argument("--csv-schema", action="store_true", help="print expected CSV columns and exit")
    ap.add_argument("--uri", default=os.environ.get("NEO4J_URI", "neo4j+s://d9abf684.databases.neo4j.io"), help="bolt:// or neo4j+s:// URI")
    ap.add_argument("--user", default=os.environ.get("NEO4J_USERNAME", "d9abf684"))
    ap.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "RUE6xAmUCT8gc3PCmsv0mZwOuDMJujJeEcsPAIa8yho"))
    ap.add_argument("--database", default=os.environ.get("NEO4J_DATABASE", "d9abf684"))
    ap.add_argument("--wipe", action="store_true", default=True, help="DETACH DELETE everything first")
    ap.add_argument("--export-json", help="write the dataset to JSON for the HTML explorer")
    ap.add_argument("--verify", action="store_true", default=True, help="run verification queries after load")
    ap.add_argument("--seed", type=int, default=518)
    args = ap.parse_args()

    if args.csv_schema:
        print(CSV_SCHEMA)
        return

    if args.json_file:
        ds = build_from_json(args.json_file)
    elif args.csv_dir:
        ds = build_from_csv(args.csv_dir)
    elif os.path.exists("data/cttc.json"):
        ds = build_from_json("data/cttc.json")
    else:
        ds = build_demo(args.seed)
    s = ds.summary()
    print(f"· dataset: {s['nodes']} nodes, {s['relationships']} relationships")
    for label, n in s["by_label"].items():
        print(f"    {n:>6}  {label}")

    if args.export_json:
        export_json(ds, args.export_json)

    if args.uri:
        if not args.password:
            sys.exit("--password or NEO4J_PASSWORD required to load")
        load_neo4j(ds, args.uri, args.user, args.password, args.database, args.wipe)
        if args.verify:
            verify_neo4j(args.uri, args.user, args.password, args.database)
    elif not args.export_json:
        print("· nothing to do — pass --uri to load, or --export-json to write a file")


if __name__ == "__main__":
    main()
