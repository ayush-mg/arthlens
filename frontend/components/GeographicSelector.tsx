'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, ChevronRight, AlertTriangle, CheckCircle2, MapPin, Globe, Compass, RotateCcw } from 'lucide-react';
import { GeoUnitSummary } from '../lib/types';
import { fetchGeoUnits, fetchGeoUnitDetail } from '../lib/api';
import { audioEngine } from '../lib/audio';

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
  const [searchError, setSearchError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [isSelectingPreset, setIsSelectingPreset] = useState<string | null>(null);
  const [presetError, setPresetError] = useState<string | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Quick preset baseline districts from nationwide database
  const PRESET_DISTRICTS = [
    { id: 'in:district:120', name: 'Prayagraj', lgd: '120' },
    { id: 'in:district:187', name: 'Varanasi', lgd: '187' },
    { id: 'in:district:396', name: 'Bhopal', lgd: '396' },
    { id: 'in:district:102', name: 'Jaipur', lgd: '102' },
    { id: 'in:district:156', name: 'Kanpur Dehat', lgd: '156' },
  ];

  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setSearchError(null);
      setActiveIndex(-1);
      return;
    }
    setIsLoading(true);
    setSearchError(null);
    try {
      const results = await fetchGeoUnits({ search: query });
      setSearchResults(results);
      setActiveIndex(-1);
    } catch (err: any) {
      console.error('Search error:', err);
      setSearchError(err.message || 'Failed to query 800 baseline records.');
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(searchQuery);
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery, performSearch]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setActiveIndex(-1);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard navigation for dropdown
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || searchResults.length === 0) {
      if (e.key === 'ArrowDown' && searchResults.length > 0) {
        setIsOpen(true);
        setActiveIndex(0);
        e.preventDefault();
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => (prev < searchResults.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : searchResults.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < searchResults.length) {
        handleSelectUnit(searchResults[activeIndex]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
      setActiveIndex(-1);
    }
  };

  const handleSelectUnit = (u: GeoUnitSummary) => {
    if (u.id === 'in:district:120') {
      audioEngine.playSonar();
    } else {
      audioEngine.playClick(920);
    }
    onSelectUnit(u);
    setIsOpen(false);
    setSearchQuery('');
    setActiveIndex(-1);
  };

  // Authoritative preset selection: Fetches genuine backend record without inventing statuses
  const handleSelectPreset = async (presetId: string) => {
    setIsSelectingPreset(presetId);
    setPresetError(null);
    try {
      const detail = await fetchGeoUnitDetail(presetId);
      if (presetId === 'in:district:120') {
        audioEngine.playSonar();
      } else {
        audioEngine.playClick(940);
      }
      onSelectUnit(detail);
    } catch (err: any) {
      console.error('Failed to fetch authoritative preset detail:', err);
      // Fail closed: never fabricate synthetic parent_id or manufactured statuses
      setPresetError(
        err.message ||
          `Unable to load authoritative record for ${
            PRESET_DISTRICTS.find((d) => d.id === presetId)?.name || presetId
          }. Please retry.`
      );
    } finally {
      setIsSelectingPreset(null);
    }
  };

  const isGeometryMissing = selectedUnit.geometry_status === 'GEOMETRY_MISSING';

  // Dynamic state resolution from parent_name or hierarchy
  const resolvedStateName =
    selectedUnit.level === 1
      ? null
      : selectedUnit.parent_name
      ? selectedUnit.parent_name
      : selectedUnit.parent_id
      ? `State (${selectedUnit.parent_id})`
      : 'Unresolved Parent State';

  return (
    <div className="space-y-3">
      {/* Editorial Cartographic Breadcrumb & Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Dynamic Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center space-x-1.5 text-xs text-editorial-charcoal-light">
          <span className="flex items-center space-x-1 text-editorial-forest font-semibold">
            <Globe className="h-3.5 w-3.5 text-editorial-copper" />
            <span>India</span>
          </span>
          {resolvedStateName && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-editorial-brass" />
              <span className="text-editorial-charcoal font-medium">{resolvedStateName}</span>
            </>
          )}
          <ChevronRight className="h-3.5 w-3.5 text-editorial-brass" />
          <span className="font-serif font-bold text-editorial-forest bg-editorial-ivory-dark/70 px-2 py-0.5 rounded border border-editorial-brass/40">
            {selectedUnit.name}
          </span>
        </nav>

        {/* Search Input with Autocomplete Dropdown */}
        <div ref={dropdownRef} className="relative w-full sm:w-80">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-editorial-brass" />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              onKeyDown={handleKeyDown}
              placeholder="Search 800 baseline districts (e.g. Bhopal, Jaipur)..."
              className="w-full rounded border border-editorial-brass/40 bg-editorial-paper py-2 pl-9 pr-4 text-xs font-mono text-editorial-charcoal placeholder-editorial-charcoal-light/60 transition-colors focus:border-editorial-copper focus:outline-none focus:ring-1 focus:ring-editorial-copper"
              aria-expanded={isOpen}
              aria-controls="district-search-results"
              aria-autocomplete="list"
              role="combobox"
            />
          </div>

          {/* Autocomplete Dropdown */}
          {isOpen && (searchQuery.trim().length > 0 || searchResults.length > 0 || searchError) && (
            <div
              id="district-search-results"
              role="listbox"
              className="absolute left-0 right-0 top-full z-40 mt-1 max-h-64 overflow-y-auto rounded border border-editorial-brass/50 bg-editorial-paper p-1 shadow-editorial-lg backdrop-blur-md"
            >
              {isLoading && (
                <div className="p-3 text-center text-xs font-mono text-editorial-charcoal-light flex items-center justify-center space-x-2">
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border border-editorial-forest border-t-transparent" />
                  <span>Querying 800 baseline administrative records...</span>
                </div>
              )}

              {searchError && !isLoading && (
                <div className="p-3 text-center text-xs font-mono space-y-2">
                  <div className="text-editorial-copper flex items-center justify-center space-x-1">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>{searchError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => performSearch(searchQuery)}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded border border-editorial-brass/40 bg-editorial-ivory text-[10px] text-editorial-charcoal hover:bg-editorial-paper cursor-pointer font-mono"
                  >
                    <RotateCcw className="h-3 w-3" />
                    <span>Retry Search</span>
                  </button>
                </div>
              )}

              {!isLoading && !searchError && searchResults.length === 0 && searchQuery.trim().length > 0 && (
                <div className="p-3 text-center text-xs font-mono text-editorial-charcoal-light">
                  No matching administrative units found.
                </div>
              )}

              {searchResults.map((u, idx) => {
                const parentState = u.parent_name || (u.parent_id ? u.parent_id : '');
                const isItemActive = idx === activeIndex;
                return (
                  <button
                    key={u.id}
                    type="button"
                    role="option"
                    aria-selected={isItemActive}
                    onClick={() => handleSelectUnit(u)}
                    onMouseEnter={() => setActiveIndex(idx)}
                    className={`flex w-full items-center justify-between rounded px-3 py-2 text-left text-xs transition-colors cursor-pointer ${
                      isItemActive
                        ? 'bg-editorial-forest text-editorial-ivory'
                        : 'text-editorial-charcoal hover:bg-editorial-ivory'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <MapPin className={`h-3.5 w-3.5 ${isItemActive ? 'text-editorial-brass-light' : 'text-editorial-copper'}`} />
                      <div>
                        <span className="font-semibold">{u.name}</span>
                        {parentState && (
                          <span className={`ml-1.5 text-[10px] ${isItemActive ? 'text-editorial-sage-light' : 'text-editorial-charcoal-light'}`}>
                            ({parentState})
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`font-mono text-[10px] ${isItemActive ? 'text-editorial-brass-light' : 'text-editorial-brass'}`}>
                        LGD {u.lgd_code}
                      </span>
                      {u.geometry_status === 'GEOMETRY_VERIFIED' ? (
                        <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-bold border ${
                          isItemActive
                            ? 'bg-editorial-ivory/20 text-editorial-ivory border-editorial-ivory/40'
                            : 'bg-editorial-forest/15 text-editorial-forest border-editorial-forest/30'
                        }`}>
                          Geometry
                        </span>
                      ) : (
                        <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono ${
                          isItemActive
                            ? 'bg-editorial-ivory/10 text-editorial-sage-light'
                            : 'bg-editorial-charcoal-light/10 text-editorial-charcoal-light'
                        }`}>
                          Missing Geom
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Preset District Selection Error */}
      {presetError && (
        <div className="flex items-center justify-between rounded border border-editorial-copper/40 bg-editorial-copper/10 px-3 py-2 text-xs font-mono text-editorial-copper">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{presetError}</span>
          </div>
          <button
            type="button"
            onClick={() => setPresetError(null)}
            className="text-[10px] underline hover:text-editorial-copper-dark ml-3 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Preset District Quick Pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] font-mono uppercase tracking-wider text-editorial-charcoal-light mr-1">
          Baseline Units:
        </span>
        {PRESET_DISTRICTS.map((dist) => {
          const isSelected = selectedUnit.id === dist.id;
          const isLoadingThis = isSelectingPreset === dist.id;
          return (
            <button
              key={dist.id}
              type="button"
              disabled={isLoadingThis}
              onClick={() => handleSelectPreset(dist.id)}
              className={`flex items-center space-x-1.5 rounded px-3 py-1 text-xs font-mono transition-all cursor-pointer ${
                isSelected
                  ? 'border border-editorial-copper bg-editorial-copper text-editorial-ivory font-bold shadow-sm'
                  : 'border border-editorial-brass/40 bg-editorial-paper text-editorial-charcoal hover:border-editorial-brass hover:bg-editorial-ivory'
              }`}
            >
              <span>{dist.name}</span>
              <span className="font-mono text-[10px] opacity-80">LGD {dist.lgd}</span>
              {dist.id === 'in:district:120' && (
                <span className="h-1.5 w-1.5 rounded-full bg-editorial-forest" title="Verified Boundary Vector" />
              )}
              {isLoadingThis && (
                <div className="h-2 w-2 animate-spin rounded-full border border-current border-t-transparent" />
              )}
            </button>
          );
        })}
      </div>

      {/* Orthogonal Coverage Status Badges & Limitation Notice */}
      <div className="flex flex-wrap items-center justify-between rounded border border-editorial-brass/30 bg-editorial-paper px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Navigation Status */}
          <span className="flex items-center space-x-1 rounded bg-editorial-ivory px-2 py-0.5 font-mono text-[11px] text-editorial-charcoal border border-editorial-brass/30">
            <Compass className="h-3 w-3 text-editorial-copper" />
            <span>NAV: {selectedUnit.navigation_status}</span>
          </span>

          {/* Geometry Status */}
          <span
            className={`flex items-center space-x-1 rounded px-2 py-0.5 font-mono text-[11px] ${
              selectedUnit.geometry_status === 'GEOMETRY_VERIFIED'
                ? 'bg-editorial-forest/15 text-editorial-forest border border-editorial-forest/40'
                : selectedUnit.geometry_status === 'GEOMETRY_HISTORICAL'
                ? 'bg-amber-600/15 text-amber-800 border border-amber-600/40'
                : selectedUnit.geometry_status === 'GEOMETRY_SIMPLIFIED'
                ? 'bg-blue-600/15 text-blue-800 border border-blue-600/40'
                : selectedUnit.geometry_status === 'GEOMETRY_UNVALIDATED'
                ? 'bg-slate-600/15 text-slate-800 border border-slate-600/40'
                : 'bg-editorial-copper/15 text-editorial-copper border border-editorial-copper/40'
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
                ? 'bg-editorial-forest/15 text-editorial-forest border border-editorial-forest/40'
                : 'bg-editorial-ivory text-editorial-charcoal-light border border-editorial-brass/30'
            }`}
          >
            <span>ANALYSIS: {selectedUnit.analytical_status}</span>
          </span>
        </div>

        {/* LGD and Census code separation proof */}
        <div className="font-mono text-[11px] text-editorial-charcoal-light">
          Canonical ID: <span className="text-editorial-forest font-semibold">{selectedUnit.id}</span>
          <span className="ml-2 text-editorial-charcoal-light/80">| LGD {selectedUnit.lgd_code}{selectedUnit.census_code ? ` • Census ${selectedUnit.census_code}` : ''}</span>
        </div>
      </div>
    </div>
  );
};
