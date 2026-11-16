'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import {
	Bot, Send, Sparkles, GitCommit, CheckCircle2,
	HelpCircle, ArrowRight, ShieldCheck, ChevronDown,
	ChevronRight, RefreshCw, Cpu, Database, Clock,
	Copy, Check, FileSearch,
} from 'lucide-react';
import { useToast } from '@/components/ui';
import {
	businessApi, AgentProposedAction,
	AgentInvestigationResponse, InvestigationPlanStep,
	downloadAuthenticatedReport,
} from '../../../../lib/business-api';
import { AgentSynthesisView } from '@/components/agent/AgentSynthesisView';

interface ConversationTurn {
	id: string;
	query: string;
	response: AgentInvestigationResponse;
	timestamp: string;
}

function formatGapLabel(key: string): string {
	const labels: Record<string, string> = {
		machine_cost: 'Machine / Equipment Purchase Price (₹)',
		down_payment: 'Cash Down Payment (₹)',
		loan_amount: 'Loan Principal Amount (₹)',
		loan_interest_rate_pct: 'Loan Interest Rate (%)',
		loan_tenure_months: 'Loan Repayment Term (Months)',
		monthly_maintenance: 'Monthly Maintenance Cost (₹)',
		unit_price: 'Selling Price Per Unit (₹)',
		unit_variable_cost: 'Variable Cost Per Unit (₹)',
		current_monthly_volume: 'Current Monthly Sales Volume (Units)',
		capacity_monthly_volume: 'Capacity Monthly Production (Units)',
		purchase_cost: 'Asset / Equipment Purchase Cost (₹)',
		monthly_operating_gain: 'Expected Monthly Net Gain (₹)',
		available_cash: 'Available Liquid Cash (₹)',
		lease_monthly_payment: 'Monthly Lease Cost (₹)',
		lease_term_months: 'Lease Duration (Months)',
		equity_injection: 'Equity Capital Infusion (₹)',
		discount_rate_pct: 'Discount / Hurdle Rate (%)',
		expansion_capex: 'Expansion Capital Expenditure (₹)',
		projected_monthly_revenue: 'Projected Monthly Inflow / Revenue (₹)',
		gross_margin_pct: 'Gross Profit Margin (%)',
		projected_monthly_opex: 'Projected Monthly Operating Expense (₹)',
		unit_cost: 'Unit Cost / Purchase Price (₹)',
		order_quantity: 'Batch Order Quantity (Units)',
		monthly_demand: 'Monthly Customer Demand (Units)',
		current_stock: 'Current Stock on Hand (Units)',
		reorder_threshold: 'Reorder Buffer Level (Units)',
		holding_cost_per_unit_month: 'Inventory Holding Cost (₹/Unit/Mo)',
		stockout_cost_per_unit: 'Stockout Penalty Cost (₹/Unit)',
		supplier_lead_time_days: 'Supplier Fulfillment Lead Time (Days)',
		customer_name: 'Customer Account / Counterparty',
		current_receivable: 'Current Outstanding Receivables (₹)',
		credit_limit: 'Recommended Credit Ceiling (₹)',
		requested_sale_amount: 'Requested Invoice Value (₹)',
		average_monthly_sales: 'Historical Monthly Volume (₹)',
		default_risk_pct: 'Estimated Default Risk (%)',
		annual_cost_of_capital_pct: 'Annual Cost of Capital (%)',
		proposed_terms_days: 'Proposed Payment Terms (Days)',
		overdue_days: 'Days Past Due',
		current_monthly_cost: 'Current Monthly Run-Rate Cost (₹)',
		proposed_monthly_cost: 'Proposed Monthly Target Cost (₹)',
		one_time_implementation_cost: 'One-Time Transition Cost (₹)',
		expected_quality_cost_monthly: 'Estimated Quality / Rework Cost (₹)',
		evaluation_months: 'Evaluation Horizon (Months)',
		cash_balance: 'Liquid Cash on Hand (₹)',
		monthly_cash_inflows: 'Monthly Cash Inflows (₹)',
		monthly_cash_outflows: 'Monthly Cash Outflows (₹)',
		receivables_due_30d: 'Receivables Maturing in 30 Days (₹)',
		receivables_collectible_amount: 'Expected Realizable Collections (₹)',
		payables_due_30d: 'Payables Due in 30 Days (₹)',
		payables_deferral_amount: 'Negotiable Payables Deferrals (₹)',
		credit_line_available: 'Available Credit Facilities (₹)',
		credit_line_draw_amount: 'Proposed Credit Facility Draw (₹)',
		credit_line_interest_pct: 'Credit Facility Interest Rate (%)',
		monthly_survival_threshold: 'Critical Cash Survival Buffer (₹)',
		current_monthly_revenue: 'Current Monthly Revenue (₹)',
		variable_cost_pct: 'Variable Cost Ratio (%)',
		monthly_fixed_costs: 'Monthly Fixed Costs (₹)',
		monthly_debt_service: 'Monthly Debt Principal & Interest (₹)',
		current_working_capital: 'Current Net Working Capital (₹)',
		monthly_revenue_growth_pct: 'Monthly Revenue Growth Rate (%)',
		monthly_capex: 'Monthly Capital Expenditure (₹)',
		current_debt: 'Total Debt Outstanding (₹)',
	};
	return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function StructuredDataGrid({ data }: { data: any }) {
	if (data === null || data === undefined) {
		return <span className="text-[#9A7E78] italic text-[11px]">None</span>;
	}
	if (typeof data !== 'object') {
		return <span className="font-semibold text-[#231412] text-xs break-words">{String(data)}</span>;
	}
	if (Array.isArray(data)) {
		if (data.length === 0) return <span className="text-[#9A7E78] italic text-[11px]">Empty list</span>;
		return (
			<div className="space-y-1.5 max-h-48 overflow-y-auto">
				{data.map((item, idx) => (
					<div key={idx} className="p-2 rounded bg-white border border-[#231412]/15 text-xs">
						<StructuredDataGrid data={item} />
					</div>
				))}
			</div>
		);
	}
	const entries = Object.entries(data);
	if (entries.length === 0) {
		return <span className="text-[#9A7E78] italic text-[11px]">Empty record</span>;
	}
	return (
		<div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs max-h-56 overflow-y-auto p-1">
			{entries.map(([key, val]) => (
				<div key={key} className="p-2 rounded bg-white border border-[#231412]/15 flex flex-col justify-between">
					<span className="text-[10px] font-bold uppercase tracking-wider text-[#6E524D] font-mono">
						{key.replace(/_/g, ' ')}
					</span>
					<div className="mt-1 font-semibold text-[#231412] break-words">
						{typeof val === 'object' && val !== null ? (
							<StructuredDataGrid data={val} />
						) : (
							String(val)
						)}
					</div>
				</div>
			))}
		</div>
	);
}

export default function AgenticCopilotPage() {
	const { toast } = useToast();
	const params = useParams();
	const businessId = params.id as string;

	const [query, setQuery] = useState('');
	const [sessionId, setSessionId] = useState<string | null>(null);
	const [investigating, setInvestigating] = useState(false);
	const [turns, setTurns] = useState<ConversationTurn[]>([]);
	const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
	const [showEvidenceDrawer, setShowEvidenceDrawer] = useState(false);
	const [copiedSessionId, setCopiedSessionId] = useState(false);
	const [proposedActions, setProposedActions] = useState<AgentProposedAction[]>([]);

	const quickPrompts = [
		'Should we purchase equipment based on our current cash position and operating data?',
		'How can we improve our working capital and solvency ratios?',
		'Which customers have overdue payments and credit exposure?',
		'Analyze our break-even safety margin against current sales.',
		'Should we extend 45-day credit terms to top retail accounts?',
	];

	const handleInvestigate = async (queryText?: string) => {
		const q = (queryText || query).trim();
		if (!q) return;

		try {
			setInvestigating(true);
			const res = await businessApi.agentInvestigate(businessId, q, sessionId || undefined);

			if (res.session_id) {
				setSessionId(res.session_id);
				const actions = await businessApi.listAgentProposedActions(businessId, res.session_id).catch(() => []);
				setProposedActions(actions);
			}

			const turn: ConversationTurn = {
				id: (res.session_id || '') + '-' + Date.now(),
				query: q,
				response: res,
				timestamp: new Date().toLocaleTimeString(),
			};

			setTurns((prev) => [...prev, turn]);
			setQuery('');
			toast.success('Agent investigation complete');
		} catch (err: any) {
			toast.error(`Agent investigation failed: ${err.message}`);
		} finally {
			setInvestigating(false);
		}
	};

	const handleResetSession = () => {
		setSessionId(null);
		setTurns([]);
		setExpandedSteps({});
		setQuery('');
		toast.info('Session reset. Starting fresh investigation context.');
	};

	const copySessionId = () => {
		if (sessionId) {
			navigator.clipboard.writeText(sessionId);
			setCopiedSessionId(true);
			setTimeout(() => setCopiedSessionId(false), 2000);
			toast.info('Session ID copied to clipboard');
		}
	};

	const toggleStepExpand = (stepKey: string) => {
		setExpandedSteps((prev) => ({
			...prev,
			[stepKey]: !prev[stepKey],
		}));
	};

	const decideProposedAction = async (action: AgentProposedAction, decision: 'confirm' | 'reject') => {
		if (!sessionId) return;
		try {
			const updated = decision === 'confirm'
				? await businessApi.confirmAgentProposedAction(businessId, sessionId, action.id)
				: await businessApi.rejectAgentProposedAction(businessId, sessionId, action.id);
			setProposedActions((items) => items.map((item) => item.id === updated.id ? updated : item));
			toast.success(decision === 'confirm' ? 'Proposed action confirmed.' : 'Proposed action rejected.');
		} catch (error) {
			toast.error((error as Error).message);
		}
	};

	const latestTurn = turns.length > 0 ? turns[turns.length - 1] : null;
	const gatheredEvidence: Record<string, any> = {};

	if (latestTurn?.response.plan) {
		latestTurn.response.plan.forEach((s) => {
			if (s.result && s.status === 'EXECUTED') {
				gatheredEvidence[s.tool_name] = s.result;
			}
		});
	}
	if (latestTurn?.response.evidence_gathered) {
		Object.assign(gatheredEvidence, latestTurn.response.evidence_gathered);
	}

	return (
		<div className="space-y-6 max-w-7xl mx-auto">
			<div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[#C8281E]/15">
				<div>
					<div className="flex items-center space-x-2">
						<h1 className="text-2xl font-bold text-[#231412]">Agentic Copilot</h1>
						<span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-[#C8281E]/10 text-[#C8281E] border border-[#C8281E]/25 flex items-center space-x-1">
							<Sparkles className="w-3 h-3 text-[#C8281E]" />
							<span>Deterministic Tool Registry</span>
						</span>
					</div>
					<p className="text-sm text-[#6E524D] mt-0.5">
						Formulates multi-step investigation DAGs, audits live business ledger tools, and synthesizes explainable guidance.
					</p>
				</div>

				<div className="flex items-center space-x-2 self-stretch md:self-auto justify-end">
					{sessionId ? (
						<div className="flex items-center space-x-2">
							<MotionButton
								onClick={copySessionId}
								title="Click to copy Session ID"
								className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#2D7D52]/10 text-[#2D7D52] border border-[#2D7D52]/30 text-xs font-mono transition-colors"
							>
								<ShieldCheck className="w-3.5 h-3.5 text-[#2D7D52]" />
								<span className="max-w-[120px] truncate">{sessionId}</span>
								{copiedSessionId ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3 opacity-60" />}
							</MotionButton>
							<MotionButton
								onClick={handleResetSession}
								className="px-3 py-1.5 rounded-xl bg-white border border-[#C8281E]/20 text-[#231412] text-xs font-semibold hover:bg-[#FAF7F2] transition-colors flex items-center space-x-1 shadow-sm"
							>
								<RefreshCw className="w-3.5 h-3.5" />
								<span>New Session</span>
							</MotionButton>
						</div>
					) : (
						<span className="text-xs text-[#6E524D] bg-white border border-[#C8281E]/20 px-3 py-1.5 rounded-xl font-medium shadow-sm">
							New Unpersisted Session
						</span>
					)}

					{Object.keys(gatheredEvidence).length > 0 && (
						<MotionButton
							onClick={() => setShowEvidenceDrawer(!showEvidenceDrawer)}
							className="px-3 py-1.5 rounded-xl bg-[#C8281E]/10 text-[#C8281E] border border-[#C8281E]/20 text-xs font-semibold hover:bg-[#C8281E]/20 transition-colors flex items-center space-x-1.5"
						>
							<FileSearch className="w-3.5 h-3.5" />
							<span>Evidence Drawer ({Object.keys(gatheredEvidence).length})</span>
						</MotionButton>
					)}
				</div>
			</div>

			<div className="p-5 rounded-2xl bg-white/95 border border-[#C8281E]/18 shadow-sm space-y-3">
				<form
					onSubmit={(e) => {
						e.preventDefault();
						handleInvestigate();
					}}
					className="flex items-center space-x-2"
				>
					<div className="relative flex-1">
						<Bot className="w-4 h-4 text-[#9A7E78] absolute left-3.5 top-1/2 transform -translate-y-1/2" />
						<input
							type="text"
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							placeholder={
								sessionId
									? "Continue conversation in current verified session..."
									: "Ask anything about business financials, debts, capital investments or break-even..."
							}
							className="w-full text-xs pl-10 pr-4 py-3 rounded-xl border border-[#C8281E]/20 focus:outline-none focus:border-[#C8281E] bg-[#FAF7F2] text-[#231412] placeholder-[#9A7E78]"
						/>
					</div>
					<MotionButton
						type="submit"
						disabled={investigating}
						className="px-5 py-3 rounded-xl bg-[#C8281E] text-white text-xs font-bold hover:bg-[#A81E15] transition-all shadow-md shadow-[#C8281E]/20 flex items-center space-x-1.5 disabled:opacity-50"
					>
						<Send className="w-3.5 h-3.5" />
						<span>{investigating ? 'Investigating...' : 'Ask'}</span>
					</MotionButton>
				</form>

				<div className="flex flex-wrap items-center gap-2 pt-1">
					<span className="text-[11px] font-semibold text-[#6E524D]">Suggested Inquiries:</span>
					{quickPrompts.map((p, idx) => (
						<MotionButton
							key={idx}
							onClick={() => {
								setQuery(p);
								handleInvestigate(p);
							}}
							className="text-[11px] px-2.5 py-1 rounded-xl bg-[#FAF7F2] hover:bg-[#C8281E]/10 hover:text-[#C8281E] transition-all text-[#231412] border border-[#C8281E]/15"
						>
							{p}
						</MotionButton>
					))}
				</div>
			</div>

			{proposedActions.length > 0 && (
				<section className="rounded-2xl border border-[#C8281E]/18 bg-white/95 p-5 shadow-sm space-y-3">
					<div className="text-xs font-bold uppercase tracking-wider text-[#231412] flex items-center space-x-1.5">
						<span className="w-2 h-2 rounded-full bg-[#D4A359]" />
						<span>Actions Awaiting Human Confirmation ({proposedActions.length}):</span>
					</div>
					{proposedActions.map((action) => (
						<article key={action.id} className="border-2 border-[#231412] bg-[#FAF7F2] p-4 shadow-[2px_2px_0px_#231412]">
							<div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#231412]/15">
								<div className="text-xs font-bold text-[#231412] font-mono uppercase">
									{action.action_type.replaceAll('_', ' ')} · {action.status.replaceAll('_', ' ')}
								</div>
								<span className="font-mono text-[10px] text-[#9A7E78]">
									{action.created_at ? new Date(action.created_at).toLocaleString() : ''}
								</span>
							</div>
							<div className="mt-2.5 grid grid-cols-2 sm:grid-cols-4 gap-2 bg-white border border-[#231412]/30 p-2.5 font-mono text-xs">
								{Object.entries(action.payload || {}).map(([key, val]) => (
									<div key={key}>
										<span className="text-[10px] uppercase font-bold text-[#5C403B] block">{key.replace(/_/g, ' ')}</span>
										<strong className="text-xs text-[#231412] block truncate">
											{typeof val === 'object' && val !== null
												? (Array.isArray(val) ? val.join(', ') : Object.entries(val).map(([k, v]) => `${k}: ${v}`).join('; '))
												: String(val)}
										</strong>
									</div>
								))}
							</div>
							<div className="mt-3 flex flex-wrap gap-2">
								{action.status === 'PENDING_CONFIRMATION' && (
									<>
										<MotionButton
											type="button"
											onClick={() => decideProposedAction(action, 'confirm')}
											className="border border-[#231412] bg-[#2D7D52] px-3.5 py-1.5 text-xs font-bold font-mono text-white shadow-sm hover:bg-[#236340]"
										>
											Confirm & Execute
										</MotionButton>
										<MotionButton
											type="button"
											onClick={() => decideProposedAction(action, 'reject')}
											className="border border-[#231412] bg-white px-3.5 py-1.5 text-xs font-bold font-mono text-rose-700 hover:bg-rose-50"
										>
											Reject
										</MotionButton>
									</>
								)}
								{action.status === 'CONFIRMED' && action.action_type === 'GENERATE_REPORT' && sessionId && (
									<MotionButton
										type="button"
										onClick={() =>
											downloadAuthenticatedReport(
												businessApi.getAgentActionReportUrl(businessId, sessionId, action.id),
												'agent-report.pdf'
											).catch((error: Error) => toast.error(error.message))
										}
										className="border border-[#231412] bg-[#C8281E] px-3.5 py-1.5 text-xs font-bold font-mono text-white"
									>
										Download Confirmed Report (PDF)
									</MotionButton>
								)}
								{action.status === 'CONFIRMED' && action.result?.resource_id && (
									<span className="self-center text-[11px] text-[#2D7D52] font-bold font-mono">
										Verified Record ID: {action.result.resource_id}
									</span>
								)}
							</div>
						</article>
					))}
				</section>
			)}

			{showEvidenceDrawer && (
				<div className="p-6 rounded-2xl bg-white border border-[#C8281E]/20 shadow-md space-y-4">
					<div className="flex items-center justify-between border-b border-[#C8281E]/15 pb-3">
						<div className="flex items-center space-x-2">
							<Database className="w-4 h-4 text-[#C8281E]" />
							<h3 className="text-sm font-bold text-[#231412]">
								Evidence Drawer — Verified Ledger & Ratio Records
							</h3>
						</div>
						<MotionButton
							onClick={() => setShowEvidenceDrawer(false)}
							className="text-xs text-[#6E524D] hover:text-[#231412] font-bold px-2 py-1 rounded-lg"
						>
							Close ✕
						</MotionButton>
					</div>
					<p className="text-xs text-[#6E524D]">
						These records were gathered directly from Postgres via deterministic tools and served as the factual ground truth for synthesis.
					</p>
					<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
						{Object.entries(gatheredEvidence).map(([key, data]) => (
							<div key={key} className="p-3.5 rounded-none bg-[#FAF7F2] border-2 border-[#231412] shadow-[2px_2px_0px_#231412] space-y-2">
								<div className="flex items-center justify-between text-xs font-mono font-bold text-[#231412]">
									<span>{key.replace(/_/g, ' ').toUpperCase()}</span>
									<span className="text-[10px] bg-[#2D7D52]/10 text-[#2D7D52] px-2 py-0.5 rounded-none border border-[#2D7D52]/30 font-sans font-bold">Verified</span>
								</div>
								<StructuredDataGrid data={data} />
							</div>
						))}
					</div>
				</div>
			)}

			{turns.length === 0 && !investigating && (
				<div className="p-12 text-center rounded-2xl border border-dashed border-[#C8281E]/25 bg-white/70 space-y-3">
					<Bot className="w-10 h-10 text-[#C8281E]/50 mx-auto" />
					<h3 className="text-sm font-bold text-[#231412]">Ready for Multi-Step Business Inquiries</h3>
					<p className="text-xs text-[#6E524D] max-w-md mx-auto">
						Ask any strategic, accounting, or solvency questions. The agent will formulate a deterministic DAG plan, audit your ledger, and provide actionable recommendations.
					</p>
				</div>
			)}

			<div className="space-y-8">
				{turns.map((turn, tIdx) => {
					const resp = turn.response;
					const planSteps = resp.plan || (resp.plan_nodes?.map((pn) => ({
						step_number: pn.step,
						title: pn.purpose,
						tool_name: pn.tool_name,
						arguments: {},
						status: pn.status,
						observation: pn.result_summary || '',
					})) as InvestigationPlanStep[]) || [];

					return (
						<div key={turn.id} className="space-y-5">
							<div className="flex items-center justify-between bg-[#C8281E] text-white px-5 py-3 rounded-2xl shadow-md shadow-[#C8281E]/20">
								<div className="flex items-center space-x-2.5 text-xs font-semibold">
									<span className="w-5 h-5 rounded-lg bg-white/20 text-white flex items-center justify-center text-[10px] font-bold">
										Q{tIdx + 1}
									</span>
									<span>{turn.query}</span>
								</div>
								<span className="text-[10px] text-white/80 font-mono">{turn.timestamp}</span>
							</div>

							{(resp.planning_attribution || resp.synthesis_attribution || resp.llm_provider) && (
								<div className="flex flex-wrap items-center gap-2">
									{resp.planning_attribution && (
										<div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white border border-[#C8281E]/15 text-[11px] shadow-sm">
											<Cpu className="w-3 h-3 text-[#C8281E]" />
											<span className="font-semibold text-[#231412]">Planning:</span>
											<span className="font-mono text-[#6E524D]">{resp.planning_attribution.model_name || resp.planning_attribution.actual_provider}</span>
											<span className="text-[#9A7E78]">|</span>
											<Clock className="w-2.5 h-2.5 text-[#9A7E78]" />
											<span className="text-[#6E524D]">{resp.planning_attribution.latency_ms}ms</span>
										</div>
									)}

									{resp.synthesis_attribution && (
										<div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white border border-[#C8281E]/15 text-[11px] shadow-sm">
											<Sparkles className="w-3 h-3 text-[#D4A359]" />
											<span className="font-semibold text-[#231412]">Synthesis:</span>
											<span className="font-mono text-[#6E524D]">{resp.synthesis_attribution.model_name || resp.synthesis_attribution.actual_provider}</span>
											<span className="text-[#9A7E78]">|</span>
											<Clock className="w-2.5 h-2.5 text-[#9A7E78]" />
											<span className="text-[#6E524D]">{resp.synthesis_attribution.latency_ms}ms</span>
										</div>
									)}

									{resp.decision_outcome && (
										<div className={`flex items-center space-x-1 px-3 py-1 rounded-full border text-[11px] font-bold ${
											resp.decision_outcome === 'FEASIBLE' || resp.decision_outcome === 'VERIFIED' || resp.decision_outcome === 'INFORMATIONAL'
												? 'bg-[#2D7D52]/10 border-[#2D7D52]/30 text-[#2D7D52]'
												: resp.decision_outcome === 'NOT_FEASIBLE'
												? 'bg-[#C8281E]/10 border-[#C8281E]/30 text-[#C8281E]'
												: 'bg-amber-500/10 border-amber-500/30 text-amber-700'
										}`}>
											<ShieldCheck className="w-3 h-3" />
											<span>Verdict: {resp.decision_outcome}</span>
										</div>
									)}
								</div>
							)}

							<div className="p-6 rounded-2xl bg-[#FAF7F2] text-[#231412] border border-[#C8281E]/20 shadow-md space-y-4">
								<div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-[#C8281E]">
									<div className="flex items-center space-x-2">
										<Sparkles className="w-4 h-4 text-[#C8281E]" />
										<span>Synthesized Business Guidance</span>
									</div>
									{resp.decision_outcome && (
										<span className="bg-[#C8281E]/10 text-[#C8281E] px-2.5 py-0.5 rounded-full border border-[#C8281E]/30 font-bold">
											{resp.decision_outcome}
										</span>
									)}
								</div>
								<AgentSynthesisView content={resp.synthesis} />

								{resp.recommended_actions && resp.recommended_actions.length > 0 && (
									<div className="pt-3 border-t border-[#C8281E]/15 space-y-2">
										<div className="text-xs font-bold text-[#C8281E] uppercase">
											Actionable Next Steps
										</div>
										<div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
											{resp.recommended_actions.map((act, i) => (
												<div
													key={i}
													className="p-3 rounded-xl bg-white border border-[#C8281E]/15 flex items-center space-x-2 text-[#231412] shadow-sm"
												>
													<CheckCircle2 className="w-3.5 h-3.5 text-[#2D7D52] shrink-0" />
													<span>{act}</span>
												</div>
											))}
										</div>
									</div>
								)}
							</div>

							{planSteps.length > 0 && (
								<div className="p-6 rounded-2xl bg-white border border-[#C8281E]/18 shadow-sm space-y-4">
									<div className="flex items-center justify-between">
										<div className="flex items-center space-x-2">
											<GitCommit className="w-4 h-4 text-[#C8281E]" />
											<h3 className="text-sm font-bold text-[#231412]">
												Investigation DAG Plan ({planSteps.length} Steps)
											</h3>
										</div>
										<span className="text-[10px] font-semibold text-[#2D7D52] bg-[#2D7D52]/10 px-2.5 py-0.5 rounded-full border border-[#2D7D52]/30">
											100% Deterministic Tool Execution
										</span>
									</div>

									<div className="space-y-3">
										{planSteps.map((step, sIdx) => {
											const stepKey = `${turn.id}-step-${step.step_number || sIdx + 1}`;
											const isExpanded = !!expandedSteps[stepKey];

											return (
												<div
													key={sIdx}
													className="p-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/15 text-xs transition-all space-y-2"
												>
													<div className="flex items-start justify-between">
														<div className="space-y-1">
															<div className="flex items-center space-x-2">
																<span className="w-5 h-5 rounded-md bg-[#C8281E] text-white flex items-center justify-center font-bold text-[10px]">
																	{step.step_number || sIdx + 1}
																</span>
																<span className="font-mono font-bold text-[#231412] bg-white px-2 py-0.5 rounded-md border border-[#C8281E]/15">
																	{step.tool_name}
																</span>
																<span className="text-[#6E524D]">{step.title}</span>
															</div>
															{step.observation && (
																<div className="text-[11px] text-[#6E524D] pl-7">
																	Result: <span className="text-[#231412] font-medium">{step.observation}</span>
																</div>
															)}
														</div>

														<div className="flex items-center space-x-2">
															<span
																className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
																	step.status === 'EXECUTED'
																		? 'bg-[#2D7D52]/10 text-[#2D7D52]'
																		: step.status === 'FAILED'
																		? 'bg-rose-100 text-rose-700'
																		: 'bg-[#F3ECE3] text-[#6E524D]'
																}`}
															>
																{step.status}
															</span>
															{(step.arguments || step.result) && (
																<MotionButton
																	onClick={() => toggleStepExpand(stepKey)}
																	className="text-[11px] text-[#C8281E] hover:underline font-semibold flex items-center space-x-0.5"
																>
																	<span>Inspector</span>
																	{isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
																</MotionButton>
															)}
														</div>
													</div>

													{isExpanded && (
														<div className="mt-2 pt-2 border-t border-[#C8281E]/15 pl-7 space-y-3">
															{step.arguments && Object.keys(step.arguments).length > 0 && (
																<div>
																	<div className="text-[10px] font-bold text-[#6E524D] uppercase tracking-wider mb-1">
																		Validated Tool Arguments:
																	</div>
																	<StructuredDataGrid data={step.arguments} />
																</div>
															)}
															{step.result && (
																<div>
																	<div className="text-[10px] font-bold text-[#6E524D] uppercase tracking-wider mb-1">
																		Live Deterministic Tool Output:
																	</div>
																	<StructuredDataGrid data={step.result} />
																</div>
															)}
														</div>
													)}
												</div>
											);
										})}
									</div>
								</div>
							)}

							{((resp.data_gaps && resp.data_gaps.length > 0) ||
								(resp.follow_up_questions && resp.follow_up_questions.length > 0)) && (
								<div className="p-6 rounded-none bg-[#FAF7F2] border-2 border-[#231412] shadow-[4px_4px_0px_#231412] space-y-4">
									<div className="flex items-center space-x-2 text-[#231412] font-black text-xs uppercase tracking-wider">
										<HelpCircle className="w-4 h-4 text-[#C8281E]" />
										<span>Identified Information Gaps & Recommended Inquiries</span>
									</div>

									{resp.data_gaps && resp.data_gaps.length > 0 && (
										<div className="space-y-1.5">
											<p className="text-[11px] font-bold uppercase tracking-wider text-[#5C403B]">Missing Ground Truth Inputs:</p>
											<div className="flex flex-wrap gap-2">
												{resp.data_gaps.map((gap, i) => (
													<span
														key={i}
														className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-none bg-white border border-[#231412] text-xs font-bold text-[#231412] shadow-[2px_2px_0px_#231412]"
													>
														<span className="w-1.5 h-1.5 rounded-full bg-[#C8281E]" />
														<span>{formatGapLabel(gap)}</span>
													</span>
												))}
											</div>
										</div>
									)}

									{resp.follow_up_questions && resp.follow_up_questions.length > 0 && (
										<div className="pt-3 border-t-2 border-[#231412]/15 space-y-2">
											<div className="text-[11px] font-black uppercase tracking-wider text-[#231412]">
												Clickable Follow-up Questions (Auto-executes in current session):
											</div>
											<div className="flex flex-wrap gap-2">
												{resp.follow_up_questions.map((q, i) => (
													<MotionButton
														key={i}
														disabled={investigating}
														onClick={() => {
															setQuery(q);
															handleInvestigate(q);
														}}
														className="text-left text-xs font-bold px-3.5 py-2 rounded-none bg-white hover:bg-[#C8281E] text-[#231412] hover:text-white border-2 border-[#231412] shadow-[2px_2px_0px_#231412] transition-colors flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
													>
														<span>&ldquo;{q}&rdquo;</span>
														<ArrowRight className="w-3.5 h-3.5 shrink-0" />
													</MotionButton>
												))}
											</div>
										</div>
									)}
								</div>
							)}
						</div>
					);
				})}
			</div>
		</div>
	);
}