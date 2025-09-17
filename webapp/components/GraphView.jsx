import dynamic from 'next/dynamic';
import { useEffect, useRef } from 'react';

const Cytoscape = dynamic(() => import('cytoscape'), { ssr: false });

export default function GraphView({ graph, onNodeClick, colorBy='label', filterLabel='', onReady }) {
  const ref = useRef(null);

  useEffect(() => {
    let cy;
    (async () => {
      const cytoscape = await Cytoscape;
      if (!ref.current || !graph) return;
      cy = cytoscape({
        container: ref.current,
        elements: [
          ...graph.nodes.map(n => ({ data: { id: String(n.id), label: n.label || n.id } })),
          ...graph.edges.map(e => ({ data: { id: String(e.id), source: String(e.source), target: String(e.target), label: e.type || '' } })),
        ],
        style: [
          { selector: 'node', style: { 'background-color': '#3b82f6', 'label': 'data(label)', 'font-size': 8, 'color': '#eef2ff' } },
          { selector: 'edge', style: { 'width': 1, 'line-color': '#64748b', 'target-arrow-color': '#64748b', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier' } },
        ],
        layout: { name: 'cose', animate: false },
      });
      // Color by label (category) if requested
      if (colorBy === 'label') {
        const palette = ['#22c55e','#ef4444','#eab308','#06b6d4','#8b5cf6','#f472b6','#14b8a6'];
        const labels = Array.from(new Set(graph.nodes.map(n=>n.label||'Node')));
        const colorMap = Object.fromEntries(labels.map((l,i)=>[l, palette[i % palette.length]]));
        cy.nodes().forEach(n=> n.style('background-color', colorMap[n.data('label')] || '#3b82f6'));
      }
      // Optional label filter
      if (filterLabel) {
        cy.nodes().forEach(n => n.style('display', (String(n.data('label'))===filterLabel)? 'element':'none'));
        cy.edges().forEach(e => {
          const s = e.source(); const t = e.target();
          e.style('display', (s.style('display')==='element' && t.style('display')==='element')? 'element':'none');
        });
      }
      cy.on('tap', 'node', (evt) => {
        const id = evt.target.id();
        if (onNodeClick) onNodeClick(id);
      });
      if (onReady) onReady(cy);
    })();
    return () => { if (cy) cy.destroy(); };
  }, [graph, colorBy, filterLabel]);

  return <div ref={ref} style={{ width: '100%', height: 480, border: '1px solid #1f2a44', borderRadius: 8 }} />;
}
