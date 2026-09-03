import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  MapPin,
  Mountain,
  Globe,
  Radio,
  Layers,
  Search,
  Key,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  RefreshCw,
  Eye,
  Maximize2,
  Navigation,
  Compass,
  Cpu,
  Server,
  Zap,
  Info,
  X,
  Flame,
  ShieldAlert,
  Network,
  Users,
  Building,
  BellRing,
  Filter,
  Check,
  ChevronLeft,
  ChevronRight,
  ShieldX,
  Ticket,
  Sparkles
} from 'lucide-react';
import { ontologyService } from '../services/ontologyService.js';

// Central Texas CTTC Sites Master Geospatial Coordinates
const SITE_GEO_LOCATIONS = {
  'site:gldt': { name: 'Goldthwaite Central Office', town: 'Goldthwaite', county: 'Mills County', state: 'Texas', lat: 31.4504, lng: -98.5714, alt_m: 463.0, alt_ft: 1519.0, type: 'central_office', isHub: true },
  'site:sang': { name: 'San Angelo Aggregation Site', town: 'San Angelo', county: 'Tom Green County', state: 'Texas', lat: 31.4638, lng: -100.4370, alt_m: 563.0, alt_ft: 1847.0, type: 'aggregation_site', isHub: true },
  'site:03': { name: 'Brady (Service Area 03)', town: 'Brady', county: 'McCulloch County', state: 'Texas', lat: 31.1352, lng: -99.3362, alt_m: 511.0, alt_ft: 1677.0, type: 'remote_site' },
  'site:04': { name: 'Brownwood (Service Area 04)', town: 'Brownwood', county: 'Brown County', state: 'Texas', lat: 31.7093, lng: -98.9912, alt_m: 422.0, alt_ft: 1385.0, type: 'remote_site' },
  'site:05': { name: 'Lampasas (Service Area 05)', town: 'Lampasas', county: 'Lampasas County', state: 'Texas', lat: 31.0649, lng: -98.1817, alt_m: 312.0, alt_ft: 1024.0, type: 'remote_site' },
  'site:06': { name: 'Llano (Service Area 06)', town: 'Llano', county: 'Llano County', state: 'Texas', lat: 30.7593, lng: -98.6750, alt_m: 314.0, alt_ft: 1030.0, type: 'remote_site' },
  'site:07': { name: 'Mason (Service Area 07)', town: 'Mason', county: 'Mason County', state: 'Texas', lat: 30.7491, lng: -99.2306, alt_m: 469.0, alt_ft: 1539.0, type: 'remote_site' },
  'site:08': { name: 'Richland Springs (Service Area 08)', town: 'Richland Springs', county: 'San Saba County', state: 'Texas', lat: 31.2677, lng: -98.9431, alt_m: 419.0, alt_ft: 1375.0, type: 'remote_site' },
  'site:09': { name: 'Early (Service Area 09)', town: 'Early', county: 'Brown County', state: 'Texas', lat: 31.7454, lng: -98.9437, alt_m: 436.0, alt_ft: 1430.0, type: 'remote_site' },
  'site:10': { name: 'Comanche (Service Area 10)', town: 'Comanche', county: 'Comanche County', state: 'Texas', lat: 31.8974, lng: -98.6042, alt_m: 421.0, alt_ft: 1381.0, type: 'remote_site' }
};

// Deterministic Pseudo-Random Offset Generator based on ID hash
function getOffsetCoords(baseLat, baseLng, idStr, radiusKm = 1.8) {
  let hash = 0;
  for (let i = 0; i < idStr.length; i++) {
    hash = idStr.charCodeAt(i) + ((hash << 5) - hash);
  }
  const angle = (Math.abs(hash) % 360) * (Math.PI / 180);
  const distance = 0.3 + ((Math.abs(hash >> 3) % 100) / 100) * radiusKm;
  // 1 deg lat ~ 111 km, 1 deg lng ~ 95 km in Central Texas
  const dLat = (distance * Math.cos(angle)) / 111.0;
  const dLng = (distance * Math.sin(angle)) / 95.0;
  return {
    lat: baseLat + dLat,
    lng: baseLng + dLng
  };
}

// Dark Telecom Style for Google Maps
const DARK_TELECOM_MAP_STYLE = [
  { elementType: 'geometry', stylers: [{ color: '#0d1117' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0d1117' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#8b949e' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#58a6ff' }]
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#484f58' }]
  },
  {
    featureType: 'poi.park',
    elementType: 'geometry',
    stylers: [{ color: '#161b22' }]
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#161b22' }]
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#0d1117' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#21262d' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#161b22' }]
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#090d16' }]
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#38bdf8' }]
  }
];

export default function GoogleNetworkMap({
  selectedSiteId = null,
  selectedNode = null,
  onSelectSite = () => { },
  onSelectNode = () => { },
  activeTabId = 'full_access',
  activeDefectFilter = null,
  searchQuery = '',
  displayedGraph = null,
  className = ''
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef(new Map());
  const polylinesRef = useRef([]);
  const infoWindowRef = useRef(null);

  const DEFAULT_MAPS_KEY = 'AIzaSyAhzxxYlLES_NUUYgP7yKlMOaLi8LDtMpA';
  const envKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || DEFAULT_MAPS_KEY;
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('google_maps_api_key') || envKey || DEFAULT_MAPS_KEY);
  const [inputKey, setInputKey] = useState(apiKey);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [mapLoaded, setMapLoaded] = useState(() => !!(window.google && window.google.maps));
  const [mapError, setMapError] = useState('');

  // Graph Dataset State
  const [graphData, setGraphData] = useState(() => displayedGraph || null);
  const [loadingGraph, setLoadingGraph] = useState(() => !displayedGraph);



  // Active Category Filter State (supports multi-selection: PON, Links, Devices, Alarms, Sites)
  // When empty: all layers are active
  const [selectedCategories, setSelectedCategories] = useState(new Set());

  const isCategoryActive = useCallback((catKey) => {
    return selectedCategories.has(catKey);
  }, [selectedCategories]);

  const toggleCategory = useCallback((catKey) => {
    setSelectedCategories(prev => {
      const next = new Set(prev);
      if (next.has(catKey)) {
        next.delete(catKey);
      } else {
        next.add(catKey);
      }
      return next;
    });
  }, []);

  const handleShowAll = useCallback(() => {
    setSelectedCategories(new Set());
  }, []);

  const [activeNode, setActiveNode] = useState(null);
  const [mapStyleMode, setMapStyleMode] = useState('dark'); // 'dark' | 'roadmap' | 'satellite' | 'terrain'
  const [searchFilter, setSearchFilter] = useState('');
  const [activeCategoryTab, setActiveCategoryTab] = useState('sites'); // 'sites' | 'pons' | 'devices' | 'alarms'
  const [isDirectoryOpen, setIsDirectoryOpen] = useState(true);

  // Load Graph Data from Service
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoadingGraph(true);
        const fullData = await ontologyService.getFullGraph();
        if (isMounted) {
          if (fullData && fullData.devices && fullData.devices.length > 0) {
            setGraphData(fullData);
          } else if (displayedGraph) {
            setGraphData(displayedGraph);
          }
        }
      } catch (err) {
        console.error('Failed to load full graph in map:', err);
        if (isMounted && displayedGraph) setGraphData(displayedGraph);
      } finally {
        if (isMounted) setLoadingGraph(false);
      }
    }
    loadData();
    return () => { isMounted = false; };
  }, []);

  // Save API Key
  const handleSaveKey = (e) => {
    e.preventDefault();
    const cleanKey = (inputKey || '').trim();
    if (!cleanKey) return;
    localStorage.setItem('google_maps_api_key', cleanKey);
    setApiKey(cleanKey);
    setIsKeyModalOpen(false);
    setMapError('');
  };

  // Load Google Maps Script
  useEffect(() => {
    if (!apiKey) return;

    if (window.google && window.google.maps) {
      setMapLoaded(true);
      return;
    }

    const scriptId = 'google-maps-script';
    const existingScript = document.getElementById(scriptId);
    if (existingScript) {
      if (window.google && window.google.maps) {
        setMapLoaded(true);
        setMapError('');
      } else {
        existingScript.addEventListener('load', () => {
          setMapLoaded(true);
          setMapError('');
        });
        existingScript.addEventListener('error', () => {
          setMapError('Failed to load Google Maps API.');
        });
      }
      return;
    }

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry,places`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      setMapLoaded(true);
      setMapError('');
    };

    script.onerror = () => {
      setMapError('Failed to load Google Maps API. Please check your API key and billing restrictions.');
    };

    document.head.appendChild(script);
  }, [apiKey]);

  // Compute Full Mapped Geo Nodes (Sites, Devices, PONs, Subscribers, Alarms)
  const mappedNodes = useMemo(() => {
    if (!graphData) return [];

    let devicesList = graphData.devices || [];
    if (devicesList.length === 0 && Array.isArray(graphData.nodes)) {
      devicesList = graphData.nodes.filter(n =>
        n.type === 'Device' ||
        (n.labels && n.labels.includes('Device')) ||
        n.role === 'core' ||
        n.role === 'aggregation' ||
        n.role === 'access' ||
        n.role === 'olt' ||
        (n.id && n.id.startsWith('dev:'))
      );
    }

    const alarmsList = graphData.alarms || [];
    const subsList = graphData.subs || [];
    const ponsList = graphData.pons || [];

    const result = [];
    const deviceMap = new Map();

    // 1. Add Sites (10 Central Texas Hubs)
    Object.entries(SITE_GEO_LOCATIONS).forEach(([siteId, sGeo]) => {
      result.push({
        id: siteId,
        type: 'Site',
        name: sGeo.name,
        town: sGeo.town,
        county: sGeo.county,
        state: sGeo.state,
        lat: sGeo.lat,
        lng: sGeo.lng,
        alt_m: sGeo.alt_m,
        alt_ft: sGeo.alt_ft,
        role: sGeo.type,
        color: sGeo.isHub ? '#2563EB' : '#10B981',
        isHub: sGeo.isHub,
        props: { ...sGeo }
      });
    });

    // Compute alarmed target IDs from authentic JSON data
    const rawNodes = graphData.nodes || [];
    const extractedAlarms = [];
    rawNodes.forEach(n => {
      if (n.alarms && Array.isArray(n.alarms)) {
        n.alarms.forEach(a => extractedAlarms.push({ ...a, on: n.id, targetName: n.name || n.id }));
      }
    });
    const effectiveAlarms = extractedAlarms.length > 0 ? extractedAlarms : (graphData.alarms || []);
    const alarmedTargetIds = new Set(effectiveAlarms.map(a => a.on || a.target || a.targetId));

    // 2. Add Network Devices (83)
    devicesList.forEach((dev, idx) => {
      const parentSiteId = dev.site || (dev.id.includes('gldt') ? 'site:gldt' : dev.id.includes('sang') ? 'site:sang' : `site:${String((idx % 8) + 3).padStart(2, '0')}`);
      const siteGeo = SITE_GEO_LOCATIONS[parentSiteId] || SITE_GEO_LOCATIONS['site:gldt'];

      const isCore = dev.role === 'core';
      const isAgg = dev.role === 'aggregation';
      const isOlt = (dev.model || '').toLowerCase().includes('olt') || dev.id.includes('olt');

      const offset = isCore
        ? { lat: siteGeo.lat, lng: siteGeo.lng }
        : getOffsetCoords(siteGeo.lat, siteGeo.lng, dev.id, isAgg ? 0.8 : isOlt ? 2.2 : 1.5);

      const isDevAlarmed = !!dev.hasAlarm || (dev.alarms && dev.alarms.length > 0) || alarmedTargetIds.has(dev.id) || (alarmedTargetIds.has('port:olt-xg01:x1/0') && dev.id === 'dev:olt-xg01');

      const devItem = {
        id: dev.id,
        type: 'Device',
        subType: isCore ? 'Core Router' : isAgg ? 'Aggregation Router' : isOlt ? 'Calix OLT' : 'Access Node',
        name: dev.name,
        model: dev.model,
        vendor: dev.vendor,
        role: dev.role,
        siteId: parentSiteId,
        town: siteGeo.town,
        county: siteGeo.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: siteGeo.alt_m + (isCore ? 0 : (idx % 5) * 2),
        alt_ft: siteGeo.alt_ft + (isCore ? 0 : (idx % 5) * 6),
        release: dev.release,
        approved: dev.approved !== false,
        outlier: !!dev.outlier,
        defects: dev.defects || [],
        mgmt_ip: dev.mgmt_ip,
        hasAlarm: isDevAlarmed,
        color: isCore ? '#0284c7' : isAgg ? '#4f46e5' : isOlt ? '#c026d3' : '#0d9488',
        props: { ...dev }
      };

      deviceMap.set(dev.id, devItem);
      result.push(devItem);
    });

    // 3. Add Customer Edge ONTs (60)
    const ontMap = new Map();
    const rawOnts = rawNodes.filter(n => n.type === 'ONT' || (n.id && n.id.startsWith('ont:')));
    const oltCandidates = Array.from(deviceMap.values()).filter(d => (d.role === 'olt') || d.id.includes('olt'));

    rawOnts.forEach((ont, idx) => {
      let parentDev = oltCandidates.find(d => ont.id.toLowerCase().includes(d.id.replace('dev:', '').toLowerCase()));
      if (!parentDev && oltCandidates.length > 0) {
        parentDev = oltCandidates[idx % oltCandidates.length];
      }
      const anchor = parentDev || result[0];
      const offset = getOffsetCoords(anchor.lat, anchor.lng, ont.id, 2.5);
      const isOntAlarmed = alarmedTargetIds.has(ont.id) || ont.hasAlarm || ont.props?.hasAlarm || (ont.alarms && ont.alarms.length > 0);

      const ontItem = {
        id: ont.id,
        type: 'ONT',
        subType: 'Customer Premise ONT (GP1100X)',
        name: ont.name || ont.id,
        model: ont.props?.model || 'GP1100X',
        parentOlt: anchor.name || anchor.id,
        parentOltId: anchor.id,
        town: anchor.town,
        county: anchor.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: anchor.alt_m,
        alt_ft: anchor.alt_ft,
        hasAlarm: isOntAlarmed,
        color: isOntAlarmed ? '#ef4444' : '#f59e0b',
        props: { ...ont.props, role: 'ont', hasAlarm: isOntAlarmed }
      };

      ontMap.set(ont.id, ontItem);
      result.push(ontItem);
    });

    // 4. Add Active Alarms (29) Anchored to their true targets
    effectiveAlarms.forEach((alm, idx) => {
      const targetNode = ontMap.get(alm.on) || deviceMap.get(alm.on) || (alm.on && alm.on.includes('olt-xg01') ? deviceMap.get('dev:olt-xg01') : null) || result[0];
      const offset = getOffsetCoords(targetNode.lat, targetNode.lng, alm.id || String(idx), 0.4);

      result.push({
        id: alm.id || `alm:${idx}`,
        type: 'Alarm',
        subType: alm.type || 'CRITICAL LOS Alarm',
        name: alm.type || alm.name || `Critical Alarm #${idx + 1}`,
        severity: alm.sev ? alm.sev.toUpperCase() : 'CRITICAL',
        targetId: alm.on || targetNode.id,
        targetName: targetNode.name || 'OLT-XG-01',
        town: targetNode.town,
        county: targetNode.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: targetNode.alt_m,
        alt_ft: targetNode.alt_ft,
        text: alm.text || alm.message || 'Loss of Signal (LOS) / ONT Unreachable',
        at: alm.at || '2026-05-14T03:10:30Z',
        color: '#ef4444',
        hasAlarm: true,
        props: { ...alm }
      });
    });

    // 5. Add PON Optical Splitters
    ponsList.slice(0, 30).forEach((pon, idx) => {
      const siteId = `site:${String((idx % 8) + 3).padStart(2, '0')}`;
      const siteGeo = SITE_GEO_LOCATIONS[siteId] || SITE_GEO_LOCATIONS['site:gldt'];
      const offset = getOffsetCoords(siteGeo.lat, siteGeo.lng, pon.id, 1.8);

      result.push({
        id: pon.id,
        type: 'PONTree',
        subType: 'Optical Splitter (1:32)',
        name: `PON Splitter (${pon.ratio || '1:32'})`,
        tech: pon.tech || 'GPON',
        onts: pon.onts,
        town: siteGeo.town,
        county: siteGeo.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: siteGeo.alt_m,
        alt_ft: siteGeo.alt_ft,
        color: '#ec4899',
        props: { ...pon }
      });
    });

    return result;
  }, [graphData]);

  // Master Optical Trunk, Device Transport & PONT Drop Polylines
  const mappedLinks = useMemo(() => {
    if (!graphData) return [];

    const links = [];
    const nodePositionMap = new Map(mappedNodes.map(n => [n.id, n]));

    // 1. Physical site trunk links (100G)
    const trunks = [
      { from: 'site:gldt', to: 'site:sang', type: '100G Unprotected Trunk (SPOF)', color: '#EF4444', weight: 4.5, isSpof: true },
      { from: 'site:gldt', to: 'site:03', type: '100G Protected Fiber Ring A', color: '#00ABE4', weight: 3.5 },
      { from: 'site:03', to: 'site:sang', type: '100G Protected Ring Secondary', color: '#00ABE4', weight: 3.5 },
      { from: 'site:gldt', to: 'site:04', type: '100G North Fiber Ring', color: '#10B981', weight: 3 },
      { from: 'site:04', to: 'site:09', type: '100G Metro Corridor Link', color: '#10B981', weight: 2.5 },
      { from: 'site:09', to: 'site:10', type: '100G Spur Link', color: '#10B981', weight: 2.5 },
      { from: 'site:10', to: 'site:gldt', type: '100G Loop Return', color: '#10B981', weight: 2.5 },
      { from: 'site:gldt', to: 'site:08', type: '100G Central Fiber Link', color: '#3B82F6', weight: 2.5 },
      { from: 'site:08', to: 'site:03', type: '100G Cross Link', color: '#3B82F6', weight: 2.5 },
      { from: 'site:03', to: 'site:07', type: '100G South Ring', color: '#8B5CF6', weight: 2.5 },
      { from: 'site:07', to: 'site:06', type: '100G South Ring', color: '#8B5CF6', weight: 2.5 },
      { from: 'site:06', to: 'site:05', type: '100G South-East Loop', color: '#8B5CF6', weight: 2.5 },
      { from: 'site:05', to: 'site:gldt', type: '100G East Core Return', color: '#8B5CF6', weight: 3 }
    ];

    trunks.forEach(t => {
      const fromNode = nodePositionMap.get(t.from);
      const toNode = nodePositionMap.get(t.to);
      if (fromNode && toNode) {
        links.push({
          id: `trunk-${t.from}-${t.to}`,
          from: fromNode,
          to: toNode,
          linkType: 'trunk',
          type: t.type,
          color: t.color,
          weight: t.weight,
          isSpof: !!t.isSpof
        });
      }
    });

    // 2. Physical Device-to-Device Transport Links (Core <-> Agg, Agg <-> ACX, ACX <-> OLT)
    let rawDevLinks = graphData.deviceLinks || [];
    if (rawDevLinks.length === 0) {
      const allRels = graphData.relationships || graphData.rels || [];
      rawDevLinks = allRels
        .filter(r => r.type !== 'PONT' && r.type !== 'FEEDS' && r.type !== 'SERVES' && r.type !== 'RAISED_BY')
        .map(r => ({
          a: r.start || r.source,
          z: r.end || r.target,
          cap: r.props?.capacity || 10
        }));
    }
    rawDevLinks.forEach((dl, idx) => {
      const fromNode = nodePositionMap.get(dl.a);
      const toNode = nodePositionMap.get(dl.z);
      if (fromNode && toNode) {
        links.push({
          id: `link-dev-${idx}`,
          from: fromNode,
          to: toNode,
          linkType: 'device_link',
          type: `${dl.cap || 10}G Transport Link`,
          color: dl.cap === 100 ? '#0284c7' : '#64748b',
          weight: dl.cap === 100 ? 3.0 : 2.0,
          opacity: 0.75
        });
      }
    });

    // 3. PONT Optical Drop Links (OLT -> Customer ONTs)
    mappedNodes.filter(n => n.type === 'ONT').forEach(ont => {
      const parentDev = nodePositionMap.get(ont.parentOltId) || Array.from(nodePositionMap.values()).find(d => d.role === 'olt');
      if (parentDev) {
        links.push({
          id: `link-pont-${parentDev.id}-${ont.id}`,
          from: parentDev,
          to: ont,
          linkType: 'pont_link',
          type: 'PONT Optical Drop Line (FTTH)',
          color: '#f59e0b',
          weight: 1.8,
          opacity: 0.85
        });
      }
    });

    return links;
  }, [graphData, mappedNodes]);

  // Dynamic Reactive Filtering based on activeDefectFilter, activeTabId, and searchQuery
  const { filteredNodes, filteredLinks, activeFilterLabel } = useMemo(() => {
    if (!mappedNodes.length) {
      return { filteredNodes: [], filteredLinks: [], activeFilterLabel: '' };
    }

    let nodes = [...mappedNodes];
    let label = '';

    // 1. Defect Filter takes top priority
    if (activeDefectFilter) {
      label = `Defect Radar: ${activeDefectFilter.label}`;
      const keywords = activeDefectFilter.filterKeywords.map(k => k.toLowerCase());

      if (activeDefectFilter.id === 'def_evpn') {
        // 8 Aggregation Routers running 23.4R2 + their physical parent sites
        nodes = nodes.filter(n => {
          const id = n.id.toLowerCase();
          const name = (n.name || '').toLowerCase();
          const release = (n.release || '').toLowerCase();
          const isDev = keywords.some(k => id.includes(k) || name.includes(k)) || release === '23.4r2';
          const isSite = n.type === 'Site' && (id === 'site:sang' || (id.startsWith('site:') && parseInt(id.replace('site:', '')) >= 3));
          return isDev || isSite;
        });
      } else if (activeDefectFilter.id === 'spof_sang') {
        // SPOF: San Angelo & Goldthwaite corridor + SPOF trunk
        nodes = nodes.filter(n => {
          const id = n.id.toLowerCase();
          return id === 'site:gldt' || id === 'site:sang' || id.includes('sang') || id.includes('gldt');
        });
      } else if (activeDefectFilter.id === 'drift_stragglers') {
        // Version drift: SANG-AGG-01 (22.3R3), ACX-19 (21.4R3), and parent sites
        nodes = nodes.filter(n => {
          const id = n.id.toLowerCase();
          const isOutlier = n.outlier || n.approved === false || (n.release && (n.release.includes('22.3') || n.release.includes('21.4')));
          const isParentSite = n.type === 'Site' && (id === 'site:sang' || id === 'site:03');
          return isOutlier || isParentSite;
        });
      } else if (activeDefectFilter.id === 'alarm_cluster') {
        // Goldthwaite active alarms and core devices
        nodes = nodes.filter(n => {
          const id = n.id.toLowerCase();
          return id.includes('gldt') || (n.type === 'Alarm' && (n.targetId || '').includes('gldt'));
        });
      } else {
        nodes = nodes.filter(n => {
          const id = n.id.toLowerCase();
          const name = (n.name || '').toLowerCase();
          return keywords.some(k => id.includes(k) || name.includes(k));
        });
      }
    }
    // 2. Topology Preset Tab Filter
    else if (activeTabId) {
      if (activeTabId === 'core_agg') {
        label = 'Topology: Core & Aggregation Backbone';
        nodes = nodes.filter(n => n.type === 'Site' || (n.type === 'Device' && (n.role === 'core' || n.role === 'aggregation')));
      } else if (activeTabId === 'acx_olt') {
        label = 'Topology: Access & OLT Distribution';
        nodes = nodes.filter(n => n.type === 'Site' || (n.type === 'Device' && (n.role === 'access' || n.role === 'olt')));
      } else if (activeTabId === 'olt_ont') {
        label = 'Topology: PONT Links & Customer ONTs';
        nodes = nodes.filter(n => n.type === 'ONT' || n.type === 'PONTree' || (n.type === 'Device' && n.role === 'olt'));
      } else if (activeTabId === 'full_access') {
        label = 'Topology: Full 5-Tier Hierarchy';
      }
    }

    // 3. Search Query Filter
    const effectiveSearch = (searchQuery || searchFilter || '').trim().toLowerCase();
    if (effectiveSearch) {
      label = (label ? `${label} | ` : '') + `Search: "${effectiveSearch}"`;
      if (effectiveSearch === 'defect' || effectiveSearch === 'evpn' || effectiveSearch === 'qinq') {
        nodes = nodes.filter(n => n.release === '23.4R2' || n.type === 'Site');
      } else if (effectiveSearch === 'spof' || effectiveSearch === 'unprotected') {
        nodes = nodes.filter(n => n.id.includes('sang') || n.id.includes('gldt'));
      } else if (effectiveSearch === 'drift' || effectiveSearch === 'outlier') {
        nodes = nodes.filter(n => n.approved === false || n.outlier || n.type === 'Site');
      } else {
        nodes = nodes.filter(n =>
          n.id.toLowerCase().includes(effectiveSearch) ||
          (n.name || '').toLowerCase().includes(effectiveSearch) ||
          (n.town || '').toLowerCase().includes(effectiveSearch) ||
          (n.county || '').toLowerCase().includes(effectiveSearch) ||
          (n.model || '').toLowerCase().includes(effectiveSearch) ||
          (n.mgmt_ip || '').includes(effectiveSearch) ||
          (n.subType || '').toLowerCase().includes(effectiveSearch)
        );
      }
    }

    // 4. Interactive Category Filter (PON, Links, Devices, Alarms, Sites with multi-select)
    if (selectedCategories.size > 0) {
      nodes = nodes.filter(n => {
        // If PON is active: show ONTs, PON splitters, and OLT devices that feed them
        if (selectedCategories.has('pons')) {
          if (n.type === 'ONT' || n.type === 'PONTree' || n.type === 'Subscriber') return true;
          if (n.type === 'Device' && (n.role === 'olt' || (n.model || '').toLowerCase().includes('olt'))) return true;
        }

        // If Devices is active: show all physical equipment (Core, Agg, Access, OLT)
        if (selectedCategories.has('devices')) {
          if (n.type === 'Device') return true;
        }

        // If Alarms is active: show hardware alarms and alarmed equipment
        if (selectedCategories.has('alarms')) {
          if (n.type === 'Alarm' || n.hasAlarm || (n.alarms && n.alarms.length > 0)) return true;
        }

        // If Sites is active: show Central Office & hub sites
        if (selectedCategories.has('sites')) {
          if (n.type === 'Site') return true;
        }

        // If Links is active: show Central Offices & backbone routers as link anchors
        if (selectedCategories.has('links')) {
          if (n.type === 'Site' || (n.type === 'Device' && (n.role === 'core' || n.role === 'aggregation' || n.role === 'olt'))) return true;
        }

        return false;
      });
    }

    const nodeIds = new Set(nodes.map(n => n.id));

    // Connect visible nodes based on active categories
    let links = [];
    if (selectedCategories.size === 0) {
      // Normal full view: connect all visible nodes
      links = mappedLinks.filter(l => {
        const fromId = l.from?.id;
        const toId = l.to?.id;
        return nodeIds.has(fromId) && nodeIds.has(toId);
      });
    } else {
      links = mappedLinks.filter(l => {
        // If Links is selected: show all links across Texas
        if (selectedCategories.has('links')) return true;

        // If PON is selected: show PONT drop lines
        if (selectedCategories.has('pons') && l.linkType === 'pont_link') {
          return nodeIds.has(l.to?.id);
        }

        // If Devices is selected: show physical transport links
        if (selectedCategories.has('devices') && l.linkType === 'device_link') {
          return nodeIds.has(l.from?.id) && nodeIds.has(l.to?.id);
        }

        // If Sites is selected: show physical site trunks (100G)
        if (selectedCategories.has('sites') && l.linkType === 'trunk') {
          return nodeIds.has(l.from?.id) && nodeIds.has(l.to?.id);
        }

        // Otherwise connect visible nodes
        return nodeIds.has(l.from?.id) && nodeIds.has(l.to?.id);
      });
    }

    // Prominently highlight SPOF trunk when SPOF defect is active
    if (activeDefectFilter?.id === 'spof_sang') {
      const spofLink = mappedLinks.find(l => l.isSpof || (l.from?.id === 'site:gldt' && l.to?.id === 'site:sang'));
      if (spofLink && !links.some(l => l.id === spofLink.id)) {
        links.push(spofLink);
      }
    }

    return { filteredNodes: nodes, filteredLinks: links, activeFilterLabel: label };
  }, [mappedNodes, mappedLinks, activeDefectFilter, activeTabId, searchQuery, searchFilter, selectedCategories]);



  // Marker Icon Generator (Supports animated emergency radar beacon for alarms & alarmed equipment)
  const createMarkerIcon = (node, isSelected = false, isDefectAffected = false, isHighlighted = false, isDimmed = false) => {
    const isAlarm = node.type === 'Alarm';
    const hasAlarm = !!node.hasAlarm || (node.alarms && node.alarms.length > 0) || !!node.props?.hasAlarm;
    const isOnt = node.type === 'ONT';
    const isPon = node.type === 'PONTree';
    const isDev = node.type === 'Device';
    const isSite = node.type === 'Site';

    // Boosted sizes for alarms and alarmed equipment so they instantly catch the eye
    let baseSize = isSelected ? 52 : (isAlarm || hasAlarm) ? 46 : isDefectAffected ? 44 : isSite ? 38 : isDev ? 30 : isPon ? 28 : 26;
    if (isHighlighted) baseSize = Math.round(baseSize * 1.25);
    if (isDimmed) baseSize = Math.max(20, Math.round(baseSize * 0.75));

    let bg = isDefectAffected ? (activeDefectFilter?.color || '#EF4444') : (node.color || '#38BDF8');
    if (isAlarm || hasAlarm) {
      bg = '#DC2626'; // Vibrant emergency crimson
    }
    const stroke = (isAlarm || hasAlarm) ? '#FFFFFF' : (isSelected ? '#FFFFFF' : isDefectAffected ? '#FECACA' : '#0F172A');

    let iconText = '';
    if (isAlarm) iconText = '🚨';
    else if (hasAlarm) iconText = '⚠';
    else if (isDefectAffected && activeDefectFilter?.id === 'def_evpn') iconText = '🔥';
    else if (isDefectAffected && activeDefectFilter?.id === 'spof_sang') iconText = '⚠️';
    else if (isDefectAffected && activeDefectFilter?.id === 'drift_stragglers') iconText = '⚡';
    else if (isSite) iconText = node.isHub ? (node.id.includes('gldt') ? 'CO' : 'AGG') : node.town.substring(0, 3).toUpperCase();
    else if (isDev) iconText = (node.subType || '').includes('Core') ? 'CR' : (node.subType || '').includes('Agg') ? 'AR' : (node.subType || '').includes('OLT') ? 'OLT' : 'SW';
    else if (isOnt) iconText = 'ONT';
    else if (isPon) iconText = 'PON';
    else iconText = 'SUB';

    const showHalo = isHighlighted || isDefectAffected || isAlarm || hasAlarm || isSelected;
    let haloColor = (isAlarm || hasAlarm) ? '#EF4444' : (isDefectAffected ? (activeDefectFilter?.color || '#EF4444') : isSelected ? '#38BDF8' : '#F59E0B');
    if (isHighlighted) {
      if (isAlarm || hasAlarm) haloColor = '#EF4444';
      else if (isPon || isOnt) haloColor = '#F43F5E';
      else if (isDev) haloColor = '#00ABE4';
      else if (isSite) haloColor = '#3B82F6';
    }

    const opacity = isDimmed ? '0.28' : '1.0';

    return {
      url: `data:image/svg+xml;utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="${baseSize}" height="${baseSize}" viewBox="0 0 48 48" opacity="${opacity}">
        <defs>
          <filter id="shadow" x="-40%" y="-40%" width="180%" height="180%">
            <feDropShadow dx="0" dy="2" stdDeviation="${(isAlarm || hasAlarm || isHighlighted) ? 5 : 2}" flood-color="${(isAlarm || hasAlarm) ? '#EF4444' : haloColor}" flood-opacity="${(isAlarm || hasAlarm) ? 1.0 : 0.6}"/>
          </filter>
        </defs>
        ${(isAlarm || hasAlarm) ? `
          <!-- Pulsing Radar Wave for Active Alarms -->
          <circle cx="24" cy="24" r="23" fill="none" stroke="#EF4444" stroke-width="3" opacity="0.9">
            <animate attributeName="r" values="17;23;17" dur="1.6s" repeatCount="indefinite"/>
            <animate attributeName="stroke-width" values="3.5;1;3.5" dur="1.6s" repeatCount="indefinite"/>
            <animate attributeName="opacity" values="0.95;0.2;0.95" dur="1.6s" repeatCount="indefinite"/>
          </circle>
          <circle cx="24" cy="24" r="20" fill="rgba(239,68,68,0.22)"/>
        ` : (showHalo ? `<circle cx="24" cy="24" r="${isHighlighted ? 22.5 : 21}" fill="none" stroke="${haloColor}" stroke-width="${isHighlighted ? 3.5 : 2.5}" opacity="0.95"/>` : '')}
        <circle cx="24" cy="24" r="17.5" fill="${bg}" stroke="${stroke}" stroke-width="${(isAlarm || hasAlarm || isSelected) ? 3 : 2}" filter="url(#shadow)" />
        <text x="24" y="${iconText === '🚨' || iconText === '🔥' || iconText === '⚠️' || iconText === '⚡' || iconText === '⚠' ? '29' : '28'}" fill="#FFFFFF" font-family="system-ui, sans-serif" font-size="${iconText === '🚨' ? '17' : iconText.length > 2 ? '10' : '13'}" font-weight="900" text-anchor="middle">${iconText}</text>
        ${hasAlarm && !isAlarm ? `
          <!-- Alarm alert badge -->
          <circle cx="36" cy="12" r="8" fill="#DC2626" stroke="#FFFFFF" stroke-width="1.8" />
          <text x="36" y="15" fill="#FFFFFF" font-family="system-ui, sans-serif" font-size="8.5" font-weight="900" text-anchor="middle">!</text>
        ` : ''}
      </svg>`,
      scaledSize: new window.google.maps.Size(baseSize, baseSize),
      anchor: new window.google.maps.Point(baseSize / 2, baseSize / 2)
    };
  };

  // 1. Initialize Map Instance ONCE
  useEffect(() => {
    if (!mapLoaded || !mapContainerRef.current || !window.google?.maps) return;
    if (mapInstanceRef.current) {
      // Trigger resize if already initialized when tab is switched
      window.google.maps.event.trigger(mapInstanceRef.current, 'resize');
      return;
    }

    try {
      window.gm_authFailure = () => {
        console.warn('Google Maps Authentication Notice: Key may require enabling Maps JavaScript API in GCP console.');
      };

      const centralTexasCenter = { lat: 31.42, lng: -99.30 };
      const map = new window.google.maps.Map(mapContainerRef.current, {
        center: centralTexasCenter,
        zoom: 8.4,
        minZoom: 6,
        maxZoom: 18,
        styles: mapStyleMode === 'dark' ? DARK_TELECOM_MAP_STYLE : null,
        mapTypeId: mapStyleMode === 'satellite' ? 'hybrid' : mapStyleMode === 'terrain' ? 'terrain' : 'roadmap',
        disableDefaultUI: false,
        zoomControl: true,
        streetViewControl: false,
        fullscreenControl: false,
        mapTypeControl: false
      });

      mapInstanceRef.current = map;
      infoWindowRef.current = new window.google.maps.InfoWindow();

      // Trigger resize after DOM paints to avoid gray/blank tiles
      setTimeout(() => {
        if (map && window.google?.maps) {
          window.google.maps.event.trigger(map, 'resize');
          map.setCenter(centralTexasCenter);
        }
      }, 150);

      // Observe container resize (e.g. sidebar toggle or window resize)
      let resizeObserver = null;
      if (window.ResizeObserver && mapContainerRef.current) {
        resizeObserver = new ResizeObserver(() => {
          if (mapInstanceRef.current && window.google?.maps) {
            window.google.maps.event.trigger(mapInstanceRef.current, 'resize');
          }
        });
        resizeObserver.observe(mapContainerRef.current);
      }

      return () => {
        if (resizeObserver) resizeObserver.disconnect();
      };
    } catch (err) {
      console.error('Error initializing map:', err);
      setMapError('Failed to initialize Google Map view.');
    }
  }, [mapLoaded]);

  // 2. Update Map Style when mapStyleMode changes
  useEffect(() => {
    if (!mapInstanceRef.current || !window.google?.maps) return;
    mapInstanceRef.current.setOptions({
      styles: mapStyleMode === 'dark' ? DARK_TELECOM_MAP_STYLE : null,
      mapTypeId: mapStyleMode === 'satellite' ? 'hybrid' : mapStyleMode === 'terrain' ? 'terrain' : 'roadmap'
    });
  }, [mapStyleMode]);

  // 3. Reactively Update Markers & Polylines on Selector or Filter Change
  useEffect(() => {
    if (!mapInstanceRef.current || !window.google?.maps) return;
    const map = mapInstanceRef.current;

    // Clear old markers
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current.clear();

    // Clear old polylines
    polylinesRef.current.forEach(p => p.setMap(null));
    polylinesRef.current = [];

    const isSpofSelected = activeDefectFilter?.id === 'spof_sang';

    // 1. Render Polylines
    filteredLinks.forEach(link => {
      const isSpofLink = link.isSpof || (link.from?.id === 'site:gldt' && link.to?.id === 'site:sang');
      const isLinkHighlighted = selectedCategories.has('links') ||
        (selectedCategories.has('pons') && link.linkType === 'pont_link') ||
        (selectedCategories.has('devices') && link.linkType === 'device_link') ||
        (selectedCategories.has('sites') && link.linkType === 'trunk');

      const strokeColor = isSpofLink ? (isSpofSelected ? '#EF4444' : '#F59E0B') : (isLinkHighlighted ? (link.linkType === 'pont_link' ? '#F43F5E' : '#00ABE4') : link.color);
      const strokeOpacity = isLinkHighlighted ? 1.0 : (isSpofSelected ? 0.3 : 0.85);
      const strokeWeight = isLinkHighlighted ? Math.max(5.5, link.weight + 2) : link.weight;
      const zIndex = isLinkHighlighted ? 180 : (isSpofLink && isSpofSelected ? 100 : 10);

      const polyline = new window.google.maps.Polyline({
        path: [
          { lat: link.from.lat, lng: link.from.lng },
          { lat: link.to.lat, lng: link.to.lng }
        ],
        geodesic: true,
        strokeColor,
        strokeOpacity,
        strokeWeight,
        zIndex,
        map
      });

      polyline.addListener('click', (e) => {
        if (infoWindowRef.current) {
          const content = `
            <div style="padding: 10px 14px; font-family: system-ui, sans-serif; min-width: 250px; color: #0f172a;">
              <div style="font-size: 10px; font-weight: 800; color: ${isSpofLink ? '#EF4444' : link.color}; text-transform: uppercase;">
                ${link.type}
              </div>
              <div style="font-size: 13px; font-weight: 800; color: #1e293b; margin: 4px 0;">
                ${link.from.name} &harr; ${link.to.name}
              </div>
              <div style="font-size: 11px; color: #64748b;">
                Endpoints: <strong>${link.from.id} &bull; ${link.to.id}</strong>
              </div>
              ${isSpofLink ? `<div style="font-size: 11px; color: #dc2626; margin-top: 5px; font-weight: bold; background: #fef2f2; padding: 4px 6px; border-radius: 6px; border: 1px solid #fecaca;">⚠ Single Point of Failure (SPOF) - Unprotected 100G link without ERPS ring</div>` : ''}
            </div>
          `;
          infoWindowRef.current.setContent(content);
          infoWindowRef.current.setPosition(e.latLng);
          infoWindowRef.current.open(map);
        }
      });

      polylinesRef.current.push(polyline);
    });

    // 2. Render Node Markers
    const bounds = new window.google.maps.LatLngBounds();
    let hasVisiblePoints = false;

    filteredNodes.forEach(node => {
      const nodeCat = node.type === 'Site' ? 'sites' : node.type === 'Device' ? 'devices' : node.type === 'Alarm' ? 'alarms' : 'pons';
      const isNodeHighlighted = selectedCategories.has(nodeCat);

      const isDefectAffected = activeDefectFilter && (
        (activeDefectFilter.id === 'def_evpn' && (node.release === '23.4R2' || node.id.includes('agg-'))) ||
        (activeDefectFilter.id === 'spof_sang' && (node.id === 'site:sang' || node.id === 'site:gldt' || node.id.includes('sang'))) ||
        (activeDefectFilter.id === 'drift_stragglers' && (node.outlier || node.approved === false)) ||
        (activeDefectFilter.id === 'alarm_cluster' && (node.type === 'Alarm' || node.id.includes('gldt'))) ||
        (activeDefectFilter.id === 'def_ont_isolated' && (node.id === 'ont:olt-xg02-3-08' || node.targetId === 'ont:olt-xg02-3-08' || (node.id && node.id.includes('olt-xg02') && node.id.endsWith('-08'))))
      );

      const isNodeSelected = node.id === selectedSiteId || (selectedNode && selectedNode.id === node.id);
      const isAlarm = node.type === 'Alarm';
      const hasAlarm = !!node.hasAlarm || (node.alarms && node.alarms.length > 0);

      const marker = new window.google.maps.Marker({
        position: { lat: node.lat, lng: node.lng },
        map,
        title: `${node.name} (${node.alt_m}m)`,
        icon: createMarkerIcon(node, isNodeSelected, isDefectAffected, isNodeHighlighted, false),
        zIndex: isNodeSelected ? 700 : isAlarm ? 600 : hasAlarm ? 500 : isNodeHighlighted ? 250 : isDefectAffected ? 150 : node.type === 'Site' ? 100 : 10
      });

      marker.addListener('click', () => {
        setActiveNode(node);
        if (onSelectNode) onSelectNode(node);
        if (node.type === 'Site' && onSelectSite) onSelectSite(node);

        if (infoWindowRef.current) {
          const isSite = node.type === 'Site';
          const isDevice = node.type === 'Device';
          const isAlarm = node.type === 'Alarm';
          const isSub = node.type === 'Subscriber';

          const content = `
            <div style="padding: 10px 14px; font-family: system-ui, sans-serif; min-width: 260px; max-width: 320px; color: #0f172a;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-size: 10px; font-weight: 800; text-transform: uppercase; background: ${node.color}22; color: ${node.color}; padding: 2px 8px; border-radius: 9999px; border: 1px solid ${node.color}44;">
                  ${node.subType || node.type}
                </span>
                <span style="font-size: 10px; font-family: monospace; font-weight: 700; color: #0284c7; background: #e0f2fe; padding: 2px 6px; border-radius: 4px;">
                  ${node.id}
                </span>
              </div>
              <h3 style="font-size: 14px; font-weight: 800; color: #0f172a; margin: 3px 0;">${node.name}</h3>
              <div style="font-size: 11px; color: #475569; margin-bottom: 8px;">${node.town || 'Central Texas'}, ${node.county || 'Texas'}</div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px; border-radius: 8px; margin-bottom: 8px;">
                <div>
                  <div style="font-size: 9.5px; color: #64748b; font-weight: 600;">GPS Coordinates</div>
                  <div style="font-family: monospace; font-size: 10.5px; font-weight: 700; color: #0f172a;">${node.lat.toFixed(4)}&deg;, ${node.lng.toFixed(4)}&deg;</div>
                </div>
                <div>
                  <div style="font-size: 9.5px; color: #64748b; font-weight: 600;">Altitude / Elevation</div>
                  <div style="font-family: monospace; font-size: 10.5px; font-weight: 800; color: #4338ca;">${node.alt_m}m (${node.alt_ft}ft)</div>
                </div>
              </div>

              ${isDevice ? `
                <div style="font-size: 11px; color: #334155; margin-bottom: 4px;">
                  <strong>Hardware:</strong> ${node.vendor} ${node.model} &bull; Junos: <strong>${node.release || 'Approved'}</strong>
                </div>
                <div style="font-size: 11px; color: #334155; margin-bottom: 6px;">
                  <strong>Management IP:</strong> <code>${node.mgmt_ip || '10.45.1.1'}</code>
                </div>
              ` : ''}

              ${isAlarm ? `
                <div style="font-size: 11px; font-weight: 700; color: #dc2626; background: #fef2f2; padding: 6px; border-radius: 6px; margin-bottom: 6px; border: 1px solid #fecaca;">
                  ⚠ ${node.text || 'Active Optical Power & BGP Threshold Alarm'}
                </div>
              ` : ''}

              ${isSub ? `
                <div style="font-size: 11px; color: #334155; margin-bottom: 6px;">
                  <strong>Service Area:</strong> ${node.area} &bull; Criticality: <strong>${node.criticality}</strong>
                </div>
              ` : ''}

              ${node.type === 'ONT' ? `
                <div style="font-size: 11px; color: #334155; margin-bottom: 4px;">
                  <strong>Equipment:</strong> ${node.model || 'GP1100X'} &bull; Parent: <strong>${node.parentOlt || 'OLT-XG-02'}</strong>
                </div>
                ${node.hasAlarm ? `
                  <div style="font-size: 11px; font-weight: 700; color: #dc2626; background: #fef2f2; padding: 6px; border-radius: 6px; margin-bottom: 6px; border: 1px solid #fecaca;">
                    ⚠ Customer Drop Optical Loss (-31.2 dBm). Parent OLT-XG-02 and upper tiers are 100% healthy.
                  </div>
                ` : ''}
              ` : ''}

              ${(hasAlarm || isAlarm) ? `
                <div style="font-size: 10.5px; color: #dc2626; font-weight: 700; background: #fef2f2; padding: 4px 6px; border-radius: 6px; border: 1px solid #fecaca;">
                  ⚠ Status: CRITICAL DEFECT &bull; Optical Loss / Alarm Active
                </div>
              ` : `
                <div style="font-size: 10.5px; color: #059669; font-weight: 700; background: #ecfdf5; padding: 4px 6px; border-radius: 6px;">
                  &check; Status: ONLINE &bull; Click to inspect in side panel
                </div>
              `}
            </div>
          `;
          infoWindowRef.current.setContent(content);
          infoWindowRef.current.open(map, marker);
        }
      });

      markersRef.current.set(node.id, marker);
      bounds.extend({ lat: node.lat, lng: node.lng });
      hasVisiblePoints = true;
    });

    // Auto-fit bounds on selector or filter change
    if (hasVisiblePoints) {
      map.fitBounds(bounds, {
        top: 70,
        bottom: 50,
        left: isDirectoryOpen ? 340 : 50,
        right: 50
      });
      const listener = window.google.maps.event.addListenerOnce(map, 'idle', () => {
        if (map.getZoom() > 14) map.setZoom(14);
      });
    }
  }, [filteredNodes, filteredLinks, selectedCategories, selectedSiteId, selectedNode, activeDefectFilter, isDirectoryOpen]);

  // Pan smoothly to node if selected externally
  useEffect(() => {
    if (!selectedNode || !mapInstanceRef.current || !window.google?.maps) return;
    const targetMarker = markersRef.current.get(selectedNode.id);
    if (targetMarker) {
      mapInstanceRef.current.panTo(targetMarker.getPosition());
      mapInstanceRef.current.setZoom(selectedNode.type === 'Site' ? 11 : 14);
      if (infoWindowRef.current) {
        window.google.maps.event.trigger(targetMarker, 'click');
      }
    }
  }, [selectedNode]);

  // Fly to node on user click in directory
  const handleFlyToNode = useCallback((node) => {
    setActiveNode(node);
    if (onSelectNode) onSelectNode(node);
    if (node.type === 'Site' && onSelectSite) onSelectSite(node);

    if (mapInstanceRef.current && window.google?.maps) {
      mapInstanceRef.current.panTo({ lat: node.lat, lng: node.lng });
      mapInstanceRef.current.setZoom(node.type === 'Site' ? 11 : 14);

      const marker = markersRef.current.get(node.id);
      if (marker && infoWindowRef.current) {
        window.google.maps.event.trigger(marker, 'click');
      }
    }
  }, [onSelectNode, onSelectSite]);

  // Fly to Link Midpoint & Open Details
  const handleFlyToLink = useCallback((link) => {
    if (!mapInstanceRef.current || !link.from || !link.to) return;
    const midLat = (link.from.lat + link.to.lat) / 2;
    const midLng = (link.from.lng + link.to.lng) / 2;
    mapInstanceRef.current.panTo({ lat: midLat, lng: midLng });
    mapInstanceRef.current.setZoom(12);

    if (infoWindowRef.current) {
      const isSpofLink = link.isSpof || (link.from?.id === 'site:gldt' && link.to?.id === 'site:sang');
      const content = `
        <div style="padding: 10px 14px; font-family: system-ui, sans-serif; min-width: 250px; color: #0f172a;">
          <div style="font-size: 10px; font-weight: 800; color: ${isSpofLink ? '#EF4444' : link.color}; text-transform: uppercase;">
            ${link.type}
          </div>
          <div style="font-size: 13px; font-weight: 800; color: #1e293b; margin: 4px 0;">
            ${link.from.name} &harr; ${link.to.name}
          </div>
          <div style="font-size: 11px; color: #64748b;">
            Endpoints: <strong>${link.from.id} &bull; ${link.to.id}</strong>
          </div>
          ${isSpofLink ? `<div style="font-size: 11px; color: #dc2626; margin-top: 5px; font-weight: bold; background: #fef2f2; padding: 4px 6px; border-radius: 6px; border: 1px solid #fecaca;">⚠ Single Point of Failure (SPOF) - Unprotected 100G link without ERPS ring</div>` : ''}
        </div>
      `;
      infoWindowRef.current.setContent(content);
      infoWindowRef.current.setPosition({ lat: midLat, lng: midLng });
      infoWindowRef.current.open(mapInstanceRef.current);
    }
  }, []);

  // Layer category counts
  const categoryCounts = useMemo(() => {
    const counts = { sites: 0, devices: 0, alarms: 0, pons: 0, links: 0 };
    mappedNodes.forEach(n => {
      if (n.type === 'Site') counts.sites++;
      else if (n.type === 'Device') counts.devices++;
      else if (n.type === 'Alarm') counts.alarms++;
      else if (n.type === 'ONT' || n.type === 'PONTree' || n.type === 'Subscriber') counts.pons++;
    });
    counts.links = mappedLinks.length;
    return counts;
  }, [mappedNodes, mappedLinks]);

  // Filtered nodes for the directory panel
  const directoryNodes = useMemo(() => {
    let list = filteredNodes;
    if (activeCategoryTab === 'devices') list = list.filter(n => n.type === 'Device');
    else if (activeCategoryTab === 'pons') list = list.filter(n => n.type === 'ONT' || n.type === 'PONTree' || n.type === 'Subscriber');
    else if (activeCategoryTab === 'alarms') list = list.filter(n => n.type === 'Alarm');
    else if (activeCategoryTab === 'sites') list = list.filter(n => n.type === 'Site');
    return list;
  }, [filteredNodes, activeCategoryTab]);

  return (
    <div className={`relative flex flex-col h-full w-full bg-slate-950 overflow-hidden rounded-xl border border-slate-800 ${className}`}>
      {/* Top Map Status Banner & Layer Toggles Overlay */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between gap-2.5 pointer-events-none flex-wrap">
        {/* Active Filter / Selector Badge */}
        <div className="flex items-center gap-2 pointer-events-auto bg-slate-900/90 backdrop-blur-md border border-slate-700/80 px-3.5 py-1.5 rounded-xl shadow-2xl">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-xs font-bold text-white flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-[#00ABE4]" />
            {activeFilterLabel || 'CTTC Central Texas Physical Topology'}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-[11px] font-mono text-slate-300">
            {filteredNodes.length} Nodes &bull; {filteredLinks.length} Links
          </span>
        </div>

        {/* Single Unified Layer & Highlight Control Bar */}
        <div className="flex items-center gap-1 pointer-events-auto bg-slate-900/90 backdrop-blur-md border border-slate-700/80 p-1 rounded-xl shadow-2xl overflow-x-auto text-[11px] font-bold">

          <button
            onClick={() => toggleCategory('sites')}
            className={`px-2.5 py-1 rounded-lg transition cursor-pointer flex items-center gap-1 ${isCategoryActive('sites')
                ? 'bg-blue-600 text-white shadow-md ring-1 ring-white font-black'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            title="Highlight / Toggle Central Offices & Hub Sites"
          >
            <span>🏢 Sites</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.sites})</span>
            {isCategoryActive('sites') && <Check className="w-3 h-3 text-white" />}
          </button>

          <button
            onClick={() => toggleCategory('pons')}
            className={`px-2.5 py-1 rounded-lg transition cursor-pointer flex items-center gap-1 ${isCategoryActive('pons')
                ? 'bg-rose-600 text-white shadow-md ring-1 ring-white font-black'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            title="Highlight / Toggle PON Trees, Splitters, and Customer ONTs"
          >
            <span>🌲 PON</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.pons})</span>
            {isCategoryActive('pons') && <Check className="w-3 h-3 text-white" />}
          </button>

          <button
            onClick={() => toggleCategory('devices')}
            className={`px-2.5 py-1 rounded-lg transition cursor-pointer flex items-center gap-1 ${isCategoryActive('devices')
                ? 'bg-indigo-600 text-white shadow-md ring-1 ring-white font-black'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            title="Highlight / Toggle Core, Agg, Access, and OLT Devices"
          >
            <span>🖥️ Devices</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.devices})</span>
            {isCategoryActive('devices') && <Check className="w-3 h-3 text-white" />}
          </button>

          <button
            onClick={() => toggleCategory('alarms')}
            className={`px-2.5 py-1 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${isCategoryActive('alarms')
                ? 'bg-red-600 text-white shadow-xl shadow-red-500/60 ring-2 ring-white font-black animate-pulse'
                : 'bg-red-950/60 text-red-300 hover:bg-red-900/80 hover:text-white border border-red-800/80 shadow-xs'
              }`}
            title="Highlight / Isolate Active Hardware Alarms (29 Active)"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            <span>🚨 Alarms</span>
            <span className="font-mono text-[10px] bg-red-800 text-white px-1.5 py-0.2 rounded-full font-black border border-red-500/60">
              {categoryCounts.alarms}
            </span>
            {isCategoryActive('alarms') && <Check className="w-3 h-3 text-white" />}
          </button>

          {selectedCategories.size > 0 && (
            <button
              onClick={handleShowAll}
              className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 hover:text-white transition cursor-pointer flex items-center gap-1 text-[10px]"
              title="Reset highlight filters"
            >
              <X className="w-3 h-3" />
              <span>Reset</span>
            </button>
          )}
        </div>

        {/* Right Map Controls */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="flex items-center bg-slate-900/90 backdrop-blur-md border border-slate-700/80 p-1 rounded-xl shadow-2xl text-xs font-semibold text-slate-300">
            <button
              onClick={() => setMapStyleMode('dark')}
              className={`px-2.5 py-1 rounded-lg transition cursor-pointer ${mapStyleMode === 'dark' ? 'bg-blue-600 text-white shadow-xs font-bold' : 'hover:text-white'
                }`}
            >
              Dark NOC
            </button>
            <button
              onClick={() => setMapStyleMode('satellite')}
              className={`px-2.5 py-1 rounded-lg transition cursor-pointer ${mapStyleMode === 'satellite' ? 'bg-blue-600 text-white shadow-xs font-bold' : 'hover:text-white'
                }`}
            >
              Satellite
            </button>
            <button
              onClick={() => setMapStyleMode('terrain')}
              className={`px-2.5 py-1 rounded-lg transition cursor-pointer ${mapStyleMode === 'terrain' ? 'bg-blue-600 text-white shadow-xs font-bold' : 'hover:text-white'
                }`}
            >
              Terrain
            </button>
          </div>

          <button
            onClick={() => setIsKeyModalOpen(true)}
            className="p-2 bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-xl transition shadow-2xl cursor-pointer"
            title="API Key Settings"
          >
            <Key className="w-4 h-4 text-amber-400" />
          </button>
        </div>
      </div>

      {/* Floating Left Side Node & Link Directory (Collapsible) */}
      {isDirectoryOpen ? (
        <div className="absolute top-16 left-3 bottom-3 w-84 z-10 pointer-events-auto bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-fadeIn">
          {/* Header & Toggle */}
          <div className="p-3 border-b border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-[#00ABE4]" />
                Geospatial Directory
              </span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-mono bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/30 font-bold">
                  {directoryNodes.length} Nodes
                </span>
                <button
                  onClick={() => setIsDirectoryOpen(false)}
                  className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition cursor-pointer"
                  title="Collapse Panel"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Directory Category Filter Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto pb-1 text-[10px] font-bold">
              {[
                { id: 'sites', label: `Sites (${categoryCounts.sites})` },
                { id: 'pons', label: `PON (${categoryCounts.pons})` },
                { id: 'devices', label: `Devices (${categoryCounts.devices})` },
                { id: 'alarms', label: `Alarms (${categoryCounts.alarms})` }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveCategoryTab(tab.id)}
                  className={`px-2 py-0.5 rounded-md whitespace-nowrap transition cursor-pointer ${activeCategoryTab === tab.id
                      ? 'bg-[#00ABE4] text-white'
                      : 'text-slate-400 hover:text-white bg-slate-800/60'
                    }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Quick Search */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Filter by name, ID, or town..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full pl-8 pr-2.5 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-[#00ABE4]"
              />
            </div>
          </div>

          {/* Directory Items List (Nodes or Links) */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {activeCategoryTab === 'links' ? (
              // Links List
              filteredLinks.slice(0, 150).map(link => {
                const isSpof = link.isSpof;
                return (
                  <div
                    key={link.id}
                    onClick={() => handleFlyToLink(link)}
                    className={`p-2.5 rounded-xl border transition cursor-pointer flex flex-col gap-1 ${isSpof
                        ? 'bg-red-950/40 hover:bg-red-950/60 border-red-800/60 ring-1 ring-red-500/30'
                        : 'bg-slate-800/40 hover:bg-slate-800 border-slate-800'
                      }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-white truncate flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: link.color }}></span>
                        <span className="truncate">{link.from?.name} &harr; {link.to?.name}</span>
                      </span>
                      <span
                        className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border shrink-0"
                        style={{ backgroundColor: `${link.color}20`, color: link.color, borderColor: `${link.color}40` }}
                      >
                        {link.linkType === 'pont_link' ? 'PONT' : link.linkType === 'trunk' ? '100G' : '10G'}
                      </span>
                    </div>
                    <div className="text-[10.5px] text-slate-400 truncate">{link.type}</div>
                    {isSpof && (
                      <div className="text-[9.5px] text-red-400 font-bold">⚠ Single Point of Failure (SPOF)</div>
                    )}
                  </div>
                );
              })
            ) : (
              // Nodes List
              directoryNodes.slice(0, 150).map(node => {
                const isSelected = activeNode?.id === node.id || (selectedNode && selectedNode.id === node.id);
                const isAlarm = node.type === 'Alarm';
                const isDefect = activeDefectFilter && (
                  (activeDefectFilter.id === 'def_evpn' && (node.release === '23.4R2' || node.id.includes('agg-'))) ||
                  (activeDefectFilter.id === 'spof_sang' && (node.id === 'site:sang' || node.id === 'site:gldt')) ||
                  (activeDefectFilter.id === 'drift_stragglers' && node.outlier)
                );

                return (
                  <div
                    key={node.id}
                    onClick={() => handleFlyToNode(node)}
                    className={`p-2.5 rounded-xl border transition cursor-pointer flex flex-col gap-1 ${isSelected
                        ? 'bg-[#00ABE4]/20 border-[#00ABE4] shadow-inner'
                        : isDefect
                          ? 'bg-red-950/40 hover:bg-red-950/60 border-red-800/60 ring-1 ring-red-500/30'
                          : isAlarm
                            ? 'bg-red-950/30 hover:bg-red-950/50 border-red-900/40'
                            : 'bg-slate-800/40 hover:bg-slate-800 border-slate-800'
                      }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-white flex items-center gap-1.5 truncate">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: node.color }}
                        ></span>
                        <span className="truncate">{node.name}</span>
                      </span>
                      <span
                        className="text-[9.5px] font-mono font-bold px-1.5 py-0.2 rounded border shrink-0"
                        style={{ backgroundColor: `${node.color}20`, color: node.color, borderColor: `${node.color}40` }}
                      >
                        {node.subType || node.type}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{node.town || 'Central Texas'}</span>
                      <span className="text-[10px] font-mono text-indigo-300 flex items-center gap-1">
                        <Mountain className="w-2.5 h-2.5 text-indigo-400" />
                        {node.alt_m}m
                      </span>
                    </div>

                    {node.model && (
                      <div className="text-[10px] text-slate-400 truncate flex items-center gap-1 font-mono">
                        <Server className="w-2.5 h-2.5 text-blue-400 shrink-0" />
                        <span>{node.vendor || 'Hardware'} {node.model} &bull; {node.mgmt_ip || node.release || 'Active'}</span>
                      </div>
                    )}

                    {node.text && (
                      <div className="text-[10px] text-red-400 truncate font-semibold">
                        ⚠ {node.text}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        <button
          onClick={() => setIsDirectoryOpen(true)}
          className="absolute top-16 left-3 z-10 pointer-events-auto p-2.5 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl shadow-2xl text-slate-300 hover:text-white flex items-center gap-1.5 text-xs font-bold transition cursor-pointer"
          title="Open Geospatial Directory"
        >
          <Layers className="w-4 h-4 text-[#00ABE4]" />
          <span>Directory ({directoryNodes.length})</span>
        </button>
      )}

      {/* Main Google Maps Viewport */}
      <div
        ref={mapContainerRef}
        className="w-full h-full min-h-[500px] flex-1"
        style={{ width: '100%', height: '100%', minHeight: '500px' }}
      />

      {/* Map Error Notice */}
      {mapError && (
        <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-20">
          <div className="w-14 h-14 rounded-2xl bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400 mb-4">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-white mb-1">Google Maps Configuration</h2>
          <p className="text-xs text-slate-400 max-w-md mb-5 leading-relaxed">{mapError}</p>
          <button
            onClick={() => setIsKeyModalOpen(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-lg cursor-pointer"
          >
            <Key className="w-4 h-4" />
            <span>Configure Google Maps API Key</span>
          </button>
        </div>
      )}

      {/* API Key Modal */}
      {isKeyModalOpen && (
        <div className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl text-slate-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-500/20 text-blue-400 rounded-xl border border-blue-500/30">
                  <Key className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Google Maps API Key</h3>
                  <p className="text-xs text-slate-400">Configure key for live geospatial rendering</p>
                </div>
              </div>
              {apiKey && (
                <button
                  onClick={() => setIsKeyModalOpen(false)}
                  className="text-slate-400 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            <form onSubmit={handleSaveKey} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5">
                  Enter your Google Maps API Key:
                </label>
                <input
                  type="text"
                  placeholder="AIzaSy..."
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                {apiKey && (
                  <button
                    type="button"
                    onClick={() => setIsKeyModalOpen(false)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                  >
                    Cancel
                  </button>
                )}
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold shadow-lg transition flex items-center gap-1.5 cursor-pointer"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Save &amp; Load Map</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
