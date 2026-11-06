'use client';

import React from 'react';
import { QualityStatus } from '../lib/types';
import { ExternalLink, HelpCircle, AlertCircle } from 'lucide-react';

interface NumberCellProps {
  quantityId: string;
  definitionKey: string;
  value: number | null;
  unit: string;
  kind: string;
  qualityStatus: QualityStatus;
  qualityColor: string;
  asOf?: string | null;
  onOpenProvenance: (quantityId: string) => void;
  className?: string;
}

export const NumberCell: React.FC<NumberCellProps> = ({
  quantityId,
  definitionKey,
  value,
  unit,
  kind,
  qualityStatus,
  qualityColor,
  asOf,
  onOpenProvenance,
  className = '',
}) => {
  const isUnavailable = value === null || qualityStatus === 'UNAVAILABLE';

  // Format value with commas for readability
  const formattedValue = isUnavailable
    ? 'UNAVAILABLE'
    : value.toLocaleString(undefined, {
        maximumFractionDigits: 2,
      });

  return (
    <button
      type="button"
      onClick={() => onOpenProvenance(quantityId)}
      className={`group relative flex w-full items-center justify-between rounded-lg border border-surface-border bg-surface-panel/80 p-3 text-left transition-all hover:border-brand-sky hover:bg-surface-hover hover:shadow-glow-sky focus:outline-none focus:ring-2 focus:ring-brand-sky ${className}`}
      aria-label={`Inspect ledger provenance for ${definitionKey}: ${formattedValue} ${unit}`}
      title="Click to open epistemic ledger provenance"
    >
      <div className="space-y-1">
        {/* Metric Label and Kind Badge */}
        <div className="flex items-center space-x-2">
          <span className="font-mono text-xs font-semibold text-slate-300 group-hover:text-white transition-colors">
            {definitionKey}
          </span>
          <span className="rounded bg-slate-800 px-1.5 py-0.2 font-mono text-[9px] uppercase tracking-wider text-slate-400 border border-slate-700/50">
            {kind}
          </span>
        </div>

        {/* Formatted Value & Unit */}
        <div className="flex items-baseline space-x-1.5">
          {isUnavailable ? (
            <span className="font-mono text-base font-bold text-slate-500 tracking-tight flex items-center space-x-1">
              <AlertCircle className="h-4 w-4 text-slate-500 mr-1 inline" />
              <span>Unavailable</span>
            </span>
          ) : (
            <>
              <span className="font-mono text-xl font-bold tracking-tight text-white group-hover:text-brand-sky transition-colors">
                {formattedValue}
              </span>
              <span className="font-mono text-xs text-slate-400">{unit}</span>
            </>
          )}
        </div>

        {/* Observation Ground Truth Date */}
        {asOf && (
          <p className="font-mono text-[10px] text-slate-500">
            Observation as of: <span className="text-slate-400">{asOf}</span>
          </p>
        )}
      </div>

      {/* Right: Quality Indicator Badge & Inspect Link */}
      <div className="flex flex-col items-end space-y-1.5">
        <div className="flex items-center space-x-1.5 rounded-full border border-surface-border bg-slate-900/90 px-2 py-0.5 text-[10px] font-semibold">
          <span
            className="h-2 w-2 rounded-full shadow-sm"
            style={{ backgroundColor: qualityColor }}
          />
          <span style={{ color: qualityColor }}>{qualityStatus}</span>
        </div>

        <span className="flex items-center space-x-1 text-[10px] text-slate-500 group-hover:text-brand-sky transition-colors">
          <span>Ledger</span>
          <ExternalLink className="h-3 w-3" />
        </span>
      </div>
    </button>
  );
};
