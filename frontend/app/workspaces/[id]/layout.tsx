'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {useParams,usePathname,useRouter} from 'next/navigation';
import {AnimatePresence,motion} from 'framer-motion';
import {
	Activity,
	Bot,
	Boxes,
	BrainCircuit,
	Building2,
	ChevronDown,
	FileText,
	LayoutDashboard,
	LogOut,
	Menu,
	Receipt,
	Settings,
	ShoppingCart,
	Target,
	User,
	Users,
	Wallet,
	Workflow,
	BookOpen,
	ScrollText,
	TrendingUp,
	ArrowDownLeft,
	ArrowUpRight,
	X,
} from 'lucide-react';
import {businessApi,BusinessWorkspace,CashPosition} from '../../../lib/business-api';
import {getCurrentUser,logoutUser,UserProfile} from '../../../lib/api';
import {useToast} from '@/components/ui';
import {formatINR} from '../../../lib/money';
import {ArthLensBrandMark} from '../../../components/motion/ArthLensBrandMark';
import {WorkspaceKineticStage} from '../../../components/motion/WorkspaceKineticSurfaces';
import {KineticVaultLoader} from '../../../components/motion/KineticVaultLoader';

const allChapters=[
	{number:'01',label:'Overview',path:'',icon:LayoutDashboard,tag:'CORE'},
	{number:'02',label:'Sales',path:'/sales',icon:Receipt,tag:'OPS'},
	{number:'03',label:'Purchases',path:'/purchases',icon:ShoppingCart,tag:'OPS'},
	{number:'04',label:'Inventory',path:'/inventory',icon:Boxes,tag:'OPS'},
	{number:'05',label:'Khata',path:'/khata',icon:BookOpen,tag:'OPS'},
	{number:'06',label:'Finance',path:'/finance',icon:Wallet,tag:'INTEL'},
	{number:'07',label:'Decisions',path:'/decisions',icon:BrainCircuit,tag:'INTEL'},
	{number:'08',label:'Scenarios',path:'/scenarios',icon:Workflow,tag:'INTEL'},
	{number:'09',label:'Goals',path:'/goals',icon:Target,tag:'INTEL'},
	{number:'10',label:'Analytics',path:'/analytics',icon:TrendingUp,tag:'INTEL'},
	{number:'11',label:'AI Agent',path:'/agent',icon:Bot,tag:'GOV'},
	{number:'12',label:'Customers',path:'/customers',icon:Users,tag:'OPS'},
	{number:'13',label:'Suppliers',path:'/suppliers',icon:Building2,tag:'OPS'},
	{number:'14',label:'Reports',path:'/reports',icon:FileText,tag:'GOV'},
	{number:'15',label:'Audit & Access',path:'/audit',icon:ScrollText,tag:'GOV'},
	{number:'16',label:'Members',path:'/members',icon:Users,tag:'AUTH'},
	{number:'17',label:'Settings',path:'/settings',icon:Settings,tag:'CONF'},
	{number:'18',label:'Constellation',path:'/constellation',icon:Workflow,tag:'MAP'},
];

export default function WorkspaceLayout({children}:{children:React.ReactNode}){
	const {toast}=useToast();
	const params=useParams();
	const pathname=usePathname();
	const router=useRouter();
	const businessId=params.id as string;

	const [authChecking,setAuthChecking]=useState(true);
	const [workspace,setWorkspace]=useState<BusinessWorkspace|null>(null);
	const [workspaces,setWorkspaces]=useState<BusinessWorkspace[]>([]);
	const [cash,setCash]=useState<CashPosition|null>(null);
	const [profile,setProfile]=useState<UserProfile|null>(null);
	const [switcherOpen,setSwitcherOpen]=useState(false);
	const [profileMenuOpen,setProfileMenuOpen]=useState(false);
	const [mobileNavOpen,setMobileNavOpen]=useState(false);
	const [quickJumpOpen,setQuickJumpOpen]=useState(false);
	const [cashModalOpen,setCashModalOpen]=useState(false);
	const [cashActionTab,setCashActionTab]=useState<'inflow'|'outflow'>('inflow');
	const [cashActionAmount,setCashActionAmount]=useState('');
	const [cashActionMethod,setCashActionMethod]=useState('CASH');
	const [cashActionNotes,setCashActionNotes]=useState('');
	const [cashActionCategory,setCashActionCategory]=useState('CAPITAL');
	const [submittingCash,setSubmittingCash]=useState(false);

	const refreshCashPosition=async()=>{
		try{
			const updated=await businessApi.getCashPosition(businessId);
			setCash(updated);
		}catch{}
	};

	useEffect(()=>{
		refreshCashPosition();
		const handleCashUpdated=()=>{
			refreshCashPosition();
		};
		window.addEventListener('arthlens-cash-updated',handleCashUpdated);
		return()=>{
			window.removeEventListener('arthlens-cash-updated',handleCashUpdated);
		};
	},[businessId,pathname]);

	const handleCashAction=async(e:React.FormEvent)=>{
		e.preventDefault();
		const amt=parseFloat(cashActionAmount);
		if(isNaN(amt)||amt<=0){
			toast.error('Please enter a valid positive cash amount.');
			return;
		}
		setSubmittingCash(true);
		try{
			const today=new Date().toISOString().slice(0,10);
			if(cashActionTab==='inflow'){
				await businessApi.recordIncome(businessId,{
					source:cashActionNotes.trim()||'Direct Liquid Cash Inflow',
					category:'CAPITAL_INFUSION',
					amount:amt,
					payment_method:cashActionMethod,
					date:today,
				});
				toast.success(`Successfully injected ₹${amt.toLocaleString('en-IN')} into liquid treasury!`);
			}else{
				await businessApi.recordExpense(businessId,{
					category:cashActionCategory,
					amount:amt,
					payment_method:cashActionMethod,
					date:today,
					description:cashActionNotes.trim()||'Owner Drawing / Cash Outflow',
				});
				toast.success(`Successfully recorded ₹${amt.toLocaleString('en-IN')} cash outflow!`);
			}
			setCashModalOpen(false);
			setCashActionAmount('');
			setCashActionNotes('');
			await refreshCashPosition();
			if(typeof window!=='undefined'){
				window.dispatchEvent(new CustomEvent('arthlens-cash-updated'));
			}
		}catch(err){
			toast.error('Treasury operation failed: '+(err instanceof Error?err.message:'Unknown error'));
		}finally{
			setSubmittingCash(false);
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
				const [current,list,cashPosition]=await Promise.all([
					businessApi.getWorkspace(businessId),
					businessApi.listWorkspaces(),
					businessApi.getCashPosition(businessId).catch(()=>null),
				]);
				if(!active)return;
				setWorkspace(current);
				setWorkspaces(list);
				setCash(cashPosition);
			}catch(err){
				if(active)toast.error('Workspace data load failed: '+(err instanceof Error?err.message:'Unknown error'));
			}
		}).catch(()=>{
			if(!active)return;
			if(typeof window!=='undefined'){
				localStorage.removeItem('arthlens_token');
			}
			router.replace('/login');
		});
		return()=>{active=false;};
	},[businessId,router,toast]);

	useEffect(()=>{
		const onShortcut=(event:KeyboardEvent)=>{
			if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){
				event.preventDefault();
				setQuickJumpOpen((open)=>!open);
			}
			if(event.key==='Escape'){
				setQuickJumpOpen(false);
				setSwitcherOpen(false);
				setProfileMenuOpen(false);
			}
		};
		const onClickOutside=(event:MouseEvent)=>{
			const target=event.target as HTMLElement|null;
			if(!target?.closest('.workspace-nav-popover')){
				setSwitcherOpen(false);
				setProfileMenuOpen(false);
			}
		};
		window.addEventListener('keydown',onShortcut);
		window.addEventListener('click',onClickOutside);
		return()=>{
			window.removeEventListener('keydown',onShortcut);
			window.removeEventListener('click',onClickOutside);
		};
	},[]);

	const handleLogout=async()=>{
		await logoutUser();
		if(typeof window!=='undefined'){
			localStorage.removeItem('arthlens_token');
		}
		router.replace('/login');
	};

	if(authChecking){
		return <KineticVaultLoader label="AUTHENTICATING SESSION & PERMISSIONS..." />;
	}

	return(
		<div className="workspace-shell min-h-screen bg-transparent text-[#231412] flex flex-col select-none">
			<header className="sticky top-0 z-40 h-16 flex items-center justify-between px-6 bg-white/95 backdrop-blur-md border-b-2 border-[#231412] shadow-sm">
				<div className="flex items-center gap-3">
					<MotionButton
						className="mobile-menu md:hidden p-2 rounded-none bg-[#FAF7F2] border border-[#231412] text-[#6E524D] hover:text-[#C8281E]"
						onClick={()=>setMobileNavOpen((open)=>!open)}
						aria-label="Toggle workspace navigation"
					>
						<Menu size={18} />
					</MotionButton>
					<Link href="/workspaces" className="flex items-center gap-2">
						<ArthLensBrandMark compact />
					</Link>
					{cash&&(
						<>
							<span className="h-5 w-px bg-[#231412]/20 hidden sm:block" />
							<MotionButton
								type="button"
								onClick={()=>setCashModalOpen(true)}
								title="Click to manage Treasury and adjust Liquid Cash"
								className="hidden sm:inline-flex items-center gap-3 px-3 py-1.5 bg-[#FAF7F2] border-2 border-[#231412] shadow-[2px_2px_0px_#231412] hover:bg-white hover:border-[#C8281E] cursor-pointer transition-all select-none text-left"
							>
								<span className="flex items-center gap-1.5">
									<span className="w-2 h-2 bg-emerald-600 inline-block border border-[#231412]" />
									<span className="text-[10px] font-mono uppercase font-bold text-[#5C403B]">Liquid cash</span>
									<strong className="text-xs font-mono font-bold text-emerald-800 tabular-nums">
										{formatINR(cash["total_liquid_cash_exact"]??cash["total_liquid_cash"])}
									</strong>
								</span>
								<span className="w-px h-3.5 bg-[#231412]/20" />
								<span className="flex items-center gap-1.5">
									<span className="w-2 h-2 bg-[#C8281E] inline-block border border-[#231412]" />
									<span className="text-[10px] font-mono uppercase font-bold text-[#5C403B]">Receivables</span>
									<strong className="text-xs font-mono font-bold text-[#C8281E] tabular-nums">
										{formatINR(cash["total_receivables_exact"]??cash["total_receivables"])}
									</strong>
								</span>
								<span className="px-1.5 py-0.5 bg-[#231412] text-white text-[9px] font-mono font-bold tracking-wider uppercase">
									TREASURY ⚙
								</span>
							</MotionButton>
						</>
					)}
				</div>

				<div className="flex items-center gap-3">
					<div className="relative workspace-nav-popover">
						<MotionButton
							className="h-9 inline-flex items-center gap-2 px-3 bg-white border-2 border-[#231412] shadow-[2px_2px_0px_#231412] hover:bg-[#FAF7F2] text-left transition-all"
							onClick={(e)=>{e.stopPropagation();setProfileMenuOpen(false);setSwitcherOpen((open)=>!open);}}
							aria-expanded={switcherOpen}
							aria-label="Switch workspace"
						>
							<strong className="text-xs sm:text-sm font-extrabold text-[#231412] tracking-tight whitespace-nowrap">
								{workspace?.name||'Active Enterprise'}
							</strong>
							{workspace?.industry&&(
								<span className="text-[11px] font-semibold text-[#5C403B] bg-[#FAF7F2] border border-[#231412]/30 px-2 py-0.5 whitespace-nowrap capitalize">
									{workspace.industry}
								</span>
							)}
							<ChevronDown size={14} className="text-[#231412] shrink-0" />
						</MotionButton>

						{switcherOpen&&(
							<div className="absolute right-0 top-full mt-2 w-64 bg-white border-2 border-[#231412] p-2 shadow-[4px_4px_0px_#231412] z-50 flex flex-col gap-1">
								<strong className="px-3 py-1 text-[10px] font-mono uppercase text-[#5C403B] font-bold">Active Workspaces</strong>
								{workspaces.filter((w)=>!w.is_archived).map((item)=>{
									const itemRecord=item as unknown as Record<string,unknown>;
									const itemId=String(itemRecord["workspace_id"]||item.id);
									return(
										<MotionButton
											key={itemId}
											className="w-full text-left px-3 py-2 text-xs text-[#231412] hover:text-white hover:bg-[#231412] flex items-center justify-between font-mono transition-colors"
											onClick={()=>{setSwitcherOpen(false);router.push('/workspaces/'+itemId);}}
										>
											<span className="truncate">{item.name}</span>
											{itemId===businessId&&<span className="text-[9px] font-mono text-emerald-600 font-bold ml-1">ACTIVE</span>}
										</MotionButton>
									);
								})}
								{workspaces.some((w)=>w.is_archived)&&(
									<>
										<div className="border-t border-[#231412]/20 my-1" />
										<strong className="px-3 py-1 text-[9px] font-mono uppercase text-[#C8281E] font-bold">Archived Workspaces</strong>
										{workspaces.filter((w)=>w.is_archived).map((item)=>{
											const itemRecord=item as unknown as Record<string,unknown>;
											const itemId=String(itemRecord["workspace_id"]||item.id);
											return(
												<MotionButton
													key={itemId}
													className="w-full text-left px-3 py-1.5 text-xs text-[#5C403B] hover:text-[#C8281E] hover:bg-[#FAF7F2] flex items-center justify-between font-mono transition-colors opacity-75"
													onClick={()=>{setSwitcherOpen(false);router.push('/workspaces/'+itemId);}}
												>
													<span className="truncate">{item.name}</span>
													<span className="text-[8px] font-mono text-[#C8281E] border border-[#C8281E]/40 px-1 py-0.2">ARCHIVED</span>
												</MotionButton>
											);
										})}
									</>
								)}
								<Link href="/workspaces" onClick={()=>setSwitcherOpen(false)} className="px-3 py-1.5 mt-1 border-t border-[#231412]/20 text-[11px] text-[#C8281E] font-mono font-bold hover:underline flex items-center justify-between">
									Manage Workspaces <span>↗</span>
								</Link>
							</div>
						)}
					</div>

					<div className="relative workspace-nav-popover">
						<MotionButton
							type="button"
							className="flex items-center justify-center w-9 h-9 bg-[#C8281E] text-white border-2 border-[#231412] shadow-[2px_2px_0px_#231412] hover:bg-[#A81E15] transition-all cursor-pointer"
							data-testid="profile-galaxy-portal"
							onClick={(e)=>{e.stopPropagation();setSwitcherOpen(false);setProfileMenuOpen((open)=>!open);}}
							aria-expanded={profileMenuOpen}
							aria-label="User profile and account options"
						>
							<span className="font-extrabold text-xs font-mono">
								{profile?.full_name?.slice(0,1).toUpperCase()||profile?.email?.slice(0,1).toUpperCase()||'U'}
							</span>
						</MotionButton>

						{profileMenuOpen&&(
							<div className="absolute right-0 top-full mt-2 w-64 bg-white border-2 border-[#231412] p-3 shadow-[4px_4px_0px_#231412] z-50 flex flex-col gap-2">
								<div className="pb-2.5 border-b-2 border-[#231412]/15">
									<div className="flex items-center gap-2.5">
										<span className="w-8 h-8 bg-[#C8281E] text-white font-bold text-xs flex items-center justify-center border border-[#231412] shrink-0">
											{profile?.full_name?.slice(0,1).toUpperCase()||profile?.email?.slice(0,1).toUpperCase()||'U'}
										</span>
										<div className="flex flex-col min-w-0">
											<strong className="text-xs text-[#231412] font-mono font-bold truncate">
												{profile?.full_name||profile?.email?.split('@')[0]||'Operator'}
											</strong>
											<span className="text-[10px] text-[#7A5A54] font-mono truncate">
												{profile?.email||''}
											</span>
										</div>
									</div>
									{profile?.roles?.[0]&&(
										<div className="mt-2 flex items-center gap-1.5">
											<span className="px-1.5 py-0.5 bg-[#FAF7F2] border border-[#231412] text-[9px] font-mono font-bold uppercase text-[#C8281E]">
												{profile.roles[0]}
											</span>
											<span className="text-[9px] font-mono text-[#5C403B] font-semibold">VERIFIED OPERATOR</span>
										</div>
									)}
								</div>

								<div className="flex flex-col gap-1 py-1">
									<Link
										href={`/workspaces/${businessId}/settings`}
										onClick={()=>setProfileMenuOpen(false)}
										className="px-3 py-2 text-xs font-mono font-bold text-[#231412] hover:bg-[#231412] hover:text-white transition-colors flex items-center gap-2 border border-transparent hover:border-[#231412]"
									>
										<User size={14} className="shrink-0" />
										<span>Profile & Settings</span>
									</Link>
									<Link
										href="/workspaces"
										onClick={()=>setProfileMenuOpen(false)}
										className="px-3 py-2 text-xs font-mono font-bold text-[#231412] hover:bg-[#231412] hover:text-white transition-colors flex items-center gap-2 border border-transparent hover:border-[#231412]"
									>
										<Building2 size={14} className="shrink-0" />
										<span>All Workspaces</span>
									</Link>
								</div>

								<div className="pt-2 border-t-2 border-[#231412]/15">
									<MotionButton
										type="button"
										onClick={()=>{setProfileMenuOpen(false);void handleLogout();}}
										className="w-full px-3 py-2 text-xs font-mono font-bold text-white bg-[#C8281E] hover:bg-[#A81E15] border border-[#231412] transition-colors flex items-center justify-center gap-2 shadow-[2px_2px_0px_#231412]"
										aria-label="Sign out"
									>
										<LogOut size={14} />
										<span>SIGN OUT</span>
									</MotionButton>
								</div>
							</div>
						)}
					</div>
				</div>
			</header>

			<div className="flex min-h-[calc(100vh-4rem)] w-full relative z-10">
				<AnimatePresence>
					{mobileNavOpen&&(
						<MotionButton
							className="fixed inset-0 z-40 bg-[#231412]/30 backdrop-blur-sm md:hidden"
							aria-label="Close navigation"
							onClick={()=>setMobileNavOpen(false)}
							initial={{opacity:0}}
							animate={{opacity:1}}
							exit={{opacity:0}}
						/>
					)}
				</AnimatePresence>

				<aside className={`workspace-sidebar fixed md:sticky top-16 z-30 h-[calc(100vh-4rem)] w-64 shrink-0 bg-white/90 backdrop-blur-md border-r border-[#C8281E]/15 p-4 flex flex-col justify-between overflow-y-auto transition-transform duration-300 ${mobileNavOpen?'translate-x-0':'-translate-x-full md:translate-x-0'}`}>
					<div className="overflow-y-auto flex-1 pr-1 space-y-4">
						<div className="space-y-1">
							<div className="text-[10px] font-mono tracking-widest text-[#C8281E] px-3 py-1 font-bold">
								CHRONICLE CHAPTERS
							</div>
							{allChapters.map((item)=>{
								const href='/workspaces/'+businessId+item.path;
								const active=item.path===''?pathname===href:pathname===href||pathname.startsWith(href+'/');
								const Icon=item.icon;
								return(
									<Link
										href={href}
										key={item.label}
										onClick={()=>setMobileNavOpen(false)}
										aria-current={active?'page':undefined}
										className={`relative flex items-center gap-2.5 px-3 py-2 text-xs select-none transition-colors ${active?'bg-[#C8281E] text-white border-2 border-[#231412] shadow-[3px_3px_0px_#231412] font-bold':'bg-[#FFFFFF] text-[#231412] border-2 border-transparent hover:border-[#231412] hover:bg-[#FAF7F2] font-semibold'}`}
									>
										<span className={`font-mono text-[10px] ${active?'text-white/80':'text-[#9A7E78]'}`}>[{item.number}]</span>
										<Icon size={15} className={`shrink-0 ${active?'text-white':'text-[#7A5A54]'}`} />
										<span className="flex-1 truncate">{item.label}</span>
									</Link>
								);
							})}
						</div>
					</div>
				</aside>

				<main className="workspace-route flex-1 min-w-0 p-6 md:p-10 max-w-7xl mx-auto w-full bg-transparent">
					<WorkspaceKineticStage>
						{children}
					</WorkspaceKineticStage>
				</main>
			</div>

			{quickJumpOpen&&(
				<div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-[#231412]/30 backdrop-blur-sm" onClick={()=>setQuickJumpOpen(false)}>
					<div className="w-full max-w-lg p-5 rounded-3xl bg-white border border-[#C8281E]/20 shadow-2xl" onClick={(e)=>e.stopPropagation()}>
						<div className="flex items-center justify-between pb-3 border-b border-[#C8281E]/15">
							<span className="text-xs font-mono tracking-widest text-[#C8281E] font-bold">QUICK JUMP TO CHAPTER</span>
							<kbd className="px-1.5 py-0.5 rounded text-[10px] bg-[#FAF7F2] text-[#6E524D] font-mono border border-[#C8281E]/20">ESC</kbd>
						</div>
						<div className="mt-3 max-h-80 overflow-y-auto space-y-1">
							{allChapters.map((route)=>{
								const href='/workspaces/'+businessId+route.path;
								const Icon=route.icon;
								return(
									<Link
										key={route.label}
										href={href}
										onClick={()=>setQuickJumpOpen(false)}
										className="flex items-center gap-3 px-3 py-2 text-xs text-[#231412] hover:bg-[#FAF7F2] hover:text-[#C8281E] transition-colors"
									>
										<span className="font-mono text-[10px] text-[#9A7E78]">[{route.number}]</span>
										<Icon size={14} className="text-[#C8281E]" />
										<span className="flex-1 font-semibold">{route.label}</span>
									</Link>
								);
							})}
						</div>
					</div>
				</div>
			)}

			{cashModalOpen&&(
				<div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#231412]/60 backdrop-blur-sm animate-in fade-in" onClick={()=>setCashModalOpen(false)}>
					<div className="w-full max-w-xl bg-[#FAF7F2] border-2 border-[#231412] shadow-[6px_6px_0px_#231412] p-6 max-h-[90vh] overflow-y-auto" onClick={(e)=>e.stopPropagation()}>
						<div className="flex items-center justify-between pb-3 border-b-2 border-[#231412] mb-5">
							<div className="flex items-center gap-2">
								<div className="w-8 h-8 bg-[#231412] text-white flex items-center justify-center font-mono font-bold text-sm shadow-[2px_2px_0px_#C8281E]">
									₹
								</div>
								<div>
									<h2 className="text-base font-black text-[#231412] tracking-tight">MANAGE TREASURY & LIQUID CASH</h2>
									<span className="text-[10px] font-mono text-[#5C403B] font-bold">SOVEREIGN LIQUIDITY LEDGER & CAPITAL BALANCES</span>
								</div>
							</div>
							<button
								type="button"
								onClick={()=>setCashModalOpen(false)}
								className="p-1.5 text-[#5C403B] hover:text-[#C8281E] border border-transparent hover:border-[#231412] transition-colors"
							>
								<X size={18} />
							</button>
						</div>

						<div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-5 font-mono">
							<div className="p-2.5 bg-white border-2 border-[#231412]">
								<span className="text-[10px] uppercase font-bold text-[#5C403B] block">Cash in Hand</span>
								<strong className="text-sm font-black text-emerald-700 block mt-0.5 tabular-nums">
									{formatINR(cash?.cash_on_hand_exact??cash?.cash_on_hand??0)}
								</strong>
							</div>
							<div className="p-2.5 bg-white border-2 border-[#231412]">
								<span className="text-[10px] uppercase font-bold text-[#5C403B] block">Bank Liquidity</span>
								<strong className="text-sm font-black text-blue-700 block mt-0.5 tabular-nums">
									{formatINR(cash?.bank_balance_exact??cash?.bank_balance??0)}
								</strong>
							</div>
							<div className="p-2.5 bg-white border-2 border-[#231412]">
								<span className="text-[10px] uppercase font-bold text-[#5C403B] block">Receivables</span>
								<strong className="text-sm font-black text-[#C8281E] block mt-0.5 tabular-nums">
									{formatINR(cash?.total_receivables_exact??cash?.total_receivables??0)}
								</strong>
							</div>
							<div className="p-2.5 bg-white border-2 border-[#231412]">
								<span className="text-[10px] uppercase font-bold text-[#5C403B] block">Payables</span>
								<strong className="text-sm font-black text-amber-700 block mt-0.5 tabular-nums">
									{formatINR(cash?.total_payables_exact??cash?.total_payables??0)}
								</strong>
							</div>
						</div>

						<div className="flex border-2 border-[#231412] mb-4 bg-white">
							<button
								type="button"
								onClick={()=>setCashActionTab('inflow')}
								className={`flex-1 py-2 text-xs font-mono font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-1.5 ${cashActionTab==='inflow'?'bg-emerald-700 text-white shadow-inner':'bg-white text-[#231412] hover:bg-emerald-50'}`}
							>
								<ArrowDownLeft size={14} /> + Inject Capital (Inflow)
							</button>
							<div className="w-0.5 bg-[#231412]" />
							<button
								type="button"
								onClick={()=>setCashActionTab('outflow')}
								className={`flex-1 py-2 text-xs font-mono font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-1.5 ${cashActionTab==='outflow'?'bg-[#C8281E] text-white shadow-inner':'bg-white text-[#231412] hover:bg-red-50'}`}
							>
								<ArrowUpRight size={14} /> - Withdraw Cash (Outflow)
							</button>
						</div>

						<form onSubmit={handleCashAction} className="space-y-3.5 bg-white p-4 border-2 border-[#231412]">
							<div>
								<label className="block text-[11px] font-mono font-bold text-[#231412] uppercase mb-1">
									{cashActionTab==='inflow'?'Cash Inflow Amount (₹) *':'Cash Outflow Amount (₹) *'}
								</label>
								<input
									type="number"
									step="any"
									min="1"
									required
									value={cashActionAmount}
									onChange={(e)=>setCashActionAmount(e.target.value)}
									placeholder="e.g. 50000"
									className="w-full h-10 px-3 bg-[#FAF7F2] border-2 border-[#231412] text-sm font-mono font-bold text-[#231412] focus:outline-none focus:border-[#C8281E]"
								/>
							</div>

							<div className="grid grid-cols-2 gap-3">
								<div>
									<label className="block text-[11px] font-mono font-bold text-[#231412] uppercase mb-1">
										Settlement Channel *
									</label>
									<select
										value={cashActionMethod}
										onChange={(e)=>setCashActionMethod(e.target.value)}
										className="w-full h-10 px-3 bg-[#FAF7F2] border-2 border-[#231412] text-xs font-mono font-bold text-[#231412] focus:outline-none focus:border-[#C8281E] appearance-none"
									>
										<option value="CASH">Physical Cash in Hand</option>
										<option value="BANK_TRANSFER">Bank Account / Transfer</option>
										<option value="UPI">UPI / Digital Wallet</option>
									</select>
								</div>
								{cashActionTab==='outflow'?(
									<div>
										<label className="block text-[11px] font-mono font-bold text-[#231412] uppercase mb-1">
											Category *
										</label>
										<select
											value={cashActionCategory}
											onChange={(e)=>setCashActionCategory(e.target.value)}
											className="w-full h-10 px-3 bg-[#FAF7F2] border-2 border-[#231412] text-xs font-mono font-bold text-[#231412] focus:outline-none focus:border-[#C8281E] appearance-none"
										>
											<option value="CAPITAL">Owner Drawing / Capital</option>
											<option value="OPERATING">Operating Expense</option>
											<option value="ADMINISTRATIVE">Administrative</option>
											<option value="OTHER">Other Disbursement</option>
										</select>
									</div>
								):(
									<div>
										<label className="block text-[11px] font-mono font-bold text-[#231412] uppercase mb-1">
											Source Reference
										</label>
										<input
											type="text"
											value={cashActionNotes}
											onChange={(e)=>setCashActionNotes(e.target.value)}
											placeholder="e.g. Owner Capital Infusion"
											className="w-full h-10 px-3 bg-[#FAF7F2] border-2 border-[#231412] text-xs font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
										/>
									</div>
								)}
							</div>

							{cashActionTab==='outflow'&&(
								<div>
									<label className="block text-[11px] font-mono font-bold text-[#231412] uppercase mb-1">
										Disbursement Purpose / Note
									</label>
									<input
										type="text"
										value={cashActionNotes}
										onChange={(e)=>setCashActionNotes(e.target.value)}
										placeholder="e.g. Cash withdrawal for store branch"
										className="w-full h-10 px-3 bg-[#FAF7F2] border-2 border-[#231412] text-xs font-mono text-[#231412] focus:outline-none focus:border-[#C8281E]"
									/>
								</div>
							)}

							<div className="pt-3 border-t border-[#231412]/15 flex items-center justify-end gap-2.5">
								<MotionButton
									type="button"
									onClick={()=>setCashModalOpen(false)}
									className="px-4 py-2 bg-[#FAF7F2] text-xs font-mono font-bold text-[#5C403B] hover:text-[#231412] border-2 border-[#231412]"
								>
									Cancel
								</MotionButton>
								<MotionButton
									type="submit"
									disabled={submittingCash}
									className={`px-5 py-2 text-white font-mono text-xs font-bold border-2 border-[#231412] shadow-[2px_2px_0px_#231412] disabled:opacity-60 transition-all ${cashActionTab==='inflow'?'bg-emerald-700 hover:bg-emerald-800':'bg-[#C8281E] hover:bg-[#A81E15]'}`}
								>
									{submittingCash?'Recording...':cashActionTab==='inflow'?'Inject Capital / Deposit Inflow':'Record Cash Outflow'}
								</MotionButton>
							</div>
						</form>
					</div>
				</div>
			)}
		</div>
	);
}
