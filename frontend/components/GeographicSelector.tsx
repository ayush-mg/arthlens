'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, ChevronRight, AlertTriangle, CheckCircle2, MapPin, Globe, Compass } from 'lucide-react';
import { GeoUnitSummary } from '../lib/types';
import { fetchGeoUnits } from '../lib/api';

interface GeographicSelectorProps {
  selectedUnit: GeoUnitSummary;
  onSelectUnit: (unit: GeoUnitSummary) => void;
}

export const GeographicSelector: React.FC<GeographicSelectorProps> = ({
  selectedUnit,
  onSelectUnit,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<GeoUnitSummary[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Quick preset districts from authoritative baseline
  const PRESET_DISTRICTS = [
    { id: 'in:district:120', name: 'Prayagraj', state: 'Uttar Pradesh', lgd: '120', verified: true },
    { id: 'in:district:187', name: 'Varanasi', state: 'Uttar Pradesh', lgd: '187', verified: false },
    { id: 'in:district:175', name: 'Rae Bareli', state: 'Uttar Pradesh', lgd: '175', verified: false },
    { id: 'in:district:158', name: 'Kaushambi', state: 'Uttar Pradesh', lgd: '158', verified: false },
  ];

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const results = await fetchGeoUnits({ search: searchQuery });
        setSearchResults(results);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isGeometryMissing = selectedUnit.geometry_status === 'GEOMETRY_MISSING';

  return (
    <div className="space-y-3">
      {/* Breadcrumb Navigation & Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center space-x-1 text-xs text-slate-400">
          <span className="flex items-center space-x-1 text-slate-300">
            <Globe className="h-3.5 w-3.5 text-brand-sky" />
            <span>India</span>
          </span>
          <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
          <span className="text-slate-300">Uttar Pradesh</span>
          <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
          <span className="font-semibold text-white bg-slate-800/60 px-2 py-0.5 rounded border border-surface-border">
            {selectedUnit.name}
          </span>
        </nav>

        {/* Search Input with Autocomplete Dropdown */}
        <div ref={dropdownRef} className="relative w-full sm:w-72">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              placeholder="Search 800 LGD districts..."
              className="w-full rounded-lg border border-surface-border bg-surface-card py-2 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 transition-colors focus:border-brand-sky focus:outline-none focus:ring-1 focus:ring-brand-sky"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {isOpen && (searchQuery.trim().length > 0 || searchResults.length > 0) && (
            <div className="absolute left-0 right-0 top-full z-40 mt-1 max-h-60 overflow-y-auto rounded-lg border border-surface-border bg-surface-card p-1 shadow-xl backdrop-blur-md">
              {isLoading && (
                <div className="p-3 text-center text-xs text-slate-400">Searching national hierarchy...</div>
              )}
              {!isLoading && searchResults.length === 0 && (
                <div className="p-3 text-center text-xs text-slate-500">No matching districts found.</div>
              )}
              {searchResults.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => {
                    onSelectUnit(u);
                    setIsOpen(false);
                    setSearchQuery('');
                  }}
                  className="flex w-full items-center justify-between rounded px-3 py-2 text-left text-xs text-slate-200 hover:bg-surface-hover transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <MapPin className="h-3.5 w-3.5 text-brand-sky" />
                    <span className="font-medium">{u.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] text-slate-500">LGD {u.lgd_code}</span>
                    {u.geometry_status === 'GEOMETRY_VERIFIED' ? (
                      <span className="rounded bg-brand-emerald/10 px-1.5 py-0.5 text-[9px] font-semibold text-brand-emerald">
                        Geometry
                      </span>
                    ) : (
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
                        Missing Geom
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Preset District Quick Pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mr-1">
          Baseline Units:
        </span>
        {PRESET_DISTRICTS.map((dist) => {
          const isSelected = selectedUnit.id === dist.id;
          return (
            <button
              key={dist.id}
              type="button"
              onClick={() =>
                onSelectUnit({
                  id: dist.id,
                  name: dist.name,
                  level: 2,
                  parent_id: 'in:state:09',
                  lgd_code: dist.lgd,
                  navigation_status: 'NAVIGABLE',
                  geometry_status: dist.verified ? 'GEOMETRY_VERIFIED' : 'GEOMETRY_MISSING',
                  analytical_status: dist.verified ? 'ANALYSABLE' : 'ANALYSIS_UNAVAILABLE',
                  has_geometry: dist.verified,
                })
              }
              className={`flex items-center space-x-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all ${
                isSelected
                  ? 'border border-brand-sky bg-brand-sky/15 text-white shadow-glow-sky'
                  : 'border border-surface-border bg-surface-card/60 text-slate-400 hover:border-slate-600 hover:text-slate-200'
              }`}
            >
              <span>{dist.name}</span>
              <span className="font-mono text-[10px] text-slate-500">LGD {dist.lgd}</span>
              {dist.verified && (
                <span className="h-1.5 w-1.5 rounded-full bg-brand-emerald" title="Geometry Verified" />
              )}
            </button>
          );
        })}
      </div>

      {/* Orthogonal Coverage Status Badges & Limitation Notice */}
      <div className="flex flex-wrap items-center justify-between rounded-lg border border-surface-border bg-surface-panel/40 px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Navigation Status */}
          <span className="flex items-center space-x-1 rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-300">
            <Compass className="h-3 w-3 text-brand-sky" />
            <span>NAV: {selectedUnit.navigation_status}</span>
          </span>

          {/* Geometry Status */}
          <span
            className={`flex items-center space-x-1 rounded px-2 py-0.5 font-mono text-[11px] ${
              selectedUnit.geometry_status === 'GEOMETRY_VERIFIED'
                ? 'bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/30'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
            }`}
          >
            {selectedUnit.geometry_status === 'GEOMETRY_VERIFIED' ? (
              <CheckCircle2 className="h-3 w-3" />
            ) : (
              <AlertTriangle className="h-3 w-3" />
            )}
            <span>GEOM: {selectedUnit.geometry_status}</span>
          </span>

          {/* Analytical Status */}
          <span
            className={`flex items-center space-x-1 rounded px-2 py-0.5 font-mono text-[11px] ${
              selectedUnit.analytical_status === 'ANALYSABLE'
                ? 'bg-brand-indigo/10 text-brand-indigo border border-brand-indigo/30'
                : 'bg-slate-800 text-slate-400'
            }`}
          >
            <span>ANALYSIS: {selectedUnit.analytical_status}</span>
          </span>
        </div>

        {/* LGD and Census code separation proof */}
        <div className="font-mono text-[11px] text-slate-400">
          Canonical ID: <span className="text-brand-sky">{selectedUnit.id}</span>
          {selectedUnit.census_code && (
            <span className="ml-2 text-slate-500">| Census: {selectedUnit.census_code}</span>
          )}
        </div>
      </div>

      {/* Strict Geographic Limitation Warning Banner (if GEOMETRY_MISSING) */}
      {isGeometryMissing && (
        <div className="flex items-start space-x-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold text-amber-200">
              Source-Gated Geographic Limitation
            </p>
            <p className="text-[11px] text-amber-300/90 leading-relaxed">
              District boundary geometry for <span className="font-mono font-bold">{selectedUnit.name}</span> remains{' '}
              <span className="font-mono font-bold">GEOMETRY_MISSING</span> in the verified baseline. Modern nationwide
              boundary vectors are source-gated and nationwide PMTiles are not generated. Only pilot district Prayagraj{' '}
              (LGD 120) has verified polygons. Tabular indicators remain navigable.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
