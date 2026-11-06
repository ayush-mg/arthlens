import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { EvidenceGraph } from '../components/EvidenceGraph';
import { EvidenceGraphData } from '../lib/types';

// Mock cytoscape for JSDOM
let registeredTapNodeHandler: ((evt: any) => void) | null = null;
let registeredTapBgHandler: ((evt: any) => void) | null = null;

const mockElements = {
  removeClass: vi.fn().mockReturnThis(),
  addClass: vi.fn().mockReturnThis(),
  not: vi.fn().mockReturnThis(),
  style: vi.fn().mockReturnThis(),
};

const mockCyInstance = {
  on: vi.fn((event: string, ...args: any[]) => {
    if (event === 'tap' && args[0] === 'node') {
      registeredTapNodeHandler = args[1];
    } else if (event === 'tap' && args.length === 1) {
      registeredTapBgHandler = args[0];
    }
  }),
  elements: vi.fn().mockReturnValue(mockElements),
  nodes: vi.fn().mockReturnValue({
    forEach: vi.fn(),
    style: vi.fn(),
  }),
  edges: vi.fn().mockReturnValue({
    forEach: vi.fn(),
    style: vi.fn(),
  }),
  zoom: vi.fn().mockReturnValue(1.0),
  fit: vi.fn(),
  destroy: vi.fn(),
};

vi.mock('cytoscape', () => {
  return {
    default: vi.fn(() => mockCyInstance),
  };
});

describe('EvidenceGraph Component', () => {
  const sampleGraph: EvidenceGraphData = {
    root_quantity_id: 'q-demand-120',
    elements: {
      nodes: [
        {
          data: {
            id: 'q-demand-120',
            label: 'demand.monthly\n85,000 INR/month',
            type: 'quantity',
            status: 'ESTIMATED',
            value: 85000.0,
            unit: 'INR/month',
            kind: 'ESTIMATED',
            evidence_floor: 2,
            details: 'Derived demand projection',
          },
        },
        {
          data: {
            id: 'claim:q-demand-120',
            label: 'Verified Claim: demand.monthly',
            type: 'claim',
            details: 'Verified commercial viability',
          },
        },
        {
          data: {
            id: 'calc:q-demand-120',
            label: 'Method: downscaling.gravity_v1',
            type: 'calculation',
            details: 'Downscaling model using Census 2011 demographics',
          },
        },
        {
          data: {
            id: 'src:DS-05',
            label: 'Source: DS-05\nCensus of India 2011',
            type: 'source',
            details: 'Decennial demographic census baseline',
          },
        },
      ],
      edges: [
        {
          data: {
            id: 'e-q-demand-claim',
            source: 'q-demand-120',
            target: 'claim:q-demand-120',
            label: 'supports',
            type: 'supports_claim',
          },
        },
        {
          data: {
            id: 'e-calc-q-demand',
            source: 'calc:q-demand-120',
            target: 'q-demand-120',
            label: 'produces',
            type: 'calculates',
          },
        },
      ],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    registeredTapNodeHandler = null;
    registeredTapBgHandler = null;
  });

  it('renders header controls, node count, and filter pills', () => {
    const handleOpenProvenance = vi.fn();

    render(
      <EvidenceGraph
        graphData={sampleGraph}
        isLoading={false}
        onOpenProvenance={handleOpenProvenance}
      />
    );

    // Verify header and filter options
    expect(screen.getByText(/Cytoscape Evidence Graph/i)).toBeInTheDocument();
    expect(screen.getByText('all')).toBeInTheDocument();
    expect(screen.getByText('quantity')).toBeInTheDocument();
    expect(screen.getByText('claim')).toBeInTheDocument();
    expect(screen.getByText('calculation')).toBeInTheDocument();
    expect(screen.getByText('source')).toBeInTheDocument();
  });

  it('displays node inspector and triggers Provenance Drawer navigation on node tap', async () => {
    const handleOpenProvenance = vi.fn();

    render(
      <EvidenceGraph
        graphData={sampleGraph}
        isLoading={false}
        onOpenProvenance={handleOpenProvenance}
      />
    );

    // Simulate clicking the quantity node in Cytoscape
    expect(registeredTapNodeHandler).toBeDefined();
    if (registeredTapNodeHandler) {
      const mockNode = {
        data: () => ({
          id: 'q-demand-120',
          label: 'demand.monthly\n85,000 INR/month',
          type: 'quantity',
          status: 'ESTIMATED',
          color: '#3B82F6',
          details: 'Derived demand projection',
        }),
        predecessors: vi.fn().mockReturnValue({
          union: vi.fn().mockReturnValue({
            union: vi.fn().mockReturnValue(mockElements),
          }),
        }),
        successors: vi.fn().mockReturnValue({
          union: vi.fn().mockReturnValue(mockElements),
        }),
      };

      act(() => {
        registeredTapNodeHandler?.({ target: mockNode });
      });
    }

    // Verify Inspector details are displayed
    await waitFor(() => {
      expect(screen.getByText('demand.monthly')).toBeInTheDocument();
      expect(screen.getByText('ESTIMATED')).toBeInTheDocument();
      expect(screen.getByText('Derived demand projection')).toBeInTheDocument();
    });

    // Action button to open full ledger record in Provenance Drawer
    const inspectBtn = screen.getByRole('button', {
      name: /Inspect Full Ledger Record in Provenance Drawer/i,
    });
    expect(inspectBtn).toBeInTheDocument();
    fireEvent.click(inspectBtn);
    expect(handleOpenProvenance).toHaveBeenCalledWith('q-demand-120');
  });

  it('supports zoom and fit controls', () => {
    const handleOpenProvenance = vi.fn();

    render(
      <EvidenceGraph
        graphData={sampleGraph}
        isLoading={false}
        onOpenProvenance={handleOpenProvenance}
      />
    );

    const zoomInBtn = screen.getByRole('button', { name: /Zoom in/i });
    const zoomOutBtn = screen.getByRole('button', { name: /Zoom out/i });
    const fitBtn = screen.getByRole('button', { name: /Fit view/i });

    fireEvent.click(zoomInBtn);
    expect(mockCyInstance.zoom).toHaveBeenCalled();

    fireEvent.click(zoomOutBtn);
    expect(mockCyInstance.zoom).toHaveBeenCalled();

    fireEvent.click(fitBtn);
    expect(mockCyInstance.fit).toHaveBeenCalled();
  });
});
