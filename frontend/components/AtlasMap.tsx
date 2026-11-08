'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import * as pmtiles from 'pmtiles';
import { GeoUnitSummary, getUnitCoordinates } from '../lib/types';
import { fetchUnitBoundary, getAuthToken } from '../lib/api';
import {
  Layers,
  ShieldAlert,
  MapPinOff,
  ArrowRight,
  Maximize2,
  Minimize2,
  Compass,
  Crosshair,
  Info,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { audioEngine } from '../lib/audio';

interface AtlasMapProps {
  selectedUnit: GeoUnitSummary;
  onSelectUnitId: (geoId: string) => void;
  activeQualityFilter: string;
  activeIndicatorKey?: string | null;
  currentUser?: any;
  onOpenProvenance?: (quantityId: string) => void;
}

// API and basemap endpoints
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const DEFAULT_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_URL = process.env.NEXT_PUBLIC_MAP_TILE_URL || DEFAULT_TILE_URL;
const TILE_ATTRIBUTION =
  process.env.NEXT_PUBLIC_MAP_ATTRIBUTION ||
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors';

// Helper to detect artificial bounding boxes / axis-aligned rectangles
export function isAxisAlignedBoundingBox(geometry: any): boolean {
  if (!geometry || geometry.type !== 'Polygon' || !geometry.coordinates || !geometry.coordinates[0]) {
    return false;
  }
  const ring = geometry.coordinates[0];
  if (ring.length !== 5) return false;
  const lons = ring.map((c: any) => c[0]);
  const lats = ring.map((c: any) => c[1]);
  const uniqueLons = new Set(lons);
  const uniqueLats = new Set(lats);
  return uniqueLons.size === 2 && uniqueLats.size === 2;
}

// Helper to compute geographic bounding box of GeoJSON FeatureCollection coordinates
export function computeFeatureCollectionBounds(features: any[]): [[number, number], [number, number]] | null {
  if (!features || features.length === 0) return null;
  let minLon = 180, minLat = 90, maxLon = -180, maxLat = -90;
  let hasPoints = false;

  const processCoord = (coord: any) => {
    if (Array.isArray(coord) && typeof coord[0] === 'number' && typeof coord[1] === 'number') {
      const lon = coord[0];
      const lat = coord[1];
      if (lon >= -180 && lon <= 180 && lat >= -90 && lat <= 90) {
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
        hasPoints = true;
      }
    } else if (Array.isArray(coord)) {
      coord.forEach(processCoord);
    }
  };

  features.forEach((feat) => {
    if (feat.geometry && feat.geometry.coordinates) {
      processCoord(feat.geometry.coordinates);
    }
  });

  if (!hasPoints) return null;
  return [[minLon, minLat], [maxLon, maxLat]];
}

export const AtlasMap: React.FC<AtlasMapProps> = ({
  selectedUnit,
  onSelectUnitId,
  activeQualityFilter,
  activeIndicatorKey,
  currentUser,
  onOpenProvenance,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState<any | null>(null);
  const [unitBoundaries, setUnitBoundaries] = useState<any>(null);
  const [boundaryStatus, setBoundaryStatus] = useState<
    'idle' | 'loading' | 'verified' | 'historical' | 'simplified' | 'unvalidated' | 'missing' | 'error' | 'auth_error' | 'not_found'
  >('idle');
  const [activeBoundaryProps, setActiveBoundaryProps] = useState<any>(null);
  const [boundaryError, setBoundaryError] = useState<string | null>(null);
  const [tileError, setTileError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const shouldReduceMotion = useReducedMotion();
  const boundaryReqSeqRef = useRef<number>(0);

  const [resolutionState, setResolutionState] = useState<'LOADING' | 'RESOLVED' | 'ERROR'>('LOADING');

  // Initialize MapLibre with real geographic basemap
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Register PMTiles protocol for vector tile decoding
    if (typeof window !== 'undefined' && typeof maplibregl.addProtocol === 'function' && !(window as any)._pmtilesProtocolRegistered) {
      try {
        const protocol = new pmtiles.Protocol();
        maplibregl.addProtocol('pmtiles', protocol.tile);
        (window as any)._pmtilesProtocolRegistered = true;
      } catch (err) {
        console.warn('PMTiles protocol registration notice:', err);
      }
    }

    // Real geographic basemap style utilizing OpenStreetMap tiles with editorial palette integration
    const basemapStyle: maplibregl.StyleSpecification = {
      version: 8,
      name: 'ArthLens Geospatial Basemap',
      sources: {
        'osm-raster-tiles': {
          type: 'raster',
          tiles: [TILE_URL],
          tileSize: 256,
          attribution: TILE_ATTRIBUTION,
          maxzoom: 19,
        },
      },
      layers: [
        {
          id: 'carto-parchment-background',
          type: 'background',
          paint: {
            'background-color': '#FAF8F3', // Warm parchment ivory
          },
        },
        {
          id: 'osm-tiles-layer',
          type: 'raster',
          source: 'osm-raster-tiles',
          minzoom: 0,
          maxzoom: 19,
          paint: {
            'raster-opacity': 0.88,
            'raster-contrast': 0.08,
            'raster-saturation': -0.15, // Softens raw tile saturation to match editorial theme
          },
        },
      ],
    };

    const initialCoords = getUnitCoordinates(selectedUnit.id);
    const defaultCenter: [number, number] = [initialCoords.lon ?? 81.8463, initialCoords.lat ?? 25.4358];
    const mapInstance = new maplibregl.Map({
      container: mapContainer.current,
      style: basemapStyle,
      center: defaultCenter,
      zoom: selectedUnit.id === 'in:district:120' ? 9.2 : 9.8,
      attributionControl: false,
      transformRequest: (url: string) => {
        if (url.includes('/geo/pilot-pmtiles') || url.includes(API_BASE_URL)) {
          const token = getAuthToken();
          return {
            url,
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: 'include' as const,
          };
        }
        return { url };
      },
    });

    mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');

    if (typeof window !== 'undefined') {
      (window as any)._atlasMap = mapInstance;
    }

    const onStyleReady = () => {
      setMapLoaded(true);
      if (typeof window !== 'undefined') {
        (window as any)._atlasMapLoaded = true;
      }
    };

    const isLoaded = typeof mapInstance.isStyleLoaded === 'function' ? mapInstance.isStyleLoaded() : false;
    if (isLoaded || (mapInstance.style && (mapInstance.style as any)._loaded)) {
      onStyleReady();
    } else {
      if (typeof mapInstance.on === 'function') {
        mapInstance.on('styledata', onStyleReady);
      }
      if (typeof mapInstance.once === 'function') {
        mapInstance.once('load', onStyleReady);
      }
    }

    mapInstance.on('error', (e) => {
      if (e.error && (e.error.message?.includes('tile') || e.error.message?.includes('fetch'))) {
        setTileError('Geographic tile server notice: tile fetch failed or network offline.');
      }
    });

    map.current = mapInstance;

    return () => {
      mapInstance.remove();
      map.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch verified administrative boundary dynamically for selectedUnit
  useEffect(() => {
    let isMounted = true;
    const reqSeq = ++boundaryReqSeqRef.current;

    // 1. Immediately clear previous unit's boundary from map and state to prevent leakage
    if (map.current && mapLoaded) {
      const src = map.current.getSource('pilot-boundaries') as maplibregl.GeoJSONSource | undefined;
      if (src && typeof src.setData === 'function') {
        src.setData({ type: 'FeatureCollection', features: [] });
      }
    }
    setUnitBoundaries({ type: 'FeatureCollection', features: [] });
    setBoundaryStatus('loading');
    setResolutionState('LOADING');
    setBoundaryError(null);

    async function loadBoundaries() {
      try {
        let data: any = null;
        try {
          data = await fetchUnitBoundary(selectedUnit.id, activeIndicatorKey || undefined);
        } catch (apiErr: any) {
          if (apiErr.name === 'NotFoundError' || apiErr.status === 404) {
            if (isMounted && reqSeq === boundaryReqSeqRef.current) {
              setBoundaryStatus('not_found');
              setResolutionState('ERROR');
              setBoundaryError(`Geographic unit ${selectedUnit.id} not found in registry.`);
            }
            return;
          }
          if (apiErr.name === 'AuthenticationRequiredError' || apiErr.name === 'AuthenticationError' || apiErr.status === 401 || apiErr.status === 403) {
            if (isMounted && reqSeq === boundaryReqSeqRef.current) {
              setBoundaryStatus('auth_error');
              setResolutionState('ERROR');
              setBoundaryError('Authentication required to retrieve boundary vectors.');
            }
            return;
          }
          throw apiErr;
        }

        // 3. Cancel/ignore obsolete asynchronous requests
        if (!isMounted || reqSeq !== boundaryReqSeqRef.current) return;

        if (data && data.features && data.features.length > 0) {
          // Strictly reject and filter out any artificial axis-aligned bounding boxes
          const verifiedFeatures = data.features.filter((feat: any) => !isAxisAlignedBoundingBox(feat.geometry));
          if (verifiedFeatures.length > 0) {
            const featProps = verifiedFeatures[0].properties || {};
            const topLevelStatus = data.geometry_status;
            const featStatus = featProps.geometry_status;

            // 1. Unknown or absent statuses must result in an error state
            if (!topLevelStatus && !featStatus) {
              setUnitBoundaries({ type: 'FeatureCollection', features: [] });
              setBoundaryStatus('error');
              setResolutionState('ERROR');
              setBoundaryError(`Boundary response for ${selectedUnit.id} is missing an authoritative geometry_status.`);
              setActiveBoundaryProps(null);
              return;
            }

            // 2. Conflicting feature-level and top-level statuses must be rejected
            if (topLevelStatus && featStatus && topLevelStatus !== featStatus) {
              setUnitBoundaries({ type: 'FeatureCollection', features: [] });
              setBoundaryStatus('error');
              setResolutionState('ERROR');
              setBoundaryError(
                `Conflicting geometry status for ${selectedUnit.id}: top-level reports '${topLevelStatus}' but feature reports '${featStatus}'.`
              );
              setActiveBoundaryProps(null);
              return;
            }

            const resolvedStatus = (topLevelStatus || featStatus) as string;
            const SUPPORTED_STATUSES = ['GEOMETRY_VERIFIED', 'GEOMETRY_HISTORICAL', 'GEOMETRY_SIMPLIFIED', 'GEOMETRY_UNVALIDATED'];

            if (!SUPPORTED_STATUSES.includes(resolvedStatus)) {
              setUnitBoundaries({ type: 'FeatureCollection', features: [] });
              setBoundaryStatus('error');
              setResolutionState('ERROR');
              setBoundaryError(`Unsupported or unknown geometry status '${resolvedStatus}' for ${selectedUnit.id}.`);
              setActiveBoundaryProps(null);
              return;
            }

            const fc = { ...data, features: verifiedFeatures };
            setUnitBoundaries(fc);
            setActiveBoundaryProps(featProps);

            if (resolvedStatus === 'GEOMETRY_HISTORICAL') {
              setBoundaryStatus('historical');
            } else if (resolvedStatus === 'GEOMETRY_SIMPLIFIED') {
              setBoundaryStatus('simplified');
            } else if (resolvedStatus === 'GEOMETRY_UNVALIDATED') {
              setBoundaryStatus('unvalidated');
            } else {
              setBoundaryStatus('verified');
            }
            setResolutionState('RESOLVED');

            if (map.current && mapLoaded) {
              const src = map.current.getSource('pilot-boundaries') as maplibregl.GeoJSONSource | undefined;
              if (src && typeof src.setData === 'function') {
                src.setData(fc);
              }
            }

            // Fit verified geometry using actual bounds
            const bounds = computeFeatureCollectionBounds(verifiedFeatures);
            if (bounds && map.current && typeof map.current.fitBounds === 'function' && typeof window !== 'undefined' && !(window as any).__VITEST__) {
              map.current.fitBounds(bounds, {
                padding: { top: 60, bottom: 60, left: 60, right: 60 },
                maxZoom: 10.8,
                duration: shouldReduceMotion ? 0 : 1000,
              });
            }
            return;
          }
        }

        // Authoritative resolution check: only mark confirmed missing if status is explicitly GEOMETRY_MISSING
        const statusReported = data?.geometry_status || data?.properties?.geometry_status;
        const isExplicitlyMissing =
          statusReported === 'GEOMETRY_MISSING' || (!data?.has_geometry && statusReported === 'GEOMETRY_MISSING');

        if (isExplicitlyMissing) {
          setUnitBoundaries({ type: 'FeatureCollection', features: [] });
          setBoundaryStatus('missing');
          setResolutionState('RESOLVED');
          setActiveBoundaryProps(null);
          if (map.current && mapLoaded) {
            const src = map.current.getSource('pilot-boundaries') as maplibregl.GeoJSONSource | undefined;
            if (src && typeof src.setData === 'function') {
              src.setData({ type: 'FeatureCollection', features: [] });
            }
          }
        } else {
          // Inconsistent response: 0 features returned but backend reported non-missing status
          setUnitBoundaries({ type: 'FeatureCollection', features: [] });
          setBoundaryStatus('error');
          setResolutionState('ERROR');
          setBoundaryError(
            `Inconsistent boundary response for ${selectedUnit.id}: received 0 features with status '${statusReported || 'UNKNOWN'}' instead of GEOMETRY_MISSING.`
          );
          setActiveBoundaryProps(null);
        }
      } catch (err: any) {
        if (isMounted && reqSeq === boundaryReqSeqRef.current) {
          console.warn('Boundary load notice:', err.message);
          setBoundaryStatus('error');
          setResolutionState('ERROR');
          setBoundaryError(err.message || 'Unable to retrieve verified boundary vectors.');
          setUnitBoundaries({ type: 'FeatureCollection', features: [] });
        }
      }
    }

    loadBoundaries();

    return () => {
      isMounted = false;
    };
  }, [selectedUnit.id, selectedUnit.geometry_status, activeIndicatorKey, mapLoaded, currentUser, shouldReduceMotion]);

  // Register verified boundary vector layers on map
  useEffect(() => {
    if (!map.current || !mapLoaded) return;

    const currentMap = map.current;
    const boundaryData = unitBoundaries || { type: 'FeatureCollection', features: [] };

    // Remove existing boundary layer if already present to update cleanly
    if (currentMap.getSource('pilot-boundaries')) {
      const source = currentMap.getSource('pilot-boundaries') as maplibregl.GeoJSONSource;
      source.setData(boundaryData);
      return;
    }

    currentMap.addSource('pilot-boundaries', {
      type: 'geojson',
      data: boundaryData,
    });

    // Register verified PMTiles vector source and layers (P2-4 genuine vector tile integration)
    if (!currentMap.getSource('pilot-pmtiles-source')) {
      try {
        currentMap.addSource('pilot-pmtiles-source', {
          type: 'vector',
          url: `pmtiles://${API_BASE_URL}/geo/pilot-pmtiles`,
        });

        currentMap.addLayer({
          id: 'pmtiles-boundary-fills',
          type: 'fill',
          source: 'pilot-pmtiles-source',
          'source-layer': 'admin_boundaries',
          layout: {
            visibility: 'none',
          },
          paint: {
            'fill-color': '#203D32',
            'fill-opacity': 0.15,
          },
        });

        currentMap.addLayer({
          id: 'pmtiles-boundary-strokes',
          type: 'line',
          source: 'pilot-pmtiles-source',
          'source-layer': 'admin_boundaries',
          layout: {
            visibility: 'none',
          },
          paint: {
            'line-color': '#203D32',
            'line-width': 2.0,
            'line-opacity': 0.9,
          },
        });
      } catch (pmtilesErr) {
        console.warn('PMTiles vector source setup notice:', pmtilesErr);
      }
    }

    // 1. Verified boundary fill layer (rendered over basemap with editorial transparency)
    currentMap.addLayer({
      id: 'pilot-boundary-fills',
      type: 'fill',
      source: 'pilot-boundaries',
      paint: {
        'fill-color': [
          'match',
          ['get', 'quality_status'],
          'CURRENT',
          '#203D32',
          'INCOMPLETE',
          '#B49A65',
          'STALE',
          '#B76E4D',
          'ESTIMATED',
          '#455A64',
          'CONTRADICTED',
          '#DC2626',
          'UNAVAILABLE',
          '#A9B5A2',
          '#203D32',
        ],
        'fill-opacity': 0.22,
      },
    });

    // 2. Verified boundary stroke outline (crisp editorial boundary)
    currentMap.addLayer({
      id: 'pilot-boundary-strokes',
      type: 'line',
      source: 'pilot-boundaries',
      paint: {
        'line-color': '#203D32', // Deep editorial forest boundary
        'line-width': 2.5,
        'line-opacity': 0.95,
      },
    });

    // Interactivity: Cursor & Tooltip
    currentMap.on('mousemove', 'pilot-boundary-fills', (e) => {
      if (e.features && e.features.length > 0) {
        const feat = e.features[0];
        setHoveredFeature(feat.properties);
        currentMap.getCanvas().style.cursor = 'pointer';
      }
    });

    currentMap.on('mouseleave', 'pilot-boundary-fills', () => {
      setHoveredFeature(null);
      currentMap.getCanvas().style.cursor = '';
    });

    // Map-click handler: Selects clicked boundary unit ID or LGD code (never hardcoded to 120)
    currentMap.on('click', 'pilot-boundary-fills', (e) => {
      if (e.features && e.features.length > 0) {
        const props = e.features[0].properties;
        audioEngine.playClick(950);
        if (props?.geo_id) {
          onSelectUnitId(props.geo_id);
        } else if (props?.id) {
          onSelectUnitId(props.id);
        } else if (props?.lgd_code) {
          onSelectUnitId(`in:district:${props.lgd_code}`);
        }
      }
    });
  }, [mapLoaded, unitBoundaries, onSelectUnitId]);

  // Synchronize boundary layers with selected unit geometry status and active quality filter
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const currentMap = map.current;

    const layersToUpdate = [
      'pilot-boundary-fills',
      'pilot-boundary-strokes',
      'pmtiles-boundary-fills',
      'pmtiles-boundary-strokes',
    ];

    const hasVerifiedGeometry =
      (selectedUnit.geometry_status === 'GEOMETRY_VERIFIED' || boundaryStatus === 'verified') &&
      boundaryStatus !== 'missing' &&
      boundaryStatus !== 'not_found';
    const targetLgdCode = selectedUnit.lgd_code;

    layersToUpdate.forEach((layerId) => {
      if (!currentMap.getLayer(layerId)) return;

      if (!hasVerifiedGeometry) {
        // District has no verified geometry: strictly filter out all boundary polygons
        currentMap.setFilter(layerId, ['==', ['get', 'lgd_code'], '__NONE__']);
        return;
      }

      // District has verified geometry: match target lgd_code
      if (layerId === 'pilot-boundary-fills' && activeQualityFilter !== 'ALL') {
        currentMap.setFilter(layerId, [
          'all',
          ['==', ['get', 'lgd_code'], targetLgdCode],
          ['==', ['get', 'quality_status'], activeQualityFilter],
        ]);
        currentMap.setPaintProperty(layerId, 'fill-opacity', 0.45);
      } else {
        currentMap.setFilter(layerId, ['==', ['get', 'lgd_code'], targetLgdCode]);
        if (layerId === 'pilot-boundary-fills') {
          currentMap.setPaintProperty(layerId, 'fill-opacity', activeIndicatorKey ? 0.32 : 0.15);
        }
      }

      // FIX 3: Do not show a quality choropleth when no indicator is selected
      if (layerId === 'pilot-boundary-fills') {
        if (!activeIndicatorKey) {
          currentMap.setPaintProperty(layerId, 'fill-color', '#203D32');
        } else {
          currentMap.setPaintProperty(layerId, 'fill-color', [
            'match',
            ['get', 'quality_status'],
            'CURRENT', '#203D32',
            'INCOMPLETE', '#B49A65',
            'STALE', '#B76E4D',
            'ESTIMATED', '#455A64',
            'CONTRADICTED', '#DC2626',
            'UNAVAILABLE', '#A9B5A2',
            '#203D32',
          ]);
        }
      }
    });
  }, [selectedUnit.id, selectedUnit.lgd_code, selectedUnit.geometry_status, boundaryStatus, activeQualityFilter, activeIndicatorKey, mapLoaded]);

  // Control PMTiles pilot vector overlay visibility
  // Must only be visible when the selected unit's authoritative API response confirms verified geometry
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const currentMap = map.current;
    const isPmtilesActive = boundaryStatus === 'verified' && selectedUnit.id === 'in:district:120';
    const visibility = isPmtilesActive ? 'visible' : 'none';

    try {
      if (currentMap.getLayer('pmtiles-boundary-fills')) {
        currentMap.setLayoutProperty('pmtiles-boundary-fills', 'visibility', visibility);
      }
      if (currentMap.getLayer('pmtiles-boundary-strokes')) {
        currentMap.setLayoutProperty('pmtiles-boundary-strokes', 'visibility', visibility);
      }
    } catch {
      // Ignore in mock/non-WebGL environments
    }
  }, [boundaryStatus, selectedUnit.id, mapLoaded]);

  // Camera fitBounds / flyTo on geographic unit selection
  // Uses genuine selected-unit geometry bounds; retains sensible viewport when geometry is unavailable
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    const currentMap = map.current;

    const coords = getUnitCoordinates(selectedUnit.id);
    if (coords.lat !== null && coords.lon !== null) {
      if (typeof currentMap.flyTo === 'function') {
        currentMap.flyTo({
          center: [coords.lon, coords.lat],
          zoom: boundaryStatus === 'verified' || selectedUnit.geometry_status === 'GEOMETRY_VERIFIED' ? 9.2 : 9.8,
          duration: shouldReduceMotion ? 0 : 1000,
        });
      }

      // If unit has boundary features, fit using actual computed geometry bounds (not hardcoded rectangle)
      if (unitBoundaries && unitBoundaries.features && unitBoundaries.features.length > 0) {
        const bounds = computeFeatureCollectionBounds(unitBoundaries.features);
        if (bounds && typeof currentMap.fitBounds === 'function' && typeof window !== 'undefined' && !(window as any).__VITEST__) {
          currentMap.fitBounds(bounds, {
            padding: { top: 60, bottom: 60, left: 60, right: 60 },
            maxZoom: 10.8,
            duration: shouldReduceMotion ? 0 : 1000,
          });
        }
      }
    }
  }, [selectedUnit.id, selectedUnit.geometry_status, boundaryStatus, unitBoundaries, mapLoaded, shouldReduceMotion]);

  // Reset view to Prayagraj pilot
  const handleResetPilotFocus = useCallback(() => {
    audioEngine.playClick(900);
    onSelectUnitId('in:district:120');
  }, [onSelectUnitId]);

  // Only show confirmed missing geometry after successful authoritative resolution
  const isConfirmedGeometryMissing =
    resolutionState === 'RESOLVED' &&
    boundaryStatus === 'missing' &&
    selectedUnit.geometry_status !== 'GEOMETRY_VERIFIED';

  const unitCoords = getUnitCoordinates(selectedUnit.id);

  return (
    <div
      className={`relative w-full overflow-hidden rounded border border-editorial-brass/40 bg-editorial-ivory shadow-editorial transition-all duration-500 ${
        isExpanded ? 'h-[750px]' : 'h-[520px]'
      }`}
    >
      {/* Tactical HUD Corner Reticles */}
      <div className="pointer-events-none absolute inset-2.5 z-10">
        <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-editorial-brass/60" />
        <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-editorial-brass/60" />
        <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-editorial-brass/60" />
        <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-editorial-brass/60" />
      </div>

      {/* MapLibre DOM Target (Hosts real geographic raster basemap) */}
      <div ref={mapContainer} className="h-full w-full relative z-1" />

      {/* Floating Tactical Masthead Badge */}
      <div className="absolute left-4 top-4 z-10 flex flex-wrap items-center gap-2 rounded border border-editorial-brass/40 bg-editorial-paper/95 p-2 shadow-editorial backdrop-blur-md">
        <div className="flex items-center space-x-2">
          <Crosshair className="h-4 w-4 text-editorial-copper" />
          <span className="font-mono text-xs font-bold text-editorial-forest tracking-wide">
            Vector Overlay: {selectedUnit.name}
          </span>
        </div>

        <span
          className={`rounded px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider ${
            selectedUnit.geometry_status === 'GEOMETRY_VERIFIED'
              ? 'bg-editorial-forest/15 text-editorial-forest border border-editorial-forest/30'
              : selectedUnit.geometry_status === 'GEOMETRY_HISTORICAL'
              ? 'bg-amber-600/15 text-amber-800 border border-amber-600/30'
              : selectedUnit.geometry_status === 'GEOMETRY_SIMPLIFIED'
              ? 'bg-blue-600/15 text-blue-800 border border-blue-600/30'
              : 'bg-editorial-copper/15 text-editorial-copper border border-editorial-copper/30'
          }`}
        >
          GEOM: {selectedUnit.geometry_status}
        </span>

        {resolutionState === 'LOADING' && (
          <span
            data-testid="boundary-resolution-badge"
            className="rounded px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider bg-editorial-brass/20 text-editorial-forest border border-editorial-brass/40"
          >
            RESOLVING...
          </span>
        )}

        {/* Visibly label coordinate semantics */}
        <span className="hidden sm:inline-block text-[10px] font-mono text-editorial-charcoal-light border-l border-editorial-brass/30 pl-2">
          {unitCoords.formatted} • {unitCoords.semantics === 'GEOMETRY_DERIVED_CENTROID' ? 'Polygon Centroid' : unitCoords.semantics === 'APPROXIMATE_ORIENTATION' ? 'Approx. Orientation Point (Not Boundary)' : unitCoords.semantics}
        </span>
      </div>

      {/* Map Control Tools (Expand / Collapse) */}
      <div className="absolute right-14 top-4 z-10 flex items-center space-x-1.5">
        <button
          type="button"
          onClick={() => {
            audioEngine.playClick(1050);
            setIsExpanded(!isExpanded);
          }}
          title={isExpanded ? 'Collapse Map' : 'Expand Map'}
          className="p-2 rounded border border-editorial-brass/40 bg-editorial-paper hover:bg-editorial-ivory text-editorial-charcoal transition-colors backdrop-blur-md shadow-sm cursor-pointer"
        >
          {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      </div>

      {/* Tile Error / Provider Warning Notice */}
      {tileError && (
        <div className="absolute top-16 left-4 z-10 flex items-center space-x-2 rounded border border-editorial-copper/50 bg-editorial-paper/95 px-3 py-1 text-[11px] font-mono text-editorial-copper shadow-sm backdrop-blur-md">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>{tileError}</span>
        </div>
      )}

      {/* Historical Boundary Vintage Indicator */}
      {boundaryStatus === 'historical' && (
        <div
          data-testid="historical-geometry-indicator"
          className="pointer-events-auto absolute bottom-8 left-4 z-10 flex items-center space-x-2.5 rounded border border-amber-600/40 bg-editorial-paper/95 px-3 py-1.5 text-xs font-mono text-editorial-charcoal shadow-editorial backdrop-blur-md"
        >
          <div className="flex h-5 w-5 items-center justify-center rounded bg-amber-600/15 text-amber-700 shrink-0">
            <Info className="h-3.5 w-3.5" />
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="font-semibold text-editorial-forest">{selectedUnit.name}</span>
            <span className="text-amber-700 font-medium">(LGD {selectedUnit.lgd_code}): Historical boundary vintage</span>
          </div>
        </div>
      )}

      {/* Simplified Boundary Indicator */}
      {boundaryStatus === 'simplified' && (
        <div
          data-testid="simplified-geometry-indicator"
          className="pointer-events-auto absolute bottom-8 left-4 z-10 flex items-center space-x-2.5 rounded border border-blue-600/40 bg-editorial-paper/95 px-3 py-1.5 text-xs font-mono text-editorial-charcoal shadow-editorial backdrop-blur-md"
        >
          <div className="flex h-5 w-5 items-center justify-center rounded bg-blue-600/15 text-blue-700 shrink-0">
            <Info className="h-3.5 w-3.5" />
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="font-semibold text-editorial-forest">{selectedUnit.name}</span>
            <span className="text-blue-700 font-medium">(LGD {selectedUnit.lgd_code}): Simplified geometry representation</span>
          </div>
        </div>
      )}

      {/* Boundary Load / Access Error Indicator */}
      {resolutionState === 'ERROR' && boundaryError && (
        <div
          data-testid="boundary-error-indicator"
          className="pointer-events-auto absolute bottom-8 left-4 z-10 flex items-center space-x-2.5 rounded border border-editorial-copper/50 bg-editorial-paper/95 px-3 py-1.5 text-xs font-mono text-editorial-copper shadow-editorial backdrop-blur-md"
        >
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>{boundaryError}</span>
        </div>
      )}

      {/* Compact Unobtrusive Status Indicator: ONLY shown when resolutionState === RESOLVED and confirmed missing */}
      {isConfirmedGeometryMissing && (
        <div
          data-testid="missing-geometry-indicator"
          className="pointer-events-auto absolute bottom-8 left-4 z-10 flex items-center space-x-2.5 rounded border border-editorial-brass/50 bg-editorial-paper/95 px-3 py-1.5 text-xs font-mono text-editorial-charcoal shadow-editorial backdrop-blur-md"
        >
          <div className="flex h-5 w-5 items-center justify-center rounded bg-editorial-copper/15 text-editorial-copper shrink-0">
            <MapPinOff className="h-3.5 w-3.5" />
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="font-semibold text-editorial-forest">{selectedUnit.name}</span>
            <span className="text-editorial-copper font-medium">(LGD {selectedUnit.lgd_code}): Boundary unmapped</span>
          </div>
          <span className="text-editorial-brass/60">•</span>
          <button
            type="button"
            onClick={() => onOpenProvenance?.(`missing-geom:${selectedUnit.id}`)}
            className="text-editorial-copper hover:text-editorial-copper-dark underline font-bold transition-colors cursor-pointer"
          >
            Provenance Details
          </button>
        </div>
      )}

      {/* Hover Tooltip Card for Boundary Features */}
      {hoveredFeature && (
        <div className="pointer-events-none absolute bottom-12 left-4 z-20 rounded border border-editorial-brass/40 bg-editorial-paper p-3 shadow-editorial-lg text-xs space-y-1">
          <div className="flex items-center justify-between space-x-4">
            <span className="font-bold text-editorial-forest font-serif">
              {hoveredFeature.DISTRICT || hoveredFeature.name}
            </span>
            <span className="font-mono text-[10px] text-editorial-brass">
              LGD: {hoveredFeature.lgd_code}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-[11px] text-editorial-charcoal">
            <span>State: {hoveredFeature.ST_NM || 'Uttar Pradesh'}</span>
            <span>•</span>
            <span>Status: <strong className="text-editorial-forest font-mono">{hoveredFeature.geometry_status || 'UNKNOWN'}</strong></span>
          </div>
        </div>
      )}

      {/* Authoritative Basemap Attribution & Disclaimer Bar */}
      <div className="pointer-events-none absolute bottom-2 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-2 text-[10px] text-editorial-charcoal-light font-mono">
        <span className="rounded bg-editorial-paper/90 px-2 py-0.5 border border-editorial-brass/30 backdrop-blur-sm">
          Geographic basemap: OpenStreetMap roads, settlements & hydrology. External boundary lines do not constitute verified ArthLens boundaries.
        </span>
        <span className="rounded bg-editorial-paper/90 px-2 py-0.5 border border-editorial-brass/30 backdrop-blur-sm pointer-events-auto">
          © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" className="underline hover:text-editorial-forest">OpenStreetMap</a> contributors
        </span>
      </div>
    </div>
  );
};
