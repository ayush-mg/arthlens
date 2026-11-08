'use client';

import React from 'react';
import { IndicatorItem, QualityStatus } from '../lib/types';
import { NumberCell } from './NumberCell';
import { Database, Inbox, Sparkles } from 'lucide-react';

interface IndicatorListProps {
  indicators: IndicatorItem[];
  isLoading: boolean;
  activeQualityFilter: QualityStatus | 'ALL';
  onOpenProvenance: (quantityId: string) => void;
  geoName: string;
  activeIndicatorKey?: string | null;
  onSelectIndicatorKey?: (key: string | null) => void;
}

export const IndicatorList: React.FC<IndicatorListProps> = ({
  indicators,
  isLoading,
  activeQualityFilter,
  onOpenProvenance,
  geoName,
  activeIndicatorKey,
  onSelectIndicatorKey,
}) => {
  // Filter indicators if a quality filter is active
  const filtered = indicators.filter((item) => {
    if (activeQualityFilter === 'ALL') return true;
    return item.quality_status === activeQualityFilter;
  });

  if (isLoading) {
    return (
      <div className="space-y-3 rounded border border-editorial-brass/40 bg-editorial-paper p-4 shadow-editorial">
        <div className="flex items-center justify-between">
          <div className="h-4 w-32 animate-pulse rounded bg-editorial-ivory-dark" />
          <div className="h-4 w-16 animate-pulse rounded bg-editorial-ivory-dark" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded border border-editorial-brass/20 bg-editorial-ivory"
            />
          ))}
        </div>
      </div>
    );
  }

  if (indicators.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded border border-dashed border-editorial-brass/50 bg-editorial-paper p-8 text-center shadow-editorial">
        <Inbox className="h-10 w-10 text-editorial-brass mb-2" />
        <h4 className="font-serif text-sm font-bold text-editorial-forest">
          No Epistemic Evidence Populated
        </h4>
        <p className="mt-1 max-w-sm text-xs text-editorial-charcoal-light leading-relaxed">
          Economic indicator records have not yet been ingested for{' '}
          <span className="font-semibold text-editorial-charcoal">{geoName}</span>. In accordance with
          Handbook Part 10.3, missing quantities are never presented as numeric zero.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded border border-editorial-brass/40 bg-editorial-paper p-4 shadow-editorial">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-editorial-brass/20 pb-2">
        <div className="flex items-center space-x-2">
          <Database className="h-4 w-4 text-editorial-copper shrink-0" />
          <h3 className="font-serif text-sm font-bold text-editorial-forest">
            Ledger-backed Economic Indicators ({filtered.length} of {indicators.length})
          </h3>
        </div>
        <div className="flex items-center space-x-1.5 text-[11px] text-editorial-charcoal-light font-mono">
          <Sparkles className="h-3 w-3 text-editorial-brass shrink-0" />
          <span>Click any metric to open ledger provenance</span>
        </div>
      </div>

      <div className="grid gap-3 grid-cols-1">
        {filtered.map((item) => {
          const isActive = activeIndicatorKey === item.definition_key;
          return (
            <div key={item.id || item.definition_key} className="space-y-1">
              <NumberCell
                quantityId={item.id}
                definitionKey={item.definition_key}
                value={item.value}
                unit={item.unit}
                kind={item.kind}
                qualityStatus={item.quality_status}
                qualityColor={item.quality_color}
                asOf={item.as_of}
                onOpenProvenance={onOpenProvenance}
                className={isActive ? 'ring-2 ring-editorial-forest shadow-md' : ''}
              />
              <div className="flex items-center justify-between px-1 text-[11px] font-mono">
                <button
                  type="button"
                  onClick={() => onSelectIndicatorKey?.(isActive ? null : item.definition_key)}
                  className={`inline-flex items-center space-x-1 rounded px-2 py-0.5 text-[10px] font-semibold transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-editorial-forest text-editorial-ivory'
                      : 'bg-editorial-ivory text-editorial-charcoal-light hover:text-editorial-forest border border-editorial-brass/30'
                  }`}
                >
                  <span>{isActive ? '✓ Active Atlas Layer' : 'Set as Atlas Choropleth'}</span>
                </button>
                {item.status === 'AVAILABLE' && (item as any).disputed && (
                  <span className="text-[10px] text-editorial-copper font-bold uppercase tracking-wider">
                    Disputed Evidence (V5)
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="py-6 text-center text-xs text-editorial-charcoal-light font-mono">
          No indicators match active quality filter{' '}
          <span className="font-bold text-editorial-forest">{activeQualityFilter}</span>.
        </div>
      )}
    </div>
  );
};
