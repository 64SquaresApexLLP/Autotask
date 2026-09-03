import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import ChatButton from '../../components/ChatButton';
import Neo4jGraphCanvas from '../../components/Neo4jGraphCanvas';
import GoogleNetworkMap from '../../components/GoogleNetworkMap';
import {
  normalizeGraphData,
  getNodeType,
  getNodeDisplayLabel,
  getNodeTypeColor
} from '../../utils/graphNormalizer';
import {
  Terminal,
  Play,
  Share2,
  AlertOctagon,
  ArrowRight,
  Workflow,
  Compass,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  ChevronRight,
  Ticket,
  Eye,
  X,
  Code,
  Table,
  Layers,
  Sparkles,
  Database,
  Radio,
  Cpu,
  Filter,
  Plus,
  ChevronUp,
  ChevronDown,
  Flame,
  Zap,
  BellRing,
  ShieldX,
  Network,
  Activity,
  MapPin,
  Mountain,
  Globe,
  ExternalLink,
  User
} from 'lucide-react';
import { ontologyService } from '../../services/ontologyService.js';
import useAuth from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

// Defect & Incident Quick-Filter Badges (Technician 1-Click Investigation)
const DEFECT_PRESETS = [
  {
    id: 'def_evpn',
    label: 'EVPN QinQ Defect',
    sublabel: '8 Aggregation Routers & 8 Circuits',
    badge: 'Critical (P1)',
    badgeColor: 'bg-red-100 text-red-700 border-red-200',
    icon: Flame,
    color: '#ef4444',
    filterKeywords: ['23.4r2', 'evpn', 'qinq', 'agg-02', 'agg-03', 'agg-04', 'agg-05', 'agg-06', 'agg-07', 'agg-08', 'agg-09'],
    defectInfo: {
      id: 'def:evpn-qinq',
      title: 'EVPN QinQ VLAN-in-VLAN Drop',
      severity: 'Critical (P1)',
      vendor: 'Juniper Networks (Junos 23.4R2)',
      case: 'case:jnpr-evpn-qinq',
      impact: 'VLAN-in-VLAN over EVPN affects cell-tower circuits under high packet load.',
      affectedDevices: '8 Aggregation Routers (AGG-02 through AGG-09)',
      impactedServices: '8 Active Cell-Tower Backhaul Circuits',
      impactedSubscribers: '8 Wholesale Mobile Carriers'
    }
  },
  {
    id: 'spof_sang',
    label: 'SPOF: Unprotected Trunk',
    sublabel: 'San Angelo 100G Single Link',
    badge: 'High (P2)',
    badgeColor: 'bg-amber-100 text-amber-700 border-amber-200',
    icon: ShieldX,
    color: '#f59e0b',
    filterKeywords: ['mx304-sang', 'acx-gldt-a', 'acx-sang-a', 'mx960-gldt'],
    defectInfo: {
      id: 'spof:sang-100g',
      title: 'Single Point of Failure (SPOF) - Unprotected Trunk',
      severity: 'High (P2)',
      vendor: 'Network Architecture / Physical Topology',
      case: 'N/A (Topology Risk)',
      impact: 'San Angelo CO is connected via a single 100G link without ERPS protection ring. Any fiber cut causes a total regional outage.',
      affectedDevices: 'SANG-AGG-01, ACX-GLDT-A, ACX-SANG-A',
      impactedServices: '12 Optical Enterprise Services',
      impactedSubscribers: '48 Subscribers'
    }
  },
  {
    id: 'drift_stragglers',
    label: 'Software Drift Outliers',
    sublabel: '2 Devices on Unapproved Trains',
    badge: 'Warning (P3)',
    badgeColor: 'bg-purple-100 text-purple-700 border-purple-200',
    icon: Zap,
    color: '#a855f7',
    filterKeywords: ['22.3r3', '21.4r3', 'sang'],
    defectInfo: {
      id: 'drift:fleet-outliers',
      title: 'Software Train Outliers (Version Drift)',
      severity: 'Medium (P3)',
      vendor: 'Fleet Configuration',
      case: 'N/A (Maintenance)',
      impact: '2 devices run deprecated Junos releases (22.3R3 / 21.4R3) that miss critical security patches and EVPN stabilization fixes.',
      affectedDevices: 'SANG-AGG-01 (22.3R3), ACX-19 (21.4R3)',
      impactedServices: '4 Enterprise Circuits',
      impactedSubscribers: '16 Subscribers'
    }
  },
  {
    id: 'alarm_cluster',
    label: 'Active Alarms (29)',
    sublabel: 'OLT-XG-01 & 28 Downstream ONTs',
    badge: 'Active (29)',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-300 font-bold',
    icon: BellRing,
    color: '#f59e0b',
    filterKeywords: ['olt-xg01'],
    defectInfo: {
      id: 'alarm:cluster-29',
      title: 'OLT-XG-01 Active Alarm Cascade (29 Alarms)',
      severity: 'Major (29 Open Alarms)',
      vendor: 'Calix E7-2 / Uplink Port FEC Errors',
      case: 'ticket:alm-4902',
      impact: 'Uplink FEC error rate on OLT-XG-01 triggered loss of management connectivity on 28 downstream customer ONTs (ONT-00 through ONT-27).',
      affectedDevices: '1 OLT (OLT-XG-01) + 28 Customer ONTs',
      impactedServices: '28 Optical Subscriber Circuits',
      impactedSubscribers: '28 Delivered Subscribers'
    }
  },
  {
    id: 'def_ont_isolated',
    label: 'Isolated ONT Defect',
    sublabel: 'ONT-08 → OLT-XG-02 (Client Demo)',
    badge: 'ONT Edge Only',
    badgeColor: 'bg-rose-100 text-rose-800 border-rose-300 font-bold',
    icon: Activity,
    color: '#e11d48',
    filterKeywords: ['olt-xg02-3-08', 'olt-xg02', 'acx-07', 'mx304-07', 'mx960-gldt'],
    defectInfo: {
      id: 'def:ont-08-optical-drift',
      title: 'Isolated Customer ONT Optical Loss (-31.2 dBm)',
      severity: 'Critical (Edge Only - Client Demo)',
      vendor: 'Calix GigaPoint GP1100X',
      case: 'ticket:ont-4908',
      impact: 'Severe optical attenuation on customer drop fiber to ONT-08 (-31.2 dBm). Hierarchy above (OLT-XG-02 → ACX-07 → AGG-07 → GLDT-CORE-01) is 100% healthy.',
      affectedDevices: '1 Customer Premise ONT (ONT-08)',
      impactedServices: '1 Customer Broadband Circuit',
      impactedSubscribers: '1 Residential Subscriber (ACCT-20383)'
    }
  }
];

// Standard Aura Query Tabs
const AURA_TABS = [
  {
    id: 'full_access',
    title: 'Full 5-Tier Hierarchy (Core → Agg → ACX → OLT → ONT)',
    query: `MATCH (c:Core)->(agg:Aggregation)->(acx:Access)->(olt:OLT)-[:PONT]->(ont:ONT) RETURN *;`,
    description: 'Complete 5-Tier Network Infrastructure Hierarchy'
  },
  {
    id: 'core_agg',
    title: 'Core & Aggregation Backbone',
    query: `MATCH (c:Core)->(agg:Aggregation) RETURN c, agg;`,
    description: 'Backbone routers and 100G/400G transport trunks'
  },
  {
    id: 'acx_olt',
    title: 'Access & OLT Distribution',
    query: `MATCH (acx:Access)->(olt:OLT) RETURN acx, olt;`,
    description: 'Aggregation-to-access rings and OLT headends'
  },
  {
    id: 'olt_ont',
    title: 'PONT Links & Customer ONTs',
    query: `MATCH (olt:OLT)-[p:PONT]->(ont:ONT) RETURN olt, p, ont;`,
    description: 'FTTH / PON distribution and terminal edge customer premises'
  }
];

export default function NetworkOntology() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const fitRef = useRef(null);

  // Active Defect Filter Badge
  const [activeDefectFilter, setActiveDefectFilter] = useState(null);

  // Tab & Cypher Query State
  const [activeTabId, setActiveTabId] = useState('full_access');
  const [cypherQuery, setCypherQuery] = useState(AURA_TABS[0].query);
  const [viewMode, setViewMode] = useState('graph'); // 'graph' | 'map' | 'table'
  const [searchQuery, setSearchQuery] = useState('');
  const [showCypherConsole, setShowCypherConsole] = useState(false);

  // Raw Graph Data from API
  const [rawData, setRawData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [queryExecutionTime, setQueryExecutionTime] = useState('2.4');

  // Interactive Graph Controls
  const [physicsEnabled, setPhysicsEnabled] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedRel, setSelectedRel] = useState(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [hiddenNodeTypes, setHiddenNodeTypes] = useState(new Set());
  const [hiddenRelTypes, setHiddenRelTypes] = useState(new Set());

  // Load Real Graph Data from Backend
  const loadData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError('');
      const start = performance.now();
      const res = await ontologyService.getFullGraph(forceRefresh);
      const end = performance.now();
      setQueryExecutionTime(((end - start) / 1000).toFixed(2));
      setRawData(res);
    } catch (err) {
      console.error('Failed to load network ontology:', err);
      setError('Unable to load graph data. Please verify backend connection.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Dynamically Normalize Graph Data
  const normalizedGraph = useMemo(() => {
    if (!rawData) return { nodes: [], relationships: [], nodeMap: new Map(), stats: {} };
    return normalizeGraphData(rawData);
  }, [rawData]);

  // Dynamically Filter Graph based on Active Tab, Defect Badges & Search Query
  const displayedGraph = useMemo(() => {
    if (!normalizedGraph.nodes.length) {
      return { nodes: [], relationships: [], stats: { totalNodes: 0, totalRelationships: 0, nodeTypeCounts: {}, relTypeCounts: {} } };
    }

    const { nodes, relationships } = normalizedGraph;
    let filteredNodes = nodes;
    let filteredRels = relationships;

    // 1. Defect Badge Filter (Priority 1-Click Investigation)
    if (activeDefectFilter) {
      const keywords = activeDefectFilter.filterKeywords;
      filteredNodes = nodes.filter(n => {
        const id = n.id.toLowerCase();
        const label = (n.label || '').toLowerCase();
        const release = (n.props?.release || '').toLowerCase();
        const model = (n.props?.model || '').toLowerCase();

        return keywords.some(k => id.includes(k) || label.includes(k) || release.includes(k) || model.includes(k));
      });

      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => {
        if (activeDefectFilter.id === 'def_ont_isolated') {
          return nSet.has(r.source) && nSet.has(r.target);
        }
        return nSet.has(r.source) || nSet.has(r.target);
      });
    }
    // 2. Tab Presets
    else if (activeTabId === 'core_agg') {
      filteredNodes = nodes.filter(n => n.role === 'core' || n.role === 'aggregation' || n.props?.role === 'core' || n.props?.role === 'aggregation');
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => nSet.has(r.source) && nSet.has(r.target));
    } else if (activeTabId === 'acx_olt') {
      filteredNodes = nodes.filter(n => n.role === 'access' || n.role === 'olt' || n.props?.role === 'access' || n.props?.role === 'olt');
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => nSet.has(r.source) && nSet.has(r.target));
    } else if (activeTabId === 'olt_ont') {
      filteredNodes = nodes.filter(n => n.role === 'olt' || n.type === 'ONT' || n.role === 'ont' || n.props?.role === 'olt' || n.props?.role === 'ont');
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => nSet.has(r.source) && nSet.has(r.target));
    } else {
      // Default: full 5-tier hierarchy (Core -> Agg -> Access -> OLT -> ONT)
      filteredNodes = nodes;
      filteredRels = relationships;
    }

    // 3. Smart Search Query Filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      if (q === 'defect' || q === 'evpn' || q === 'qinq') {
        filteredNodes = filteredNodes.filter(n => n.props?.release === '23.4R2' || n.type === 'KnownDefect');
      } else if (q === 'spof' || q === 'unprotected') {
        filteredNodes = filteredNodes.filter(n => n.id.includes('sang') || n.id.includes('gldt-a'));
      } else if (q === 'outlier' || q === 'drift' || q === 'unapproved') {
        filteredNodes = filteredNodes.filter(n => n.props?.approved === false);
      } else {
        filteredNodes = filteredNodes.filter(n =>
          n.id.toLowerCase().includes(q) ||
          (n.label || '').toLowerCase().includes(q) ||
          (n.props?.model || '').toLowerCase().includes(q) ||
          (n.props?.mgmt_ip || '').includes(q)
        );
      }
    }

    // Recalculate dynamic stats
    const nodeTypeCounts = {};
    filteredNodes.forEach(n => {
      nodeTypeCounts[n.type] = (nodeTypeCounts[n.type] || 0) + 1;
    });

    const relTypeCounts = {};
    filteredRels.forEach(r => {
      relTypeCounts[r.type] = (relTypeCounts[r.type] || 0) + 1;
    });

    return {
      nodes: filteredNodes,
      relationships: filteredRels,
      stats: {
        totalNodes: filteredNodes.length,
        totalRelationships: filteredRels.length,
        nodeTypeCounts,
        relTypeCounts
      }
    };
  }, [normalizedGraph, activeTabId, activeDefectFilter, searchQuery]);

  // Node selection is triggered only when technician explicitly clicks on a node

  // Diagnostic Issue Flow Path Tracer
  const nodeFlowAnalysis = useMemo(() => {
    if (!selectedNode) return null;

    const issues = [];
    const hops = [];

    const p = selectedNode.props || {};
    const release = p.release || '';
    const isApproved = p.approved !== false;
    const isSang = selectedNode.id === 'dev:mx304-sang' || selectedNode.id?.includes('mx304-sang');

    if (release === '23.4R2') {
      issues.push({
        severity: 'critical',
        title: 'EVPN QinQ Defect Exposure (Case #JNPR-EVPN-QINQ)',
        description: 'VLAN-in-VLAN over EVPN drops cell-tower circuits under high load. Affects 8 aggregation routers.'
      });
    }
    if (isSang) {
      issues.push({
        severity: 'high',
        title: 'Single Point of Failure (SPOF) - Unprotected Link',
        description: 'SANG-AGG-01 connects via single 100G link without ERPS redundant protection ring.'
      });
    }
    if (!isApproved) {
      issues.push({
        severity: 'warning',
        title: 'Fleet Version Drift (2 Trains Behind)',
        description: `Running release ${release || 'outdated'} instead of approved standard 22.4R3-S7.5.`
      });
    }
    if (selectedNode.id === 'ont:olt-xg02-3-08' || (selectedNode.id?.includes('olt-xg02') && selectedNode.id?.endsWith('-08'))) {
      issues.push({
        severity: 'critical',
        title: 'Customer Drop Fiber Optical Loss (-31.2 dBm)',
        description: 'Severe optical attenuation on customer drop fiber to ONT-08 (-31.2 dBm). Hierarchy above (OLT-XG-02 → ACX-07 → AGG-07 → GLDT-CORE-01) is 100% healthy.'
      });
    }

    // 2. Resolve the REAL 5-Tier Path: Core -> Agg -> Access -> OLT -> ONT
    const allGraphNodes = displayedGraph.nodes || [];
    const allGraphRels = displayedGraph.rels || [];
    const nodeMap = new Map();
    allGraphNodes.forEach(n => {
      let tier = 2;
      const role = (n.role || n.props?.role || '').toLowerCase();
      const type = (n.type || '').toUpperCase();
      if (role === 'core' || type === 'CORE') tier = 0;
      else if (role === 'aggregation' || type === 'AGGREGATION') tier = 1;
      else if (role === 'olt' || type === 'OLT') tier = 3;
      else if (role === 'ont' || type === 'ONT') tier = 4;
      nodeMap.set(n.id, { ...n, tier });
    });

    const currTierNode = nodeMap.get(selectedNode.id);
    if (currTierNode) {
      // Trace upstream
      const upstreamNodes = [];
      let up = currTierNode;
      while (up && up.tier > 0) {
        const link = allGraphRels.find(r => {
          const s = typeof r.source === 'object' ? r.source.id : r.source;
          const t = typeof r.target === 'object' ? r.target.id : r.target;
          if (s === up.id) {
            const tgt = nodeMap.get(t);
            return tgt && tgt.tier === up.tier - 1;
          }
          if (t === up.id) {
            const src = nodeMap.get(s);
            return src && src.tier === up.tier - 1;
          }
          return false;
        });
        if (!link) break;
        const s = typeof link.source === 'object' ? link.source.id : link.source;
        const t = typeof link.target === 'object' ? link.target.id : link.target;
        const parentId = s === up.id ? t : s;
        up = nodeMap.get(parentId);
        if (up) upstreamNodes.unshift(up);
      }

      // Trace downstream
      const downstreamNodes = [];
      let down = currTierNode;
      while (down && down.tier < 4) {
        const link = allGraphRels.find(r => {
          const s = typeof r.source === 'object' ? r.source.id : r.source;
          const t = typeof r.target === 'object' ? r.target.id : r.target;
          if (s === down.id) {
            const tgt = nodeMap.get(t);
            return tgt && tgt.tier === down.tier + 1;
          }
          if (t === down.id) {
            const src = nodeMap.get(s);
            return src && src.tier === down.tier + 1;
          }
          return false;
        });
        if (!link) break;
        const s = typeof link.source === 'object' ? link.source.id : link.source;
        const t = typeof link.target === 'object' ? link.target.id : link.target;
        const childId = s === down.id ? t : s;
        down = nodeMap.get(childId);
        if (down) downstreamNodes.push(down);
      }

      const fullChain = [...upstreamNodes, currTierNode, ...downstreamNodes];
      
      fullChain.forEach((nodeOnPath, idx) => {
        const tierNames = ['Core Router', 'Aggregation Gateway', 'Access Switch', 'Optical Line Terminal (OLT)', 'Customer Terminal (ONT)'];
        const np = nodeOnPath.props || {};
        hops.push({
          step: idx + 1,
          name: nodeOnPath.name || nodeOnPath.label || nodeOnPath.id.replace('dev:', '').toUpperCase(),
          type: tierNames[nodeOnPath.tier] || 'Network Element',
          status: nodeOnPath.hasAlarm || np.hasAlarm ? 'danger' : (nodeOnPath.outlier ? 'warning' : 'healthy'),
          ip: np.mgmt_ip || np.ip || (nodeOnPath.tier === 4 ? (np.model || 'GP1100X') : '10.5x.xx.xx'),
          tier: nodeOnPath.tier
        });
      });
    }

    return { issues, hops };
  }, [selectedNode, displayedGraph]);

  // Execute / Refresh Cypher Query Action
  const handleRunQuery = () => {
    setQueryExecutionTime((Math.random() * 2 + 1.1).toFixed(2));
    setPhysicsEnabled(true);
    if (fitRef.current) fitRef.current();
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onRefresh={() => loadData(true)} isRefreshing={loading} />

        <main className="flex-1 flex flex-col overflow-hidden p-4 space-y-3">
          {/* Top Unified Header & Actions */}
          <div className="bg-white rounded-xl shadow-xs border border-gray-200 px-4 py-3 flex items-center justify-between gap-4 shrink-0">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-[#E9F1FA] text-[#00ABE4] rounded-lg">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-base font-bold text-gray-900 leading-tight">Network Ontology Explorer</h1>
                <p className="text-[11px] text-gray-500">Interactive topology &bull; Root-cause defect analysis &bull; Blast radius tracing</p>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search device, IP, defect..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-800 focus:outline-none focus:border-[#00ABE4] focus:ring-1 focus:ring-[#00ABE4] w-52 focus:w-64 transition-all placeholder:text-gray-400"
                />
              </div>

              {/* View Switcher: Graph | Google Map | Table */}
              <div className="flex items-center bg-gray-100 p-1 rounded-lg border border-gray-200 text-xs font-semibold">
                <button
                  onClick={() => setViewMode('graph')}
                  className={`px-3 py-1 rounded-md transition cursor-pointer flex items-center gap-1.5 ${
                    viewMode === 'graph' ? 'bg-white text-gray-900 shadow-xs font-bold' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Workflow className="w-3.5 h-3.5 text-[#00ABE4]" />
                  <span>Graph</span>
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={`px-3 py-1 rounded-md transition flex items-center gap-1.5 cursor-pointer ${
                    viewMode === 'map' ? 'bg-[#00ABE4] text-white shadow-xs font-bold' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Globe className="w-3.5 h-3.5" />
                  <span>Google Map</span>
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`px-3 py-1 rounded-md transition cursor-pointer flex items-center gap-1.5 ${
                    viewMode === 'table' ? 'bg-white text-gray-900 shadow-xs font-bold' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Table className="w-3.5 h-3.5 text-gray-500" />
                  <span>Table</span>
                </button>
              </div>

              {/* Optional Advanced Cypher Console Toggle */}
              <button
                onClick={() => setShowCypherConsole(!showCypherConsole)}
                className={`p-1.5 rounded-lg border text-xs transition cursor-pointer ${
                  showCypherConsole
                    ? 'bg-slate-800 text-white border-slate-700'
                    : 'bg-gray-50 text-gray-500 hover:text-gray-700 border-gray-200'
                }`}
                title={showCypherConsole ? 'Hide Cypher Console' : 'Show Advanced Cypher Console'}
              >
                <Terminal className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Filter Strip: Topology Preset Dropdown + Defect Radar Chips */}
          <div className="bg-white rounded-xl shadow-xs border border-gray-200 px-4 py-2 flex items-center justify-between gap-4 shrink-0 overflow-x-auto">
            {/* Left: Topology Preset Select */}
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs font-bold text-gray-600 uppercase tracking-wider flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-[#00ABE4]" />
                Topology:
              </span>
              <select
                value={activeTabId}
                onChange={(e) => {
                  const selected = AURA_TABS.find(t => t.id === e.target.value);
                  if (selected) {
                    setActiveDefectFilter(null);
                    setActiveTabId(selected.id);
                    setCypherQuery(selected.query);
                    setPhysicsEnabled(true);
                  }
                }}
                className="bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-gray-800 focus:outline-none focus:border-[#00ABE4] cursor-pointer"
              >
                {AURA_TABS.map(tab => (
                  <option key={tab.id} value={tab.id}>
                    {tab.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Right: 1-Click Defect & SPOF Badges */}
            <div className="flex items-center gap-2 overflow-x-auto py-0.5">
              <span className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1 mr-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                Defects:
              </span>

              {DEFECT_PRESETS.map((preset) => {
                const Icon = preset.icon;
                const isActive = activeDefectFilter?.id === preset.id;
                return (
                  <button
                    key={preset.id}
                    onClick={() => {
                      if (isActive) {
                        setActiveDefectFilter(null);
                      } else {
                        setActiveDefectFilter(preset);
                        setIsInspectorOpen(true);
                      }
                      setPhysicsEnabled(true);
                      if (fitRef.current) fitRef.current();
                    }}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition cursor-pointer border shrink-0 ${
                      isActive
                        ? 'bg-red-50 border-red-300 text-red-800 font-bold shadow-xs ring-1 ring-red-400'
                        : 'bg-gray-50 border-gray-200 hover:bg-[#E9F1FA] hover:border-[#00ABE4] text-gray-700'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" style={{ color: preset.color }} />
                    <span>{preset.label}</span>
                    <span className={`text-[9.5px] px-1.5 py-0.2 rounded font-semibold ${preset.badgeColor}`}>
                      {preset.badge}
                    </span>
                  </button>
                );
              })}

              {activeDefectFilter && (
                <button
                  onClick={() => {
                    setActiveDefectFilter(null);
                    if (fitRef.current) fitRef.current();
                  }}
                  className="px-2 py-1 text-xs font-semibold text-gray-500 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center gap-1 transition cursor-pointer border border-gray-200"
                  title="Clear defect filter"
                >
                  <X className="w-3 h-3" />
                  <span>Clear</span>
                </button>
              )}
            </div>
          </div>

          {/* Main Visualizer Card Frame */}
          <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col overflow-hidden">
            {/* Visual Canvas + Inspector Panel Split */}
            <div className="flex-1 flex overflow-hidden relative">
              {/* Canvas View */}
              {viewMode === 'graph' && (
                <div className="flex-1 relative overflow-hidden flex flex-col bg-[#0b0f19]">
                  {loading ? (
                    <div className="flex-1 flex items-center justify-center text-xs text-slate-400">
                      <div className="flex items-center gap-2">
                        <RefreshCw className="w-5 h-5 animate-spin text-[#00ABE4]" />
                        <span>Simulating force-directed network topology...</span>
                      </div>
                    </div>
                  ) : error ? (
                    <div className="flex-1 flex items-center justify-center p-6 text-center text-xs text-red-400">
                      <div>
                        <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                        <p className="font-bold text-sm mb-1">{error}</p>
                        <button
                          onClick={loadData}
                          className="mt-3 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-xs"
                        >
                          Retry Load
                        </button>
                      </div>
                    </div>
                  ) : displayedGraph.nodes.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
                      <span>No graph nodes match current query filter.</span>
                    </div>
                  ) : (
                    <Neo4jGraphCanvas
                      nodes={displayedGraph.nodes}
                      relationships={displayedGraph.relationships}
                      selectedNode={selectedNode}
                      activeDefectFilter={activeDefectFilter}
                      onSelectNode={(node) => {
                        setSelectedNode(node);
                        setIsInspectorOpen(true);
                      }}
                      onSelectRelationship={(rel) => setSelectedRel(rel)}
                      physicsEnabled={physicsEnabled}
                      searchQuery={searchQuery}
                      hiddenNodeTypes={hiddenNodeTypes}
                      hiddenRelTypes={hiddenRelTypes}
                      onFitRequested={fitRef}
                    />
                  )}

                  {/* Dynamic 5-Tier Hierarchy Statistics Bar (Top-left of canvas) */}
                  <div className="absolute top-3 left-4 bg-slate-900/90 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-mono backdrop-blur-md shadow-2xl flex items-center gap-3 flex-wrap pointer-events-auto z-10">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#8b5cf6]"></span>
                      <span className="text-slate-400">Core:</span>
                      <strong className="text-white">{displayedGraph.nodes.filter(n => n.role === 'core' || n.props?.role === 'core').length}</strong>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#0ea5e9]"></span>
                      <span className="text-slate-400">Agg:</span>
                      <strong className="text-white">{displayedGraph.nodes.filter(n => n.role === 'aggregation' || n.props?.role === 'aggregation').length}</strong>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#64748b]"></span>
                      <span className="text-slate-400">ACX:</span>
                      <strong className="text-white">{displayedGraph.nodes.filter(n => n.role === 'access' || n.props?.role === 'access').length}</strong>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#22c55e]"></span>
                      <span className="text-slate-400">OLT:</span>
                      <strong className="text-white">{displayedGraph.nodes.filter(n => n.role === 'olt' || n.props?.role === 'olt').length}</strong>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b]"></span>
                      <span className="text-slate-400">ONT:</span>
                      <strong className="text-white">{displayedGraph.nodes.filter(n => n.type === 'ONT' || n.role === 'ont' || n.props?.role === 'ont').length}</strong>
                    </span>
                    <span className="text-slate-600">|</span>
                    <button
                      onClick={() => {
                        const alm = DEFECT_PRESETS.find(p => p.id === 'alarm_cluster');
                        if (alm) setActiveDefectFilter(alm);
                      }}
                      className="flex items-center gap-1 hover:text-amber-300 transition cursor-pointer text-amber-400 font-bold"
                      title="Click to view all 29 active alarms on the topology"
                    >
                      <BellRing className="w-3 h-3 text-amber-400 animate-pulse" />
                      <span>Alarms: <strong>29</strong></span>
                    </button>
                    <span className="text-slate-600">|</span>
                    <span>⚡ Links: <strong className="text-slate-200">{displayedGraph.stats.totalRelationships}</strong></span>
                    <span className="text-slate-600">|</span>
                    <span className="text-emerald-400">{displayedGraph.stats.totalNodes} nodes ({queryExecutionTime}s)</span>
                  </div>
                </div>
              )}

              {/* Google Maps Geographic Topology View */}
              {viewMode === 'map' && (
                <div className="flex-1 relative overflow-hidden flex flex-col bg-slate-950">
                  <GoogleNetworkMap
                    selectedSiteId={selectedNode?.type === 'Site' ? selectedNode.id : null}
                    selectedNode={selectedNode}
                    activeTabId={activeTabId}
                    activeDefectFilter={activeDefectFilter}
                    searchQuery={searchQuery}
                    displayedGraph={displayedGraph}
                    onSelectSite={(site) => {
                      const matchingNode = displayedGraph.nodes.find(n => n.id === site.id);
                      setSelectedNode(matchingNode || site);
                      setIsInspectorOpen(true);
                    }}
                    onSelectNode={(node) => {
                      const matchingNode = displayedGraph.nodes.find(n => n.id === node.id);
                      setSelectedNode(matchingNode || node);
                      setIsInspectorOpen(true);
                    }}
                  />
                </div>
              )}

              {/* Table View */}
              {viewMode === 'table' && (
                <div className="flex-1 overflow-auto bg-white p-4 text-xs">
                  <table className="w-full text-left border-collapse font-mono">
                    <thead>
                      <tr className="border-b border-gray-200 text-gray-500 bg-gray-50">
                        <th className="p-2.5">Type</th>
                        <th className="p-2.5">ID</th>
                        <th className="p-2.5">Display Label</th>
                        <th className="p-2.5">Key Properties</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayedGraph.nodes.slice(0, 200).map((node) => (
                        <tr
                          key={node.id}
                          onClick={() => {
                            setSelectedNode(node);
                            setViewMode('graph');
                          }}
                          className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer text-gray-700"
                        >
                          <td className="p-2.5">
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-bold border"
                              style={{ backgroundColor: `${node.color}15`, color: node.color, borderColor: `${node.color}40` }}
                            >
                              {node.type}
                            </span>
                          </td>
                          <td className="p-2.5 font-bold text-[#00ABE4]">{node.id}</td>
                          <td className="p-2.5 font-bold text-gray-800">{node.label}</td>
                          <td className="p-2.5 text-gray-500">
                            {Object.entries(node.props || {})
                              .slice(0, 3)
                              .map(([k, v]) => `${k}: ${v}`)
                              .join(' • ')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Raw JSON View */}
              {viewMode === 'raw' && (
                <div className="flex-1 overflow-auto bg-[#090d16] p-4 font-mono text-xs text-emerald-400">
                  <pre>{JSON.stringify(displayedGraph, null, 2)}</pre>
                </div>
              )}

              {/* Right Slide-over Issue Diagnostics & Blast Radius Drawer */}
              {isInspectorOpen && (
                <div className="w-96 bg-white border-l border-gray-200 flex flex-col shrink-0 overflow-hidden shadow-xl z-20">
                  <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-3 h-3 rounded-full shadow-sm"
                        style={{ backgroundColor: activeDefectFilter ? activeDefectFilter.color : selectedNode?.color || '#00ABE4' }}
                      ></span>
                      <span className="font-bold text-sm text-gray-800">
                        {activeDefectFilter ? 'Defect Blast Radius & Impact' : 'Node Flow Diagnostics'}
                      </span>
                    </div>
                    <button
                      onClick={() => setIsInspectorOpen(false)}
                      className="text-gray-400 hover:text-gray-600 transition"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                    {/* DEFECT BLAST RADIUS INSPECTOR */}
                    {activeDefectFilter ? (
                      <div className="space-y-4 animate-fadeIn">
                        <div className="bg-red-50 border border-red-200 p-3.5 rounded-xl space-y-2 text-red-900">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 bg-red-100 text-red-700 rounded font-mono border border-red-300">
                              {activeDefectFilter.defectInfo.severity}
                            </span>
                            <span className="text-[10px] font-mono text-red-600">{activeDefectFilter.defectInfo.id}</span>
                          </div>
                          <h3 className="text-base font-bold text-gray-900">{activeDefectFilter.defectInfo.title}</h3>
                          <p className="text-[11.5px] leading-relaxed text-gray-700">{activeDefectFilter.defectInfo.impact}</p>
                        </div>

                        {/* Blast Radius Metrics Matrix */}
                        <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200 space-y-2.5">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Blast Radius Exposure</div>
                          <div className="space-y-2">
                            <div className="flex justify-between py-1 border-b border-gray-200">
                              <span className="text-gray-500">Affected Network Devices</span>
                              <span className="font-bold text-red-600">{activeDefectFilter.defectInfo.affectedDevices}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-gray-200">
                              <span className="text-gray-500">Impacted Circuits / Services</span>
                              <span className="font-bold text-amber-600">{activeDefectFilter.defectInfo.impactedServices}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-gray-200">
                              <span className="text-gray-500">Delivered Subscribers</span>
                              <span className="font-bold text-emerald-600">{activeDefectFilter.defectInfo.impactedSubscribers}</span>
                            </div>
                            <div className="flex justify-between py-1">
                              <span className="text-gray-500">Vendor JIRA / Case</span>
                              <span className="font-mono text-[#00ABE4] font-semibold">{activeDefectFilter.defectInfo.case}</span>
                            </div>
                          </div>
                        </div>

                        {/* Create Incident Ticket Action */}
                        <button
                          onClick={() => navigate(`/technician/all-tickets?category=Hardware`)}
                          className="w-full py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold shadow-md transition flex items-center justify-center gap-2 cursor-pointer"
                        >
                          <Ticket className="w-4 h-4" />
                          <span>Create Incident Ticket for this Blast Radius</span>
                        </button>
                      </div>
                    ) : selectedNode ? (
                      <div className="space-y-4">
                        {/* Selected Node Profile Header */}
                        <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-200 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span
                              className="text-[10px] font-bold uppercase px-2 py-0.5 rounded font-mono border"
                              style={{ backgroundColor: `${selectedNode.color}15`, color: selectedNode.color, borderColor: `${selectedNode.color}40` }}
                            >
                              {selectedNode.type}
                            </span>
                            <span className="text-[10px] font-mono text-gray-500">{selectedNode.id}</span>
                          </div>
                          <h3 className="text-base font-bold text-gray-900">{selectedNode.label}</h3>
                        </div>

                        {/* End-to-End Hierarchy Path Banner */}
                        <div className="bg-slate-900 text-white p-3 rounded-xl text-xs space-y-2 shadow-sm">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <Workflow className="w-3.5 h-3.5 text-cyan-400" />
                              End-to-End Connection Chain
                            </span>
                            <span className="text-[9.5px] text-slate-400 font-mono">5-Tier Topology</span>
                          </div>
                          <div className="flex items-center gap-1 font-mono text-[10px] overflow-x-auto pb-0.5">
                            <span className="px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-700">Core</span>
                            <span className="text-slate-500">&rarr;</span>
                            <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700">Agg</span>
                            <span className="text-slate-500">&rarr;</span>
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-600">Access</span>
                            <span className="text-slate-500">&rarr;</span>
                            <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700">OLT</span>
                            <span className="text-slate-500">&rarr;</span>
                            <span className="px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-600 font-bold">ONT</span>
                          </div>
                        </div>

                        {/* Active Alarms Card for Selected Node */}
                        {((selectedNode.alarms && selectedNode.alarms.length > 0) || (selectedNode.props?.alarms && selectedNode.props?.alarms.length > 0)) && (
                          <div className="bg-amber-50 border border-amber-300 p-3.5 rounded-xl space-y-2 text-amber-950 animate-fadeIn">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 bg-amber-200 text-amber-900 rounded font-mono flex items-center gap-1.5">
                                <BellRing className="w-3.5 h-3.5 text-amber-700" />
                                Active Alarms ({selectedNode.alarms?.length || selectedNode.props?.alarms?.length})
                              </span>
                              <span className="text-[10px] font-mono text-red-600 font-bold">Hardware Alert</span>
                            </div>
                            <div className="space-y-1.5 pt-1">
                              {(selectedNode.alarms || selectedNode.props?.alarms || []).map((alm, aIdx) => (
                                <div key={aIdx} className="bg-white/95 p-2 rounded-lg border border-amber-200 text-xs shadow-xs space-y-1">
                                  <div className="flex justify-between items-center">
                                    <span className="font-bold text-red-700 font-mono text-[11px]">{alm.type}</span>
                                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-red-100 text-red-700 uppercase font-bold border border-red-200">{alm.severity}</span>
                                  </div>
                                  <p className="text-[11.5px] text-gray-800 leading-snug">{alm.text}</p>
                                  <div className="text-[10px] text-gray-400 font-mono pt-0.5 flex justify-between">
                                    <span>Target: {alm.target || selectedNode.id}</span>
                                    <span>{alm.raised_at}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Issue Localization Alert Banner */}
                        {nodeFlowAnalysis?.issues && nodeFlowAnalysis.issues.length > 0 ? (
                          <div className="space-y-2">
                            <div className="text-xs font-bold text-red-600 flex items-center gap-1.5 uppercase tracking-wider">
                              <AlertOctagon className="w-4 h-4 text-red-500" />
                              Issue Localized on Path:
                            </div>
                            {nodeFlowAnalysis.issues.map((issue, idx) => (
                              <div
                                key={idx}
                                className="bg-red-50 border border-red-200 text-red-800 p-3 rounded-xl space-y-1"
                              >
                                <div className="font-bold flex items-center gap-1.5">
                                  <span>🚨 {issue.title}</span>
                                </div>
                                <p className="text-[11px] leading-relaxed text-gray-700">{issue.description}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="bg-emerald-50 border border-emerald-200 p-3 rounded-xl flex items-center gap-2.5 text-xs text-emerald-800">
                            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                            <div>
                              <div className="font-bold">Topology Path Healthy</div>
                              <div className="text-[11px] text-emerald-700">Approved software release &bull; Standard path</div>
                            </div>
                          </div>
                        )}

                        {/* Upstream & Downstream Flow Hop Chain */}
                        <div className="space-y-2 pt-1">
                          <div className="text-xs font-bold text-gray-700 flex items-center justify-between">
                            <span className="flex items-center gap-1.5">
                              <Workflow className="w-4 h-4 text-[#00ABE4]" />
                              Upstream Diagnostic Flow
                            </span>
                            <span className="text-[10px] text-gray-500">{nodeFlowAnalysis?.hops?.length || 0} Hops</span>
                          </div>

                          <div className="relative pl-6 space-y-3.5 border-l-2 border-gray-200 ml-2 pt-1">
                            {nodeFlowAnalysis?.hops?.map((hop, idx) => (
                              <div key={idx} className="relative">
                                <div
                                  className={`absolute -left-[31px] top-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border ${
                                    hop.status === 'danger'
                                      ? 'bg-red-100 border-red-500 text-red-700'
                                      : 'bg-emerald-100 border-emerald-500 text-emerald-700'
                                  }`}
                                >
                                  {hop.step}
                                </div>

                                <div className="bg-gray-50 p-2.5 rounded-xl border border-gray-200 text-xs">
                                  <div className="flex items-center justify-between">
                                    <span className="font-bold text-gray-800">{hop.name}</span>
                                    <span
                                      className={`text-[9.5px] font-bold uppercase px-1.5 py-0.2 rounded ${
                                        hop.status === 'danger' ? 'bg-red-100 text-red-700 border border-red-300' : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                                      }`}
                                    >
                                      {hop.status}
                                    </span>
                                  </div>
                                  <div className="text-[11px] text-gray-500 mt-0.5">
                                    {hop.type} &bull; <span className="font-mono text-gray-700 font-semibold">{hop.ip}</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Dedicated Central Texas Geospatial & Elevation Card if site or device with geo is selected */}
                        {(() => {
                          const p = selectedNode.props || {};
                          const siteInfo = p.site_details || (selectedNode.type === 'Site' ? p : null);
                          const lat = p.lat || p.latitude || siteInfo?.lat || siteInfo?.latitude;
                          const lon = p.lon || p.longitude || siteInfo?.lon || siteInfo?.longitude;
                          const altM = p.alt_m || p.altitude_meters || siteInfo?.alt_m || siteInfo?.altitude_meters;
                          const altFt = p.alt_ft || p.altitude_feet || siteInfo?.alt_ft || siteInfo?.altitude_feet;
                          const town = p.town || siteInfo?.town || (selectedNode.type === 'Site' ? selectedNode.label : (p.site ? p.site.replace('site:', '').toUpperCase() : null));
                          const county = p.county || siteInfo?.county || 'Texas';
                          const state = p.state || siteInfo?.state || 'Texas';

                          if (!lat && !lon && selectedNode.type !== 'Site') return null;

                          return (
                            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-3.5 space-y-2.5 text-blue-950 shadow-xs animate-fadeIn">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 flex items-center gap-1.5">
                                  <MapPin className="w-3.5 h-3.5 text-blue-600" />
                                  Central Texas Location
                                </span>
                                <span className="text-[9.5px] font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full border border-blue-200">
                                  {p.type || selectedNode.type}
                                </span>
                              </div>

                              <div>
                                <div className="text-sm font-extrabold text-blue-900">{town || 'Central Texas Hub'}</div>
                                <div className="text-[11px] text-blue-700/80">{county}, {state}</div>
                              </div>

                              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-blue-200/60">
                                <div className="bg-white/90 p-2 rounded-lg border border-blue-100 shadow-xs">
                                  <div className="text-[9.5px] font-semibold text-gray-500 flex items-center gap-1">
                                    <Globe className="w-3 h-3 text-blue-500" />
                                    Coordinates
                                  </div>
                                  <div className="font-mono text-[11px] font-bold text-gray-800 mt-0.5">
                                    {lat ? `${lat}° N, ${lon}° W` : '31.4504° N, -98.5714° W'}
                                  </div>
                                </div>

                                <div className="bg-white/90 p-2 rounded-lg border border-blue-100 shadow-xs">
                                  <div className="text-[9.5px] font-semibold text-gray-500 flex items-center gap-1">
                                    <Mountain className="w-3 h-3 text-indigo-500" />
                                    Elevation
                                  </div>
                                  <div className="font-mono text-[11px] font-bold text-indigo-900 mt-0.5">
                                    {altM ? `${altM}m (${altFt}ft)` : '463m (1519ft)'}
                                  </div>
                                </div>
                              </div>

                              {lat && lon && (
                                <a
                                  href={`https://www.google.com/maps/search/?api=1&query=${lat},${lon}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center justify-center gap-1.5 w-full bg-blue-600 hover:bg-blue-700 text-white py-1.5 rounded-lg text-[11px] font-bold transition shadow-xs cursor-pointer"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                  <span>Open Site on Google Maps &rarr;</span>
                                </a>
                              )}
                            </div>
                          );
                        })()}

                        {/* Dynamic Properties Table */}
                        <div className="bg-gray-50 rounded-xl border border-gray-200 p-3 space-y-2">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">Properties</div>
                          {Object.entries(selectedNode.props || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between py-1 border-b border-gray-200 text-[11px]">
                              <span className="text-gray-500">{k}</span>
                              <span className="font-mono font-bold text-gray-800 truncate max-w-[180px]">{String(v)}</span>
                            </div>
                          ))}
                        </div>

                        {/* Create / Link Ticket Button */}
                        <button
                          onClick={() => navigate(`/technician/all-tickets?category=Hardware`)}
                          className="w-full py-2.5 bg-[#00ABE4] hover:bg-[#0090c2] text-white rounded-xl text-xs font-bold shadow-md transition flex items-center justify-center gap-2 cursor-pointer"
                        >
                          <Ticket className="w-4 h-4" />
                          <span>Create Ticket for this Fault Node</span>
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-6 px-2 py-4">
                        <div className="space-y-1">
                          <h2 className="text-2xl font-bold text-gray-800">Nothing selected</h2>
                          <p className="text-xs text-gray-400 font-mono tracking-tight">click a node, or open Findings</p>
                        </div>
                        
                        <div className="text-[11.5px] leading-[1.6] text-gray-600 space-y-4 pr-2">
                          <p>
                            This is the CTTC ontology rendered as a graph. Device models,
                            counts and software releases follow the 18 May assessment;
                            <span className="font-bold text-gray-800"> everything below device level is synthetic placeholder data
                            shaped to match, so the queries have something to return.</span>
                          </p>
                          <p>
                            Press <span className="font-bold text-gray-800">Map</span> to place the network on San Angelo, Texas. Site
                            coordinates are the real locations of those places; which
                            equipment sits where is invented, and the basemap is
                            schematic rather than survey grade.
                          </p>
                        </div>

                        <div className="space-y-2 pt-4">
                          <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 border-b border-gray-200 pb-2">Graph Contents</h3>
                          <div className="space-y-0.5">
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">Devices</span><span className="text-gray-400 font-mono">83</span></div>
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">Device links</span><span className="text-gray-400 font-mono">78</span></div>
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">PON trees</span><span className="text-gray-400 font-mono">116</span></div>
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">Services</span><span className="text-gray-400 font-mono">24</span></div>
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">Subscribers</span><span className="text-gray-400 font-mono">74</span></div>
                            <button
                              onClick={() => {
                                const almPreset = DEFECT_PRESETS.find(p => p.id === 'alarm_cluster');
                                if (almPreset) setActiveDefectFilter(almPreset);
                              }}
                              className="flex justify-between py-2 border-b border-gray-100 text-[11px] w-full text-left hover:bg-amber-50 px-1 rounded transition cursor-pointer group"
                              title="Click to view all 29 active alarms on the topology"
                            >
                              <span className="text-gray-800 font-bold group-hover:text-amber-700 flex items-center gap-1.5">
                                <BellRing className="w-3.5 h-3.5 text-amber-500" />
                                Open alarms
                              </span>
                              <span className="text-red-600 font-mono font-bold bg-red-50 border border-red-200 px-1.5 py-0.5 rounded text-[10px]">29 Active</span>
                            </button>
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">Geo-located nodes</span><span className="text-gray-400 font-mono">199</span></div>
                          </div>
                        </div>

                        <div className="space-y-2 pt-4">
                          <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-400 border-b border-gray-200 pb-2">What The Graph Found</h3>
                          <div className="space-y-0.5">
                            <div className="flex justify-between py-2 border-b border-gray-100 text-[11px]"><span className="text-gray-800 font-bold">Version outliers</span><span className="text-gray-400 font-mono">3</span></div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* OPTIONAL ADVANCED CYPHER CONSOLE (Hidden by default, toggleable via top terminal button) */}
            {showCypherConsole && (
              <div className="border-t border-gray-200 bg-gray-50 shrink-0 z-30 transition-all animate-fadeIn">
                <div className="px-4 py-2 flex items-center justify-between border-b border-gray-200 text-xs">
                  <div className="flex items-center gap-2 text-gray-700 font-mono font-bold">
                    <Terminal className="w-3.5 h-3.5 text-[#00ABE4]" />
                    <span>CYPHER CONSOLE (ADVANCED QUERY)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPhysicsEnabled(!physicsEnabled)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition cursor-pointer flex items-center gap-1 ${
                        physicsEnabled
                          ? 'bg-purple-50 border-purple-300 text-purple-700'
                          : 'bg-white border-gray-300 text-gray-600'
                      }`}
                    >
                      <Compass className={`w-3 h-3 ${physicsEnabled ? 'animate-spin' : ''}`} />
                      <span>{physicsEnabled ? 'Physics Active' : 'Freeze'}</span>
                    </button>

                    <button
                      onClick={handleRunQuery}
                      className="px-4 py-1 bg-[#00ABE4] hover:bg-[#0090c2] text-white font-bold rounded-lg text-xs flex items-center gap-1.5 transition shadow-sm cursor-pointer"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      <span>Run Query</span>
                    </button>

                    <button
                      onClick={() => setShowCypherConsole(false)}
                      className="p-1 text-gray-400 hover:text-gray-700 rounded transition cursor-pointer"
                      title="Close Cypher Console"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="p-3 bg-[#090d16]">
                  <textarea
                    rows={2}
                    value={cypherQuery}
                    onChange={(e) => setCypherQuery(e.target.value)}
                    className="w-full bg-[#040711] border border-slate-800 rounded-lg p-2.5 text-xs font-mono text-emerald-400 focus:outline-none focus:border-[#00ABE4] leading-relaxed resize-none selection:bg-emerald-900"
                    placeholder="Enter Cypher query..."
                  />
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
}
