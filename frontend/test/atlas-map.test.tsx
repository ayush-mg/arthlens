import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AtlasMap } from '../components/AtlasMap';
import { GeoUnitSummary } from '../lib/types';

// Mock MapLibre GL JS for JSDOM
const mockMapInstance = {
  addControl: vi.fn(),
  on: vi.fn((event: string, ...args: any[]) => {
    if (event === 'load') {
      const cb = args[args.length - 1];
      setTimeout(cb, 10);
    }
  }),
  getSource: vi.fn().mockReturnValue(null),
  addSource: vi.fn(),
  addLayer: vi.fn(),
  flyTo: vi.fn(),
  remove: vi.fn(),
  getCanvas: vi.fn().mockReturnValue({ style: {} }),
};

vi.mock('maplibre-gl', () => {
  return {
    default: {
      Map: vi.fn(() => mockMapInstance),
      NavigationControl: vi.fn(),
    },
  };
});

describe('AtlasMap Component', () => {
  const verifiedPrayagraj: GeoUnitSummary = {
    id: 'in:district:120',
    name: 'Prayagraj',
    level: 2,
    parent_id: 'in:state:09',
    lgd_code: '120',
    census_code: '175',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_VERIFIED',
    analytical_status: 'ANALYSABLE',
    has_geometry: true,
  };

  const missingVaranasi: GeoUnitSummary = {
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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders verified pilot boundary overlay for Prayagraj and adds data-driven layers', async () => {
    const handleSelectUnitId = vi.fn();

    render(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={handleSelectUnitId}
        activeQualityFilter="ALL"
      />
    );

    // Overlay badge confirms GEOMETRY_VERIFIED
    expect(screen.getByText(/Vector Overlay: Prayagraj/i)).toBeInTheDocument();
    expect(screen.getByText('GEOMETRY_VERIFIED')).toBeInTheDocument();

    // Map attribution is present
    expect(screen.getByText(/CARTO basemap for spatial orientation only/i)).toBeInTheDocument();
    expect(screen.getByText(/OpenStreetMap/i)).toBeInTheDocument();

    // Source-gated overlay must NOT be displayed for verified district
    expect(screen.queryByText(/Boundary Geometry Unavailable/i)).not.toBeInTheDocument();

    // Verify map layers were registered with data-driven quality shading
    await waitFor(() => {
      expect(mockMapInstance.addSource).toHaveBeenCalledWith(
        'pilot-boundaries',
        expect.objectContaining({ type: 'geojson' })
      );
      expect(mockMapInstance.addLayer).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'pilot-boundary-fills',
          type: 'fill',
        })
      );
    });
  });

  it('displays elegant unavailable-geometry card without arbitrary or radar coordinates when geometry is missing', () => {
    const handleSelectUnitId = vi.fn();

    render(
      <AtlasMap
        selectedUnit={missingVaranasi}
        onSelectUnitId={handleSelectUnitId}
        activeQualityFilter="ALL"
      />
    );

    // Overlay badge confirms GEOMETRY_MISSING
    expect(screen.getByText('GEOMETRY_MISSING')).toBeInTheDocument();

    // Elegant source-gated card must be displayed
    expect(screen.getByText('Administrative Polygons Source-Gated')).toBeInTheDocument();
    expect(screen.getAllByText(/Varanasi/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/spatial coordinates and polygons are never fabricated or approximated/i)).toBeInTheDocument();

    // Must NOT contain arbitrary or approximate coordinate claims
    expect(screen.queryByText(/Coordinates approximate/i)).not.toBeInTheDocument();

    // Action button allows user to return to verified pilot boundary
    const focusBtn = screen.getByRole('button', { name: /Focus Pilot Boundary \(Prayagraj LGD 120\)/i });
    expect(focusBtn).toBeInTheDocument();
    fireEvent.click(focusBtn);
    expect(handleSelectUnitId).toHaveBeenCalledWith('in:district:120');
  });

  it('re-centers camera via flyTo when Prayagraj is selected', async () => {
    const handleSelectUnitId = vi.fn();

    const { rerender } = render(
      <AtlasMap
        selectedUnit={missingVaranasi}
        onSelectUnitId={handleSelectUnitId}
        activeQualityFilter="ALL"
      />
    );

    // Switch to Prayagraj
    rerender(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={handleSelectUnitId}
        activeQualityFilter="ALL"
      />
    );

    await waitFor(() => {
      expect(mockMapInstance.flyTo).toHaveBeenCalledWith(
        expect.objectContaining({
          center: [81.8463, 25.4358],
          zoom: 9.2,
        })
      );
    });
  });
});
