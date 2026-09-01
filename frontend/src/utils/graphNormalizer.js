/**
 * Graph Data Normalization & Dynamic Property Resolver Layer
 * Fully decoupled from specific backend payload structures.
 * Automatically handles any node types, relationship types, and properties without hardcoding.
 */

// Neo4j-aligned curated color palette for standard telecom ontology entities
const STANDARD_TYPE_COLORS = {
  Device: '#38bdf8',          // Sky Blue (Core/Agg/Access Routers)
  Router: '#38bdf8',
  Switch: '#38bdf8',
  Site: '#60a5fa',            // Blue
  Port: '#f472b6',            // Coral Pink / Magenta
  Interface: '#f472b6',
  PONTree: '#fb7185',         // Rose / Coral
  Splitter: '#ec4899',        // Deep Pink
  ONT: '#e879f9',             // Fuchsia / Violet
  Service: '#34d399',         // Emerald Green
  Circuit: '#34d399',
  Subscriber: '#10b981',      // Green
  Customer: '#10b981',
  SoftwareVersion: '#a78bfa', // Lavender
  Release: '#a78bfa',
  KnownDefect: '#ef4444',     // Crimson Alert
  Defect: '#ef4444',
  Alarm: '#f59e0b',           // Amber Warning
  Link: '#94a3b8',            // Slate
  Optic: '#38bdf8',
  Change: '#c084fc',
  VendorCase: '#f97316'
};

/**
 * Deterministic color generator for any arbitrary/new entity types
 */
export function getNodeTypeColor(type = 'default') {
  if (STANDARD_TYPE_COLORS[type]) {
    return STANDARD_TYPE_COLORS[type];
  }
  // Generate HSL color deterministically from type string
  let hash = 0;
  for (let i = 0; i < type.length; i++) {
    hash = type.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash) % 360;
  return `hsl(${h}, 75%, 60%)`;
}

/**
 * Extract primary node type/label from a node object
 */
export function getNodeType(node) {
  if (!node) return 'Entity';
  if (Array.isArray(node.labels) && node.labels.length > 0) {
    // Prefer non-generic label if multiple labels exist
    const primary = node.labels.find(l => !['Entity', 'Node', 'Juniper', 'Calix'].includes(l)) || node.labels[0];
    return primary;
  }
  if (node.type) return String(node.type);
  if (node.label) return String(node.label);
  if (node.role) return String(node.role);
  if (node.id && typeof node.id === 'string' && node.id.includes(':')) {
    const prefix = node.id.split(':')[0].toLowerCase();
    if (prefix === 'dev') return 'Device';
    if (prefix === 'port') return 'Port';
    if (prefix === 'site') return 'Site';
    if (prefix === 'pon') return 'PONTree';
    if (prefix === 'ont') return 'ONT';
    if (prefix === 'opt') return 'Optic';
    if (prefix === 'link') return 'Link';
    if (prefix === 'sw') return 'SoftwareVersion';
    if (prefix === 'def') return 'KnownDefect';
    if (prefix === 'svc') return 'Service';
    if (prefix === 'sub') return 'Subscriber';
    if (prefix === 'alm') return 'Alarm';
    if (prefix === 'chg') return 'Change';
    if (prefix === 'case') return 'VendorCase';
  }
  return 'Node';
}

/**
 * Intelligent dynamic display label resolver
 * Checks properties in intelligent priority order with safe fallbacks
 */
export function getNodeDisplayLabel(node) {
  if (!node) return '';
  const p = node.properties || node.props || node;

  // Priority order for display label
  const candidate =
    p.name ||
    p.customer_name ||
    p.port_name ||
    p.circuit_id ||
    p.account ||
    p.release ||
    p.title ||
    p.label ||
    p.model ||
    p.symptom ||
    p.mgmt_ip ||
    p.serial;

  if (candidate && typeof candidate === 'string') {
    return candidate;
  }

  // Fallback to formatted node ID
  if (node.id && typeof node.id === 'string') {
    if (node.id.includes(':')) {
      return node.id.split(':').slice(1).join(':');
    }
    return node.id;
  }

  return String(node.id || 'Node');
}

/**
 * Extract relationship type from edge/rel object
 */
export function getRelationshipType(rel) {
  if (!rel) return 'CONNECTED_TO';
  if (rel.type) return String(rel.type);
  if (rel.relationship) return String(rel.relationship);
  if (rel.label) return String(rel.label);
  return 'LINKED';
}

/**
 * Normalize any arbitrary backend graph response into standardized { nodes: [], relationships: [] }
 */
export function normalizeGraphData(raw) {
  if (!raw) return { nodes: [], relationships: [], nodeMap: new Map(), stats: {} };

  let rawNodes = [];
  let rawRels = [];

  // Case 1: Standard { nodes: [...], relationships: [...] }
  if (Array.isArray(raw.nodes)) {
    rawNodes = raw.nodes;
    rawRels = Array.isArray(raw.relationships)
      ? raw.relationships
      : Array.isArray(raw.rels)
      ? raw.rels
      : Array.isArray(raw.links)
      ? raw.links
      : [];
  }
  // Case 2: Legacy { devices: [...], deviceLinks: [...] }
  else if (Array.isArray(raw.devices)) {
    rawNodes = raw.devices.map(d => ({
      id: d.id,
      labels: ['Device', d.vendor || 'Hardware'],
      props: { ...d }
    }));
    rawRels = (raw.deviceLinks || []).map((l, idx) => ({
      id: `rel-${idx}`,
      type: l.prot === 'unprotected' ? 'UNPROTECTED_LINK' : 'TERMINATES',
      start: l.a,
      end: l.z,
      props: { ...l }
    }));
  }

  const nodeMap = new Map();
  const normalizedNodes = [];

  rawNodes.forEach(rn => {
    if (!rn || !rn.id) return;
    const type = getNodeType(rn);
    const label = getNodeDisplayLabel(rn);
    const props = rn.properties || rn.props || rn;
    const color = getNodeTypeColor(type);

    const isCore = props.role === 'core' || type === 'Site';
    const isDevice = type === 'Device' || type === 'Router';
    const radius = isCore ? 12 : isDevice ? 8.5 : 5;

    const normalizedNode = {
      id: String(rn.id),
      type,
      label,
      props,
      color,
      radius,
      isCore,
      isDevice
    };

    nodeMap.set(normalizedNode.id, normalizedNode);
    normalizedNodes.push(normalizedNode);
  });

  const normalizedRels = [];
  rawRels.forEach((rr, idx) => {
    if (!rr) return;
    const source = String(rr.start || rr.source || rr.from || rr.a || '');
    const target = String(rr.end || rr.target || rr.to || rr.z || '');
    const type = getRelationshipType(rr);

    if (!source || !target || !nodeMap.has(source) || !nodeMap.has(target)) {
      return;
    }

    normalizedRels.push({
      id: String(rr.id || `rel-${idx}`),
      source,
      target,
      type,
      props: rr.properties || rr.props || rr
    });
  });

  // Calculate dynamic stats per node type and rel type
  const nodeTypeCounts = {};
  normalizedNodes.forEach(n => {
    nodeTypeCounts[n.type] = (nodeTypeCounts[n.type] || 0) + 1;
  });

  const relTypeCounts = {};
  normalizedRels.forEach(r => {
    relTypeCounts[r.type] = (relTypeCounts[r.type] || 0) + 1;
  });

  return {
    nodes: normalizedNodes,
    relationships: normalizedRels,
    nodeMap,
    stats: {
      totalNodes: normalizedNodes.length,
      totalRelationships: normalizedRels.length,
      nodeTypeCounts,
      relTypeCounts
    },
    findings: raw.findings || {},
    meta: raw.meta || raw.summary || {},
    sites: raw.sites || {},
    devices: raw.devices || []
  };
}
