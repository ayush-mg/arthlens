'use client';

import React from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import {
  X,
  ShieldAlert,
  ArrowRight,
  Clock,
  FileText,
  GitBranch,
  Network,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import { LedgerQuantityDetail } from '../lib/types';

interface ProvenanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  quantity: LedgerQuantityDetail | null;
  isLoading: boolean;
  error?: string | null;
  onNavigateQuantity: (quantityId: string) => void;
  onViewInGraph: (quantityId: string) => void;
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
          className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm transition-opacity"
        />

        {/* Slide-over panel */}
        <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
          <motion.div
            initial={shouldReduceMotion ? { opacity: 0 } : { x: '100%' }}
            animate={shouldReduceMotion ? { opacity: 1 } : { x: 0 }}
            exit={shouldReduceMotion ? { opacity: 0 } : { x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
            className="w-screen max-w-md border-l border-surface-border bg-surface-card p-6 shadow-2xl overflow-y-auto"
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-surface-border pb-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="rounded bg-brand-sky/15 px-2 py-0.5 font-mono text-[10px] font-semibold text-brand-sky border border-brand-sky/20">
                    Epistemic Ledger Record
                  </span>
                  <span className="font-mono text-xs text-slate-500">
                    Floor {quantity?.evidence_floor ?? '-'}
                  </span>
                </div>
                <h2 className="font-mono text-lg font-bold text-white break-words">
                  {quantity?.definition_key || (isLoading ? 'Querying Ledger...' : 'Record Query')}
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-1 text-slate-400 hover:bg-surface-hover hover:text-white transition-colors"
                aria-label="Close provenance drawer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {isLoading && (
              <div className="py-16 text-center text-xs text-slate-400">
                <div className="mx-auto h-7 w-7 animate-spin rounded-full border-2 border-brand-sky border-t-transparent mb-3" />
                Retrieving verifiable record from Epistemic Ledger...
              </div>
            )}

            {error && !isLoading && (
              <div className="py-14 text-center text-xs">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-rose-500/40 bg-rose-500/10 text-rose-400 mb-4">
                  <AlertCircle className="h-6 w-6" />
                </div>
                <h3 className="font-mono text-sm font-bold text-white mb-2">
                  Ledger Record Unavailable
                </h3>
                <p className="max-w-xs mx-auto text-slate-300 leading-relaxed mb-4">
                  {error}
                </p>
                <div className="rounded-lg border border-surface-border bg-slate-900/60 p-3 text-[11px] text-slate-400 leading-relaxed text-left">
                  <strong className="text-slate-300">Epistemic Guard Invariant:</strong> To prevent misleading or hallucinated context, invalid or missing quantity references strictly fail closed and never display an unrelated or cached record.
                </div>
              </div>
            )}

            {quantity && !isLoading && !error && (
              <div className="mt-5 space-y-6">
                {/* 1. Value & Quality Token */}
                <div className="rounded-xl border border-surface-border bg-surface-panel p-4 shadow-sm">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <span className="font-mono text-2xl font-black text-white">
                        {quantity.value === null
                          ? 'UNAVAILABLE'
                          : quantity.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      </span>
                      <span className="ml-2 font-mono text-sm text-slate-400">{quantity.unit}</span>
                    </div>

                    <div
                      className="flex items-center space-x-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider"
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
                  <p className="mt-3 text-xs leading-relaxed text-slate-300">
                    {quantity.quality.explanation}
                  </p>
                </div>

                {/* 2. Calculation Restrictions & Warnings (if any) */}
                {quantity.calculation_restrictions.length > 0 && (
                  <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 space-y-1.5 text-xs">
                    <div className="flex items-center space-x-2 text-amber-300 font-semibold">
                      <ShieldAlert className="h-4 w-4" />
                      <span>Gated Calculation Restrictions</span>
                    </div>
                    <ul className="list-disc pl-5 text-[11px] text-amber-200/90 space-y-1">
                      {quantity.calculation_restrictions.map((r, idx) => (
                        <li key={idx}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 3. Epistemic Metadata Matrix */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Epistemic Attributes
                  </h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-lg border border-surface-border bg-surface-panel/60 p-2.5">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                        Provenance Kind
                      </span>
                      <span className="font-mono font-semibold text-slate-200">
                        {quantity.kind}
                      </span>
                    </div>

                    <div className="rounded-lg border border-surface-border bg-surface-panel/60 p-2.5">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                        Evidence Floor
                      </span>
                      <span className="font-mono font-semibold text-slate-200">
                        Tier {quantity.evidence_floor}
                      </span>
                    </div>

                    <div className="rounded-lg border border-surface-border bg-surface-panel/60 p-2.5">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                        Spatial Resolution
                      </span>
                      <span className="font-mono font-semibold text-slate-200">
                        Resolution {quantity.resolution}
                      </span>
                    </div>

                    <div className="rounded-lg border border-surface-border bg-surface-panel/60 p-2.5">
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                        Suitability Verdict
                      </span>
                      <span className="font-mono font-semibold text-brand-sky text-[11px] truncate block">
                        {quantity.quality.suitability}
                      </span>
                    </div>
                  </div>
                </div>

                {/* 4. Temporal Breakdown */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Temporal Ground Truth & Freshness
                  </h4>
                  <div className="rounded-lg border border-surface-border bg-surface-panel/60 p-3 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 flex items-center space-x-1">
                        <Calendar className="h-3.5 w-3.5 text-slate-500" />
                        <span>Observation Date (as_of):</span>
                      </span>
                      <span className="font-mono font-semibold text-white">
                        {quantity.as_of || 'Unspecified'}
                      </span>
                    </div>

                    {quantity.temporal && (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Elapsed Age:</span>
                          <span className="font-mono text-slate-300">
                            {quantity.temporal.elapsed_days !== null
                              ? `${quantity.temporal.elapsed_days} days`
                              : 'Uncalculated'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Max Allowed Age:</span>
                          <span className="font-mono text-slate-300">
                            {quantity.temporal.max_age_days !== null
                              ? `${quantity.temporal.max_age_days} days`
                              : 'None (Unconfigured)'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Retrieval Date:</span>
                          <span className="font-mono text-slate-400">
                            {quantity.temporal.retrieval_date || 'N/A'}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* 5. Source Citations & Method */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Source Register & Methodology
                  </h4>
                  <div className="rounded-lg border border-surface-border bg-surface-panel/60 p-3 space-y-2 text-xs">
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                        Source Reference
                      </span>
                      <span className="font-mono font-semibold text-slate-200">
                        {quantity.source_refs.join(', ') || 'Internal Epistemic Model'}
                      </span>
                    </div>

                    {quantity.method_id && (
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                          Derivation Method ID
                        </span>
                        <span className="font-mono text-slate-300">{quantity.method_id}</span>
                      </div>
                    )}

                    {quantity.assumptions && (
                      <div>
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                          Methodological Assumptions
                        </span>
                        <p className="text-[11px] text-slate-400 leading-relaxed">
                          {quantity.assumptions}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 6. Parent Quantities & Navigation */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Parent Ancestry ({quantity.parents.length})
                    </h4>
                    <span className="text-[10px] text-slate-500">DAG Lineage</span>
                  </div>

                  {quantity.parents.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-surface-border p-3 text-center text-xs text-slate-500">
                      Root Observation: No parent inputs (Direct Ground Truth).
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {quantity.parents.map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => onNavigateQuantity(p.id)}
                          className="flex w-full items-center justify-between rounded-lg border border-surface-border bg-surface-panel p-2.5 text-left transition-colors hover:border-brand-sky hover:bg-surface-hover group"
                        >
                          <div className="space-y-0.5">
                            <span className="font-mono text-xs font-semibold text-white group-hover:text-brand-sky transition-colors">
                              {p.definition_key}
                            </span>
                            <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                              <span className="font-mono">
                                {p.value?.toLocaleString()} {p.unit}
                              </span>
                              <span>•</span>
                              <span className="uppercase text-[9px]">{p.kind}</span>
                            </div>
                          </div>
                          <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-brand-sky group-hover:translate-x-0.5 transition-all" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* 7. Action: View in Evidence Graph */}
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => onViewInGraph(quantity.id)}
                    className="flex w-full items-center justify-center space-x-2 rounded-xl bg-gradient-to-r from-brand-indigo to-brand-sky py-2.5 px-4 text-xs font-bold text-white shadow-glow-indigo hover:opacity-90 transition-opacity"
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
