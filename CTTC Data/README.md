# CTTC network ontology — loader and explorer

Two scripts and one HTML page. Nothing here needs a running Neo4j to be useful;
the explorer is fully standalone.


## What's in this archive

```
cttc-network-ontology/
├─ README.md                        this file
├─ cttc_graph_loader.py             builds the graph, loads Neo4j, exports JSON
├─ prep_viz.py                      compiles the explorer payload + analytics
├─ cypher/
│  ├─ 01-constraints.cypher         constraints and indexes — run first
│  ├─ q1-fault-domain.cypher        narrow a fault domain from an alarm cluster
│  ├─ q2-defect-blast-radius.cypher services and subscribers on defect-affected software
│  ├─ q3-spof.cypher                services with no path around the core
│  ├─ q4-path-drift.cypher          intended vs. current path diff
│  ├─ q5-version-drift.cypher       fleet version drift and stragglers
│  └─ q6-utilities.cypher           alias resolution + topology as of an instant
├─ explorer/
│  └─ cttc-network-explorer.html    open in a browser — no server, no build step
├─ data/
│  ├─ cttc.json                     full graph export (nodes + relationships)
│  └─ viz.json                      compact payload the explorer embeds
└─ docs/
   ├─ artifacts.md                  links to the four companion pages
   └─ CTTC-Network-Ontology.pptx    two-slide summary, with speaker notes
```

Open `explorer/cttc-network-explorer.html` directly in any browser to see the
graph — it needs nothing installed.

## Files

| File | What it does |
|---|---|
| `cttc_graph_loader.py` | Builds the graph and loads it into Neo4j. Also exports JSON. |
| `prep_viz.py` | Turns the loader's JSON into the compact payload the explorer embeds, running the analytics the Cypher queries would run. |
| `cttc-network-explorer.html` | Self-contained interactive topology explorer, data already embedded. |

## Quick start

```bash
pip install neo4j                      # only needed to actually load

# 1. generate the dataset and look at it, no database involved
python cttc_graph_loader.py --demo --export-json cttc.json

# 2. load it into Neo4j and run the verification queries
python cttc_graph_loader.py --demo \
    --uri bolt://localhost:7687 --user neo4j --password secret \
    --wipe --verify

# 3. rebuild the explorer payload after changing the data
python prep_viz.py cttc.json viz.json
```

To re-embed a new dataset into the explorer, replace the `const DATA = {...}`
assignment at the top of the `<script>` block with the contents of `viz.json`.

## Loading real data instead of the demo

```bash
python cttc_graph_loader.py --csv-schema      # prints the expected columns
python cttc_graph_loader.py --csv-dir ./exports --uri ... --user ... --password ...
```

Expected files in the directory (all optional — missing ones are skipped):

```
devices.csv     id,name,vendor,model,role,serial,mgmt_ip,site_id,software_release,aliases
ports.csv       id,name,device_id,speed_gbps,role,admin_state,oper_state
links.csv       id,a_port_id,z_port_id,type,capacity_gbps,protection_role
pon.csv         id,olt_port_id,split_ratio,ont_count,technology
onts.csv        id,serial,model,firmware,pon_id,rx_dbm,subscriber_id
services.csv    id,circuit_id,class,bandwidth_mbps,state,subscriber_id,path_ports
subscribers.csv id,account,premise_id,service_area,criticality
```

`aliases` and `path_ports` are pipe-separated (`GLDT-A|10.42.7.11`). Every
relationship the loader writes carries `source`, `method`, `observed_at`,
`valid_from`, `valid_to` and `confidence`, per the schema's provenance rule —
so a config-derived edge is distinguishable from a diagram-derived one.

## What the demo data is, and is not

**Real**, from the Wavsys standing review of 18 May 2026: device models and
counts (1× MX960, 9× MX304, ~40× ACX 5448D, 29× Calix E7-2 XG801, EXA estate,
GP1100X ONT fleet), the software releases in play, the three named defects, the
ERPS management ring, and which devices sit two trains back.

**Placeholder**, generated to give the queries something to traverse: all
identifiers, serials, management IPs, port names, link topology, PON/ONT
assignments, circuits, subscribers, alarms and the incident. Site names beyond
Goldthwaite and San Angelo are invented.

Nothing in the explorer's Findings tab is a claim about CTTC's real network. It
is a demonstration that the model answers the questions.

## The incident in the demo data

28 ONTs on one PON tree behind `OLT-XG-01` go unreachable inside a four-minute
window, preceded 90 seconds earlier by a rising FEC error count on that OLT's
uplink. The OLT itself stays reachable, no change window is open, and optical
levels are in range — three negative results, which is what actually narrows
the fault domain to the uplink and its aggregation interface.

## Verification queries the loader runs with `--verify`

1. Node counts by label
2. Version drift — devices off their model's dominant release
3. Defect blast radius — services and subscribers on affected software
4. Fault-domain candidates — PONs with an alarm cluster

The full six-query set is in the CTTC Graph Schema artifact.
