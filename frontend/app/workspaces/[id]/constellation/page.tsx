'use client';
import { MotionButton } from '@/components/ui/motion-button';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Activity, Boxes, Building2, CircleDollarSign, GitBranch, Target, Users } from 'lucide-react';
import { businessApi, Customer, Product, Supplier } from '../../../../lib/business-api';
import { formatINR } from '../../../../lib/money';
import { useToast } from '@/components/ui';

type RecordNode = { id: string; label: string; type: string; metric: string; href: string; icon: 'workspace' | 'customer' | 'supplier' | 'product' | 'goal' | 'decision' };
const icons = { workspace: Building2, customer: Users, supplier: Building2, product: Boxes, goal: Target, decision: GitBranch };

export default function SystemTopologyPage() {
	const { toast } = useToast();
	const businessId = useParams().id as string;
	const [records, setRecords] = useState<RecordNode[]>([]);
	const [selected, setSelected] = useState<RecordNode | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		let active = true;
		Promise.all([
			businessApi.getWorkspace(businessId), businessApi.getCashPosition(businessId),
			businessApi.listCustomers(businessId), businessApi.listSuppliers(businessId),
			businessApi.listProducts(businessId), businessApi.listGoals(businessId), businessApi.getDecisionHistory(businessId),
		]).then(([workspace, cash, customers, suppliers, products, goals, decisions]) => {
			const rows: RecordNode[] = [{
				id: workspace.id, label: workspace.name, type: 'Workspace',
				metric: 'Liquid cash ' + formatINR(cash.total_liquid_cash_exact ?? cash.total_liquid_cash),
				href: '/workspaces/' + businessId, icon: 'workspace',
			}];
			rows.push(...(customers as Customer[]).map((item) => ({ id: item.id, label: item.name, type: 'Customer', metric: 'Receivable ' + formatINR(item.current_balance_amount), href: '/workspaces/' + businessId + '/customers', icon: 'customer' as const })));
			rows.push(...(suppliers as Supplier[]).map((item) => ({ id: item.id, label: item.name, type: 'Supplier', metric: 'Payable ' + formatINR(item.current_balance_amount), href: '/workspaces/' + businessId + '/suppliers', icon: 'supplier' as const })));
			rows.push(...(products as Product[]).map((item) => ({ id: item.id, label: item.name, type: item.current_stock <= item.reorder_level ? 'Low units product' : 'Product', metric: item.current_stock + ' ' + item.unit_of_measure + ' · WAC ' + formatINR(item.weighted_average_cost), href: '/workspaces/' + businessId + '/inventory', icon: 'product' as const })));
			rows.push(...goals.map((item) => ({ id: item.id, label: item.title, type: 'Goal', metric: item.progress_pct.toFixed(1) + '% · due ' + item.target_date, href: '/workspaces/' + businessId + '/goals', icon: 'goal' as const })));
			rows.push(...decisions.map((item) => ({ id: item.evaluation_id, label: item.model_id, type: 'Decision', metric: item.outcome, href: '/workspaces/' + businessId + '/decisions', icon: 'decision' as const })));
			if (active) setRecords(rows);
		}).catch((error: Error) => {
			if (active) toast.error('System topology could not be loaded: ' + error.message);
		}).finally(() => { if (active) setLoading(false); });
		return () => { active = false; };
	}, [businessId, toast]);

	return (
		<main className="mx-auto max-w-7xl space-y-6 p-5 md:p-8">
			<header>
				<p className="text-xs font-semibold uppercase tracking-widest text-[#C8281E]">SYSTEM ARCHITECTURE</p>
				<h1 className="mt-1 text-2xl font-bold text-[#231412]">System topology</h1>
				<p className="mt-1 text-sm text-[#6E524D]">Explore how live customers, suppliers, inventory, goals, and decisions connect to this workspace.</p>
			</header>
			<div className="grid gap-5 lg:grid-cols-[1fr_300px]">
				<section aria-label="Workspace records" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
					{loading && <p className="text-sm text-[#6E524D]">Loading workspace records…</p>}
					{records.map((record) => {
						const Icon = icons[record.icon];
						const isSelected = selected?.type === record.type && selected?.id === record.id;
						return <MotionButton key={record.type + '-' + record.id} onClick={() => setSelected(record)} className={'min-h-28 rounded-2xl border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-[#C8281E]/40 shadow-sm ' + (isSelected ? 'border-[#C8281E] bg-[#C8281E]/10' : 'border-[#C8281E]/20 bg-white/90 hover:border-[#C8281E]/40 hover:bg-white')}>
							<span className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-wider text-[#9A7E78]">{record.type}</span><Icon size={15} className="text-[#C8281E]" /></span>
							<span className="mt-2 block font-semibold text-[#231412]">{record.label}</span>
							<span className="mt-2 block text-xs tabular-nums text-[#6E524D]">{record.metric}</span>
						</MotionButton>;
					})}
					{!loading && !records.length && <p className="text-sm text-[#6E524D]">No workspace records found.</p>}
				</section>
				<aside className="rounded-2xl border border-[#C8281E]/20 bg-white/90 p-5 shadow-sm" aria-live="polite">
					<span className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-[.13em] text-[#9A7E78]"><Activity size={13} className="text-[#C8281E]" /> Record detail</span>
					<h2 className="mt-3 font-bold text-[#231412]">{selected?.label ?? 'Select a record'}</h2>
					{selected ? <><p className="mt-1 text-xs uppercase text-[#9A7E78]">{selected.type}</p><p className="mt-4 text-sm tabular-nums text-[#6E524D]">{selected.metric}</p><Link href={selected.href} className="mt-5 inline-flex rounded-xl bg-[#C8281E] px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#A81E15]">Open module</Link></> : <p className="mt-2 text-xs leading-relaxed text-[#6E524D]">Select a workspace record to see its metric and open the source module.</p>}
					{!selected && <CircleDollarSign size={27} className="mt-6 text-[#C8281E]/40" />}
				</aside>
			</div>
		</main>
	);
}