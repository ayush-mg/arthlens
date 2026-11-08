'use client';

import React, { useRef, useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { PerspectiveCard } from './motion/PerspectiveCard';
import {
  FileText,
  Network,
  Lock,
  Layers,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
  (window as any).gsap = gsap;
  (window as any).ScrollTrigger = ScrollTrigger;
}

interface PipelineStage {
  step: string;
  title: string;
  category: string;
  description: string;
  badge: string;
  badgeColor: string;
  icon: React.ReactNode;
  specs: string[];
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    step: 'STAGE 01',
    category: 'SURVEY BASELINE',
    title: 'Official Demographic Ground Truth',
    description:
      'Census of India 2011 Primary Census Abstract (PCA) and Village/Town Directory records ingested with complete MDDS crosswalks under Government Open Data License - India (GODL).',
    badge: 'GODL AUTHORIZED',
    badgeColor: 'border-editorial-forest/30 bg-editorial-forest/10 text-editorial-forest',
    icon: <FileText className="h-6 w-6 text-editorial-forest" />,
    specs: [
      'Census 2011 MDDS (State 09, District 175, Sub-district 00890)',
      'Immutable ingest snapshot preservation in PostgreSQL',
      'Historical source vintage retained (Census 2011 max age 3650d)',
    ],
  },
  {
    step: 'STAGE 02',
    category: 'SPATIAL RESOLUTION',
    title: 'LGD Canonical Administrative Hierarchy',
    description:
      'Deterministic hierarchical resolution across 800 baseline records (763 districts, 36 states/UTs, 1 nation). Nationwide boundary vectors and PMTiles remain source-gated.',
    badge: 'MoPR DIRECTORY',
    badgeColor: 'border-editorial-copper/30 bg-editorial-copper/10 text-editorial-copper',
    icon: <Network className="h-6 w-6 text-editorial-copper" />,
    specs: [
      'Canonical IDs: in:state:{code}, in:district:{lgd}, in:subdistrict:{dist}:{sub}',
      'LGD March 2022 directory crosswalks',
      'Spatial boundaries strictly source-gated',
    ],
  },
  {
    step: 'STAGE 03',
    category: 'CRYPTOGRAPHIC LEDGER',
    title: 'Immutable Epistemic Ledger (13 Fields)',
    description:
      'Every numeric observation is stored as an immutable Quantity record with explicit definition key, Pint unit, evidence floor, uncertainty, and SHA-256 provenance hash.',
    badge: 'ZERO FABRICATION',
    badgeColor: 'border-editorial-brass/40 bg-editorial-brass/10 text-editorial-forest',
    icon: <Lock className="h-6 w-6 text-editorial-forest" />,
    specs: [
      'Pint dimensional analysis: INR, persons, kg/month, dimensionless',
      'Immutable ledger quantities with PostgreSQL check constraints',
      'SHA-256 raw record checksum auditability',
    ],
  },
  {
    step: 'STAGE 04',
    category: 'TEMPORAL DRIFT & POLICY',
    title: 'Continuous Quality Evaluation',
    description:
      'Automatic classification of every indicator into 5 mutually exclusive presentation states: UNAVAILABLE, INCOMPLETE, STALE, ESTIMATED, or CURRENT based on explicit source freshness policies.',
    badge: '5-TIER PRECEDENCE',
    badgeColor: 'border-editorial-copper/30 bg-editorial-copper/10 text-editorial-copper',
    icon: <Layers className="h-6 w-6 text-editorial-copper" />,
    specs: [
      'Precedence: UNAVAILABLE > INCOMPLETE > STALE > ESTIMATED > CURRENT',
      'Stale observation flag on 10-year Census baseline',
      'Visual hatching and dotted patterns for non-current data',
    ],
  },
  {
    step: 'STAGE 05',
    category: 'INTERACTIVE ATLAS',
    title: 'Verified Spatial Canvas & Evidence Graph',
    description:
      'MapLibre GL JS vector cartography renders verified pilot boundaries with data-driven quality shading. Every displayed metric opens its complete ledger ancestry DAG.',
    badge: 'PILOT VERIFIED',
    badgeColor: 'border-editorial-forest/30 bg-editorial-forest/10 text-editorial-forest',
    icon: <CheckCircle2 className="h-6 w-6 text-editorial-forest" />,
    specs: [
      'Genuine Prayagraj district administrative geometry (Census 2011 baseline)',
      'Sub-districts and modern nationwide boundaries strictly source-gated',
      'Full Cytoscape.js ancestry graph exploration',
    ],
  },
];

export const EpistemicPipelineSection: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion || !containerRef.current || !viewportRef.current || !trackRef.current) return;

    let resizeObserver: ResizeObserver | null = null;

    const ctx = gsap.context(() => {
      const scrollWidth = trackRef.current!.scrollWidth;
      const viewportWidth = viewportRef.current!.clientWidth;
      const amountToScroll = Math.max(0, scrollWidth - viewportWidth + 64);

      if (amountToScroll > 0) {
        gsap.to(trackRef.current, {
          x: -amountToScroll,
          ease: 'none',
          scrollTrigger: {
            id: 'epistemic-pipeline-horizontal',
            trigger: containerRef.current,
            start: 'top top',
            end: () => `+=${amountToScroll * 1.25}`,
            pin: true,
            scrub: 1,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });
      }

      // ResizeObserver to recalibrate on responsive layout changes
      resizeObserver = new ResizeObserver(() => {
        ScrollTrigger.refresh();
      });
      if (viewportRef.current) resizeObserver.observe(viewportRef.current);
      if (trackRef.current) resizeObserver.observe(trackRef.current);
    }, containerRef);

    return () => {
      if (resizeObserver) resizeObserver.disconnect();
      ctx.revert();
    };
  }, []);

  return (
    <section
      id="epistemic-pipeline-section"
      ref={containerRef}
      className="relative min-h-screen bg-editorial-paper border-b border-editorial-brass/40 overflow-hidden flex flex-col justify-center py-16"
    >
      {/* Section Header */}
      <div className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full mb-10">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-editorial-copper block mb-2">
              Architecture & Ingestion Pipeline
            </span>
            <h2 className="text-3xl sm:text-5xl font-serif font-bold text-editorial-forest tracking-tight">
              The 5-Stage Epistemic Engine
            </h2>
          </div>
          <div className="flex items-center space-x-2 text-xs font-mono text-editorial-charcoal-light">
            <span>Scroll horizontally to inspect the pipeline</span>
            <ArrowRight className="h-4 w-4 text-editorial-copper" />
          </div>
        </div>
      </div>

      {/* Dedicated Clipping Viewport */}
      <div
        ref={viewportRef}
        className="w-full overflow-hidden px-4 sm:px-6 lg:px-8"
      >
        {/* Horizontal Scroll Track */}
        <div
          ref={trackRef}
          className="epistemic-track flex space-x-6 w-max will-change-transform"
        >
          {PIPELINE_STAGES.map((stage, idx) => (
            <div key={idx} className="w-[340px] sm:w-[420px] shrink-0">
              <PerspectiveCard
                maxTilt={5}
                spotlightColor="rgba(180, 154, 101, 0.15)"
                className="h-full p-6 rounded border border-editorial-brass/40 bg-editorial-ivory shadow-editorial flex flex-col justify-between"
              >
                <div>
                  {/* Stage Header */}
                  <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-4 mb-5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-editorial-copper tracking-wider">
                        {stage.step}
                      </span>
                      <span className="text-editorial-brass">•</span>
                      <span className="font-mono text-[10px] text-editorial-charcoal-light">
                        {stage.category}
                      </span>
                    </div>
                    <span
                      className={`rounded border px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider ${stage.badgeColor}`}
                    >
                      {stage.badge}
                    </span>
                  </div>

                  {/* Stage Title and Icon */}
                  <div className="flex items-start space-x-3 mb-3">
                    <div className="p-2 rounded border border-editorial-brass/30 bg-editorial-paper shrink-0">
                      {stage.icon}
                    </div>
                    <h3 className="font-serif text-lg font-bold text-editorial-forest leading-snug">
                      {stage.title}
                    </h3>
                  </div>

                  <p className="text-xs text-editorial-charcoal leading-relaxed mb-6">
                    {stage.description}
                  </p>
                </div>

                {/* Technical Specifications */}
                <div className="border-t border-editorial-brass/20 pt-4">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-editorial-charcoal-light block mb-2">
                    System Invariants:
                  </span>
                  <ul className="space-y-1.5 text-[11px] font-mono text-editorial-charcoal-light">
                    {stage.specs.map((spec, sIdx) => (
                      <li key={sIdx} className="flex items-start space-x-2">
                        <span className="text-editorial-copper font-bold">•</span>
                        <span>{spec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </PerspectiveCard>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
