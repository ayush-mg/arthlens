'use client';

import React, { useEffect, useState } from 'react';
import {
  FlaskConical,
  GitBranch,
  Plus,
  ShieldAlert,
  Lock,
  Calculator,
  Download,
  TrendingUp,
  Landmark,
  Compass,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  FileText,
  FileCode,
  Activity,
  Pencil,
  Trash2,
  GitCompareArrows,
} from 'lucide-react';
import { audioEngine } from '../lib/audio';
import {
  branchScenario,
  calculateScenario,
  createScenario,
  updateScenario,
  deleteScenario,
  compareScenarios,
  ScenarioComparisonResult,
  downloadReportFile,
  fetchMyScenarios,
  getScenarioReportDownloadUrl,
  ScenarioCalculationResults,
  ScenarioCalculationParams,
  FinancialSimulationResults,
  FinancialSimulationRequest,
  simulateScenario,
  ScenarioRecord,
} from '../lib/api';

interface ScenarioLaboratoryProps {
  geoName: string;
  geoId: string;
  userId: string | null;
  isAuthenticated: boolean;
  onSignIn?: () => void;
}

interface ScenarioBranch {
  id: string;
  name: string;
  scenario: Record<string, any>;
  capitalInr: number | null;
  assumptions: string[];
  calculations?: ScenarioCalculationResults | null;
  financialSimulation?: FinancialSimulationResults | null;
}

const toScenarioBranch = (record: ScenarioRecord): ScenarioBranch => {
  const capital = record.scenario?.capital;
  const geoId = record.scenario?.geo_id;
  const calculations = record.scenario?.calculations;
  const financialSimulation = record.scenario?.financial_simulation;
  return {
    id: record.id,
    name: record.name,
    scenario: record.scenario || {},
    capitalInr: typeof capital === 'number' && Number.isFinite(capital) ? capital : null,
    assumptions: [
      ...(typeof capital === 'number' && Number.isFinite(capital)
        ? [`User-entered capital: ₹${capital.toLocaleString('en-IN')}`]
        : []),
      ...(typeof geoId === 'string' ? [`Selected geographic scope: ${geoId}`] : []),
    ],
    calculations: calculations || null,
    financialSimulation: financialSimulation || null,
  };
};

const formatSimulationMetric = (value: number, metricName: string): string => (
  metricName === 'cash_shortfall_probability'
    ? `${(value * 100).toFixed(1)}%`
    : `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
);

const getQuantileBand = (metric: FinancialSimulationResults['metrics'][string]) => {
  const values = Object.entries(metric.quantiles)
    .map(([level, point]) => ({ level: Number(level), value: point.value, quantityId: point.quantity_id }))
    .sort((left, right) => left.level - right.level);
  if (!values.length) return null;
  const low = values[0];
  const high = values[values.length - 1];
  const middle = values[Math.floor(values.length / 2)];
  const minimum = Math.min(low.value, high.value, metric.mean);
  const maximum = Math.max(low.value, high.value, metric.mean);
  const span = maximum - minimum || 1;
  return {
    low,
    high,
    middle,
    left: ((low.value - minimum) / span) * 100,
    width: Math.max(((high.value - low.value) / span) * 100, 1),
    mean: ((metric.mean - minimum) / span) * 100,
  };
};

export const ScenarioLaboratory: React.FC<ScenarioLaboratoryProps> = ({
  geoName,
  geoId,
  userId,
  isAuthenticated,
  onSignIn,
}) => {
  const [scenarios, setScenarios] = useState<ScenarioBranch[]>([]);
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const [newScenarioName, setNewScenarioName] = useState('');
  const [newCapital, setNewCapital] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editCapital, setEditCapital] = useState('');
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [compareLeftId, setCompareLeftId] = useState('');
  const [compareRightId, setCompareRightId] = useState('');
  const [comparison, setComparison] = useState<ScenarioComparisonResult | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  // Business Assumptions Form State
  const [pricePerUnit, setPricePerUnit] = useState('');
  const [variableCost, setVariableCost] = useState('');
  const [fixedCosts, setFixedCosts] = useState('');
  const [loanPrincipal, setLoanPrincipal] = useState('');
  const [annualRate, setAnnualRate] = useState('');
  const [loanTerm, setLoanTerm] = useState('');
  const [moratoriumMonths, setMoratoriumMonths] = useState('');
  const [moratoriumTreatment, setMoratoriumTreatment] = useState('');
  const [subsidyAmount, setSubsidyAmount] = useState('');
  const [subsidyTreatment, setSubsidyTreatment] = useState('');
  const [subsidyReleaseMonth, setSubsidyReleaseMonth] = useState('');
  const [targetVolume, setTargetVolume] = useState('');
  const [isCalculating, setIsCalculating] = useState(false);
  const [calculationError, setCalculationError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [simulationProjectionJson, setSimulationProjectionJson] = useState('');
  const [simulationDistributionsJson, setSimulationDistributionsJson] = useState('');
  const [simulationSensitivityJson, setSimulationSensitivityJson] = useState('');
  const [simulationSeed, setSimulationSeed] = useState('');
  const [simulationSampleCount, setSimulationSampleCount] = useState('');
  const [simulationMinimumCount, setSimulationMinimumCount] = useState('');
  const [simulationQuantilesJson, setSimulationQuantilesJson] = useState('');
  const [simulationTolerancesJson, setSimulationTolerancesJson] = useState('');
  const [simulationShortfallTolerance, setSimulationShortfallTolerance] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setScenarios([]);
    setActiveScenarioId(null);
    setScenarioError(null);
    if (!isAuthenticated) {
      return () => {
        isMounted = false;
      };
    }

    setIsLoadingScenarios(true);
    fetchMyScenarios()
      .then((records) => {
        if (!isMounted) return;
        const loaded = records.map(toScenarioBranch);
        setScenarios(loaded);
        setActiveScenarioId(loaded[0]?.id ?? null);
        setCompareLeftId(loaded[0]?.id ?? '');
        setCompareRightId(loaded[1]?.id ?? '');
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setScenarioError(err instanceof Error ? err.message : 'Failed to load saved scenarios.');
        }
      })
      .finally(() => {
        if (isMounted) setIsLoadingScenarios(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, userId]);

  const activeScenario = scenarios.find((s) => s.id === activeScenarioId);

  useEffect(() => {
    if (!activeScenario) return;
    setEditName(activeScenario.name);
    setEditCapital(typeof activeScenario.scenario.capital === 'number'
      ? String(activeScenario.scenario.capital)
      : '');
  }, [activeScenario]);

  const handleBranch = async (parentScenario: ScenarioBranch) => {
    if (!isAuthenticated) {
      onSignIn?.();
      return;
    }
    audioEngine.playClick(1050);
    setIsSubmitting(true);
    setScenarioError(null);
    try {
      const branchName = `${parentScenario.name} (Branch)`;
      const saved = await branchScenario(parentScenario.id, branchName);
      const newBranch = toScenarioBranch(saved);
      setScenarios((prev) => [newBranch, ...prev]);
      setActiveScenarioId(newBranch.id);
      if (scenarios.length) setCompareRightId(newBranch.id);
    } catch (err: unknown) {
      setScenarioError(err instanceof Error ? err.message : 'Branching failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newScenarioName.trim()) return;
    const capitalInr = Number(newCapital);
    if (!Number.isSafeInteger(capitalInr) || capitalInr <= 0) {
      setScenarioError('Enter a positive whole-rupee capital assumption.');
      return;
    }
    if (!isAuthenticated) {
      onSignIn?.();
      return;
    }
    audioEngine.playClick(980);
    setIsSubmitting(true);
    setScenarioError(null);
    try {
      const saved = await createScenario(newScenarioName.trim(), {
        capital: capitalInr,
        geo_id: geoId,
      });
      const created = toScenarioBranch({
        ...saved,
        scenario: saved.scenario || { capital: capitalInr, geo_id: geoId },
      });
      setScenarios((prev) => [created, ...prev]);
      setActiveScenarioId(created.id);
      if (!compareLeftId) setCompareLeftId(created.id);
      else if (!compareRightId) setCompareRightId(created.id);
      setNewScenarioName('');
      setNewCapital('');
    } catch (err: unknown) {
      setScenarioError(err instanceof Error ? err.message : 'Failed to create scenario.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveScenario = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!activeScenario || !editName.trim()) return;
    const capital = editCapital.trim() ? Number(editCapital) : null;
    if (capital !== null && (!Number.isSafeInteger(capital) || capital <= 0)) {
      setScenarioError('Capital must be a positive whole-rupee assumption, or blank.');
      return;
    }
    const editableScenario = Object.fromEntries(
      Object.entries(activeScenario.scenario).filter(([key]) => ![
        'calculations', 'financial_assumptions', 'financial_simulation', 'spatial_demand',
        'accessibility', 'policy_evaluation', 'assumption_quantity_ids', 'branch_lineage',
      ].includes(key))
    );
    if (capital === null) delete editableScenario.capital;
    else editableScenario.capital = capital;
    setIsSavingEdit(true);
    setScenarioError(null);
    try {
      const saved = await updateScenario(activeScenario.id, editName.trim(), editableScenario);
      const updated = toScenarioBranch(saved);
      setScenarios((previous) => previous.map((scenario) => scenario.id === updated.id ? updated : scenario));
    } catch (err: unknown) {
      setScenarioError(err instanceof Error ? err.message : 'Scenario update failed.');
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDeleteScenario = async (scenario: ScenarioBranch) => {
    if (!window.confirm(`Delete “${scenario.name}” and its saved scenario results?`)) return;
    setIsSubmitting(true);
    setScenarioError(null);
    try {
      await deleteScenario(scenario.id);
      const remaining = scenarios.filter((item) => item.id !== scenario.id);
      setScenarios(remaining);
      if (activeScenarioId === scenario.id) setActiveScenarioId(remaining[0]?.id ?? null);
      if (compareLeftId === scenario.id) setCompareLeftId(remaining[0]?.id ?? '');
      if (compareRightId === scenario.id) setCompareRightId(remaining[1]?.id ?? '');
      setComparison(null);
    } catch (err: unknown) {
      setScenarioError(err instanceof Error ? err.message : 'Scenario deletion failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCompareScenarios = async () => {
    if (!compareLeftId || !compareRightId || compareLeftId === compareRightId) return;
    setIsComparing(true);
    setScenarioError(null);
    try {
      setComparison(await compareScenarios(compareLeftId, compareRightId));
    } catch (err: unknown) {
      setScenarioError(err instanceof Error ? err.message : 'Scenario comparison failed.');
    } finally {
      setIsComparing(false);
    }
  };

  const handleCalculate = async () => {
    if (!activeScenario) return;
    if (!pricePerUnit.trim() || !variableCost.trim() || !fixedCosts.trim()) {
      setCalculationError('Enter selling price, variable cost, and monthly fixed costs to calculate break-even.');
      return;
    }
    setIsCalculating(true);
    setCalculationError(null);
    audioEngine.playClick(1020);
    try {
      const params: ScenarioCalculationParams = {
        price_per_unit: Number(pricePerUnit),
        variable_cost_per_unit: Number(variableCost),
        fixed_costs_per_month: Number(fixedCosts),
      };
      if (loanPrincipal.trim()) params.loan_principal = Number(loanPrincipal);
      if (annualRate.trim()) params.annual_interest_rate = Number(annualRate) / 100;
      if (loanTerm.trim()) params.loan_term_months = Number(loanTerm);
      if (moratoriumMonths.trim()) params.moratorium_months = Number(moratoriumMonths);
      if (moratoriumTreatment) {
        params.moratorium_interest_treatment = moratoriumTreatment as 'PAID' | 'CAPITALISED';
      }
      if (subsidyAmount.trim()) params.subsidy_amount = Number(subsidyAmount);
      if (subsidyTreatment) {
        params.subsidy_treatment = subsidyTreatment as ScenarioCalculationParams['subsidy_treatment'];
      }
      if (subsidyReleaseMonth.trim()) params.subsidy_release_month = Number(subsidyReleaseMonth);
      if (targetVolume.trim()) params.target_monthly_units = Number(targetVolume);
      const res = await calculateScenario(activeScenario.id, params);
      setScenarios((prev) =>
        prev.map((s) => (s.id === activeScenario.id ? { ...s, calculations: res.calculations } : s))
      );
    } catch (err: unknown) {
      setCalculationError(err instanceof Error ? err.message : 'Calculation failed.');
    } finally {
      setIsCalculating(false);
    }
  };

  const handleDownloadDossier = async (format: 'json' | 'csv' | 'xlsx' | 'pdf') => {
    if (!activeScenario) return;
    setDownloadingFormat(format);
    audioEngine.playClick(950);
    try {
      const url = getScenarioReportDownloadUrl(activeScenario.id, format);
      await downloadReportFile(url, `arthlens-dossier-${activeScenario.name.toLowerCase().replace(/\s+/g, '-')}.${format}`);
    } catch (err: unknown) {
      setCalculationError(err instanceof Error ? err.message : `Failed to download ${format.toUpperCase()} report.`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleSimulate = async () => {
    if (!activeScenario) return;
    setSimulationError(null);
    let request: FinancialSimulationRequest;
    try {
      const requiredNumber = (value: string, label: string) => {
        if (!value.trim()) throw new Error(`Enter ${label}.`);
        const number = Number(value);
        if (!Number.isFinite(number)) throw new Error(`${label} must be finite.`);
        return number;
      };
      request = {
        projection: JSON.parse(simulationProjectionJson),
        distributions: JSON.parse(simulationDistributionsJson),
        sensitivity_parameter_values: JSON.parse(simulationSensitivityJson),
        seed: requiredNumber(simulationSeed, 'a reproducibility seed'),
        sample_count: requiredNumber(simulationSampleCount, 'a sample count'),
        minimum_sample_count: requiredNumber(simulationMinimumCount, 'a minimum sample count'),
        quantile_levels: JSON.parse(simulationQuantilesJson),
        convergence_tolerances: JSON.parse(simulationTolerancesJson),
        shortfall_probability_tolerance: requiredNumber(
          simulationShortfallTolerance,
          'a shortfall probability tolerance'
        ),
      };
    } catch (err: unknown) {
      setSimulationError(err instanceof Error ? err.message : 'Complete every simulation input explicitly.');
      return;
    }

    setIsSimulating(true);
    audioEngine.playClick(1040);
    try {
      const result = await simulateScenario(activeScenario.id, request);
      setScenarios((previous) => previous.map((scenario) => (
        scenario.id === activeScenario.id
          ? { ...scenario, financialSimulation: result }
          : scenario
      )));
    } catch (err: unknown) {
      setSimulationError(err instanceof Error ? err.message : 'Simulation failed.');
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="relative w-full overflow-hidden rounded border border-editorial-brass/40 bg-editorial-ivory shadow-editorial p-6 space-y-6">
      {/* Tactical HUD Reticles */}
      <div className="pointer-events-none absolute inset-2 z-10">
        <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-editorial-brass/60" />
        <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-editorial-brass/60" />
        <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-editorial-brass/60" />
        <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-editorial-brass/60" />
      </div>

      {/* Header Masthead */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-editorial-brass/30 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <FlaskConical className="h-5 w-5 text-editorial-copper" />
            <h2 className="font-serif text-lg font-bold text-editorial-forest">
              Scenario Laboratory (Exploratory Financial Lab)
            </h2>
            <span className="rounded bg-editorial-copper/15 border border-editorial-copper/30 px-2 py-0.5 text-[10px] font-mono font-bold text-editorial-copper">
              FLOOR 1: SCENARIO
            </span>
          </div>
          <p className="mt-1 text-xs text-editorial-charcoal-light font-mono">
            Territory: <strong className="text-editorial-forest">{geoName}</strong> ({geoId}) • Sandbox isolation strictly prevents scenario assumptions from elevating to factual facts.
          </p>
        </div>

        {/* Monotonicity Notice Badge */}
        <div className="flex items-center space-x-2 rounded border border-editorial-brass/30 bg-editorial-paper px-3 py-1.5 text-[11px] font-mono text-editorial-charcoal">
          <ShieldAlert className="h-4 w-4 text-editorial-brass" />
          <span>Epistemic Invariant: Floor 1 models never override Floor 4 facts</span>
        </div>
      </div>

      {!isAuthenticated && (
        <div className="rounded border border-editorial-brass/50 bg-editorial-paper p-4 text-xs font-mono text-editorial-charcoal flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Lock className="h-4 w-4 text-editorial-copper" />
            <span>Sign in as ENTREPRENEUR to persist and branch exploratory micro-enterprise scenarios.</span>
          </div>
          <button
            type="button"
            onClick={onSignIn}
            className="rounded border border-editorial-forest bg-editorial-forest px-3 py-1 text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer"
          >
            Sign In
          </button>
        </div>
      )}

      {scenarioError && (
        <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3 text-xs font-mono text-editorial-copper">
          {scenarioError}
        </div>
      )}

      {/* Main Grid: Branches on Left, Active Parameters on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Scenario Branch Explorer (5 Columns) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-editorial-forest uppercase tracking-wider flex items-center space-x-1.5">
              <GitBranch className="h-3.5 w-3.5 text-editorial-copper" />
              <span>Scenario Branches ({scenarios.length})</span>
            </span>
          </div>

          <div className="space-y-2">
            {isLoadingScenarios && (
              <p className="rounded border border-editorial-brass/30 bg-editorial-paper p-3 text-xs font-mono text-editorial-charcoal-light">
                Loading saved scenarios…
              </p>
            )}
            {!isLoadingScenarios && scenarios.length === 0 && (
              <p className="rounded border border-editorial-brass/30 bg-editorial-paper p-3 text-xs font-mono text-editorial-charcoal-light">
                No saved scenarios are available. Create one below; no sample financial results are assumed.
              </p>
            )}
            {scenarios.map((scen) => {
              const isActive = scen.id === activeScenarioId;
              return (
                <div
                  key={scen.id}
                  onClick={() => {
                    audioEngine.playClick(940);
                    setActiveScenarioId(scen.id);
                  }}
                  className={`rounded border p-3 transition-all cursor-pointer text-xs space-y-2 ${
                    isActive
                      ? 'border-editorial-copper bg-editorial-paper shadow-sm ring-1 ring-editorial-copper/50'
                      : 'border-editorial-brass/30 bg-editorial-paper/60 hover:bg-editorial-paper'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <span className="font-serif font-bold text-editorial-forest text-sm">
                      {scen.name}
                    </span>
                    {scen.capitalInr !== null && (
                      <span className="font-mono text-[10px] text-editorial-copper font-semibold">
                        ₹{(scen.capitalInr / 100000).toFixed(1)}L
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-editorial-charcoal-light">
                    <span>
                      {scen.calculations ? (
                        <span className="text-editorial-forest font-semibold flex items-center space-x-1">
                          <CheckCircle2 className="h-3 w-3 inline text-editorial-forest" />
                          <span>Calculated</span>
                        </span>
                      ) : (
                        'Draft Input'
                      )}
                    </span>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleBranch(scen);
                        }}
                        className="inline-flex items-center space-x-1 text-editorial-copper hover:text-editorial-copper-dark font-semibold underline cursor-pointer disabled:opacity-50"
                      >
                        <GitBranch className="h-3 w-3" />
                        <span>Branch</span>
                      </button>
                      <button
                        type="button"
                        disabled={isSubmitting}
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleDeleteScenario(scen);
                        }}
                        aria-label={`Delete ${scen.name}`}
                        className="inline-flex items-center gap-1 text-editorial-copper hover:text-red-800 font-semibold underline cursor-pointer disabled:opacity-50"
                      >
                        <Trash2 className="h-3 w-3" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {scenarios.length > 1 && (
            <section className="rounded border border-editorial-brass/40 bg-editorial-paper p-3.5 space-y-3">
              <div className="flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-wider text-editorial-forest">
                <GitCompareArrows className="h-3.5 w-3.5 text-editorial-copper" />
                <span>Compare saved scenarios</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[['Left scenario', compareLeftId, setCompareLeftId], ['Right scenario', compareRightId, setCompareRightId]].map(([label, value, setter]) => (
                  <label key={label as string} className="space-y-1">
                    <span className="block font-mono text-[10px] text-editorial-charcoal-light">{label as string}</span>
                    <select
                      value={value as string}
                      onChange={(event) => {
                        (setter as (next: string) => void)(event.target.value);
                        setComparison(null);
                      }}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory px-2 py-1.5 font-mono text-[10px] text-editorial-charcoal"
                    >
                      {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}
                    </select>
                  </label>
                ))}
              </div>
              <button
                type="button"
                disabled={isComparing || !compareLeftId || !compareRightId || compareLeftId === compareRightId}
                onClick={() => void handleCompareScenarios()}
                className="w-full rounded border border-editorial-forest bg-editorial-forest px-3 py-2 font-mono text-[10px] font-bold text-editorial-ivory hover:bg-editorial-forest-dark disabled:opacity-50"
              >
                {isComparing ? 'Comparing…' : 'Compare persisted results'}
              </button>
              {comparison && (
                <div className="space-y-2 border-t border-editorial-brass/25 pt-2" aria-live="polite">
                  <div className="flex justify-between font-mono text-[10px]">
                    <span className="font-bold text-editorial-forest">{comparison.status}</span>
                    <span className="text-editorial-charcoal-light">Saved {comparison.id.slice(0, 8)}</span>
                  </div>
                  {Object.entries(comparison.metrics).map(([metric, result]) => (
                    <div key={metric} className="flex justify-between gap-2 border-b border-editorial-brass/15 pb-1 font-mono text-[10px] text-editorial-charcoal">
                      <span>{metric.replaceAll('_', ' ')}</span>
                      <span title={`Delta quantity ${result.delta_right_minus_left.quantity_id}`}>
                        {result.delta_right_minus_left.value.toLocaleString('en-IN')} {result.unit}
                      </span>
                    </div>
                  ))}
                  {Object.keys(comparison.unavailable_metrics).length > 0 && (
                    <p className="text-[10px] font-mono text-editorial-copper">
                      {Object.keys(comparison.unavailable_metrics).length} metric(s) unavailable because both saved scenarios lack matching evidence.
                    </p>
                  )}
                </div>
              )}
            </section>
          )}

          {/* Create New Scenario Form */}
          <form onSubmit={handleCreate} className="rounded border border-editorial-brass/40 bg-editorial-paper p-3.5 space-y-3">
            <span className="font-mono text-[11px] font-bold text-editorial-forest uppercase tracking-wider block">
              Author New Scenario
            </span>
            <input
              type="text"
              value={newScenarioName}
              onChange={(e) => setNewScenarioName(e.target.value)}
              placeholder="e.g., Kirana Retail Grocery in Naini"
              className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-3 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
            />
            <label className="block space-y-1">
              <span className="font-mono text-[11px] text-editorial-charcoal-light">
                Capital assumption (INR, entered by you)
              </span>
              <input
                type="number"
                min="1"
                step="1"
                value={newCapital}
                onChange={(e) => setNewCapital(e.target.value)}
                className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-3 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
              />
            </label>
            <button
              type="submit"
              disabled={isSubmitting || !newScenarioName.trim()}
              className="w-full inline-flex items-center justify-center space-x-1.5 rounded border border-editorial-forest bg-editorial-forest py-2 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Initialize Scenario Branch</span>
            </button>
          </form>
        </div>

        {/* Active Scenario Parameters & Interactive Financial Lab (8 Columns) */}
        <div className="lg:col-span-8 space-y-4">
          {!activeScenario && (
            <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-5 text-xs font-mono text-editorial-charcoal-light">
              Choose or initialize a saved scenario on the left to enter assumptions and execute financial simulations.
            </div>
          )}

          {activeScenario && (
            <div className="rounded border border-editorial-brass/40 bg-editorial-paper p-5 shadow-sm space-y-5">
              {/* Scenario Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-editorial-brass/20 pb-3">
                <div>
                  <span className="font-mono text-[10px] uppercase text-editorial-copper font-bold tracking-wider">
                    Active Scenario Exploration
                  </span>
                  <h3 className="font-serif text-lg font-bold text-editorial-forest">
                    {activeScenario.name}
                  </h3>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="rounded bg-editorial-forest/15 border border-editorial-forest/30 px-2 py-0.5 text-xs font-mono font-bold text-editorial-forest">
                    Persisted
                  </span>
                  {activeScenario.calculations && (
                    <span className="rounded bg-editorial-brass/20 border border-editorial-brass/50 px-2 py-0.5 text-xs font-mono font-bold text-editorial-forest-dark">
                      Model Ready
                    </span>
                  )}
                </div>
              </div>

              <form onSubmit={handleSaveScenario} className="grid gap-2 rounded border border-editorial-brass/30 bg-editorial-ivory p-3 sm:grid-cols-[1fr_10rem_auto] sm:items-end">
                <label className="space-y-1">
                  <span className="block font-mono text-[10px] text-editorial-charcoal-light">Scenario name</span>
                  <input
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                    maxLength={255}
                    required
                    className="w-full rounded border border-editorial-brass/40 bg-editorial-paper px-2.5 py-1.5 font-mono text-xs text-editorial-charcoal"
                  />
                </label>
                <label className="space-y-1">
                  <span className="block font-mono text-[10px] text-editorial-charcoal-light">Capital assumption (₹)</span>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={editCapital}
                    onChange={(event) => setEditCapital(event.target.value)}
                    className="w-full rounded border border-editorial-brass/40 bg-editorial-paper px-2.5 py-1.5 font-mono text-xs text-editorial-charcoal"
                  />
                </label>
                <button
                  type="submit"
                  disabled={isSavingEdit || !editName.trim()}
                  className="inline-flex items-center justify-center gap-1.5 rounded border border-editorial-brass/50 bg-editorial-paper px-3 py-1.5 font-mono text-[10px] font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory disabled:opacity-50"
                >
                  <Pencil className="h-3 w-3" />
                  {isSavingEdit ? 'Saving…' : 'Save edits'}
                </button>
              </form>

              {/* Business Assumptions Input Form */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-editorial-forest uppercase tracking-wider flex items-center space-x-1.5">
                    <Calculator className="h-3.5 w-3.5 text-editorial-copper" />
                    <span>Business Assumptions & Financial Parameters</span>
                  </span>
                  <span className="font-mono text-[10px] text-editorial-charcoal-light">
                    Explicit user assumptions • Floor 3
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Selling Price / Unit (₹)</span>
                    <input
                      type="number"
                      min="0.01"
                      value={pricePerUnit}
                      onChange={(e) => setPricePerUnit(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Variable Cost / Unit (₹)</span>
                    <input
                      type="number"
                      min="0"
                      value={variableCost}
                      onChange={(e) => setVariableCost(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Monthly Fixed Costs (₹)</span>
                    <input
                      type="number"
                      min="0"
                      value={fixedCosts}
                      onChange={(e) => setFixedCosts(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Target Monthly Volume</span>
                    <input
                      type="number"
                      value={targetVolume}
                      onChange={(e) => setTargetVolume(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Loan Principal (₹)</span>
                    <input
                      type="number"
                      min="0"
                      value={loanPrincipal}
                      onChange={(e) => setLoanPrincipal(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Annual Rate (% APR)</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={annualRate}
                      onChange={(e) => setAnnualRate(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Repayment Term (Months)</span>
                    <input
                      type="number"
                      min="1"
                      value={loanTerm}
                      onChange={(e) => setLoanTerm(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Moratorium (Months)</span>
                    <input type="number" min="0" value={moratoriumMonths}
                      onChange={(e) => setMoratoriumMonths(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper" />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Moratorium Interest</span>
                    <select value={moratoriumTreatment} onChange={(e) => setMoratoriumTreatment(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper">
                      <option value="">Choose treatment</option>
                      <option value="PAID">Paid during moratorium</option>
                      <option value="CAPITALISED">Capitalised</option>
                    </select>
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Subsidy Amount (₹)</span>
                    <input type="number" min="0" value={subsidyAmount}
                      onChange={(e) => setSubsidyAmount(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper" />
                  </label>
                  <label className="space-y-1 block">
                    <span className="text-[10px] text-editorial-charcoal-light block">Subsidy Treatment</span>
                    <select value={subsidyTreatment} onChange={(e) => setSubsidyTreatment(e.target.value)}
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper">
                      <option value="">Choose treatment</option>
                      <option value="ADJUSTS_PRINCIPAL">Adjusts principal</option>
                      <option value="BACK_ENDED_RELEASE">Back-ended release</option>
                      <option value="LOCKED_DEPOSIT">Locked deposit</option>
                    </select>
                  </label>
                  {(subsidyTreatment === 'BACK_ENDED_RELEASE' || subsidyTreatment === 'LOCKED_DEPOSIT') && (
                    <label className="space-y-1 block">
                      <span className="text-[10px] text-editorial-charcoal-light block">Subsidy Release (Month)</span>
                      <input type="number" min="1" value={subsidyReleaseMonth}
                        onChange={(e) => setSubsidyReleaseMonth(e.target.value)}
                        className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper" />
                    </label>
                  )}
                  <div className="flex items-end">
                    <button
                      type="button"
                      disabled={isCalculating}
                      onClick={handleCalculate}
                      className="w-full inline-flex items-center justify-center space-x-1.5 rounded border border-editorial-copper bg-editorial-copper py-1.5 px-3 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-copper-dark transition-colors cursor-pointer shadow-sm disabled:opacity-50"
                    >
                      <Calculator className="h-3.5 w-3.5" />
                      <span>{isCalculating ? 'Computing…' : 'Execute Model'}</span>
                    </button>
                  </div>
                </div>

                {calculationError && (
                  <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-2.5 text-xs font-mono text-editorial-copper flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{calculationError}</span>
                  </div>
                )}
              </div>

              {/* Computed Mathematical Results Section */}
              {activeScenario.calculations && (
                <div className="space-y-3 border-t border-editorial-brass/20 pt-4">
                  <span className="font-mono text-xs font-bold text-editorial-forest uppercase tracking-wider block">
                    Deterministic Financial & Spatial Outcomes
                  </span>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-1">
                      <span className="text-[10px] text-editorial-charcoal-light block flex items-center space-x-1">
                        <TrendingUp className="h-3 w-3 text-editorial-copper" />
                        <span>Break-Even Units</span>
                      </span>
                      <span className="text-base font-bold text-editorial-forest block">
                        {activeScenario.calculations.break_even_units?.toLocaleString('en-IN') ?? 'N/A'}
                      </span>
                      <span className="text-[10px] text-editorial-charcoal-light">
                        Margin: {typeof activeScenario.calculations.contribution_margin !== 'number'
                          ? 'unavailable'
                          : `₹${activeScenario.calculations.contribution_margin}`}
                        {typeof activeScenario.calculations.margin_percentage !== 'number'
                          ? ''
                          : ` (${activeScenario.calculations.margin_percentage}%)`}
                      </span>
                    </div>

                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-1">
                      <span className="text-[10px] text-editorial-charcoal-light block flex items-center space-x-1">
                        <Landmark className="h-3 w-3 text-editorial-forest" />
                        <span>Monthly EMI</span>
                      </span>
                      <span className="text-base font-bold text-editorial-forest block">
                        {typeof activeScenario.calculations.monthly_emi !== 'number'
                          ? 'Unavailable'
                          : `₹${activeScenario.calculations.monthly_emi.toLocaleString('en-IN')}`}
                      </span>
                      <span className="text-[10px] text-editorial-charcoal-light">
                        Total: {typeof activeScenario.calculations.total_repaid !== 'number'
                          ? 'unavailable'
                          : `₹${activeScenario.calculations.total_repaid.toLocaleString('en-IN')}`}
                      </span>
                    </div>

                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-1">
                      <span className="text-[10px] text-editorial-charcoal-light block flex items-center space-x-1">
                        <Compass className="h-3 w-3 text-editorial-brass" />
                        <span>Spatial Demand</span>
                      </span>
                      <span className="text-base font-bold text-editorial-forest block">
                        {activeScenario.calculations.spatial_demand_status === 'COMPLETED'
                          ? activeScenario.calculations.spatial_demand_allocated?.toLocaleString('en-IN')
                          : 'Insufficient data'}
                      </span>
                      <span className="text-[10px] text-editorial-charcoal-light">
                        {activeScenario.calculations.spatial_demand_status === 'COMPLETED'
                          ? 'Huff Gravity Model'
                          : 'Zone demand, routing, facility attributes and decay assumption required'}
                      </span>
                    </div>

                    <div className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-1">
                      <span className="text-[10px] text-editorial-charcoal-light block">Feasibility Verdict</span>
                      <span className={`text-xs font-bold uppercase rounded px-2 py-0.5 inline-block ${
                        activeScenario.calculations.feasibility_status === 'FEASIBLE'
                          ? 'bg-editorial-forest/15 text-editorial-forest border border-editorial-forest/30'
                          : 'bg-editorial-copper/15 text-editorial-copper border border-editorial-copper/30'
                      }`}>
                        {activeScenario.calculations.feasibility_status}
                      </span>
                      <span className="text-[10px] text-editorial-charcoal-light block">
                        Target {activeScenario.calculations.target_monthly_units?.toLocaleString('en-IN') ?? 'unavailable'} units
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <section className="rounded border border-editorial-brass/40 bg-editorial-paper p-4 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-editorial-forest">
                      <Activity className="h-4 w-4 text-editorial-copper" />
                      <span>Reproducible Uncertainty & Sensitivity</span>
                    </div>
                    <p className="mt-1 max-w-3xl text-[11px] font-mono text-editorial-charcoal-light">
                      Supply the full monthly projection, distribution parameters, seed, quantiles, and convergence tolerances. Each result is saved with its ledger quantity IDs.
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={isSimulating || !isAuthenticated}
                    onClick={handleSimulate}
                    className="inline-flex shrink-0 items-center justify-center gap-2 rounded border border-editorial-forest bg-editorial-forest px-3 py-2 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors disabled:opacity-50"
                  >
                    <Activity className="h-3.5 w-3.5" />
                    <span>{isSimulating ? 'Sampling…' : 'Run Analysis'}</span>
                  </button>
                </div>

                <div className="grid gap-3 lg:grid-cols-2">
                  <label className="space-y-1 block">
                    <span className="text-[10px] font-mono text-editorial-charcoal-light">Explicit projection inputs (JSON)</span>
                    <textarea
                      value={simulationProjectionJson}
                      onChange={(event) => setSimulationProjectionJson(event.target.value)}
                      rows={7}
                      spellCheck={false}
                      aria-label="Explicit simulation projection JSON"
                      className="w-full resize-y rounded border border-editorial-brass/40 bg-editorial-ivory p-2.5 font-mono text-[10px] text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                    <span className="text-[9px] font-mono text-editorial-charcoal-light block">
                      Required fields: initial_quantity, monthly_growth_rate, seasonality_factors, price_per_unit_by_month, variable_cost_per_unit_by_month, operating_expenses_by_month, debt_service_by_month, taxes_by_month, other_payments_by_month, subsidy_cash_release_by_month, working_capital_need_by_month, opening_working_capital_need, equity, disbursed_loan, capex, days_inventory, days_receivable, days_payable.
                    </span>
                  </label>
                  <div className="space-y-3">
                    <label className="space-y-1 block">
                      <span className="text-[10px] font-mono text-editorial-charcoal-light">Distribution definitions (JSON array)</span>
                      <textarea
                        value={simulationDistributionsJson}
                        onChange={(event) => setSimulationDistributionsJson(event.target.value)}
                        rows={4}
                        spellCheck={false}
                        aria-label="Simulation distribution definitions JSON"
                        className="w-full resize-y rounded border border-editorial-brass/40 bg-editorial-ivory p-2.5 font-mono text-[10px] text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                      />
                      <span className="text-[9px] font-mono text-editorial-charcoal-light block">
                        Target paths use a field name or a 1-based monthly path such as price_per_unit_by_month.1. NORMAL requires mean and standard_deviation; UNIFORM requires low and high; TRIANGULAR requires left, mode, and right.
                      </span>
                    </label>
                    <label className="space-y-1 block">
                      <span className="text-[10px] font-mono text-editorial-charcoal-light">One-at-a-time sensitivity alternatives (JSON object)</span>
                      <textarea
                        value={simulationSensitivityJson}
                        onChange={(event) => setSimulationSensitivityJson(event.target.value)}
                        rows={3}
                        spellCheck={false}
                        aria-label="Sensitivity alternatives JSON"
                        className="w-full resize-y rounded border border-editorial-brass/40 bg-editorial-ivory p-2.5 font-mono text-[10px] text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                      />
                    </label>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {[
                    ['Seed', simulationSeed, setSimulationSeed],
                    ['Draw count', simulationSampleCount, setSimulationSampleCount],
                    ['Minimum draws for convergence', simulationMinimumCount, setSimulationMinimumCount],
                    ['Shortfall probability tolerance', simulationShortfallTolerance, setSimulationShortfallTolerance],
                  ].map(([label, value, setter]) => (
                    <label key={label as string} className="space-y-1 block">
                      <span className="text-[10px] font-mono text-editorial-charcoal-light block">{label as string}</span>
                      <input
                        type="number"
                        value={value as string}
                        onChange={(event) => (setter as (value: string) => void)(event.target.value)}
                        className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                      />
                    </label>
                  ))}
                  <label className="space-y-1 block">
                    <span className="text-[10px] font-mono text-editorial-charcoal-light block">Quantile levels (JSON array)</span>
                    <input
                      value={simulationQuantilesJson}
                      onChange={(event) => setSimulationQuantilesJson(event.target.value)}
                      aria-label="Quantile levels JSON"
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                  <label className="space-y-1 block sm:col-span-2 xl:col-span-3">
                    <span className="text-[10px] font-mono text-editorial-charcoal-light block">Metric convergence tolerances (JSON object)</span>
                    <input
                      value={simulationTolerancesJson}
                      onChange={(event) => setSimulationTolerancesJson(event.target.value)}
                      aria-label="Metric convergence tolerances JSON"
                      className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory py-1.5 px-2.5 text-xs font-mono text-editorial-charcoal focus:outline-none focus:border-editorial-copper"
                    />
                  </label>
                </div>

                {simulationError && (
                  <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-2.5 text-xs font-mono text-editorial-copper flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{simulationError}</span>
                  </div>
                )}

                {activeScenario.financialSimulation?.status === 'COMPLETED' && (
                  <div className="space-y-4 border-t border-editorial-brass/25 pt-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-editorial-charcoal-light">
                      <span>Run {activeScenario.financialSimulation.run_id} · PCG64 seed {activeScenario.financialSimulation.metadata.seed} · {activeScenario.financialSimulation.metadata.sample_count.toLocaleString('en-IN')} draws</span>
                      <span className={`rounded border px-2 py-0.5 font-bold ${activeScenario.financialSimulation.converged ? 'border-editorial-forest/30 bg-editorial-forest/10 text-editorial-forest' : 'border-editorial-copper/30 bg-editorial-copper/10 text-editorial-copper'}`}>
                        {activeScenario.financialSimulation.converged ? 'CONVERGED' : 'NOT CONVERGED'}
                      </span>
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      {Object.entries(activeScenario.financialSimulation.metrics).map(([metricName, metric]) => {
                        const band = getQuantileBand(metric);
                        return (
                          <div key={metricName} className="rounded border border-editorial-brass/30 bg-editorial-ivory p-3 space-y-2">
                            <div className="flex items-start justify-between gap-2">
                              <span className="font-mono text-[10px] uppercase tracking-wide text-editorial-charcoal-light">{metricName.replaceAll('_', ' ')}</span>
                              <span className="font-mono text-[9px] font-bold text-editorial-forest">{metric.converged ? 'CONVERGED' : 'OPEN'}</span>
                            </div>
                            <div className="font-mono text-lg font-bold text-editorial-forest" title={`Ledger quantity ${metric.mean_quantity_id}`}>
                              {formatSimulationMetric(metric.mean, metricName)}
                            </div>
                            {band && (
                              <div className="space-y-1.5">
                                <div className="relative h-2 rounded-full bg-editorial-brass/15" aria-label={`${metricName} quantile range`}>
                                  <div className="absolute top-0 h-2 rounded-full bg-editorial-forest/35" style={{ left: `${band.left}%`, width: `${band.width}%` }} />
                                  <div className="absolute -top-0.5 h-3 w-0.5 bg-editorial-copper" style={{ left: `${band.mean}%` }} />
                                </div>
                                <div className="flex justify-between font-mono text-[9px] text-editorial-charcoal-light">
                                  <span title={`Ledger quantity ${band.low.quantityId}`}>{formatSimulationMetric(band.low.value, metricName)}</span>
                                  <span title={`Ledger quantity ${band.high.quantityId}`}>{formatSimulationMetric(band.high.value, metricName)}</span>
                                </div>
                              </div>
                            )}
                            <div className="text-[9px] font-mono text-editorial-charcoal-light" title={`Ledger quantity ${metric.standard_error_quantity_id}`}>
                              Standard error: {formatSimulationMetric(metric.standard_error, metricName)}
                            </div>
                            <div className="space-y-0.5 border-t border-editorial-brass/15 pt-1">
                              {Object.entries(metric.quantiles).map(([level, point]) => (
                                <div key={level} className="flex justify-between gap-2 font-mono text-[9px] text-editorial-charcoal-light" title={`Ledger quantity ${point.quantity_id}`}>
                                  <span>q={level}</span>
                                  <span>{formatSimulationMetric(point.value, metricName)} · {point.quantity_id.slice(0, 8)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="rounded border border-editorial-copper/25 bg-editorial-copper/5 p-3 font-mono">
                      <div className="text-[10px] uppercase tracking-wide text-editorial-charcoal-light">Probability that projected cash falls below zero</div>
                      <div className="mt-1 text-lg font-bold text-editorial-copper" title={`Ledger quantity ${activeScenario.financialSimulation.cash_shortfall_probability.quantity_id}`}>
                        {(activeScenario.financialSimulation.cash_shortfall_probability.value * 100).toFixed(1)}%
                      </div>
                      <div className="text-[9px] text-editorial-charcoal-light" title={`Ledger quantity ${activeScenario.financialSimulation.cash_shortfall_probability.standard_error_quantity_id}`}>
                        Standard error {(activeScenario.financialSimulation.cash_shortfall_probability.standard_error * 100).toFixed(1)} percentage points · {activeScenario.financialSimulation.cash_shortfall_probability.quantity_id}
                      </div>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[580px] border-collapse font-mono text-[10px]">
                        <thead>
                          <tr className="border-b border-editorial-brass/30 text-left text-editorial-charcoal-light">
                            <th className="py-2 pr-3">Input changed</th>
                            <th className="py-2 pr-3">Alternative</th>
                            <th className="py-2 pr-3">Minimum cash</th>
                            <th className="py-2">Change vs baseline</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeScenario.financialSimulation.sensitivity.points.map((point, index) => {
                            const minimumCash = point.outputs.minimum_cash;
                            return (
                              <tr key={`${point.parameter}-${index}`} className="border-b border-editorial-brass/15 text-editorial-charcoal">
                                <td className="py-2 pr-3">{point.parameter}</td>
                                <td className="py-2 pr-3" title={point.parameter_quantity_id ? `Ledger quantity ${point.parameter_quantity_id}` : undefined}>{point.value.toLocaleString('en-IN')}</td>
                                <td className="py-2 pr-3" title={`Ledger quantity ${minimumCash.quantity_id}`}>{formatSimulationMetric(minimumCash.value, 'minimum_cash')}</td>
                                <td className="py-2" title={`Ledger quantity ${minimumCash.delta_quantity_id}`}>{formatSimulationMetric(minimumCash.delta, 'minimum_cash')} · {minimumCash.delta_quantity_id.slice(0, 8)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>

              {/* Decision Dossier Generation & Multi-Format Download Suite */}
              <div className="rounded border border-editorial-brass/40 bg-editorial-ivory p-4 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <span className="font-mono text-xs font-bold text-editorial-forest uppercase tracking-wider block">
                      Download Auditable Decision Dossier
                    </span>
                    <span className="text-[11px] font-mono text-editorial-charcoal-light">
                      Export verified empirical evidence and scenario models in standard formats.
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-semibold text-editorial-forest px-2 py-0.5 rounded bg-editorial-forest/10 border border-editorial-forest/20">
                    OWASP Sanitized
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 pt-1 font-mono text-xs">
                  <button
                    type="button"
                    disabled={downloadingFormat !== null}
                    onClick={() => handleDownloadDossier('json')}
                    className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest/40 bg-editorial-paper px-3 py-1.5 font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <FileCode className="h-3.5 w-3.5" />
                    <span>{downloadingFormat === 'json' ? 'Generating…' : 'JSON Dossier'}</span>
                  </button>

                  <button
                    type="button"
                    disabled={downloadingFormat !== null}
                    onClick={() => handleDownloadDossier('csv')}
                    className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest/40 bg-editorial-paper px-3 py-1.5 font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <FileSpreadsheet className="h-3.5 w-3.5" />
                    <span>{downloadingFormat === 'csv' ? 'Generating…' : 'CSV Matrix'}</span>
                  </button>

                  <button
                    type="button"
                    disabled={downloadingFormat !== null}
                    onClick={() => handleDownloadDossier('xlsx')}
                    className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest/40 bg-editorial-paper px-3 py-1.5 font-bold text-editorial-forest hover:bg-editorial-forest hover:text-editorial-ivory transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <FileSpreadsheet className="h-3.5 w-3.5" />
                    <span>{downloadingFormat === 'xlsx' ? 'Generating…' : 'Excel Workbook (.xlsx)'}</span>
                  </button>

                  <button
                    type="button"
                    disabled={downloadingFormat !== null}
                    onClick={() => handleDownloadDossier('pdf')}
                    className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest bg-editorial-forest px-3.5 py-1.5 font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer shadow-sm disabled:opacity-50"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    <span>{downloadingFormat === 'pdf' ? 'Generating…' : 'Publication PDF'}</span>
                  </button>
                </div>
              </div>

              {/* Epistemic Footer */}
              <div className="border-t border-editorial-brass/20 pt-3 text-[11px] font-mono text-editorial-charcoal-light flex items-center justify-between">
                <span>Handbook Part 10.3 • Sandboxed Floor 1 model calculations</span>
                <span className="text-editorial-forest font-semibold">PostgreSQL Epistemic Ledger</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
