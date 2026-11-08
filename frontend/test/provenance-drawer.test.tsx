import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProvenanceDrawer } from '../components/ProvenanceDrawer';
import { LedgerQuantityDetail } from '../lib/types';

const sampleQuantity: LedgerQuantityDetail = {
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
  assumptions: 'Downscaled monthly household retail spending model combining 2011 census demographics.',
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
    explanation: 'Value is modelled / estimated (kind=ESTIMATED), not an empirical direct observation.',
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
    'Stale Ancestry Restriction (inherited from historical contributing parent quantity q-pop-120-2011)',
  ],
};

describe('ProvenanceDrawer Component', () => {
  it('renders all required epistemic provenance fields', () => {
    const handleClose = vi.fn();
    const handleNavigate = vi.fn();
    const handleViewInGraph = vi.fn();

    render(
      <ProvenanceDrawer
        isOpen={true}
        onClose={handleClose}
        quantity={sampleQuantity}
        isLoading={false}
        onNavigateQuantity={handleNavigate}
        onViewInGraph={handleViewInGraph}
      />
    );

    // 1. Definition key & value
    expect(screen.getByText('demand.monthly')).toBeInTheDocument();
    expect(screen.getByText('85,000')).toBeInTheDocument();
    expect(screen.getByText('INR/month')).toBeInTheDocument();

    // 2. Kind & floor
    expect(screen.getAllByText('ESTIMATED').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Floor 2/i).length).toBeGreaterThanOrEqual(1);

    // 3. Method & Assumptions
    expect(screen.getByText('downscaling.gravity_v1')).toBeInTheDocument();
    expect(screen.getByText(/Downscaled monthly household retail spending model/i)).toBeInTheDocument();

    // 4. Calculation restrictions
    expect(screen.getByText(/Estimated Projection/i)).toBeInTheDocument();
    expect(screen.getByText(/Stale Ancestry Restriction/i)).toBeInTheDocument();

    // 5. Parent quantities
    expect(screen.getByText('population.total')).toBeInTheDocument();
    expect(screen.getByText(/persons/i)).toBeInTheDocument();
  });

  it('supports parent quantity navigation on click', () => {
    const handleClose = vi.fn();
    const handleNavigate = vi.fn();
    const handleViewInGraph = vi.fn();

    render(
      <ProvenanceDrawer
        isOpen={true}
        onClose={handleClose}
        quantity={sampleQuantity}
        isLoading={false}
        onNavigateQuantity={handleNavigate}
        onViewInGraph={handleViewInGraph}
      />
    );

    // Click the parent quantity button
    const parentButton = screen.getByText('population.total').closest('button');
    expect(parentButton).toBeTruthy();
    if (parentButton) {
      fireEvent.click(parentButton);
      expect(handleNavigate).toHaveBeenCalledWith('q-pop-120-2011');
    }
  });

  it('navigates to Evidence Graph on action button click', () => {
    const handleClose = vi.fn();
    const handleNavigate = vi.fn();
    const handleViewInGraph = vi.fn();

    render(
      <ProvenanceDrawer
        isOpen={true}
        onClose={handleClose}
        quantity={sampleQuantity}
        isLoading={false}
        onNavigateQuantity={handleNavigate}
        onViewInGraph={handleViewInGraph}
      />
    );

    const graphBtn = screen.getByRole('button', { name: /Explore in Evidence Graph/i });
    fireEvent.click(graphBtn);
    expect(handleViewInGraph).toHaveBeenCalledWith('q-demand-120-2026');
  });

  it('renders strictly floors 1-4 on monotonicity ladder and never displays Level 0 / Floor 0', () => {
    render(
      <ProvenanceDrawer
        isOpen={true}
        onClose={vi.fn()}
        quantity={sampleQuantity}
        isLoading={false}
      />
    );

    // Monotonicity ladder header
    expect(screen.getByText(/Floor Monotonicity Ladder \(Floors 1–4\)/i)).toBeInTheDocument();

    // Valid floors 1-4 must exist
    expect(screen.getAllByText('Floor 4').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Floor 3').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Floor 2').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Floor 1').length).toBeGreaterThan(0);

    // Floor 0 / Level 0 must strictly NOT exist
    expect(screen.queryByText(/Floor 0/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Level 0/i)).not.toBeInTheDocument();
    expect(screen.getByText(/UNAVAILABLE is a QualityStatus token/i)).toBeInTheDocument();
  });
});
