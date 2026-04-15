import { useRef, useCallback, useEffect, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { GraphData } from '../types';
import { ENTITY_COLORS, ENTITY_LABELS } from '../types';

interface GraphVisualizationProps {
  data: GraphData;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  onSelectEdge: (source: string, target: string) => void;
  /** Same filters as the sidebar / dashboard. Empty = all types. */
  typeFilters: string[];
  searchQuery: string;
  confidenceThreshold: number;
}

type ShapeType = 'circle' | 'diamond' | 'square' | 'triangle' | 'hexagon' | 'star' | 'pentagon' | 'cross' | 'octagon';

const ENTITY_SHAPES: Record<string, ShapeType> = {
  person: 'circle',
  organization: 'diamond',
  location: 'triangle',
  date: 'square',
  money: 'hexagon',
  'communication platform': 'pentagon',
  email: 'star',
  phone: 'cross',
  'ic number': 'octagon',
};

function drawShape(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  shape: ShapeType,
) {
  ctx.beginPath();
  switch (shape) {
    case 'circle':
      ctx.arc(x, y, size, 0, Math.PI * 2);
      break;
    case 'diamond':
      ctx.moveTo(x, y - size);
      ctx.lineTo(x + size, y);
      ctx.lineTo(x, y + size);
      ctx.lineTo(x - size, y);
      ctx.closePath();
      break;
    case 'square':
      ctx.rect(x - size, y - size, size * 2, size * 2);
      break;
    case 'triangle':
      ctx.moveTo(x, y - size);
      ctx.lineTo(x + size * 1.1, y + size * 0.8);
      ctx.lineTo(x - size * 1.1, y + size * 0.8);
      ctx.closePath();
      break;
    case 'hexagon':
      for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i - Math.PI / 6;
        const px = x + size * Math.cos(angle);
        const py = y + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      break;
    case 'pentagon':
      for (let i = 0; i < 5; i++) {
        const angle = (Math.PI * 2 / 5) * i - Math.PI / 2;
        const px = x + size * Math.cos(angle);
        const py = y + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      break;
    case 'star': {
      for (let i = 0; i < 5; i++) {
        const outerAngle = (Math.PI * 2 / 5) * i - Math.PI / 2;
        const innerAngle = outerAngle + Math.PI / 5;
        const ox = x + size * Math.cos(outerAngle);
        const oy = y + size * Math.sin(outerAngle);
        const ix = x + size * 0.45 * Math.cos(innerAngle);
        const iy = y + size * 0.45 * Math.sin(innerAngle);
        if (i === 0) ctx.moveTo(ox, oy);
        else ctx.lineTo(ox, oy);
        ctx.lineTo(ix, iy);
      }
      ctx.closePath();
      break;
    }
    case 'cross': {
      const arm = size * 0.35;
      ctx.moveTo(x - arm, y - size);
      ctx.lineTo(x + arm, y - size);
      ctx.lineTo(x + arm, y - arm);
      ctx.lineTo(x + size, y - arm);
      ctx.lineTo(x + size, y + arm);
      ctx.lineTo(x + arm, y + arm);
      ctx.lineTo(x + arm, y + size);
      ctx.lineTo(x - arm, y + size);
      ctx.lineTo(x - arm, y + arm);
      ctx.lineTo(x - size, y + arm);
      ctx.lineTo(x - size, y - arm);
      ctx.lineTo(x - arm, y - arm);
      ctx.closePath();
      break;
    }
    case 'octagon':
      for (let i = 0; i < 8; i++) {
        const angle = (Math.PI / 4) * i - Math.PI / 8;
        const px = x + size * Math.cos(angle);
        const py = y + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      break;
  }
}

export function GraphVisualization({
  data,
  selectedNodeId,
  onSelectNode,
  onSelectEdge,
  typeFilters,
  searchQuery,
  confidenceThreshold,
}: GraphVisualizationProps) {
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredData = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const nodes = data.nodes.filter((n) => {
      if (typeFilters.length > 0 && !typeFilters.includes(n.type)) return false;
      if ((n.score ?? 0) < confidenceThreshold) return false;
      if (q && !n.label.toLowerCase().includes(q)) return false;
      return true;
    });
    const nodeIds = new Set(nodes.map((n) => n.id));
    const edges = data.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
    );
    return { nodes, edges };
  }, [data, typeFilters, searchQuery, confidenceThreshold]);

  const presentTypes = useMemo(() => {
    const types = new Set<string>();
    filteredData.nodes.forEach((n) => types.add(n.type));
    return ENTITY_LABELS.filter((l) => types.has(l));
  }, [filteredData.nodes]);

  const sidebarFiltersActive =
    typeFilters.length > 0 ||
    searchQuery.trim().length > 0 ||
    filteredData.nodes.length < data.nodes.length;

  const graphData = useMemo(() => {
    const nodes = filteredData.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      score: n.score,
      connections: n.connections,
      occurrences: n.occurrences,
    }));

    const links = filteredData.edges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
      relationship: e.relationship,
      source_label: e.source_label,
      target_label: e.target_label,
    }));

    return { nodes, links };
  }, [filteredData]);

  const connectedNodes = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const connected = new Set<string>();
    connected.add(selectedNodeId);
    for (const e of filteredData.edges) {
      if (e.source === selectedNodeId) connected.add(e.target);
      if (e.target === selectedNodeId) connected.add(e.source);
    }
    return connected;
  }, [selectedNodeId, filteredData.edges]);

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge')?.strength(-400);
      fgRef.current.d3Force('link')?.distance(180);
    }
  }, [graphData]);

  const handleNodeClick = useCallback(
    (node: any) => {
      onSelectNode(node.id);
    },
    [onSelectNode]
  );

  const handleLinkClick = useCallback(
    (link: any) => {
      const src = typeof link.source === 'object' ? link.source.id : link.source;
      const tgt = typeof link.target === 'object' ? link.target.id : link.target;
      onSelectEdge(src, tgt);
    },
    [onSelectEdge]
  );

  const paintNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const color = ENTITY_COLORS[node.type] || '#64748b';
      const shape = ENTITY_SHAPES[node.type] || 'circle';
      const baseSize = 8 + (node.connections || 1) * 2;
      const size = Math.min(baseSize, 28);
      const isSelected = node.id === selectedNodeId;
      const isConnected = connectedNodes.has(node.id);
      const dimmed = selectedNodeId && !isConnected;

      drawShape(ctx, node.x!, node.y!, size, shape);
      ctx.fillStyle = dimmed ? `${color}30` : color;
      ctx.fill();

      if (isSelected) {
        drawShape(ctx, node.x!, node.y!, size + 2, shape);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2.5;
        ctx.stroke();
      } else if (!dimmed) {
        drawShape(ctx, node.x!, node.y!, size, shape);
        ctx.strokeStyle = `${color}60`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      const fontSize = Math.max(12 / globalScale, 3);
      if (globalScale > 0.4) {
        ctx.font = `${isSelected ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = dimmed ? '#475569' : '#e2e8f0';
        ctx.fillText(node.label, node.x!, node.y! + size + 3);
      }
    },
    [selectedNodeId, connectedNodes]
  );

  const paintLink = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const src = link.source;
      const tgt = link.target;
      if (!src.x || !tgt.x) return;

      const srcId = typeof src === 'object' ? src.id : src;
      const tgtId = typeof tgt === 'object' ? tgt.id : tgt;
      const isHighlighted =
        selectedNodeId && (connectedNodes.has(srcId) && connectedNodes.has(tgtId));
      const dimmed = selectedNodeId && !isHighlighted;

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle = dimmed ? '#1e293b' : '#475569';
      ctx.lineWidth = dimmed ? 0.3 : Math.min(link.weight || 1, 4) * 0.7;
      ctx.stroke();

      if (globalScale > 1.2 && link.relationship && !dimmed) {
        const midX = (src.x + tgt.x) / 2;
        const midY = (src.y + tgt.y) / 2;
        const fontSize = Math.max(8 / globalScale, 2);
        ctx.font = `${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#64748b';
        ctx.fillText(link.relationship, midX, midY);
      }
    },
    [selectedNodeId, connectedNodes]
  );

  if (data.nodes.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex items-center justify-center text-slate-500">
        No graph data to display
      </div>
    );
  }

  if (filteredData.nodes.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 h-full flex flex-col items-center justify-center text-slate-500 px-6 text-center gap-2">
        <p className="text-sm text-slate-400">No nodes match the sidebar filters.</p>
        <p className="text-xs text-slate-600">
          Adjust entity types, search text, or confidence under Filter in the left panel.
        </p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="bg-slate-900 rounded-xl border border-slate-800 h-full overflow-hidden relative"
    >
      <div className="absolute top-3 left-3 z-10 bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-800">
        <span className="text-xs text-slate-400">
          {filteredData.nodes.length} nodes &middot; {filteredData.edges.length} edges
          {sidebarFiltersActive && (
            <span className="text-blue-400 ml-1">(sidebar filters)</span>
          )}
        </span>
      </div>

      {presentTypes.length > 0 && (
        <div className="absolute bottom-3 left-3 right-3 z-10 bg-slate-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-800 max-h-28 overflow-y-auto">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5 font-medium">
            Shape legend
          </p>
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {presentTypes.map((label) => {
              const shape = ENTITY_SHAPES[label] || 'circle';
              return (
                <div
                  key={label}
                  className="flex items-center gap-1.5 text-[10px] text-slate-400 capitalize"
                >
                  <ShapeIcon shape={shape} color={ENTITY_COLORS[label]} />
                  {label}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        onNodeClick={handleNodeClick}
        onLinkClick={handleLinkClick}
        backgroundColor="#0f172a"
        width={containerRef.current?.clientWidth}
        height={containerRef.current?.clientHeight}
        cooldownTicks={100}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const size = 8 + (node.connections || 1) * 2 + 4;
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, Math.min(size, 32), 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
      />
    </div>
  );
}

function ShapeIcon({ shape, color }: { shape: ShapeType; color: string }) {
  const size = 12;
  const half = size / 2;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      {shape === 'circle' && <circle cx={half} cy={half} r={half - 1} fill={color} />}
      {shape === 'square' && <rect x={1} y={1} width={size - 2} height={size - 2} fill={color} />}
      {shape === 'diamond' && (
        <polygon points={`${half},1 ${size - 1},${half} ${half},${size - 1} 1,${half}`} fill={color} />
      )}
      {shape === 'triangle' && (
        <polygon points={`${half},1 ${size - 1},${size - 1} 1,${size - 1}`} fill={color} />
      )}
      {shape === 'hexagon' && (
        <polygon
          points={[0, 1, 2, 3, 4, 5].map((i) => {
            const a = (Math.PI / 3) * i - Math.PI / 6;
            return `${half + (half - 1) * Math.cos(a)},${half + (half - 1) * Math.sin(a)}`;
          }).join(' ')}
          fill={color}
        />
      )}
      {shape === 'pentagon' && (
        <polygon
          points={[0, 1, 2, 3, 4].map((i) => {
            const a = (Math.PI * 2 / 5) * i - Math.PI / 2;
            return `${half + (half - 1) * Math.cos(a)},${half + (half - 1) * Math.sin(a)}`;
          }).join(' ')}
          fill={color}
        />
      )}
      {shape === 'star' && (
        <polygon
          points={[0, 1, 2, 3, 4].flatMap((i) => {
            const oa = (Math.PI * 2 / 5) * i - Math.PI / 2;
            const ia = oa + Math.PI / 5;
            return [
              `${half + (half - 1) * Math.cos(oa)},${half + (half - 1) * Math.sin(oa)}`,
              `${half + (half - 1) * 0.45 * Math.cos(ia)},${half + (half - 1) * 0.45 * Math.sin(ia)}`,
            ];
          }).join(' ')}
          fill={color}
        />
      )}
      {shape === 'cross' && (
        <polygon points={`4,1 8,1 8,4 11,4 11,8 8,8 8,11 4,11 4,8 1,8 1,4 4,4`} fill={color} />
      )}
      {shape === 'octagon' && (
        <polygon
          points={[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
            const a = (Math.PI / 4) * i - Math.PI / 8;
            return `${half + (half - 1) * Math.cos(a)},${half + (half - 1) * Math.sin(a)}`;
          }).join(' ')}
          fill={color}
        />
      )}
    </svg>
  );
}
