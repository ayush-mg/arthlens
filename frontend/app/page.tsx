'use client';

import React, { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { CinematicNavbar } from '../components/cinematic/CinematicNavbar';
import { CinematicStorytelling } from '../components/cinematic/CinematicStorytelling';
import { SmoothScrollProvider } from '../components/motion/SmoothScrollProvider';
import { TactileReticleCursor } from '../components/motion/TactileReticleCursor';
import { audioEngine } from '../lib/audio';
import { Terminal, Clock, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function LandingAndCinematicPage() {
  const router = useRouter();

  const handleEnterWorkspace = useCallback(() => {
    audioEngine.playSonar();
    router.push('/app');
  }, [router]);

  const handleExploreGraph = useCallback(() => {
    audioEngine.playClick(1050);
    router.push('/app?view=graph');
  }, [router]);

  return (
    <SmoothScrollProvider>
      {/* Precision Tactical Reticle Cursor with Lat/Long Telemetry */}
      <TactileReticleCursor />

      <div className="flex min-h-screen flex-col bg-editorial-ivory text-editorial-charcoal selection:bg-editorial-forest/20 selection:text-editorial-forest overflow-x-hidden w-full max-w-full">
        {/* Dedicated Cinematic Brand Navigation Bar — No workspace tabs or geographic selectors */}
        <CinematicNavbar />

        {/* 9-Scene Cinematic Storytelling Narrative Sequence */}
        <main className="flex-1 overflow-x-hidden w-full max-w-full">
          <CinematicStorytelling
            onEnterWorkspace={handleEnterWorkspace}
            onExploreGraph={handleExploreGraph}
          />
        </main>

        {/* Editorial Cartographic Footer */}
        <footer className="border-t border-editorial-brass/40 bg-editorial-forest text-editorial-ivory py-12 px-4 sm:px-6 lg:px-8 text-xs font-mono">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex flex-col space-y-1">
              <span className="font-bold text-editorial-ivory font-serif text-sm tracking-wide">
                ARTHLENS NATIONAL ECONOMIC & SPATIAL INTELLIGENCE
              </span>
              <p className="text-[11px] text-editorial-sage-light/80">
                Data sources: Census 2011 MDDS (Office of the Registrar General & Census Commissioner, India) •
                Local Government Directory (Ministry of Panchayati Raj) under Government Open Data License - India (GODL).
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-6 text-[11px]">
              <div className="flex items-center space-x-1.5 text-editorial-brass-light">
                <Terminal className="h-3.5 w-3.5 text-editorial-brass-light" />
                <span>RFC 7946 GeoJSON Standard</span>
              </div>
              <div className="flex items-center space-x-1.5 text-editorial-brass-light">
                <Clock className="h-3.5 w-3.5 text-editorial-brass-light" />
                <span>Epistemic Ledger v1.0</span>
              </div>
              <Link
                href="/app"
                className="inline-flex items-center space-x-1 px-3 py-1.5 rounded border border-editorial-brass bg-editorial-brass/20 text-editorial-ivory hover:bg-editorial-brass/30 transition-colors font-bold"
              >
                <span>Launch Atlas</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </footer>
      </div>
    </SmoothScrollProvider>
  );
}
