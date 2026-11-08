'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Compass,
  Volume2,
  VolumeX,
  ArrowRight,
  Network,
  Menu,
  X,
  Globe,
  Layers,
  Sparkles,
} from 'lucide-react';
import { audioEngine } from '../../lib/audio';

export const CinematicNavbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(false);

  useEffect(() => {
    setAudioEnabled(audioEngine.isEnabled());
  }, []);

  const handleToggleAudio = () => {
    const nextState = audioEngine.toggleMute();
    setAudioEnabled(nextState);
  };

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    audioEngine.playTick();
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-editorial-brass/30 bg-editorial-forest text-editorial-ivory shadow-editorial backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-3 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        {/* Left: Cartographic Editorial Brand Masthead */}
        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          <Link
            href="/"
            onClick={() => audioEngine.playClick(900)}
            className="flex items-center space-x-2 group"
          >
            <div className="flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded border border-editorial-brass/50 bg-editorial-forest-dark text-editorial-brass shadow-sm group-hover:border-editorial-brass transition-colors shrink-0">
              <Compass className="h-4 w-4 animate-pulse-subtle text-editorial-brass" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-serif text-base sm:text-lg font-bold tracking-wide text-editorial-ivory">
                  ArthLens
                </span>
                <span className="hidden sm:inline-block border border-editorial-brass/40 bg-editorial-brass/15 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-widest text-editorial-brass-light uppercase">
                  National Platform
                </span>
              </div>
              <p className="text-[10px] font-mono tracking-wider text-editorial-sage-light/80 hidden md:block">
                Spatial & Financial Intelligence for India
              </p>
            </div>
          </Link>
        </div>

        {/* Center: Story Navigation Links (Desktop) */}
        <nav
          aria-label="Story Chapters"
          className="hidden lg:flex items-center space-x-1 text-xs font-mono text-editorial-ivory/80"
        >
          <button
            type="button"
            onClick={() => scrollToSection('scene-01-prologue')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('scene-02-landscape')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            Territory
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('scene-03-problem')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            The Problem
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('scene-04-atlas')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            Atlas Engine
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('scene-05-evidence')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            Ledger DAG
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('scene-06-simulation')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            Simulation
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('scene-07-policy')}
            className="px-2.5 py-1 rounded hover:text-editorial-ivory hover:bg-editorial-forest-dark/60 transition-colors cursor-pointer"
          >
            Policy
          </button>
        </nav>

        {/* Right: Direct Actions & Audio Toggle */}
        <div className="flex items-center space-x-1.5 sm:space-x-3 shrink-0">
          {/* Audio Preference Toggle (Default OFF) */}
          <button
            type="button"
            onClick={handleToggleAudio}
            title={audioEnabled ? 'Tactile Audio Active (Mute)' : 'Tactile Audio Muted (Enable)'}
            className="flex items-center space-x-1 sm:space-x-1.5 rounded border border-editorial-brass/30 bg-editorial-forest-dark/80 p-1.5 sm:px-2.5 sm:py-1.5 text-xs font-mono text-editorial-ivory/80 hover:text-editorial-ivory hover:border-editorial-brass transition-colors cursor-pointer"
            aria-label={audioEnabled ? 'Mute micro-acoustics' : 'Enable tactile micro-acoustics'}
          >
            {audioEnabled ? (
              <Volume2 className="h-3.5 w-3.5 text-editorial-brass" />
            ) : (
              <VolumeX className="h-3.5 w-3.5 text-editorial-sage-light/60" />
            )}
            <span className="hidden sm:inline text-[9px] uppercase tracking-wider text-editorial-brass-light font-bold">
              {audioEnabled ? 'Audio ON' : 'Audio OFF'}
            </span>
          </button>

          {/* Evidence Graph Shortcut into /app?view=graph */}
          <Link
            href="/app?view=graph"
            onClick={() => audioEngine.playClick(1050)}
            className="hidden md:inline-flex items-center space-x-1.5 rounded border border-editorial-brass/40 bg-editorial-forest-dark/90 px-3 py-1.5 text-xs font-mono font-semibold text-editorial-ivory hover:border-editorial-brass hover:bg-editorial-forest-dark transition-all cursor-pointer shadow-sm"
          >
            <Network className="h-3.5 w-3.5 text-editorial-copper" />
            <span>Evidence Graph</span>
          </Link>

          {/* Primary App Entry CTA into /app */}
          <Link
            href="/app"
            onClick={() => audioEngine.playClick(880)}
            className="inline-flex items-center space-x-1 sm:space-x-1.5 rounded border border-editorial-brass bg-editorial-brass/20 hover:bg-editorial-brass/30 px-2.5 sm:px-3.5 py-1.5 text-[11px] sm:text-xs font-mono font-bold tracking-wider text-editorial-ivory shadow-sm transition-all cursor-pointer whitespace-nowrap"
          >
            <span>LAUNCH ATLAS</span>
            <ArrowRight className="h-3.5 w-3.5 text-editorial-brass-light" />
          </Link>

          {/* Mobile Menu Hamburger */}
          <button
            type="button"
            onClick={() => {
              audioEngine.playTick();
              setMobileMenuOpen(!mobileMenuOpen);
            }}
            className="lg:hidden p-1.5 rounded text-editorial-ivory/80 hover:text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer"
            aria-label="Toggle story chapters"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-editorial-brass/20 bg-editorial-forest-dark/95 backdrop-blur-md px-4 py-4 space-y-2 text-xs font-mono">
          <div className="text-[10px] uppercase font-bold tracking-widest text-editorial-brass-light/80 mb-2">
            Story Chapters
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <button
              type="button"
              onClick={() => scrollToSection('scene-01-prologue')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              01 Prologue
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-02-landscape')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              02 Territory
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-03-problem')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              03 The Problem
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-04-atlas')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              04 Atlas Engine
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-05-evidence')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              05 Ledger DAG
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-06-simulation')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              06 Simulation
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-07-policy')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              07 Policy Rules
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('scene-08-agentic')}
              className="text-left px-2.5 py-2 rounded bg-editorial-forest/40 hover:bg-editorial-forest text-editorial-ivory transition-colors"
            >
              08 Agentic Engine
            </button>
          </div>

          <div className="pt-3 border-t border-editorial-brass/20 flex flex-col space-y-2">
            <Link
              href="/app?view=graph"
              onClick={() => {
                setMobileMenuOpen(false);
                audioEngine.playClick(1050);
              }}
              className="flex items-center justify-between p-2 rounded bg-editorial-copper/20 border border-editorial-copper/40 text-editorial-ivory font-bold"
            >
              <span className="flex items-center space-x-2">
                <Network className="h-4 w-4 text-editorial-copper" />
                <span>Evidence Graph</span>
              </span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>

            <Link
              href="/app"
              onClick={() => {
                setMobileMenuOpen(false);
                audioEngine.playSonar();
              }}
              className="flex items-center justify-between p-2 rounded bg-editorial-brass text-editorial-forest font-bold"
            >
              <span className="flex items-center space-x-2">
                <Layers className="h-4 w-4" />
                <span>Enter Atlas Workspace</span>
              </span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};

