import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AtlasMap, isAxisAlignedBoundingBox } from '../components/AtlasMap';
import { GeoUnitSummary } from '../lib/types';
import { fetchUnitBoundary } from '../lib/api';
import maplibregl from 'maplibre-gl';

// Mock MapLibre GL JS for JSDOM
const mockMapInstance = {
  addControl: vi.fn(),
  on: vi.fn((event: string, ...args: any[]) => {
    if (event === 'load' || event === 'styledata') {
      const cb = args[args.length - 1];
      setTimeout(cb, 10);
    }
  }),
  once: vi.fn((event: string, cb: any) => {
    setTimeout(cb, 10);
  }),
  isStyleLoaded: vi.fn().mockReturnValue(true),
  getSource: vi.fn().mockReturnValue(null),
  addSource: vi.fn(),
  getLayer: vi.fn().mockImplementation((id: string) => ({ id })),
  addLayer: vi.fn(),
  setFilter: vi.fn(),
  setPaintProperty: vi.fn(),
  setLayoutProperty: vi.fn(),
  fitBounds: vi.fn(),
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

// Mock api fetchPilotBoundaries and fetchUnitBoundary
vi.mock('../lib/api', () => ({
  getAuthToken: vi.fn().mockReturnValue('mock-token'),
  fetchPilotBoundaries: vi.fn().mockResolvedValue({
    type: 'FeatureCollection',
    name: 'Administrative_Boundaries_Prayagraj_Census2011',
    features: [
      {
        type: 'Feature',
        id: 'in:district:120',
        properties: {
          DISTRICT: 'Prayagraj',
          lgd_code: '120',
          geometry_status: 'GEOMETRY_VERIFIED',
          quality_status: 'CURRENT',
        },
        geometry: {
          type: 'Polygon',
          coordinates: [
            // Realistic non-axis-aligned boundary with > 5 coordinates
            [
              [81.52, 24.80],
              [81.70, 24.85],
              [82.00, 24.90],
              [82.35, 25.20],
              [82.20, 25.75],
              [81.90, 25.70],
              [81.52, 24.80],
            ],
          ],
        },
      },
    ],
  }),
  fetchUnitBoundary: vi.fn().mockImplementation(async (geoId: string) => {
    if (geoId === 'in:district:120') {
      return {
        type: 'FeatureCollection',
        name: 'Administrative_Boundaries_DS-09',
        features: [
          {
            type: 'Feature',
            id: 'in:district:120',
            properties: {
              DISTRICT: 'Prayagraj',
              name: 'Prayagraj',
              lgd_code: '120',
              geometry_status: 'GEOMETRY_VERIFIED',
              quality_status: 'CURRENT',
            },
            geometry: {
              type: 'Polygon',
              coordinates: [
                [
                  [81.52, 24.80],
                  [81.70, 24.85],
                  [82.00, 24.90],
                  [82.35, 25.20],
                  [82.20, 25.75],
                  [81.90, 25.70],
                  [81.52, 24.80],
                ],
              ],
            },
          },
        ],
        geo_id: 'in:district:120',
        geometry_status: 'GEOMETRY_VERIFIED',
        has_geometry: true,
      };
    }
    return {
      type: 'FeatureCollection',
      name: 'Administrative_Boundaries',
      features: [],
      geo_id: geoId,
      geometry_status: 'GEOMETRY_MISSING',
      has_geometry: false,
    };
  }),
}));

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

  it('initializes MapLibre with a real geographic basemap source (not empty sources)', () => {
    render(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    expect(maplibregl.Map).toHaveBeenCalledWith(
      expect.objectContaining({
        style: expect.objectContaining({
          sources: expect.objectContaining({
            'osm-raster-tiles': expect.objectContaining({
              type: 'raster',
              tiles: expect.arrayContaining([expect.stringContaining('tile.openstreetmap.org')]),
            }),
          }),
        }),
      })
    );
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
    expect(screen.getByText(/GEOM: GEOMETRY_VERIFIED/i)).toBeInTheDocument();

    // Map attribution is present for OSM contributors
    expect(screen.getAllByText(/OpenStreetMap/i).length).toBeGreaterThanOrEqual(1);

    // Source-gated overlay must NOT be displayed for verified district
    expect(screen.queryByText(/Administrative Boundary Source-Gated/i)).not.toBeInTheDocument();

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
      expect(mockMapInstance.addLayer).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'pilot-boundary-strokes',
          type: 'line',
        })
      );
    });
  });

  it('displays compact unobtrusive missing-geometry indicator without blocking map interaction when geometry is missing (Varanasi)', async () => {
    const handleSelectUnitId = vi.fn();
    const handleOpenProvenance = vi.fn();

    render(
      <AtlasMap
        selectedUnit={missingVaranasi}
        onSelectUnitId={handleSelectUnitId}
        activeQualityFilter="ALL"
        onOpenProvenance={handleOpenProvenance}
      />
    );

    // Overlay badge confirms GEOMETRY_MISSING
    expect(screen.getAllByText(/GEOM: GEOMETRY_MISSING/i).length).toBeGreaterThanOrEqual(1);

    // Compact unobtrusive status indicator must be displayed (never an oversized blocking card)
    await waitFor(() => {
      const indicator = screen.getByTestId('missing-geometry-indicator');
      expect(indicator).toBeInTheDocument();
      expect(screen.getByText(/Boundary unmapped/i)).toBeInTheDocument();
    });

    // Verify no blocking full-map overlay exists
    expect(screen.queryByText(/Varanasi Administrative Boundary Source-Gated/i)).not.toBeInTheDocument();

    // Provenance button allows inspecting source gaps
    const provBtn = screen.getByRole('button', { name: /Provenance Details/i });
    expect(provBtn).toBeInTheDocument();
    fireEvent.click(provBtn);
    expect(handleOpenProvenance).toHaveBeenCalledWith('missing-geom:in:district:187');
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

  it('filters out boundary polygons when switching from verified district to unverified district', async () => {
    // Return mock layer for getLayer
    mockMapInstance.getLayer.mockReturnValue({});

    const { rerender } = render(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    // Initial verified Prayagraj filter
    await waitFor(() => {
      expect(mockMapInstance.setFilter).toHaveBeenCalledWith(
        'pilot-boundary-fills',
        ['==', ['get', 'lgd_code'], '120']
      );
    });

    // Switch to Varanasi (GEOMETRY_MISSING)
    rerender(
      <AtlasMap
        selectedUnit={missingVaranasi}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    // Must filter out all boundary polygons so Prayagraj's polygon does not leak
    await waitFor(() => {
      expect(mockMapInstance.setFilter).toHaveBeenCalledWith(
        'pilot-boundary-fills',
        ['==', ['get', 'lgd_code'], '__NONE__']
      );
      expect(mockMapInstance.setFilter).toHaveBeenCalledWith(
        'pilot-boundary-strokes',
        ['==', ['get', 'lgd_code'], '__NONE__']
      );
    });
  });

  it('correctly detects and rejects synthetic axis-aligned bounding boxes', () => {
    // 4-corner bounding box rectangle (5 points, 2 unique X, 2 unique Y)
    const bboxPolygon = {
      type: 'Polygon',
      coordinates: [
        [
          [81.52, 24.78],
          [82.35, 24.78],
          [82.35, 25.79],
          [81.52, 25.79],
          [81.52, 24.78],
        ],
      ],
    };

    expect(isAxisAlignedBoundingBox(bboxPolygon)).toBe(true);

    // Realistic multi-vertex boundary polygon
    const realPolygon = {
      type: 'Polygon',
      coordinates: [
        [
          [81.52, 24.80],
          [81.70, 24.85],
          [82.00, 24.90],
          [82.35, 25.20],
          [82.20, 25.75],
          [81.90, 25.70],
          [81.52, 24.80],
        ],
      ],
    };

    expect(isAxisAlignedBoundingBox(realPolygon)).toBe(false);
  });

  it('registers genuine PMTiles vector source and vector layers', async () => {
    render(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    await waitFor(() => {
      expect(mockMapInstance.addSource).toHaveBeenCalledWith(
        'pilot-pmtiles-source',
        expect.objectContaining({
          type: 'vector',
          url: expect.stringContaining('pmtiles://'),
        })
      );
      expect(mockMapInstance.addLayer).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'pmtiles-boundary-fills',
          type: 'fill',
          source: 'pilot-pmtiles-source',
          'source-layer': 'admin_boundaries',
        })
      );
      expect(mockMapInstance.addLayer).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'pmtiles-boundary-strokes',
          type: 'line',
          source: 'pilot-pmtiles-source',
          'source-layer': 'admin_boundaries',
        })
      );
    });
  });

  it('fetches unit boundary dynamically via fetchUnitBoundary and clears previous layer', async () => {
    const mockSource = {
      setData: vi.fn(),
    };
    mockMapInstance.getSource.mockImplementation((id: string) => {
      if (id === 'pilot-boundaries') return mockSource;
      return null;
    });

    const { rerender } = render(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    await waitFor(() => {
      expect(mockSource.setData).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'FeatureCollection',
          features: expect.arrayContaining([
            expect.objectContaining({ id: 'in:district:120' }),
          ]),
        })
      );
    });

    // Switch to missing Varanasi: must immediately clear previous boundary
    rerender(
      <AtlasMap
        selectedUnit={missingVaranasi}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    await waitFor(() => {
      expect(mockSource.setData).toHaveBeenCalledWith({
        type: 'FeatureCollection',
        features: [],
      });
      expect(screen.getByTestId('missing-geometry-indicator')).toBeInTheDocument();
    });
  });

  it('triggers error state when receiving 0 features with non-missing status (inconsistent response)', async () => {
    const originalImpl = vi.mocked(fetchUnitBoundary).getMockImplementation();
    vi.mocked(fetchUnitBoundary).mockImplementation(async () => ({
      type: 'FeatureCollection',
      name: 'Inconsistent_Response',
      features: [],
      geo_id: 'in:district:999',
      geometry_status: 'GEOMETRY_VERIFIED',
      has_geometry: true,
    } as any));

    try {
      render(
        <AtlasMap
          selectedUnit={{
            ...missingVaranasi,
            id: 'in:district:999',
          }}
          onSelectUnitId={vi.fn()}
          activeQualityFilter="ALL"
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('boundary-error-indicator')).toBeInTheDocument();
        expect(screen.getByText(/Inconsistent boundary response/i)).toBeInTheDocument();
        expect(screen.queryByTestId('missing-geometry-indicator')).not.toBeInTheDocument();
      });
    } finally {
      if (originalImpl) {
        vi.mocked(fetchUnitBoundary).mockImplementation(originalImpl);
      }
    }
  });

  it('starts in loading resolution state before boundary resolves', async () => {
    render(
      <AtlasMap
        selectedUnit={{
          ...verifiedPrayagraj,
          geometry_status: 'GEOMETRY_UNVALIDATED',
          has_geometry: false,
        }}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    // Initial render must show resolution loading badge or spinner before settling
    expect(screen.getByTestId('boundary-resolution-badge')).toBeInTheDocument();
  });

  it('rejects boundary responses with unknown geometry status', async () => {
    const originalImpl = vi.mocked(fetchUnitBoundary).getMockImplementation();
    vi.mocked(fetchUnitBoundary).mockImplementation(async () => ({
      type: 'FeatureCollection',
      name: 'Unknown_Status_Response',
      features: [
        {
          type: 'Feature',
          id: 'in:district:120',
          properties: {
            geometry_status: 'UNKNOWN_CUSTOM_TIER',
          },
          geometry: {
            type: 'Polygon',
            coordinates: [[[81.5, 24.8], [82.3, 24.8], [82.3, 25.7], [81.5, 25.5], [81.5, 24.8]]],
          },
        },
      ],
      geometry_status: 'UNKNOWN_CUSTOM_TIER',
      has_geometry: true,
    } as any));

    try {
      render(
        <AtlasMap
          selectedUnit={verifiedPrayagraj}
          onSelectUnitId={vi.fn()}
          activeQualityFilter="ALL"
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('boundary-error-indicator')).toBeInTheDocument();
        expect(screen.getByText(/Unsupported or unknown geometry status/i)).toBeInTheDocument();
      });
    } finally {
      if (originalImpl) vi.mocked(fetchUnitBoundary).mockImplementation(originalImpl);
    }
  });

  it('rejects conflicting top-level and feature-level geometry statuses', async () => {
    const originalImpl = vi.mocked(fetchUnitBoundary).getMockImplementation();
    vi.mocked(fetchUnitBoundary).mockImplementation(async () => ({
      type: 'FeatureCollection',
      name: 'Conflicting_Status_Response',
      features: [
        {
          type: 'Feature',
          id: 'in:district:120',
          properties: {
            geometry_status: 'GEOMETRY_HISTORICAL',
          },
          geometry: {
            type: 'Polygon',
            coordinates: [[[81.5, 24.8], [82.3, 24.8], [82.3, 25.7], [81.5, 25.5], [81.5, 24.8]]],
          },
        },
      ],
      geometry_status: 'GEOMETRY_VERIFIED', // Conflicts with feature's GEOMETRY_HISTORICAL
      has_geometry: true,
    } as any));

    try {
      render(
        <AtlasMap
          selectedUnit={verifiedPrayagraj}
          onSelectUnitId={vi.fn()}
          activeQualityFilter="ALL"
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('boundary-error-indicator')).toBeInTheDocument();
        expect(screen.getByText(/Conflicting geometry status/i)).toBeInTheDocument();
      });
    } finally {
      if (originalImpl) vi.mocked(fetchUnitBoundary).mockImplementation(originalImpl);
    }
  });

  it('rejects boundary response missing authoritative status (no implicit GEOMETRY_VERIFIED fallback)', async () => {
    const originalImpl = vi.mocked(fetchUnitBoundary).getMockImplementation();
    vi.mocked(fetchUnitBoundary).mockImplementation(async () => ({
      type: 'FeatureCollection',
      name: 'Missing_Status_Response',
      features: [
        {
          type: 'Feature',
          id: 'in:district:120',
          properties: {
            // No geometry_status in properties
          },
          geometry: {
            type: 'Polygon',
            coordinates: [[[81.5, 24.8], [82.3, 24.8], [82.3, 25.7], [81.5, 25.5], [81.5, 24.8]]],
          },
        },
      ],
      // No top-level geometry_status
      has_geometry: true,
    } as any));

    try {
      render(
        <AtlasMap
          selectedUnit={{
            ...verifiedPrayagraj,
            geometry_status: 'GEOMETRY_UNVALIDATED',
          }}
          onSelectUnitId={vi.fn()}
          activeQualityFilter="ALL"
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('boundary-error-indicator')).toBeInTheDocument();
        expect(screen.getByText(/missing an authoritative geometry_status/i)).toBeInTheDocument();
      });
    } finally {
      if (originalImpl) vi.mocked(fetchUnitBoundary).mockImplementation(originalImpl);
    }
  });

  it('only enables PMTiles vector overlay when unit is verified Prayagraj', async () => {
    mockMapInstance.setLayoutProperty.mockClear();

    const { rerender } = render(
      <AtlasMap
        selectedUnit={verifiedPrayagraj}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    // For verified Prayagraj, pmtiles overlay must be set to 'visible'
    await waitFor(() => {
      expect(mockMapInstance.setLayoutProperty).toHaveBeenCalledWith(
        'pmtiles-boundary-fills',
        'visibility',
        'visible'
      );
    });

    mockMapInstance.setLayoutProperty.mockClear();

    // When switching to Varanasi, pmtiles overlay must be toggled to 'none'
    rerender(
      <AtlasMap
        selectedUnit={missingVaranasi}
        onSelectUnitId={vi.fn()}
        activeQualityFilter="ALL"
      />
    );

    await waitFor(() => {
      expect(mockMapInstance.setLayoutProperty).toHaveBeenCalledWith(
        'pmtiles-boundary-fills',
        'visibility',
        'none'
      );
    });
  });
});
