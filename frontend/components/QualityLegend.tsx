'use client';

import React from 'react';
import { QualityStatus } from '../lib/types';
import { Info, HelpCircle } from 'lucide-react';

interface QualityLegendProps {
  activeFilter: QualityStatus | 'ALL';
  onFilterChange: (status: QualityStatus | 'ALL') => void;
}

interface QualityStateInfo {
  status: QualityStatus;
  label: string;
  color: string;
  pattern: string;
  epistemicBasis: string;
  handbookCitation: string;
}

export const QUALITY_STATES: QualityStateInfo[] = [
  {
    status: 'CURRENT',
    label: 'Current Data',
    color: '#22C55E',
    pattern: 'Solid Fill',
    epistemicBasis: 'Kind.OBSERVED within approved max age threshold (fresh & complete).',
    handbookCitation: 'Part 7.5 Step 10 & Part 10.2',
  },
  {
    status: 'INCOMPLETE',
    label: 'Incomplete Coverage',
    color: '#EAB308',
    pattern: 'Dashed Outline',
    epistemicBasis: 'Attributes present but missing sub-units or partial spatial dimensions.',
    handbookCitation: 'Part 7.4 & Step 10',
  },
  {
    status: 'STALE',
    label: 'Stale Observation',
    color: '#F97316',
    pattern: 'Hatched Fill',
    epistemicBasis: 'Authentic empirical observation exceeding 10-year / source threshold.',
    handbookCitation: 'Part 7.4 (10-year rule)',
  },
  {
    status: 'ESTIMATED',
    label: 'Estimated / Modelled',
    color: '#3B82F6',
    pattern: 'Dotted Fill',
    epistemicBasis: 'Modelled projection or downscaled value (Kind.ESTIMATED; floor <= 2).',
    handbookCitation: 'Part 4.2 & Step 10',
  },
  {
    status: 'UNAVAILABLE',
    label: 'Data Unavailable',
    color: '#94A3B8',
    pattern: 'Diagonal Cross',
    epistemicBasis: 'No observation exists for geographic unit. Never substituted with 0.',
    handbookCitation: 'Part 7.5 & 10.3 (No silent zeroes)',
  },
];

export const QualityLegend: React.FC<QualityLegendProps> = ({
  activeFilter,
  onFilterChange,
}) => {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card p-3 shadow-lg">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center space-x-1.5">
          <Info className="h-4 w-4 text-brand-sky" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Atlas Quality Shading Overlay
          </h3>
        </div>
        <span className="font-mono text-[10px] text-slate-500">
          Handbook Part 7.5 Step 10 Precedence: UNAVAILABLE &gt; INCOMPLETE &gt; STALE &gt; ESTIMATED &gt; CURRENT
        </span>
      </div>

      {/* State Filter Buttons */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
        <button
          type="button"
          onClick={() => onFilterChange('ALL')}
          className={`flex items-center justify-center rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all ${
            activeFilter === 'ALL'
              ? 'border-brand-sky bg-brand-sky/15 text-white shadow-glow-sky'
              : 'border-surface-border bg-surface-panel/60 text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>All Indicators</span>
        </button>

        {QUALITY_STATES.map((item) => {
          const isActive = activeFilter === item.status;
          return (
            <button
              key={item.status}
              type="button"
              onClick={() => onFilterChange(isActive ? 'ALL' : item.status)}
              className={`group flex items-center space-x-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition-all ${
                isActive
                  ? 'border-white/40 bg-surface-panel text-white shadow-md'
                  : 'border-surface-border bg-surface-panel/50 text-slate-300 hover:border-slate-600 hover:bg-surface-panel'
              }`}
              title={`${item.status}: ${item.epistemicBasis}`}
            >
              <span
                className="h-3 w-3 shrink-0 rounded-sm border border-black/40 shadow-sm"
                style={{ backgroundColor: item.color }}
              />
              <div className="min-w-0 flex-1 truncate">
                <span className="font-semibold block truncate">{item.status}</span>
                <span className="text-[10px] text-slate-400 block truncate">{item.label}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
