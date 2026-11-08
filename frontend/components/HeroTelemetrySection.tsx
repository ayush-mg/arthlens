'use client';

import React, { useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { KineticHeadline } from './motion/KineticHeadline';
import { MagneticButton } from './motion/MagneticButton';
import { Compass, ShieldCheck, Database, Layers, ArrowDown, Activity, Sparkles } from 'lucide-react';

// Lazy-load Three.js procedural 3D background canvas to reduce initial route bundle
const SpatialParticleMesh = dynamic(
  () => import('./motion/SpatialParticleMesh').then((m) => m.SpatialParticleMesh),
  {
    ssr: false,
    loading: () => null,
  }
);

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

interface HeroTelemetrySectionProps {
  onEnterWorkspace: () => void;
  onExploreGraph: () => void;
}

export const HeroTelemetrySection: React.FC<HeroTelemetrySectionProps> = ({
  onEnterWorkspace,
  onExploreGraph,
}) => {
  const sectionRef = useRef<HTMLDivElement>(null);
  const hudRef = useRef<HTMLDivElement>(null);
  const badge1Ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion || !sectionRef.current) return;

    const ctx = gsap.context(() => {
      if (badge1Ref.current) {
        gsap.to(badge1Ref.current, {
          y: -50,
          opacity: 0.5,
          ease: 'none',
          scrollTrigger: {
            trigger: sectionRef.current,
            start: 'top top',
            end: 'bottom top',
            scrub: true,
          },
        });
      }
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative min-h-[88vh] flex flex-col justify-between pt-20 pb-12 px-4 sm:px-6 lg:px-8 border-b border-editorial-brass/40 overflow-hidden bg-editorial-ivory bg-carto-graticule"
    >
      {/* Three.js 3D Spatial Topographic Terrain & Particle Field */}
      <SpatialParticleMesh className="opacity-70" />

      {/* Top telemetry status ticker */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 border-b border-editorial-brass/30 pb-4 text-xs font-mono text-editorial-charcoal-light">
        <div className="flex items-center space-x-3">
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-editorial-forest opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-editorial-forest" />
          </span>
          <span className="text-editorial-forest font-bold tracking-wider">SYSTEM: OPERATIONAL</span>
          <span className="text-editorial-brass">/</span>
          <span className="hidden sm:inline text-editorial-charcoal">GEODETIC DATUM: WGS-84 (EPSG:4326)</span>
          <span className="hidden sm:inline text-editorial-brass">/</span>
          <span className="hidden md:inline text-editorial-charcoal">LGD DIRECTORY: 2026 BASELINE</span>
        </div>

        <div className="flex items-center space-x-6 text-[11px]">
          <div className="flex items-center space-x-2">
            <Activity className="h-3.5 w-3.5 text-editorial-copper" />
            <span>PERSISTED QUANTITIES: <span className="text-editorial-forest font-bold">36 (CENSUS 2011 DS-05 INGESTED)</span></span>
          </div>
          <div className="hidden lg:flex items-center space-x-1.5 text-editorial-charcoal-light">
            <span>AUDIT POLICY:</span>
            <span className="text-editorial-forest font-bold">FAIL-CLOSED</span>
          </div>
        </div>
      </div>

      {/* Main hero typography & interactive presentation */}
      <div className="relative z-10 my-auto py-10 max-w-5xl">
        <div className="mb-4 inline-flex items-center space-x-2 rounded border border-editorial-brass/50 bg-editorial-paper px-3.5 py-1 text-xs font-mono text-editorial-forest shadow-sm">
          <Sparkles className="h-3.5 w-3.5 text-editorial-copper" />
          <span className="font-semibold tracking-wider uppercase">Editorial Geospatial & Financial Intelligence</span>
        </div>

        <h1 className="font-serif text-4xl sm:text-6xl font-bold tracking-tight text-editorial-forest mb-4 leading-tight">
          EPISTEMIC GROUND TRUTH: VERIFIABLE ADMINISTRATIVE & ECONOMIC INTELLIGENCE
        </h1>

        <p className="max-w-2xl text-base sm:text-lg text-editorial-charcoal font-normal leading-relaxed mb-8">
          A high-precision territorial intelligence workspace built on the Local Government Directory (MoPR),
          Census 2011 MDDS, and an immutable cryptographic epistemic ledger.
          Every displayed number is strictly gated by verified observation records.
        </p>

        {/* Action button cluster */}
        <div className="flex flex-wrap items-center gap-4">
          <MagneticButton
            onClick={onEnterWorkspace}
            className="group px-7 py-3.5 rounded border border-editorial-forest bg-editorial-forest text-editorial-ivory font-serif font-bold text-sm shadow-editorial hover:bg-editorial-forest-dark transition-all duration-300 cursor-pointer"
          >
            <span className="flex items-center space-x-2">
              <Compass className="h-4 w-4 transition-transform group-hover:rotate-45 duration-300 text-editorial-brass-light" />
              <span>Launch Economic Atlas</span>
              <ArrowDown className="h-4 w-4 transition-transform group-hover:translate-y-0.5 text-editorial-brass-light" />
            </span>
          </MagneticButton>

          <MagneticButton
            onClick={onExploreGraph}
            className="px-6 py-3.5 rounded border border-editorial-brass/60 bg-editorial-paper hover:bg-editorial-ivory text-editorial-charcoal text-sm font-mono font-medium transition-colors shadow-sm cursor-pointer"
          >
            <span className="flex items-center space-x-2">
              <Database className="h-4 w-4 text-editorial-copper" />
              <span>Inspect Evidence Graph</span>
            </span>
          </MagneticButton>
        </div>
      </div>

      {/* Bottom telemetry indicators */}
      <div
        ref={hudRef}
        className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-editorial-brass/30"
      >
        <div className="flex flex-col">
          <span className="text-[11px] font-mono text-editorial-charcoal-light uppercase tracking-wider">Geographic Records</span>
          <span className="text-xl sm:text-2xl font-bold font-mono text-editorial-forest">800 Baseline</span>
          <span className="text-[11px] text-editorial-charcoal-light">763 Districts, 36 States/UTs, 1 Nation</span>
        </div>

        <div className="flex flex-col">
          <span className="text-[11px] font-mono text-editorial-charcoal-light uppercase tracking-wider">Quality States</span>
          <span className="text-xl sm:text-2xl font-bold font-mono text-editorial-forest">5-Tier</span>
          <span className="text-[11px] text-editorial-charcoal-light">CURRENT to UNAVAILABLE</span>
        </div>

        <div className="flex flex-col">
          <span className="text-[11px] font-mono text-editorial-charcoal-light uppercase tracking-wider">Ledger Invariant</span>
          <span className="text-xl sm:text-2xl font-bold font-mono text-editorial-copper">100% Gated</span>
          <span className="text-[11px] text-editorial-charcoal-light">Zero Silent Numeric Zeros</span>
        </div>

        <div className="flex flex-col">
          <span className="text-[11px] font-mono text-editorial-charcoal-light uppercase tracking-wider">Spatial Vector Status</span>
          <span className="text-xl sm:text-2xl font-bold font-mono text-editorial-brass">Source-Gated</span>
          <span className="text-[11px] text-editorial-charcoal-light">PMTiles gated by Survey of India</span>
        </div>
      </div>

      {/* Parallax floating background elements */}
      <div
        ref={badge1Ref}
        className="pointer-events-none absolute right-12 top-28 hidden xl:flex flex-col p-4 rounded border border-editorial-brass/40 bg-editorial-paper/95 shadow-editorial-lg w-64 z-1"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-mono text-editorial-copper font-bold">PILOT TELEMETRY</span>
          <ShieldCheck className="h-3.5 w-3.5 text-editorial-forest" />
        </div>
        <div className="text-xs text-editorial-charcoal font-mono font-bold">Prayagraj (LGD: 120)</div>
        <div className="text-[11px] text-editorial-charcoal-light mt-1">Status: GEOMETRY_VERIFIED • STALE DATA</div>
        <div className="mt-2 text-[10px] font-mono text-editorial-brass border-t border-editorial-brass/20 pt-1">
          25.4358° N, 81.8463° E
        </div>
      </div>
    </section>
  );
};
