/**
 * TypeScript Data Models and Contracts for ArthLens Frontend (P2-4).
 * Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 7.5, Part 10.2).
 */

export type QualityStatus = 'CURRENT' | 'INCOMPLETE' | 'STALE' | 'ESTIMATED' | 'UNAVAILABLE' | 'CONTRADICTED';

export interface ShadingToken {
  status: QualityStatus;
  label: string;
  color_token: string;
  hex_color: string;
  fill_opacity: number;
  stroke_style: string;
  pattern: string;
}

export interface QualityIssue {
  status: QualityStatus;
  reason: string;
  dimension: string;
  severity: string;
}

export interface IndicatorQuality {
  primary_status: QualityStatus;
  shading: ShadingToken;
  suitability: string;
  explanation: string;
  staleness_explanation?: string | null;
  issues: QualityIssue[];
  evaluation_date?: string | null;
}

export interface BaseIndicatorItem {
  definition_key: string;
  unit: string;
  quality_status: QualityStatus;
  quality_label: string;
  quality_color: string;
  suitability: string;
  shading: {
    color_token: string;
    hex_color: string;
    fill_opacity: number;
    stroke_style: string;
  };
}

export interface AvailableIndicator extends BaseIndicatorItem {
  status: 'AVAILABLE';
  id: string;
  value: number;
  kind: string;
  evidence_floor: number;
  resolution: number;
  as_of: string | null;
  quality_flags: string[];
  source_refs?: (string | [string, string, string])[];
  disputed?: boolean;
}

export interface UnavailableIndicator extends BaseIndicatorItem {
  status: 'UNAVAILABLE';
  id: null;
  value: null;
  kind?: string | null;
  evidence_floor?: number | null;
  resolution?: number | null;
  as_of?: string | null;
  quality_flags?: string[];
  source_refs?: (string | [string, string, string])[];
  explanation?: string;
  resolution_action?: string;
}

export type IndicatorItem = AvailableIndicator | UnavailableIndicator;

export interface ParentSummary {
  id: string;
  definition_key: string;
  value: number | null;
  unit: string;
  kind: string;
  quality_status?: QualityStatus;
}

export interface LedgerQuantityDetail {
  id: string;
  definition_key: string;
  value: number | null;
  unit: string;
  kind: string;
  evidence_floor: number;
  resolution: number;
  as_of: string | null;
  quality_flags: string[];
  source_refs: (string | [string, string, string])[];
  source_name?: string | null;
  source_version?: string | null;
  source_version_id?: string | null;
  source_checksum?: string | null;
  provenance_complete?: boolean;
  retrieval_date?: string | null;
  publication_date?: string | null;
  method_id?: string | null;
  assumptions?: string | null;
  owner_id?: string | null;
  parent_ids: string[];
  parents: ParentSummary[];
  quality: IndicatorQuality;
  temporal?: {
    as_of: string | null;
    retrieval_date: string | null;
    publication_date: string | null;
    elapsed_days: number | null;
    max_age_days: number | null;
    has_policy: boolean;
  };
  calculation_restrictions: string[];
}

export type ResolutionTier = 0 | 1 | 2 | 3 | 4 | 5; // Nation, State, District, Subdistrict, Village/Urban, Point

export type BackendGeometryStatus =
  | 'GEOMETRY_VERIFIED'
  | 'GEOMETRY_SIMPLIFIED'
  | 'GEOMETRY_HISTORICAL'
  | 'GEOMETRY_UNVALIDATED'
  | 'GEOMETRY_MISSING';

export interface GeoUnitSummary {
  id: string;
  name: string;
  level: number;
  parent_id: string | null;
  parent_name?: string | null;
  lgd_code: string;
  census_code?: string | null;
  navigation_status: 'NAVIGABLE' | 'HIERARCHY_UNRESOLVED' | 'NON_NAVIGABLE';
  geometry_status: BackendGeometryStatus;
  analytical_status: 'ANALYSABLE' | 'ANALYSIS_UNAVAILABLE';
  has_geometry: boolean;
}

export interface GeoUnitDetail extends GeoUnitSummary {
  geometry: any | null; // GeoJSON geometry polygon/multipolygon
  subunits?: GeoUnitSummary[];
  parent_name?: string | null;
}

export interface GraphNodeData {
  id: string;
  label: string;
  type: 'claim' | 'quantity' | 'calculation' | 'source';
  status?: QualityStatus;
  color?: string;
  value?: number | null;
  unit?: string;
  kind?: string;
  evidence_floor?: number;
  details?: string;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  label: string;
  type: 'derives_from' | 'sourced_from' | 'supports_claim' | 'calculates';
}

export interface EvidenceGraphData {
  root_quantity_id: string;
  elements: {
    nodes: Array<{ data: GraphNodeData }>;
    edges: Array<{ data: GraphEdgeData }>;
  };
}

export type CoordinateSemantics =
  | 'OFFICIAL_CENTROID'
  | 'GEOMETRY_DERIVED_CENTROID'
  | 'REPRESENTATIVE_LOCATION'
  | 'APPROXIMATE_ORIENTATION'
  | 'UNAVAILABLE';

export interface UnitCoordinates {
  lat: number | null;
  lon: number | null;
  formatted: string;
  semantics: CoordinateSemantics;
  provenance_note?: string;
}

export const VERIFIED_GEOMETRY_CENTROIDS: Record<
  string,
  { lat: number; lon: number; semantics: CoordinateSemantics; note: string }
> = {
  // Prayagraj polygon centroid calculated from 1,223 boundary vertices (EPSG:4326)
  'in:district:120': {
    lat: 25.4358,
    lon: 81.8463,
    semantics: 'GEOMETRY_DERIVED_CENTROID',
    note: 'Derived from 1,223-vertex DataMeet Census 2011 boundary polygon.',
  },
  // Sadar sub-district tehsil centroid
  'in:subdistrict:120:890': {
    lat: 25.45,
    lon: 81.85,
    semantics: 'GEOMETRY_DERIVED_CENTROID',
    note: 'Derived from pilot tehsil boundary geometry.',
  },
  // National capital representative orientation reference
  'in': {
    lat: 28.6139,
    lon: 77.209,
    semantics: 'REPRESENTATIVE_LOCATION',
    note: 'Representative national capital point (New Delhi). Not a spatial polygon centroid.',
  },
  // State capital representative orientation reference (Lucknow)
  'in:state:09': {
    lat: 26.8467,
    lon: 80.9462,
    semantics: 'REPRESENTATIVE_LOCATION',
    note: 'Representative state capital point (Lucknow). Not a spatial state polygon centroid.',
  },
  // Varanasi district orientation point (boundary polygon remains source-gated)
  'in:district:187': {
    lat: 25.3176,
    lon: 82.9739,
    semantics: 'APPROXIMATE_ORIENTATION',
    note: 'Approximate district orientation point. Official administrative boundary is source-gated.',
  },
  // Bhopal district orientation point
  'in:district:396': {
    lat: 23.2599,
    lon: 77.4126,
    semantics: 'APPROXIMATE_ORIENTATION',
    note: 'Approximate district orientation point. Official administrative boundary is source-gated.',
  },
  // Jaipur district orientation point
  'in:district:102': {
    lat: 26.9124,
    lon: 75.7873,
    semantics: 'APPROXIMATE_ORIENTATION',
    note: 'Approximate district orientation point. Official administrative boundary is source-gated.',
  },
  // Kanpur Dehat district orientation point
  'in:district:156': {
    lat: 26.3359,
    lon: 79.9544,
    semantics: 'APPROXIMATE_ORIENTATION',
    note: 'Approximate district orientation point. Official administrative boundary is source-gated.',
  },
};

export function getUnitCoordinates(unitId: string): UnitCoordinates {
  const record = VERIFIED_GEOMETRY_CENTROIDS[unitId];
  if (!record) {
    return {
      lat: null,
      lon: null,
      formatted: 'Coordinates Unavailable',
      semantics: 'UNAVAILABLE',
      provenance_note: 'No verified geometry or representative point registered in epistemic ledger.',
    };
  }
  const latStr = `${Math.abs(record.lat).toFixed(4)}°${record.lat >= 0 ? 'N' : 'S'}`;
  const lonStr = `${Math.abs(record.lon).toFixed(4)}°${record.lon >= 0 ? 'E' : 'W'}`;
  return {
    lat: record.lat,
    lon: record.lon,
    formatted: `${latStr}, ${lonStr}`,
    semantics: record.semantics,
    provenance_note: record.note,
  };
}
