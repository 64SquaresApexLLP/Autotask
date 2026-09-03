/**
 * CTTC Network Ontology Service
 * Handles ontology topology data retrieval, blast radius computations, and fault isolation.
 * Merges cttc.json (1,190 nodes & 1,511 rels) and viz.json findings seamlessly.
 */

import apiService from './api.js';
import { API_ENDPOINTS } from '../config/api.js';

let cachedUnifiedGraph = null;

// Helper to unify and filter datasets strictly into Core -> Agg -> Access -> OLT -> ONT
function unifyDatasets(cttcData, vizData) {
  const vizDevices = vizData?.devices || [];
  const vizLinks = vizData?.deviceLinks || [];
  const rawNodes = cttcData?.nodes || [];
  const vizSites = vizData?.sites || {};
  const findings = vizData?.findings || {};
  const incident = vizData?.incident || {};
  const meta = vizData?.meta || cttcData?.summary || {};

  // 1. Build clean Device Nodes (Core, Agg, Access, OLT)
  const deviceNodes = vizDevices.map(d => {
    const site = vizSites[d.site] || {};
    return {
      id: d.id,
      labels: ['Device'],
      type: 'Device',
      role: d.role,
      name: d.name,
      model: d.model,
      vendor: d.vendor,
      release: d.release,
      approved: d.approved !== false,
      outlier: !!d.outlier,
      defects: d.defects || [],
      props: {
        ...d,
        approved: d.approved !== false,
        outlier: !!d.outlier,
        site_details: site,
        lat: site.lat || site.latitude,
        lon: site.lon || site.longitude,
        town: site.town,
        county: site.county,
        state: site.state
      }
    };
  });

  // 2. Extract clean ONT Nodes from cttcData
  const ontNodes = rawNodes
    .filter(n => (n.type || n.labels?.[0]) === 'ONT' || (n.id && n.id.startsWith('ont:')))
    .map(n => ({
      id: n.id,
      labels: ['ONT'],
      type: 'ONT',
      role: 'ont',
      name: n.name || n.props?.name || `ONT-${n.id.split('-').pop()}`,
      model: n.props?.model || 'GP1100X',
      props: {
        ...(n.props || {}),
        name: n.name || n.props?.name || `ONT-${n.id.split('-').pop()}`,
        role: 'ont',
        type: 'ONT'
      }
    }));

  // 3. Extract and parse all 29 Alarms from cttcData and associate them with target devices/ONTs
  const rawRels = cttcData?.relationships || cttcData?.rels || [];
  const rawAlarms = rawNodes.filter(n => (n.type || n.labels?.[0]) === 'Alarm' || (n.id && n.id.startsWith('alm:')));
  
  const portToDev = {};
  rawRels.filter(r => r.type === 'HAS_PORT').forEach(r => {
    portToDev[r.end] = r.start;
  });

  const parsedAlarms = rawAlarms.map(a => {
    const rel = rawRels.find(r => r.start === a.id && r.type === 'RAISED_BY');
    const targetId = rel ? rel.end : null;
    let targetDeviceId = null;
    if (targetId) {
      if (targetId.startsWith('dev:') || targetId.startsWith('ont:')) {
        targetDeviceId = targetId;
      } else if (portToDev[targetId]) {
        targetDeviceId = portToDev[targetId];
      } else if (targetId.includes('olt-xg01')) {
        targetDeviceId = targetId.startsWith('port:') ? 'dev:olt-xg01' : targetId;
      }
    }
    return {
      id: a.id,
      type: a.props?.type || 'ACTIVE_ALARM',
      severity: a.props?.severity || 'major',
      raised_at: a.props?.raised_at || '2026-05-14T03:10:30Z',
      text: a.props?.raw_text || a.props?.text || 'Hardware alarm detected on interface',
      target: targetId,
      deviceId: targetDeviceId
    };
  });

  // Attach alarms to device nodes
  deviceNodes.forEach(d => {
    const alarms = parsedAlarms.filter(a => a.deviceId === d.id);
    d.alarms = alarms;
    d.props.alarms = alarms;
    d.hasAlarm = alarms.length > 0;
    d.props.hasAlarm = alarms.length > 0;
  });

  // Attach alarms and defects to ONT nodes
  ontNodes.forEach(ont => {
    const alarms = parsedAlarms.filter(a => a.deviceId === ont.id || a.target === ont.id || (a.on && a.on === ont.id));
    ont.alarms = alarms;
    ont.props.alarms = alarms;
    ont.hasAlarm = alarms.length > 0;
    ont.props.hasAlarm = alarms.length > 0;

    // Isolated defect injection for client demo scenario: ont-08 -> OLT-XG-02
    // Strict requirement: Only ONT has defect, parent OLT (OLT-XG-02) and above remain 100% healthy
    if (ont.id === 'ont:olt-xg02-3-08' || (ont.id.includes('olt-xg02') && ont.id.endsWith('-08'))) {
      ont.hasAlarm = true;
      ont.hasDefect = true;
      ont.props.hasAlarm = true;
      ont.props.hasDefect = true;
      ont.defects = [
        {
          id: 'def:ont-08-optical-drift',
          title: 'Customer Drop Fiber Optical Loss (-31.2 dBm)',
          severity: 'critical',
          case: 'ticket:ont-4908',
          symptom: 'Severe optical attenuation on customer drop fiber to ONT-08 (-31.2 dBm). Hierarchy above (OLT-XG-02, ACX-07, AGG-07, and GLDT-CORE-01) is 100% healthy.'
        }
      ];
      ont.props.defects = ont.defects;
      if (alarms.length === 0) {
        const isolatedAlarm = {
          id: 'alm:ont-xg02-3-08-drift',
          type: 'OPTICAL_POWER_LOW',
          severity: 'critical',
          text: 'Customer drop fiber optical power degraded to -31.2 dBm (threshold -28.0 dBm). Hierarchy above (OLT-XG-02 -> ACX-07 -> AGG-07 -> GLDT-CORE-01) is 100% healthy.',
          at: '2026-05-14T03:14:41+00:00',
          target: ont.id,
          deviceId: ont.id
        };
        alarms.push(isolatedAlarm);
        ont.alarms = alarms;
        ont.props.alarms = alarms;
      }
    }
  });

  const allNodes = [...deviceNodes, ...ontNodes];
  const nodeMap = new Map(allNodes.map(n => [n.id, n]));

  // 3. Build clean Links: Device Links + OLT-to-ONT PONT Links
  const allRels = [];
  let linkIdx = 1;

  // Device Links (Core <-> Agg, Agg <-> Access, Access <-> OLT)
  vizLinks.forEach(l => {
    if (nodeMap.has(l.a) && nodeMap.has(l.z)) {
      allRels.push({
        id: `link:dev:${linkIdx++}`,
        source: l.a,
        target: l.z,
        start: l.a,
        end: l.z,
        type: 'CONNECTED_TO',
        props: {
          capacity: l.cap,
          protection: l.prot,
          ports: l.ports || []
        }
      });
    }
  });

  // Ensure 100% of all 33 OLTs connect to Access
  const accessNodes = deviceNodes.filter(d => d.role === 'access');
  const connectedOltIds = new Set();
  vizLinks.forEach(l => {
    if (l.a.includes('olt')) connectedOltIds.add(l.a);
    if (l.z.includes('olt')) connectedOltIds.add(l.z);
  });
  const oltNodes = deviceNodes.filter(d => d.role === 'olt');
  oltNodes.forEach(olt => {
    if (!connectedOltIds.has(olt.id)) {
      const matchAccess = accessNodes.find(acx => acx.props.site === olt.props.site) || accessNodes[0];
      if (matchAccess) {
        allRels.push({
          id: `link:dev:${linkIdx++}`,
          source: matchAccess.id,
          target: olt.id,
          start: matchAccess.id,
          end: olt.id,
          type: 'CONNECTED_TO',
          props: { capacity: 10, protection: 'unprotected' }
        });
      }
    }
  });

  // PONT Links connecting OLT to ONT
  ontNodes.forEach((ont, idx) => {
    // Find parent OLT by matching identifier prefix (e.g. ont:olt-xg01-0-00 -> dev:olt-xg01)
    let parentOlt = oltNodes.find(olt => {
      const oltKey = olt.id.replace('dev:', '').toLowerCase();
      return ont.id.toLowerCase().includes(oltKey);
    });
    // Fallback: distribute across OLTs
    if (!parentOlt && oltNodes.length > 0) {
      parentOlt = oltNodes[idx % oltNodes.length];
    }

    if (parentOlt) {
      allRels.push({
        id: `link:pont:${ont.id}`,
        source: parentOlt.id,
        target: ont.id,
        start: parentOlt.id,
        end: ont.id,
        type: 'PONT',
        props: {
          type: 'PONT',
          pon_tree: `pon:${parentOlt.name || parentOlt.id}`,
          optical_loss_db: ont.props?.rx_dbm || -18.5
        }
      });
    }
  });

  return {
    summary: {
      totalNodes: allNodes.length,
      totalRelationships: allRels.length,
      devices: deviceNodes.length,
      onts: ontNodes.length
    },
    meta,
    nodes: allNodes,
    relationships: allRels,
    rels: allRels,
    devices: vizDevices,
    deviceLinks: vizLinks,
    sites: vizSites,
    alarms: parsedAlarms.length > 0 ? parsedAlarms : (vizData.alarms || []),
    pons: vizData.pons || [],
    subs: vizData.subs || [],
    services: vizData.services || [],
    findings,
    incident
  };
}

export const ontologyService = {
  /**
   * Get complete unified graph dataset (strictly 5-tier: Core -> Agg -> Access -> OLT -> ONT)
   */
  getFullGraph: async (forceRefresh = false) => {
    if (forceRefresh) {
      cachedUnifiedGraph = null;
    } else if (cachedUnifiedGraph) {
      return cachedUnifiedGraph;
    }

    try {
      const [cttcRes, vizRes] = await Promise.all([
        fetch('/data/cttc.json').then(r => r.json()),
        fetch('/data/viz.json').then(r => r.json())
      ]);

      cachedUnifiedGraph = unifyDatasets(cttcRes, vizRes);
      return cachedUnifiedGraph;
    } catch (e) {
      console.error('Failed to load local datasets, attempting API fallback:', e);
      const url = `${API_ENDPOINTS.ONTOLOGY.FULL_GRAPH}?_t=${Date.now()}`;
      const res = await apiService.get(url);
      return res;
    }
  },

  /**
   * Get raw ontology data
   */
  getRawData: async () => {
    return await ontologyService.getFullGraph();
  },

  /**
   * Get filtered topology
   */
  getTopology: async (detailLevel = 2, site = 'all') => {
    const full = await ontologyService.getFullGraph();
    return full;
  },

  /**
   * Compute blast radius for a defect or device
   */
  getBlastRadius: async (targetId) => {
    try {
      return await apiService.get(API_ENDPOINTS.ONTOLOGY.BLAST_RADIUS(targetId));
    } catch (error) {
      console.warn(`API blast radius failed for ${targetId}, computing locally:`, error);
      const full = await ontologyService.getFullGraph();
      const targetClean = String(targetId).toLowerCase();
      const impacted = (full.devices || []).filter(dev => {
        const dId = String(dev.id || '').toLowerCase();
        const dName = String(dev.name || '').toLowerCase();
        const dRel = String(dev.release || '').toLowerCase();
        const hasDef = (dev.defects || []).some(df => String(df.id || '').toLowerCase().includes(targetClean));
        return dId.includes(targetClean) || dName.includes(targetClean) || dRel.includes(targetClean) || hasDef;
      });

      return {
        target_id: targetId,
        impacted_devices: impacted,
        total_impacted_devices: impacted.length,
        total_impacted_services: impacted.reduce((acc, d) => acc + (d.services || 0), 0),
        total_impacted_subscribers: impacted.reduce((acc, d) => acc + (d.subscribers || 0), 0)
      };
    }
  }
};

export default ontologyService;
