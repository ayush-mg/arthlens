'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Navbar } from '../components/Navbar';
import { GeographicSelector } from '../components/GeographicSelector';
import { AtlasMap } from '../components/AtlasMap';
import { QualityLegend } from '../components/QualityLegend';
import { IndicatorList } from '../components/IndicatorList';
import { ProvenanceDrawer } from '../components/ProvenanceDrawer';
import { EvidenceGraph } from '../components/EvidenceGraph';
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
} from '../lib/api';
import { Sparkles, Compass, ShieldCheck, MapPin, Database } from 'lucide-react';

export default function AtlasPage() {
  const shouldReduceMotion = useReducedMotion();

  // Navigation & Tab State
  const [currentTab, setCurrentTab] = useState<'atlas' | 'graph'>('atlas');
  const [role, setRole] = useState<'ENTREPRENEUR' | 'STEWARD' | 'ADMIN'>('ENTREPRENEUR');

  // Geographic Selection State (Defaults to Pilot Prayagraj district)
  const [selectedUnit, setSelectedUnit] = useState<GeoUnitSummary>({
    id: 'in:district:120',
    name: 'Prayagraj',
    level: 2,
    parent_id: 'in:state:09',
    lgd_code: '120',
    census_code: '175',
    navigation_status: 'NAVIGABLE',
    geometry_status: 'GEOMETRY_VERIFIED',
    analytical_status: 'ANALYSABLE',
    has_geometry: true,
  });

  // Indicators & Quality State
  const [indicators, setIndicators] = useState<IndicatorItem[]>([]);
  const [isLoadingIndicators, setIsLoadingIndicators] = useState(false);
  const [activeQualityFilter, setActiveQualityFilter] = useState<QualityStatus | 'ALL'>('ALL');

  // Provenance Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedQuantity, setSelectedQuantity] = useState<LedgerQuantityDetail | null>(null);
  const [isLoadingQuantity, setIsLoadingQuantity] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  // Evidence Graph State
  const [graphData, setGraphData] = useState<EvidenceGraphData | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);

  // Load graph for Cytoscape.js Evidence Graph
  const loadGraphForQuantity = useCallback(async (quantityId: string) => {
    setIsLoadingGraph(true);
    try {
      const data = await fetchEvidenceGraph(quantityId);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to fetch evidence graph:', err);
    } finally {
      setIsLoadingGraph(false);
    }
  }, []);

  // Fetch indicators when selectedUnit changes
  useEffect(() => {
    let isMounted = true;
    async function loadIndicators() {
      setIsLoadingIndicators(true);
      try {
        const data = await fetchGeoIndicators(selectedUnit.id);
        if (isMounted) {
          setIndicators(data);
          // If in graph view, auto-load graph for the first indicator
          if (data.length > 0) {
            loadGraphForQuantity(data[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load indicators:', err);
      } finally {
        if (isMounted) setIsLoadingIndicators(false);
      }
    }
    loadIndicators();
    return () => {
      isMounted = false;
    };
  }, [selectedUnit.id, loadGraphForQuantity]);

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

  // Action: Switch to Evidence Graph from Drawer
  const handleViewInGraph = useCallback(
    (quantityId: string) => {
      setDrawerOpen(false);
      setCurrentTab('graph');
      loadGraphForQuantity(quantityId);
    },
    [loadGraphForQuantity]
  );

  return (
    <div className="flex min-h-screen flex-col bg-surface-ground text-slate-100 selection:bg-brand-sky/30 selection:text-white">
      {/* 1. Global Application Navbar */}
      <Navbar
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        selectedGeoName={selectedUnit.name}
        selectedGeoId={selectedUnit.id}
        role={role}
        onRoleChange={setRole}
      />

      {/* 2. Main Workspace Layout */}
      <main className="flex-1 px-4 py-6 sm:px-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* Sticky Epistemic Anchor Bar */}
        <div className="sticky top-14 z-30 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-surface-border/90 bg-surface-base/85 px-4 py-2.5 shadow-xl backdrop-blur-md">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-brand-sky/15 text-brand-sky border border-brand-sky/30">
              <MapPin className="h-3.5 w-3.5" />
            </div>
            <div className="text-xs">
              <span className="font-semibold text-white">{selectedUnit.name}</span>
              <span className="ml-2 font-mono text-[10px] text-slate-400">
                LGD {selectedUnit.lgd_code} {selectedUnit.census_code ? `• Census ${selectedUnit.census_code}` : ''}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-400">
            <span className="hidden sm:inline-flex items-center space-x-1.5 text-brand-sky">
              <ShieldCheck className="h-3.5 w-3.5" />
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

        {/* Dynamic Workspace: Atlas Map or Evidence Graph */}
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
            />
          ) : (
            <EvidenceGraph
              graphData={graphData}
              isLoading={isLoadingGraph}
              onOpenProvenance={handleOpenProvenance}
            />
          )}
        </motion.section>

        {/* Quality Legend & Precedence Engine */}
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
          />
        </motion.section>
      </main>

      {/* 3. Slide-over Provenance Drawer (Opens on ANY number click) */}
      <ProvenanceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        quantity={selectedQuantity}
        isLoading={isLoadingQuantity}
        error={drawerError}
        onNavigateQuantity={handleOpenProvenance}
        onViewInGraph={handleViewInGraph}
      />
    </div>
  );
}
