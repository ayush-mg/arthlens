'use client';

import React from 'react';
import { QualityStatus } from '../lib/types';
import { ExternalLink, AlertCircle } from 'lucide-react';
import { audioEngine } from '../lib/audio';

interface NumberCellProps {
  quantityId: string | null;
  definitionKey: string;
  value: number | null;
  unit: string;
  kind?: string | null;
  qualityStatus: QualityStatus;
  qualityColor: string;
  asOf?: string | null;
  onOpenProvenance?: (quantityId: string) => void;
  className?: string;
  explanation?: string;
}

export const NumberCell: React.FC<NumberCellProps> = ({
  quantityId,
  definitionKey,
  value,
  unit,
  kind = 'OBSERVED',
  qualityStatus,
  qualityColor,
  asOf,
  onOpenProvenance,
  className = '',
  explanation,
}) => {
  const isUnavailable = value === null || qualityStatus === 'UNAVAILABLE' || !quantityId;

  // Format value with Indian locale (lakhs/crores) for Indian micro-enterprises
  const formattedValue = isUnavailable
    ? 'UNAVAILABLE'
    : value.toLocaleString('en-IN', {
        maximumFractionDigits: 2,
      });

  return (
    <button
      type="button"
      data-reticle="lock"
      onMouseEnter={() => audioEngine.playTick()}
      onClick={() => {
        audioEngine.playClick(1000);
        if (quantityId && onOpenProvenance) {
          onOpenProvenance(quantityId);
        }
      }}
      className={`group relative flex w-full flex-col justify-between rounded border border-editorial-brass/40 bg-editorial-paper p-3.5 text-left transition-all hover:border-editorial-copper hover:bg-editorial-ivory focus:outline-none focus:ring-1 focus:ring-editorial-copper ${quantityId ? 'cursor-pointer' : 'cursor-default'} shadow-sm min-w-0 ${className}`}
      aria-label={`Inspect ledger provenance for ${definitionKey}: ${formattedValue} ${unit}`}
      title={quantityId ? "Click to open epistemic ledger provenance" : "Data gap: no ledger quantity registered"}
    >
      {/* Top Row: Metric Label, Kind Badge, and Quality Status Badge */}
      <div className="flex w-full items-center justify-between gap-2 border-b border-editorial-brass/20 pb-2">
        <div className="flex items-center space-x-1.5 min-w-0 flex-1">
          <span className="font-mono text-xs font-semibold text-editorial-charcoal group-hover:text-editorial-forest transition-colors truncate">
            {definitionKey}
          </span>
          {kind && (
            <span className="shrink-0 rounded bg-editorial-ivory px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-editorial-charcoal-light border border-editorial-brass/30">
              {kind}
            </span>
          )}
        </div>

        {/* Quality Indicator Badge */}
        <div className="shrink-0 flex items-center space-x-1.5 rounded-full border border-editorial-brass/30 bg-editorial-ivory px-2 py-0.5 text-[10px] font-semibold">
          <span
            className="h-2 w-2 rounded-full shadow-sm shrink-0"
            style={{ backgroundColor: qualityColor }}
          />
          <span style={{ color: qualityColor }}>{qualityStatus}</span>
        </div>
      </div>

      {/* Middle Row: Unobstructed Full-Width Value & Unit */}
      <div className="my-2.5 flex items-baseline space-x-2 min-w-0">
        {isUnavailable ? (
          <span className="font-mono text-base font-bold text-editorial-charcoal-light/70 tracking-tight flex items-center space-x-1">
            <AlertCircle className="h-4 w-4 text-editorial-copper mr-1 inline shrink-0" />
            <span>Unavailable</span>
          </span>
        ) : (
          <div className="flex flex-wrap items-baseline gap-x-2 min-w-0">
            <span className="font-mono text-xl sm:text-2xl font-bold tracking-tight text-editorial-charcoal group-hover:text-editorial-copper transition-colors break-all">
              {formattedValue}
            </span>
            <span className="font-mono text-xs text-editorial-charcoal-light shrink-0">{unit}</span>
          </div>
        )}
      </div>

      {/* Bottom Row: Ground Truth Date and Ledger Link */}
      <div className="flex w-full items-center justify-between pt-1 text-[10px] font-mono border-t border-editorial-brass/10">
        <div>
          {asOf ? (
            <p className="text-editorial-charcoal-light">
              Observation: <span className="text-editorial-charcoal font-medium">{asOf}</span>
            </p>
          ) : isUnavailable ? (
            <span className="text-editorial-charcoal-light/60">Data gap: uningested metric</span>
          ) : (
            <span className="text-editorial-charcoal-light/60">Ledger registered</span>
          )}
        </div>

        {quantityId ? (
          <span className="flex items-center space-x-1 text-editorial-charcoal-light group-hover:text-editorial-copper transition-colors">
            <span>Ledger</span>
            <ExternalLink className="h-3 w-3 shrink-0" />
          </span>
        ) : (
          <span className="text-editorial-charcoal-light/50 italic">Uningested</span>
        )}
      </div>
    </button>
  );
};
