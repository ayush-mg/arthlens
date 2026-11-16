'use client';
import { MotionButton } from '@/components/ui/motion-button';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import {
  TrendingUp,
  Scale,
  Clock,
  PieChart,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  FileDown,
} from 'lucide-react';
import {
  businessApi,
  ProfitAndLossStatement,
  CashFlowStatement,
  WorkingCapitalAnalysis,
  AgeingAnalysis,
  BreakEvenAnalysis,
  BusinessHealthScore,
} from '../../../../lib/business-api';
import { downloadAuthenticatedReport } from '../../../../lib/business-api';
import { formatINR } from '../../../../lib/money';
import { useToast } from '@/components/ui';

export default function FinancialIntelligencePage() {
  const { toast } = useToast();
  const params = useParams();
  const businessId = params.id as string;

  const [activeTab, setActiveTab] = useState<'PNL' | 'CASHFLOW' | 'WORKING_CAPITAL' | 'AGEING' | 'BREAKEVEN' | 'HEALTH'>('PNL');
  const [pnl, setPnl] = useState<ProfitAndLossStatement | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlowStatement | null>(null);
  const [workingCapital, setWorkingCapital] = useState<WorkingCapitalAnalysis | null>(null);
  const [ageing, setAgeing] = useState<AgeingAnalysis | null>(null);
  const [breakEven, setBreakEven] = useState<BreakEvenAnalysis | null>(null);
  const [health, setHealth] = useState<BusinessHealthScore | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAllAnalytics() {
      try {
        const [pnlRes, cfRes, wcRes, ageRes, beRes, hlRes] = await Promise.all([
          businessApi.getPnL(businessId).catch(() => null),
          businessApi.getCashFlow(businessId).catch(() => null),
          businessApi.getWorkingCapital(businessId).catch(() => null),
          businessApi.getAgeing(businessId).catch(() => null),
          businessApi.getBreakEven(businessId).catch(() => null),
          businessApi.getHealthScore(businessId).catch(() => null),
        ]);
        setPnl(pnlRes);
        setCashFlow(cfRes);
        setWorkingCapital(wcRes);
        setAgeing(ageRes);
        setBreakEven(beRes);
        setHealth(hlRes);
      } catch (err) {
        console.error('Failed to load financial intelligence metrics', err);
      } finally {
        setLoading(false);
      }
    }
    loadAllAnalytics();
  }, [businessId]);

  const formatCurrency = (val: number | string | undefined | null) => {
    if (val === undefined || val === null) return '₹0.00';
    return formatINR(val);
  };

  const formatPercent = (val: number | undefined | null) => {
    if (val === undefined || val === null) return '0.0%';
    return `${Number(val).toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-3 text-slate-500">
          <div className="w-5 h-5 border-2 border-black/[0.08] border-t-transparent rounded-none animate-spin" />
          <span className="text-sm font-medium">Computing deterministic financial statements...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-2 border-b border-black/[0.08]/10">
        <div>
          <h1 className="text-2xl font-bold text-[#0D0F17]">Financial Intelligence Engine</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Deterministic P&L, multi-stream Cash Flow, solvency ratios, ageing buckets, and 5-pillar health.
          </p>
        </div>

        <MotionButton
          type="button"
          onClick={() => downloadAuthenticatedReport(
            businessApi.getDossierPdfUrl(businessId), `arthlens-dossier-${businessId}.pdf`,
          ).catch((err: Error) => toast.error(`Report download failed: ${err.message}`))}
          className="flex items-center space-x-1.5 px-3.5 py-2 rounded-none bg-[#2B4EFF] text-[#0D0F17] text-xs font-semibold hover:bg-[#E9E8E2] transition-all shadow-sm"
        >
          <FileDown className="w-4 h-4 text-[#F59E0B]" />
          <span>Export Complete Dossier (PDF)</span>
        </MotionButton>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-black/[0.08]/10 pb-1 overflow-x-auto">
        {[
          { key: 'PNL', label: 'Profit & Loss', icon: TrendingUp },
          { key: 'CASHFLOW', label: 'Cash Flow', icon: Scale },
          { key: 'WORKING_CAPITAL', label: 'Working Capital & Solvency', icon: PieChart },
          { key: 'AGEING', label: 'Ageing Buckets', icon: Clock },
          { key: 'BREAKEVEN', label: 'Break-Even & Safety', icon: CheckCircle2 },
          { key: 'HEALTH', label: '5-Pillar Health Score', icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <MotionButton
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`px-4 py-2 text-xs font-bold rounded-none transition-all flex items-center space-x-2 whitespace-nowrap ${
                isActive ? 'bg-[#2B4EFF] text-[#0D0F17] shadow-sm' : 'text-slate-500 hover:bg-white'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </MotionButton>
          );
        })}
      </div>

      {/* Tab 1: P&L */}
      {activeTab === 'PNL' && pnl && (
        <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0D0F17]">Statement of Profit and Loss</h2>
            <span className="text-xs text-slate-500">Accounting Period to Date</span>
          </div>

          {pnl.data_quality_warnings.length > 0 && (
            <div role="status" className="rounded-none border border-[#F59E0B]/40 bg-[#F59E0B]/10 p-3 text-sm text-[#F59E0B]">
              <p className="font-semibold">Some historical figures need reconciliation</p>
              <ul className="mt-1 list-disc pl-5">
                {pnl.data_quality_warnings.map((warning, index) => <li key={`${index}-${warning}`}>{warning}</li>)}
              </ul>
            </div>
          )}

          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 text-slate-500">
              <span>Sales (excluding output tax)</span>
              <span>{formatCurrency(pnl.gross_sales)}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 text-slate-500">
              <span>Sales returns</span>
              <span>- {formatCurrency(pnl.sales_returns)}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 text-slate-500">
              <span>Other income</span>
              <span>{formatCurrency(pnl.direct_income)}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 font-bold text-[#0D0F17]">
              <span>Total revenue</span>
              <span>{formatCurrency(pnl.total_revenue)}</span>
            </div>

            {/* COGS */}
            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 text-slate-500">
              <span className="pl-4">Cost of Goods Sold (Raw materials & inventory WAC)</span>
              <span>- {formatCurrency(pnl.cost_of_goods_sold)}</span>
            </div>

            {/* Gross Profit */}
            <div className="flex justify-between py-2.5 bg-white px-3 rounded-none font-bold text-[#10B981]">
              <span>Gross Profit (Margin: {formatPercent(pnl.gross_margin_percent)})</span>
              <span>{formatCurrency(pnl.gross_profit)}</span>
            </div>

            {/* OPEX */}
            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 text-slate-500">
              <span className="pl-4">Operating Expenses (Salaries, rent, utilities, misc)</span>
              <span>- {formatCurrency(pnl.total_operating_expenses)}</span>
            </div>

            {/* EBITDA */}
            <div className="flex justify-between py-2 border-b border-black/[0.08]/10 font-bold text-[#0D0F17]">
              <span>Operating Profit ({formatPercent(pnl.operating_margin_percent)})</span>
              <span>{formatCurrency(pnl.operating_profit_ebitda)}</span>
            </div>

            {/* Net Profit */}
            <div className="flex justify-between py-3 bg-[#2B4EFF] text-[#0D0F17] px-4 rounded-none font-bold text-base shadow-sm">
              <span>Net Profit (Net Margin: {formatPercent(pnl.net_margin_percent)})</span>
              <span>{formatCurrency(pnl.net_profit)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Cash Flow */}
      {activeTab === 'CASHFLOW' && cashFlow && (
        <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0D0F17]">Multi-Stream Cash Flow Statement</h2>
            <span className="text-xs text-slate-500">Deterministic Reconciliation</span>
          </div>

          <div className="space-y-4 text-sm">
            {/* Operating */}
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-2">
              <div className="font-bold text-[#0D0F17] text-xs uppercase tracking-wider">
                1. Operating Activities
              </div>
              <div className="flex justify-between text-xs text-slate-500">
                <span>Customer Cash Collections & Direct Receipts</span>
                <span className="font-semibold text-[#10B981]">+{formatCurrency(cashFlow.operating_cash_inflow)}</span>
              </div>
              <div className="flex justify-between text-xs text-slate-500">
                <span>Supplier Payments & Direct Operating Outflows</span>
                <span className="font-semibold text-[#B76E4D]">-{formatCurrency(cashFlow.operating_cash_outflow)}</span>
              </div>
              <div className="flex justify-between font-bold text-xs pt-2 border-t border-black/[0.08]/10 text-[#0D0F17]">
                <span>Net Cash from Operating Activities</span>
                <span>{formatCurrency(cashFlow.net_operating_cash_flow)}</span>
              </div>
            </div>

            {/* Investing */}
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-2">
              <div className="font-bold text-[#0D0F17] text-xs uppercase tracking-wider">
                2. Investing Activities
              </div>
              <div className="flex justify-between text-xs text-slate-500">
                <span>Capital Equipment & Machine Purchases</span>
                <span>{formatCurrency(cashFlow.investing_cash_flow)}</span>
              </div>
            </div>

            {/* Financing */}
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-2">
              <div className="font-bold text-[#0D0F17] text-xs uppercase tracking-wider">
                3. Financing Activities
              </div>
              <div className="flex justify-between text-xs text-slate-500">
                <span>Loan Disbursals, Repayments, & Equity Infusions</span>
                <span>{formatCurrency(cashFlow.financing_cash_flow)}</span>
              </div>
            </div>

            {/* Net Change */}
            <div className="p-4 rounded-none bg-[#2B4EFF] text-[#0D0F17] flex items-center justify-between font-bold shadow-sm">
              <div>
                <div className="text-xs uppercase text-[#F59E0B]">Net Change in Cash Position</div>
                <div className="text-lg">{formatCurrency(cashFlow.net_change_in_cash)}</div>
              </div>
              <div className="text-right text-xs">
                <div>Opening: {formatCurrency(cashFlow.opening_cash_balance)}</div>
                <div className="text-[#F59E0B] font-bold">Closing: {formatCurrency(cashFlow.closing_cash_balance)}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Working Capital */}
      {activeTab === 'WORKING_CAPITAL' && workingCapital && (
        <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0D0F17]">Working Capital & Solvency Ratios</h2>
            <span
              className={`px-3 py-1 rounded-none text-xs font-bold ${
                workingCapital.solvency_health === 'STRONG'
                  ? 'bg-[#10B981]/10 text-[#10B981]'
                  : workingCapital.solvency_health === 'ADEQUATE'
                  ? 'bg-[#F59E0B]/10 text-[#F59E0B]'
                  : 'bg-[#F59E0B]/10 text-[#F59E0B]'
              }`}
            >
              Solvency: {workingCapital.solvency_health}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Current Assets */}
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-2 text-xs">
              <div className="font-bold text-[#0D0F17] uppercase">Current Assets</div>
              <div className="flex justify-between">
                <span>Cash & Bank Balances</span>
                <span className="font-semibold">{formatCurrency(workingCapital.cash_and_bank)}</span>
              </div>
              <div className="flex justify-between">
                <span>Accounts Receivable (Khata Dues)</span>
                <span className="font-semibold">{formatCurrency(workingCapital.accounts_receivable)}</span>
              </div>
              <div className="flex justify-between">
                <span>Inventory Valuation (WAC)</span>
                <span className="font-semibold">{formatCurrency(workingCapital.inventory_valuation)}</span>
              </div>
              <div className="flex justify-between font-bold pt-2 border-t border-black/[0.08]/10 text-[#0D0F17] text-sm">
                <span>Total Current Assets</span>
                <span>{formatCurrency(workingCapital.current_assets)}</span>
              </div>
            </div>

            {/* Current Liabilities */}
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 space-y-2 text-xs">
              <div className="font-bold text-[#0D0F17] uppercase">Current Liabilities</div>
              <div className="flex justify-between">
                <span>Accounts Payable (Supplier Dues)</span>
                <span className="font-semibold">{formatCurrency(workingCapital.accounts_payable)}</span>
              </div>
              <div className="flex justify-between font-bold pt-2 border-t border-black/[0.08]/10 text-[#0D0F17] text-sm">
                <span>Total Current Liabilities</span>
                <span>{formatCurrency(workingCapital.current_liabilities)}</span>
              </div>
            </div>
          </div>

          {/* Ratios Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 shadow-sm text-center">
              <div className="text-xs text-slate-500 uppercase font-semibold">Net Working Capital</div>
              <div className="text-xl font-bold text-[#0D0F17] mt-1">
                {formatCurrency(workingCapital.net_working_capital)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Liquid operational buffer</div>
            </div>

            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 shadow-sm text-center">
              <div className="text-xs text-slate-500 uppercase font-semibold">Current Ratio</div>
              <div className="text-xl font-bold text-[#0D0F17] mt-1">
                {workingCapital.current_ratio?.toFixed(2) ?? 'N/A'}x
              </div>
              <div className="text-[10px] text-[#10B981] mt-0.5">Benchmark: &gt; 1.33x</div>
            </div>

            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10 shadow-sm text-center">
              <div className="text-xs text-slate-500 uppercase font-semibold">Quick Ratio (Acid Test)</div>
              <div className="text-xl font-bold text-[#0D0F17] mt-1">
                {workingCapital.quick_ratio?.toFixed(2) ?? 'N/A'}x
              </div>
              <div className="text-[10px] text-[#10B981] mt-0.5">Benchmark: &gt; 1.00x</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Ageing */}
      {activeTab === 'AGEING' && ageing && (
        <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0D0F17]">Ageing Buckets Analysis</h2>
            <span className="text-xs text-slate-500">As of {ageing.as_of_date}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Receivables Buckets */}
            <div className="space-y-3">
              <div className="font-bold text-[#0D0F17] text-xs uppercase tracking-wider">
                Accounts Receivable Ageing (Total: {formatCurrency(ageing.receivables.total)})
              </div>
              {[
                { label: '0 - 30 Days (Current)', val: ageing.receivables.bucket_0_30, color: 'bg-[#10B981]' },
                { label: '31 - 60 Days', val: ageing.receivables.bucket_31_60, color: 'bg-[#F59E0B]' },
                { label: '61 - 90 Days', val: ageing.receivables.bucket_61_90, color: 'bg-[#F59E0B]' },
                { label: '90+ Days (Overdue / Risk)', val: ageing.receivables.bucket_90_plus, color: 'bg-[#2B4EFF]' },
              ].map((b, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">{b.label}</span>
                    <span className="font-semibold text-[#0D0F17]">{formatCurrency(b.val)}</span>
                  </div>
                  <div className="w-full bg-white h-2 rounded-none overflow-hidden border border-black/[0.08]/5">
                    <div
                      className={`h-full ${b.color}`}
                      style={{
                        width: `${Number(ageing.receivables.total) > 0 ? (Number(b.val) / Number(ageing.receivables.total)) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Payables Buckets */}
            <div className="space-y-3">
              <div className="font-bold text-[#0D0F17] text-xs uppercase tracking-wider">
                Accounts Payable Ageing (Total: {formatCurrency(ageing.payables.total)})
              </div>
              {[
                { label: '0 - 30 Days (Current)', val: ageing.payables.bucket_0_30, color: 'bg-[#10B981]' },
                { label: '31 - 60 Days', val: ageing.payables.bucket_31_60, color: 'bg-[#F59E0B]' },
                { label: '61 - 90 Days', val: ageing.payables.bucket_61_90, color: 'bg-[#F59E0B]' },
                { label: '90+ Days (Critical Supplier Dues)', val: ageing.payables.bucket_90_plus, color: 'bg-[#2B4EFF]' },
              ].map((b, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">{b.label}</span>
                    <span className="font-semibold text-[#0D0F17]">{formatCurrency(b.val)}</span>
                  </div>
                  <div className="w-full bg-white h-2 rounded-none overflow-hidden border border-black/[0.08]/5">
                    <div
                      className={`h-full ${b.color}`}
                      style={{
                        width: `${Number(ageing.payables.total) > 0 ? (Number(b.val) / Number(ageing.payables.total)) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Break-Even */}
      {activeTab === 'BREAKEVEN' && breakEven && (
        <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0D0F17]">Break-Even & Margin of Safety</h2>
            <span
              className={`px-3 py-1 rounded-none text-xs font-bold ${
                breakEven.is_operating_above_breakeven
                  ? 'bg-[#10B981]/10 text-[#10B981]'
                  : 'bg-[#F59E0B]/10 text-[#F59E0B]'
              }`}
            >
              {breakEven.is_operating_above_breakeven ? 'Operating Above Break-Even' : 'Below Break-Even'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10">
              <div className="text-xs text-slate-500 uppercase font-semibold">Revenue in selected period</div>
              <div className="text-xl font-bold text-[#0D0F17] mt-1">
                {formatCurrency(breakEven.total_revenue)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Recorded revenue for the reporting period</div>
            </div>

            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10">
              <div className="text-xs text-slate-500 uppercase font-semibold">Break-Even Revenue</div>
              <div className="text-xl font-bold text-[#0D0F17] mt-1">
                {breakEven.break_even_revenue_monthly == null ? 'N/A' : formatCurrency(breakEven.break_even_revenue_monthly)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Selected period contribution margin basis</div>
            </div>

            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10">
              <div className="text-xs text-slate-500 uppercase font-semibold">Contribution Margin</div>
              <div className="text-xl font-bold text-[#10B981] mt-1">
                {formatPercent(breakEven.contribution_margin_ratio * 100)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Revenue less recorded variable costs</div>
            </div>

            <div className="p-4 rounded-none bg-white border border-black/[0.08]/10">
              <div className="text-xs text-slate-500 uppercase font-semibold">Margin of Safety</div>
              <div className="text-xl font-bold text-[#0D0F17] mt-1">
                {breakEven.margin_of_safety_pct == null ? 'N/A' : formatPercent(breakEven.margin_of_safety_pct)}
              </div>
              <div className="text-[10px] text-[#10B981] mt-0.5">Cushion before operational loss</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Health Score */}
      {activeTab === 'HEALTH' && health && (
        <div className="p-6 rounded-none bg-white border border-black/[0.08]/10 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0D0F17]">5-Pillar Composite Business Health</h2>
            <span className="text-xs font-bold px-3 py-1 bg-[#10B981]/10 text-[#10B981] rounded-none">
              {health.grade} ({health.overall_score}/100)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-center">
            {[
              { pillar: 'Liquidity', score: health.pillars.liquidity?.score ?? 0 },
              { pillar: 'Profitability', score: health.pillars.profitability?.score ?? 0 },
              { pillar: 'Solvency', score: health.pillars.solvency?.score ?? 0 },
              { pillar: 'Efficiency', score: health.pillars.efficiency?.score ?? 0 },
              { pillar: 'Cash runway', score: health.pillars.cash_runway?.score ?? 0 },
            ].map((p, idx) => (
              <div key={idx} className="p-4 rounded-none bg-white border border-black/[0.08]/10">
                <div className="text-xs text-slate-500 font-semibold">{p.pillar}</div>
                <div className="text-2xl font-bold text-[#0D0F17] mt-1">{p.score}</div>
                <div className="w-full bg-[#E9E8E2] h-1.5 rounded-none overflow-hidden mt-2">
                  <div className="bg-[#2B4EFF] h-full" style={{ width: `${p.score}%` }} />
                </div>
              </div>
            ))}
          </div>

          {/* Strengths & Vulnerabilities */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div className="p-4 rounded-none bg-[#10B981]/10 border border-[#10B981]/40 space-y-2">
              <div className="flex items-center space-x-1.5 font-bold text-xs uppercase text-[#10B981]">
                <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                <span>Operational Strengths</span>
              </div>
              <ul className="text-xs text-[#10B981] space-y-1 list-disc pl-4">
                {health.key_strengths.map((str, i) => (
                  <li key={i}>{str}</li>
                ))}
              </ul>
            </div>

            <div className="p-4 rounded-none bg-[#F59E0B]/10 border border-[#F59E0B]/40 space-y-2">
              <div className="flex items-center space-x-1.5 font-bold text-xs uppercase text-[#F59E0B]">
                <AlertCircle className="w-4 h-4 text-[#F59E0B]" />
                <span>Identified Vulnerabilities</span>
              </div>
              <ul className="text-xs text-[#F59E0B] space-y-1 list-disc pl-4">
                {health.identified_risks.map((vuln, i) => (
                  <li key={i}>{vuln}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
