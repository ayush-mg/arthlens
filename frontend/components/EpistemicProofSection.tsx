'use client';

import React from 'react';
import { PerspectiveCard } from './motion/PerspectiveCard';
import { ShieldCheck, XCircle, CheckCircle2, ArrowRight } from 'lucide-react';

interface EpistemicProofSectionProps {
  onFocusIndicator: () => void;
}

export const EpistemicProofSection: React.FC<EpistemicProofSectionProps> = ({
  onFocusIndicator,
}) => {
  return (
    <section className="relative py-24 px-4 sm:px-6 lg:px-8 bg-editorial-ivory border-b border-editorial-brass/40 overflow-hidden">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-copper uppercase tracking-widest px-3 py-1 rounded border border-editorial-copper/30 bg-editorial-copper/10 mb-3 font-semibold">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Scene 03 // The Conventional Fragility</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-serif font-bold text-editorial-forest tracking-tight mb-4">
            Every Displayed Number Opens Its Ledger Record.
          </h2>
          <p className="text-sm sm:text-base text-editorial-charcoal font-sans leading-relaxed">
            In conventional platforms, metrics are opaque, disconnected from their sources, and silent numeric zeros mask missing records. In ArthLens, no factual value exists without an immutable cryptographic provenance trail.
          </p>
        </div>

        {/* Side-by-side Architectural Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          {/* Card 1: Conventional Dashboard Anti-Pattern */}
          <PerspectiveCard
            maxTilt={4}
            spotlightColor="rgba(183, 110, 77, 0.08)"
            className="p-8 border-editorial-copper/30 bg-editorial-paper"
          >
            <div className="flex items-center justify-between mb-6">
              <span className="text-xs font-mono text-editorial-copper font-bold uppercase tracking-wider flex items-center space-x-2">
                <XCircle className="h-4 w-4" />
                <span>Conventional SaaS Dashboard</span>
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-editorial-copper/15 text-editorial-copper border border-editorial-copper/30 font-bold">
                UNVERIFIED
              </span>
            </div>

            <div className="space-y-4 mb-6">
              <div className="p-4 rounded border border-editorial-copper/30 bg-editorial-ivory relative space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono text-editorial-charcoal-light">Total Demand Estimate</span>
                  <span className="text-[9px] font-mono uppercase font-bold px-1.5 py-0.5 rounded bg-editorial-copper/20 text-editorial-copper border border-editorial-copper/40">
                    Fictional illustrative anti-pattern
                  </span>
                </div>
                <span className="text-2xl font-bold font-mono text-editorial-charcoal block">₹85,000 / mo</span>
                <span className="text-[11px] text-editorial-copper block font-mono">
                  Source unknown • Model projection unstated • Not an empirical observation
                </span>
              </div>

              <div className="space-y-2 text-xs text-editorial-charcoal font-mono">
                <div className="flex items-start space-x-2">
                  <XCircle className="h-3.5 w-3.5 text-editorial-copper shrink-0 mt-0.5" />
                  <span>Silent numeric zeroes masquerading as verified observations</span>
                </div>
                <div className="flex items-start space-x-2">
                  <XCircle className="h-3.5 w-3.5 text-editorial-copper shrink-0 mt-0.5" />
                  <span>Synthetic bounding box polygons drawn over unverified districts</span>
                </div>
                <div className="flex items-start space-x-2">
                  <XCircle className="h-3.5 w-3.5 text-editorial-copper shrink-0 mt-0.5" />
                  <span>Client-side fake role toggle pretending to grant permissions</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-editorial-brass/20 text-[11px] font-mono text-editorial-copper">
              Epistemic Verdict: Unacceptable for capital allocation decisions.
            </div>
          </PerspectiveCard>

          {/* Card 2: ArthLens Epistemic Integrity Pattern */}
          <PerspectiveCard
            maxTilt={4}
            spotlightColor="rgba(32, 61, 50, 0.12)"
            className="p-8 border-editorial-forest/40 bg-editorial-paper shadow-editorial"
          >
            <div className="flex items-center justify-between mb-6">
              <span className="text-xs font-mono text-editorial-forest font-bold uppercase tracking-wider flex items-center space-x-2">
                <CheckCircle2 className="h-4 w-4" />
                <span>ArthLens Epistemic Ledger</span>
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-editorial-forest/15 text-editorial-forest border border-editorial-forest/30 font-bold">
                CRYPTOGRAPHICALLY GATED
              </span>
            </div>

            <div className="space-y-4 mb-6">
              <div className="p-4 rounded border border-editorial-forest/30 bg-editorial-ivory space-y-1">
                <span className="text-[11px] font-mono text-editorial-charcoal-light block">Total Demand Estimate</span>
                <span className="text-2xl font-bold font-mono text-editorial-forest block">UNAVAILABLE</span>
                <span className="text-[11px] text-editorial-forest block font-mono">
                  Zero unpersisted quantities • Fail-closed without speculative synthesis
                </span>
              </div>

              <div className="space-y-2 text-xs text-editorial-charcoal font-mono">
                <div className="flex items-start space-x-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-editorial-forest shrink-0 mt-0.5" />
                  <span>Every displayed number opens its complete ledger record</span>
                </div>
                <div className="flex items-start space-x-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-editorial-forest shrink-0 mt-0.5" />
                  <span>Genuine 800 baseline geographic records: 763 districts, 36 states/UTs, 1 nation</span>
                </div>
                <div className="flex items-start space-x-2">
                  <CheckCircle2 className="h-3.5 w-3.5 text-editorial-forest shrink-0 mt-0.5" />
                  <span>Authoritative backend RBAC with HTTP-only cookies and audit log</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-editorial-brass/20 text-[11px] font-mono text-editorial-forest font-bold">
              Epistemic Verdict: Authoritative decision intelligence for Indian micro-enterprises.
            </div>
          </PerspectiveCard>
        </div>

        {/* Call to Action */}
        <div className="text-center">
          <button
            type="button"
            onClick={onFocusIndicator}
            className="inline-flex items-center space-x-2 rounded border border-editorial-forest bg-editorial-forest px-6 py-3 font-serif font-bold text-sm text-editorial-ivory hover:bg-editorial-forest-dark transition-all cursor-pointer shadow-editorial"
          >
            <span>Inspect Verified Epistemic Indicators in Workspace</span>
            <ArrowRight className="h-4 w-4 text-editorial-brass-light" />
          </button>
        </div>
      </div>
    </section>
  );
};
