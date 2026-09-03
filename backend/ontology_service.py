"""
CTTC Network Ontology Service
Loads network topology, optical infrastructure, services, defects, and alarms.
Provides graph traversal, blast radius computation, and SPOF analysis.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Base path to CTTC data directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTTC_DATA_DIR = os.path.join(BASE_DIR, "CTTC Data", "data")
VIZ_JSON_PATH = os.path.join(CTTC_DATA_DIR, "viz.json")
CTTC_JSON_PATH = os.path.join(CTTC_DATA_DIR, "cttc.json")

# In-memory cached datasets
_CACHED_UNIFIED_GRAPH: Optional[Dict[str, Any]] = None


def load_full_graph(reload: bool = False) -> Dict[str, Any]:
    """
    Load and unify BOTH cttc.json (1,190 nodes & 1,511 relationships) 
    and viz.json (rich metadata, defect blast radii, SPOF findings, and device analytics).
    """
    global _CACHED_UNIFIED_GRAPH
    if _CACHED_UNIFIED_GRAPH is not None and not reload:
        return _CACHED_UNIFIED_GRAPH

    try:
        cttc_data = {}
        viz_data = {}

        if os.path.exists(CTTC_JSON_PATH):
            with open(CTTC_JSON_PATH, "r", encoding="utf-8") as f:
                cttc_data = json.load(f)
                logger.info(f"Loaded cttc.json ({len(cttc_data.get('nodes', []))} nodes)")

        if os.path.exists(VIZ_JSON_PATH):
            with open(VIZ_JSON_PATH, "r", encoding="utf-8") as f:
                viz_data = json.load(f)
                logger.info(f"Loaded viz.json ({len(viz_data.get('devices', []))} devices)")

        raw_nodes = cttc_data.get("nodes", [])
        raw_relationships = cttc_data.get("relationships", []) or cttc_data.get("rels", [])

        # Build enrichment index from viz.json
        viz_devices = {d["id"]: d for d in viz_data.get("devices", [])}
        viz_sites = viz_data.get("sites", {})
        findings = viz_data.get("findings", {})
        incident = viz_data.get("incident", {})
        meta = viz_data.get("meta", cttc_data.get("summary", {}))

        # Enrich each node with detailed operational properties from viz.json
        enriched_nodes = []
        for n in raw_nodes:
            node_id = n.get("id")
            labels = list(n.get("labels", []))
            props = dict(n.get("props", {}))

            # Merge device-level metadata
            if node_id in viz_devices:
                dev = viz_devices[node_id]
                for k, v in dev.items():
                    if k not in props or props[k] is None:
                        props[k] = v
                # Ensure defects, approved, outlier, and services counts are present
                props["approved"] = dev.get("approved", True)
                props["outlier"] = dev.get("outlier", False)
                props["defects"] = dev.get("defects", [])
                props["services_count"] = dev.get("services", 0)
                props["subscribers_count"] = dev.get("subscribers", 0)

            # Merge site metadata
            if node_id in viz_sites:
                site_info = viz_sites[node_id]
                props["site_details"] = site_info
                for geo_key in ["name", "town", "county", "state", "lat", "lon", "latitude", "longitude", "alt_m", "alt_ft", "altitude_meters", "altitude_feet"]:
                    if geo_key in site_info and site_info[geo_key] is not None:
                        props[geo_key] = site_info[geo_key]

            enriched_nodes.append({
                "id": node_id,
                "labels": labels,
                "props": props
            })

        # Convert deviceLinks into direct relationships so device-to-device topology is always linked
        direct_device_rels = []
        for idx, dl in enumerate(viz_data.get("deviceLinks", [])):
            direct_device_rels.append({
                "id": f"link:dev:{idx+1}",
                "start": dl.get("a"),
                "end": dl.get("z"),
                "source": dl.get("a"),
                "target": dl.get("z"),
                "type": "CONNECTED_TO",
                "props": dl
            })

        combined_rels = direct_device_rels + raw_relationships

        _CACHED_UNIFIED_GRAPH = {
            "summary": cttc_data.get("summary", {}),
            "meta": meta,
            "nodes": enriched_nodes,
            "relationships": combined_rels,
            "rels": combined_rels,
            "devices": viz_data.get("devices", []),
            "deviceLinks": viz_data.get("deviceLinks", []),
            "sites": viz_sites,
            "alarms": viz_data.get("alarms", []),
            "pons": viz_data.get("pons", []),
            "subs": viz_data.get("subs", []),
            "services": viz_data.get("services", []),
            "findings": findings,
            "incident": incident
        }

        logger.info(f"Successfully unified cttc.json ({len(enriched_nodes)} nodes, {len(raw_relationships)} rels) and viz.json ({len(findings)} findings)")
        return _CACHED_UNIFIED_GRAPH

    except Exception as e:
        logger.error(f"Error merging cttc.json and viz.json: {e}")
        return get_fallback_ontology_data()


def load_ontology_data() -> Dict[str, Any]:
    """Load and cache the CTTC ontology data from viz.json and cttc.json"""
    return load_full_graph()


def get_topology(detail_level: int = 2, site_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Get graph nodes and links formatted for the React visualizer.
    detail_level: 1 (Backbone), 2 (+ OLT), 3 (+ PON & ONT)
    """
    data = load_ontology_data()
    devices = data.get("devices", [])
    device_links = data.get("deviceLinks", [])
    sites = data.get("sites", {})
    findings = data.get("findings", {})
    incident = data.get("incident", {})

    filtered_devices = devices
    if detail_level == 1:
        # Core & Aggregation only
        filtered_devices = [d for d in devices if d.get("role") in ["core", "aggregation"]]
    elif detail_level == 2:
        # Backbone + OLT + Access
        filtered_devices = [d for d in devices if d.get("role") in ["core", "aggregation", "access", "olt"]]

    if site_filter and site_filter != "all":
        filtered_devices = [d for d in filtered_devices if d.get("site") == site_filter]

    allowed_device_ids = {d["id"] for d in filtered_devices}
    filtered_links = [
        link for link in device_links
        if link.get("a") in allowed_device_ids and link.get("z") in allowed_device_ids
    ]

    spof_services = findings.get("spof", {}).get("services", 0)
    spof_count = len(spof_services) if isinstance(spof_services, (list, dict)) else int(spof_services or 0)
    defect_list = findings.get("defect_exposure", [])
    defect_count = len(defect_list) if isinstance(defect_list, list) else int(defect_list or 0)

    return {
        "meta": data.get("meta", {}),
        "sites": sites,
        "devices": filtered_devices,
        "links": filtered_links,
        "findings": findings,
        "incident": incident,
        "counts": {
            "total_devices": len(devices),
            "rendered_devices": len(filtered_devices),
            "rendered_links": len(filtered_links),
            "sites": len(sites),
            "defects": defect_count,
            "spof_services": spof_count
        }
    }


def compute_blast_radius(target_id: str) -> Dict[str, Any]:
    """
    Compute impact blast radius for a given defect ID, software release, or device ID.
    Traverses: Defect / Software Version -> Running Devices -> Attached Services -> Subscribers
    """
    data = load_ontology_data()
    devices = data.get("devices", [])
    findings = data.get("findings", {})
    defects = findings.get("defects", [])

    impacted_devices = []
    impacted_subscribers_count = 0
    impacted_services_count = 0
    matched_defect = None
    target_clean = str(target_id).strip().lower()

    # 1. Match against defects list in findings or directly on devices
    for d in defects:
        if str(d.get("id", "")).lower() == target_clean or target_clean in str(d.get("id", "")).lower():
            matched_defect = d
            break

    # 2. Find all devices carrying this defect or matching target
    for dev in devices:
        has_defect = False
        dev_defects = dev.get("defects", [])
        for df in dev_defects:
            if str(df.get("id", "")).lower() == target_clean or target_clean in str(df.get("id", "")).lower():
                has_defect = True
                if not matched_defect:
                    matched_defect = df
                break
        
        # Or if target is a software release
        if str(dev.get("release", "")).lower() == target_clean:
            has_defect = True

        # Or if target is the device itself
        if str(dev.get("id", "")).lower() == target_clean or str(dev.get("name", "")).lower() == target_clean:
            has_defect = True

        if has_defect:
            impacted_devices.append(dev)
            impacted_services_count += int(dev.get("services", 0) or 0)
            impacted_subscribers_count += int(dev.get("subscribers", 0) or 0)

    return {
        "target_id": target_id,
        "matched_defect": matched_defect,
        "impacted_devices": impacted_devices,
        "total_impacted_devices": len(impacted_devices),
        "total_impacted_services": impacted_services_count,
        "total_impacted_subscribers": impacted_subscribers_count
    }


# Alias for backwards compatibility
get_blast_radius = compute_blast_radius


def get_fallback_ontology_data() -> Dict[str, Any]:
    """Fallback sample dataset in case CTTC file is temporarily missing"""
    return {
        "meta": {"source": "Fallback CTTC Topology"},
        "sites": {
            "site:gldt": {"name": "Goldthwaite", "type": "central_office"},
            "site:sang": {"name": "San Angelo", "type": "aggregation_site"}
        },
        "devices": [
            {
                "id": "dev:mx960-gldt",
                "name": "GLDT-CORE-01",
                "model": "MX960",
                "vendor": "Juniper",
                "role": "core",
                "site": "site:gldt",
                "release": "24.4R1-S3.6",
                "approved": True,
                "services": 24,
                "subscribers": 24,
                "mgmt_ip": "10.56.91.67"
            },
            {
                "id": "dev:mx304-sang",
                "name": "SANG-AGG-01",
                "model": "MX304",
                "vendor": "Juniper",
                "role": "aggregation",
                "site": "site:sang",
                "release": "22.3R3",
                "approved": False,
                "services": 6,
                "subscribers": 6,
                "mgmt_ip": "10.58.208.119"
            }
        ],
        "deviceLinks": [
            {"a": "dev:mx304-sang", "z": "dev:mx960-gldt", "cap": 100, "prot": "unprotected"}
        ],
        "findings": {"defect_exposure": [], "spof": {"services": []}},
        "incident": {}
    }
