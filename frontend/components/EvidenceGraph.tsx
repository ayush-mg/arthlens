'use client';

import React, { useEffect, useRef, useState } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
import { EvidenceGraphData, GraphNodeData } from '../lib/types';
import { Network, ZoomIn, ZoomOut, Maximize2, Filter, Info, ExternalLink, Sparkles } from 'lucide-react';

interface EvidenceGraphProps {
  graphData: EvidenceGraphData | null;
  isLoading: boolean;
  onOpenProvenance: (quantityId: string) => void;
}

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({
  graphData,
  isLoading,
  onOpenProvenance,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Destroy existing instance
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: {
        nodes: graphData.elements.nodes.map((n) => ({
          data: n.data,
        })),
        edges: graphData.elements.edges.map((e) => ({
          data: e.data,
        })),
      },
      style: [
        // Base Node Style
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '120px',
            'font-family': 'monospace',
            'font-size': '10px',
            'font-weight': 'bold',
            color: '#f8fafc',
            width: '80px',
            height: '80px',
            'border-width': 2,
            'border-color': '#475569',
            'background-color': '#1e293b',
            'transition-property': 'background-color, border-color, border-width, opacity',
            'transition-duration': 0.25,
          },
        },
        // Quantity Nodes
        {
          selector: 'node[type = "quantity"]',
          style: {
            shape: 'round-rectangle',
            width: '110px',
            height: '65px',
            'background-color': '#0f172a',
            'border-color': 'data(color)',
            'border-width': 2.5,
          },
        },
        // Claim Nodes
        {
          selector: 'node[type = "claim"]',
          style: {
            shape: 'diamond',
            width: '90px',
            height: '90px',
            'background-color': '#1e1b4b',
            'border-color': '#6366f1',
            'border-width': 2.5,
          },
        },
        // Calculation Nodes
        {
          selector: 'node[type = "calculation"]',
          style: {
            shape: 'round-octagon',
            width: '95px',
            height: '65px',
            'background-color': '#083344',
            'border-color': '#06b6d4',
            'border-width': 2,
          },
        },
        // Source Nodes
        {
          selector: 'node[type = "source"]',
          style: {
            shape: 'barrel',
            width: '100px',
            height: '60px',
            'background-color': '#451a03',
            'border-color': '#f59e0b',
            'border-width': 2,
          },
        },
        // Edges Style
        {
          selector: 'edge',
          style: {
            width: 2,
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#64748b',
            'line-color': '#475569',
            'arrow-scale': 1.2,
            label: 'data(label)',
            'font-size': '8px',
            'font-family': 'monospace',
            color: '#94a3b8',
            'text-rotation': 'autorotate',
            'text-margin-y': -8,
          },
        },
        // Highlighted Ancestry
        {
          selector: '.highlighted',
          style: {
            'border-color': '#38bdf8',
            'border-width': 4,
            'line-color': '#38bdf8',
            'target-arrow-color': '#38bdf8',
            opacity: 1,
          },
        },
        // Dimmed Non-Ancestry
        {
          selector: '.dimmed',
          style: {
            opacity: 0.2,
          },
        },
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 40,
        spacingFactor: 1.5,
        avoidOverlap: true,
      },
    });

    // Node click handler: highlight ancestry and show inspector
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      setSelectedNode(node.data());

      // Highlight upstream and downstream ancestry
      const connected = node.predecessors().union(node.successors()).union(node);
      cy.elements().removeClass('highlighted dimmed');
      cy.elements().not(connected).addClass('dimmed');
      connected.addClass('highlighted');
    });

    // Background click handler: reset highlighting
    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        cy.elements().removeClass('highlighted dimmed');
        setSelectedNode(null);
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [graphData]);

  // Apply Node Type Filters
  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    if (filterType === 'all') {
      cy.elements().style('display', 'element');
    } else {
      cy.nodes().forEach((n) => {
        if (n.data('type') === filterType) {
          n.style('display', 'element');
        } else {
          n.style('display', 'none');
        }
      });
      // Ensure edges connecting visible nodes remain visible
      cy.edges().forEach((e) => {
        const sourceVisible = e.source().style('display') === 'element';
        const targetVisible = e.target().style('display') === 'element';
        e.style('display', sourceVisible && targetVisible ? 'element' : 'none');
      });
    }
  }, [filterType]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 30);

  return (
    <div className="relative h-[560px] w-full overflow-hidden rounded-xl border border-surface-border bg-surface-card shadow-2xl">
      {/* Cytoscape Canvas Container */}
      <div ref={containerRef} className="h-full w-full bg-slate-950/80" />

      {/* Floating Header Controls */}
      <div className="absolute left-4 top-4 z-10 flex flex-wrap items-center gap-2 rounded-lg border border-surface-border bg-surface-base/90 p-2 shadow-lg backdrop-blur-md text-xs">
        <div className="flex items-center space-x-2 mr-2">
          <Network className="h-4 w-4 text-brand-indigo" />
          <span className="font-bold text-white">Cytoscape Evidence Graph</span>
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center rounded border border-surface-border bg-slate-900 p-0.5">
          {['all', 'quantity', 'claim', 'calculation', 'source'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilterType(t)}
              className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase font-semibold transition-colors ${
                filterType === t
                  ? 'bg-brand-indigo text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas Zoom & View Controls */}
      <div className="absolute right-4 top-4 z-10 flex flex-col space-y-1 rounded-lg border border-surface-border bg-surface-base/90 p-1 shadow-lg backdrop-blur-md">
        <button
          type="button"
          onClick={handleZoomIn}
          className="rounded p-1.5 text-slate-400 hover:bg-surface-hover hover:text-white transition-colors"
          title="Zoom in"
          aria-label="Zoom in"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="rounded p-1.5 text-slate-400 hover:bg-surface-hover hover:text-white transition-colors"
          title="Zoom out"
          aria-label="Zoom out"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleFit}
          className="rounded p-1.5 text-slate-400 hover:bg-surface-hover hover:text-white transition-colors"
          title="Fit graph to view"
          aria-label="Fit view"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>

      {/* Selected Node Details Inspector Panel */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 right-4 z-20 max-w-md rounded-xl border border-surface-border bg-surface-card/95 p-4 shadow-2xl backdrop-blur-md text-xs space-y-2.5">
          <div className="flex items-start justify-between">
            <div className="space-y-0.5">
              <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-400 border border-slate-700/60">
                {selectedNode.type}
              </span>
              <h4 className="font-mono text-sm font-bold text-white break-words">
                {selectedNode.label.split('\n')[0]}
              </h4>
            </div>
            {selectedNode.status && (
              <span
                className="rounded-full px-2 py-0.5 font-mono text-[10px] font-bold"
                style={{
                  backgroundColor: `${selectedNode.color || '#3b82f6'}20`,
                  color: selectedNode.color || '#3b82f6',
                }}
              >
                {selectedNode.status}
              </span>
            )}
          </div>

          <p className="text-[11px] text-slate-300 leading-relaxed">
            {selectedNode.details || 'Epistemic DAG node registered in ArthLens verifiable ledger.'}
          </p>

          {/* Action: Open in Provenance Drawer if Quantity */}
          {selectedNode.type === 'quantity' && (
            <button
              type="button"
              onClick={() => onOpenProvenance(selectedNode.id)}
              className="flex items-center space-x-1.5 text-xs font-semibold text-brand-sky hover:underline"
            >
              <span>Inspect Full Ledger Record in Provenance Drawer</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
          <div className="text-center text-xs text-slate-400">
            <div className="mx-auto h-7 w-7 animate-spin rounded-full border-2 border-brand-indigo border-t-transparent mb-2" />
            Loading verifiable ancestry graph...
          </div>
        </div>
      )}
    </div>
  );
};
