'use client';

import React from 'react';
import { QualityStatus } from '../lib/types';
import { Info } from 'lucide-react';
import { audioEngine } from '../lib/audio';

interface QualityLegendProps {
  activeFilter: QualityStatus | 'ALL';
  onFilterChange: (status: QualityStatus | 'ALL') => void;
}

export interface QualityStateInfo {
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
  {
    status: 'CONTRADICTED',
    label: 'Contradicted',
    color: '#DC2626',
    pattern: 'Cross Hatch',
    epistemicBasis: 'Multiple official sources disagree beyond tolerance on definition, geography or period.',
    handbookCitation: 'Part 4.5 Spec V5 (ContradictionVisibilitySpec)',
  },
];

export const QualityLegend: React.FC<QualityLegendProps> = ({
  activeFilter,
  onFilterChange,
}) => {
  return (
    <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-3 shadow-editorial">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center space-x-1.5">
          <Info className="h-4 w-4 text-editorial-copper" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-editorial-forest font-serif">
            Atlas Quality Shading Overlay
          </h3>
        </div>
        <span className="font-mono text-[10px] text-editorial-charcoal-light hidden sm:inline">
          Handbook Part 7.5 Precedence: UNAVAILABLE &gt; CONTRADICTED &gt; INCOMPLETE &gt; STALE &gt; ESTIMATED &gt; CURRENT
        </span>
      </div>

      {/* State Filter Buttons */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-7">
        <button
          type="button"
          onClick={() => {
            audioEngine.playClick(850);
            onFilterChange('ALL');
          }}
          className={`flex items-center justify-center rounded border px-2.5 py-1.5 text-xs font-mono font-medium transition-all cursor-pointer ${
            activeFilter === 'ALL'
              ? 'border-editorial-forest bg-editorial-forest text-editorial-ivory shadow-sm'
              : 'border-editorial-brass/30 bg-editorial-ivory text-editorial-charcoal hover:bg-editorial-paper'
          }`}
        >
          <span>All Indicators</span>
        </button>

        {QUALITY_STATES.map((item, idx) => {
          const isActive = activeFilter === item.status;
          return (
            <button
              key={item.status}
              type="button"
              onClick={() => {
                audioEngine.playClick(900 + idx * 80);
                onFilterChange(item.status);
              }}
              className={`flex items-center space-x-2 rounded border px-2 py-1.5 text-xs font-mono transition-all cursor-pointer ${
                isActive
                  ? 'border-editorial-copper bg-editorial-copper/15 font-bold shadow-sm'
                  : 'border-editorial-brass/30 bg-editorial-ivory text-editorial-charcoal hover:bg-editorial-paper'
              }`}
            >
              <span
                className="h-2 w-2 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: item.color }}
              />
              <span className="truncate">{item.status}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
