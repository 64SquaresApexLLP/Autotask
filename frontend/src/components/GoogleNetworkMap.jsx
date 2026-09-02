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
  Check
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
  onSelectSite = () => {},
  className = ''
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef(new Map());
  const polylinesRef = useRef([]);
  const infoWindowRef = useRef(null);

  const envKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('google_maps_api_key') || envKey);
  const [inputKey, setInputKey] = useState(apiKey);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(!apiKey);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState('');

  // Graph Dataset State
  const [graphData, setGraphData] = useState(null);
  const [loadingGraph, setLoadingGraph] = useState(true);

  // Layer Toggles
  const [visibleLayers, setVisibleLayers] = useState({
    sites: true,
    devices: true,
    alarms: true,
    subscribers: true,
    pontrees: false,
    trunks: true
  });

  const [activeNode, setActiveNode] = useState(null);
  const [mapStyleMode, setMapStyleMode] = useState('dark'); // 'dark' | 'roadmap' | 'satellite' | 'terrain'
  const [searchFilter, setSearchFilter] = useState('');
  const [activeCategoryTab, setActiveCategoryTab] = useState('all'); // 'all' | 'sites' | 'devices' | 'alarms' | 'subscribers'

  // Load Graph Data from Service
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        setLoadingGraph(true);
        const data = await ontologyService.getFullGraph();
        if (isMounted) setGraphData(data);
      } catch (err) {
        console.error('Failed to load full graph in map:', err);
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
    if (existingScript) existingScript.remove();

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
      setMapError('Failed to load Google Maps API. Please check your API key and billing/domain restrictions.');
    };

    document.head.appendChild(script);
  }, [apiKey]);

  // Compute Full Mapped Geo Nodes (Sites, Devices, PONs, Subscribers, Alarms)
  const mappedNodes = useMemo(() => {
    if (!graphData) return [];

    const rawNodes = graphData.nodes || [];
    const devicesList = graphData.devices || [];
    const alarmsList = graphData.alarms || [];
    const subsList = graphData.subs || [];
    const ponsList = graphData.pons || [];
    const ontsList = graphData.onts || [];

    const result = [];
    const deviceMap = new Map();

    // 1. Add Sites (10)
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
        color: isCore ? '#0284c7' : isAgg ? '#4f46e5' : isOlt ? '#c026d3' : '#0d9488',
        props: { ...dev }
      };

      deviceMap.set(dev.id, devItem);
      result.push(devItem);
    });

    // 3. Add Alarms (29 Active)
    alarmsList.forEach(alm => {
      const targetDev = deviceMap.get(alm.on) || deviceMap.get('dev:mx960-gldt') || result[0];
      const offset = getOffsetCoords(targetDev.lat, targetDev.lng, alm.id, 0.4);

      result.push({
        id: alm.id,
        type: 'Alarm',
        subType: alm.type,
        name: alm.type,
        severity: alm.sev,
        targetId: alm.on,
        targetName: targetDev.name || alm.on,
        town: targetDev.town,
        county: targetDev.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: targetDev.alt_m,
        alt_ft: targetDev.alt_ft,
        text: alm.text,
        at: alm.at,
        color: '#ef4444',
        props: { ...alm }
      });
    });

    // 4. Add Subscribers (74)
    subsList.forEach((sub, idx) => {
      const areaNum = parseInt(sub.area?.replace(/\D/g, '') || String((idx % 10) + 1));
      const siteId = areaNum === 1 ? 'site:gldt' : areaNum === 2 ? 'site:sang' : `site:${String(areaNum).padStart(2, '0')}`;
      const siteGeo = SITE_GEO_LOCATIONS[siteId] || SITE_GEO_LOCATIONS['site:gldt'];
      const offset = getOffsetCoords(siteGeo.lat, siteGeo.lng, sub.id, 3.5);

      result.push({
        id: sub.id,
        type: 'Subscriber',
        subType: 'Customer Premise',
        name: sub.account || `Account ${sub.id}`,
        area: sub.area,
        criticality: sub.crit,
        town: siteGeo.town,
        county: siteGeo.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: siteGeo.alt_m,
        alt_ft: siteGeo.alt_ft,
        ontId: sub.ont,
        color: '#10b981',
        props: { ...sub }
      });
    });

    // 5. Add PON Trees & Splitters
    ponsList.slice(0, 30).forEach((pon, idx) => {
      const siteId = `site:${String((idx % 8) + 3).padStart(2, '0')}`;
      const siteGeo = SITE_GEO_LOCATIONS[siteId] || SITE_GEO_LOCATIONS['site:gldt'];
      const offset = getOffsetCoords(siteGeo.lat, siteGeo.lng, pon.id, 2.5);

      result.push({
        id: pon.id,
        type: 'PONTree',
        subType: 'PON Optical Tree',
        name: `PON Splitter (${pon.ratio || '1:32'})`,
        tech: pon.tech || 'GPON',
        onts: pon.onts,
        town: siteGeo.town,
        county: siteGeo.county,
        lat: offset.lat,
        lng: offset.lng,
        alt_m: siteGeo.alt_m,
        alt_ft: siteGeo.alt_ft,
        color: '#fb7185',
        props: { ...pon }
      });
    });

    return result;
  }, [graphData]);

  // Optical Trunk & Device Links Polylines
  const mappedLinks = useMemo(() => {
    if (!graphData) return [];

    const links = [];
    const nodePositionMap = new Map(mappedNodes.map(n => [n.id, n]));

    // Physical site trunk links
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
          type: t.type,
          color: t.color,
          weight: t.weight,
          isSpof: !!t.isSpof
        });
      }
    });

    // Links between sites and their devices
    mappedNodes.filter(n => n.type === 'Device').forEach(dev => {
      const parentSite = nodePositionMap.get(dev.siteId);
      if (parentSite) {
        links.push({
          id: `link-${parentSite.id}-${dev.id}`,
          from: parentSite,
          to: dev,
          type: `${dev.subType} Local Trunk Interface`,
          color: '#38BDF8',
          weight: 1.5,
          opacity: 0.5
        });
      }
    });

    return links;
  }, [graphData, mappedNodes]);

  // Marker Icon Generator based on node type
  const createMarkerIcon = (node, isSelected = false) => {
    const size = isSelected ? 46 : node.type === 'Site' ? 40 : node.type === 'Alarm' ? 36 : node.type === 'Device' ? 32 : 26;
    const bg = node.color || '#38BDF8';
    const stroke = isSelected ? '#FFFFFF' : '#0F172A';

    let iconText = '';
    if (node.type === 'Site') iconText = node.isHub ? (node.id.includes('gldt') ? 'CO' : 'AGG') : node.town.substring(0, 3).toUpperCase();
    else if (node.type === 'Alarm') iconText = '⚠';
    else if (node.type === 'Device') iconText = (node.subType || '').includes('Core') ? 'CR' : (node.subType || '').includes('Agg') ? 'AR' : (node.subType || '').includes('OLT') ? 'OLT' : 'SW';
    else if (node.type === 'Subscriber') iconText = 'SUB';
    else iconText = 'PON';

    const isAlarm = node.type === 'Alarm';

    return {
      url: `data:image/svg+xml;utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 44 44">
        <defs>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000000" flood-opacity="0.6"/>
          </filter>
        </defs>
        ${isAlarm ? `<circle cx="22" cy="22" r="21" fill="none" stroke="#EF4444" stroke-width="2" opacity="0.8"/>` : ''}
        <circle cx="22" cy="22" r="18" fill="${bg}" stroke="${stroke}" stroke-width="3" filter="url(#shadow)" />
        <text x="22" y="${isAlarm ? '27' : '26'}" fill="#FFFFFF" font-family="system-ui, sans-serif" font-size="${isAlarm ? '14' : '10'}" font-weight="900" text-anchor="middle">${iconText}</text>
      </svg>`,
      scaledSize: new window.google.maps.Size(size, size),
      anchor: new window.google.maps.Point(size / 2, size / 2)
    };
  };

  // Render Markers and Polylines on Google Map
  useEffect(() => {
    if (!mapLoaded || !mapContainerRef.current || !window.google?.maps) return;

    try {
      const centralTexasCenter = { lat: 31.42, lng: -99.30 };

      const map = new window.google.maps.Map(mapContainerRef.current, {
        center: centralTexasCenter,
        zoom: 8.4,
        minZoom: 6,
        maxZoom: 17,
        styles: mapStyleMode === 'dark' ? DARK_TELECOM_MAP_STYLE : null,
        mapTypeId:
          mapStyleMode === 'satellite'
            ? 'hybrid'
            : mapStyleMode === 'terrain'
            ? 'terrain'
            : 'roadmap',
        disableDefaultUI: false,
        zoomControl: true,
        streetViewControl: false,
        fullscreenControl: false,
        mapTypeControl: false
      });

      mapInstanceRef.current = map;
      infoWindowRef.current = new window.google.maps.InfoWindow();

      // Clear existing markers and polylines
      markersRef.current.forEach(m => m.setMap(null));
      markersRef.current.clear();
      polylinesRef.current.forEach(p => p.setMap(null));
      polylinesRef.current = [];

      // 1. Render Fiber Trunks & Links
      if (visibleLayers.trunks) {
        mappedLinks.forEach(link => {
          const polyline = new window.google.maps.Polyline({
            path: [
              { lat: link.from.lat, lng: link.from.lng },
              { lat: link.to.lat, lng: link.to.lng }
            ],
            geodesic: true,
            strokeColor: link.color,
            strokeOpacity: link.isSpof ? 0.9 : 0.8,
            strokeWeight: link.weight,
            map
          });

          polyline.addListener('click', (e) => {
            if (infoWindowRef.current) {
              const content = `
                <div style="padding: 10px 14px; font-family: system-ui, sans-serif; min-width: 240px; color: #0f172a;">
                  <div style="font-size: 10px; font-weight: 800; color: ${link.color}; text-transform: uppercase;">
                    ${link.type}
                  </div>
                  <div style="font-size: 13px; font-weight: 800; color: #1e293b; margin: 4px 0;">
                    ${link.from.name} &harr; ${link.to.name}
                  </div>
                  <div style="font-size: 11px; color: #64748b;">
                    Link Endpoints: <strong>${link.from.id} &bull; ${link.to.id}</strong>
                  </div>
                  ${link.isSpof ? `<div style="font-size: 10.5px; color: #dc2626; margin-top: 4px; font-weight: bold;">⚠ Single Point of Failure (SPOF) - Unprotected link</div>` : ''}
                </div>
              `;
              infoWindowRef.current.setContent(content);
              infoWindowRef.current.setPosition(e.latLng);
              infoWindowRef.current.open(map);
            }
          });

          polylinesRef.current.push(polyline);
        });
      }

      // 2. Render Node Markers (Filtered by Layer Visibility)
      mappedNodes.forEach(node => {
        const isVisible =
          (node.type === 'Site' && visibleLayers.sites) ||
          (node.type === 'Device' && visibleLayers.devices) ||
          (node.type === 'Alarm' && visibleLayers.alarms) ||
          (node.type === 'Subscriber' && visibleLayers.subscribers) ||
          (node.type === 'PONTree' && visibleLayers.pontrees);

        if (!isVisible) return;

        const marker = new window.google.maps.Marker({
          position: { lat: node.lat, lng: node.lng },
          map,
          title: `${node.name} (${node.alt_m}m)`,
          icon: createMarkerIcon(node, node.id === selectedSiteId)
        });

        marker.addListener('click', () => {
          setActiveNode(node);
          if (node.type === 'Site') onSelectSite(node);

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

                <div style="font-size: 10.5px; color: #059669; font-weight: 700; background: #ecfdf5; padding: 4px 6px; border-radius: 6px;">
                  &check; Status: ONLINE &bull; ${node.props?.status || 'Active Node'}
                </div>
              </div>
            `;
            infoWindowRef.current.setContent(content);
            infoWindowRef.current.open(map, marker);
          }
        });

        markersRef.current.set(node.id, marker);
      });
    } catch (err) {
      console.error('Error initializing Google Map with nodes:', err);
      setMapError('Failed to initialize Google Map view with full network nodes.');
    }
  }, [mapLoaded, mapStyleMode, visibleLayers, mappedNodes, mappedLinks, apiKey]);

  // Pan to any node smoothly
  const handleFlyToNode = useCallback((node) => {
    setActiveNode(node);
    if (node.type === 'Site') onSelectSite(node);

    if (mapInstanceRef.current && window.google?.maps) {
      mapInstanceRef.current.panTo({ lat: node.lat, lng: node.lng });
      mapInstanceRef.current.setZoom(node.type === 'Site' ? 11 : 14);

      const marker = markersRef.current.get(node.id);
      if (marker && infoWindowRef.current) {
        google.maps.event.trigger(marker, 'click');
      }
    }
  }, [onSelectSite]);

  // Reset View to Full State
  const handleResetView = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.panTo({ lat: 31.42, lng: -99.30 });
      mapInstanceRef.current.setZoom(8.4);
      if (infoWindowRef.current) infoWindowRef.current.close();
    }
  };

  // Filter side list items
  const filteredSideNodes = useMemo(() => {
    return mappedNodes.filter(n => {
      const matchesCategory =
        activeCategoryTab === 'all' ||
        (activeCategoryTab === 'sites' && n.type === 'Site') ||
        (activeCategoryTab === 'devices' && n.type === 'Device') ||
        (activeCategoryTab === 'alarms' && n.type === 'Alarm') ||
        (activeCategoryTab === 'subscribers' && n.type === 'Subscriber') ||
        (activeCategoryTab === 'pontrees' && n.type === 'PONTree');

      const matchesSearch =
        n.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
        n.id.toLowerCase().includes(searchFilter.toLowerCase()) ||
        (n.town || '').toLowerCase().includes(searchFilter.toLowerCase()) ||
        (n.county || '').toLowerCase().includes(searchFilter.toLowerCase()) ||
        (n.model || '').toLowerCase().includes(searchFilter.toLowerCase());

      return matchesCategory && matchesSearch;
    });
  }, [mappedNodes, activeCategoryTab, searchFilter]);

  // Layer category counts
  const categoryCounts = useMemo(() => {
    const counts = { sites: 0, devices: 0, alarms: 0, subscribers: 0, pontrees: 0 };
    mappedNodes.forEach(n => {
      if (n.type === 'Site') counts.sites++;
      else if (n.type === 'Device') counts.devices++;
      else if (n.type === 'Alarm') counts.alarms++;
      else if (n.type === 'Subscriber') counts.subscribers++;
      else if (n.type === 'PONTree') counts.pontrees++;
    });
    return counts;
  }, [mappedNodes]);

  return (
    <div className={`relative flex flex-col h-full w-full bg-slate-950 overflow-hidden rounded-xl border border-slate-800 ${className}`}>
      {/* Top Map Toolbar & Layer Toggles Overlay */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between gap-3 pointer-events-none flex-wrap">
        {/* Left Status & Quick Stats */}
        <div className="flex items-center gap-2 pointer-events-auto bg-slate-900/90 backdrop-blur-md border border-slate-700/80 px-3.5 py-1.5 rounded-xl shadow-2xl">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="text-xs font-bold text-white flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-blue-400" />
            CTTC Physical Topology Map
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-[11px] font-mono text-slate-300">
            {mappedNodes.length} Nodes &bull; {mappedLinks.length} Links
          </span>
        </div>

        {/* Center Layer Visibility Filter Toggles */}
        <div className="flex items-center gap-1.5 pointer-events-auto bg-slate-900/90 backdrop-blur-md border border-slate-700/80 p-1 rounded-xl shadow-2xl overflow-x-auto text-[11px] font-bold">
          <button
            onClick={() => setVisibleLayers(prev => ({ ...prev, sites: !prev.sites }))}
            className={`px-2.5 py-1 rounded-lg transition flex items-center gap-1.5 ${
              visibleLayers.sites ? 'bg-blue-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🏢 Sites</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.sites})</span>
          </button>

          <button
            onClick={() => setVisibleLayers(prev => ({ ...prev, devices: !prev.devices }))}
            className={`px-2.5 py-1 rounded-lg transition flex items-center gap-1.5 ${
              visibleLayers.devices ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🖥️ Devices</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.devices})</span>
          </button>

          <button
            onClick={() => setVisibleLayers(prev => ({ ...prev, alarms: !prev.alarms }))}
            className={`px-2.5 py-1 rounded-lg transition flex items-center gap-1.5 ${
              visibleLayers.alarms ? 'bg-red-600 text-white shadow-xs animate-pulse' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🚨 Alarms</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.alarms})</span>
          </button>

          <button
            onClick={() => setVisibleLayers(prev => ({ ...prev, subscribers: !prev.subscribers }))}
            className={`px-2.5 py-1 rounded-lg transition flex items-center gap-1.5 ${
              visibleLayers.subscribers ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>👥 Subs</span>
            <span className="font-mono text-[10px] opacity-80">({categoryCounts.subscribers})</span>
          </button>

          <button
            onClick={() => setVisibleLayers(prev => ({ ...prev, pontrees: !prev.pontrees }))}
            className={`px-2.5 py-1 rounded-lg transition flex items-center gap-1.5 ${
              visibleLayers.pontrees ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>🌲 PON</span>
          </button>

          <button
            onClick={() => setVisibleLayers(prev => ({ ...prev, trunks: !prev.trunks }))}
            className={`px-2.5 py-1 rounded-lg transition flex items-center gap-1.5 ${
              visibleLayers.trunks ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'
            }`}
          >
            <span>⚡ Links</span>
          </button>
        </div>

        {/* Right Map Controls */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="flex items-center bg-slate-900/90 backdrop-blur-md border border-slate-700/80 p-1 rounded-xl shadow-2xl text-xs font-semibold text-slate-300">
            <button
              onClick={() => setMapStyleMode('dark')}
              className={`px-2.5 py-1 rounded-lg transition ${
                mapStyleMode === 'dark' ? 'bg-blue-600 text-white shadow-xs' : 'hover:text-white'
              }`}
            >
              Dark NOC
            </button>
            <button
              onClick={() => setMapStyleMode('satellite')}
              className={`px-2.5 py-1 rounded-lg transition ${
                mapStyleMode === 'satellite' ? 'bg-blue-600 text-white shadow-xs' : 'hover:text-white'
              }`}
            >
              Satellite
            </button>
            <button
              onClick={() => setMapStyleMode('terrain')}
              className={`px-2.5 py-1 rounded-lg transition ${
                mapStyleMode === 'terrain' ? 'bg-blue-600 text-white shadow-xs' : 'hover:text-white'
              }`}
            >
              Terrain
            </button>
          </div>

          <button
            onClick={handleResetView}
            className="p-2 bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-xl transition shadow-2xl cursor-pointer"
            title="Reset to Full Central Texas View"
          >
            <Compass className="w-4 h-4 text-blue-400" />
          </button>

          <button
            onClick={() => setIsKeyModalOpen(true)}
            className="p-2 bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 rounded-xl transition shadow-2xl cursor-pointer"
            title="API Key Settings"
          >
            <Key className="w-4 h-4 text-amber-400" />
          </button>
        </div>
      </div>

      {/* Floating Left Side Multi-Category Node Directory */}
      <div className="absolute top-16 left-3 bottom-3 w-80 z-10 pointer-events-auto bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header & Search */}
        <div className="p-3 border-b border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              Network Node Directory
            </span>
            <span className="text-[10px] font-mono bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/30">
              {filteredSideNodes.length} Loaded
            </span>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search node, router, alarm, IP..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full pl-8 pr-2.5 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto text-[10px] font-bold text-slate-400 pb-0.5">
            {['all', 'sites', 'devices', 'alarms', 'subscribers', 'pontrees'].map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategoryTab(cat)}
                className={`px-2 py-1 rounded-md capitalize transition whitespace-nowrap ${
                  activeCategoryTab === cat ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 hover:text-white'
                }`}
              >
                {cat === 'all' ? 'All' : cat === 'pontrees' ? 'PON' : cat}
              </button>
            ))}
          </div>
        </div>

        {/* Nodes List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {filteredSideNodes.slice(0, 150).map(node => {
            const isSelected = activeNode?.id === node.id;
            const isAlarm = node.type === 'Alarm';
            return (
              <div
                key={node.id}
                onClick={() => handleFlyToNode(node)}
                className={`p-2.5 rounded-xl border transition cursor-pointer flex flex-col gap-1 ${
                  isSelected
                    ? 'bg-blue-600/20 border-blue-500/60 shadow-inner'
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
                    <span>{node.vendor} {node.model} &bull; {node.mgmt_ip || node.release}</span>
                  </div>
                )}

                {node.text && (
                  <div className="text-[10px] text-red-400 truncate font-semibold">
                    ⚠ {node.text}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Google Maps Viewport */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Map Error Notice */}
      {mapError && (
        <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center z-20">
          <div className="w-14 h-14 rounded-2xl bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400 mb-4">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-white mb-1">Google Maps API Configuration</h2>
          <p className="text-xs text-slate-400 max-w-md mb-5 leading-relaxed">{mapError}</p>
          <button
            onClick={() => setIsKeyModalOpen(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-lg cursor-pointer"
          >
            <Key className="w-4 h-4" />
            <span>Update Google Maps API Key</span>
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
