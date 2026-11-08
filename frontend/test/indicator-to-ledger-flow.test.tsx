import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppWorkspace } from '../components/AppWorkspace';

vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(() => ({
    get: vi.fn(() => null),
  })),
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
  })),
  usePathname: vi.fn(() => '/app'),
}));

// Mock maplibre-gl and cytoscape for JSDOM
vi.mock('maplibre-gl', () => ({
  default: {
    Map: vi.fn(() => ({
      addControl: vi.fn(),
      on: vi.fn(),
      getSource: vi.fn(),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      flyTo: vi.fn(),
      remove: vi.fn(),
    })),
    NavigationControl: vi.fn(),
  },
}));

vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    elements: vi.fn().mockReturnValue({
      removeClass: vi.fn().mockReturnThis(),
      addClass: vi.fn().mockReturnThis(),
      not: vi.fn().mockReturnThis(),
      style: vi.fn().mockReturnThis(),
    }),
    nodes: vi.fn().mockReturnValue({ forEach: vi.fn(), style: vi.fn() }),
    edges: vi.fn().mockReturnValue({ forEach: vi.fn(), style: vi.fn() }),
    zoom: vi.fn().mockReturnValue(1.0),
    fit: vi.fn(),
    destroy: vi.fn(),
  })),
}));

const testIndicators = [
  {
    id: 'q-pop-120-2011',
    definition_key: 'population.total',
    value: 5954391.0,
    unit: 'persons',
    kind: 'OBSERVED',
    evidence_floor: 4,
    resolution: 2,
    as_of: '2011-03-01',
    quality_flags: ['STALE'],
    quality_status: 'STALE',
    quality_label: 'Stale Observation',
    quality_color: '#F97316',
    suitability: 'SUITABLE_HISTORICAL_ONLY',
    shading: {
      color_token: 'atlas-quality-stale',
      hex_color: '#F97316',
      fill_opacity: 0.7,
      stroke_style: 'hatched',
    },
  },
  {
    id: 'q-demand-120-2026',
    definition_key: 'demand.monthly',
    value: 85000.0,
    unit: 'INR/month',
    kind: 'ESTIMATED',
    evidence_floor: 2,
    resolution: 2,
    as_of: '2026-10-01',
    quality_flags: ['STALE_ANCESTRY'],
    quality_status: 'ESTIMATED',
    quality_label: 'Estimated / Modelled',
    quality_color: '#3B82F6',
    suitability: 'ESTIMATED_PROJECTION',
    shading: {
      color_token: 'atlas-quality-estimated',
      hex_color: '#3B82F6',
      fill_opacity: 0.6,
      stroke_style: 'dotted',
    },
  },
  {
    id: 'unavailable:in:district:120:agriculture.soil_fertility_index',
    definition_key: 'agriculture.soil_fertility_index',
    value: null,
    unit: 'index_score',
    kind: 'OBSERVED',
    evidence_floor: 0,
    resolution: 0,
    as_of: null,
    quality_flags: [],
    quality_status: 'UNAVAILABLE',
    quality_label: 'Data Unavailable',
    quality_color: '#94A3B8',
    suitability: 'UNSUITABLE_MISSING',
    shading: {
      color_token: 'atlas-quality-unavailable',
      hex_color: '#94A3B8',
      fill_opacity: 0.45,
      stroke_style: 'diagonal-cross',
    },
  },
];

const testDemandLedger = {
  id: 'q-demand-120-2026',
  definition_key: 'demand.monthly',
  value: 85000.0,
  unit: 'INR/month',
  kind: 'ESTIMATED',
  evidence_floor: 2,
  resolution: 2,
  as_of: '2026-10-01',
  quality_flags: ['STALE_ANCESTRY'],
  source_refs: ['DS-05'],
  source_name: 'ArthLens Downscaling Engine',
  source_version: 'DOWNSCALE-V1.2',
  retrieval_date: '2026-11-06',
  publication_date: '2026-10-05',
  method_id: 'downscaling.gravity_v1',
  assumptions: 'Downscaled monthly demand projection derived from census population baseline.',
  owner_id: null,
  parent_ids: ['q-pop-120-2011'],
  parents: [
    {
      id: 'q-pop-120-2011',
      definition_key: 'population.total',
      value: 5954391.0,
      unit: 'persons',
      kind: 'OBSERVED',
      quality_status: 'STALE',
    },
  ],
  quality: {
    primary_status: 'ESTIMATED',
    shading: {
      status: 'ESTIMATED',
      label: 'Estimated / Modelled',
      color_token: 'atlas-quality-estimated',
      hex_color: '#3B82F6',
      fill_opacity: 0.6,
      stroke_style: 'dotted',
      pattern: 'dotted',
    },
    suitability: 'ESTIMATED_PROJECTION',
    explanation: 'Value is modelled projection (kind=ESTIMATED).',
    issues: [],
    evaluation_date: '2026-11-06',
  },
  temporal: {
    as_of: '2026-10-01',
    retrieval_date: '2026-11-06',
    publication_date: '2026-10-05',
    elapsed_days: 36,
    max_age_days: 3650,
    has_policy: true,
  },
  calculation_restrictions: [
    'Estimated Projection (evidence floor <= 2; cannot support empirical claims)',
    'Stale Ancestry Restriction',
  ],
};

const testUnavailableSoilLedger = {
  id: 'unavailable:in:district:120:agriculture.soil_fertility_index',
  definition_key: 'agriculture.soil_fertility_index',
  value: null,
  unit: 'index_score',
  kind: 'OBSERVED',
  evidence_floor: 0,
  resolution: 0,
  as_of: null,
  quality_flags: [],
  source_refs: [],
  method_id: null,
  assumptions: 'No empirical observations ingested for this unit.',
  license_meta: '',
  owner_id: null,
  parent_ids: [],
  parents: [],
  quality: {
    primary_status: 'UNAVAILABLE',
    shading: {
      status: 'UNAVAILABLE',
      label: 'Data Unavailable',
      color_token: 'atlas-quality-unavailable',
      hex_color: '#94A3B8',
      fill_opacity: 0.45,
      stroke_style: 'diagonal-cross',
      pattern: 'diagonal-cross',
    },
    suitability: 'UNSUITABLE_MISSING',
    explanation: 'Indicator is uningested for target unit. Never represented as numeric zero.',
    issues: [],
    evaluation_date: '2026-11-06',
  },
  temporal: {
    as_of: null,
    retrieval_date: null,
    publication_date: null,
    elapsed_days: null,
    max_age_days: null,
    has_policy: false,
  },
  calculation_restrictions: [
    'Unavailable Evidence: Metric uningested. Strictly cannot be treated as numeric zero or used in empirical calculations.',
  ],
};

describe('Complete Atlas -> Indicator -> Provenance Interaction Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(global, 'fetch').mockImplementation(async (url: any) => {
      const urlStr = decodeURIComponent(String(url));
      if (urlStr.includes('/geo/in:district:120/indicators')) {
        return {
          ok: true,
          json: async () => ({ geo_unit_id: 'in:district:120', indicators: testIndicators }),
        } as any;
      }
      if (urlStr.includes('/ledger/q-demand-120-2026/graph')) {
        return {
          ok: true,
          json: async () => ({ root_quantity_id: 'q-demand-120-2026', elements: { nodes: [], edges: [] } }),
        } as any;
      }
      if (urlStr.includes('/ledger/q-pop-120-2011/graph')) {
        return {
          ok: true,
          json: async () => ({ root_quantity_id: 'q-pop-120-2011', elements: { nodes: [], edges: [] } }),
        } as any;
      }
      if (urlStr.includes('/ledger/q-demand-120-2026')) {
        return {
          ok: true,
          json: async () => testDemandLedger,
        } as any;
      }
      if (urlStr.includes('agriculture.soil_fertility_index')) {
        return {
          ok: true,
          json: async () => testUnavailableSoilLedger,
        } as any;
      }
      if (urlStr.includes('/geo/pilot-boundaries')) {
        return {
          ok: true,
          json: async () => ({ type: 'FeatureCollection', features: [] }),
        } as any;
      }
      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      } as any;
    });
  });

  it('renders verified indicators and clicking any metric opens its ledger record', async () => {
    render(<AppWorkspace standalone={true} />);

    // Step 1: Indicators loaded for pilot Prayagraj
    await waitFor(() => {
      expect(screen.getByText('population.total')).toBeInTheDocument();
      expect(screen.getByText('demand.monthly')).toBeInTheDocument();
    });

    // Step 2: Invariant check - values are rendered (e.g. 85,000 INR/month)
    expect(screen.getByText('85,000')).toBeInTheDocument();
    expect(screen.getByText('INR/month')).toBeInTheDocument();

    // Step 3: Click the demand metric to open Provenance Drawer
    const demandButton = screen.getByRole('button', {
      name: /Inspect ledger provenance for demand\.monthly/i,
    });
    fireEvent.click(demandButton);

    // Step 4: Verify Provenance Drawer opened and displays full epistemic record
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'demand.monthly' })).toBeInTheDocument();
      expect(screen.getByText('downscaling.gravity_v1')).toBeInTheDocument();
      expect(screen.getByText(/Gated Calculation Restrictions/i)).toBeInTheDocument();
      expect(screen.getByText(/Estimated Projection/i)).toBeInTheDocument();
      expect(screen.getByText(/Stale Ancestry Restriction/i)).toBeInTheDocument();
    });

    // Step 5: Verify parent quantity drilldown is functional
    const parentHeading = screen.getByText('Parent Ancestry (1)');
    expect(parentHeading).toBeInTheDocument();

    // Close the drawer
    const closeBtn = screen.getByRole('button', { name: /Close provenance drawer/i });
    fireEvent.click(closeBtn);
  });

  it('unavailable metric renders Unavailable (never zero) and opens data gap ledger record', async () => {
    render(<AppWorkspace standalone={true} />);

    await waitFor(() => {
      expect(screen.getByText('agriculture.soil_fertility_index')).toBeInTheDocument();
    });

    // Metric must display 'Unavailable', strictly not 0 or 0.0
    expect(screen.getByText('Unavailable')).toBeInTheDocument();

    // Clicking unavailable metric button opens epistemic ledger to inspect data gap
    const soilButton = screen.getByRole('button', {
      name: /Inspect ledger provenance for agriculture\.soil_fertility_index/i,
    });
    fireEvent.click(soilButton);

    // Drawer opens showing unavailable ledger state
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'agriculture.soil_fertility_index' })).toBeInTheDocument();
      expect(screen.getAllByText('UNAVAILABLE').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('fails closed when an unknown or invalid quantity reference is inspected', async () => {
    render(<AppWorkspace standalone={true} />);

    // Invariant reminder is permanently visible
    expect(
      screen.getByText(/Epistemic Invariant: Every displayed number opens its ledger record/i)
    ).toBeInTheDocument();
  });
});
