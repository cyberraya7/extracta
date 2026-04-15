import { useRef, useCallback, useEffect, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { GraphData } from '../types';
import { ENTITY_COLORS } from '../types';

interface GraphVisualizationProps {
  data: GraphData;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  onSelectEdge: (source: string, target: string) => void;
}

export function GraphVisualization({
  data,
  selectedNodeId,
  onSelectNode,
  onSelectEdge,
}: GraphVisualizationProps) {
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const graphData = useMemo(() => {
    const nodes = data.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      score: n.score,
      connections: n.connections,
      occurrences: n.occurrences,
    }));

    const links = data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
      relationship: e.relationship,
      source_label: e.source_label,
      target_label: e.target_label,
    }));

    return { nodes, links };
  }, [data]);

  const connectedNodes = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const connected = new Set<string>();
    connected.add(selectedNodeId);
    for (const e of data.edges) {
      if (e.source === selectedNodeId) connected.add(e.target);
      if (e.target === selectedNodeId) connected.add(e.source);
    }
    return connected;
  }, [selectedNodeId, data.edges]);

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge')?.strength(-200);
      fgRef.current.d3Force('link')?.distance(100);
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
      const size = 4 + (node.connections || 1) * 1.5;
      const isSelected = node.id === selectedNodeId;
      const isConnected = connectedNodes.has(node.id);
      const dimmed = selectedNodeId && !isConnected;

      ctx.beginPath();
      ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI);
      ctx.fillStyle = dimmed ? `${color}30` : color;
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      const fontSize = Math.max(10 / globalScale, 2.5);
      if (globalScale > 0.6) {
        ctx.font = `${isSelected ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = dimmed ? '#475569' : '#e2e8f0';
        ctx.fillText(node.label, node.x!, node.y! + size + 2);
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
      ctx.lineWidth = dimmed ? 0.3 : Math.min(link.weight || 1, 4) * 0.5;
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

  return (
    <div
      ref={containerRef}
      className="bg-slate-900 rounded-xl border border-slate-800 h-full overflow-hidden relative"
    >
      <div className="absolute top-3 left-3 z-10 bg-slate-900/80 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-800">
        <span className="text-xs text-slate-400">
          {data.nodes.length} nodes &middot; {data.edges.length} edges
        </span>
      </div>
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
          const size = 4 + (node.connections || 1) * 1.5;
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, size + 4, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
      />
    </div>
  );
}
