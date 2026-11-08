'use client';

import React, { useRef, useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion, useReducedMotion } from 'framer-motion';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import {
  Compass,
  MapPin,
  ShieldCheck,
  Layers,
  Network,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  TrendingUp,
  Scale,
  Bot,
  ArrowRight,
  Search,
  Globe,
  Building2,
  Factory,
  ChevronRight,
  GitBranch,
  FileCode,
  ShieldAlert,
  Sparkles,
  ExternalLink,
  Lock,
  XCircle,
  FileText,
} from 'lucide-react';
import { MagneticButton } from '../motion/MagneticButton';
import { KineticHeadline } from '../motion/KineticHeadline';
import { PerspectiveCard } from '../motion/PerspectiveCard';
import { HeroTelemetrySection } from '../HeroTelemetrySection';
import { EpistemicProofSection } from '../EpistemicProofSection';
import { EpistemicPipelineSection } from '../EpistemicPipelineSection';
import { audioEngine } from '../../lib/audio';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
  (window as any).gsap = gsap;
  (window as any).ScrollTrigger = ScrollTrigger;
}

interface CinematicStorytellingProps {
  onEnterWorkspace: () => void;
  onExploreGraph: () => void;
}

export const CinematicStorytelling: React.FC<CinematicStorytellingProps> = ({
  onEnterWorkspace,
  onExploreGraph,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const progressBarRef = useRef<HTMLDivElement>(null);
  const shouldReduceMotion = useReducedMotion();

  // Scene 2 interactive scale selector state
  const [activeTerritoryScale, setActiveTerritoryScale] = useState<
    'nation' | 'state' | 'district' | 'enterprise'
  >('district');

  const territoryScales = {
    nation: {
      title: 'The Sovereign Union',
      unitCount: '1 National Federal Entity',
      description:
        'National macroeconomic accounts, inter-state trade corridors, GST revenue vectors, and union-level fiscal governance.',
      metrics: [
        { label: 'Retained Baseline', value: '1 National Record' },
        { label: 'States & UTs', value: '36 Territories' },
        { label: 'Admin Districts', value: '763 Baseline Records' },
      ],
      icon: Globe,
    },
    state: {
      title: 'Federated State Systems',
      unitCount: '36 States & Union Territories',
      description:
        'Sub-national industrial policy, state gross domestic product (SGDP), agricultural market committees (APMC), and state-level subsidy allocations.',
      metrics: [
        { label: 'Federated Units', value: '28 States + 8 UTs' },
        { label: 'LGD Code Coverage', value: '100% Normalized' },
        { label: 'Fiscal Policies', value: 'Sub-National ASTs' },
      ],
      icon: Building2,
    },
    district: {
      title: 'Administrative Districts',
      unitCount: '763 Baseline Districts',
      description:
        'The foundational empirical atom of Indian governance. Local Government Directory (LGD) verified hierarchy with Census 2011 MDDS historical anchors.',
      metrics: [
        { label: 'Census Baseline', value: '2011 MDDS Crosswalk' },
        { label: 'Pilot Survey Geometry', value: 'Prayagraj (LGD 120)' },
        { label: 'Modern Boundaries', value: 'Source-Gated (SoI Portal)' },
      ],
      icon: MapPin,
    },
    enterprise: {
      title: 'Micro-Enterprise & Production Cluster',
      unitCount: 'Informal & Formal Economic Units',
      description:
        'Individual manufacturing facilities, food-processing units, retail catchments, and local labor markets operating under statutory regulatory schemes.',
      metrics: [
        { label: 'Spatial Resolution', value: 'Tier 3 (Sub-district)' },
        { label: 'Downscaling Model', value: 'popweight_v1 (P3)' },
        { label: 'Credit Arithmetic', value: 'Deterministic AST' },
      ],
      icon: Factory,
    },
  };

  // GSAP Choreography & ScrollTrigger Narrative scrub
  useGSAP(
    () => {
      if (shouldReduceMotion || !containerRef.current) return;

      // 1. Global Scroll Progress Tracker
      if (progressBarRef.current) {
        gsap.to(progressBarRef.current, {
          scaleX: 1,
          ease: 'none',
          scrollTrigger: {
            trigger: containerRef.current,
            start: 'top top',
            end: 'bottom bottom',
            scrub: true,
          },
        });
      }

      // 2. Scene 02 Landscape Scale Morph Choreography
      gsap.fromTo(
        '#scene-02-landscape .territory-card',
        { y: 60, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.9,
          stagger: 0.15,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '#scene-02-landscape',
            start: 'top 75%',
            toggleActions: 'play none none reverse',
          },
        }
      );

      // 3. Scene 04 Atlas Cartographic Reveal
      gsap.fromTo(
        '#scene-04-atlas .atlas-reveal-hud',
        { scale: 0.94, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 1.1,
          ease: 'expo.out',
          scrollTrigger: {
            trigger: '#scene-04-atlas',
            start: 'top 70%',
            toggleActions: 'play none none reverse',
          },
        }
      );

      // 4. Scene 06 Simulation & Scene 07 Policy Logic Stagger
      gsap.fromTo(
        '#scene-06-simulation .simulation-node',
        { x: -40, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.12,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: '#scene-06-simulation',
            start: 'top 75%',
            toggleActions: 'play none none reverse',
          },
        }
      );

      gsap.fromTo(
        '#scene-07-policy .kleene-card',
        { y: 30, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.7,
          stagger: 0.1,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: '#scene-07-policy',
            start: 'top 75%',
            toggleActions: 'play none none reverse',
          },
        }
      );

      // 5. Scene 08 Agentic Engine Timeline Flow
      gsap.fromTo(
        '#scene-08-agentic .agentic-step',
        { opacity: 0, scale: 0.92 },
        {
          opacity: 1,
          scale: 1,
          duration: 0.8,
          stagger: 0.1,
          ease: 'back.out(1.2)',
          scrollTrigger: {
            trigger: '#scene-08-agentic',
            start: 'top 70%',
            toggleActions: 'play none none reverse',
          },
        }
      );
    },
    { scope: containerRef, dependencies: [shouldReduceMotion] }
  );

  return (
    <div ref={containerRef} className="relative w-full overflow-hidden">
      {/* Top Fixed Scroll Progress Scrub Bar */}
      <div className="fixed top-16 left-0 right-0 h-1 bg-editorial-brass/20 z-40 pointer-events-none">
        <div
          ref={progressBarRef}
          className="h-full bg-editorial-copper origin-left scale-x-0 will-change-transform shadow-sm"
        />
      </div>

      {/* ========================================================================= */}
      {/* SCENE 01 — THE PROLOGUE & LIVE TELEMETRY HERO                            */}
      {/* ========================================================================= */}
      <div id="scene-01-prologue">
        <HeroTelemetrySection
          onEnterWorkspace={onEnterWorkspace}
          onExploreGraph={onExploreGraph}
        />
      </div>

      {/* ========================================================================= */}
      {/* SCENE 02 — MULTI-SCALE TERRITORY & GEOGRAPHIC BASELINE                    */}
      {/* ========================================================================= */}
      <section
        id="scene-02-landscape"
        className="relative py-28 px-4 sm:px-6 lg:px-8 border-b border-editorial-brass/40 bg-editorial-ivory bg-carto-graticule overflow-hidden"
      >
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Header */}
          <div className="max-w-3xl space-y-4">
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-copper uppercase tracking-widest px-3 py-1 rounded border border-editorial-copper/30 bg-editorial-copper/10">
              <Globe className="h-3.5 w-3.5" />
              <span>Scene 02 // Multi-Scale Territory</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-serif font-bold text-editorial-forest tracking-tight">
              India&apos;s Multi-Scale Economic Anatomy
            </h2>
            <p className="text-sm sm:text-base text-editorial-charcoal font-sans leading-relaxed">
              Economic facts do not exist in isolation. Every production facility, loan contract,
              and policy entitlement anchors to a rigorous territorial hierarchy across{' '}
              <span className="font-bold text-editorial-forest">
                800 retained geographic baseline records: 763 district records, 36 state/UT records and 1 national record
              </span>
              . Modern nationwide spatial vector boundaries remain source-gated to prevent boundary conflation.
            </p>
          </div>

          {/* Scale Switcher Tabs */}
          <div className="flex flex-wrap gap-2 border-b border-editorial-brass/30 pb-4">
            {(['nation', 'state', 'district', 'enterprise'] as const).map((scale) => {
              const Icon = territoryScales[scale].icon;
              const isActive = activeTerritoryScale === scale;
              return (
                <button
                  key={scale}
                  type="button"
                  data-reticle="lock"
                  onClick={() => {
                    audioEngine.playTick();
                    setActiveTerritoryScale(scale);
                  }}
                  className={`flex items-center space-x-2 px-4 py-2 rounded font-mono text-xs font-semibold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-editorial-forest text-editorial-ivory shadow-sm'
                      : 'border border-editorial-brass/40 bg-editorial-paper text-editorial-charcoal hover:border-editorial-copper'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="uppercase">{scale}</span>
                </button>
              );
            })}
          </div>

          {/* Active Scale Detail View */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            <div className="lg:col-span-2 territory-card">
              <PerspectiveCard
                maxTilt={4}
                className="p-8 border-editorial-brass/40 bg-editorial-paper shadow-editorial space-y-6"
              >
                <div className="flex items-start justify-between border-b border-editorial-brass/20 pb-4">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-widest text-editorial-copper block mb-1">
                      Territorial Scale // {activeTerritoryScale.toUpperCase()}
                    </span>
                    <h3 className="text-2xl sm:text-3xl font-serif font-bold text-editorial-forest">
                      {territoryScales[activeTerritoryScale].title}
                    </h3>
                  </div>
                  <span className="px-3 py-1 rounded border border-editorial-brass/40 bg-editorial-ivory text-xs font-mono font-bold text-editorial-forest">
                    {territoryScales[activeTerritoryScale].unitCount}
                  </span>
                </div>

                <p className="text-sm text-editorial-charcoal leading-relaxed">
                  {territoryScales[activeTerritoryScale].description}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-editorial-brass/20">
                  {territoryScales[activeTerritoryScale].metrics.map((m, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded border border-editorial-brass/30 bg-editorial-ivory space-y-1"
                    >
                      <span className="text-[10px] font-mono uppercase text-editorial-charcoal-light block">
                        {m.label}
                      </span>
                      <span className="font-mono text-sm font-bold text-editorial-forest">
                        {m.value}
                      </span>
                    </div>
                  ))}
                </div>
              </PerspectiveCard>
            </div>

            {/* Cartographic Sidebar Telemetry */}
            <div className="space-y-4 territory-card">
              <div className="rounded border border-editorial-brass/40 bg-editorial-forest p-6 text-editorial-ivory space-y-4 shadow-editorial">
                <div className="flex items-center space-x-2 text-editorial-brass-light text-xs font-mono">
                  <Compass className="h-4 w-4" />
                  <span className="font-bold uppercase tracking-wider">Geographic Invariant</span>
                </div>
                <h4 className="font-serif text-lg font-bold">
                  Historical Baseline Retention
                </h4>
                <p className="text-xs text-editorial-sage-light leading-relaxed">
                  ArthLens freezes a 800-unit geographic baseline. Historical 2011 boundaries are
                  strictly segregated from modern 763 LGD hierarchies. No automatic boundary
                  distortion or name-matching conflation is permitted.
                </p>
                <div className="pt-2 text-[10px] font-mono text-editorial-brass">
                  Source: LGD March 2022 Crosswalk & Census 2011 MDDS
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SCENE 03 — THE EPISTEMIC PROBLEM & CRISIS OF UNVERIFIED SAAS              */}
      {/* ========================================================================= */}
      <div id="scene-03-problem">
        <EpistemicProofSection
          onFocusIndicator={() => {
            audioEngine.playSonar();
            onEnterWorkspace();
          }}
        />
      </div>

      {/* ========================================================================= */}
      {/* SCENE 04 — THE ATLAS WORKSPACE ENGINE                                     */}
      {/* ========================================================================= */}
      <section
        id="scene-04-atlas"
        className="relative py-28 px-4 sm:px-6 lg:px-8 border-b border-editorial-brass/40 bg-editorial-forest text-editorial-ivory overflow-hidden"
      >
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Header */}
          <div className="max-w-3xl space-y-4">
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-brass-light uppercase tracking-widest px-3 py-1 rounded border border-editorial-brass/40 bg-editorial-forest-dark/80">
              <Layers className="h-3.5 w-3.5 text-editorial-brass" />
              <span>Scene 04 // Dynamic Geodetic HUD</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-serif font-bold text-editorial-ivory tracking-tight">
              Spatial Vector Cartography with Verifiable Ground Truth
            </h2>
            <p className="text-sm sm:text-base text-editorial-sage-light leading-relaxed">
              The ArthLens Atlas combines MapLibre GL JS vector graphics with standard OpenStreetMap
              tiles. Geographic administrative boundaries are strictly source-gated: verified
              district vectors render with precise boundary strokes, while territories with
              pending geometries transparently disclose their limitation.
            </p>
          </div>

          {/* Interactive Atlas Simulation Viewport */}
          <div className="atlas-reveal-hud rounded-lg border border-editorial-brass/40 bg-editorial-forest-dark p-6 lg:p-8 shadow-editorial-lg space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-editorial-brass/20 pb-4 text-xs font-mono">
              <div className="flex items-center space-x-3">
                <span className="h-2.5 w-2.5 rounded-full bg-editorial-brass animate-pulse" />
                <span className="font-bold text-editorial-ivory">MAP ENGINE: MAPLIBRE GL JS v4.0</span>
                <span className="text-editorial-brass/60">/</span>
                <span className="text-editorial-sage-light">PROJECTION: EPSG:3857 (WGS-84 WEB MERCATOR)</span>
              </div>
              <div className="flex items-center space-x-3 text-[11px] text-editorial-brass-light">
                <span>PILOT GEOMETRY: 1,223 VERTICES</span>
                <span>•</span>
                <span>TILES: OPENSTREETMAP CONTRIBUTORS</span>
              </div>
            </div>

            {/* Cartographic Visual Simulation */}
            <div className="relative h-80 sm:h-[420px] w-full rounded border border-editorial-brass/30 bg-editorial-charcoal overflow-hidden flex items-center justify-center">
              {/* Graticule Overlay */}
              <div className="absolute inset-0 bg-carto-graticule opacity-25 pointer-events-none" />

              {/* Rich Cartographic Vector Preview of Pilot Prayagraj (EPSG:4326) */}
              <svg
                viewBox="0 0 800 500"
                className="w-full h-full p-4 text-editorial-brass"
                fill="none"
                stroke="currentColor"
              >
                {/* Geodetic Coordinate Grid lines and ticks */}
                <g stroke="#B89758" strokeWidth="0.5" strokeOpacity="0.25" strokeDasharray="3 3">
                  <line x1="80" y1="40" x2="80" y2="460" />
                  <line x1="240" y1="40" x2="240" y2="460" />
                  <line x1="400" y1="40" x2="400" y2="460" />
                  <line x1="560" y1="40" x2="560" y2="460" />
                  <line x1="720" y1="40" x2="720" y2="460" />
                  <line x1="40" y1="100" x2="760" y2="100" />
                  <line x1="40" y1="200" x2="760" y2="200" />
                  <line x1="40" y1="300" x2="760" y2="300" />
                  <line x1="40" y1="400" x2="760" y2="400" />
                </g>

                {/* Coordinate Labels */}
                <g className="text-[9px] font-mono fill-editorial-brass/70 stroke-none">
                  <text x="85" y="55">81°30&apos;E</text>
                  <text x="245" y="55">81°45&apos;E</text>
                  <text x="405" y="55">82°00&apos;E</text>
                  <text x="565" y="55">82°15&apos;E</text>
                  <text x="725" y="55">82°30&apos;E</text>
                  <text x="45" y="105">25°45&apos;N</text>
                  <text x="45" y="205">25°30&apos;N</text>
                  <text x="45" y="305">25°15&apos;N</text>
                  <text x="45" y="405">25°00&apos;N</text>
                </g>

                {/* Concentric Geodetic Elevation Contours */}
                <path
                  d="M140,240 Q250,150 420,180 T710,230"
                  stroke="#B89758"
                  strokeWidth="0.75"
                  strokeOpacity="0.35"
                />
                <path
                  d="M130,290 Q280,210 430,240 T720,290"
                  stroke="#B89758"
                  strokeWidth="0.75"
                  strokeOpacity="0.35"
                />
                <path
                  d="M120,340 Q290,270 440,300 T730,350"
                  stroke="#B89758"
                  strokeWidth="0.75"
                  strokeOpacity="0.3"
                />

                {/* River Ganga & River Yamuna confluence (Sangam) */}
                {/* River Yamuna flowing from south-west */}
                <path
                  d="M110,380 C210,360 310,310 395,250"
                  stroke="#5A9690"
                  strokeWidth="3.5"
                  strokeOpacity="0.85"
                  strokeLinecap="round"
                />
                {/* River Ganga flowing from north-west */}
                <path
                  d="M170,110 C240,160 320,210 395,250"
                  stroke="#5A9690"
                  strokeWidth="4"
                  strokeOpacity="0.85"
                  strokeLinecap="round"
                />
                {/* Combined Ganga flowing east */}
                <path
                  d="M395,250 C480,260 590,240 730,220"
                  stroke="#5A9690"
                  strokeWidth="4.5"
                  strokeOpacity="0.85"
                  strokeLinecap="round"
                />

                {/* Pilot District Exterior Boundary (Prayagraj LGD 120 / Census 175) */}
                <path
                  d="M210,95 L340,80 L440,95 L530,130 L610,180 L670,260 L650,340 L580,410 L480,450 L350,455 L250,420 L160,340 L140,250 L160,170 Z"
                  className="stroke-editorial-brass fill-editorial-brass/10"
                  strokeWidth="2.5"
                />

                {/* Internal Tehsil Administrative Partitions */}
                {/* Soraon (North) */}
                <path
                  d="M210,95 L340,80 L380,140 L260,165 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />
                {/* Phulpur (North-East) */}
                <path
                  d="M340,80 L440,95 L530,130 L490,195 L380,140 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />
                {/* Sadar / Urban Core (Center) */}
                <path
                  d="M260,165 L380,140 L440,225 L340,260 Z"
                  className="stroke-editorial-copper fill-editorial-copper/25"
                  strokeWidth="1.5"
                />
                {/* Handia (East) */}
                <path
                  d="M530,130 L610,180 L670,260 L570,270 L490,195 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />
                {/* Karchhana (South of Ganga) */}
                <path
                  d="M340,260 L440,225 L570,270 L540,350 L420,340 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />
                {/* Bara (South-West) */}
                <path
                  d="M160,250 L260,240 L340,260 L420,340 L350,410 L250,420 L160,340 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />
                {/* Meja (South-East) */}
                <path
                  d="M420,340 L540,350 L650,340 L580,410 L480,430 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />
                {/* Koraon (Far South Escarpment) */}
                <path
                  d="M350,410 L480,430 L480,450 L350,455 Z"
                  className="stroke-editorial-brass/60 fill-editorial-forest/30"
                  strokeWidth="1"
                  strokeDasharray="4 2"
                />

                {/* Tehsil Text Annotations */}
                <g className="text-[10px] font-mono fill-editorial-ivory stroke-none font-semibold">
                  <text x="270" y="125">Soraon</text>
                  <text x="410" y="125">Phulpur</text>
                  <text x="315" y="210" className="fill-editorial-copper-light font-bold">Sadar (Doab)</text>
                  <text x="560" y="215">Handia</text>
                  <text x="450" y="295">Karchhana</text>
                  <text x="230" y="335">Bara</text>
                  <text x="510" y="380">Meja</text>
                  <text x="390" y="445">Koraon</text>
                </g>

                {/* River Labels */}
                <g className="text-[9px] font-mono fill-[#7BB4AC] stroke-none italic">
                  <text x="220" y="185">River Ganga →</text>
                  <text x="210" y="365">River Yamuna →</text>
                </g>

                {/* Sangam Confluence Pinpoint Target */}
                <circle cx="395" cy="250" r="5" className="fill-editorial-copper stroke-editorial-ivory" strokeWidth="1.5" />
                <circle cx="395" cy="250" r="10" className="stroke-editorial-copper animate-ping opacity-75" strokeWidth="1" />
                <rect x="412" y="238" width="168" height="22" rx="3" className="fill-editorial-forest-dark/95 stroke-editorial-brass/50" strokeWidth="0.75" />
                <text x="418" y="253" className="text-[9.5px] font-mono font-bold fill-editorial-ivory stroke-none">
                  Sangam (25.43° N, 81.88° E)
                </text>
              </svg>

              {/* Status Badge in Viewport - Explicit Conceptual Attribution */}
              <div className="absolute bottom-4 left-4 max-w-md rounded border border-editorial-brass/40 bg-editorial-forest-dark/95 px-3.5 py-2 text-xs font-mono text-editorial-ivory backdrop-blur-sm shadow-sm">
                <span className="text-editorial-copper font-bold uppercase tracking-wider block mb-0.5">
                  Conceptual Cartographic Diagram (EPSG:4326 Datum)
                </span>
                <span className="text-editorial-sage-light text-[10px] leading-tight block">
                  Illustrative schematic of Prayagraj fluvial confluence &amp; tehsil partitions.
                  Genuine 1,223-vertex PostGIS boundary polygons are rendered dynamically via MapLibre GL in the Epistemic Workspace.
                </span>
              </div>

              <div className="absolute top-4 right-4 rounded border border-editorial-brass/30 bg-editorial-forest/80 px-2.5 py-1 text-[10px] font-mono text-editorial-sage-light">
                Schematic Projection • Live PMTiles / GeoJSON in Workspace
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <p className="text-xs font-mono text-editorial-sage-light max-w-2xl">
                Handbook Invariant: When an unverified territory (e.g. Varanasi) is selected,
                ArthLens renders real basemap context and displays an explicit Source-Gated Boundary
                Card without inventing bounding-box polygons.
              </p>
              <button
                type="button"
                onClick={onEnterWorkspace}
                className="inline-flex items-center space-x-2 rounded border border-editorial-brass bg-editorial-brass/20 px-4 py-2 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-brass/30 transition-colors cursor-pointer"
              >
                <span>OPEN LIVE ATLAS WORKSPACE</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SCENE 05 — THE EVIDENCE ENGINE & PINNED PIPELINE SEQUENCE                 */}
      {/* ========================================================================= */}
      <div id="scene-05-evidence">
        {/* Monotonicity Ladder Header & Floor Cards */}
        <div className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-editorial-brass/30 bg-editorial-paper">
          <div className="max-w-3xl mb-10">
            <span className="text-xs font-mono uppercase tracking-widest text-editorial-copper block mb-2 font-semibold">
              Scene 05 // Epistemic Governance
            </span>
            <h2 className="text-3xl sm:text-5xl font-serif font-bold text-editorial-forest tracking-tight mb-4">
              The Epistemic Monotonicity Ladder
            </h2>
            <p className="text-sm sm:text-base text-editorial-charcoal font-sans leading-relaxed">
              In ArthLens, every quantity carries an invariant evidence floor from 1 to 4. In accordance with Handbook Rule 4.2, evidence levels strictly non-increase through computational DAGs: no derivation can possess higher epistemic strength than its weakest parent.
            </p>
          </div>

          {/* Canonical 4 Evidence Floors per Handbook Section 4.2 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="p-5 rounded border border-editorial-forest bg-editorial-ivory shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-1.5">
                  <span className="font-mono text-xs font-bold text-editorial-forest bg-editorial-forest/10 px-2 py-0.5 rounded">
                    FLOOR 4
                  </span>
                  <span className="text-[10px] font-mono text-editorial-forest font-semibold">(HIGHEST)</span>
                </div>
                <ShieldCheck className="h-4 w-4 text-editorial-forest" />
              </div>
              <span className="font-serif font-bold text-base text-editorial-forest block">
                Observed &amp; Statutory
              </span>
              <p className="text-xs text-editorial-charcoal mt-1 leading-relaxed">
                Empirical ground truth collected directly by statutory government bodies (Census 2011 MDDS, MoSPI, RBI, NSSO). Non-fungible empirical foundation.
              </p>
              <span className="text-[10px] text-editorial-charcoal-light font-mono block mt-3 pt-2 border-t border-editorial-brass/20">
                Persistence: Postgres Quantities • Census DS-05
              </span>
            </div>

            <div className="p-5 rounded border border-editorial-brass/50 bg-editorial-ivory shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs font-bold text-editorial-copper bg-editorial-copper/10 px-2 py-0.5 rounded">
                  FLOOR 3
                </span>
                <CheckCircle2 className="h-4 w-4 text-editorial-copper" />
              </div>
              <span className="font-serif font-bold text-base text-editorial-charcoal block">
                User / Assumed &amp; Reconciled
              </span>
              <p className="text-xs text-editorial-charcoal mt-1 leading-relaxed">
                Direct user inputs, vetted administrative crosswalks (LGD 2022 mapping), verified accounting parameters, and official conversion tables.
              </p>
              <span className="text-[10px] text-editorial-charcoal-light font-mono block mt-3 pt-2 border-t border-editorial-brass/20">
                Persistence: Administrative Crosswalks
              </span>
            </div>

            <div className="p-5 rounded border border-editorial-brass/40 bg-editorial-ivory shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs font-bold text-editorial-copper bg-editorial-copper/10 px-2 py-0.5 rounded">
                  FLOOR 2
                </span>
                <Activity className="h-4 w-4 text-editorial-copper" />
              </div>
              <span className="font-serif font-bold text-base text-editorial-charcoal block">
                Calibrated Model
              </span>
              <p className="text-xs text-editorial-charcoal mt-1 leading-relaxed">
                Scientifically calibrated algorithmic estimates, econometric downscaling, and population-weighted spatial distributions anchored to Floor 4.
              </p>
              <span className="text-[10px] text-editorial-charcoal-light font-mono block mt-3 pt-2 border-t border-editorial-brass/20">
                Specification: popweight_v1 • Spatial Downscale
              </span>
            </div>

            <div className="p-5 rounded border border-editorial-brass/40 bg-editorial-ivory shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-1.5">
                  <span className="font-mono text-xs font-bold text-editorial-charcoal-light bg-editorial-charcoal/10 px-2 py-0.5 rounded">
                    FLOOR 1
                  </span>
                  <span className="text-[10px] font-mono text-editorial-charcoal-light font-semibold">(LOWEST)</span>
                </div>
                <AlertTriangle className="h-4 w-4 text-editorial-charcoal-light" />
              </div>
              <span className="font-serif font-bold text-base text-editorial-charcoal block">
                Uncalibrated Scenario
              </span>
              <p className="text-xs text-editorial-charcoal mt-1 leading-relaxed">
                Hypothetical what-if scenarios, stress-test perturbations, heuristic financial models, and exploratory counterfactual projections.
              </p>
              <span className="text-[10px] text-editorial-charcoal-light font-mono block mt-3 pt-2 border-t border-editorial-brass/20">
                Specification: Exploratory Scenarios
              </span>
            </div>
          </div>

          {/* Orthogonal Quality Status Dimension (Handbook Section 4.3) */}
          <div className="p-5 rounded border border-editorial-brass/40 bg-editorial-ivory">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div className="flex items-center space-x-2">
                <Scale className="h-4 w-4 text-editorial-copper" />
                <span className="font-serif font-bold text-sm text-editorial-forest">
                  Orthogonal Dimension: 5-State Quality Evaluation Token
                </span>
              </div>
              <span className="text-[11px] font-mono text-editorial-charcoal-light">
                Handbook Section 4.3 • QualityStatus Enum
              </span>
            </div>
            <p className="text-xs text-editorial-charcoal mb-4 leading-relaxed">
              Evidence Floor (1–4) measures <em>epistemic origin</em>. Independently, every observation is tagged with a <em>QualityStatus</em> token reflecting freshness, completeness, or absence. Notice that <span className="font-mono font-bold text-editorial-copper">UNAVAILABLE</span> is a quality state, not a floor tier.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center font-mono text-[11px]">
              <div className="p-2.5 rounded border border-emerald-600/30 bg-emerald-50 text-emerald-800">
                <span className="font-bold block">CURRENT</span>
                <span className="text-[9px] text-emerald-700">Recent observation</span>
              </div>
              <div className="p-2.5 rounded border border-amber-600/30 bg-amber-50 text-amber-800">
                <span className="font-bold block">STALE</span>
                <span className="text-[9px] text-amber-700">&gt; 5 yrs (e.g. Census 2011)</span>
              </div>
              <div className="p-2.5 rounded border border-blue-600/30 bg-blue-50 text-blue-800">
                <span className="font-bold block">ESTIMATED</span>
                <span className="text-[9px] text-blue-700">Model-derived</span>
              </div>
              <div className="p-2.5 rounded border border-yellow-600/30 bg-yellow-50 text-yellow-800">
                <span className="font-bold block">INCOMPLETE</span>
                <span className="text-[9px] text-yellow-700">Partial coverage</span>
              </div>
              <div className="p-2.5 rounded border border-red-600/30 bg-red-50 text-red-800">
                <span className="font-bold block">UNAVAILABLE</span>
                <span className="text-[9px] text-red-700">Fail-closed / missing</span>
              </div>
            </div>
          </div>
        </div>

        {/* Pinned 5-Stage Horizontal Ingestion & Pipeline Sequence */}
        <EpistemicPipelineSection />
      </div>

      {/* ========================================================================= */}
      {/* SCENE 06 — ECONOMIC SIMULATION ENGINE (LOOP B ARCHITECTURE)               */}
      {/* ========================================================================= */}
      <section
        id="scene-06-simulation"
        className="relative py-28 px-4 sm:px-6 lg:px-8 border-b border-editorial-brass/40 bg-editorial-ivory bg-carto-graticule overflow-hidden"
      >
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Header */}
          <div className="max-w-3xl space-y-4">
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-copper uppercase tracking-widest px-3 py-1 rounded border border-editorial-copper/30 bg-editorial-copper/10">
              <Cpu className="h-3.5 w-3.5" />
              <span>Scene 06 // Roadmap: Phase 3 Computational Simulation</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-serif font-bold text-editorial-forest tracking-tight">
              Loop B: Economic Simulation Engine
            </h2>
            <p className="text-sm sm:text-base text-editorial-charcoal font-sans leading-relaxed">
              In accordance with Handbook UX Rule 10.3, confidence intervals and financial projections
              are not synthesized without running verified models. The Phase 3 simulation engine
              operates deterministic capital, debt-service, and spatial downscaling models.
            </p>
            <div className="rounded border border-editorial-copper/30 bg-editorial-copper/10 p-2.5 text-xs font-mono text-editorial-copper-dark flex flex-wrap items-center justify-between gap-2">
              <span><strong>Architectural Scope:</strong> Phase 2 Ingestion & Ledger DAG Operational</span>
              <span className="font-bold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded bg-editorial-copper/20 border border-editorial-copper/40">
                Phase 3 Dynamic Solvers
              </span>
            </div>
          </div>

          {/* Architecture Pipeline Visualization */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="simulation-node">
              <PerspectiveCard
                maxTilt={4}
                className="p-6 border-editorial-brass/40 bg-editorial-paper shadow-editorial space-y-4 h-full"
              >
                <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-3">
                  <span className="font-mono text-xs font-bold text-editorial-copper">STEP 01</span>
                  <span className="font-mono text-[9px] uppercase px-2 py-0.5 rounded border border-editorial-brass/40 bg-editorial-ivory">
                    Spatial Downscale
                  </span>
                </div>
                <h4 className="font-serif text-lg font-bold text-editorial-forest">
                  Population-Weighted Allocation
                </h4>
                <p className="text-xs text-editorial-charcoal leading-relaxed">
                  `popweight_v1` downscales district-level empirical quantities to sub-district
                  tehsils proportionally. Floor strictly drops to Floor 2 (Estimated).
                </p>
                <div className="text-[10px] font-mono text-editorial-charcoal-light border-t border-editorial-brass/20 pt-3">
                  Status: Scheduled for Phase 3 Implementation
                </div>
              </PerspectiveCard>
            </div>

            <div className="simulation-node">
              <PerspectiveCard
                maxTilt={4}
                className="p-6 border-editorial-brass/40 bg-editorial-paper shadow-editorial space-y-4 h-full"
              >
                <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-3">
                  <span className="font-mono text-xs font-bold text-editorial-copper">STEP 02</span>
                  <span className="font-mono text-[9px] uppercase px-2 py-0.5 rounded border border-editorial-brass/40 bg-editorial-ivory">
                    Deterministic Finance
                  </span>
                </div>
                <h4 className="font-serif text-lg font-bold text-editorial-forest">
                  Debt-Service & Cash-Flow Arithmetic
                </h4>
                <p className="text-xs text-editorial-charcoal leading-relaxed">
                  Interest, principal amortisation, and working capital requirements calculated with
                  fixed-precision decimal arithmetic. Floating-point round-off error is barred.
                </p>
                <div className="text-[10px] font-mono text-editorial-charcoal-light border-t border-editorial-brass/20 pt-3">
                  Status: Scheduled for Phase 3 Implementation
                </div>
              </PerspectiveCard>
            </div>

            <div className="simulation-node">
              <PerspectiveCard
                maxTilt={4}
                className="p-6 border-editorial-brass/40 bg-editorial-paper shadow-editorial space-y-4 h-full"
              >
                <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-3">
                  <span className="font-mono text-xs font-bold text-editorial-copper">STEP 03</span>
                  <span className="font-mono text-[9px] uppercase px-2 py-0.5 rounded border border-editorial-brass/40 bg-editorial-ivory">
                    Audit Verification
                  </span>
                </div>
                <h4 className="font-serif text-lg font-bold text-editorial-forest">
                  Cryptographic Ledger Commit
                </h4>
                <p className="text-xs text-editorial-charcoal leading-relaxed">
                  Every calculated simulation output generates a new Ledger record with explicit
                  parent quantity IDs, preserving end-to-end evidence lineage.
                </p>
                <div className="text-[10px] font-mono text-editorial-charcoal-light border-t border-editorial-brass/20 pt-3">
                  Status: Epistemic Ledger Architecture Implemented
                </div>
              </PerspectiveCard>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SCENE 07 — POLICY INTELLIGENCE & 3-VALUED KLEENE LOGIC (LOOP C)           */}
      {/* ========================================================================= */}
      <section
        id="scene-07-policy"
        className="relative py-28 px-4 sm:px-6 lg:px-8 border-b border-editorial-brass/40 bg-editorial-paper overflow-hidden"
      >
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Header */}
          <div className="max-w-3xl space-y-4">
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-forest uppercase tracking-widest px-3 py-1 rounded border border-editorial-forest/30 bg-editorial-forest/10">
              <Scale className="h-3.5 w-3.5" />
              <span>Scene 07 // Roadmap: Phase 3 Scheme ASTs</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-serif font-bold text-editorial-forest tracking-tight">
              Loop C: Policy & Scheme Intelligence
            </h2>
            <p className="text-sm sm:text-base text-editorial-charcoal font-sans leading-relaxed">
              Conventional software forces decisions into binary True or False, silently guessing
              when facts are unobserved. ArthLens enforces 3-valued Kleene logic: missing evidence
              evaluates strictly to <span className="font-bold text-editorial-copper">UNKNOWN</span>.
            </p>
            <div className="rounded border border-editorial-forest/30 bg-editorial-forest/10 p-2.5 text-xs font-mono text-editorial-forest flex flex-wrap items-center justify-between gap-2">
              <span><strong>Architectural Scope:</strong> 3-Valued Kleene Schema & Coverage Model Implemented</span>
              <span className="font-bold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded bg-editorial-forest/20 border border-editorial-forest/40">
                Phase 3 AST Evaluator
              </span>
            </div>
          </div>

          {/* Kleene Logic Triad */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="kleene-card p-6 rounded border border-editorial-forest/40 bg-editorial-ivory space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-editorial-forest">LOGIC TIER 1</span>
                <CheckCircle2 className="h-5 w-5 text-editorial-forest" />
              </div>
              <h3 className="font-serif text-lg font-bold text-editorial-forest">
                TRUE: Verified Eligible
              </h3>
              <p className="text-xs text-editorial-charcoal leading-relaxed">
                All statutory criteria satisfied with empirical evidence at or above the required
                evidence floor.
              </p>
            </div>

            <div className="kleene-card p-6 rounded border border-editorial-copper/40 bg-editorial-ivory space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-editorial-copper">LOGIC TIER 2</span>
                <AlertTriangle className="h-5 w-5 text-editorial-copper" />
              </div>
              <h3 className="font-serif text-lg font-bold text-editorial-copper">
                UNKNOWN: Missing Evidence
              </h3>
              <p className="text-xs text-editorial-charcoal leading-relaxed">
                One or more prerequisite variables are unobserved. The system flags exactly what
                evidence must be gathered before eligibility can be established.
              </p>
            </div>

            <div className="kleene-card p-6 rounded border border-editorial-charcoal/30 bg-editorial-ivory space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-editorial-charcoal">LOGIC TIER 3</span>
                <XCircle className="h-5 w-5 text-editorial-charcoal" />
              </div>
              <h3 className="font-serif text-lg font-bold text-editorial-charcoal">
                FALSE: Proven Ineligible
              </h3>
              <p className="text-xs text-editorial-charcoal leading-relaxed">
                At least one statutory condition is definitively violated by verified empirical facts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SCENE 08 — THE AGENTIC ANALYTICAL ENGINE                                  */}
      {/* ========================================================================= */}
      <section
        id="scene-08-agentic"
        className="relative py-28 px-4 sm:px-6 lg:px-8 border-b border-editorial-brass/40 bg-editorial-forest text-editorial-ivory overflow-hidden"
      >
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Header */}
          <div className="max-w-3xl space-y-4">
            <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-brass-light uppercase tracking-widest px-3 py-1 rounded border border-editorial-brass/40 bg-editorial-forest-dark/80">
              <Bot className="h-3.5 w-3.5 text-editorial-brass" />
              <span>Scene 08 // Roadmap: Phase 3 Autonomous Orchestration</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-serif font-bold text-editorial-ivory tracking-tight">
              The Agentic Analytical Engine
            </h2>
            <p className="text-sm sm:text-base text-editorial-sage-light leading-relaxed">
              The Phase 3 architecture specifies autonomous analytical agents. Unlike conversational
              LLMs that hallucinate ungrounded numbers, the ArthLens agent specification strictly
              delegates calculations to deterministic tools and verifies every intermediate output
              against the Epistemic Ledger.
            </p>
            <div className="rounded border border-editorial-brass/40 bg-editorial-forest-dark/95 p-2.5 text-xs font-mono text-editorial-brass-light flex flex-wrap items-center justify-between gap-2">
              <span><strong>Architectural Scope:</strong> PostgreSQL Audit Log & Deterministic Security Guardrails Enforced</span>
              <span className="font-bold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded bg-editorial-brass/20 border border-editorial-brass/40">
                Phase 3 Multi-Agent Loop
              </span>
            </div>
          </div>

          {/* Orchestration Workflow */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                title: 'Goal Interpretation',
                desc: 'Parse entrepreneur requirements, target sector, and geographic scope into typed parameters.',
              },
              {
                step: '02',
                title: 'Deterministic Tools',
                desc: 'Call verified PostGIS spatial queries, ledger retrieval, and audited financial algorithms.',
              },
              {
                step: '03',
                title: 'Mathematical Proof',
                desc: 'Verify floor monotonicity invariants, debt coverage ratios, and cash-flow balances.',
              },
              {
                step: '04',
                title: 'Tamper-Evident Audit',
                desc: 'Register complete agent reasoning chains and tool invocations into the PostgreSQL audit log.',
              },
            ].map((s, idx) => (
              <div
                key={idx}
                className="agentic-step p-6 rounded border border-editorial-brass/30 bg-editorial-forest-dark space-y-3"
              >
                <span className="font-mono text-xs font-bold text-editorial-brass">
                  PHASE {s.step}
                </span>
                <h4 className="font-serif text-lg font-bold text-editorial-ivory">
                  {s.title}
                </h4>
                <p className="text-xs text-editorial-sage-light leading-relaxed">
                  {s.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* SCENE 09 — ENTER ARTHLENS & SEAMLESS WORKSPACE HAND-OFF                   */}
      {/* ========================================================================= */}
      <section
        id="scene-09-enter"
        className="relative py-32 px-4 sm:px-6 lg:px-8 bg-editorial-ivory text-editorial-charcoal overflow-hidden text-center"
      >
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="inline-flex items-center space-x-2 text-xs font-mono text-editorial-forest uppercase tracking-widest px-3.5 py-1.5 rounded border border-editorial-forest/40 bg-editorial-forest/10">
            <Sparkles className="h-4 w-4 text-editorial-copper" />
            <span>Launch Epistemic Environment</span>
          </div>

          <h2 className="text-4xl sm:text-7xl font-serif font-bold text-editorial-forest tracking-tight leading-tight">
            Verifiable Spatial Economics for India.
          </h2>

          <p className="text-base sm:text-lg text-editorial-charcoal max-w-2xl mx-auto leading-relaxed">
            Transition directly from narrative overview to the operational Epistemic Workspace.
            Inspect 800 baseline geographic units, explore the MapLibre Atlas, query ledger-backed
            indicators, and trace verifiable cryptographic provenance.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              type="button"
              data-reticle="lock"
              onClick={() => {
                audioEngine.playSonar();
                onEnterWorkspace();
              }}
              className="w-full sm:w-auto px-8 py-4 rounded border border-editorial-forest bg-editorial-forest text-editorial-ivory font-mono text-sm font-bold hover:bg-editorial-forest-dark transition-all shadow-editorial cursor-pointer flex items-center justify-center space-x-3 group"
            >
              <span>LAUNCH GEOSPATIAL ATLAS</span>
              <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <button
              type="button"
              data-reticle="lock"
              onClick={() => {
                audioEngine.playClick(1050);
                onExploreGraph();
              }}
              className="w-full sm:w-auto px-8 py-4 rounded border border-editorial-brass/60 bg-editorial-paper text-editorial-forest font-mono text-sm font-bold hover:border-editorial-copper hover:text-editorial-copper transition-all shadow-editorial cursor-pointer flex items-center justify-center space-x-3"
            >
              <Network className="h-4 w-4 text-editorial-copper" />
              <span>EXPLORE EVIDENCE GRAPH</span>
            </button>
          </div>

          <div className="pt-8 text-[11px] font-mono text-editorial-charcoal-light flex items-center justify-center space-x-4">
            <span>EPSG:4326 Datum</span>
            <span>•</span>
            <span>800 Retained Baseline Units</span>
            <span>•</span>
            <span>GODL / DataMeet ODbL Attributed</span>
          </div>
        </div>
      </section>
    </div>
  );
};
