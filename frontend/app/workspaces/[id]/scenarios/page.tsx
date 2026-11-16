'use client';
import { MotionButton } from '@/components/ui/motion-button';

import React, { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useParams } from 'next/navigation';
import { Activity, Award, CheckCircle2, GitCompareArrows, Play, Plus, RotateCcw, Save, Trash2, X } from 'lucide-react';
import { useToast } from '@/components/ui';
import { BusinessScenario, BusinessScenarioVersion, businessApi } from '../../../../lib/business-api';
import { formatINR } from '../../../../lib/money';

type FormValues = Record<string, string>;
const initialForm: FormValues = {
  name: '', description: '', horizon_months: '12', initial_quantity: '', monthly_volume_growth_pct: '',
  selling_price: '', variable_cost_per_unit: '', fixed_monthly_operating_expenses: '', opening_cash: '',
  monthly_debt_service: '', monthly_taxes: '', monthly_other_payments: '', monthly_subsidy_cash_release: '',
  monthly_working_capital_need: '', opening_working_capital_need: '', equity: '', disbursed_loan: '', capex: '', financing_mode: '',
  days_inventory: '', days_receivable: '', days_payable: '', annual_discount_rate_pct: '',
  loan_interest_rate_pct: '', loan_tenure_months: '', lease_payment_monthly: '',
  optimistic_growth_pct: '', optimistic_price: '', optimistic_unit_cost: '', optimistic_monthly_opex: '',
  pessimistic_growth_pct: '', pessimistic_price: '', pessimistic_unit_cost: '', pessimistic_monthly_opex: '',
};
const optionalNumbers = [
  'monthly_debt_service', 'monthly_taxes', 'monthly_other_payments', 'monthly_subsidy_cash_release',
  'monthly_working_capital_need', 'opening_working_capital_need', 'equity', 'disbursed_loan', 'capex',
  'days_inventory', 'days_receivable', 'days_payable', 'annual_discount_rate_pct',
  'loan_interest_rate_pct', 'loan_tenure_months', 'lease_payment_monthly',
];

function fieldLabel(key: string) {
  return key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function assumptionsFrom(values: FormValues) {
  const numeric = (key: string) => {
    const raw = values[key];
    const n = Number(raw);
    return isNaN(n) ? 0 : n;
  };
  const result: Record<string, any> = {
    horizon_months: Number(values.horizon_months || 12),
    initial_quantity: numeric('initial_quantity'),
    monthly_volume_growth_rate: numeric('monthly_volume_growth_pct') / 100,
    selling_price: numeric('selling_price'),
    variable_cost_per_unit: numeric('variable_cost_per_unit'),
    fixed_monthly_operating_expenses: numeric('fixed_monthly_operating_expenses'),
    opening_cash: numeric('opening_cash'),
  };
  optionalNumbers.forEach((key) => {
    const rawVal = values[key];
    const value = typeof rawVal === 'string' ? rawVal.trim() : '';
    if (value !== '' && !isNaN(Number(value))) {
      const outputKey = key === 'annual_discount_rate_pct' ? 'annual_discount_rate' : key;
      const divisor = ['annual_discount_rate_pct', 'loan_interest_rate_pct'].includes(key) ? 100 : 1;
      result[outputKey] = Number(value) / divisor;
    }
  });
  if (values.financing_mode) result.financing_mode = values.financing_mode;
  const cases: Record<string, Record<string, number>> = {};
  for (const caseName of ['optimistic', 'pessimistic']) {
    const overrides: Record<string, number> = {};
    const fields = [
      [`${caseName}_growth_pct`, 'monthly_volume_growth_rate', 0.01],
      [`${caseName}_price`, 'selling_price', 1],
      [`${caseName}_unit_cost`, 'variable_cost_per_unit', 1],
      [`${caseName}_monthly_opex`, 'fixed_monthly_operating_expenses', 1],
    ] as const;
    fields.forEach(([formKey, driver, divisor]) => {
      const rawVal = values[formKey];
      const value = typeof rawVal === 'string' ? rawVal.trim() : '';
      if (value !== '' && !isNaN(Number(value))) overrides[driver] = Number(value) / divisor;
    });
    if (Object.keys(overrides).length) cases[caseName] = overrides;
  }
  if (Object.keys(cases).length) result.cases = cases;
  return result;
}

function formFrom(assumptions?: Record<string, any>, name = '', description = ''): FormValues {
  const values: FormValues = { ...initialForm, name, description };
  if (!assumptions) return values;
  values.horizon_months = String(assumptions.horizon_months ?? '12');
  values.initial_quantity = String(assumptions.initial_quantity ?? '');
  values.monthly_volume_growth_pct = String(Number(assumptions.monthly_volume_growth_rate ?? 0) * 100);
  values.selling_price = String(assumptions.selling_price ?? '');
  values.variable_cost_per_unit = String(assumptions.variable_cost_per_unit ?? '');
  values.fixed_monthly_operating_expenses = String(assumptions.fixed_monthly_operating_expenses ?? '');
  values.opening_cash = String(assumptions.opening_cash ?? '');
  optionalNumbers.forEach((key) => {
    const target = key === 'annual_discount_rate_pct' ? 'annual_discount_rate' : key;
    if (assumptions[target] !== undefined) values[key] = String(Number(assumptions[target]) * (['annual_discount_rate_pct', 'loan_interest_rate_pct'].includes(key) ? 100 : 1));
  });
  values.financing_mode = assumptions.financing_mode ?? '';
  for (const caseName of ['optimistic', 'pessimistic']) {
    const overrides = assumptions.cases?.[caseName] ?? {};
    values[`${caseName}_growth_pct`] = overrides.monthly_volume_growth_rate === undefined ? '' : String(overrides.monthly_volume_growth_rate * 100);
    values[`${caseName}_price`] = overrides.selling_price === undefined ? '' : String(overrides.selling_price);
    values[`${caseName}_unit_cost`] = overrides.variable_cost_per_unit === undefined ? '' : String(overrides.variable_cost_per_unit);
    values[`${caseName}_monthly_opex`] = overrides.fixed_monthly_operating_expenses === undefined ? '' : String(overrides.fixed_monthly_operating_expenses);
  }
  return values;
}

function MoneyMetric({ label, value }: { label: string; value: unknown }) {
  return <div className="rounded-none bg-white p-3"><div className="text-xs text-slate-500">{label}</div><div className="mt-1 font-semibold text-[#0D0F17]">{formatINR(String(value ?? 0))}</div></div>;
}

export default function ScenarioLaboratoryPage() {
  const params = useParams();
  const businessId = params.id as string;
  const { toast } = useToast();
  const [scenarios, setScenarios] = useState<BusinessScenario[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [versions, setVersions] = useState<BusinessScenarioVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formMode, setFormMode] = useState<'create_scenario' | 'new_version'>('create_scenario');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [busyComparing, setBusyComparing] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  const [form, setForm] = useState<FormValues>(initialForm);
  const [comparisonIds, setComparisonIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<any>(null);
  const [iterations, setIterations] = useState('1000');
  const [seed, setSeed] = useState('');
  const [driver, setDriver] = useState('monthly_volume_growth_rate');
  const [distribution, setDistribution] = useState('NORMAL');
  const [distributionValues, setDistributionValues] = useState<Record<string, string>>({});
  const [run, setRun] = useState<any>(null);
  const [runHistory, setRunHistory] = useState<any[]>([]);
  const [busyRun, setBusyRun] = useState(false);

  const selected = useMemo(() => scenarios.find((item) => item.id === selectedId) ?? null, [scenarios, selectedId]);
  const activeVersion = useMemo(() => versions.find((item) => item.id === selectedVersionId) ?? versions[0] ?? null, [versions, selectedVersionId]);

  const loadScenarios = useCallback(async () => {
    setLoading(true);
    try {
      const items = await businessApi.listScenarios(businessId);
      setScenarios(items);
      setSelectedId((currentId) => currentId && !items.some((item) => item.id === currentId) ? '' : currentId);
    } catch (cause) {
      toast.error(`Could not load scenarios: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  }, [businessId, toast]);

  const loadVersions = useCallback(async (scenarioId: string) => {
    setVersions([]);
    setSelectedVersionId('');
    setRun(null);
    setRunHistory([]);
    if (!scenarioId) return;
    try {
      const [rows, runs] = await Promise.all([
        businessApi.listScenarioVersions(businessId, scenarioId),
        businessApi.listScenarioRuns(businessId, scenarioId),
      ]);
      setVersions(rows);
      setRunHistory(runs);
      setSelectedVersionId(rows[0]?.id ?? '');
    } catch (cause) {
      toast.error(`Could not load scenario versions: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    }
  }, [businessId, toast]);

  useEffect(() => { void loadScenarios(); }, [loadScenarios]);
  useEffect(() => { void loadVersions(selectedId); }, [loadVersions, selectedId]);

  function startNewScenario() {
    setFormMode('create_scenario');
    setForm({ ...initialForm });
    setShowForm(true);
  }

  function startNewVersion(version?: BusinessScenarioVersion) {
    setFormMode('new_version');
    setForm(version ? formFrom(version.assumptions, selected?.name ?? '', selected?.description ?? '') : { ...initialForm });
    setShowForm(true);
  }

  async function submitScenario(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      const assumptions = assumptionsFrom(form);
      if (formMode === 'create_scenario') {
        if (!form.name.trim()) throw new Error('Provide a scenario name.');
        const created = await businessApi.createScenario(businessId, {
          name: form.name.trim(),
          description: form.description.trim(),
          assumptions,
        });
        toast.success(`Scenario "${created.name}" created.`);
        setScenarios((current) => [created, ...current]);
        setSelectedId(created.id);
        await loadVersions(created.id);
      } else {
        if (!selected) throw new Error('No scenario selected to version.');
        const created = await businessApi.createScenarioVersion(businessId, selected.id, assumptions);
        toast.success(`New version created for "${selected.name}".`);
        setScenarios((current) => current.map((item) => item.id === selected.id ? created : item));
        await loadVersions(selected.id);
      }
      setShowForm(false);
    } catch (cause) {
      toast.error(`Scenario could not be saved: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  }

  async function runMonteCarlo() {
    if (!selected) return;
    const configNames = distribution === 'NORMAL' ? ['mean', 'std_dev'] : distribution === 'UNIFORM' ? ['min_val', 'max_val'] : distribution === 'TRIANGULAR' ? ['low', 'mode', 'high'] : ['min_val', 'mode', 'max_val'];
    if (configNames.some((key) => distributionValues[key]?.trim() === '')) {
      toast.error(`Enter all ${distribution.toLowerCase()} distribution parameters.`);
      return;
    }
    setBusyRun(true);
    try {
      const params: Record<string, number | string> = { distribution };
      configNames.forEach((key) => { params[key] = Number(distributionValues[key]); });
      if (distribution === 'PERT') params.lambda_param = 4;
      const result = await businessApi.runScenarioMonteCarlo(businessId, selected.id, {
        iterations: Number(iterations),
        ...(seed.trim() ? { random_seed: Number(seed) } : {}),
        distributions: { [driver]: params },
      });
      setRun(result);
    } catch (cause) {
      toast.error(`Simulation failed: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    } finally {
      setBusyRun(false);
    }
  }

  async function replay() {
    if (!run || !selected) return;
    setBusyRun(true);
    try {
      const result = await businessApi.replayScenarioRun(businessId, selected.id, run.id);
      toast.success(result.replayed ? 'Replay matched the saved result.' : 'Replay did not match.');
    } catch (cause) {
      toast.error(`Replay failed: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    } finally {
      setBusyRun(false);
    }
  }

  async function compare() {
    if (comparisonIds.length < 2 || comparisonIds.length > 5) return;
    setBusyComparing(true);
    try {
      const result = await businessApi.compareScenarioVersions(businessId, comparisonIds);
      setComparison(result);
    } catch (cause) {
      toast.error(`Comparison failed: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    } finally {
      setBusyComparing(false);
    }
  }

  async function handleDeleteScenario() {
    if (!selected) return;
    setDeleting(true);
    try {
      await businessApi.deleteScenario(businessId, selected.id);
      toast.success(`Scenario "${selected.name}" has been deleted.`);
      setShowDeleteModal(false);
      setComparison(null);
      setComparisonIds([]);
      const remainingScenarios = scenarios.filter((s) => s.id !== selected.id);
      setScenarios(remainingScenarios);
      setSelectedId(remainingScenarios[0]?.id ?? '');
    } catch (cause) {
      toast.error(`Could not delete scenario: ${cause instanceof Error ? cause.message : 'Unknown error'}`);
    } finally {
      setDeleting(false);
    }
  }

  const input = (key: string, options: { required?: boolean; step?: string; min?: string } = {}) => (
    <label key={key} className="block text-xs font-medium text-[#231412]">{fieldLabel(key)}{options.required && <span className="ml-1 text-[#C8281E]">*</span>}
      <input required={options.required} type="number" step={options.step ?? 'any'} min={options.min} value={form[key] ?? ''} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} className="mt-1 w-full rounded-lg border border-[#231412]/20 bg-white px-3 py-1.5 text-xs font-mono text-[#231412] focus:border-[#C8281E] focus:outline-none focus:ring-1 focus:ring-[#C8281E]" />
    </label>
  );

  const currentAnalysis = activeVersion?.analysis;
  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3"><div><div className="text-xs font-bold uppercase tracking-widest text-[#B76E4D]">Decision Intelligence</div><h1 className="text-2xl font-bold text-[#0D0F17]">Scenario Laboratory</h1><p className="mt-1 text-sm text-slate-500">Version explicit assumptions, compare cases, inspect sensitivities, and replay seeded simulations.</p></div><MotionButton onClick={() => startNewScenario()} className="inline-flex items-center gap-2 rounded-none bg-[#2B4EFF] px-4 py-2 text-sm font-semibold text-[#0D0F17]"><Plus className="h-4 w-4" /> New scenario</MotionButton></header>

      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        <aside className="space-y-3 rounded-none border border-black/[0.08]/10 bg-white p-4 shadow-sm"><div className="flex items-center justify-between"><h2 className="font-semibold text-[#0D0F17]">Saved scenarios</h2><MotionButton onClick={() => void loadScenarios()} className="text-xs underline">Refresh</MotionButton></div>
          {loading && <p className="text-sm text-slate-500">Loading…</p>}{!loading && scenarios.length === 0 && <p className="rounded-none bg-white p-3 text-sm text-slate-500">No scenarios saved in this workspace.</p>}
          <div className="space-y-2">{scenarios.map((scenario) => <MotionButton key={scenario.id} onClick={() => setSelectedId(scenario.id)} className={`w-full rounded-none border p-3 text-left ${selectedId === scenario.id ? 'border-black/[0.08] bg-[#2B4EFF]/5' : 'border-black/[0.08]/10 hover:border-[#F59E0B]'}`}><span className="block font-semibold text-[#0D0F17]">{scenario.name}</span><span className="mt-1 block text-xs text-slate-500">Version {scenario.current_version} · {scenario.description || 'No description'}</span></MotionButton>)}</div>
          {selected && (
            <div className="mt-4 border-t pt-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold uppercase tracking-wide text-slate-500">Immutable versions</h3>
                <span className="text-[11px] font-mono text-[#231412]/60">
                  {comparisonIds.length}/5 selected
                </span>
              </div>
              <div className="space-y-1.5">
                {versions.map((version) => {
                  const isCompared = comparisonIds.includes(version.id);
                  const isActive = selectedVersionId === version.id;
                  return (
                    <div
                      key={version.id}
                      className={`flex items-center justify-between rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
                        isActive ? 'border-[#231412] bg-[#231412]/5 font-semibold' : 'border-[#231412]/10 hover:border-[#231412]/30'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => setSelectedVersionId(version.id)}
                        className="flex-1 text-left text-xs text-[#231412]"
                      >
                        Version {version.version_number}
                        {isActive && <span className="ml-1.5 text-[10px] text-[#C8281E] font-bold">ACTIVE</span>}
                      </button>
                      <label className="flex items-center gap-1 cursor-pointer pl-2 border-l border-[#231412]/10">
                        <input
                          type="checkbox"
                          checked={isCompared}
                          onChange={(event) =>
                            setComparisonIds((current) =>
                              event.target.checked ? [...current, version.id] : current.filter((id) => id !== version.id)
                            )
                          }
                          aria-label={`Compare version ${version.version_number}`}
                          className="h-3.5 w-3.5 rounded border-[#231412]/30 text-[#C8281E] focus:ring-[#C8281E]"
                        />
                        <span className="text-[10px] text-[#231412]/70 font-mono">Compare</span>
                      </label>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 space-y-1.5">
                <MotionButton
                  disabled={comparisonIds.length < 2 || comparisonIds.length > 5 || busyComparing}
                  onClick={() => void compare()}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg border-2 border-[#231412] bg-[#231412] px-3 py-2 text-xs font-bold text-white disabled:opacity-40 hover:bg-[#3D2522] transition-colors"
                >
                  <GitCompareArrows className="h-3.5 w-3.5" />
                  {busyComparing ? 'Comparing…' : comparisonIds.length >= 2 ? `Compare ${comparisonIds.length} versions` : 'Compare selected versions'}
                </MotionButton>
                <div className="flex items-center justify-between text-[11px] px-0.5">
                  <span className="text-[#231412]/60 text-[10px]">
                    {comparisonIds.length < 2 ? 'Select 2 to 5 versions to compare' : `${comparisonIds.length} versions ready`}
                  </span>
                  {comparisonIds.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setComparisonIds([])}
                      className="text-[10px] font-bold text-[#C8281E] hover:underline"
                    >
                      Clear selection
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </aside>

        <div className="space-y-5">
          {selected && activeVersion ? <>
            <section className="rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold text-[#0D0F17]">{selected.name} · Version {activeVersion.version_number}</h2>
                  <p className="mt-1 text-xs text-slate-500">Snapshot {activeVersion.baseline_snapshot_hash.slice(0, 16)}… · {activeVersion.assumptions.horizon_months} month projection</p>
                </div>
                <div className="flex items-center gap-2">
                  <MotionButton
                    type="button"
                    onClick={() => setShowDeleteModal(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#C8281E]/30 bg-white px-3 py-2 text-xs font-bold text-[#C8281E] shadow-sm hover:bg-[#C8281E]/10 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete scenario
                  </MotionButton>
                  <MotionButton
                    type="button"
                    onClick={() => startNewVersion(activeVersion)}
                    className="inline-flex items-center gap-2 rounded-lg border border-[#231412]/20 bg-white px-3 py-2 text-xs font-bold text-[#231412] shadow-sm hover:border-[#231412] transition-colors"
                  >
                    <Save className="h-3.5 w-3.5" /> Save new version
                  </MotionButton>
                </div>
              </div>
              {currentAnalysis && <div className="mt-5 grid gap-4 md:grid-cols-3">{['base', 'optimistic', 'pessimistic'].map((caseName) => { const summary = currentAnalysis.cases[caseName]?.summary; return <div key={caseName} className="rounded-none border border-black/[0.08]/10 p-4"><div className="mb-3 text-sm font-bold capitalize text-[#0D0F17]">{caseName}</div><div className="grid grid-cols-2 gap-2">{summary && <><MoneyMetric label="Net profit" value={summary.total_net_profit} /><MoneyMetric label="Ending cash" value={summary.ending_cash} /><MoneyMetric label="NPV" value={summary.npv} /><div className="rounded-none bg-white p-3"><div className="text-xs text-slate-500">Minimum DSCR</div><div className="mt-1 font-semibold">{summary.minimum_dscr ?? 'Unavailable'}</div></div></>}</div></div>; })}</div>}
              <div className="mt-5"><h3 className="mb-2 text-sm font-semibold text-[#0D0F17]">Base case monthly trajectory</h3><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-xs"><thead><tr className="border-b text-slate-500"><th className="py-2">Month</th><th>Revenue</th><th>Net profit</th><th>Cash flow</th><th>Ending cash</th><th>DSCR</th></tr></thead><tbody>{(currentAnalysis?.cases.base.months ?? []).map((month: any) => <tr key={month.month} className="border-b border-black/[0.08]/5"><td className="py-2">{month.month}</td><td>{formatINR(String(month.revenue))}</td><td>{formatINR(String(month.net_profit))}</td><td>{formatINR(String(month.cash_flow))}</td><td>{formatINR(String(month.closing_cash))}</td><td>{month.dscr ?? '—'}</td></tr>)}</tbody></table></div></div>
              <div className="mt-5"><h3 className="mb-2 text-sm font-semibold text-[#0D0F17]">Sensitivity tornado · ±10% and ±20%</h3><div className="grid gap-2 md:grid-cols-2">{(currentAnalysis?.sensitivity_tornado ?? []).map((item: any) => <div key={item.driver} className="rounded-none bg-white p-3 text-xs"><div className="font-semibold">{fieldLabel(item.driver)}</div><div className="mt-1 text-slate-500">Largest net profit impact: {formatINR(String(item.max_net_profit_impact))}</div><div className="mt-2 flex flex-wrap gap-2">{item.variations.map((variation: any) => <span key={variation.change_pct} className="rounded-none bg-white px-2 py-1">{variation.change_pct}% · {formatINR(String(variation.total_net_profit))}</span>)}</div></div>)}</div></div>
            </section>

            <section className="rounded-none border border-black/[0.08]/10 bg-white p-5 shadow-sm"><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-[#B76E4D]" /><h2 className="font-bold text-[#0D0F17]">Seeded Monte Carlo</h2></div><p className="mt-1 text-xs text-slate-500">Choose one driver distribution. Omitted seed is generated and saved with the run.</p><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><label className="text-xs">Driver<select value={driver} onChange={(event) => setDriver(event.target.value)} className="mt-1 w-full rounded-none border px-2 py-2">{['monthly_volume_growth_rate', 'initial_quantity', 'selling_price', 'variable_cost_per_unit', 'fixed_monthly_operating_expenses'].map((item) => <option key={item} value={item}>{fieldLabel(item)}</option>)}</select></label><label className="text-xs">Distribution<select value={distribution} onChange={(event) => { setDistribution(event.target.value); setDistributionValues({}); }} className="mt-1 w-full rounded-none border px-2 py-2"><option>NORMAL</option><option>UNIFORM</option><option>TRIANGULAR</option><option>PERT</option></select></label><label className="text-xs">Iterations<input type="number" min="1" max="100000" value={iterations} onChange={(event) => setIterations(event.target.value)} className="mt-1 w-full rounded-none border px-3 py-2" /></label><label className="text-xs">Seed (optional)<input type="number" min="0" value={seed} onChange={(event) => setSeed(event.target.value)} className="mt-1 w-full rounded-none border px-3 py-2" /></label></div><div className="mt-3 grid gap-3 sm:grid-cols-3">{(distribution === 'NORMAL' ? ['mean', 'std_dev'] : distribution === 'UNIFORM' ? ['min_val', 'max_val'] : distribution === 'TRIANGULAR' ? ['low', 'mode', 'high'] : ['min_val', 'mode', 'max_val']).map((key) => <label key={key} className="text-xs">{fieldLabel(key)}<input type="number" step="any" value={distributionValues[key] ?? ''} onChange={(event) => setDistributionValues((current) => ({ ...current, [key]: event.target.value }))} className="mt-1 w-full rounded-none border px-3 py-2" /></label>)}</div><MotionButton onClick={() => void runMonteCarlo()} disabled={busyRun} className="mt-3 inline-flex items-center gap-2 rounded-none bg-[#2B4EFF] px-4 py-2 text-sm font-semibold text-[#0D0F17] disabled:opacity-50"><Play className="h-4 w-4" /> {busyRun ? 'Running…' : 'Run simulation'}</MotionButton>
              {run && <div className="mt-4 rounded-none bg-white p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div className="text-xs text-slate-500">Run {run.id} · seed {run.random_seed} · {run.iterations} iterations</div><MotionButton disabled={busyRun} onClick={() => void replay()} className="inline-flex items-center gap-2 rounded-none border px-3 py-2 text-xs font-semibold"><RotateCcw className="h-3.5 w-3.5" /> Replay saved run</MotionButton></div><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(run.metrics ?? run.result?.metrics ?? {}).map(([metric, stats]: [string, any]) => <div key={metric} className="rounded-none bg-white p-3"><div className="text-xs font-semibold text-[#0D0F17]">{fieldLabel(metric)}</div><div className="mt-1 text-xs text-slate-500">Mean {formatINR(String(stats.mean))} · SD {formatINR(String(stats.std_dev))}</div><div className="mt-1 text-[11px] text-slate-500">P10 {formatINR(String(stats.p10))} · P50 {formatINR(String(stats.p50))} · P90 {formatINR(String(stats.p90))}</div></div>)}</div><div className="mt-3 text-xs">Probability of loss: <b>{((run.probability_of_loss ?? run.result?.probability_of_loss ?? 0) * 100).toFixed(2)}%</b> · Cash shortfall: <b>{((run.probability_of_cash_shortfall ?? run.result?.probability_of_cash_shortfall ?? 0) * 100).toFixed(2)}%</b></div></div>}
              {runHistory.length > 0 && <div className="mt-4 border-t pt-4"><h3 className="mb-2 text-sm font-semibold text-[#0D0F17]">Saved simulation runs</h3><div className="space-y-2">{runHistory.map((saved) => <div key={saved.id} className="flex flex-wrap items-center justify-between gap-2 rounded-none border border-black/[0.08]/10 p-3"><MotionButton onClick={() => setRun(saved)} className="text-left text-xs"><span className="block font-semibold">{saved.created_at ? new Date(saved.created_at).toLocaleString() : 'Saved run'} · Version {versions.find((item) => item.id === saved.scenario_version_id)?.version_number ?? '—'}</span><span className="text-slate-500">Seed {saved.random_seed} · {saved.iterations} iterations</span></MotionButton><MotionButton disabled={busyRun} onClick={async () => { setRun(saved); setBusyRun(true); try { const replayResult = await businessApi.replayScenarioRun(businessId, selected.id, saved.id); toast.success(replayResult.replayed ? 'Replay matched the saved result.' : 'Replay did not match.'); } catch (cause) { toast.error(`Replay failed: ${cause instanceof Error ? cause.message : 'Unknown error'}`); } finally { setBusyRun(false); } }} className="rounded-none border px-3 py-1.5 text-xs">Replay</MotionButton></div>)}</div></div>}
            </section>
          </> : <div className="rounded-none border border-dashed border-black/[0.08]/25 bg-white/70 p-10 text-center text-sm text-slate-500">Choose a saved scenario to inspect its immutable versions, projection, and simulations.</div>}
        </div>
      </div>

      {comparison && (
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border-2 border-[#231412] bg-[#FAF7F2] p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#231412] text-white">
              <GitCompareArrows className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-black text-[#231412]">
                Version Comparison Active ({comparison.versions?.length ?? 0} versions evaluated)
              </div>
              <p className="text-xs text-[#231412]/70">
                Direct side-by-side metrics across Base, Optimistic, and Pessimistic cases.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <MotionButton
              type="button"
              onClick={() => setComparison({ ...comparison })}
              className="rounded-lg border-2 border-[#231412] bg-[#231412] px-4 py-2 text-xs font-bold text-white hover:bg-[#3D2522] transition-colors"
            >
              View Full Comparison
            </MotionButton>
            <MotionButton
              type="button"
              onClick={() => {
                setComparison(null);
                setComparisonIds([]);
              }}
              className="rounded-lg border border-[#C8281E]/30 bg-white px-3.5 py-2 text-xs font-bold text-[#C8281E] hover:bg-[#C8281E]/10 transition-colors"
            >
              Clear
            </MotionButton>
          </div>
        </section>
      )}

      {mounted && showForm && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#231412]/60 p-4 sm:p-6 backdrop-blur-sm">
          <form
            onSubmit={submitScenario}
            className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border-2 border-[#231412] bg-[#FAF7F2] shadow-2xl overflow-hidden"
          >
            {/* Pinned Sticky Header */}
            <div className="flex shrink-0 items-center justify-between border-b-2 border-[#231412] bg-[#FAF7F2] px-6 py-4">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-[#C8281E]">
                  Scenario Modeling Studio
                </div>
                <h2 className="text-xl font-black text-[#231412]">
                  {formMode === 'create_scenario' ? 'Create a New Scenario' : `Save a New Version · ${selected?.name ?? ''}`}
                </h2>
                <p className="mt-0.5 text-xs text-[#231412]/70">
                  Only supplied assumptions enter the simulation model. Blank optional finance drivers are treated as zero.
                </p>
              </div>
              <MotionButton
                type="button"
                onClick={() => setShowForm(false)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#231412]/20 bg-white px-3.5 py-1.5 text-xs font-bold text-[#231412] shadow-sm hover:border-[#C8281E] hover:text-[#C8281E] transition-colors"
              >
                ✕ Close
              </MotionButton>
            </div>

            {/* Scrollable Form Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-white">
              {formMode === 'create_scenario' && (
                <div className="grid gap-4 sm:grid-cols-2 rounded-xl border border-[#231412]/15 bg-[#FAF7F2]/50 p-4">
                  <label className="text-xs font-bold text-[#231412]">
                    Scenario Name <span className="text-[#C8281E]">*</span>
                    <input
                      required
                      placeholder="e.g. Q4 Capacity Expansion"
                      value={form.name}
                      onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                      className="mt-1 w-full rounded-lg border border-[#231412]/20 bg-white px-3 py-2 text-xs font-sans text-[#231412] focus:border-[#C8281E] focus:outline-none focus:ring-1 focus:ring-[#C8281E]"
                    />
                  </label>
                  <label className="text-xs font-bold text-[#231412]">
                    Description
                    <input
                      placeholder="e.g. Evaluating expansion capex and working capital impact"
                      value={form.description}
                      onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                      className="mt-1 w-full rounded-lg border border-[#231412]/20 bg-white px-3 py-2 text-xs font-sans text-[#231412] focus:border-[#C8281E] focus:outline-none focus:ring-1 focus:ring-[#C8281E]"
                    />
                  </label>
                </div>
              )}

              <div className="rounded-xl border border-[#231412]/15 bg-[#FAF7F2]/30 p-4">
                <div className="flex items-center justify-between mb-3 border-b border-[#231412]/10 pb-2">
                  <h3 className="text-sm font-black text-[#231412] uppercase tracking-wide">
                    Base Case Operational Assumptions
                  </h3>
                  <span className="text-[11px] text-[#231412]/60 font-mono">Core drivers required</span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <label className="block text-xs font-medium text-[#231412]">
                    Horizon Months <span className="text-[#C8281E]">*</span>
                    <select
                      value={form.horizon_months}
                      onChange={(event) => setForm((current) => ({ ...current, horizon_months: event.target.value }))}
                      className="mt-1 w-full rounded-lg border border-[#231412]/20 bg-white px-3 py-2 text-xs font-mono text-[#231412] focus:border-[#C8281E] focus:outline-none focus:ring-1 focus:ring-[#C8281E]"
                    >
                      <option value="12">12 months</option>
                      <option value="24">24 months</option>
                      <option value="36">36 months</option>
                    </select>
                  </label>
                  {input('initial_quantity', { required: true, min: '0' })}
                  {input('monthly_volume_growth_pct', { required: true })}
                  {input('selling_price', { required: true, min: '0' })}
                  {input('variable_cost_per_unit', { required: true, min: '0' })}
                  {input('fixed_monthly_operating_expenses', { required: true, min: '0' })}
                  {input('opening_cash', { required: true, min: '0' })}
                </div>
                <p className="mt-3 text-[11px] text-[#231412]/60 italic">
                  Growth and discount rates are entered as percentages (e.g. 5 for 5%). Monetary figures use the workspace currency.
                </p>
              </div>

              <div className="rounded-xl border border-[#231412]/15 bg-[#FAF7F2]/30 p-4">
                <div className="flex items-center justify-between mb-3 border-b border-[#231412]/10 pb-2">
                  <h3 className="text-sm font-black text-[#231412] uppercase tracking-wide">
                    Finance & Working Capital Levers
                  </h3>
                  <span className="text-[11px] text-[#231412]/60 font-mono">Optional levers (default: 0)</span>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <label className="block text-xs font-medium text-[#231412]">
                    Financing Mode
                    <select
                      value={form.financing_mode}
                      onChange={(event) => setForm((current) => ({ ...current, financing_mode: event.target.value }))}
                      className="mt-1 w-full rounded-lg border border-[#231412]/20 bg-white px-3 py-2 text-xs font-mono text-[#231412] focus:border-[#C8281E] focus:outline-none focus:ring-1 focus:ring-[#C8281E]"
                    >
                      <option value="">Not specified</option>
                      <option value="OWN_CAPITAL">Own capital</option>
                      <option value="LOAN">Loan</option>
                      <option value="LEASE">Lease</option>
                      <option value="MIXED">Mixed</option>
                    </select>
                  </label>
                  {optionalNumbers.map((key) => input(key, key === 'loan_tenure_months' ? { step: '1', min: '1' } : {}))}
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {(['optimistic', 'pessimistic'] as const).map((caseName) => (
                  <div key={caseName} className="rounded-xl border border-[#231412]/15 bg-[#FAF7F2]/40 p-4">
                    <h3 className="mb-3 text-sm font-black capitalize text-[#231412] flex items-center justify-between">
                      <span>{caseName} Stress Case Overrides</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${caseName === 'optimistic' ? 'bg-[#15803D]/10 text-[#15803D]' : 'bg-[#C8281E]/10 text-[#C8281E]'}`}>
                        {caseName.toUpperCase()}
                      </span>
                    </h3>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {input(`${caseName}_growth_pct`)}
                      {input(`${caseName}_price`)}
                      {input(`${caseName}_unit_cost`)}
                      {input(`${caseName}_monthly_opex`)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Pinned Sticky Footer */}
            <div className="flex shrink-0 items-center justify-end gap-3 border-t-2 border-[#231412] bg-[#FAF7F2] px-6 py-4">
              <MotionButton
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-lg border-2 border-[#231412]/20 bg-white px-4 py-2 text-xs font-bold text-[#231412] hover:bg-slate-100 transition-colors"
              >
                Cancel
              </MotionButton>
              <MotionButton
                disabled={saving}
                className="inline-flex items-center gap-2 rounded-lg border-2 border-[#231412] bg-[#C8281E] px-5 py-2 text-xs font-bold text-white shadow hover:bg-[#A82018] disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving…' : formMode === 'create_scenario' ? 'Save Scenario' : 'Create Immutable Version'}
              </MotionButton>
            </div>
          </form>
        </div>,
        document.body
      )}

      {/* Delete Confirmation Modal */}
      {mounted && showDeleteModal && selected && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#231412]/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border-2 border-[#231412] bg-[#FAF7F2] p-6 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#C8281E]/10 text-[#C8281E]">
                <Trash2 className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-lg font-black text-[#231412]">Delete Scenario</h3>
                <p className="text-xs text-[#231412]/70">Permanent workspace deletion</p>
              </div>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-[#231412]/80">
              Are you sure you want to permanently delete <strong>&ldquo;{selected.name}&rdquo;</strong>?
              All {versions.length} immutable version{versions.length === 1 ? '' : 's'}, financial projections, and saved simulation runs will be removed immediately.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <MotionButton
                type="button"
                disabled={deleting}
                onClick={() => setShowDeleteModal(false)}
                className="rounded-lg border border-[#231412]/20 bg-white px-4 py-2 text-xs font-bold text-[#231412] hover:bg-slate-100 transition-colors"
              >
                Cancel
              </MotionButton>
              <MotionButton
                type="button"
                disabled={deleting}
                onClick={() => void handleDeleteScenario()}
                className="inline-flex items-center gap-2 rounded-lg border-2 border-[#C8281E] bg-[#C8281E] px-4 py-2 text-xs font-bold text-white shadow hover:bg-[#A82018] disabled:opacity-50 transition-colors"
              >
                {deleting ? 'Deleting…' : 'Yes, Delete Scenario'}
              </MotionButton>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Comparison Modal */}
      {mounted && comparison && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#231412]/60 p-4 sm:p-6 backdrop-blur-sm">
          <div className="flex max-h-[92vh] w-full max-w-6xl flex-col rounded-2xl border-2 border-[#231412] bg-[#FAF7F2] shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex shrink-0 items-center justify-between border-b-2 border-[#231412] bg-[#FAF7F2] px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#231412] text-white">
                  <GitCompareArrows className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-[#C8281E]">
                    Side-by-Side Model Evaluation
                  </div>
                  <h2 className="text-xl font-black text-[#231412]">
                    Scenario Version Comparison
                  </h2>
                  <p className="mt-0.5 text-xs text-[#231412]/70">
                    Comparing {comparison.versions?.length ?? 0} immutable versions across Base, Optimistic, and Pessimistic cases.
                  </p>
                </div>
              </div>
              <MotionButton
                type="button"
                onClick={() => setComparison(null)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#231412]/20 bg-white px-3.5 py-1.5 text-xs font-bold text-[#231412] shadow-sm hover:border-[#C8281E] hover:text-[#C8281E] transition-colors"
              >
                <X className="h-4 w-4" /> Close
              </MotionButton>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-white">
              <div
                className="grid gap-4"
                style={{
                  gridTemplateColumns: `repeat(${Math.min(Math.max(comparison.versions.length, 1), 4)}, minmax(240px, 1fr))`,
                }}
              >
                {comparison.versions.map((item: any, idx: number) => {
                  const base = item.cases?.base ?? {};
                  const opt = item.cases?.optimistic ?? {};
                  const pess = item.cases?.pessimistic ?? {};
                  const allNpvs = comparison.versions.map((v: any) => v.cases?.base?.npv ?? -Infinity);
                  const maxNpv = Math.max(...allNpvs);
                  const isTopNpv = base.npv === maxNpv && comparison.versions.length > 1;

                  return (
                    <div
                      key={item.version_id || idx}
                      className={`flex flex-col rounded-xl border-2 p-4 transition-all ${
                        isTopNpv
                          ? 'border-[#15803D] bg-[#15803D]/[0.02] shadow-md ring-2 ring-[#15803D]/20'
                          : 'border-[#231412]/15 bg-[#FAF7F2]/30'
                      }`}
                    >
                      {/* Version Card Header */}
                      <div className="border-b border-[#231412]/10 pb-3">
                        <div className="flex items-center justify-between">
                          <span className="rounded bg-[#231412] px-2 py-0.5 text-[10px] font-bold text-white uppercase">
                            Version {item.version_number}
                          </span>
                          {isTopNpv && (
                            <span className="flex items-center gap-1 text-[10px] font-black text-[#15803D] bg-[#15803D]/10 px-2 py-0.5 rounded-full">
                              <Award className="h-3 w-3" /> TOP NPV
                            </span>
                          )}
                        </div>
                        <h3 className="mt-2 text-sm font-black text-[#231412] truncate" title={item.scenario_name}>
                          {item.scenario_name || 'Scenario'}
                        </h3>
                        <p className="text-[10px] font-mono text-[#231412]/60 truncate" title={item.baseline_snapshot_hash}>
                          Hash: {item.baseline_snapshot_hash?.slice(0, 12)}…
                        </p>
                      </div>

                      {/* Base Case Metrics */}
                      <div className="mt-4 space-y-2 flex-1">
                        <div className="text-[11px] font-black uppercase tracking-wider text-[#231412]">
                          Base Case Trajectory
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="rounded-lg border border-[#231412]/10 bg-white p-2.5">
                            <span className="block text-[10px] text-[#231412]/60">Net Profit</span>
                            <span className="mt-0.5 block text-xs font-black text-[#231412]">
                              {formatINR(String(base.total_net_profit ?? 0))}
                            </span>
                          </div>
                          <div className="rounded-lg border border-[#231412]/10 bg-white p-2.5">
                            <span className="block text-[10px] text-[#231412]/60">Ending Cash</span>
                            <span className="mt-0.5 block text-xs font-black text-[#231412]">
                              {formatINR(String(base.ending_cash ?? 0))}
                            </span>
                          </div>
                          <div className="rounded-lg border border-[#231412]/10 bg-white p-2.5">
                            <span className="block text-[10px] text-[#231412]/60">NPV (Discounted)</span>
                            <span className={`mt-0.5 block text-xs font-black ${isTopNpv ? 'text-[#15803D]' : 'text-[#231412]'}`}>
                              {formatINR(String(base.npv ?? 0))}
                            </span>
                          </div>
                          <div className="rounded-lg border border-[#231412]/10 bg-white p-2.5">
                            <span className="block text-[10px] text-[#231412]/60">Min DSCR</span>
                            <span className="mt-0.5 block text-xs font-black text-[#231412]">
                              {base.minimum_dscr != null ? `${base.minimum_dscr}x` : '—'}
                            </span>
                          </div>
                        </div>

                        {/* Revenue & Cash Flow details */}
                        <div className="rounded-lg border border-[#231412]/10 bg-white p-2.5 space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-[#231412]/60">Total Revenue:</span>
                            <span className="font-bold text-[#231412]">{formatINR(String(base.total_revenue ?? 0))}</span>
                          </div>
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-[#231412]/60">Min Cash:</span>
                            <span className="font-bold text-[#231412]">{formatINR(String(base.minimum_cash ?? 0))}</span>
                          </div>
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-[#231412]/60">Cash Conv. Cycle:</span>
                            <span className="font-mono text-[#231412]">{base.cash_conversion_cycle_days ?? 0} days</span>
                          </div>
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-[#231412]/60">First Shortfall:</span>
                            <span className={`font-bold ${base.first_shortfall_month ? 'text-[#C8281E]' : 'text-[#15803D]'}`}>
                              {base.first_shortfall_month ? `Month ${base.first_shortfall_month}` : 'None'}
                            </span>
                          </div>
                        </div>

                        {/* Stress Cases */}
                        <div className="pt-2 border-t border-[#231412]/10 space-y-2">
                          <div className="text-[11px] font-black uppercase tracking-wider text-[#231412]">
                            Stress Sensitivity
                          </div>
                          <div className="rounded-lg border border-[#15803D]/20 bg-[#15803D]/5 p-2 text-xs">
                            <span className="block text-[10px] font-bold text-[#15803D] uppercase">Optimistic Case</span>
                            <div className="mt-1 flex items-center justify-between text-[11px]">
                              <span>Net Profit:</span>
                              <span className="font-bold">{formatINR(String(opt.total_net_profit ?? 0))}</span>
                            </div>
                            <div className="flex items-center justify-between text-[11px]">
                              <span>NPV:</span>
                              <span className="font-bold">{formatINR(String(opt.npv ?? 0))}</span>
                            </div>
                          </div>
                          <div className="rounded-lg border border-[#C8281E]/20 bg-[#C8281E]/5 p-2 text-xs">
                            <span className="block text-[10px] font-bold text-[#C8281E] uppercase">Pessimistic Case</span>
                            <div className="mt-1 flex items-center justify-between text-[11px]">
                              <span>Net Profit:</span>
                              <span className="font-bold">{formatINR(String(pess.total_net_profit ?? 0))}</span>
                            </div>
                            <div className="flex items-center justify-between text-[11px]">
                              <span>NPV:</span>
                              <span className="font-bold">{formatINR(String(pess.npv ?? 0))}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Footer */}
            <div className="flex shrink-0 items-center justify-between border-t-2 border-[#231412] bg-[#FAF7F2] px-6 py-4">
              <span className="text-xs text-[#231412]/70 font-mono">
                {comparison.versions?.length} versions evaluated side-by-side
              </span>
              <MotionButton
                type="button"
                onClick={() => setComparison(null)}
                className="rounded-lg border-2 border-[#231412] bg-[#231412] px-5 py-2 text-xs font-bold text-white hover:bg-[#3D2522] transition-colors"
              >
                Close Comparison
              </MotionButton>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
