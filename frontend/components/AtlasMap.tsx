'use client';

import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { GeoUnitSummary } from '../lib/types';
import { fetchPilotBoundaries } from '../lib/api';
import { Layers, ShieldAlert, MapPinOff, ArrowRight, ExternalLink } from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';

interface AtlasMapProps {
  selectedUnit: GeoUnitSummary;
  onSelectUnitId: (geoId: string) => void;
  activeQualityFilter: string;
}

export const AtlasMap: React.FC<AtlasMapProps> = ({
  selectedUnit,
  onSelectUnitId,
  activeQualityFilter,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState<any | null>(null);
  const [pilotBoundaries, setPilotBoundaries] = useState<any>(null);
  const shouldReduceMotion = useReducedMotion();

  // Initialize MapLibre map instance with CARTO Dark Matter basemap
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const darkStyle: maplibregl.StyleSpecification = {
      version: 8,
      name: 'ArthLens Dark Intelligence',
      sources: {
        'carto-dark': {
          type: 'raster',
          tiles: [
            'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
          ],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors, © CARTO',
        },
      },
      layers: [
        {
          id: 'carto-dark-layer',
          type: 'raster',
          source: 'carto-dark',
          minzoom: 0,
          maxzoom: 19,
          paint: {
            'raster-opacity': 0.85,
          },
        },
      ],
    };

    const mapInstance = new maplibregl.Map({
      container: mapContainer.current,
      style: darkStyle,
      center: [81.8463, 25.4358], // Centered on Prayagraj pilot district
      zoom: 8.5,
      attributionControl: false, // Custom styled attribution badge below
    });

    mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');

    mapInstance.on('load', () => {
      setMapLoaded(true);
    });

    map.current = mapInstance;

    return () => {
      mapInstance.remove();
      map.current = null;
    };
  }, []);

  // Fetch verified pilot boundary data
  useEffect(() => {
    async function loadBoundaries() {
      const data = await fetchPilotBoundaries();
      setPilotBoundaries(data);
    }
    loadBoundaries();
  }, []);

  // Add / update GeoJSON layers when map and pilot boundaries are loaded
  useEffect(() => {
    if (!map.current || !mapLoaded || !pilotBoundaries) return;

    const currentMap = map.current;

    // Check if source already exists
    if (!currentMap.getSource('pilot-boundaries')) {
      currentMap.addSource('pilot-boundaries', {
        type: 'geojson',
        data: pilotBoundaries,
      });

      // 1. Fill layer with authoritative P2-3 data-driven paint expression
      currentMap.addLayer({
        id: 'pilot-boundary-fills',
        type: 'fill',
        source: 'pilot-boundaries',
        paint: {
          'fill-color': [
            'match',
            ['get', 'quality_status'],
            'CURRENT',
            '#22C55E',
            'INCOMPLETE',
            '#EAB308',
            'STALE',
            '#F97316',
            'ESTIMATED',
            '#3B82F6',
            'UNAVAILABLE',
            '#94A3B8',
            '#94A3B8', // Default fallback
          ],
          'fill-opacity': [
            'match',
            ['get', 'quality_status'],
            'CURRENT',
            0.65,
            'INCOMPLETE',
            0.6,
            'STALE',
            0.7,
            'ESTIMATED',
            0.6,
            'UNAVAILABLE',
            0.45,
            0.5,
          ],
        },
      });

      // 2. Stroke layer
      currentMap.addLayer({
        id: 'pilot-boundary-strokes',
        type: 'line',
        source: 'pilot-boundaries',
        paint: {
          'line-color': '#38BDF8',
          'line-width': 2,
          'line-opacity': 0.9,
        },
      });

      // Hover interaction
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

      // Feature click
      currentMap.on('click', 'pilot-boundary-fills', (e) => {
        if (e.features && e.features.length > 0) {
          const props = e.features[0].properties;
          if (props?.lgd_code === '120') {
            onSelectUnitId('in:district:120');
          } else if (props?.lgd_code === '890') {
            onSelectUnitId('in:subdistrict:120:890');
          }
        }
      });
    }
  }, [mapLoaded, pilotBoundaries, onSelectUnitId]);

  // Adjust camera when Prayagraj is selected
  useEffect(() => {
    if (!map.current || !mapLoaded) return;
    if (selectedUnit.id === 'in:district:120') {
      map.current.flyTo({
        center: [81.8463, 25.4358],
        zoom: 9.2,
        duration: shouldReduceMotion ? 0 : 1200,
      });
    }
  }, [selectedUnit.id, mapLoaded, shouldReduceMotion]);

  const isGeometryMissing = selectedUnit.geometry_status === 'GEOMETRY_MISSING';

  return (
    <div className="relative h-[500px] w-full overflow-hidden rounded-xl border border-surface-border bg-surface-card shadow-2xl">
      {/* MapLibre DOM Target */}
      <div ref={mapContainer} className="h-full w-full" />

      {/* Floating Map Legend & Control Overlay */}
      <div className="absolute left-4 top-4 z-10 flex items-center space-x-2 rounded-lg border border-surface-border bg-surface-base/90 p-2 shadow-lg backdrop-blur-md">
        <Layers className="h-4 w-4 text-brand-sky" />
        <span className="font-mono text-xs font-bold text-white">
          Vector Overlay: {selectedUnit.name}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
            selectedUnit.geometry_status === 'GEOMETRY_VERIFIED'
              ? 'bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/20'
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}
        >
          {selectedUnit.geometry_status}
        </span>
      </div>

      {/* Elegant Unavailable-Geometry State Card (No arbitrary or radar coordinates) */}
      {isGeometryMissing && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-slate-950/75 p-6 text-center backdrop-blur-sm">
          <motion.div
            initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="max-w-lg rounded-2xl border border-amber-500/30 bg-surface-card/95 p-6 shadow-2xl backdrop-blur-md"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-400 mb-4">
              <MapPinOff className="h-6 w-6" />
            </div>

            <span className="inline-flex items-center space-x-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-amber-300 mb-2">
              <ShieldAlert className="h-3 w-3" />
              <span>Boundary Geometry Unavailable</span>
            </span>

            <h3 className="font-mono text-base font-bold text-white">
              Administrative Polygons Source-Gated
            </h3>

            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              <strong className="text-white">{selectedUnit.name}</strong> (LGD Code {selectedUnit.lgd_code}) is registered in the verified LGD hierarchy, but official 2026 administrative boundary vectors are source-gated by the Survey of India / Ministry of Panchayati Raj.
            </p>

            <p className="mt-2 text-[11px] leading-relaxed text-slate-400 border-l-2 border-amber-500/40 pl-3 text-left">
              In strict adherence to ArthLens epistemic standards, spatial coordinates and polygons are never fabricated or approximated. Tabular economic metrics and ledger provenance remain 100% verifiable below.
            </p>

            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => onSelectUnitId('in:district:120')}
                className="inline-flex items-center space-x-2 rounded-lg border border-brand-sky/40 bg-brand-sky/15 px-3.5 py-2 font-mono text-xs font-semibold text-brand-sky hover:bg-brand-sky/25 hover:border-brand-sky transition-all"
              >
                <span>Focus Pilot Boundary (Prayagraj LGD 120)</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Hover Tooltip Card */}
      {hoveredFeature && (
        <div className="pointer-events-none absolute bottom-10 left-4 z-20 rounded-lg border border-surface-border bg-surface-card/95 p-3 shadow-xl backdrop-blur-md text-xs space-y-1">
          <div className="flex items-center justify-between space-x-4">
            <span className="font-bold text-white">
              {hoveredFeature.DISTRICT || hoveredFeature.SUBDISTRICT}
            </span>
            <span className="font-mono text-[10px] text-slate-400">
              LGD: {hoveredFeature.lgd_code}
            </span>
          </div>
          <div className="flex items-center space-x-2 text-[11px] text-slate-300">
            <span>State: {hoveredFeature.ST_NM}</span>
            <span>•</span>
            <span>Status: <strong className="text-brand-sky">{hoveredFeature.quality_status || 'VERIFIED'}</strong></span>
          </div>
        </div>
      )}

      {/* External Map Provider Attribution & Boundary Disclaimer Badge */}
      <div className="pointer-events-none absolute bottom-2 left-3 right-3 z-10 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500 font-mono">
        <span className="rounded bg-slate-950/80 px-2 py-0.5 border border-slate-800/80 backdrop-blur-sm">
          CARTO basemap for spatial orientation only. External administrative lines do not constitute verified ArthLens boundaries.
        </span>
        <span className="rounded bg-slate-950/80 px-2 py-0.5 border border-slate-800/80 backdrop-blur-sm pointer-events-auto">
          © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer" className="underline hover:text-slate-300">OpenStreetMap</a> contributors, © <a href="https://carto.com/attributions" target="_blank" rel="noreferrer" className="underline hover:text-slate-300">CARTO</a>
        </span>
      </div>
    </div>
  );
};
