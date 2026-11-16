'use client';
import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {useParams} from 'next/navigation';
import {motion,type Variants} from 'framer-motion';
import {
	Activity,
	ArrowDownLeft,
	ArrowRight,
	ArrowUpRight,
	BarChart3,
	BrainCircuit,
	Bot,
	CircleDollarSign,
	FileText,
	Receipt,
	ShieldCheck,
	ShoppingCart,
	Target,
	TrendingUp,
	Wallet,
} from 'lucide-react';
import {
	businessApi,
	BusinessHealthScore,
	CashFlowStatement,
	CashPosition,
	Goal,
	ProfitAndLossStatement,
	SalesInvoice,
} from '../../../lib/business-api';
import {formatINR} from '../../../lib/money';
import {NumberTicker} from '../../../components/motion/NumberTicker';
import {ScrambleText} from '../../../components/motion/ScrambleText';
import {SpotlightCard} from '../../../components/motion/SpotlightCard';

const revealGroup:Variants={
	hidden:{},
	visible:{transition:{staggerChildren:0.085,delayChildren:0.06}},
};

const revealCard:Variants={
	hidden:{opacity:1,y:22,scale:0.985},
	visible:{
		opacity:1,
		y:0,
		scale:1,
		transition:{type:'spring',stiffness:230,damping:25},
	},
};

const cashflowFields:Array<{
	key:keyof CashFlowStatement;
	label:string;
}>=[
	{key:'operating_cash_inflow',label:'Operating inflow'},
	{key:'operating_cash_outflow',label:'Operating outflow'},
	{key:'investing_cash_flow',label:'Investing'},
	{key:'financing_cash_flow',label:'Financing'},
];

function amount(value:number|string|null|undefined):number{
	const parsed=Number(value??0);
	return Number.isFinite(parsed)?parsed:0;
}

function currency(value:number|string|null|undefined):string{
	return formatINR(value??0);
}

function MetricCard({
	label,
	value,
	prefix='',
	suffix='',
	decimals=0,
	note,
	icon:Icon,
}:{
	label:string;
	value:number|null;
	prefix?:string;
	suffix?:string;
	decimals?:number;
	note:string;
	icon:typeof Wallet;
}){
	return(
		<SpotlightCard className="h-full">
			<motion.article variants={revealCard} className="bg-white/92 border border-[#C8281E]/20 rounded-2xl p-5 shadow-sm flex flex-col justify-between gap-2 h-full">
				<div className="flex items-center justify-between"><span className="text-xs font-bold uppercase tracking-wider text-[#7A5A54]">{label}</span><Icon className="w-4 h-4 text-[#C8281E] shrink-0" /></div>
				<div className="text-2xl font-extrabold text-[#231412] block my-1 tabular-nums">{value===null?'—':<NumberTicker value={value} prefix={prefix} suffix={suffix} decimals={decimals} />}</div>
				<div className="text-xs text-[#6E524D] block">{note}</div>
			</motion.article>
		</SpotlightCard>
	);
}

export default function WorkspaceOverviewPage(){
	const params=useParams();
	const businessId=params.id as string;
	const [cash,setCash]=useState<CashPosition|null>(null);
	const [cashFlow,setCashFlow]=useState<CashFlowStatement|null>(null);
	const [health,setHealth]=useState<BusinessHealthScore|null>(null);
	const [pnl,setPnl]=useState<ProfitAndLossStatement|null>(null);
	const [goals,setGoals]=useState<Goal[]>([]);
	const [invoices,setInvoices]=useState<SalesInvoice[]>([]);
	const [loading,setLoading]=useState(true);

	useEffect(()=>{
		let active=true;
		setLoading(true);
		Promise.all([
			businessApi.getCashPosition(businessId).catch(()=>null),
			businessApi.getCashFlow(businessId).catch(()=>null),
			businessApi.getHealthScore(businessId).catch(()=>null),
			businessApi.getPnL(businessId).catch(()=>null),
			businessApi.listGoals(businessId).catch(()=>[]),
			businessApi.listInvoices(businessId).catch(()=>[]),
		]).then(([cashPosition,flow,healthScore,profitAndLoss,goalList,invoiceList])=>{
			if(!active)return;
			setCash(cashPosition);
			setCashFlow(flow);
			setHealth(healthScore);
			setPnl(profitAndLoss);
			setGoals(goalList);
			setInvoices(invoiceList);
		}).finally(()=>{
			if(active)setLoading(false);
		});
		return()=>{active=false;};
	},[businessId]);

	const activeGoals=useMemo(
		()=>goals.filter((goal)=>!['COMPLETED','CANCELLED','ACHIEVED'].includes(goal.status.toUpperCase())).slice(0,3),
		[goals],
	);
	const recentInvoices=useMemo(()=>invoices.slice(0,4),[invoices]);
	const score=Math.max(0,Math.min(100,Number(health?.["overall_score"]??0)));
	const scoreTone=score>=75?'emerald':score>=50?'amber':'rose';
	const flowMax=Math.max(1,...cashflowFields.map(({key})=>Math.abs(amount(cashFlow?.[key]))));
	const healthPillars=Object.entries(health?.["pillars"]??{}).slice(0,4);
	const cashRunway=Number(health?.["cash_runway_months"]??0);

	return(
		<div className="workspace-cockpit">
			<motion.header
				className="cockpit-page-header flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8"
				initial={{y:12}}
				animate={{y:0}}
				transition={{type:'spring',stiffness:220,damping:26}}
			>
				<div>
					<p className="text-xs font-bold uppercase tracking-widest text-[#C8281E] flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-[#C8281E] inline-block" /> WORKSPACE OVERVIEW</p>
					<h1 className="text-3xl font-extrabold text-[#231412] tracking-tight"><ScrambleText text="Financial cockpit" /></h1>
					<p className="text-sm text-[#6E524D] mt-1">Cash, operating health, and the next decisions in one live view.</p>
				</div>
				<div className="cockpit-header-actions flex items-center gap-3">
					<Link href={`/workspaces/${businessId}/reports`} className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-[#7A5A54] bg-white/90 border border-[#C8281E]/20 rounded-xl hover:text-[#231412] transition-colors"><FileText className="w-4 h-4 shrink-0 text-[#C8281E]" /> Reports</Link>
					<Link href={`/workspaces/${businessId}/sales`} className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-[#C8281E] rounded-xl hover:bg-[#A81E15] transition-colors shadow-sm"><Receipt className="w-4 h-4 shrink-0" /> New sale <ArrowRight className="w-3.5 h-3.5 shrink-0" /></Link>
				</div>
			</motion.header>

			<motion.section
				className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8"
				variants={revealGroup}
				initial="hidden"
				animate="visible"
				aria-label="Financial summary"
			>
				<MetricCard label="Liquid cash" value={loading?null:amount(cash?.["total_liquid_cash_exact"]??cash?.["total_liquid_cash"])} prefix="₹" decimals={2} note="Cash on hand and bank" icon={Wallet} />
				<MetricCard label="Period revenue" value={loading?null:amount(pnl?.["total_revenue_exact"]??pnl?.["total_revenue"])} prefix="₹" decimals={2} note="Posted business activity" icon={TrendingUp} />
				<MetricCard label="Net profit" value={loading?null:amount(pnl?.["net_profit_exact"]??pnl?.["net_profit"])} prefix="₹" decimals={2} note="After operating expenses" icon={CircleDollarSign} />
				<MetricCard label="Business health" value={loading||!health?null:Math.round(score)} suffix=" / 100" note={health?.["grade"]??'Waiting for health data'} icon={ShieldCheck} />
			</motion.section>

			<motion.section
				className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8"
				variants={revealGroup}
				initial="hidden"
				animate="visible"
				aria-label="Financial cockpit details"
			>
				<SpotlightCard className="lg:col-span-2">
					<motion.article variants={revealCard} className="bg-white/92 border border-[#C8281E]/20 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full">
						<div className="flex items-center justify-between pb-4 border-b border-[#C8281E]/10 mb-4">
							<div className="flex items-center gap-3">
								<span className="p-2 rounded-xl bg-[#C8281E]/10 text-[#C8281E]"><Activity className="w-4 h-4 shrink-0" /></span>
								<div><p className="text-xs font-bold uppercase tracking-wider text-[#7A5A54]">Cash movement</p><h2 className="text-lg font-extrabold text-[#231412]">Cash-flow bridge</h2></div>
							</div>
							<span className="text-[10px] font-bold tracking-wider px-2.5 py-1 rounded-full bg-[#C8281E]/10 text-[#C8281E]">CURRENT PERIOD</span>
						</div>
						<div className="flex items-center justify-between py-3 px-4 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12 mb-3">
							<span className="text-sm font-semibold text-[#231412]">Net operating cash flow</span>
							<strong className={`text-base font-bold tabular-nums ${amount(cashFlow?.["net_operating_cash_flow"])>=0?'text-[#C8281E]':'text-[#8A1810]'}`}>
								{currency(cashFlow?.["net_operating_cash_flow"])}
							</strong>
						</div>
						<div className="space-y-2 mb-4">
							{cashflowFields.map(({key,label})=>{
								const val=amount(cashFlow?.[key]);
								const barWidth=val===0?0:Math.max(4,Math.abs(val)/flowMax*100);
								return(
									<div key={key} className="flex flex-col py-2.5 px-4 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12">
										<div className="flex items-center justify-between mb-1.5">
											<span className="text-xs font-semibold text-[#7A5A54]">{label}</span>
											<strong className="text-xs font-bold text-[#C8281E] tabular-nums">{currency(cashFlow?.[key])}</strong>
										</div>
										<div className="h-1.5 w-full bg-[#EFE9E1] rounded-full overflow-hidden" role="progressbar" aria-label={label} aria-valuenow={Math.round(barWidth)} aria-valuemin={0} aria-valuemax={100}>
											<motion.div className="h-full bg-[#C8281E] rounded-full" initial={{width:0}} animate={{width:`${barWidth}%`}} transition={{duration:0.85,delay:0.2,ease:[0.22,1,0.36,1]}} />
										</div>
									</div>
								);
							})}
						</div>
						<div className="flex items-center justify-between pt-3 border-t border-[#C8281E]/10 text-xs text-[#7A5A54]">
							<span>Opening <strong className="text-[#231412] tabular-nums">{currency(cashFlow?.["opening_cash_balance"])}</strong></span>
							<ArrowRight className="w-3.5 h-3.5 text-[#C8281E] shrink-0" />
							<span>Closing <strong className="text-[#231412] tabular-nums">{currency(cashFlow?.["closing_cash_balance"])}</strong></span>
						</div>
					</motion.article>
				</SpotlightCard>

				<SpotlightCard>
					<motion.article variants={revealCard} className="bg-white/92 border border-[#C8281E]/20 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full">
						<div className="flex items-center justify-between pb-4 border-b border-[#C8281E]/10 mb-4">
							<div className="flex items-center gap-3">
								<span className="p-2 rounded-xl bg-[#C8281E]/10 text-[#C8281E]"><ShieldCheck className="w-4 h-4 shrink-0" /></span>
								<div><p className="text-xs font-bold uppercase tracking-wider text-[#7A5A54]">Resilience signals</p><h2 className="text-lg font-extrabold text-[#231412]">Business health</h2></div>
							</div>
							<span className={`text-[10px] font-bold tracking-wider px-2.5 py-1 rounded-full ${scoreTone==='emerald'?'bg-emerald-50 text-emerald-700 border border-emerald-200':scoreTone==='amber'?'bg-amber-50 text-amber-700 border border-amber-200':'bg-rose-50 text-rose-700 border border-rose-200'}`}>{health?.["grade"]??'Awaiting data'}</span>
						</div>
						<div className="flex items-center gap-5 my-3">
							<div className="relative w-24 h-24 shrink-0 flex items-center justify-center">
								<svg className="w-24 h-24 -rotate-90" viewBox="0 0 112 112" aria-hidden="true">
									<circle cx="56" cy="56" r="47" stroke="#EFE9E1" strokeWidth="8" fill="none" />
									<motion.circle
										cx="56" cy="56" r="47" stroke="#C8281E" strokeWidth="8" strokeLinecap="round" fill="none"
										initial={{strokeDashoffset:295.3}}
										animate={{strokeDashoffset:295.3-(295.3*score)/100}}
										strokeDasharray={295.3}
										transition={{duration:1.1,delay:0.25,ease:'easeOut'}}
									/>
								</svg>
								<div className="absolute inset-0 flex flex-col items-center justify-center text-center">
									<strong className="text-xl font-extrabold text-[#231412] leading-none">{loading||!health?'—':Math.round(score)}</strong>
									<span className="text-[9px] font-bold tracking-wider text-[#7A5A54] mt-0.5">HEALTH</span>
								</div>
							</div>
							<div className="flex-1 min-w-0">
								<strong className="text-sm font-bold text-[#231412] block truncate">{health?.["classification"]??health?.["grade"]??'Building baseline'}</strong>
								<p className="text-xs text-[#6E524D] mt-1 line-clamp-2">{health?.["priority_recommendations"]?.[0]??health?.["identified_risks"]?.[0]??'Post transactions to unlock workspace health guidance.'}</p>
								<div className="flex items-center gap-1.5 text-xs text-[#C8281E] font-medium mt-2"><Activity className="w-3.5 h-3.5 shrink-0" /><span>{cashRunway?`${cashRunway.toFixed(1)} mo runway`:'Runway unavailable'}</span></div>
							</div>
						</div>
						<div className="space-y-2 mt-4 pt-3 border-t border-[#C8281E]/10">
							{healthPillars.map(([pillarName,pillar],index)=>{
								const percentage=pillar.max>0?Math.max(0,Math.min(100,pillar.score/pillar.max*100)):0;
								return(
									<div key={pillarName} className="text-xs">
										<div className="flex items-center justify-between mb-1">
											<span className="text-[#7A5A54] capitalize">{pillarName.replaceAll('_',' ')}</span>
											<strong className="text-[#231412] font-semibold">{Math.round(pillar.score)}</strong>
										</div>
										<div className="h-1.5 w-full bg-[#EFE9E1] rounded-full overflow-hidden">
											<motion.div className="h-full bg-[#C8281E] rounded-full" initial={{width:0}} animate={{width:`${percentage}%`}} transition={{duration:0.7,delay:0.35+index*0.1,ease:'easeOut'}} />
										</div>
									</div>
								);
							})}
						</div>
					</motion.article>
				</SpotlightCard>

				<SpotlightCard>
					<motion.article variants={revealCard} className="bg-white/92 border border-[#C8281E]/20 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full">
						<div className="flex items-center justify-between pb-4 border-b border-[#C8281E]/10 mb-4">
							<div className="flex items-center gap-3">
								<span className="p-2 rounded-xl bg-[#C8281E]/10 text-[#C8281E]"><BarChart3 className="w-4 h-4 shrink-0" /></span>
								<div><p className="text-xs font-bold uppercase tracking-wider text-[#7A5A54]">Liquidity composition</p><h2 className="text-lg font-extrabold text-[#231412]">Working capital</h2></div>
							</div>
							<Link href={`/workspaces/${businessId}/finance`} aria-label="Open finance" className="p-1.5 rounded-lg text-[#7A5A54] hover:text-[#C8281E] hover:bg-[#C8281E]/10 transition-colors"><ArrowRight className="w-4 h-4 shrink-0" /></Link>
						</div>
						<div className="p-4 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12 mb-4">
							<span className="text-xs font-semibold text-[#7A5A54] block">Net liquid working capital</span>
							<strong className="text-xl font-extrabold text-[#231412] block mt-1 tabular-nums">{currency(cash?.["net_liquid_working_capital_exact"]??cash?.["net_liquid_working_capital"])}</strong>
						</div>
						<div className="grid grid-cols-2 gap-3">
							<div className="p-3 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12">
								<span className="text-[11px] font-semibold text-[#7A5A54] block">Receivables</span>
								<strong className="text-sm font-extrabold text-[#231412] block my-0.5 tabular-nums">{currency(cash?.["total_receivables_exact"]??cash?.["total_receivables"])}</strong>
								<small className="text-[10px] text-[#6E524D] flex items-center gap-1"><ArrowDownLeft className="w-3 h-3 text-emerald-600 shrink-0" /> Collections</small>
							</div>
							<div className="p-3 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12">
								<span className="text-[11px] font-semibold text-[#7A5A54] block">Payables</span>
								<strong className="text-sm font-extrabold text-[#231412] block my-0.5 tabular-nums">{currency(cash?.["total_payables_exact"]??cash?.["total_payables"])}</strong>
								<small className="text-[10px] text-[#6E524D] flex items-center gap-1"><ArrowUpRight className="w-3 h-3 text-[#C8281E] shrink-0" /> Obligations</small>
							</div>
						</div>
					</motion.article>
				</SpotlightCard>

				<SpotlightCard>
					<motion.article variants={revealCard} className="bg-white/92 border border-[#C8281E]/20 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full">
						<div className="flex items-center justify-between pb-4 border-b border-[#C8281E]/10 mb-4">
							<div className="flex items-center gap-3">
								<span className="p-2 rounded-xl bg-[#C8281E]/10 text-[#C8281E]"><Target className="w-4 h-4 shrink-0" /></span>
								<div><p className="text-xs font-bold uppercase tracking-wider text-[#7A5A54]">Progress against plan</p><h2 className="text-lg font-extrabold text-[#231412]">Active goals</h2></div>
							</div>
							<Link href={`/workspaces/${businessId}/goals`} className="text-xs font-bold text-[#C8281E] hover:underline flex items-center gap-1">All goals <ArrowRight className="w-3 h-3 shrink-0" /></Link>
						</div>
						{activeGoals.length?(
							<div className="space-y-3">
								{activeGoals.map((goal,index)=>(
									<div className="p-3 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12" key={goal.id}>
										<div className="flex items-center justify-between mb-1">
											<strong className="text-xs font-bold text-[#231412] truncate max-w-[140px]">{goal.title}</strong>
											<span className="text-xs font-extrabold text-[#C8281E]">{Math.round(goal.progress_pct)}%</span>
										</div>
										<span className="text-[11px] text-[#7A5A54] block mb-2 tabular-nums">{currency(goal.current_amount_exact??goal.current_amount)} of {currency(goal.target_amount_exact??goal.target_amount)}</span>
										<div className="h-1.5 w-full bg-[#EFE9E1] rounded-full overflow-hidden">
											<motion.div className="h-full bg-[#C8281E] rounded-full" initial={{width:0}} animate={{width:`${Math.max(0,Math.min(100,goal.progress_pct))}%`}} transition={{duration:0.8,delay:0.25+index*0.12}} />
										</div>
									</div>
								))}
							</div>
						):(
							<div className="flex flex-col items-center justify-center py-8 text-center text-[#7A5A54]">
								<Target className="w-8 h-8 text-[#C8281E]/40 mb-2 shrink-0" />
								<span className="text-xs font-medium">No active goals yet</span>
								<Link href={`/workspaces/${businessId}/goals`} className="mt-2 text-xs font-bold text-[#C8281E] hover:underline flex items-center gap-1">Set a milestone <ArrowRight className="w-3 h-3 shrink-0" /></Link>
							</div>
						)}
					</motion.article>
				</SpotlightCard>

				<SpotlightCard>
					<motion.article variants={revealCard} className="bg-white/92 border border-[#C8281E]/20 rounded-2xl p-6 shadow-sm flex flex-col justify-between h-full">
						<div className="flex items-center justify-between pb-4 border-b border-[#C8281E]/10 mb-4">
							<div className="flex items-center gap-3">
								<span className="p-2 rounded-xl bg-[#C8281E]/10 text-[#C8281E]"><Receipt className="w-4 h-4 shrink-0" /></span>
								<div><p className="text-xs font-bold uppercase tracking-wider text-[#7A5A54]">Recent activity</p><h2 className="text-lg font-extrabold text-[#231412]">Sales invoices</h2></div>
							</div>
							<Link href={`/workspaces/${businessId}/sales`} className="text-xs font-bold text-[#C8281E] hover:underline flex items-center gap-1">View sales <ArrowRight className="w-3 h-3 shrink-0" /></Link>
						</div>
						{recentInvoices.length?(
							<div className="space-y-2">
								{recentInvoices.map((invoice)=>(
									<div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12" key={invoice.id}>
										<div className="flex items-center gap-2.5 min-w-0">
											<span className="p-1.5 rounded-lg bg-[#C8281E]/10 text-[#C8281E]"><Receipt className="w-3.5 h-3.5 shrink-0" /></span>
											<div className="truncate"><strong className="text-xs font-bold text-[#231412] block truncate">{invoice.invoice_number}</strong><small className="text-[10px] text-[#7A5A54]">{new Date(invoice.invoice_date).toLocaleDateString()}</small></div>
										</div>
										<div className="text-right ml-2 shrink-0">
											<strong className="text-xs font-extrabold text-[#231412] block tabular-nums">{currency(invoice.total_amount_exact??invoice.total_amount)}</strong>
											<span className="text-[10px] font-semibold text-[#C8281E] uppercase tracking-wider">{invoice.status.replaceAll('_',' ')}</span>
										</div>
									</div>
								))}
							</div>
						):(
							<div className="flex flex-col items-center justify-center py-8 text-center text-[#7A5A54]">
								<Receipt className="w-8 h-8 text-[#C8281E]/40 mb-2 shrink-0" />
								<span className="text-xs font-medium">No invoices recorded yet</span>
								<Link href={`/workspaces/${businessId}/sales`} className="mt-2 text-xs font-bold text-[#C8281E] hover:underline flex items-center gap-1">Create a sale <ArrowRight className="w-3 h-3 shrink-0" /></Link>
							</div>
						)}
					</motion.article>
				</SpotlightCard>
			</motion.section>

			<section className="p-6 bg-white/92 border border-[#C8281E]/20 rounded-2xl shadow-sm" aria-label="Workspace shortcuts">
				<div className="mb-4">
					<p className="text-xs font-bold uppercase tracking-widest text-[#C8281E] flex items-center gap-2 mb-1"><span className="w-2 h-2 rounded-full bg-[#C8281E] inline-block" /> MOVE THE BUSINESS FORWARD</p>
					<h2 className="text-xl font-extrabold text-[#231412]">Where would you like to go next?</h2>
				</div>
				<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
					<Link href={`/workspaces/${businessId}/purchases`} className="flex items-center justify-between p-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12 hover:border-[#C8281E]/40 text-[#231412] font-semibold text-xs transition-colors group">
						<span className="flex items-center gap-2.5"><ShoppingCart className="w-4 h-4 text-[#C8281E] shrink-0" /> Record purchase</span>
						<ArrowRight className="w-3.5 h-3.5 text-[#7A5A54] group-hover:text-[#C8281E] group-hover:translate-x-0.5 transition-all shrink-0" />
					</Link>
					<Link href={`/workspaces/${businessId}/analytics`} className="flex items-center justify-between p-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12 hover:border-[#C8281E]/40 text-[#231412] font-semibold text-xs transition-colors group">
						<span className="flex items-center gap-2.5"><TrendingUp className="w-4 h-4 text-[#C8281E] shrink-0" /> Explore analytics</span>
						<ArrowRight className="w-3.5 h-3.5 text-[#7A5A54] group-hover:text-[#C8281E] group-hover:translate-x-0.5 transition-all shrink-0" />
					</Link>
					<Link href={`/workspaces/${businessId}/decisions`} className="flex items-center justify-between p-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12 hover:border-[#C8281E]/40 text-[#231412] font-semibold text-xs transition-colors group">
						<span className="flex items-center gap-2.5"><BrainCircuit className="w-4 h-4 text-[#C8281E] shrink-0" /> Evaluate a decision</span>
						<ArrowRight className="w-3.5 h-3.5 text-[#7A5A54] group-hover:text-[#C8281E] group-hover:translate-x-0.5 transition-all shrink-0" />
					</Link>
					<Link href={`/workspaces/${businessId}/agent`} className="flex items-center justify-between p-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/12 hover:border-[#C8281E]/40 text-[#231412] font-semibold text-xs transition-colors group">
						<span className="flex items-center gap-2.5"><Bot className="w-4 h-4 text-[#C8281E] shrink-0" /> Ask the investigator</span>
						<ArrowRight className="w-3.5 h-3.5 text-[#7A5A54] group-hover:text-[#C8281E] group-hover:translate-x-0.5 transition-all shrink-0" />
					</Link>
				</div>
			</section>
		</div>
	);
}
