'use client';

import React from 'react';
import { Layers, Network, ShieldCheck, MapPin, Database, Sparkles } from 'lucide-react';

interface NavbarProps {
  currentTab: 'atlas' | 'graph';
  onTabChange: (tab: 'atlas' | 'graph') => void;
  selectedGeoName: string;
  selectedGeoId: string;
  role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN';
  onRoleChange: (role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onTabChange,
  selectedGeoName,
  selectedGeoId,
  role,
  onRoleChange,
}) => {
  return (
    <header className="sticky top-0 z-30 w-full border-b border-surface-border bg-surface-base/90 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Left: Brand & Scope */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2.5">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-sky via-brand-indigo to-brand-cyan shadow-glow-sky">
              <Database className="h-5 w-5 text-slate-950 font-bold" />
              <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface-base bg-quality-current" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-base font-bold tracking-tight text-white">
                  ArthLens
                </span>
                <span className="rounded bg-brand-sky/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-brand-sky border border-brand-sky/20">
                  ATLAS v1.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Evidence-Gated Economic Decision Engine
              </p>
            </div>
          </div>

          <div className="hidden h-6 w-px bg-surface-border md:block" />

          {/* Active Geographic Scope Pill */}
          <div className="hidden items-center space-x-2 rounded-full border border-surface-border bg-surface-panel/80 px-3 py-1 md:flex">
            <MapPin className="h-3.5 w-3.5 text-brand-sky" />
            <span className="text-xs font-medium text-slate-200">{selectedGeoName}</span>
            <span className="font-mono text-[10px] text-slate-400">({selectedGeoId})</span>
          </div>
        </div>

        {/* Center: View Mode Switcher (Atlas vs Evidence Graph) */}
        <div className="flex items-center rounded-lg border border-surface-border bg-surface-panel p-1">
          <button
            type="button"
            onClick={() => onTabChange('atlas')}
            className={`flex items-center space-x-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all ${
              currentTab === 'atlas'
                ? 'bg-brand-sky text-slate-950 shadow-glow-sky'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Atlas Map</span>
          </button>
          <button
            type="button"
            onClick={() => onTabChange('graph')}
            className={`flex items-center space-x-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all ${
              currentTab === 'graph'
                ? 'bg-brand-indigo text-white shadow-glow-indigo'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Network className="h-3.5 w-3.5" />
            <span>Evidence Graph</span>
          </button>
        </div>

        {/* Right: Security Role & Verification Indicator */}
        <div className="flex items-center space-x-3">
          <div className="hidden items-center space-x-2 rounded-md border border-surface-border bg-surface-panel/60 px-2.5 py-1 sm:flex">
            <ShieldCheck className="h-3.5 w-3.5 text-brand-emerald" />
            <span className="font-mono text-[11px] text-slate-300">RBAC:</span>
            <select
              value={role}
              onChange={(e) => onRoleChange(e.target.value as any)}
              className="bg-transparent font-mono text-xs font-bold text-brand-sky outline-none cursor-pointer"
              aria-label="User RBAC Role"
            >
              <option value="ENTREPRENEUR" className="bg-slate-900 text-slate-200">ENTREPRENEUR</option>
              <option value="STEWARD" className="bg-slate-900 text-slate-200">STEWARD</option>
              <option value="ADMIN" className="bg-slate-900 text-slate-200">ADMIN</option>
            </select>
          </div>

          <div className="flex items-center space-x-1.5 rounded-full border border-quality-current/30 bg-quality-current/10 px-2.5 py-0.5 text-[11px] font-semibold text-quality-current">
            <span className="h-1.5 w-1.5 rounded-full bg-quality-current animate-pulse" />
            <span>Ledger Gated</span>
          </div>
        </div>
      </div>
    </header>
  );
};
