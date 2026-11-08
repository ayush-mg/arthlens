'use client';

import React, { useState, useEffect } from 'react';
import {
  FileText,
  ShieldAlert,
  Code2,
  Lock,
} from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { audioEngine } from '../lib/audio';
import { fetchPolicyRules, PolicyRuleRecord } from '../lib/api';

interface PolicyWorkspaceProps {
  geoName: string;
  geoId: string;
  role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN';
  isAuthenticated: boolean;
  onSignIn?: () => void;
}

interface SchemeInfo {
  code: string;
  name: string;
}

const SCHEMES: SchemeInfo[] = [
  {
    code: 'PMFME',
    name: 'PM Formalisation of Micro food processing Enterprises Scheme',
  },
  {
    code: 'PMEGP',
    name: "Prime Minister's Employment Generation Programme",
  },
  {
    code: 'PM-MUDRA',
    name: 'Pradhan Mantri MUDRA Yojana (Shishu / Kishore / Tarun)',
  },
];

export const PolicyWorkspace: React.FC<PolicyWorkspaceProps> = ({
  geoName,
  geoId,
  role,
  isAuthenticated,
  onSignIn,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const [selectedSchemeCode, setSelectedSchemeCode] = useState<string>('PMFME');
  const [showAstViewer, setShowAstViewer] = useState(false);
  const [backendRules, setBackendRules] = useState<PolicyRuleRecord[]>([]);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [ruleError, setRuleError] = useState<string | null>(null);

  const selectedScheme = SCHEMES.find((s) => s.code === selectedSchemeCode) || SCHEMES[0];

  useEffect(() => {
    let isMounted = true;
    async function loadRules() {
      if (!isAuthenticated) {
        setBackendRules([]);
        setRuleError(null);
        setIsLoadingRules(false);
        return;
      }
      setIsLoadingRules(true);
      setBackendRules([]);
      setRuleError(null);
      try {
        const rules = await fetchPolicyRules(selectedScheme.code);
        if (isMounted) {
          setBackendRules(rules);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setRuleError(err instanceof Error ? err.message : 'Failed to load stored policy rules.');
        }
      } finally {
        if (isMounted) setIsLoadingRules(false);
      }
    }
    loadRules();
    return () => {
      isMounted = false;
    };
  }, [selectedScheme.code, isAuthenticated]);

  return (
    <div className="relative w-full overflow-hidden rounded border border-editorial-brass/40 bg-editorial-ivory shadow-editorial p-6 space-y-6">
      {/* Tactical HUD Reticles */}
      <div className="pointer-events-none absolute inset-2 z-10">
        <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-editorial-brass/60" />
        <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-editorial-brass/60" />
        <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-editorial-brass/60" />
        <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-editorial-brass/60" />
      </div>

      {/* Masthead */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-editorial-brass/30 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <FileText className="h-5 w-5 text-editorial-copper" />
            <h2 className="font-serif text-lg font-bold text-editorial-forest">
              Scheme Rule Registry
            </h2>
            <span className="rounded bg-editorial-copper/15 border border-editorial-copper/30 px-2 py-0.5 text-[10px] font-mono font-bold text-editorial-copper">
              NOT AN ELIGIBILITY DECISION
            </span>
          </div>
          <p className="mt-1 text-xs text-editorial-charcoal-light font-mono">
            Only rule versions stored by the backend are shown. Scheme parameters and eligibility are not approved or evaluated here.
          </p>
        </div>

        <div className="flex items-center space-x-2 rounded border border-editorial-brass/30 bg-editorial-paper px-3 py-1.5 text-[11px] font-mono text-editorial-copper">
          <ShieldAlert className="h-4 w-4" />
          <span>Human policy review remains outstanding</span>
        </div>
      </div>

      {/* Scheme Selector Tabs */}
      <div className="flex flex-wrap gap-2">
        {SCHEMES.map((scheme) => {
          const isSelected = scheme.code === selectedSchemeCode;
          return (
            <button
              key={scheme.code}
              type="button"
              onClick={() => {
                audioEngine.playClick(960);
                setSelectedSchemeCode(scheme.code);
              }}
              className={`rounded px-3.5 py-2 text-xs font-mono font-bold transition-all cursor-pointer ${
                isSelected
                  ? 'border border-editorial-forest bg-editorial-forest text-editorial-ivory shadow-sm'
                  : 'border border-editorial-brass/40 bg-editorial-paper text-editorial-charcoal hover:bg-editorial-paper/80'
              }`}
            >
              <span>{scheme.code}</span>
            </button>
          );
        })}
      </div>

      {/* Scheme Detail Card & 3-Valued Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Scheme Register Scope (4 Columns) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-4 space-y-3 font-mono text-xs shadow-sm">
            <span className="text-[10px] text-editorial-copper font-bold uppercase tracking-wider block">
              Candidate Scheme
            </span>
            <h3 className="font-serif font-bold text-editorial-forest text-base">
              {selectedScheme.name}
            </h3>
            <div className="space-y-1.5 text-[11px] text-editorial-charcoal border-t border-editorial-brass/20 pt-2.5">
              <p>
                <strong className="text-editorial-charcoal-light">Code:</strong> {selectedScheme.code}
              </p>
              <p>Source currentness and parameters have not been independently approved.</p>
              <p>
                Selected geography {geoName} ({geoId}) is context only; no geographic eligibility has been evaluated.
              </p>
            </div>
            <div className="border-t border-editorial-brass/20 pt-2 text-[10px] text-editorial-charcoal-light">
              The backend rule store is a draft registry, not a production eligibility service.
            </div>

            {role === 'STEWARD' && (
              <button
                type="button"
                onClick={() => setShowAstViewer(!showAstViewer)}
                className="w-full inline-flex items-center justify-center space-x-1.5 rounded border border-editorial-brass bg-editorial-ivory py-1.5 text-xs font-mono font-bold text-editorial-charcoal hover:bg-editorial-paper transition-colors cursor-pointer"
              >
                <Code2 className="h-3.5 w-3.5 text-editorial-copper" />
                <span>{showAstViewer ? 'Hide AST Representation' : 'Inspect Rule AST (Steward)'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Stored Rule Versions (8 Columns) */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-editorial-forest uppercase tracking-wider flex items-center space-x-1.5">
              <FileText className="h-3.5 w-3.5 text-editorial-forest" />
              <span>Stored rule versions ({backendRules.length})</span>
            </span>
          </div>

          {isLoadingRules && (
            <p className="rounded border border-editorial-brass/30 bg-editorial-paper p-3 text-xs font-mono text-editorial-charcoal-light">
              Loading stored rule versions…
            </p>
          )}
          {ruleError && (
            <p role="alert" className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3 text-xs font-mono text-editorial-copper">
              {ruleError}
            </p>
          )}
          {!isAuthenticated && (
            <p className="rounded border border-editorial-brass/30 bg-editorial-paper p-3 text-xs font-mono text-editorial-charcoal-light flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Sign in to inspect rule versions stored by the backend.
              <button type="button" onClick={onSignIn} className="underline">Sign in</button>
            </p>
          )}
          {!isLoadingRules && isAuthenticated && !ruleError && backendRules.length === 0 && (
            <p className="rounded border border-editorial-brass/30 bg-editorial-paper p-3 text-xs font-mono text-editorial-charcoal-light">
              No rule versions are registered for {selectedScheme.code}. No eligibility result is available.
            </p>
          )}
          <div className="space-y-2">
            {backendRules.map((rule) => (
              <div
                key={rule.id}
                className="rounded border border-editorial-brass/30 bg-editorial-paper p-3.5 space-y-2 text-xs shadow-sm"
              >
                <div className="flex items-center justify-between gap-3 font-mono">
                  <span className="font-bold text-editorial-forest">Version {rule.version}</span>
                  <span className="rounded border border-editorial-brass/40 px-2 py-0.5 text-[10px] text-editorial-copper">
                    {rule.status}
                  </span>
                </div>
                <pre className="overflow-x-auto border-t border-editorial-brass/20 pt-2 text-[11px] text-editorial-charcoal">
                  {JSON.stringify(rule.rule_ast, null, 2)}
                </pre>
              </div>
            ))}
          </div>

          {/* AST Viewer for Stewards */}
          {showAstViewer && role === 'STEWARD' && (
            <motion.div
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="rounded border border-editorial-brass/50 bg-editorial-paper p-4 font-mono text-xs text-editorial-charcoal space-y-2"
            >
              <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-2">
                <span className="font-bold text-editorial-forest">
                  Stored AST: {selectedScheme.code}
                </span>
                <span className="text-[10px] text-editorial-copper">Stored versions only</span>
              </div>
              <pre className="overflow-x-auto p-3 rounded bg-editorial-ivory border border-editorial-brass/30 text-[11px] text-editorial-charcoal leading-relaxed">
                {JSON.stringify(backendRules.map((rule) => ({
                  version: rule.version,
                  status: rule.status,
                  rule_ast: rule.rule_ast,
                })), null, 2)}
              </pre>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};
