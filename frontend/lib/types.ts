/**
 * TypeScript Data Models and Contracts for ArthLens Frontend (P2-4).
 * Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 7.5, Part 10.2).
 */

export type QualityStatus = 'CURRENT' | 'INCOMPLETE' | 'STALE' | 'ESTIMATED' | 'UNAVAILABLE';

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

export interface IndicatorItem {
  id: string;
  definition_key: string;
  value: number | null;
  unit: string;
  kind: string;
  evidence_floor: number;
  resolution: number;
  as_of: string | null;
  quality_flags: string[];
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
  source_refs: string[];
  source_name?: string | null;
  source_version?: string | null;
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

export type ResolutionTier = 0 | 1 | 2 | 3; // Nation, State, District, Subdistrict

export interface GeoUnitSummary {
  id: string;
  name: string;
  level: number;
  parent_id: string | null;
  lgd_code: string;
  census_code?: string | null;
  navigation_status: 'NAVIGABLE' | 'NON_NAVIGABLE';
  geometry_status: 'GEOMETRY_VERIFIED' | 'GEOMETRY_MISSING';
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
