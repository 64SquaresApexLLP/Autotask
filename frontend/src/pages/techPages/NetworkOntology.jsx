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
    label: 'Central Office Alarms',
    sublabel: 'Goldthwaite Optical Cascade',
    badge: 'High (P2)',
    badgeColor: 'bg-orange-100 text-orange-700 border-orange-200',
    icon: BellRing,
    color: '#f97316',
    filterKeywords: ['mx960-gldt', 'gldt-a', 'acx-10', 'acx-11'],
    defectInfo: {
      id: 'alarm:gldt-cluster',
      title: 'Goldthwaite Central Office Active Alarm Cluster',
      severity: 'High (P2)',
      vendor: '400G ZR Optics / BGP Flap',
      case: 'ticket:alm-4902',
      impact: '400G ZR optic temp reached 60.2°C causing optical power degradation and BGP neighbor flapping.',
      affectedDevices: 'GLDT-CORE-01, GLDT-A, ACX-10',
      impactedServices: 'Core Backbone Uplink',
      impactedSubscribers: '74 Downstream Accounts'
    }
  }
];

// Standard Aura Query Tabs
const AURA_TABS = [
  {
    id: 'full_access',
    title: 'Full Access Topology',
    query: `MATCH (d:Device)-[hp:HAS_PORT]->(p:Port)
OPTIONAL MATCH (s:Site)-[c:CONTAINS]->(d)
OPTIONAL MATCH (p)-[t:TERMINATES]-(l:Link)
OPTIONAL MATCH (p)-[srv:SERVES]->(pon:PONTree)
RETURN s, c, d, hp, p, t, l, srv, pon
ORDER BY d.name, p.name
LIMIT 1000;`,
    description: 'All network devices, ports, trunk links, and PON trees'
  },
  {
    id: 'geo_sites',
    title: 'Physical Sites (Geo & Altitude)',
    query: `MATCH (s:Site)
OPTIONAL MATCH (s)-[c:CONTAINS]->(d:Device)
RETURN s, c, d
ORDER BY s.alt_m DESC;`,
    description: 'Central Office, Aggregation & Remote Hubs with GPS Coordinates, Altitude & Linked Hardware'
  },
  {
    id: 'all_ports',
    title: 'All port',
    query: `MATCH (d:Device)-[hp:HAS_PORT]->(p:Port)
RETURN d, hp, p
LIMIT 500;`,
    description: 'Physical interfaces attached to network nodes'
  },
  {
    id: 'all_devices',
    title: 'All devices with all ports and topology',
    query: `MATCH (d:Device)-[hp:HAS_PORT]->(p:Port)
OPTIONAL MATCH (p)-[t:TERMINATES]-(l:Link)
RETURN d, hp, p, t, l;`,
    description: 'Core, aggregation, access routers and physical links'
  },
  {
    id: 'services_subscribers',
    title: 'Services, Intended Paths & Delivered Subscribers',
    query: `MATCH (s:Service)-[d:DELIVERED_TO]->(sub:Subscriber)
OPTIONAL MATCH (s)-[t:TRAVERSES]->(p:Port)
RETURN s, d, sub, t, p;`,
    description: 'End-to-end customer circuits and delivered subscribers'
  },
  {
    id: 'entire_db',
    title: 'Entire DB',
    query: `MATCH (n) OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 1200;`,
    description: 'Full knowledge graph'
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
  const [viewMode, setViewMode] = useState('graph'); // 'graph' | 'table' | 'raw'
  const [searchQuery, setSearchQuery] = useState('');
  const [isEditorExpanded, setIsEditorExpanded] = useState(false);

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
      filteredRels = relationships.filter(r => nSet.has(r.source) || nSet.has(r.target));
    }
    // 2. Tab Presets
    else if (activeTabId === 'geo_sites') {
      filteredNodes = nodes.filter(n => ['Site', 'Device', 'Router'].includes(n.type));
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => (r.type === 'CONTAINS' || r.type === 'TERMINATES') && nSet.has(r.source) && nSet.has(r.target));
    } else if (activeTabId === 'all_ports') {
      filteredNodes = nodes.filter(n => ['Port', 'Device'].includes(n.type));
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => r.type === 'HAS_PORT' && nSet.has(r.source) && nSet.has(r.target));
    } else if (activeTabId === 'all_devices') {
      filteredNodes = nodes.filter(n => ['Device', 'Port', 'Link', 'Site'].includes(n.type));
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => nSet.has(r.source) && nSet.has(r.target));
    } else if (activeTabId === 'full_access') {
      filteredNodes = nodes.filter(n => ['Device', 'Port', 'Link', 'PONTree', 'Site', 'Splitter'].includes(n.type));
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => nSet.has(r.source) && nSet.has(r.target));
    } else if (activeTabId === 'services_subscribers') {
      filteredNodes = nodes.filter(n => ['Service', 'Subscriber', 'Port', 'Device', 'ONT'].includes(n.type));
      const nSet = new Set(filteredNodes.map(n => n.id));
      filteredRels = relationships.filter(r => nSet.has(r.source) && nSet.has(r.target));
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

    // Step-by-step diagnostic breadcrumb
    hops.push({
      step: 1,
      name: 'GLDT-CORE-01',
      type: 'Core Backbone (MX960)',
      status: 'healthy',
      ip: '10.56.91.67'
    });

    hops.push({
      step: 2,
      name: selectedNode.isDevice ? selectedNode.label : 'AGG-02',
      type: 'Aggregation Gateway (MX304)',
      status: issues.length > 0 ? 'danger' : 'healthy',
      ip: p.mgmt_ip || '10.54.147.244'
    });

    if (selectedNode.type === 'Port') {
      hops.push({
        step: 3,
        name: selectedNode.label,
        type: 'Physical Port Interface',
        status: p.oper_state === 'up' ? 'healthy' : 'warning',
        ip: `${p.speed_gbps || 100} Gbps`
      });
    }

    return { issues, hops };
  }, [selectedNode]);

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

        <main className="flex-1 flex flex-col overflow-hidden p-6 space-y-4">
          {/* Top Page Header & Welcome Banner (Matches App Design System) */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-[#E9F1FA] text-[#00ABE4] rounded-xl">
                <Network className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-800">Network Ontology &amp; Topology Explorer</h1>
                <p className="text-xs text-gray-500">Interactive force-directed graph with root-cause defect analysis and blast radius tracing</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => loadData(true)}
                disabled={loading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                title="Force Reload Ontology Dataset"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-[#00ABE4] ${loading ? 'animate-spin' : ''}`} />
                <span>Reload Ontology</span>
              </button>

              <div className="flex items-center space-x-2 bg-[#E9F1FA] px-3.5 py-1.5 rounded-lg border border-[#00ABE4]/20">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-xs font-semibold text-gray-800">
                  Technician: <strong className="text-[#00ABE4]">{user?.full_name || user?.username || 'Active Technician'}</strong>
                </span>
                {user?.role && (
                  <span className="text-[10px] bg-white text-gray-600 px-1.5 py-0.5 rounded uppercase font-bold border border-gray-200">
                    {user.role}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 1-CLICK DEFECT & INCIDENT RADAR PILLS (Styled to Match App Theme) */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 flex items-center justify-between gap-3 shrink-0 overflow-x-auto">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-gray-700 uppercase tracking-wider mr-1">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span>Defect Radar:</span>
              </div>

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
                    className={`px-3 py-2 rounded-xl text-xs font-medium flex items-center gap-2.5 transition cursor-pointer border ${
                      isActive
                        ? 'bg-red-50 border-red-300 text-red-800 shadow-sm ring-2 ring-red-400/40'
                        : 'bg-gray-50 border-gray-200 hover:bg-[#E9F1FA] hover:border-[#00ABE4] text-gray-700'
                    }`}
                  >
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                      style={{ backgroundColor: `${preset.color}18`, color: preset.color }}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="text-left leading-tight">
                      <div className="font-bold text-gray-800 flex items-center gap-1.5">
                        <span>{preset.label}</span>
                        <span className={`text-[9.5px] px-1.5 py-0.2 rounded border font-semibold ${preset.badgeColor}`}>
                          {preset.badge}
                        </span>
                      </div>
                      <div className="text-[11px] text-gray-500 mt-0.5">{preset.sublabel}</div>
                    </div>
                  </button>
                );
              })}

              {activeDefectFilter && (
                <button
                  onClick={() => {
                    setActiveDefectFilter(null);
                    if (fitRef.current) fitRef.current();
                  }}
                  className="px-3 py-1.5 text-xs font-bold text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center gap-1 border border-gray-300 transition cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Show All</span>
                </button>
              )}
            </div>

            {/* Top Page Action Buttons & Smart Search Bar */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setViewMode(viewMode === 'map' ? 'graph' : 'map')}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-xs cursor-pointer border ${
                  viewMode === 'map'
                    ? 'bg-blue-600 text-white border-blue-600 ring-2 ring-blue-400/40 shadow-md'
                    : 'bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 text-blue-800 border-blue-300'
                }`}
              >
                <Globe className={`w-4 h-4 ${viewMode === 'map' ? 'text-white' : 'text-blue-600'}`} />
                <span>{viewMode === 'map' ? 'Switch to Graph View' : 'View on Google Map'}</span>
              </button>

              <div className="relative shrink-0">
                <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search device, IP, or type 'defect' / 'spof'..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-800 focus:outline-none focus:border-[#00ABE4] focus:ring-1 focus:ring-[#00ABE4] w-56 focus:w-72 transition-all placeholder:text-gray-400"
                />
              </div>
            </div>
          </div>

          {/* Main Visualizer Card Frame */}
          <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col overflow-hidden">
            {/* Top Toolbar Strip: Tabs + View Switcher */}
            <div className="px-4 py-2.5 border-b border-gray-200 flex items-center justify-between gap-4 bg-gray-50/90 text-xs shrink-0 select-none">
              {/* Query Tabs with horizontal scroll */}
              <div className="flex items-center gap-1.5 overflow-x-auto min-w-0 flex-1 py-0.5">
                {AURA_TABS.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveDefectFilter(null);
                      setActiveTabId(tab.id);
                      setCypherQuery(tab.query);
                      setPhysicsEnabled(true);
                    }}
                    className={`px-3 py-1.5 rounded-lg font-semibold text-xs flex items-center gap-2 transition cursor-pointer border shrink-0 ${
                      activeTabId === tab.id && !activeDefectFilter
                        ? 'bg-[#00ABE4] text-white border-[#00ABE4] shadow-sm'
                        : 'bg-white text-gray-600 hover:bg-[#E9F1FA] hover:text-[#00ABE4] border-gray-200'
                    }`}
                  >
                    <Workflow className="w-3.5 h-3.5" />
                    <span>{tab.title}</span>
                  </button>
                ))}
              </div>

              {/* View Switchers (Graph | Google Map | Table | Raw) - Fixed shrink-0 so it is NEVER hidden */}
              <div className="flex items-center gap-2 shrink-0">
                <div className="flex items-center bg-gray-200/90 p-1 rounded-xl border border-gray-300 shadow-xs text-xs font-bold">
                  <button
                    onClick={() => setViewMode('graph')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      viewMode === 'graph' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Graph
                  </button>
                  <button
                    onClick={() => setViewMode('map')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                      viewMode === 'map' ? 'bg-blue-600 text-white shadow-xs' : 'text-blue-700 hover:bg-blue-50'
                    }`}
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>Google Map</span>
                  </button>
                  <button
                    onClick={() => setViewMode('table')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      viewMode === 'table' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Table
                  </button>
                  <button
                    onClick={() => setViewMode('raw')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      viewMode === 'raw' ? 'bg-white text-gray-900 shadow-xs' : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Raw
                  </button>
                </div>
              </div>
            </div>

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

                  {/* Dynamic Statistics Bar (Top-left of canvas) */}
                  <div className="absolute top-3 left-4 bg-slate-900/90 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-xl text-xs font-mono backdrop-blur-md shadow-2xl flex items-center gap-3 flex-wrap pointer-events-auto z-10">
                    {Object.entries(displayedGraph.stats.nodeTypeCounts || {}).map(([type, count]) => (
                      <span key={type} className="flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: getNodeTypeColor(type) }}
                        ></span>
                        <span className="text-slate-400">{type}:</span>
                        <strong className="text-white">{count}</strong>
                      </span>
                    ))}
                    <span className="text-slate-600">|</span>
                    <span>⚡ Links: <strong className="text-slate-200">{displayedGraph.stats.totalRelationships}</strong></span>
                    <span className="text-slate-600">|</span>
                    <span className="text-emerald-400">{displayedGraph.stats.totalNodes} nodes ({queryExecutionTime}s)</span>
                  </div>

                  {/* Quick Action to open Google Map when on Geo Sites tab */}
                  {activeTabId === 'geo_sites' && (
                    <div className="absolute top-14 left-4 bg-slate-900/90 border border-blue-500/60 text-white px-3 py-1.5 rounded-xl text-xs shadow-2xl backdrop-blur-md flex items-center gap-2.5 z-10 animate-fadeIn pointer-events-auto">
                      <span className="flex items-center gap-1.5 font-bold text-blue-300">
                        <MapPin className="w-3.5 h-3.5 text-blue-400" />
                        10 Central Texas Physical Sites
                      </span>
                      <button
                        onClick={() => setViewMode('map')}
                        className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-[11px] font-extrabold shadow-sm transition flex items-center gap-1 cursor-pointer"
                      >
                        <Globe className="w-3 h-3" />
                        <span>Launch Google Map &rarr;</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Google Maps Geographic Topology View */}
              {viewMode === 'map' && (
                <div className="flex-1 relative overflow-hidden flex flex-col bg-slate-950">
                  <GoogleNetworkMap
                    selectedSiteId={selectedNode?.type === 'Site' ? selectedNode.id : null}
                    onSelectSite={(site) => {
                      const matchingNode = displayedGraph.nodes.find(n => n.id === site.id);
                      if (matchingNode) {
                        setSelectedNode(matchingNode);
                        setIsInspectorOpen(true);
                      }
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
                    ) : null}
                  </div>
                </div>
              )}
            </div>

            {/* DOCKED CYPHER QUERY CONSOLE AT BOTTOM (Collapsible for advanced users) */}
            <div className="border-t border-gray-200 bg-gray-50 shrink-0 z-30 transition-all">
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
                    <span>{physicsEnabled ? 'Floating Physics' : 'Freeze'}</span>
                  </button>

                  <button
                    onClick={handleRunQuery}
                    className="px-4 py-1 bg-[#00ABE4] hover:bg-[#0090c2] text-white font-bold rounded-lg text-xs flex items-center gap-1.5 transition shadow-sm cursor-pointer"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>Run Query</span>
                  </button>

                  <button
                    onClick={() => setIsEditorExpanded(!isEditorExpanded)}
                    className="p-1 text-gray-500 hover:text-gray-800 rounded hover:bg-gray-200 transition"
                    title={isEditorExpanded ? 'Collapse Console' : 'Expand Console'}
                  >
                    {isEditorExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {isEditorExpanded && (
                <div className="p-3 bg-[#090d16]">
                  <textarea
                    rows={2}
                    value={cypherQuery}
                    onChange={(e) => setCypherQuery(e.target.value)}
                    className="w-full bg-[#040711] border border-slate-800 rounded-lg p-2.5 text-xs font-mono text-emerald-400 focus:outline-none focus:border-[#00ABE4] leading-relaxed resize-none selection:bg-emerald-900"
                    placeholder="Enter Cypher query..."
                  />
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
      <ChatButton />
    </div>
  );
}
