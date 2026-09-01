/**
 * CTTC Network Ontology Service
 * Handles ontology topology data retrieval, blast radius computations, and fault isolation.
 * Merges cttc.json (1,190 nodes & 1,511 rels) and viz.json findings seamlessly.
 */

import apiService from './api.js';
import { API_ENDPOINTS } from '../config/api.js';

let cachedUnifiedGraph = null;

// Helper to unify cttc.json and viz.json in the frontend
function unifyDatasets(cttcData, vizData) {
  const rawNodes = cttcData?.nodes || [];
  const rawRels = cttcData?.relationships || cttcData?.rels || [];

  const vizDevices = {};
  (vizData?.devices || []).forEach(d => {
    vizDevices[d.id] = d;
  });

  const vizSites = vizData?.sites || {};
  const findings = vizData?.findings || {};
  const incident = vizData?.incident || {};
  const meta = vizData?.meta || cttcData?.summary || {};

  const enrichedNodes = rawNodes.map(n => {
    const nodeId = n.id;
    const labels = Array.isArray(n.labels) ? n.labels : [n.type || 'Entity'];
    const props = { ...(n.props || n.properties || {}) };

    if (vizDevices[nodeId]) {
      const dev = vizDevices[nodeId];
      Object.assign(props, dev);
      props.approved = dev.approved !== false;
      props.outlier = !!dev.outlier;
      props.defects = dev.defects || [];
      props.services_count = dev.services || 0;
      props.subscribers_count = dev.subscribers || 0;
    }

    if (vizSites[nodeId]) {
      props.site_details = vizSites[nodeId];
      if (!props.name) props.name = vizSites[nodeId].name;
    }

    return {
      id: nodeId,
      labels,
      props
    };
  });

  return {
    summary: cttcData?.summary || {},
    meta,
    nodes: enrichedNodes,
    relationships: rawRels,
    rels: rawRels,
    devices: vizData?.devices || [],
    deviceLinks: vizData?.deviceLinks || [],
    sites: vizSites,
    findings,
    incident
  };
}

export const ontologyService = {
  /**
   * Get complete unified graph dataset (cttc.json + viz.json)
   */
  getFullGraph: async () => {
    if (cachedUnifiedGraph) {
      return cachedUnifiedGraph;
    }

    // 1. Attempt API fetch from backend
    try {
      const res = await Promise.race([
        apiService.get(API_ENDPOINTS.ONTOLOGY.FULL_GRAPH),
        new Promise((_, reject) => setTimeout(() => reject(new Error('API Timeout')), 4000))
      ]);
      if (res && res.nodes && res.nodes.length > 0) {
        cachedUnifiedGraph = res;
        return res;
      }
    } catch (err) {
      console.warn('Backend API unavailable, loading local static cttc.json and viz.json:', err);
    }

    // 2. Direct static bundle fallback (Guarantees 100% reliable load)
    try {
      const [cttcRes, vizRes] = await Promise.all([
        fetch('/data/cttc.json').then(r => r.json()),
        fetch('/data/viz.json').then(r => r.json())
      ]);

      const unified = unifyDatasets(cttcRes, vizRes);
      cachedUnifiedGraph = unified;
      return unified;
    } catch (fallbackErr) {
      console.error('Failed to load local static datasets:', fallbackErr);
      throw fallbackErr;
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
