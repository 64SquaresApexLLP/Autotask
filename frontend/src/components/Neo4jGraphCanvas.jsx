import React, { useEffect, useRef, useCallback } from 'react';
import {
  forceSimulation,
  forceManyBody,
  forceLink,
  forceCollide,
  forceCenter,
  forceX,
  forceY
} from 'd3-force';

/**
 * Neo4j-Style Production D3 Force-Directed Canvas Graph Visualizer
 * - Anti-overlap collision physics & spread
 * - Smart Level-of-Detail (LOD) labels to prevent text crowding
 * - Smooth cursor-anchored zoom & pan
 * - Interactive node dragging & selection
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
  const simRef = useRef(null);
  const nodesRef = useRef([]);
  const linksRef = useRef([]);
  const animFrameRef = useRef(null);

  // Pan & Zoom state with wide zoom dynamic range
  const transformRef = useRef({ x: 0, y: 0, scale: 0.85 });
  const isDraggingCanvasRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const hoveredNodeRef = useRef(null);
  const draggedNodeRef = useRef(null);
  const pulseOffsetRef = useRef(0);

  // Filter visible nodes and links
  const visibleData = React.useMemo(() => {
    const visibleNodes = nodes.filter(n => !hiddenNodeTypes.has(n.type));
    const nodeSet = new Set(visibleNodes.map(n => n.id));
    const visibleRels = relationships.filter(
      r =>
        !hiddenRelTypes.has(r.type) &&
        nodeSet.has(typeof r.source === 'object' ? r.source.id : r.source) &&
        nodeSet.has(typeof r.target === 'object' ? r.target.id : r.target)
    );
    return { nodes: visibleNodes, links: visibleRels };
  }, [nodes, relationships, hiddenNodeTypes, hiddenRelTypes]);

  // 1-Hop Connected Neighbors of Selected Node
  const neighborSet = React.useMemo(() => {
    if (!selectedNode) return new Set();
    const set = new Set([selectedNode.id]);
    relationships.forEach(r => {
      const sId = typeof r.source === 'object' ? r.source.id : r.source;
      const tId = typeof r.target === 'object' ? r.target.id : r.target;
      if (sId === selectedNode.id) set.add(tId);
      if (tId === selectedNode.id) set.add(sId);
    });
    return set;
  }, [selectedNode, relationships]);

  // Fit & Center Viewport
  const handleFit = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !nodesRef.current.length) return;
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodesRef.current.forEach(n => {
      if (typeof n.x === 'number') {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }
    });

    const graphWidth = Math.max(maxX - minX, 150);
    const graphHeight = Math.max(maxY - minY, 150);

    const scaleX = (rect.width * 0.85) / graphWidth;
    const scaleY = (rect.height * 0.85) / graphHeight;
    const scale = Math.max(0.15, Math.min(scaleX, scaleY, 1.3));

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    transformRef.current = {
      scale,
      x: rect.width / 2 - centerX * scale,
      y: rect.height / 2 - centerY * scale
    };
    renderFrame();
  }, []);

  // Expose fit to parent if ref requested
  useEffect(() => {
    if (onFitRequested) {
      onFitRequested.current = handleFit;
    }
  }, [onFitRequested, handleFit]);

  // Main Canvas Render Frame with Anti-Overlap & Smart LOD
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

    // Deep Dark Canvas Background (#0b0f19)
    ctx.fillStyle = '#0b0f19';
    ctx.fillRect(0, 0, rect.width, rect.height);

    const { x, y, scale } = transformRef.current;
    ctx.translate(x, y);
    ctx.scale(scale, scale);

    const simNodes = nodesRef.current;
    const simLinks = linksRef.current;

    // 1. Draw Links
    simLinks.forEach(link => {
      const source = link.source;
      const target = link.target;
      if (!source || !target || typeof source.x !== 'number' || typeof target.x !== 'number') return;

      const sId = source.id;
      const tId = target.id;
      const isConnected = selectedNode && (sId === selectedNode.id || tId === selectedNode.id);
      const isDimmed = selectedNode && !isConnected;

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);

      if (isConnected) {
        // Connected link highlighted in standard Neo4j Sky Blue
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2.4 / scale;
      } else {
        // Default clean slate link
        ctx.strokeStyle = isDimmed ? 'rgba(51, 65, 85, 0.25)' : '#1e293b';
        ctx.lineWidth = 0.85 / scale;
      }
      ctx.stroke();

      // Flow pulse particle on active clicked connection
      if (isConnected) {
        const progress = pulseOffsetRef.current;
        const px = source.x + (target.x - source.x) * progress;
        const py = source.y + (target.y - source.y) * progress;

        ctx.beginPath();
        ctx.arc(px, py, 2.5 / scale, 0, Math.PI * 2);
        ctx.fillStyle = '#67e8f9';
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    });

    // 2. Draw Nodes (Circular Neo4j dots)
    simNodes.forEach(node => {
      if (typeof node.x !== 'number' || typeof node.y !== 'number') return;

      const isSelected = selectedNode && selectedNode.id === node.id;
      const isNeighbor = neighborSet.has(node.id);
      const isHovered = hoveredNodeRef.current && hoveredNodeRef.current.id === node.id;
      const isDimmed = selectedNode && !isNeighbor;
      const isSearchMatch = searchQuery && node.label?.toLowerCase().includes(searchQuery.toLowerCase());

      // Glowing Halo on Selected or Search Match
      if (isSelected || isSearchMatch || isHovered) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + (isSelected ? 7 : 4), 0, Math.PI * 2);
        ctx.fillStyle = isSelected
          ? 'rgba(56, 189, 248, 0.45)'
          : isSearchMatch
          ? 'rgba(239, 68, 68, 0.4)'
          : 'rgba(244, 114, 182, 0.35)';
        ctx.fill();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = isDimmed ? 'rgba(71, 85, 105, 0.35)' : node.color;
      ctx.fill();
      ctx.strokeStyle = isSelected ? '#ffffff' : '#0f172a';
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.stroke();

      // 3. SMART LEVEL-OF-DETAIL LABELS (Anti-Overlap)
      // Only show text for Devices, Selected, Search Match, or when zoomed in closely!
      const shouldShowLabel =
        node.isDevice ||
        isSelected ||
        isSearchMatch ||
        isHovered ||
        (scale > 1.35 && (node.type === 'Site' || node.type === 'Service')) ||
        scale > 2.2;

      if (shouldShowLabel) {
        const labelText = node.label || node.id;
        const fontSize = Math.max(8, Math.min(11, (node.isDevice ? 11 : 9) / Math.sqrt(scale)));

        ctx.font = `${node.isDevice || isSelected ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // Subtle dark background pill for crystal-clear readability
        const textMetrics = ctx.measureText(labelText);
        const textWidth = textMetrics.width;
        const textHeight = fontSize + 2;
        const textY = node.y + node.radius + 3;

        ctx.fillStyle = 'rgba(11, 15, 25, 0.75)';
        ctx.fillRect(node.x - textWidth / 2 - 3, textY, textWidth + 6, textHeight);

        ctx.fillStyle = isSelected ? '#38bdf8' : isDimmed ? '#475569' : node.isDevice ? '#e2e8f0' : '#cbd5e1';
        ctx.fillText(labelText, node.x, textY + 1);
      }
    });

    ctx.restore();
  }, [selectedNode, neighborSet, searchQuery, activeDefectFilter]);

  // Initialize and Update D3 Force Simulation with Anti-Overlap Physics
  useEffect(() => {
    if (!visibleData.nodes.length) {
      nodesRef.current = [];
      linksRef.current = [];
      if (simRef.current) simRef.current.stop();
      renderFrame();
      return;
    }

    const canvas = canvasRef.current;
    const rect = canvas ? canvas.getBoundingClientRect() : { width: 1200, height: 800 };
    const width = rect.width || 1200;
    const height = rect.height || 800;

    const existingMap = new Map(nodesRef.current.map(n => [n.id, n]));

    const simNodes = visibleData.nodes.map(n => {
      const prev = existingMap.get(n.id);
      return {
        ...n,
        x: prev ? prev.x : width / 2 + (Math.random() - 0.5) * 450,
        y: prev ? prev.y : height / 2 + (Math.random() - 0.5) * 450,
        vx: prev ? prev.vx : 0,
        vy: prev ? prev.vy : 0
      };
    });

    const simLinks = visibleData.links.map(l => ({
      ...l,
      source: l.source,
      target: l.target
    }));

    nodesRef.current = simNodes;
    linksRef.current = simLinks;

    if (simRef.current) {
      simRef.current.stop();
    }

    // Stronger collision and charge spacing to prevent any overlapping!
    const simulation = forceSimulation(simNodes)
      .force(
        'link',
        forceLink(simLinks)
          .id(d => d.id)
          .distance(d => (d.type === 'HAS_PORT' ? 45 : 90))
          .strength(0.75)
      )
      .force(
        'charge',
        forceManyBody()
          .strength(d => (d.isDevice ? -220 : -65))
          .distanceMax(800)
      )
      .force(
        'collide',
        forceCollide()
          .radius(d => d.radius + 12)
          .iterations(3)
      )
      .force('center', forceCenter(width / 2, height / 2))
      .force('x', forceX(width / 2).strength(0.035))
      .force('y', forceY(height / 2).strength(0.035))
      .alpha(1)
      .alphaDecay(0.025)
      .alphaMin(0.001);

    simRef.current = simulation;

    simulation.on('tick', () => {
      renderFrame();
    });

    simulation.on('end', () => {
      renderFrame();
    });

    const timer = setTimeout(() => {
      handleFit();
    }, 400);

    return () => {
      clearTimeout(timer);
      simulation.stop();
    };
  }, [visibleData, handleFit, renderFrame]);

  // Handle Physics Toggle
  useEffect(() => {
    if (!simRef.current) return;
    if (physicsEnabled) {
      simRef.current.alpha(0.3).restart();
    } else {
      simRef.current.stop();
    }
  }, [physicsEnabled]);

  // Particle Pulse Loop for Selected Edges
  useEffect(() => {
    let lastTime = performance.now();
    const loop = (now) => {
      pulseOffsetRef.current = (pulseOffsetRef.current + 0.018) % 1;
      if (selectedNode) {
        renderFrame();
      }
      animFrameRef.current = requestAnimationFrame(loop);
    };
    animFrameRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [selectedNode, renderFrame]);

  // Mouse Handlers: Dragging, Centered Cursor Zoom, & Hover Detection
  const handleMouseDown = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const { x, y, scale } = transformRef.current;
    const graphX = (mouseX - x) / scale;
    const graphY = (mouseY - y) / scale;

    const clicked = nodesRef.current.find(n => {
      const dx = n.x - graphX;
      const dy = n.y - graphY;
      return dx * dx + dy * dy <= (n.radius + 8) * (n.radius + 8);
    });

    if (clicked) {
      onSelectNode(clicked);
      draggedNodeRef.current = clicked;
      clicked.fx = clicked.x;
      clicked.fy = clicked.y;
      if (simRef.current) simRef.current.alphaTarget(0.3).restart();
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

    if (draggedNodeRef.current) {
      const { x, y, scale } = transformRef.current;
      draggedNodeRef.current.fx = (mouseX - x) / scale;
      draggedNodeRef.current.fy = (mouseY - y) / scale;
      return;
    }

    const { x, y, scale } = transformRef.current;
    const graphX = (mouseX - x) / scale;
    const graphY = (mouseY - y) / scale;

    const hovered = nodesRef.current.find(n => {
      const dx = n.x - graphX;
      const dy = n.y - graphY;
      return dx * dx + dy * dy <= (n.radius + 8) * (n.radius + 8);
    });

    if (hovered !== hoveredNodeRef.current) {
      hoveredNodeRef.current = hovered;
      onHoverNode(hovered);
      canvas.style.cursor = hovered ? 'pointer' : 'grab';
    }
  };

  const handleMouseUp = (e) => {
    if (isDraggingCanvasRef.current && dragStartRef.current.initialX !== undefined) {
      const distMoved = Math.hypot(
        e.clientX - dragStartRef.current.initialX,
        e.clientY - dragStartRef.current.initialY
      );
      if (distMoved < 4) {
        // User clicked empty space -> clear selection
        onSelectNode(null);
      }
    }
    isDraggingCanvasRef.current = false;
    if (draggedNodeRef.current) {
      draggedNodeRef.current.fx = null;
      draggedNodeRef.current.fy = null;
      draggedNodeRef.current = null;
      if (simRef.current) simRef.current.alphaTarget(0);
    }
  };

  // Proper Smooth Mouse-Centered Zoom
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

  // Zoom Button Helpers
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
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className="w-full h-full block cursor-grab select-none"
      />

      {/* Floating Canvas Controls (Zoom In, Zoom Out, Fit to Screen, Reset) */}
      <div className="absolute bottom-4 right-4 z-20 flex items-center gap-1.5 bg-[#111827]/90 border border-slate-800 p-1.5 rounded-xl backdrop-blur-md shadow-2xl">
        <button
          onClick={zoomIn}
          className="p-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800 transition"
          title="Zoom In (+)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <button
          onClick={zoomOut}
          className="p-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800 transition"
          title="Zoom Out (-)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 12H4" />
          </svg>
        </button>
        <button
          onClick={handleFit}
          className="p-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800 transition"
          title="Fit Graph to Screen"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      </div>
    </div>
  );
}
