'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  X,
  ShieldAlert,
  ArrowRight,
  Calendar,
  Network,
  AlertCircle,
  GitCommit,
  CheckCircle2,
  Copy,
  Check,
} from 'lucide-react';
import { LedgerQuantityDetail } from '../lib/types';
import { audioEngine } from '../lib/audio';

interface ProvenanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  quantity: LedgerQuantityDetail | null;
  isLoading: boolean;
  error?: string | null;
  onNavigateQuantity?: (quantityId: string) => void;
  onViewInGraph?: (quantityId: string) => void;
}

export const ProvenanceDrawer: React.FC<ProvenanceDrawerProps> = ({
  isOpen,
  onClose,
  quantity,
  isLoading,
  error,
  onNavigateQuantity,
  onViewInGraph,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [copiedChecksum, setCopiedChecksum] = useState(false);

  useEffect(() => {
    if (isOpen) {
      audioEngine.playChime();
    }
  }, [isOpen]);

  const handleCopyChecksum = () => {
    if (quantity?.source_checksum && typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(quantity.source_checksum);
      setCopiedChecksum(true);
      audioEngine.playTick();
      setTimeout(() => setCopiedChecksum(false), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-editorial-charcoal/60 backdrop-blur-sm transition-opacity"
        />

        {/* Slide-over panel */}
        <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
          <motion.div
            initial={shouldReduceMotion ? { opacity: 0 } : { x: '100%' }}
            animate={shouldReduceMotion ? { opacity: 1 } : { x: 0 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="w-screen max-w-md border-l border-editorial-brass/40 bg-editorial-paper p-6 shadow-editorial-lg overflow-y-auto"
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-editorial-brass/30 pb-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="rounded bg-editorial-forest/15 px-2 py-0.5 font-mono text-[10px] font-semibold text-editorial-forest border border-editorial-forest/30 uppercase tracking-wider">
                    Epistemic Ledger Record
                  </span>
                  <span className="font-mono text-xs text-editorial-charcoal-light">
                    {quantity?.evidence_floor ? `Floor ${quantity.evidence_floor}` : '-'}
                  </span>
                </div>
                <h2 className="font-serif text-lg font-bold text-editorial-forest break-words">
                  {quantity?.definition_key || (isLoading ? 'Querying Ledger...' : 'Record Query')}
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded p-1 text-editorial-charcoal-light hover:bg-editorial-ivory hover:text-editorial-charcoal transition-colors cursor-pointer"
                aria-label="Close provenance drawer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {isLoading && (
              <div className="py-16 text-center text-xs font-mono text-editorial-charcoal-light">
                <div className="mx-auto h-7 w-7 animate-spin rounded-full border-2 border-editorial-forest border-t-transparent mb-3" />
                Retrieving verifiable record from Epistemic Ledger...
              </div>
            )}

            {error && !isLoading && (
              <div className="py-14 text-center text-xs">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded border border-editorial-copper/40 bg-editorial-copper/10 text-editorial-copper mb-4">
                  <AlertCircle className="h-6 w-6" />
                </div>
                <h3 className="font-serif text-base font-bold text-editorial-forest mb-2">
                  Ledger Record Unavailable
                </h3>
                <p className="max-w-xs mx-auto text-editorial-charcoal leading-relaxed mb-4">
                  {error}
                </p>
                <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 text-[11px] text-editorial-charcoal-light leading-relaxed text-left">
                  <strong className="text-editorial-charcoal">Epistemic Guard Invariant:</strong> To prevent misleading or hallucinated context, invalid or missing quantity references strictly fail closed and never display an unrelated or cached record.
                </div>
              </div>
            )}

            {quantity && !isLoading && !error && (
              <div className="mt-5 space-y-6">
                {/* 1. Value & Quality Token */}
                <div className="rounded border border-editorial-brass/40 bg-editorial-ivory p-4 shadow-sm">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <span className="font-mono text-2xl font-bold text-editorial-charcoal">
                        {quantity.value === null
                          ? 'UNAVAILABLE'
                          : quantity.value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </span>
                      <span className="ml-2 font-mono text-sm text-editorial-charcoal-light">{quantity.unit}</span>
                    </div>

                    <div
                      className="flex items-center space-x-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider font-mono"
                      style={{
                        backgroundColor: `${quantity.quality.shading.hex_color}20`,
                        color: quantity.quality.shading.hex_color,
                        border: `1px solid ${quantity.quality.shading.hex_color}40`,
                      }}
                    >
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ backgroundColor: quantity.quality.shading.hex_color }}
                      />
                      <span>{quantity.quality.primary_status}</span>
                    </div>
                  </div>

                  {/* Quality Explanation */}
                  <p className="mt-3 text-xs leading-relaxed text-editorial-charcoal-light">
                    {quantity.quality.explanation}
                  </p>
                </div>

                {/* 2. Calculation Restrictions & Warnings (if any) */}
                {quantity.calculation_restrictions.length > 0 && (
                  <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3.5 space-y-1.5 text-xs">
                    <div className="flex items-center space-x-2 text-editorial-copper-dark font-semibold">
                      <ShieldAlert className="h-4 w-4 text-editorial-copper" />
                      <span>Gated Calculation Restrictions</span>
                    </div>
                    <ul className="list-disc pl-5 text-[11px] text-editorial-charcoal space-y-1">
                      {quantity.calculation_restrictions.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 3. Epistemic Metadata Matrix */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-editorial-charcoal-light font-mono">
                    Epistemic Attributes
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2.5">
                      <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                        Provenance Kind
                      </span>
                      <span className="font-mono font-semibold text-editorial-charcoal">
                        {quantity.kind}
                      </span>
                    </div>

                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2.5">
                      <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                        Evidence Floor
                      </span>
                      <span className="font-mono font-semibold text-editorial-charcoal">
                        {quantity.evidence_floor ? `Floor ${quantity.evidence_floor}` : 'Unspecified'}
                      </span>
                    </div>

                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2.5">
                      <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                        Spatial Resolution
                      </span>
                      <span className="font-mono font-semibold text-editorial-charcoal">
                        Tier {quantity.resolution}
                      </span>
                    </div>

                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2.5">
                      <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                        Suitability Verdict
                      </span>
                      <span className="font-mono font-semibold text-editorial-forest text-[11px] truncate block">
                        {quantity.quality.suitability}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Evidence Floor Monotonicity Ladder — 4 Canonical Floors per Handbook Part 4.2 */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-editorial-charcoal-light font-mono">
                      Floor Monotonicity Ladder (Floors 1–4)
                    </h4>
                    <span className="inline-flex items-center space-x-1 font-mono text-[10px] text-editorial-forest font-bold">
                      <CheckCircle2 className="h-3 w-3" />
                      <span>Invariant Validated</span>
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5 text-center font-mono text-[9px]">
                    {[
                      { floor: 4, label: 'Observed', sub: 'Statutory/Census' },
                      { floor: 3, label: 'User/Assumed', sub: 'Vetted Input' },
                      { floor: 2, label: 'Calibrated', sub: 'Model/Downscale' },
                      { floor: 1, label: 'Scenario', sub: 'Hypothetical' },
                    ].map(({ floor, label, sub }) => {
                      const isCurrent = quantity.evidence_floor === floor;
                      const isBelow = quantity.evidence_floor < floor;
                      return (
                        <div
                          key={floor}
                          className={`rounded border p-1.5 transition-all ${
                            isCurrent
                              ? 'border-editorial-forest bg-editorial-forest text-editorial-ivory font-bold shadow-sm'
                              : isBelow
                              ? 'border-editorial-brass/20 bg-editorial-ivory/50 text-editorial-charcoal-light/50'
                              : 'border-editorial-brass/40 bg-editorial-paper text-editorial-charcoal'
                          }`}
                        >
                          <div className="font-bold">Floor {floor}</div>
                          <div className="text-[8.5px] font-semibold truncate">{label}</div>
                          <div className="text-[7.5px] text-editorial-charcoal-light truncate">{sub}</div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-editorial-charcoal-light">
                    <span>Part 4.2 Invariant: Derived floor ({quantity.evidence_floor}) = min(parents).</span>
                    <span className="text-[9px] text-editorial-copper">UNAVAILABLE is a QualityStatus token</span>
                  </div>
                </div>

                {/* 4. Temporal Breakdown */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-editorial-charcoal-light font-mono">
                    Temporal Ground Truth & Freshness
                  </h4>
                  <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-editorial-charcoal-light flex items-center space-x-1">
                        <Calendar className="h-3.5 w-3.5 text-editorial-copper" />
                        <span>Observation Date (as_of):</span>
                      </span>
                      <span className="font-mono font-semibold text-editorial-charcoal">
                        {quantity.as_of || 'Unspecified'}
                      </span>
                    </div>

                    {quantity.temporal && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-editorial-charcoal-light">Elapsed Age:</span>
                          <span className="font-mono text-editorial-charcoal">
                            {quantity.temporal.elapsed_days !== null
                              ? `${quantity.temporal.elapsed_days} days`
                              : 'Uncalculated'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-editorial-charcoal-light">Max Allowed Age:</span>
                          <span className="font-mono text-editorial-charcoal">
                            {quantity.temporal.max_age_days !== null
                              ? `${quantity.temporal.max_age_days} days`
                              : 'None (Unconfigured)'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-editorial-charcoal-light">Retrieval Date:</span>
                          <span className="font-mono text-editorial-charcoal-light">
                            {quantity.temporal.retrieval_date || 'N/A'}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* 5. Source Citations & Method */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-editorial-charcoal-light font-mono">
                    Source Register & Methodology
                  </h4>
                  <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-2 text-xs">
                    {quantity.source_name && (
                      <div>
                        <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                          Source Registry Authority
                        </span>
                        <span className="font-mono font-semibold text-editorial-forest text-[11px] block">
                          {quantity.source_name}
                        </span>
                      </div>
                    )}

                    {quantity.source_version_id && (
                      <div>
                        <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                          Exact Source Version ID (Verified)
                        </span>
                        <span className="font-mono text-xs text-editorial-charcoal break-all block">
                          {quantity.source_version_id}
                        </span>
                      </div>
                    )}

                    {quantity.provenance_complete === false && (
                      <div className="rounded border border-editorial-copper/30 bg-editorial-copper/10 p-2 text-[10px] font-mono text-editorial-copper-dark">
                        ⚠ Incomplete exact provenance: referenced source version not registered or verified.
                      </div>
                    )}

                    <div>
                      <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                        Source Reference
                      </span>
                      <span className="font-mono font-semibold text-editorial-charcoal break-all">
                        {quantity.source_refs.join(', ') || 'Internal Epistemic Model'}
                      </span>
                    </div>

                    {quantity.source_checksum && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                            Source SHA-256 Checksum (Immutable)
                          </span>
                          <button
                            type="button"
                            onClick={handleCopyChecksum}
                            className="inline-flex items-center space-x-1 text-[10px] font-mono text-editorial-copper hover:text-editorial-copper-dark cursor-pointer transition-colors"
                            title="Copy SHA-256 hash"
                          >
                            {copiedChecksum ? (
                              <>
                                <Check className="h-3 w-3 text-editorial-forest" />
                                <span className="text-editorial-forest font-bold">Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                        </div>
                        <div className="mt-0.5 flex items-center space-x-1.5 rounded bg-editorial-paper border border-editorial-brass/40 px-2 py-1 font-mono text-[10px] text-editorial-forest break-all">
                          <GitCommit className="h-3 w-3 shrink-0 text-editorial-copper" />
                          <span className="select-all">{quantity.source_checksum}</span>
                        </div>
                      </div>
                    )}

                    {quantity.method_id && (
                      <div>
                        <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                          Derivation Method ID
                        </span>
                        <span className="font-mono text-editorial-charcoal">{quantity.method_id}</span>
                      </div>
                    )}

                    {quantity.assumptions && (
                      <div>
                        <span className="text-[10px] text-editorial-charcoal-light uppercase tracking-wider block font-mono">
                          Methodological Assumptions
                        </span>
                        <p className="text-[11px] text-editorial-charcoal-light leading-relaxed">
                          {quantity.assumptions}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 6. Parent Quantities & Navigation */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-editorial-charcoal-light font-mono">
                      Parent Ancestry ({quantity.parents.length})
                    </h4>
                    <span className="text-[10px] text-editorial-brass font-mono">DAG Lineage</span>
                  </div>

                  {quantity.parents.length === 0 ? (
                    <div className="rounded border border-dashed border-editorial-brass/40 p-3 text-center text-xs text-editorial-charcoal-light">
                      Root Observation: No parent inputs (Direct Ground Truth).
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {quantity.parents.map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => onNavigateQuantity?.(p.id)}
                          className="flex w-full items-center justify-between rounded border border-editorial-brass/30 bg-editorial-ivory p-2.5 text-left transition-colors hover:border-editorial-copper hover:bg-editorial-paper group cursor-pointer"
                        >
                          <div className="space-y-0.5">
                            <span className="font-mono text-xs font-semibold text-editorial-charcoal group-hover:text-editorial-copper transition-colors">
                              {p.definition_key}
                            </span>
                            <div className="flex items-center space-x-2 text-[11px] text-editorial-charcoal-light">
                              <span className="font-mono">
                                {p.value?.toLocaleString('en-IN')} {p.unit}
                              </span>
                              <span>•</span>
                              <span className="uppercase text-[9px] font-mono">{p.kind}</span>
                            </div>
                          </div>
                          <ArrowRight className="h-4 w-4 text-editorial-brass group-hover:text-editorial-copper group-hover:translate-x-0.5 transition-all" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* 7. Action: View in Evidence Graph */}
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => onViewInGraph?.(quantity.id)}
                    className="flex w-full items-center justify-center space-x-2 rounded border border-editorial-forest bg-editorial-forest py-2.5 px-4 text-xs font-mono font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-all cursor-pointer shadow-sm"
                  >
                    <Network className="h-4 w-4" />
                    <span>Explore in Evidence Graph</span>
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
};
