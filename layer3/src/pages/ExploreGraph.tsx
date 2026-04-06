import { useEffect, useState, useMemo, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { fetchGraph, type GraphPayload } from "../api/client";

export function ExploreGraph() {
  const [data, setData] = useState<GraphPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });

  useEffect(() => {
    fetchGraph()
      .then(setData)
      .catch((e: Error) => setErr(e.message));
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      setDims({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight
      });
    }
    const handleResize = () => {
      if (containerRef.current) {
        setDims({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [containerRef.current]);

  const graphData = useMemo(() => {
    if (!data?.nodes?.length) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map(n => ({ 
        id: String(n.id), 
        name: n.name || String(n.id), 
        val: 1,
        fraud: n.fraud || (n.risk_score != null && n.risk_score >= 0.7)
      })),
      links: data.edges?.map(e => ({ source: String(e.source), target: String(e.target) })) || []
    };
  }, [data]);

  return (
    <div className="page" style={{ height: "calc(100vh - 40px)", display: "flex", flexDirection: "column" }}>
      <h1>Explore Network</h1>
      <p className="muted">
        Live AI-Agent monitoring visualization. Flagged and propagated nodes glow <span style={{ color: "var(--danger)" }}>red</span>.
      </p>
      {err && <p className="err">{err}</p>}
      
      <div 
        ref={containerRef}
        className="card" 
        style={{ flex: 1, marginTop: "1rem", padding: 0, overflow: "hidden", position: "relative" }}>
        {graphData.nodes.length > 0 && (
          <ForceGraph2D
            width={dims.width}
            height={dims.height}
            graphData={graphData}
            nodeLabel="name"
            nodeRelSize={6}
            linkColor={() => "rgba(51, 65, 85, 0.6)"}
            linkWidth={1.5}
            backgroundColor="transparent"
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Inter, Sans-Serif`;

              ctx.beginPath();
              ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
              ctx.fillStyle = node.fraud ? "#ef4444" : "#3b82f6";
              
              if (node.fraud) {
                ctx.shadowColor = "#ef4444";
                ctx.shadowBlur = 15;
              } else {
                ctx.shadowBlur = 0;
              }
              
              ctx.fill();
              ctx.shadowBlur = 0;
              
              // const isSupplier = label.startsWith("S");
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = node.fraud ? '#fca5a5' : '#cbd5e1';
              ctx.fillText(label.slice(0, 10), node.x, node.y + 12);
            }}
          />
        )}
      </div>
    </div>
  );
}
