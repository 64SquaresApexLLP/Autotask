import React, { useEffect, useRef, useCallback } from 'react';

/**
 * CTTC Hierarchical Network Topology Canvas
 * Strict Deterministic 5-tier grid wrapper layout. Zero physics.
 * Core (0) -> Aggregation (1) -> Access (2) -> OLT (3) -> ONT (4)
 */
export default function Neo4jGraphCanvas({
  nodes = [],
  relationships = [],
  selectedNode = null,
  activeDefectFilter = null,
  onSelectNode = () => {},
  onSelectRelationship = () => {},
  physicsEnabled = true,
  searchQuery = '',
  hiddenNodeTypes = new Set(),
  hiddenRelTypes = new Set(),
  onHoverNode = () => {},
  onFitRequested = null
}) {
  const canvasRef = useRef(null);
  const nodesRef = useRef([]);
  const linksRef = useRef([]);
  const animFrameRef = useRef(null);

  // Pan & Zoom state
  const transformRef = useRef({ x: 0, y: 0, scale: 0.85 });
  const isDraggingCanvasRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const hoveredNodeRef = useRef(null);
  const pulseOffsetRef = useRef(0);

  // 1. Map Data into Strict Tiers with Deterministic Flex-Wrap Grid Positioning
  const visibleData = React.useMemo(() => {
    const tierNodesMap = { 0: [], 1: [], 2: [], 3: [], 4: [] };
    const nodeMap = new Map();

    nodes.forEach(n => {
      // 1. Strictly only allow Device and ONT nodes - filter out all ports, splitters, sites, alarms, links
      const isOnt = n.type === 'ONT' || (n.id && n.id.startsWith('ont:'));
      const isDevice = !isOnt && (n.type === 'Device' || (n.id && n.id.startsWith('dev:')) || (n.role && !['aggregation_facing', 'access_facing', 'uplink'].includes(n.role)));

      if (!isDevice && !isOnt) return;

      // Explicitly reject entity types that must never be in the device topology
      if (['Port', 'Site', 'Alarm', 'Service', 'ServicePath', 'Splitter', 'PONTree', 'Link', 'Optic', 'Subscriber', 'SoftwareVersion', 'KnownDefect', 'VendorCase', 'Ticket', 'ProtectionGroup'].includes(n.type)) {
        return;
      }
      if (n.id && (n.id.startsWith('port:') || n.id.startsWith('spl:') || n.id.startsWith('site:') || n.id.startsWith('alm:') || n.id.startsWith('svc:') || n.id.startsWith('pon:') || n.id.startsWith('sub:') || n.id.startsWith('link:'))) {
        return;
      }

      let tier = -1;
      let roleLabel = '';
      let color = '';
      let fill = '';

      const idLower = (n.id || '').toLowerCase();
      const roleLower = (n.role || '').toLowerCase();
      const modelLower = (n.model || '').toLowerCase();

      if (roleLower === 'core' || idLower.includes('core') || idLower.includes('mx960')) {
        tier = 0; roleLabel = 'Core'; color = '#8b5cf6'; fill = '#4c1d95';
      } else if (roleLower === 'aggregation' || idLower.includes('mx304') || (idLower.includes('agg') && !idLower.includes('acx'))) {
        tier = 1; roleLabel = 'Aggregation'; color = '#0ea5e9'; fill = '#0f766e';
      } else if (roleLower === 'access' || idLower.includes('acx') || modelLower.includes('acx')) {
        tier = 2; roleLabel = 'Access'; color = '#64748b'; fill = '#334155';
      } else if (!isOnt && (roleLower === 'olt' || idLower.includes('olt') || modelLower.includes('olt') || modelLower.includes('e7'))) {
        tier = 3; roleLabel = 'OLT'; color = '#22c55e'; fill = '#14532d';
      } else if (isOnt || roleLower === 'ont' || idLower.startsWith('ont:')) {
        tier = 4; roleLabel = 'ONT'; color = '#f59e0b'; fill = '#78350f';
      }

      if (tier >= 0) {
        const tn = { ...n, tier, roleLabel, borderColor: color, fillColor: fill };
        tierNodesMap[tier].push(tn);
        nodeMap.set(n.id, tn);
      }
    });

    const finalNodes = [];
    const COL_SPACING = 100; // Horizontal gap between rectangular boxes
    const ROW_SPACING = 45; // Vertical gap when wrapping within a tier
    const TIER_SPACING = 130; // Vertical gap between different tiers

    let currentY = 120;

    const tiersConfig = [
      { id: 0, maxPerRow: 1, minPerRow: 1 },
      { id: 1, maxPerRow: 10, minPerRow: 8 },
      { id: 2, maxPerRow: 14, minPerRow: 11 },
      { id: 3, maxPerRow: 14, minPerRow: 11 },
      { id: 4, maxPerRow: 15, minPerRow: 12 }
    ];

    tiersConfig.forEach(tConfig => {
      const tNodes = tierNodesMap[tConfig.id];
      if (!tNodes || tNodes.length === 0) return;
      
      // Sort alphabetically by name or ID to ensure stable layout
      tNodes.sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id));

      let rows = [];
      let remaining = tNodes.length;
      let maxCols = tConfig.maxPerRow;

      while (remaining > 0) {
        let colsInThisRow = Math.min(remaining, maxCols);
        rows.push(colsInThisRow);
        remaining -= colsInThisRow;
        maxCols = Math.max(tConfig.minPerRow, maxCols - 1); 
      }

      let nodeIndex = 0;
      rows.forEach((colsInThisRow, r) => {
        for (let c = 0; c < colsInThisRow; c++) {
          const node = tNodes[nodeIndex++];
          node.x = (c - (colsInThisRow - 1) / 2) * COL_SPACING;
          node.y = currentY + r * ROW_SPACING;
          finalNodes.push(node);
        }
      });

      // Shift Y down for the next tier group
      currentY += (rows.length - 1) * ROW_SPACING + TIER_SPACING;
    });

    const finalLinks = [];
    const linkSet = new Set();

    // Helper to resolve nodes across ID variations
    const resolveNode = (id) => {
      if (!id) return null;
      const strId = String(id);
      if (nodeMap.has(strId)) return nodeMap.get(strId);
      const withoutDev = strId.replace('dev:', '');
      if (nodeMap.has(withoutDev)) return nodeMap.get(withoutDev);
      const withDev = `dev:${strId}`;
      if (nodeMap.has(withDev)) return nodeMap.get(withDev);
      for (const [nid, n] of nodeMap.entries()) {
        if (nid.toLowerCase() === strId.toLowerCase() || n.name?.toLowerCase() === strId.toLowerCase()) {
          return n;
        }
      }
      return null;
    };

    // 1. Process relationships passed from props
    relationships.forEach(r => {
      if (hiddenRelTypes.has(r.type)) return;
      const sId = typeof r.source === 'object' ? (r.source.id || r.source) : (r.source || r.start || r.from || r.a);
      const tId = typeof r.target === 'object' ? (r.target.id || r.target) : (r.target || r.end || r.to || r.z);
      
      const sNode = resolveNode(sId);
      const tNode = resolveNode(tId);

      if (sNode && tNode) {
        const key = `${sNode.id}->${tNode.id}`;
        const revKey = `${tNode.id}->${sNode.id}`;
        if (!linkSet.has(key) && !linkSet.has(revKey)) {
          linkSet.add(key);
          const isPont = (sNode.tier === 3 && tNode.tier === 4) || (tNode.tier === 3 && sNode.tier === 4);
          finalLinks.push({
            ...r,
            id: r.id || key,
            source: sNode,
            target: tNode,
            displayType: isPont ? 'PONT' : (r.type || 'CONNECTED_TO')
          });
        }
      }
    });

    // 2. Guarantee 100% Hierarchy Connections Across All 5 Tiers
    const coreNodes = tierNodesMap[0] || [];
    const aggNodes = tierNodesMap[1] || [];
    const accessNodes = tierNodesMap[2] || [];
    const oltNodes = tierNodesMap[3] || [];
    const ontNodes = tierNodesMap[4] || [];

    // Guarantee Core <-> Aggregation links (All 9 Agg routers connect to Core)
    if (coreNodes.length > 0) {
      const coreNode = coreNodes[0];
      aggNodes.forEach(agg => {
        const key = `${coreNode.id}->${agg.id}`;
        const revKey = `${agg.id}->${coreNode.id}`;
        if (!linkSet.has(key) && !linkSet.has(revKey)) {
          linkSet.add(key);
          finalLinks.push({
            id: `link:backbone:${agg.id}`,
            source: coreNode,
            target: agg,
            displayType: '100G'
          });
        }
      });
    }

    // Guarantee Aggregation <-> Access links (Each of 40 Access switches connects to an Agg router)
    accessNodes.forEach((acx, idx) => {
      const hasAggLink = finalLinks.some(l => 
        (l.source.id === acx.id && l.target.tier === 1) || 
        (l.target.id === acx.id && l.source.tier === 1)
      );
      if (!hasAggLink && aggNodes.length > 0) {
        const parentAgg = aggNodes[idx % aggNodes.length];
        const key = `${parentAgg.id}->${acx.id}`;
        linkSet.add(key);
        finalLinks.push({
          id: `link:access:${acx.id}`,
          source: parentAgg,
          target: acx,
          displayType: '10G'
        });
      }
    });

    // Guarantee Access <-> OLT links (Each of 33 OLTs connects to an Access switch)
    oltNodes.forEach((olt, idx) => {
      const hasAcxLink = finalLinks.some(l => 
        (l.source.id === olt.id && l.target.tier === 2) || 
        (l.target.id === olt.id && l.source.tier === 2)
      );
      if (!hasAcxLink && accessNodes.length > 0) {
        const parentAcx = accessNodes[idx % accessNodes.length];
        const key = `${parentAcx.id}->${olt.id}`;
        linkSet.add(key);
        finalLinks.push({
          id: `link:olt:${olt.id}`,
          source: parentAcx,
          target: olt,
          displayType: '10G'
        });
      }
    });

    // Guarantee OLT <-> ONT PONT links (Each of 60 ONTs connects to its parent OLT)
    ontNodes.forEach((ont, idx) => {
      const hasOltLink = finalLinks.some(l => 
        (l.source.id === ont.id && l.target.tier === 3) || 
        (l.target.id === ont.id && l.source.tier === 3)
      );
      if (!hasOltLink && oltNodes.length > 0) {
        let parentOlt = oltNodes.find(olt => {
          const oltBase = olt.id.replace('dev:', '').toLowerCase();
          return ont.id.toLowerCase().includes(oltBase);
        });
        if (!parentOlt) {
          parentOlt = oltNodes[idx % oltNodes.length];
        }
        const key = `${parentOlt.id}->${ont.id}`;
        linkSet.add(key);
        finalLinks.push({
          id: `link:pont:${ont.id}`,
          source: parentOlt,
          target: ont,
          displayType: 'PONT'
        });
      }
    });

    return { nodes: finalNodes, links: finalLinks };
  }, [nodes, relationships, hiddenNodeTypes, hiddenRelTypes]);

  // Handle Resize and Auto-Fit
  const handleFit = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !nodesRef.current.length) return;
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodesRef.current.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });

    const graphWidth = Math.max(maxX - minX, 500) + 260; // Padding for tier labels on left
    const graphHeight = Math.max(maxY - minY, 500) + 140;

    const scaleX = (rect.width * 0.88) / graphWidth;
    const scaleY = (rect.height * 0.88) / graphHeight;
    const scale = Math.max(0.2, Math.min(scaleX, scaleY, 1.15));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    transformRef.current = {
      scale,
      x: rect.width / 2 - centerX * scale,
      y: rect.height / 2 - centerY * scale
    };
    renderFrame();
  }, []);

  useEffect(() => {
    if (onFitRequested) {
      onFitRequested.current = handleFit;
    }
  }, [onFitRequested, handleFit]);

  // Master Render Frame
  const renderFrame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Light Theme Background
    ctx.fillStyle = '#f4f6f8';
    ctx.fillRect(0, 0, rect.width, rect.height);

    const { x, y, scale } = transformRef.current;
    ctx.translate(x, y);
    ctx.scale(scale, scale);

    const simNodes = nodesRef.current;
    const simLinks = linksRef.current;

    // Draw Left-side Tier Text aligned with the grid
    ctx.font = 'bold 11px Inter, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    
    let minX = 0, maxX = 0;
    simNodes.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
    });
    const labelX = minX - 45;

    const tiers = [
      { t: 0, label: 'CORE' },
      { t: 1, label: 'AGGREGATION' },
      { t: 2, label: 'ACCESS' },
      { t: 3, label: 'OLT' },
      { t: 4, label: 'ONT' }
    ];

    tiers.forEach(tDef => {
      const nodesInTier = simNodes.filter(n => n.tier === tDef.t);
      if (nodesInTier.length > 0) {
        let minTierY = Infinity;
        nodesInTier.forEach(n => { if (n.y < minTierY) minTierY = n.y; });
        ctx.fillText(tDef.label, labelX, minTierY);
      }
    });

    // Compute End-to-End Hierarchical Path (ONT <-> OLT <-> Access <-> Agg <-> Core)
    const activeTarget = selectedNode || hoveredNodeRef.current;
    const activePathNodeIds = new Set();
    const activePathLinkKeys = new Set();

    if (activeTarget) {
      activePathNodeIds.add(activeTarget.id);

      // Trace UPSTREAM towards Core: target (tier T) -> parent (tier T - 1) -> ... -> Core (tier 0)
      let currUp = activeTarget;
      while (currUp && currUp.tier > 0) {
        const upstreamLink = simLinks.find(l => {
          const s = l.source;
          const t = l.target;
          if (s.id === currUp.id && t.tier === currUp.tier - 1) return true;
          if (t.id === currUp.id && s.tier === currUp.tier - 1) return true;
          return false;
        });
        if (!upstreamLink) break;
        const nextNode = upstreamLink.source.id === currUp.id ? upstreamLink.target : upstreamLink.source;
        activePathNodeIds.add(nextNode.id);
        activePathLinkKeys.add(`${upstreamLink.source.id}->${upstreamLink.target.id}`);
        activePathLinkKeys.add(`${upstreamLink.target.id}->${upstreamLink.source.id}`);
        currUp = nextNode;
      }

      // Trace DOWNSTREAM towards ONT: target (tier T) -> children (tier T + 1) -> ...
      let downCurrs = [activeTarget];
      while (downCurrs.length > 0) {
        const nextDown = [];
        downCurrs.forEach(dc => {
          simLinks.forEach(l => {
            const s = l.source;
            const t = l.target;
            if (s.id === dc.id && t.tier === dc.tier + 1) {
              activePathNodeIds.add(t.id);
              activePathLinkKeys.add(`${s.id}->${t.id}`);
              activePathLinkKeys.add(`${t.id}->${s.id}`);
              nextDown.push(t);
            } else if (t.id === dc.id && s.tier === dc.tier + 1) {
              activePathNodeIds.add(s.id);
              activePathLinkKeys.add(`${s.id}->${t.id}`);
              activePathLinkKeys.add(`${t.id}->${s.id}`);
              nextDown.push(s);
            }
          });
        });
        downCurrs = nextDown;
      }
    }

    // Draw Links (Visible, high-contrast, with full path tracing)
    simLinks.forEach(link => {
      const source = link.source;
      const target = link.target;
      if (!source || !target || typeof source.x !== 'number' || typeof target.x !== 'number') return;

      const isPathLink = activePathLinkKeys.has(`${source.id}->${target.id}`);
      const isSelected = selectedNode && (source.id === selectedNode.id || target.id === selectedNode.id);

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);

      if (isPathLink || isSelected) {
        // High-visibility glowing solid path link
        ctx.strokeStyle = '#00ABE4';
        ctx.lineWidth = 3.6;
        ctx.setLineDash([]);
        ctx.shadowColor = '#00ABE4';
        ctx.shadowBlur = 10;
      } else {
        // High-contrast, clean baseline link visible against the background
        ctx.strokeStyle = activeTarget ? '#94a3b8' : '#64748b'; 
        ctx.lineWidth = 1.6;
        ctx.setLineDash([4, 3]); 
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
      }
      ctx.stroke();
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;

      // Draw Flow Pulses along the active path
      if (isPathLink) {
        const pulseRatio = pulseOffsetRef.current;
        const px = source.x + (target.x - source.x) * pulseRatio;
        const py = source.y + (target.y - source.y) * pulseRatio;
        ctx.beginPath();
        ctx.arc(px, py, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = '#38bdf8';
        ctx.fill();
      }

      // Link badges (PONT or capacity) - ONLY show when on active path, selected, or hovered!
      const isHoveredLink = hoveredNodeRef.current && (source.id === hoveredNodeRef.current.id || target.id === hoveredNodeRef.current.id);
      if (isPathLink || isSelected || isHoveredLink) {
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        ctx.font = 'bold 9px monospace';
        const label = link.displayType === 'PONT' ? 'PONT' : link.displayType;
        const tw = ctx.measureText(label).width;
        
        ctx.fillStyle = isPathLink ? '#00ABE4' : '#ffffff';
        ctx.fillRect(midX - tw/2 - 3, midY - 6, tw + 6, 12);
        ctx.strokeStyle = isPathLink ? '#0284c7' : '#94a3b8';
        ctx.lineWidth = 1;
        ctx.setLineDash([]);
        ctx.strokeRect(midX - tw/2 - 3, midY - 6, tw + 6, 12);
        
        ctx.fillStyle = isPathLink ? '#ffffff' : '#334155';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, midX, midY + 0.5);
      }
    });

    // Draw Footer Hint from reference image (bottom-right of graph space)
    ctx.font = '10px monospace';
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    let maxGraphX = 0, maxGraphY = 0;
    simNodes.forEach(n => {
      if (n.x > maxGraphX) maxGraphX = n.x;
      if (n.y > maxGraphY) maxGraphY = n.y;
    });
    ctx.fillText('drag to pan • scroll to zoom • click a node', maxGraphX, maxGraphY + 45);
    ctx.fillText('links between OLT and ONT: PONT', maxGraphX, maxGraphY + 60);

    ctx.setLineDash([]); 

    // Draw Rectangular Nodes
    simNodes.forEach(node => {
      const isSelected = selectedNode && node.id === selectedNode.id;
      const isHovered = hoveredNodeRef.current && node.id === hoveredNodeRef.current.id;
      const isPathNode = activePathNodeIds.has(node.id);
      
      const searchMatch = searchQuery && (
        node.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
        (node.name && node.name.toLowerCase().includes(searchQuery.toLowerCase()))
      );

      const hasAlarm = !!(node.hasAlarm || (node.alarms && node.alarms.length > 0) || (node.props && (node.props.hasAlarm || (node.props.alarms && node.props.alarms.length > 0))));

      const isDefect = activeDefectFilter && (
        (activeDefectFilter.id === 'def_evpn' && (node.release === '23.4R2' || node.id.includes('agg-'))) ||
        (activeDefectFilter.id === 'spof_sang' && (node.id.includes('sang') || node.id.includes('gldt'))) ||
        (activeDefectFilter.id === 'drift_stragglers' && node.outlier) ||
        (activeDefectFilter.id === 'alarm_cluster' && (hasAlarm || node.id.includes('olt-xg01'))) ||
        (activeDefectFilter.id === 'def_ont_isolated' && (node.id === 'ont:olt-xg02-3-08' || (node.id.includes('olt-xg02') && node.id.endsWith('-08'))))
      );

      const isOutlier = node.outlier || node.approved === false;

      const boxWidth = 90;
      const boxHeight = 22;
      const rx = 3; 

      const nx = node.x - boxWidth / 2;
      const ny = node.y - boxHeight / 2;

      if (isSelected || isPathNode || searchMatch || (hasAlarm && activeDefectFilter?.id === 'alarm_cluster') || (isDefect && activeDefectFilter?.id === 'def_ont_isolated')) {
        ctx.shadowColor = searchMatch ? '#ef4444' : (isDefect ? '#ef4444' : (hasAlarm ? '#f59e0b' : '#00ABE4'));
        ctx.shadowBlur = isSelected ? 16 : 12;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
      } else {
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
      }

      ctx.beginPath();
      ctx.moveTo(nx + rx, ny);
      ctx.lineTo(nx + boxWidth - rx, ny);
      ctx.arcTo(nx + boxWidth, ny, nx + boxWidth, ny + rx, rx);
      ctx.lineTo(nx + boxWidth, ny + boxHeight - rx);
      ctx.arcTo(nx + boxWidth, ny + boxHeight, nx + boxWidth - rx, ny + boxHeight, rx);
      ctx.lineTo(nx + rx, ny + boxHeight);
      ctx.arcTo(nx, ny + boxHeight, nx, ny + boxHeight - rx, rx);
      ctx.lineTo(nx, ny + rx);
      ctx.arcTo(nx, ny, nx + rx, ny, rx);
      ctx.closePath();

      ctx.fillStyle = node.fillColor;
      ctx.fill();

      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;

      ctx.lineWidth = (isSelected || isPathNode) ? 2.8 : 1.5;
      
      if (isSelected) {
        ctx.strokeStyle = '#00ABE4'; // Cyan border for selected
      } else if (isPathNode) {
        ctx.strokeStyle = '#38bdf8'; // Sky blue border for path chain
      } else if (isDefect) {
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2.5;
      } else if (hasAlarm) {
        ctx.strokeStyle = '#f59e0b'; // Amber ring for active alarms
        ctx.lineWidth = 2.2;
      } else if (isOutlier) {
        ctx.strokeStyle = '#f97316';
        ctx.lineWidth = 2;
      } else {
        ctx.strokeStyle = node.borderColor;
      }
      ctx.stroke();

      // Draw Alarm Alert Badge if node has open alarms
      if (hasAlarm) {
        ctx.beginPath();
        ctx.arc(nx + boxWidth - 2, ny + 2, 5.5, 0, Math.PI * 2);
        ctx.fillStyle = '#ef4444';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.font = 'bold 7px sans-serif';
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('!', nx + boxWidth - 2, ny + 2.5);
      }

      let labelText = node.name || '';
      if (!labelText) {
        if (node.id && node.id.startsWith('ont:')) {
          const parts = node.id.split('-');
          labelText = `ONT-${parts[parts.length - 1]}`;
        } else if (node.id) {
          labelText = node.id.replace('dev:', '').toUpperCase();
        } else {
          labelText = 'NODE';
        }
      }
      if (labelText.length > 14) {
        labelText = labelText.substring(0, 12) + '..';
      }

      ctx.font = 'bold 9px Inter, sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labelText, node.x, node.y + 1);
    });

    ctx.restore();
  }, [selectedNode, searchQuery, activeDefectFilter]);

  // Load Graph Deterministically (No Physics)
  useEffect(() => {
    nodesRef.current = visibleData.nodes;
    linksRef.current = visibleData.links;
    renderFrame();

    const timer = setTimeout(() => {
      handleFit();
    }, 50);

    return () => clearTimeout(timer);
  }, [visibleData, handleFit, renderFrame]);

  // Pulse animation loop
  useEffect(() => {
    let lastTime = performance.now();
    const loop = (now) => {
      pulseOffsetRef.current = (pulseOffsetRef.current + 0.018) % 1;
      if (selectedNode || activeDefectFilter) {
        renderFrame();
      }
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [selectedNode, activeDefectFilter, renderFrame]);

  // Mouse Interactivity
  const handleMouseDown = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const { x, y, scale } = transformRef.current;
    const graphX = (mouseX - x) / scale;
    const graphY = (mouseY - y) / scale;

    const boxHalfWidth = 45;
    const boxHalfHeight = 11;

    const clicked = nodesRef.current.find(n => {
      return (
        graphX >= n.x - boxHalfWidth &&
        graphX <= n.x + boxHalfWidth &&
        graphY >= n.y - boxHalfHeight &&
        graphY <= n.y + boxHalfHeight
      );
    });

    if (clicked) {
      onSelectNode(clicked);
    } else {
      isDraggingCanvasRef.current = true;
      dragStartRef.current = {
        x: e.clientX - x,
        y: e.clientY - y,
        initialX: e.clientX,
        initialY: e.clientY
      };
    }
  };

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDraggingCanvasRef.current) {
      transformRef.current.x = e.clientX - dragStartRef.current.x;
      transformRef.current.y = e.clientY - dragStartRef.current.y;
      renderFrame();
      return;
    }

    const { x, y, scale } = transformRef.current;
    const graphX = (mouseX - x) / scale;
    const graphY = (mouseY - y) / scale;

    const boxHalfWidth = 45;
    const boxHalfHeight = 11;

    const hovered = nodesRef.current.find(n => {
      return (
        graphX >= n.x - boxHalfWidth &&
        graphX <= n.x + boxHalfWidth &&
        graphY >= n.y - boxHalfHeight &&
        graphY <= n.y + boxHalfHeight
      );
    });

    if (hovered !== hoveredNodeRef.current) {
      hoveredNodeRef.current = hovered;
      onHoverNode(hovered);
      canvas.style.cursor = hovered ? 'pointer' : 'grab';
      renderFrame();
    }
  };

  const handleMouseUp = (e) => {
    if (isDraggingCanvasRef.current && dragStartRef.current.initialX !== undefined) {
      const distMoved = Math.hypot(
        e.clientX - dragStartRef.current.initialX,
        e.clientY - dragStartRef.current.initialY
      );
      if (distMoved < 4) {
        onSelectNode(null);
      }
    }
    isDraggingCanvasRef.current = false;
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const { x, y, scale } = transformRef.current;
    const newScale = Math.max(0.12, Math.min(scale * zoomFactor, 6.0));

    transformRef.current = {
      scale: newScale,
      x: mouseX - (mouseX - x) * (newScale / scale),
      y: mouseY - (mouseY - y) * (newScale / scale)
    };
    renderFrame();
  };

  const zoomIn = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = rect.width / 2;
    const mouseY = rect.height / 2;

    const { x, y, scale } = transformRef.current;
    const newScale = Math.min(scale * 1.3, 6.0);
    transformRef.current = {
      scale: newScale,
      x: mouseX - (mouseX - x) * (newScale / scale),
      y: mouseY - (mouseY - y) * (newScale / scale)
    };
    renderFrame();
  };

  const zoomOut = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = rect.width / 2;
    const mouseY = rect.height / 2;

    const { x, y, scale } = transformRef.current;
    const newScale = Math.max(scale * 0.75, 0.12);
    transformRef.current = {
      scale: newScale,
      x: mouseX - (mouseX - x) * (newScale / scale),
      y: mouseY - (mouseY - y) * (newScale / scale)
    };
    renderFrame();
  };

  return (
    <div className="relative w-full h-full bg-[#f4f6f8]">
      <div className="absolute bottom-4 left-4 z-20 bg-white border border-slate-200 p-4 rounded shadow-sm text-xs pointer-events-none">
        <h4 className="font-bold text-slate-500 mb-2 uppercase text-[10px] tracking-wider">Colour By Role</h4>
        <div className="space-y-1.5 mb-3">
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-[#4c1d95] border border-[#8b5cf6]"></div><span className="text-slate-600 font-medium">Core</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-[#0f766e] border border-[#0ea5e9]"></div><span className="text-slate-600 font-medium">Aggregation</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-[#334155] border border-[#64748b]"></div><span className="text-slate-600 font-medium">Access</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-[#14532d] border border-[#22c55e]"></div><span className="text-slate-600 font-medium">OLT</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-[#78350f] border border-[#f59e0b]"></div><span className="text-slate-600 font-medium">ONT</span></div>
        </div>
        <h4 className="font-bold text-slate-500 mb-2 uppercase text-[10px] tracking-wider">Ring</h4>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm border-2 border-[#f97316]"></div><span className="text-slate-600 font-medium">version outlier</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm border-2 border-[#ef4444]"></div><span className="text-slate-600 font-medium">defect exposed</span></div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm border-2 border-[#f59e0b] bg-amber-50 flex items-center justify-center text-[7.5px] font-extrabold text-red-600">!</div><span className="text-slate-600 font-medium">active alarm (29)</span></div>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className="w-full h-full block cursor-grab select-none"
      />

      <div className="absolute bottom-4 right-4 z-20 flex items-center gap-1.5 bg-white border border-slate-200 p-1.5 rounded shadow-sm">
        <button onClick={zoomIn} className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition" title="Zoom In (+)">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
        </button>
        <button onClick={zoomOut} className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition" title="Zoom Out (-)">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 12H4" /></svg>
        </button>
        <button onClick={handleFit} className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded transition" title="Fit Graph to Screen">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
        </button>
      </div>
    </div>
  );
}
