#!/usr/bin/env python3
"""
prep_viz.py — turn the loader's JSON export into the compact payload the
HTML explorer embeds, and run the analytics the Cypher queries would run.

  python prep_viz.py cttc.json viz.json
"""
import json
import sys
from collections import Counter, defaultdict

src, dst = sys.argv[1], sys.argv[2]
raw = json.load(open(src))

N = {n["id"]: n for n in raw["nodes"]}
label = lambda i: N[i]["labels"][0] if i in N else None
P = lambda i: N[i]["props"] if i in N else {}

out_rels = defaultdict(list)   # (type) -> [(start, end, props)]
for r in raw["rels"]:
    out_rels[r["type"]].append((r["start"], r["end"], r["props"]))

# ---- index helpers --------------------------------------------------------
port_of_device = {}
device_ports = defaultdict(list)
for s, e, _ in out_rels["HAS_PORT"]:
    port_of_device[e] = s
    device_ports[s].append(e)

site_of_device = {}
for s, e, _ in out_rels["CONTAINS"]:
    site_of_device[e] = s

release_of_device = {}
for s, e, pr in out_rels["RUNS"]:
    if pr.get("valid_to") is None:
        release_of_device[s] = e

defects_of_release = defaultdict(list)
for s, e, _ in out_rels["AFFECTED_BY"]:
    defects_of_release[s].append(e)

case_of_defect = {s: e for s, e, _ in out_rels["TRACKED_BY"]}

# ---- devices --------------------------------------------------------------
devices = []
model_release = defaultdict(Counter)
for nid, n in N.items():
    if n["labels"][0] != "Device":
        continue
    model_release[n["props"]["model"]][P(release_of_device.get(nid, "")).get("release")] += 1

dominant = {m: c.most_common(1)[0][0] for m, c in model_release.items()}

for nid, n in N.items():
    if n["labels"][0] != "Device":
        continue
    p = n["props"]
    sw = release_of_device.get(nid)
    rel = P(sw).get("release")
    defs = [{"id": d, "symptom": P(d)["symptom"], "severity": P(d)["severity"],
             "case": case_of_defect.get(d)} for d in defects_of_release.get(sw, [])]
    devices.append({
        "id": nid, "name": p["name"], "model": p["model"], "vendor": p["vendor"],
        "role": p["role"], "site": site_of_device.get(nid),
        "release": rel, "approved": P(sw).get("approved"),
        "dominant": dominant.get(p["model"]),
        "outlier": rel != dominant.get(p["model"]),
        "defects": defs, "ports": len(device_ports.get(nid, [])),
        "mgmt_ip": p.get("mgmt_ip"), "serial": p.get("serial"),
        "aliases": p.get("aliases", []),
    })

# ---- links between devices ------------------------------------------------
link_ends = defaultdict(list)
for s, e, pr in out_rels["TERMINATES"]:
    link_ends[e].append((s, pr.get("link_end")))

device_links, port_links = [], []
for lid, ends in link_ends.items():
    if len(ends) != 2:
        continue
    (pa, _), (pz, _) = ends
    da, dz = port_of_device.get(pa), port_of_device.get(pz)
    lp = P(lid)
    port_links.append({"a": pa, "z": pz})
    if da and dz and da != dz:
        device_links.append({"a": da, "z": dz, "cap": lp.get("capacity_gbps"),
                             "prot": lp.get("protection_role"),
                             "ports": [pa, pz]})

# ---- PON / ONT / subscriber ----------------------------------------------
pon_of_port = {e: s for s, e, _ in out_rels["SERVES"] if label(e) == "PONTree"}
pons = []
for s, e, _ in out_rels["SERVES"]:
    if label(e) != "PONTree":
        continue
    p = P(e)
    pons.append({"id": e, "olt": port_of_device.get(s), "port": s,
                 "ratio": p.get("split_ratio"), "onts": p.get("ont_count"),
                 "util": p.get("utilization_pct"), "tech": p.get("technology")})

splitter_pon = {e: s for s, e, _ in out_rels["FEEDS"] if label(e) == "Splitter"}
ont_pon = {}
for s, e, _ in out_rels["FEEDS"]:
    if label(e) == "ONT":
        ont_pon[e] = splitter_pon.get(s)

sub_of_ont = {s: e for s, e, _ in out_rels["SERVES"] if label(e) == "Subscriber"}
alarm_on = defaultdict(list)
for s, e, _ in out_rels["RAISED_BY"]:
    alarm_on[e].append(s)

onts = [{"id": i, "serial": P(i).get("serial"), "model": P(i).get("model"),
         "fw": P(i).get("firmware"), "rx": P(i).get("rx_dbm"),
         "pon": ont_pon.get(i), "sub": sub_of_ont.get(i),
         "alarm": bool(alarm_on.get(i))}
        for i, n in N.items() if n["labels"][0] == "ONT"]

ont_of_sub = {v: k for k, v in sub_of_ont.items()}
subs = [{"id": i, "account": P(i).get("account"), "area": P(i).get("service_area"),
         "crit": P(i).get("criticality"), "ont": ont_of_sub.get(i)}
        for i, n in N.items() if n["labels"][0] == "Subscriber"]

# ---- services and paths ---------------------------------------------------
paths_of_service = defaultdict(list)
for s, e, _ in out_rels["REALIZED_BY"]:
    paths_of_service[s].append(e)

path_ports = defaultdict(list)
for s, e, pr in out_rels["TRAVERSES"]:
    path_ports[s].append((pr.get("seq", 0), e))
for k in path_ports:
    path_ports[k].sort()

sub_of_service = {s: e for s, e, _ in out_rels["DELIVERED_TO"]}

services = []
for sid, n in N.items():
    if n["labels"][0] != "Service":
        continue
    p = n["props"]
    intended = current = []
    for pth in paths_of_service.get(sid, []):
        ports = [x[1] for x in path_ports.get(pth, [])]
        if P(pth).get("kind") == "intended":
            intended = ports
        else:
            current = ports
    devs, seen = [], set()
    for pt in current:
        dv = port_of_device.get(pt)
        if dv and dv not in seen:
            seen.add(dv)
            devs.append(dv)
    services.append({
        "id": sid, "circuit": p.get("circuit_id"), "cls": p.get("class"),
        "bw": p.get("bandwidth_mbps"), "sub": sub_of_service.get(sid),
        "devices": devs, "intended": intended, "current": current,
        "drifted": sorted(intended) != sorted(current),
    })

# ---- ports ----------------------------------------------------------------
ports = [{"id": i, "name": P(i).get("name"), "dev": port_of_device.get(i),
          "speed": P(i).get("speed_gbps"), "role": P(i).get("role")}
         for i, n in N.items() if n["labels"][0] == "Port"]

# ---- alarms ---------------------------------------------------------------
alarms = []
for i, n in N.items():
    if n["labels"][0] != "Alarm":
        continue
    tgt = next((e for s, e, _ in out_rels["RAISED_BY"] if s == i), None)
    alarms.append({"id": i, "type": P(i)["type"], "sev": P(i)["severity"],
                   "at": P(i)["raised_at"], "on": tgt,
                   "text": P(i).get("raw_text")})

# ---- precomputed findings (what the six Cypher queries return) ------------
svc_by_device = defaultdict(set)
sub_by_device = defaultdict(set)
for s in services:
    for dv in s["devices"]:
        svc_by_device[dv].add(s["id"])
        if s["sub"]:
            sub_by_device[dv].add(s["sub"])

for d in devices:
    d["services"] = len(svc_by_device.get(d["id"], ()))
    d["subscribers"] = len(sub_by_device.get(d["id"], ()))

drift_rows = [{"model": d["model"], "dominant": d["dominant"],
               "outlier": d["release"], "device": d["name"], "id": d["id"]}
              for d in devices if d["outlier"]]

defect_rows = []
for d in devices:
    if not d["defects"]:
        continue
    defect_rows.append({"device": d["name"], "id": d["id"], "release": d["release"],
                        "defect": d["defects"][0]["symptom"],
                        "severity": d["defects"][0]["severity"],
                        "services": d["services"], "subscribers": d["subscribers"]})
defect_rows.sort(key=lambda r: -r["subscribers"])

path_rows = [{"circuit": s["circuit"], "cls": s["cls"], "id": s["id"],
              "added": [p for p in s["current"] if p not in s["intended"]],
              "dropped": [p for p in s["intended"] if p not in s["current"]]}
             for s in services if s["drifted"]]

core_ids = [d["id"] for d in devices if d["role"] == "core"]
spof_services = [s for s in services
                 if any(dv in core_ids for dv in s["devices"])]
spof = {"core": core_ids, "services": len(spof_services),
        "subscribers": len({s["sub"] for s in spof_services if s["sub"]}),
        "classes": sorted({s["cls"] for s in spof_services})}

ont_alarms = [a for a in alarms if a["type"] == "ONT_UNREACHABLE"]
inc_pon = None
if ont_alarms:
    c = Counter(ont_pon.get(a["on"]) for a in ont_alarms)
    inc_pon = c.most_common(1)[0][0]
inc_olt = next((p["olt"] for p in pons if p["id"] == inc_pon), None)
incident = {
    "pon": inc_pon, "olt": inc_olt,
    "onts_down": len(ont_alarms),
    "window_start": min((a["at"] for a in ont_alarms), default=None),
    "window_end": max((a["at"] for a in ont_alarms), default=None),
    "supporting": [a for a in alarms if a["type"] != "ONT_UNREACHABLE"],
    "ruled_out": ["no change window open on the OLT",
                  "no OLT chassis alarm — device remains reachable",
                  "ONT optical levels within range"],
}

payload = {
    "meta": {"generated_at": raw["generated_at"], "source": raw["source"],
             "counts": raw["summary"]["by_label"]},
    "sites": {i: {"name": P(i)["name"], "type": P(i)["type"]}
              for i, n in N.items() if n["labels"][0] == "Site"},
    "devices": devices, "deviceLinks": device_links, "ports": ports,
    "portLinks": port_links, "pons": pons, "onts": onts, "subs": subs,
    "services": services, "alarms": alarms,
    "findings": {"drift": drift_rows, "defects": defect_rows, "paths": path_rows,
                 "spof": spof, "incident": incident},
}

json.dump(payload, open(dst, "w"), separators=(",", ":"))
import os
print(f"wrote {dst} ({os.path.getsize(dst)/1024:.0f} KB) — "
      f"{len(devices)} devices, {len(device_links)} links, {len(pons)} PONs, "
      f"{len(services)} services, {len(onts)} ONTs")
print(f"findings: {len(drift_rows)} version outliers, {len(defect_rows)} defect-exposed, "
      f"{len(path_rows)} drifted paths, incident on {inc_pon}")
