'use client';

import React from 'react';
import { IndicatorItem, QualityStatus } from '../lib/types';
import { NumberCell } from './NumberCell';
import { Database, Inbox, Sparkles, ShieldCheck } from 'lucide-react';

interface IndicatorListProps {
  indicators: IndicatorItem[];
  isLoading: boolean;
  activeQualityFilter: QualityStatus | 'ALL';
  onOpenProvenance: (quantityId: string) => void;
  geoName: string;
}

export const IndicatorList: React.FC<IndicatorListProps> = ({
  indicators,
  isLoading,
  activeQualityFilter,
  onOpenProvenance,
  geoName,
}) => {
  // Filter indicators if a quality filter is active
  const filtered = indicators.filter((item) => {
    if (activeQualityFilter === 'ALL') return true;
    return item.quality_status === activeQualityFilter;
  });

  if (isLoading) {
    return (
      <div className="space-y-3 rounded-xl border border-surface-border bg-surface-card p-4">
        <div className="flex items-center justify-between">
          <div className="h-4 w-32 animate-pulse rounded bg-slate-800" />
          <div className="h-4 w-16 animate-pulse rounded bg-slate-800" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-lg border border-surface-border bg-surface-panel"
            />
          ))}
        </div>
      </div>
    );
  }

  if (indicators.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-border bg-surface-card/40 p-8 text-center">
        <Inbox className="h-10 w-10 text-slate-600 mb-2" />
        <h4 className="text-sm font-semibold text-slate-300">
          No Epistemic Evidence Populated
        </h4>
        <p className="mt-1 max-w-sm text-xs text-slate-500">
          Economic indicator records have not yet been ingested for{' '}
          <span className="font-semibold text-slate-400">{geoName}</span>. In accordance with
          Handbook Part 10.3, missing quantities are never presented as numeric zero.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-xl border border-surface-border bg-surface-card p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="h-4 w-4 text-brand-sky" />
          <h3 className="text-sm font-bold text-white">
            Verified Economic Indicators ({filtered.length} of {indicators.length})
          </h3>
        </div>
        <div className="flex items-center space-x-1.5 text-[11px] text-slate-400">
          <Sparkles className="h-3 w-3 text-brand-indigo" />
          <span>Click any metric to open ledger provenance</span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {filtered.map((item) => (
          <NumberCell
            key={item.id}
            quantityId={item.id}
            definitionKey={item.definition_key}
            value={item.value}
            unit={item.unit}
            kind={item.kind}
            qualityStatus={item.quality_status}
            qualityColor={item.quality_color}
            asOf={item.as_of}
            onOpenProvenance={onOpenProvenance}
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="py-6 text-center text-xs text-slate-500">
          No indicators match active quality filter{' '}
          <span className="font-mono font-bold text-slate-300">{activeQualityFilter}</span>.
        </div>
      )}
    </div>
  );
};
