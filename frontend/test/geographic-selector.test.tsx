import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GeographicSelector } from '../components/GeographicSelector';
import { GeoUnitSummary } from '../lib/types';

describe('GeographicSelector Component', () => {
  it('renders breadcrumb and verified geometry status for Prayagraj', () => {
    const handleSelect = vi.fn();
    const prayagraj: GeoUnitSummary = {
      id: 'in:district:120',
      name: 'Prayagraj',
      level: 2,
      parent_id: 'in:state:09',
      parent_name: 'Uttar Pradesh',
      lgd_code: '120',
      census_code: '175',
      navigation_status: 'NAVIGABLE',
      geometry_status: 'GEOMETRY_VERIFIED',
      analytical_status: 'ANALYSABLE',
      has_geometry: true,
    };

    render(
      <GeographicSelector
        selectedUnit={prayagraj}
        onSelectUnit={handleSelect}
      />
    );

    expect(screen.getByText('India')).toBeInTheDocument();
    expect(screen.getByText('Uttar Pradesh')).toBeInTheDocument();
    expect(screen.getAllByText('Prayagraj').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/GEOM: GEOMETRY_VERIFIED/i)).toBeInTheDocument();
    expect(screen.getByText(/NAV: NAVIGABLE/i)).toBeInTheDocument();
    expect(screen.getByText(/ANALYSIS: ANALYSABLE/i)).toBeInTheDocument();

    // No warning banner when geometry is verified
    expect(screen.queryByText(/Source-Gated Geographic Limitation/i)).not.toBeInTheDocument();
  });

  it('displays compact unobtrusive status indicator and keeps selector usable without oversized warning banner when geometry is missing', () => {
    const handleSelect = vi.fn();
    const varanasi: GeoUnitSummary = {
      id: 'in:district:187',
      name: 'Varanasi',
      level: 2,
      parent_id: 'in:state:09',
      lgd_code: '187',
      census_code: '197',
      navigation_status: 'NAVIGABLE',
      geometry_status: 'GEOMETRY_MISSING',
      analytical_status: 'ANALYSIS_UNAVAILABLE',
      has_geometry: false,
    };

    render(
      <GeographicSelector
        selectedUnit={varanasi}
        onSelectUnit={handleSelect}
      />
    );

    // Crucial requirement: No blocking or oversized warning banner
    expect(screen.queryByText(/Source-Gated Geographic Limitation/i)).not.toBeInTheDocument();

    // Compact status badges accurately communicate GEOM: GEOMETRY_MISSING without obstructing the user
    expect(screen.getByText(/GEOM: GEOMETRY_MISSING/i)).toBeInTheDocument();
    expect(screen.getByText(/NAV: NAVIGABLE/i)).toBeInTheDocument();
    expect(screen.getByText(/ANALYSIS: ANALYSIS_UNAVAILABLE/i)).toBeInTheDocument();

    // Geographic selector remains completely enabled and usable
    const searchInput = screen.getByRole('combobox');
    expect(searchInput).not.toBeDisabled();
  });
});
