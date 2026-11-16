'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {FormEvent,useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {AnimatePresence,motion,useReducedMotion} from 'framer-motion';
import gsap from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
import {
	Archive,
	ArchiveRestore,
	ArrowRight,
	Building2,
	ChevronDown,
	Layers,
	LogOut,
	Plus,
	RefreshCw,
	Trash2,
	X,
} from 'lucide-react';
import {businessApi,BusinessWorkspace} from '../../lib/business-api';
import {getCurrentUser,logoutUser,UserProfile} from '../../lib/api';
import {useToast} from '@/components/ui';
import {ArthLensBrandMark} from '../../components/motion/ArthLensBrandMark';
import {KineticVaultLoader} from '../../components/motion/KineticVaultLoader';

export default function WorkspacesPage(){
	const router=useRouter();
	const {toast}=useToast();
	const prefersReducedMotion=useReducedMotion();
	const [workspaces,setWorkspaces]=useState<BusinessWorkspace[]>([]);
	const [activeTab,setActiveTab]=useState<'active'|'archived'>('active');
	const [loading,setLoading]=useState(true);
	const [authChecking,setAuthChecking]=useState(true);
	const [profile,setProfile]=useState<UserProfile|null>(null);
	const [drawerOpen,setDrawerOpen]=useState(false);
	const [name,setName]=useState('');
	const [industry,setIndustry]=useState('');
	const [address,setAddress]=useState('');
	const [currency,setCurrency]=useState('INR');
	const [initialCash,setInitialCash]=useState('100000');
	const [description,setDescription]=useState('');
	const [creating,setCreating]=useState(false);

	const containerRef=useRef<HTMLDivElement>(null);
	const tileRefs=useRef<Array<HTMLElement|null>>([]);

	const loadWorkspaces=async()=>{
		setLoading(true);
		try{
			const list=await businessApi.listWorkspaces();
			setWorkspaces(list);
		}catch(err){
			toast.error('Failed to load workspaces: '+(err instanceof Error?err.message:'Unknown error'));
		}finally{
			setLoading(false);
		}
	};

	useEffect(()=>{
		let active=true;
		setAuthChecking(true);
		getCurrentUser().then(async(user)=>{
			if(!active)return;
			if(!user){
				if(typeof window!=='undefined'){
					localStorage.removeItem('arthlens_token');
				}
				router.replace('/login');
				return;
			}
			setProfile(user);
			setAuthChecking(false);
			try{
				const list=await businessApi.listWorkspaces();
				if(active)setWorkspaces(list);
			}catch{
				if(active)setWorkspaces([]);
			}finally{
				if(active)setLoading(false);
			}
		}).catch(()=>{
			if(!active)return;
			if(typeof window!=='undefined'){
				localStorage.removeItem('arthlens_token');
			}
			router.replace('/login');
		});
		return()=>{active=false;};
	},[router]);

	const activeWorkspaces=workspaces.filter((w)=>!w.is_archived);
	const archivedWorkspaces=workspaces.filter((w)=>Boolean(w.is_archived));
	const displayedWorkspaces=activeTab==='active'?activeWorkspaces:archivedWorkspaces;

	useEffect(()=>{
		if(prefersReducedMotion||typeof window==='undefined'||authChecking)return;
		gsap.registerPlugin(ScrollTrigger);
		const ctx=gsap.context(()=>{
			displayedWorkspaces.forEach((wsItem,index)=>{
				const tile=tileRefs.current[index];
				if(!tile)return;
				gsap.fromTo(tile,
					{
						y:40,
						rotateX:6,
						scale:0.96,
					},
					{
						y:0,
						rotateX:0,
						scale:1,
						duration:0.55,
						ease:'power2.out',
						clearProps:'transform',
						scrollTrigger:{
							trigger:tile,
							start:'top 92%',
							once:true,
						},
					}
				);
			});
		},containerRef);
		return()=>ctx.revert();
	},[displayedWorkspaces,prefersReducedMotion,authChecking]);

	const handleEnterWorkspace=(workspaceId:string)=>{
		router.push('/workspaces/'+workspaceId);
	};

	const handleToggleArchive=async(workspaceId:string,willArchive:boolean,workspaceName:string)=>{
		const confirmMsg=willArchive
			?`Archive enterprise "${workspaceName}"? It will be hidden from active workspaces and placed in read-only audit mode.`
			:`Restore enterprise "${workspaceName}" back to active workspaces?`;
		if(!window.confirm(confirmMsg))return;
		try{
			await businessApi.archiveWorkspace(workspaceId,willArchive);
			toast.success(willArchive?`"${workspaceName}" archived`: `"${workspaceName}" restored to active`);
			await loadWorkspaces();
		}catch(err){
			toast.error('Failed to change archive state: '+(err instanceof Error?err.message:'Unknown error'));
		}
	};

	const handleDeleteWorkspace=async(workspaceId:string,workspaceName:string)=>{
		const confirmMsg=`PERMANENTLY DELETE enterprise "${workspaceName}"?\n\nThis will purge all journal entries, FIFO inventory lots, invoices, and decisions. This action CANNOT be undone.\n\nClick OK to permanently delete.`;
		if(!window.confirm(confirmMsg))return;
		try{
			await businessApi.deleteWorkspace(workspaceId);
			toast.success(`Enterprise "${workspaceName}" deleted permanently`);
			await loadWorkspaces();
		}catch(err){
			toast.error('Failed to delete workspace: '+(err instanceof Error?err.message:'Unknown error'));
		}
	};

	const handleLogout=async()=>{
		await logoutUser();
		if(typeof window!=='undefined'){
			localStorage.removeItem('arthlens_token');
		}
		router.replace('/login');
	};

	const createWorkspace=async(event:FormEvent)=>{
		event.preventDefault();
		if(!name.trim())return;
		setCreating(true);
		try{
			const created=await businessApi.createWorkspace({
				name:name.trim(),
				industry:industry.trim()||'General Commerce',
				currency:currency.trim()||'INR',
				address:address.trim()||undefined,
			});
			const initCashNum=parseFloat(initialCash);
			if(!isNaN(initCashNum)&&initCashNum>0){
				try{
					await businessApi.recordIncome(created.id,{
						source:"Owner's Opening Capital Infusion",
						category:'CAPITAL_INFUSION',
						amount:initCashNum,
						payment_method:'CASH',
						date:new Date().toISOString().slice(0,10),
					});
				}catch(cashErr){
					console.error('Failed to seed initial cash:',cashErr);
				}
			}
			toast.success(`Business ${created.name} successfully established with opening cash ₹${initCashNum||0}!`);
			setDrawerOpen(false);
			setName('');
			setIndustry('');
			setAddress('');
			setDescription('');
			setInitialCash('100000');
			setCurrency('INR');
			setActiveTab('active');
			await loadWorkspaces();
		}catch(err){
			toast.error('Failed to create workspace: '+(err instanceof Error?err.message:'Unknown error'));
		}finally{
			setCreating(false);
		}
	};

	if(authChecking){
		return <KineticVaultLoader label="AUTHENTICATING SESSION..." />;
	}

	return(
		<div className="relative min-h-screen w-full bg-transparent text-[#231412] select-none overflow-x-hidden">
			<header className="fixed top-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-b-2 border-[#231412] px-6 md:px-12 py-3.5 flex items-center justify-between shadow-sm">
				<div className="flex items-center gap-4">
					<Link href="/" className="brand-lockup flex items-center gap-2">
						<ArthLensBrandMark />
					</Link>
					<span className="h-5 w-px bg-[#231412]/20 hidden sm:block" />
					<span className="text-xs font-mono text-[#5C403B] uppercase tracking-wider hidden md:inline font-bold">
						ARTHLENS INTELLIGENCE · WORKSPACE CHRONICLE
					</span>
				</div>
				<div className="flex items-center gap-3">
					<span className="px-3 py-1 rounded-none bg-white border border-[#231412]/30 text-xs font-mono text-[#231412] shadow-sm hidden sm:inline">
						{profile?.email||'Authenticated'}
					</span>
					<MotionButton
						type="button"
						onClick={()=>setDrawerOpen(true)}
						className="inline-flex items-center gap-2 px-4 py-2 bg-[#C8281E] text-white font-mono text-xs font-bold shadow-[2px_2px_0px_#231412] hover:bg-[#A81E15] border border-[#231412] transition-all"
					>
						<Plus size={14} /> Establish Enterprise
					</MotionButton>
					<MotionButton
						type="button"
						onClick={handleLogout}
						className="p-2 bg-white border border-[#231412]/30 text-[#6E524D] hover:text-[#C8281E] hover:border-[#C8281E] transition-all shadow-sm"
						aria-label="Sign out"
					>
						<LogOut size={16} />
					</MotionButton>
				</div>
			</header>

			<main className="pt-28 pb-24 max-w-6xl mx-auto px-6 relative z-10" ref={containerRef}>
				<div className="text-center max-w-2xl mx-auto mb-8">
					<div className="inline-flex items-center gap-2 px-3 py-1 rounded-none bg-[#C8281E]/10 border border-[#C8281E]/20 text-[10px] font-mono font-bold tracking-widest text-[#C8281E] uppercase mb-3">
						<Layers size={12} /> CHRONICLE OF COMMERCE
					</div>
					<h1 className="text-3xl md:text-5xl font-black tracking-tight text-[#231412]">
						Select Your <span className="text-[#C8281E]">ArthLens</span> Workspace
					</h1>
					<p className="mt-3 text-sm text-[#6E524D] leading-relaxed">
						Each workspace is an autonomous operating system: double-entry Khata, FIFO lot reconciliation, versioned decisions, and private agent oversight.
					</p>
				</div>

				<div className="flex items-center justify-between flex-wrap gap-4 mb-6 border-b-2 border-[#231412] pb-3">
					<div className="flex items-center gap-2">
						<button
							type="button"
							onClick={()=>setActiveTab('active')}
							className={`px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider border-2 transition-all ${activeTab==='active'?'bg-[#231412] text-white border-[#231412] shadow-[3px_3px_0px_#C8281E]':'bg-[#FAF7F2] text-[#231412] border-[#231412]/40 hover:border-[#231412]'}`}
						>
							Active Enterprises ({activeWorkspaces.length})
						</button>
						<button
							type="button"
							onClick={()=>setActiveTab('archived')}
							className={`px-4 py-2 font-mono text-xs font-bold uppercase tracking-wider border-2 transition-all ${activeTab==='archived'?'bg-[#231412] text-white border-[#231412] shadow-[3px_3px_0px_#C8281E]':'bg-[#FAF7F2] text-[#5C403B] border-[#231412]/40 hover:border-[#231412]'}`}
						>
							Archived ({archivedWorkspaces.length})
						</button>
					</div>

					<span className="text-[10px] font-mono text-[#5C403B]">
						{activeTab==='active'
							?`${activeWorkspaces.length} ACTIVE LEDGERS ONLINE`
							:`${archivedWorkspaces.length} ARCHIVED IN AUDIT ARCHIVE`}
					</span>
				</div>

				{loading?(
					<div className="p-16 text-center text-xs font-mono text-[#7A5A54]">
						<RefreshCw size={24} className="animate-spin mx-auto mb-3 text-[#C8281E]" />
						SYNCHRONIZING ENTERPRISE TOPOLOGY...
					</div>
				):displayedWorkspaces.length===0?(
					<div className="p-16 rounded-none bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412] text-center max-w-lg mx-auto">
						<div className="w-16 h-16 bg-[#FAF7F2] border-2 border-[#231412] flex items-center justify-center text-[#C8281E] mx-auto mb-4 shadow-[2px_2px_0px_#231412]">
							<Building2 size={28} />
						</div>
						<h2 className="text-xl font-black text-[#231412] mb-2">
							{activeTab==='active'?'No Active Workspaces Found':'No Archived Workspaces'}
						</h2>
						<p className="text-xs text-[#6E524D] mb-6">
							{activeTab==='active'
								?(archivedWorkspaces.length>0
									?`All your workspaces are currently archived (${archivedWorkspaces.length} in archive). Check the Archived tab to restore them.`
									:'Establish your first enterprise to launch your double-entry Khata and analytics.')
								:'Workspaces you archive will be stored here in read-only audit mode.'}
						</p>
						{activeTab==='active'&&(
							<MotionButton
								type="button"
								onClick={()=>setDrawerOpen(true)}
								className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#C8281E] text-white font-mono text-xs font-bold border-2 border-[#231412] shadow-[3px_3px_0px_#231412] hover:bg-[#A81E15] transition-all"
							>
								<Plus size={14} /> Establish New Enterprise
							</MotionButton>
						)}
					</div>
				):(
					<div className="space-y-6">
						{displayedWorkspaces.map((ws,index)=>{
							const wsRecord=ws as unknown as Record<string,unknown>;
							const wsId=String(wsRecord["workspace_id"]||ws.id);
							const isArchived=Boolean(ws.is_archived);
							return(
								<article
									key={wsId}
									ref={(node)=>{tileRefs.current[index]=node;}}
									data-testid={`workspace-card-${wsId}`}
									className="group p-7 rounded-none bg-white border-2 border-[#231412] shadow-[4px_4px_0px_#231412] hover:shadow-[6px_6px_0px_#C8281E] transition-all relative overflow-hidden"
								>
									<div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
										<div className="space-y-2 flex-1 min-w-0">
											<div className="flex items-center gap-2 flex-wrap">
												<span className="px-2.5 py-0.5 bg-[#C8281E]/10 text-[#C8281E] font-mono text-[10px] font-bold tracking-wider border border-[#C8281E]/30">
													CHAPTER {String(index+1).padStart(2,'0')}
												</span>
												<span className="px-2.5 py-0.5 bg-[#FAF7F2] text-[#5C403B] font-mono text-[10px] font-bold border border-[#231412]/20">
													{ws.industry||'Commerce'}
												</span>
												<span className="px-2.5 py-0.5 bg-emerald-50 text-emerald-800 font-mono text-[10px] font-bold border border-emerald-300">
													{ws.role||'OWNER'}
												</span>
												{isArchived&&(
													<span className="px-2.5 py-0.5 bg-[#C8281E] text-white font-mono text-[10px] font-bold tracking-widest uppercase border border-[#231412]">
														ARCHIVED (READ-ONLY)
													</span>
												)}
											</div>
											<h2 className="text-2xl font-black text-[#231412] group-hover:text-[#C8281E] transition-colors truncate">
												{ws.name}
											</h2>
											<p className="text-xs text-[#6E524D] line-clamp-2">
												{ws.address||'Autonomous Khata ledger and decision graph.'}
											</p>
										</div>

										<div className="shrink-0 flex items-center gap-2.5 flex-wrap">
											<MotionButton
												type="button"
												onClick={()=>handleEnterWorkspace(wsId)}
												className="inline-flex items-center gap-2 px-4 py-2 bg-[#C8281E] text-white font-mono text-xs font-bold border-2 border-[#231412] shadow-[2px_2px_0px_#231412] hover:bg-[#A81E15] transition-all"
											>
												{isArchived?'Enter Read-Only':'Enter Workspace'} <ArrowRight size={14} />
											</MotionButton>

											<MotionButton
												type="button"
												data-testid={`workspace-archive-${wsId}`}
												onClick={()=>handleToggleArchive(wsId,!isArchived,ws.name)}
												title={isArchived?'Restore to active workspaces':'Archive workspace'}
												className="inline-flex items-center gap-1.5 px-3 py-2 bg-[#FAF7F2] text-[#231412] hover:bg-[#231412] hover:text-white border-2 border-[#231412] font-mono text-xs font-bold transition-colors shadow-[2px_2px_0px_#231412]"
											>
												{isArchived?(
													<>
														<ArchiveRestore size={13} />
														<span>Restore</span>
													</>
												):(
													<>
														<Archive size={13} />
														<span>Archive</span>
													</>
												)}
											</MotionButton>

											<MotionButton
												type="button"
												data-testid={`workspace-delete-${wsId}`}
												onClick={()=>handleDeleteWorkspace(wsId,ws.name)}
												title="Permanently delete workspace"
												className="inline-flex items-center gap-1 px-2.5 py-2 bg-[#FAF7F2] text-[#C8281E] hover:bg-[#C8281E] hover:text-white border-2 border-[#231412] font-mono text-xs font-bold transition-colors shadow-[2px_2px_0px_#231412]"
											>
												<Trash2 size={13} />
											</MotionButton>
										</div>
									</div>
								</article>
							);
						})}
					</div>
				)}
			</main>

			<AnimatePresence>
				{drawerOpen&&(
					<div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#231412]/50 backdrop-blur-sm" onClick={()=>setDrawerOpen(false)}>
						<motion.div
							initial={{opacity:0,scale:0.95,y:20}}
							animate={{opacity:1,scale:1,y:0}}
							exit={{opacity:0,scale:0.95,y:20}}
							transition={{duration:0.25,ease:'easeOut'}}
							className="w-full max-w-lg p-7 rounded-none bg-white border-2 border-[#231412] shadow-[6px_6px_0px_#231412] relative"
							onClick={(e)=>e.stopPropagation()}
						>
							<div className="flex items-center justify-between pb-4 border-b-2 border-[#231412] mb-6">
								<div className="flex items-center gap-2.5">
									<div className="p-2 bg-[#C8281E] text-white border border-[#231412]">
										<Building2 size={18} />
									</div>
									<div>
										<h2 className="text-lg font-black text-[#231412]">Establish New Enterprise</h2>
										<span className="text-[10px] font-mono text-[#5C403B] font-bold">AUTONOMOUS WORKSPACE REGISTRATION</span>
									</div>
								</div>
								<MotionButton
									type="button"
									onClick={()=>setDrawerOpen(false)}
									className="p-1.5 text-[#5C403B] hover:text-[#C8281E] hover:bg-[#FAF7F2] transition-colors border border-transparent hover:border-[#231412]"
								>
									<X size={18} />
								</MotionButton>
							</div>

							<form onSubmit={createWorkspace} data-testid="create-workspace-form" className="space-y-4">
								<div>
									<label className="block text-xs font-mono font-bold text-[#231412] uppercase tracking-wider mb-1.5">
										Enterprise Name *
									</label>
									<input
										type="text"
										required
										data-testid="workspace-name-input"
										value={name}
										onChange={(e)=>setName(e.target.value)}
										placeholder="e.g. Apex Manufacturing Solutions"
										className="w-full h-11 px-3.5 bg-[#FAF7F2] border-2 border-[#231412] text-sm text-[#231412] placeholder-[#5C403B]/60 focus:outline-none focus:border-[#C8281E] font-mono"
									/>
								</div>

								<div>
									<label className="block text-xs font-mono font-bold text-[#231412] uppercase tracking-wider mb-1.5">
										Industry Sector
									</label>
									<input
										type="text"
										data-testid="workspace-description-input"
										value={industry}
										onChange={(e)=>setIndustry(e.target.value)}
										placeholder="e.g. Precision Engineering"
										className="w-full h-11 px-3.5 bg-[#FAF7F2] border-2 border-[#231412] text-sm text-[#231412] placeholder-[#5C403B]/60 focus:outline-none focus:border-[#C8281E] font-mono"
									/>
								</div>

								<div className="grid grid-cols-2 gap-3">
									<div>
										<label className="block text-xs font-mono font-bold text-[#231412] uppercase tracking-wider mb-1.5">
											Currency
										</label>
										<div className="relative">
											<select
												data-testid="workspace-currency-input"
												value={currency}
												onChange={(e)=>setCurrency(e.target.value)}
												className="w-full h-11 pl-3.5 pr-8 bg-[#FAF7F2] border-2 border-[#231412] text-sm text-[#231412] font-mono font-bold focus:outline-none focus:border-[#C8281E] cursor-pointer appearance-none rounded-none"
											>
												<option value="INR">INR (₹) - Indian Rupee</option>
												<option value="USD">USD ($) - US Dollar</option>
												<option value="EUR">EUR (€) - Euro</option>
												<option value="GBP">GBP (£) - British Pound</option>
												<option value="AED">AED (د.إ) - UAE Dirham</option>
												<option value="SGD">SGD (S$) - Singapore Dollar</option>
												<option value="CAD">CAD (C$) - Canadian Dollar</option>
												<option value="AUD">AUD (A$) - Australian Dollar</option>
												<option value="JPY">JPY (¥) - Japanese Yen</option>
											</select>
											<ChevronDown size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#231412] pointer-events-none" />
										</div>
									</div>
									<div>
										<label className="block text-xs font-mono font-bold text-[#231412] uppercase tracking-wider mb-1.5">
											Registered City
										</label>
										<input
											type="text"
											value={address}
											onChange={(e)=>setAddress(e.target.value)}
											placeholder="e.g. Mumbai, MH"
											className="w-full h-11 px-3.5 bg-[#FAF7F2] border-2 border-[#231412] text-sm text-[#231412] focus:outline-none focus:border-[#C8281E] font-mono"
										/>
									</div>
								</div>

								<div>
									<div className="flex items-center justify-between mb-1.5">
										<label className="block text-xs font-mono font-bold text-[#231412] uppercase tracking-wider">
											Initial Liquid Cash in Hand (₹)
										</label>
										<span className="text-[10px] font-mono text-emerald-700 font-bold bg-emerald-50 border border-emerald-300 px-1.5 py-0.5">
											OPENING TREASURY
										</span>
									</div>
									<input
										type="number"
										min="0"
										step="100"
										data-testid="workspace-initial-cash-input"
										value={initialCash}
										onChange={(e)=>setInitialCash(e.target.value)}
										placeholder="e.g. 100000"
										className="w-full h-11 px-3.5 bg-[#FAF7F2] border-2 border-[#231412] text-sm text-[#231412] font-mono font-bold focus:outline-none focus:border-[#C8281E]"
									/>
									<p className="mt-1 text-[11px] font-mono text-[#5C403B]">
										Initial liquid capital deposited to fund purchases and operations immediately upon establishment.
									</p>
								</div>

								<div className="pt-4 flex items-center justify-end gap-3 border-t border-[#231412]/15">
									<MotionButton
										type="button"
										onClick={()=>setDrawerOpen(false)}
										className="px-4 py-2.5 bg-[#FAF7F2] text-xs font-mono font-bold text-[#5C403B] hover:text-[#231412] border-2 border-[#231412]"
									>
										Cancel
									</MotionButton>
									<MotionButton
										type="submit"
										disabled={creating}
										data-testid="create-workspace-submit"
										className="px-5 py-2.5 bg-[#C8281E] text-white font-mono text-xs font-bold border-2 border-[#231412] shadow-[2px_2px_0px_#231412] hover:bg-[#A81E15] transition-all disabled:opacity-60"
									>
										{creating?'Establishing...':'Establish Enterprise'}
									</MotionButton>
								</div>
							</form>
						</motion.div>
					</div>
				)}
			</AnimatePresence>
		</div>
	);
}