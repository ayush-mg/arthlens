'use client';

import React, { useEffect, useRef, useState } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
import { EvidenceGraphData, GraphNodeData } from '../lib/types';
import {
  Network,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ExternalLink,
  Lock,
  AlertCircle,
  RotateCcw,
  KeyRound,
  ShieldAlert,
} from 'lucide-react';
import { audioEngine } from '../lib/audio';

interface EvidenceGraphProps {
  graphData: EvidenceGraphData | null;
  isLoading: boolean;
  error?: string | null;
  isAuthenticated?: boolean;
  onOpenProvenance: (quantityId: string) => void;
  onSignIn?: () => void;
  onRetry?: () => void;
}

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({
  graphData,
  isLoading,
  error,
  isAuthenticated = true,
  onOpenProvenance,
  onSignIn,
  onRetry,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const selectedNodeRef = useRef<GraphNodeData | null>(null);

  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  // Keep ref synchronized for event handlers
  useEffect(() => {
    selectedNodeRef.current = selectedNode;
  }, [selectedNode]);

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
        // Base Node Style (Editorial Cartography)
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
            color: '#252923',
            width: '85px',
            height: '85px',
            'border-width': 2,
            'border-color': '#B49A65',
            'background-color': '#F3F0E8',
            'transition-property': 'background-color, border-color, border-width, opacity',
            'transition-duration': 0.25,
          },
        },
        // Quantity Nodes
        {
          selector: 'node[type = "quantity"]',
          style: {
            shape: 'round-rectangle',
            width: '115px',
            height: '70px',
            'background-color': '#FFFFFF',
            'border-color': '#203D32',
            'border-width': 2.5,
          },
        },
        // Claim Nodes
        {
          selector: 'node[type = "claim"]',
          style: {
            shape: 'diamond',
            width: '95px',
            height: '95px',
            'background-color': '#EDE8DC',
            'border-color': '#B76E4D',
            'border-width': 2.5,
          },
        },
        // Calculation Nodes
        {
          selector: 'node[type = "calculation"]',
          style: {
            shape: 'round-octagon',
            width: '100px',
            height: '70px',
            'background-color': '#FAF8F3',
            'border-color': '#B49A65',
            'border-width': 2,
          },
        },
        // Source Nodes
        {
          selector: 'node[type = "source"]',
          style: {
            shape: 'ellipse',
            width: '85px',
            height: '85px',
            'background-color': '#EDE8DC',
            'border-color': '#203D32',
            'border-width': 2,
          },
        },
        // Edge Base Style
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#B49A65',
            'target-arrow-color': '#203D32',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2,
            opacity: 0.8,
            label: 'data(label)',
            'font-family': 'monospace',
            'font-size': '8px',
            color: '#6E766A',
            'text-background-opacity': 0.85,
            'text-background-color': '#FAF8F3',
            'text-background-padding': '2px',
          },
        },
        // Highlighting styles
        {
          selector: 'node.highlighted',
          style: {
            'border-color': '#B76E4D',
            'border-width': 4,
            'background-color': '#FFF8F4',
          },
        },
        {
          selector: 'edge.highlighted',
          style: {
            'line-color': '#B76E4D',
            'target-arrow-color': '#B76E4D',
            width: 3.5,
            opacity: 1,
          },
        },
        {
          selector: '.faded',
          style: {
            opacity: 0.2,
          },
        },
      ],
      layout: {
        name: 'breadthfirst',
        directed: true,
        padding: 40,
        spacingFactor: 1.4,
      },
    });

    // Tap on Node -> Select and Highlight Ancestry
    cy.on('tap', 'node', (evt: EventObject) => {
      audioEngine.playClick(1150);
      const node = evt.target;
      const nodeData = node.data() as GraphNodeData;
      setSelectedNode(nodeData);

      // Highlight ancestry and dependents
      cy.elements().removeClass('highlighted faded');
      const ancestors = node.predecessors();
      const descendants = node.successors();
      const connected = ancestors.union(descendants).union(node);

      connected.addClass('highlighted');
      cy.elements().not(connected).addClass('faded');
    });

    // Hover over Node -> Highlight connections
    cy.on('mouseover', 'node', (evt: EventObject) => {
      const node = evt.target;
      const ancestors = node.predecessors();
      const descendants = node.successors();
      const connected = ancestors.union(descendants).union(node);
      connected.addClass('highlighted');
      cy.elements().not(connected).addClass('faded');
    });

    cy.on('mouseout', 'node', () => {
      const active = selectedNodeRef.current;
      if (!active) {
        cy.elements().removeClass('highlighted faded');
      } else {
        const activeNode = cy.$(`node#${active.id}`);
        if (activeNode.length > 0) {
          cy.elements().removeClass('highlighted faded');
          const connected = activeNode.predecessors().union(activeNode.successors()).union(activeNode);
          connected.addClass('highlighted');
          cy.elements().not(connected).addClass('faded');
        }
      }
    });

    // Tap on Canvas background -> Deselect
    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        audioEngine.playTick();
        setSelectedNode(null);
        cy.elements().removeClass('highlighted faded');
      }
    });

    if (typeof cy.ready === 'function') {
      cy.ready(() => {
        if (typeof cy.resize === 'function') cy.resize();
        if (typeof cy.fit === 'function') cy.fit(undefined, 40);
      });
    }

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graphData]);

  // Handle Type Filter Change
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
    <div className="relative h-[560px] lg:h-[620px] w-full overflow-hidden rounded border border-editorial-brass/40 bg-editorial-paper shadow-editorial">
      {/* Cytoscape Canvas Container */}
      <div ref={containerRef} className="h-full w-full bg-editorial-paper" />

      {/* Floating Header Controls */}
      <div className="absolute left-4 top-4 z-10 flex flex-wrap items-center gap-2 rounded border border-editorial-brass/40 bg-editorial-paper/95 p-2 shadow-editorial backdrop-blur-md text-xs">
        <div className="flex items-center space-x-2 mr-2">
          <Network className="h-4 w-4 text-editorial-copper" />
          <span className="font-serif font-bold text-editorial-forest">Cytoscape Evidence Graph</span>
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center rounded border border-editorial-brass/30 bg-editorial-ivory p-0.5">
          {['all', 'quantity', 'claim', 'calculation', 'source'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilterType(t)}
              className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase font-semibold transition-colors cursor-pointer ${
                filterType === t
                  ? 'bg-editorial-forest text-editorial-ivory shadow-sm'
                  : 'text-editorial-charcoal-light hover:text-editorial-charcoal'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas Zoom & View Controls */}
      <div className="absolute right-4 top-4 z-10 flex flex-col space-y-1 rounded border border-editorial-brass/40 bg-editorial-paper/95 p-1 shadow-editorial backdrop-blur-md">
        <button
          type="button"
          onClick={handleZoomIn}
          className="rounded p-1.5 text-editorial-charcoal hover:bg-editorial-ivory transition-colors cursor-pointer"
          title="Zoom in"
          aria-label="Zoom in"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="rounded p-1.5 text-editorial-charcoal hover:bg-editorial-ivory transition-colors cursor-pointer"
          title="Zoom out"
          aria-label="Zoom out"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={handleFit}
          className="rounded p-1.5 text-editorial-charcoal hover:bg-editorial-ivory transition-colors cursor-pointer"
          title="Fit graph to view"
          aria-label="Fit view"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>

      {/* Selected Node Details Inspector Panel */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 right-4 z-20 max-w-md rounded border border-editorial-brass/50 bg-editorial-paper/98 p-4 shadow-editorial-lg backdrop-blur-md text-xs space-y-2.5">
          <div className="flex items-start justify-between">
            <div className="space-y-0.5">
              <span className="rounded bg-editorial-ivory px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-editorial-charcoal-light border border-editorial-brass/30">
                {selectedNode.type}
              </span>
              <h4 className="font-mono text-sm font-bold text-editorial-charcoal break-words">
                {selectedNode.label.split('\n')[0]}
              </h4>
            </div>
            {selectedNode.status && (
              <span
                className="rounded-full px-2 py-0.5 font-mono text-[10px] font-bold"
                style={{
                  backgroundColor: `${selectedNode.color || '#B49A65'}20`,
                  color: selectedNode.color || '#203D32',
                }}
              >
                {selectedNode.status}
              </span>
            )}
          </div>

          <p className="text-[11px] text-editorial-charcoal-light leading-relaxed">
            {selectedNode.details || 'Epistemic DAG node registered in ArthLens verifiable ledger.'}
          </p>

          {/* Action: Open in Provenance Drawer if Quantity */}
          {selectedNode.type === 'quantity' && (
            <button
              type="button"
              onClick={() => onOpenProvenance(selectedNode.id)}
              className="flex items-center space-x-1.5 text-xs font-semibold text-editorial-copper hover:underline cursor-pointer font-mono"
            >
              <span>Inspect Full Ledger Record in Provenance Drawer</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {/* 1. Unauthenticated Access State */}
      {!isAuthenticated && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 text-center bg-editorial-paper/95 backdrop-blur-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-editorial-brass/50 bg-editorial-ivory text-editorial-forest mb-3 shadow-sm">
            <Lock className="h-6 w-6 text-editorial-copper" />
          </div>
          <h4 className="font-serif text-base font-bold text-editorial-forest mb-1">
            Authentication Required to Inspect Ancestry DAG
          </h4>
          <p className="max-w-md text-xs text-editorial-charcoal leading-relaxed mb-4">
            Under Handbook Part 10.1 and RBAC policies, detailed epistemic dependency graphs, parent quantities, and derivation lineages require an authenticated session.
          </p>
          {onSignIn && (
            <button
              type="button"
              onClick={onSignIn}
              className="inline-flex items-center space-x-2 rounded border border-editorial-forest bg-editorial-forest px-4 py-2 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-all shadow-sm cursor-pointer"
            >
              <KeyRound className="h-3.5 w-3.5" />
              <span>Sign In with Credentials</span>
            </button>
          )}
        </div>
      )}

      {/* 2. Error State */}
      {error && !isLoading && isAuthenticated && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center p-6 text-center bg-editorial-paper/95 backdrop-blur-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-editorial-copper/40 bg-editorial-copper/10 text-editorial-copper mb-3 shadow-sm">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h4 className="font-serif text-base font-bold text-editorial-forest mb-1">
            Evidence Graph Query Failed
          </h4>
          <p className="max-w-md text-xs text-editorial-charcoal leading-relaxed mb-4">
            {error}
          </p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center space-x-1.5 rounded border border-editorial-brass/40 bg-editorial-ivory px-3 py-1.5 font-mono text-xs text-editorial-charcoal hover:bg-editorial-paper transition-all shadow-sm cursor-pointer"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retry Graph Query</span>
            </button>
          )}
        </div>
      )}

      {/* 3. Empty State when authenticated but no graph loaded */}
      {isAuthenticated && !graphData && !isLoading && !error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-carto-graticule">
          <Network className="h-10 w-10 text-editorial-brass/60 mb-3" />
          <h4 className="font-serif text-base font-bold text-editorial-forest">
            Evidence Ancestry DAG
          </h4>
          <p className="max-w-md text-xs text-editorial-charcoal-light mt-1">
            Select an indicator from the Epistemic Ledger to render its complete verifiable calculation graph, parent quantities, and data sources.
          </p>
        </div>
      )}

      {/* 4. Loading State */}
      {isLoading && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-editorial-paper/85 backdrop-blur-sm">
          <div className="text-center text-xs font-mono text-editorial-charcoal-light">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-editorial-forest border-t-transparent mb-2" />
            <span>Retrieving verifiable ancestry graph from Epistemic Ledger...</span>
          </div>
        </div>
      )}
    </div>
  );
};
