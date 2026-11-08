'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Navbar } from './Navbar';
import { GeographicSelector } from './GeographicSelector';
import { AtlasMap } from './AtlasMap';
import { QualityLegend } from './QualityLegend';
import { IndicatorList } from './IndicatorList';
import { ProvenanceDrawer } from './ProvenanceDrawer';
import { EvidenceGraph } from './EvidenceGraph';
import { TactileReticleCursor } from './motion/TactileReticleCursor';
import { audioEngine } from '../lib/audio';
import {
  GeoUnitSummary,
  IndicatorItem,
  LedgerQuantityDetail,
  EvidenceGraphData,
  QualityStatus,
} from '../lib/types';
import {
  fetchGeoIndicators,
  fetchGeoUnitDetail,
  fetchLedgerQuantity,
  fetchEvidenceGraph,
  getCurrentUser,
  loginUser,
  logoutUser,
  isDevAutoAuthEnabled,
  UserProfile,
} from '../lib/api';
import { ShieldCheck, MapPin, Terminal, Clock, ExternalLink, AlertTriangle, Cpu, Layers, FileCheck2 } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ScenarioLaboratory } from './ScenarioLaboratory';
import { PolicyWorkspace } from './PolicyWorkspace';
import { AgentConsole } from './AgentConsole';
import { AnalyticalReportModal } from './AnalyticalReportModal';

const VALID_TABS = ['atlas', 'graph', 'scenarios', 'policy', 'agent'] as const;
type WorkspaceTab = (typeof VALID_TABS)[number];

interface AppWorkspaceProps {
  standalone?: boolean;
  currentTab?: WorkspaceTab;
  onTabChange?: (tab: WorkspaceTab) => void;
  role?: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN';
  onRoleChange?: (role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN') => void;
  currentUser?: UserProfile | null;
  onSwitchAccount?: (role: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN', password?: string) => Promise<void>;
  onLogout?: () => Promise<void>;
}

const getTierDescriptor = (level: number): string => {
  switch (level) {
    case 0:
      return 'National Territory';
    case 1:
      return 'State / Union Territory';
    case 2:
      return 'District';
    case 3:
      return 'Sub-district / Tehsil';
    case 4:
      return 'Village / Urban Ward';
    default:
      return `Tier ${level} Jurisdiction`;
  }
};

export const AppWorkspace: React.FC<AppWorkspaceProps> = ({
  standalone = false,
  currentTab: controlledTab,
  onTabChange: controlledOnTabChange,
  role: controlledRole,
  onRoleChange: controlledOnRoleChange,
  currentUser: controlledUser,
  onSwitchAccount: controlledSwitchAccount,
  onLogout: controlledLogout,
}) => {
  const shouldReduceMotion = useReducedMotion();
  const workspaceRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();

  // Sequence guard against race conditions in out-of-order indicator responses
  const indicatorSeqRef = useRef<number>(0);
  // Sequence guard against race conditions in out-of-order geo unit metadata responses
  const unitSelectionSeqRef = useRef<number>(0);

  // Navigation & Tab State: Read view param from URL query (?view=graph, ?view=scenarios, etc.)
  const rawView = searchParams?.get('view');
  const initialTab: WorkspaceTab = VALID_TABS.includes(rawView as any) ? (rawView as WorkspaceTab) : 'atlas';
  const [internalTab, setInternalTab] = useState<WorkspaceTab>(initialTab);
  const currentTab = controlledTab !== undefined ? controlledTab : internalTab;
  const setCurrentTab = controlledOnTabChange || setInternalTab;

  const [reportModalOpen, setReportModalOpen] = useState(false);

  // React to URL search param changes
  useEffect(() => {
    const viewParam = searchParams?.get('view') as WorkspaceTab;
    if (viewParam && VALID_TABS.includes(viewParam) && currentTab !== viewParam) {
      setCurrentTab(viewParam);
    }
  }, [searchParams, currentTab, setCurrentTab]);

  const handleTabChange = useCallback((newTab: WorkspaceTab) => {
    setCurrentTab(newTab);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (newTab !== 'atlas') {
        url.searchParams.set('view', newTab);
      } else {
        url.searchParams.delete('view');
      }
      window.history.replaceState(null, '', url.toString());
    }
  }, [setCurrentTab]);

  const [internalRole, setInternalRole] = useState<'ENTREPRENEUR' | 'STEWARD' | 'ADMIN'>('ENTREPRENEUR');
  const role = controlledRole !== undefined ? controlledRole : internalRole;
  const setRole = controlledOnRoleChange || setInternalRole;

  const [internalUser, setInternalUser] = useState<UserProfile | null>(null);
  const currentUser = controlledUser !== undefined ? controlledUser : internalUser;
  const setCurrentUser = setInternalUser;

  // Geographic Selection State (Defaults to Pilot Prayagraj district)
  const [selectedUnit, setSelectedUnit] = useState<GeoUnitSummary>({
    id: 'in:district:120',
    name: 'Prayagraj',
    level: 2,
    parent_id: 'in:state:09',
    lgd_code: '120',
    census_code: '175',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_UNVALIDATED',
    analytical_status: 'ANALYSIS_UNAVAILABLE',
    has_geometry: false,
  });

  const [geoUnitError, setGeoUnitError] = useState<string | null>(null);

  // Indicators & Quality State
  const [indicators, setIndicators] = useState<IndicatorItem[]>([]);
  const [isLoadingIndicators, setIsLoadingIndicators] = useState(false);
  const [indicatorError, setIndicatorError] = useState<string | null>(null);
  const [activeQualityFilter, setActiveQualityFilter] = useState<QualityStatus | 'ALL'>('ALL');

  // Active Indicator Selection for Atlas choropleth quality shading (FIX 3)
  const [activeIndicatorKey, setActiveIndicatorKey] = useState<string | null>(null);

  // Provenance Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedQuantity, setSelectedQuantity] = useState<LedgerQuantityDetail | null>(null);
  const [isLoadingQuantity, setIsLoadingQuantity] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  // Evidence Graph State
  const [graphData, setGraphData] = useState<EvidenceGraphData | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  // Initialize Authentication on load
  useEffect(() => {
    let isMounted = true;
    async function initAuth() {
      try {
        const user = await getCurrentUser();
        if (user && isMounted) {
          setCurrentUser(user);
          setRole((user.roles[0] as any) || 'ENTREPRENEUR');
        } else if (!user && isMounted && isDevAutoAuthEnabled()) {
          // Dev initialization: authenticate default entrepreneur session only when dev auto-auth is active
          try {
            const devUser = await loginUser('entrepreneur@arthlens.org', 'Password123!');
            if (isMounted) {
              setCurrentUser(devUser);
              setRole('ENTREPRENEUR');
            }
          } catch {
            // Backend offline or testing environment
          }
        }
      } catch (err) {
        console.warn('Auth initialization notice:', err);
      }
    }
    initAuth();
    return () => {
      isMounted = false;
    };
  }, [setCurrentUser, setRole]);

  // Global Keyboard Shortcuts (1=Map, 2=Graph, m=Mute Audio)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput = activeEl && ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeEl.tagName);
      if (isInput) return;

      if (e.key === '1') {
        handleTabChange('atlas');
        audioEngine.playClick(900);
      } else if (e.key === '2') {
        handleTabChange('graph');
        audioEngine.playClick(1100);
      } else if (e.key === '3') {
        handleTabChange('scenarios');
        audioEngine.playClick(950);
      } else if (e.key === '4') {
        handleTabChange('policy');
        audioEngine.playClick(980);
      } else if (e.key === '5') {
        handleTabChange('agent');
        audioEngine.playClick(1020);
      } else if (e.key === 'd' || e.key === 'D') {
        setReportModalOpen((prev) => !prev);
        audioEngine.playClick(1000);
      } else if (e.key === 'm' || e.key === 'M') {
        audioEngine.toggleMute();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleTabChange]);

  // Account switching handler
  const handleSwitchAccount = useCallback(async (newRole: 'ENTREPRENEUR' | 'STEWARD' | 'ADMIN', explicitPassword?: string) => {
    if (controlledSwitchAccount) {
      await controlledSwitchAccount(newRole, explicitPassword);
      const data = await fetchGeoIndicators(selectedUnit.id);
      setIndicators(data);
      return;
    }
    const emailMap = {
      ENTREPRENEUR: 'entrepreneur@arthlens.org',
      STEWARD: 'steward@arthlens.org',
      ADMIN: 'admin@arthlens.org',
    };
    const password = explicitPassword || (isDevAutoAuthEnabled() ? 'Password123!' : '');
    if (!password) {
      throw new Error('Explicit password required for authentication in production.');
    }
    try {
      const user = await loginUser(emailMap[newRole], password);
      setCurrentUser(user);
      setRole(newRole);
      // Reload indicators after re-authenticating
      const data = await fetchGeoIndicators(selectedUnit.id);
      setIndicators(data);
    } catch (err) {
      console.error('Account switch failed:', err);
      throw err;
    }
  }, [selectedUnit.id, controlledSwitchAccount, setRole, setCurrentUser]);

  const handleLogout = useCallback(async () => {
    if (controlledLogout) {
      await controlledLogout();
      setIndicators([]);
      setGraphData(null);
      return;
    }
    await logoutUser();
    setCurrentUser(null);
    setIndicators([]);
    setGraphData(null);
  }, [controlledLogout, setCurrentUser]);

  // Synchronize unit metadata with backend to ensure genuine geometry status
  useEffect(() => {
    let isMounted = true;
    unitSelectionSeqRef.current += 1;
    const currentSeq = unitSelectionSeqRef.current;

    async function syncUnitDetail() {
      setGeoUnitError(null);
      try {
        const detail = await fetchGeoUnitDetail(selectedUnit.id);
        if (isMounted && currentSeq === unitSelectionSeqRef.current && detail) {
          setSelectedUnit((prev) => {
            if (
              prev.id === detail.id &&
              (prev.geometry_status !== detail.geometry_status ||
                prev.has_geometry !== detail.has_geometry ||
                prev.analytical_status !== detail.analytical_status)
            ) {
              return {
                ...prev,
                geometry_status: detail.geometry_status as any,
                has_geometry: detail.has_geometry,
                analytical_status: detail.analytical_status as any,
              };
            }
            return prev;
          });
        }
      } catch (err: any) {
        if (isMounted && currentSeq === unitSelectionSeqRef.current) {
          setGeoUnitError(err.message || 'Failed to sync geographic unit detail');
        }
      }
    }
    syncUnitDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedUnit.id, currentUser]);

  // Load graph for Cytoscape.js Evidence Graph
  const loadGraphForQuantity = useCallback(async (quantityId: string) => {
    setIsLoadingGraph(true);
    setGraphError(null);
    try {
      const data = await fetchEvidenceGraph(quantityId);
      setGraphData(data);
    } catch (err: any) {
      console.error('Failed to fetch evidence graph:', err);
      setGraphError(err.message || 'Unable to retrieve evidence graph from backend.');
      setGraphData(null);
    } finally {
      setIsLoadingGraph(false);
    }
  }, []);

  // Fetch indicators when selectedUnit changes — sequence guard and immediate reset prevent stale displays
  useEffect(() => {
    let isMounted = true;
    indicatorSeqRef.current += 1;
    const currentSeq = indicatorSeqRef.current;

    // Immediately clear indicators and active graph to prevent stale data displays
    setIndicators([]);
    setGraphData(null);
    setGraphError(null);
    setIndicatorError(null);
    setIsLoadingIndicators(true);

    async function loadIndicators() {
      try {
        const data = await fetchGeoIndicators(selectedUnit.id);
        if (isMounted && currentSeq === indicatorSeqRef.current) {
          setIndicators(data);
          // If in graph view or indicators exist, auto-load graph for the first available indicator
          const firstAvailable = data.find((d) => d.id !== null);
          if (firstAvailable && firstAvailable.id) {
            loadGraphForQuantity(firstAvailable.id);
          }
        }
      } catch (err: any) {
        if (isMounted && currentSeq === indicatorSeqRef.current) {
          console.error('Failed to load indicators:', err);
          setIndicatorError(err.message || 'Unable to retrieve epistemic indicators from backend.');
        }
      } finally {
        if (isMounted && currentSeq === indicatorSeqRef.current) {
          setIsLoadingIndicators(false);
        }
      }
    }

    loadIndicators();
    return () => {
      isMounted = false;
    };
  }, [selectedUnit.id, loadGraphForQuantity, currentUser]);

  // Load full quantity record for Provenance Drawer (Fails closed on invalid IDs)
  const handleOpenProvenance = useCallback(async (quantityId: string) => {
    setDrawerOpen(true);
    setIsLoadingQuantity(true);
    setSelectedQuantity(null);
    setDrawerError(null);
    try {
      const record = await fetchLedgerQuantity(quantityId);
      setSelectedQuantity(record);
    } catch (err: any) {
      console.error('Failed to fetch ledger quantity:', err);
      setDrawerError(
        err.message || `Quantity record '${quantityId}' not found in epistemic ledger.`
      );
    } finally {
      setIsLoadingQuantity(false);
    }
  }, []);

  // Listen for custom open-provenance event for external triggers and automated tests
  useEffect(() => {
    const handleCustomOpen = (e: any) => {
      if (e.detail) {
        handleOpenProvenance(e.detail);
      }
    };
    window.addEventListener('open-provenance', handleCustomOpen);
    return () => window.removeEventListener('open-provenance', handleCustomOpen);
  }, [handleOpenProvenance]);

  // Action: Switch to Evidence Graph from Drawer
  const handleViewInGraph = useCallback(
    (quantityId: string) => {
      setDrawerOpen(false);
      handleTabChange('graph');
      loadGraphForQuantity(quantityId);
      workspaceRef.current?.scrollIntoView({ behavior: 'smooth' });
    },
    [handleTabChange, loadGraphForQuantity]
  );

  return (
    <div
      id="atlas-workspace"
      ref={workspaceRef}
      className={`relative w-full overflow-x-hidden max-w-full ${standalone ? 'min-h-screen flex flex-col bg-editorial-ivory text-editorial-charcoal' : ''}`}
    >
      {/* Precision Tactical Reticle Cursor with Lat/Long Telemetry */}
      {standalone && <TactileReticleCursor />}

      {/* Global Navigation Bar when standalone */}
      {standalone && (
        <Navbar
          currentTab={currentTab}
          onTabChange={handleTabChange}
          selectedGeoName={selectedUnit.name}
          selectedGeoId={selectedUnit.id}
          user={currentUser}
          onSwitchAccount={handleSwitchAccount}
          onLogout={handleLogout}
          role={role}
          onRoleChange={setRole}
          onLogin={(user) => {
            setCurrentUser(user);
            setRole((user.roles[0] as any) || 'ENTREPRENEUR');
          }}
          onOpenReport={() => setReportModalOpen(true)}
        />
      )}

      {/* Top Breadcrumb & Link to Cinematic Tour if standalone */}
      {standalone && (
        <div className="bg-editorial-paper border-b border-editorial-brass/30 px-4 sm:px-6 py-2 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center space-x-2 text-editorial-charcoal-light">
            <Link href="/" className="hover:text-editorial-forest transition-colors flex items-center space-x-1">
              <span>Overview</span>
            </Link>
            <span>/</span>
            <span className="font-bold text-editorial-forest">Epistemic Workspace</span>
          </div>
          <Link
            href="/"
            className="flex items-center space-x-1 text-editorial-forest hover:text-editorial-forest-dark font-semibold transition-colors"
          >
            <span>View Cinematic Introduction</span>
            <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      )}

      {/* Workspace Inner Container — Dominant Spatial Cockpit Architecture */}
      <div className="py-6 sm:py-8 px-4 sm:px-6 lg:px-8 max-w-[1600px] mx-auto w-full space-y-6">
        {/* Sticky Epistemic Invariant Anchor Bar */}
        <div className="sticky top-16 z-30 flex flex-wrap items-center justify-between gap-3 rounded border border-editorial-brass/40 bg-editorial-paper/95 px-4 py-3 shadow-editorial backdrop-blur-md">
          <div className="flex items-center space-x-3">
            <div className="flex h-7 w-7 items-center justify-center rounded border border-editorial-forest/40 bg-editorial-forest/15 text-editorial-forest">
              <MapPin className="h-4 w-4" />
            </div>
            <div className="text-xs">
              <span className="font-serif font-bold text-editorial-forest text-sm">{selectedUnit.name}</span>
              <span className="ml-2 font-mono text-[10px] text-editorial-charcoal-light">
                LGD {selectedUnit.lgd_code} {selectedUnit.census_code ? `• Census ${selectedUnit.census_code}` : ''}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-xs font-mono text-editorial-charcoal">
            <span className="inline-flex items-center space-x-1.5 text-editorial-forest font-semibold">
              <ShieldCheck className="h-4 w-4 text-editorial-forest" />
              <span>Epistemic Invariant: Every displayed number opens its ledger record</span>
            </span>
          </div>
        </div>

        {/* Geographic Selection & Breadcrumbs */}
        <motion.section
          aria-label="Geographic Selector"
          initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <GeographicSelector
            selectedUnit={selectedUnit}
            onSelectUnit={setSelectedUnit}
          />
        </motion.section>

        {/* Dominant Spatial Cockpit Layout: 12-Column Spatial Instrument Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Spatial Instrument Canvas: MapLibre Atlas / Cytoscape DAG (8 Columns) */}
          <div className="lg:col-span-8 space-y-6">
            <motion.section
              aria-label="Geospatial Map and Evidence Graph"
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.05 }}
              className="transition-all duration-300"
            >
              {currentTab === 'atlas' ? (
                <AtlasMap
                  selectedUnit={selectedUnit}
                  onSelectUnitId={async (geoId) => {
                    const detail = await fetchGeoUnitDetail(geoId);
                    setSelectedUnit(detail);
                  }}
                  activeQualityFilter={activeQualityFilter}
                  activeIndicatorKey={activeIndicatorKey}
                  currentUser={currentUser}
                  onOpenProvenance={handleOpenProvenance}
                />
              ) : currentTab === 'graph' ? (
                <EvidenceGraph
                  graphData={graphData}
                  isLoading={isLoadingGraph}
                  error={graphError}
                  isAuthenticated={!!currentUser}
                  onOpenProvenance={handleOpenProvenance}
                  onSignIn={() => {
                    const signInBtn = document.querySelector('button[aria-label="User RBAC Role and Account Session"]') as HTMLElement;
                    if (signInBtn) signInBtn.click();
                  }}
                  onRetry={() => {
                    const firstWithId = indicators.find((d) => d.id !== null);
                    if (firstWithId && firstWithId.id) {
                      loadGraphForQuantity(firstWithId.id);
                    }
                  }}
                />
              ) : currentTab === 'scenarios' ? (
                <ScenarioLaboratory
                  geoName={selectedUnit.name}
                  geoId={selectedUnit.id}
                  userId={currentUser?.id ?? null}
                  isAuthenticated={!!currentUser}
                  onSignIn={() => {
                    const signInBtn = document.querySelector('button[aria-label="User RBAC Role and Account Session"]') as HTMLElement;
                    if (signInBtn) signInBtn.click();
                  }}
                />
              ) : currentTab === 'policy' ? (
                <PolicyWorkspace
                  geoName={selectedUnit.name}
                  geoId={selectedUnit.id}
                  role={role}
                  isAuthenticated={!!currentUser}
                  onSignIn={() => {
                    const signInBtn = document.querySelector('button[aria-label="User RBAC Role and Account Session"]') as HTMLElement;
                    if (signInBtn) signInBtn.click();
                  }}
                />
              ) : (
                <AgentConsole
                  geoName={selectedUnit.name}
                  geoId={selectedUnit.id}
                  isAuthenticated={!!currentUser}
                  onSignIn={() => {
                    const signInBtn = document.querySelector('button[aria-label="User RBAC Role and Account Session"]') as HTMLElement;
                    if (signInBtn) signInBtn.click();
                  }}
                />
              )}
            </motion.section>

            {/* Quality Legend & Precedence Engine — Directly pairs with spatial canvas */}
            <motion.section
              aria-label="Atlas Quality Overlay Shading"
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <QualityLegend
                activeFilter={activeQualityFilter}
                onFilterChange={setActiveQualityFilter}
              />
            </motion.section>
          </div>

          {/* Contextual Intelligence Readout Panel (4 Columns) */}
          <div className="lg:col-span-4 space-y-6">
            {/* Territory Intelligence Summary Card */}
            <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-4 shadow-editorial space-y-3">
              <div className="flex items-center justify-between border-b border-editorial-brass/20 pb-2.5">
                <span className="font-mono text-[10px] uppercase font-bold tracking-wider text-editorial-copper flex items-center space-x-1.5">
                  <Layers className="h-3.5 w-3.5" />
                  <span>Territorial Readout</span>
                </span>
                <span className="font-mono text-[10px] text-editorial-charcoal-light">
                  {selectedUnit.id}
                </span>
              </div>

              <div className="space-y-1">
                <h3 className="font-serif text-lg font-bold text-editorial-forest">
                  {selectedUnit.name}
                </h3>
                <p className="text-xs text-editorial-charcoal-light font-mono">
                  Administrative Level {selectedUnit.level} {getTierDescriptor(selectedUnit.level)} • LGD {selectedUnit.lgd_code}
                </p>
              </div>

              {geoUnitError && (
                <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-2 text-xs text-editorial-copper font-mono flex items-start space-x-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  <span>{geoUnitError}</span>
                </div>
              )}

              {indicatorError && (
                <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-2.5 text-xs text-editorial-copper font-mono space-y-1">
                  <div className="flex items-center space-x-1.5 font-bold">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>Epistemic Backend Notice</span>
                  </div>
                  <p className="text-[11px] leading-relaxed">{indicatorError}</p>
                </div>
              )}
            </div>

            {/* Verified Economic Indicators Matrix */}
            <motion.section
              aria-label="Economic Indicators"
              initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.15 }}
            >
              <IndicatorList
                indicators={indicators}
                isLoading={isLoadingIndicators}
                activeQualityFilter={activeQualityFilter}
                onOpenProvenance={handleOpenProvenance}
                geoName={selectedUnit.name}
                activeIndicatorKey={activeIndicatorKey}
                onSelectIndicatorKey={setActiveIndicatorKey}
              />
            </motion.section>
          </div>
        </div>
      </div>

      {/* Territorial Decision Dossier Modal */}
      <AnalyticalReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        selectedUnit={selectedUnit}
        indicators={indicators}
      />

      {/* Slide-over Provenance Drawer (Opens on ANY number click) */}
      <ProvenanceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        quantity={selectedQuantity}
        isLoading={isLoadingQuantity}
        error={drawerError}
        onNavigateQuantity={handleOpenProvenance}
        onViewInGraph={handleViewInGraph}
      />

      {/* Editorial Cartographic Footer when standalone */}
      {standalone && (
        <footer className="mt-auto border-t border-editorial-brass/40 bg-editorial-forest text-editorial-ivory py-12 px-4 sm:px-6 lg:px-8 text-xs font-mono">
          <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex flex-col space-y-1">
              <span className="font-bold text-editorial-ivory font-serif text-sm tracking-wide">
                ARTHLENS NATIONAL ECONOMIC & SPATIAL INTELLIGENCE
              </span>
              <p className="text-[11px] text-editorial-sage-light/80">
                Data sources: Census 2011 MDDS (Office of the Registrar General & Census Commissioner, India) •
                Local Government Directory (Ministry of Panchayati Raj) under Government Open Data License - India (GODL).
              </p>
            </div>

            <div className="flex items-center space-x-6 text-[11px]">
              <div className="flex items-center space-x-1.5 text-editorial-brass-light">
                <Terminal className="h-3.5 w-3.5 text-editorial-brass-light" />
                <span>RFC 7946 GeoJSON Standard</span>
              </div>
              <div className="flex items-center space-x-1.5 text-editorial-brass-light">
                <Clock className="h-3.5 w-3.5 text-editorial-brass-light" />
                <span>Epistemic Ledger v1.0</span>
              </div>
            </div>
          </div>
        </footer>
      )}
    </div>
  );
};
