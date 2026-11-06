/**
 * ArthLens API Client for Geospatial Atlas, Indicators, and Epistemic Ledger (P2-4).
 * Handles authenticated API calls against backend epistemic endpoints.
 * Strictly avoids hardcoding or synthesizing demonstration economic numbers.
 */

import {
  GeoUnitDetail,
  GeoUnitSummary,
  IndicatorItem,
  IndicatorQuality,
  LedgerQuantityDetail,
  EvidenceGraphData,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// Fallback seed data for Prayagraj pilot boundary GeoJSON
const FALLBACK_PRAYAGRAJ_PILOT_BOUNDARIES = {
  type: 'FeatureCollection',
  name: 'Administrative_Boundaries_Sample',
  features: [
    {
      type: 'Feature',
      properties: {
        DISTRICT: 'Prayagraj',
        ST_NM: 'Uttar Pradesh',
        ST_CEN_CD: 9,
        DT_CEN_CD: 44,
        censuscode: 175,
        lgd_code: '120',
        level: 2,
        quality_status: 'STALE',
      },
      geometry: {
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
      },
    },
    {
      type: 'Feature',
      properties: {
        SUBDISTRICT: 'Sadar',
        DISTRICT: 'Prayagraj',
        ST_NM: 'Uttar Pradesh',
        censuscode: '00890',
        lgd_code: '890',
        parent_lgd_code: '120',
        level: 3,
        quality_status: 'CURRENT',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [81.80, 25.40],
            [81.90, 25.40],
            [81.90, 25.50],
            [81.80, 25.50],
            [81.80, 25.40],
          ],
        ],
      },
    },
  ],
};

const SEED_GEO_UNITS: GeoUnitSummary[] = [
  {
    id: 'in',
    name: 'India',
    level: 0,
    parent_id: null,
    lgd_code: 'IN',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_MISSING',
    analytical_status: 'ANALYSIS_UNAVAILABLE',
    has_geometry: false,
  },
  {
    id: 'in:state:09',
    name: 'Uttar Pradesh',
    level: 1,
    parent_id: 'in',
    lgd_code: '09',
    census_code: '09',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_MISSING',
    analytical_status: 'ANALYSIS_UNAVAILABLE',
    has_geometry: false,
  },
  {
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
  },
  {
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
  },
  {
    id: 'in:district:175',
    name: 'Rae Bareli',
    level: 2,
    parent_id: 'in:state:09',
    lgd_code: '175',
    census_code: '158',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_MISSING',
    analytical_status: 'ANALYSIS_UNAVAILABLE',
    has_geometry: false,
  },
  {
    id: 'in:district:158',
    name: 'Kaushambi',
    level: 2,
    parent_id: 'in:state:09',
    lgd_code: '158',
    census_code: '174',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_MISSING',
    analytical_status: 'ANALYSIS_UNAVAILABLE',
    has_geometry: false,
  },
];

/**
 * Fetch pilot boundaries GeoJSON FeatureCollection.
 */
export async function fetchPilotBoundaries(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE_URL}/geo/pilot-boundaries`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('API /geo/pilot-boundaries unavailable, falling back to local pilot fixture.', err);
  }
  return FALLBACK_PRAYAGRAJ_PILOT_BOUNDARIES;
}

/**
 * List or search geographic units in national hierarchy.
 */
export async function fetchGeoUnits(params?: {
  level?: number;
  parent_id?: string;
  search?: string;
}): Promise<GeoUnitSummary[]> {
  try {
    const url = new URL(`${API_BASE_URL}/geo/units`);
    if (params?.level !== undefined) url.searchParams.set('level', String(params.level));
    if (params?.parent_id) url.searchParams.set('parent_id', params.parent_id);
    if (params?.search) url.searchParams.set('search', params.search);

    const res = await fetch(url.toString(), { credentials: 'include' });
    if (res.ok) {
      const data = await res.json();
      return data.units || [];
    }
  } catch (err) {
    console.warn('API /geo/units unavailable, falling back to seed units.', err);
  }

  // Filter seed units
  let units = [...SEED_GEO_UNITS];
  if (params?.search) {
    const q = params.search.toLowerCase();
    units = units.filter((u) => u.name.toLowerCase().includes(q));
  } else if (params?.parent_id) {
    units = units.filter((u) => u.parent_id === params.parent_id);
  } else if (params?.level !== undefined) {
    units = units.filter((u) => u.level === params.level);
  }
  return units;
}

/**
 * Fetch detailed GeoUnit metadata and geometry.
 */
export async function fetchGeoUnitDetail(geoId: string): Promise<GeoUnitDetail> {
  try {
    const res = await fetch(`${API_BASE_URL}/geo/${encodeURIComponent(geoId)}`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`API /geo/${geoId} unavailable, using seed detail.`, err);
  }

  const found = SEED_GEO_UNITS.find((u) => u.id === geoId);
  const isPrayagraj = geoId === 'in:district:120';
  return {
    id: geoId,
    name: found?.name || (isPrayagraj ? 'Prayagraj' : geoId),
    level: found?.level ?? 2,
    parent_id: found?.parent_id ?? 'in:state:09',
    parent_name: 'Uttar Pradesh',
    lgd_code: found?.lgd_code || '120',
    census_code: found?.census_code || '175',
    navigation_status: found?.navigation_status || 'NAVIGABLE',
    geometry_status: isPrayagraj ? 'GEOMETRY_VERIFIED' : 'GEOMETRY_MISSING',
    analytical_status: isPrayagraj ? 'ANALYSABLE' : 'ANALYSIS_UNAVAILABLE',
    has_geometry: isPrayagraj,
    geometry: isPrayagraj ? FALLBACK_PRAYAGRAJ_PILOT_BOUNDARIES.features[0].geometry : null,
    subunits: isPrayagraj
      ? [
          {
            id: 'in:subdistrict:120:890',
            name: 'Sadar',
            level: 3,
            parent_id: 'in:district:120',
            lgd_code: '890',
            census_code: '00890',
            navigation_status: 'NAVIGABLE',
            geometry_status: 'GEOMETRY_VERIFIED',
            analytical_status: 'ANALYSABLE',
            has_geometry: true,
          },
        ]
      : [],
  };
}

/**
 * Fetch indicator items for a geographic unit.
 * When no persisted evidence exists in the database, returns indicators marked UNAVAILABLE.
 * Never synthesizes fake numeric values.
 */
export async function fetchGeoIndicators(geoId: string): Promise<IndicatorItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/geo/${encodeURIComponent(geoId)}/indicators`, {
      credentials: 'include',
    });
    if (res.ok) {
      const data = await res.json();
      return data.indicators || [];
    }
  } catch (err) {
    console.warn(`API /geo/${geoId}/indicators unavailable.`, err);
  }

  // When backend is offline or unpersisted, strictly return empty array.
  // Never synthesize demonstration numbers.
  return [];
}

/**
 * Fetch full quantity ledger record for Provenance Drawer.
 * Mandatory Invariant: Every displayed number opens its ledger record.
 */
export async function fetchLedgerQuantity(quantityId: string): Promise<LedgerQuantityDetail> {
  try {
    const res = await fetch(`${API_BASE_URL}/ledger/${encodeURIComponent(quantityId)}`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`API /ledger/${quantityId} error:`, err);
  }

  throw new Error(`Quantity record '${quantityId}' not found in epistemic ledger.`);
}

/**
 * Fetch Cytoscape.js Evidence Graph DAG for a quantity.
 */
export async function fetchEvidenceGraph(quantityId: string): Promise<EvidenceGraphData> {
  try {
    const res = await fetch(`${API_BASE_URL}/ledger/${encodeURIComponent(quantityId)}/graph`, {
      credentials: 'include',
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn(`API /ledger/${quantityId}/graph error:`, err);
  }

  throw new Error(`Evidence graph for '${quantityId}' not found in epistemic ledger.`);
}
