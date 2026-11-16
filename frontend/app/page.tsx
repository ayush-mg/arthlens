"use client";
import React,{useEffect,useRef,useState}from"react";
import Link from"next/link";
import{useRouter}from"next/navigation";
import{motion,useMotionValue,useSpring}from"framer-motion";
import{getMe}from"@/lib/api";
import{FloatingBounceSatellites,SatelliteBoxItem}from"@/components/motion/FloatingBounceSatellites";
import{ZoomScrollPortal,ZoomPortalMetric}from"@/components/motion/ZoomScrollPortal";
import{VelocityMarquee}from"@/components/motion/VelocityMarquee";
import{MaskText}from"@/components/motion/MaskText";
import{ScrambleText}from"@/components/motion/ScrambleText";
import{NumberTicker}from"@/components/motion/NumberTicker";
import{ArthLensBrandMark}from"@/components/motion/ArthLensBrandMark";
interface PillarChapter{
	index:string;
	eyebrow:string;
	title:string;
	subtitle:string;
	body:string;
	metrics:string[];
}
interface CapabilityInstrument{
	code:string;
	name:string;
	domain:string;
	summary:string;
	telemetry:string;
}
const heroSatellites:SatelliteBoxItem[]=[
	{
		id:"sat-khata",
		eyebrow:"KHATA SYNC",
		metric:"0.00ms DRIFT",
		delta:"PAISA EXACT",
		badgeTone:"crimson",
		positionClass:"",
		parallaxSpeed:-0.38,
		floatDelay:0.2
	},
	{
		id:"sat-fifo",
		eyebrow:"FIFO LOT #409",
		metric:"+18.4% MARGIN",
		delta:"BATCH TRACED",
		badgeTone:"emerald",
		positionClass:"",
		parallaxSpeed:0.32,
		floatDelay:0.9
	},
	{
		id:"sat-runway",
		eyebrow:"CASH RUNWAY",
		metric:"14.2 MONTHS",
		delta:"+12.8% PULSE",
		badgeTone:"crimson",
		positionClass:"",
		parallaxSpeed:-0.3,
		floatDelay:1.5
	},
	{
		id:"sat-gov",
		eyebrow:"GOVERNANCE",
		metric:"HUMAN LOCKED",
		delta:"SHA-256 AUDIT",
		badgeTone:"amber",
		positionClass:"",
		parallaxSpeed:0.36,
		floatDelay:2.1
	}
];
const vaultMetrics:ZoomPortalMetric[]=[
	{
		label:"01 | INGESTION",
		value:"Atomic Vouchers",
		detail:"Every supplier bill & GST invoice validated"
	},
	{
		label:"02 | LEDGER",
		value:"Balanced Khata",
		detail:"Debit equals credit on every write"
	},
	{
		label:"03 | INVENTORY",
		value:"FIFO Depletion",
		detail:"Exact batch COGS per line item"
	},
	{
		label:"04 | COGNITION",
		value:"Governed AI",
		detail:"Explicit human approval required"
	}
];
const pillarChapters:PillarChapter[]=[
	{
		index:"01",
		eyebrow:"PILLAR I | DOUBLE-ENTRY KHATA",
		title:"Books That Refuse to Drift.",
		subtitle:"Every invoice, receipt, and credit note is posted as an atomic, balanced journal.",
		body:"No orphan balances. No silent rounding errors. Track customer receivables and supplier payables down to the exact paisa with instant party-level statements and settlement histories.",
		metrics:["Precision: 100% Paisa-Exact","Reconciliation: Instant Party Khata","Integrity: Immutable Audit Trail"]
	},
	{
		index:"02",
		eyebrow:"PILLAR II | FIFO LOT TRACEABILITY",
		title:"Know the True Margin of Every Unit Sold.",
		subtitle:"Batch-by-batch cost consumption across fluctuating supplier prices.",
		body:"When raw material costs shift between shipments, average costing lies. ArthLens traces exact First-In, First-Out lot depletion on every sale so your gross margin is a proven fact, never an estimate.",
		metrics:["Valuation: Strict FIFO Batches","Alerts: Velocity Reorder Triggers","Margin: Per-Invoice COGS Proof"]
	},
	{
		index:"03",
		eyebrow:"PILLAR III | DETERMINISTIC CASHFLOW BRIDGE",
		title:"See Why Profit and Cash Diverge.",
		subtitle:"Reconcile opening cash to closing bank balance across every operating stream.",
		body:"Stress-test working capital before you commit. Simulate delayed receivables, inventory restocks, and tax outflows to see your exact 90-day liquidity runway.",
		metrics:["Bridge: Opening to Closing","Simulation: Multi-Variable Stress","Health Score: 0-100 Deterministic"]
	},
	{
		index:"04",
		eyebrow:"PILLAR IV | HUMAN-GOVERNED AI",
		title:"AI That Proposes. Operators Who Command.",
		subtitle:"Zero blind mutations. Every recommendation is staged, cited, and reversible.",
		body:"Our financial copilot reads across all 18 modules to surface reorder alerts, credit risks, and margin anomalies—staging every action in a governed approval queue awaiting your explicit sign-off.",
		metrics:["Authority: Human-in-the-loop","Context: 18-Module Live Graph","Safety: Zero Unapproved Writes"]
	}
];
const capabilityInstruments:CapabilityInstrument[]=[
	{code:"01",name:"Command Overview",domain:"CORE",summary:"Real-time treasury, receivables, and operating pulse.",telemetry:"LIVE SYNC"},
	{code:"02",name:"Sales & GST Invoicing",domain:"COMMERCE",summary:"Issue compliant tax invoices with automatic FIFO cost binding.",telemetry:"FIFO LINKED"},
	{code:"03",name:"Purchase & Bills",domain:"COMMERCE",summary:"Record supplier inward bills and spawn traceable stock lots.",telemetry:"LOT SPAWN"},
	{code:"04",name:"FIFO Inventory Matrix",domain:"SUPPLY",summary:"Track batch-wise stock valuation, aging, and reorder velocity.",telemetry:"BATCH EXACT"},
	{code:"05",name:"Double-Entry Khata",domain:"LEDGER",summary:"Paisa-accurate party ledgers with automated journal balancing.",telemetry:"ZERO DRIFT"},
	{code:"06",name:"Customer Directory",domain:"PARTIES",summary:"Credit limits, aging buckets, and receivable collection velocity.",telemetry:"CREDIT GUARD"},
	{code:"07",name:"Supplier Network",domain:"PARTIES",summary:"Payable schedules, lead-time reliability, and vendor terms.",telemetry:"AP TRACKED"},
	{code:"08",name:"Treasury & Cashflow",domain:"FINANCE",summary:"Opening-to-closing cash bridge and liquidity runway modeling.",telemetry:"14.2M RUNWAY"},
	{code:"09",name:"Expense Controller",domain:"FINANCE",summary:"Categorized operating burn with voucher-level audit proof.",telemetry:"VOUCHER LOCK"},
	{code:"10",name:"GST & Tax Engine",domain:"COMPLIANCE",summary:"Input tax credit reconciliation and output liability schedules.",telemetry:"ITC MATCHED"},
	{code:"11",name:"Executive Analytics",domain:"INTELLIGENCE",summary:"Cohort profitability, SKU contribution, and margin waterfalls.",telemetry:"MARGIN PROOF"},
	{code:"12",name:"What-If Simulator",domain:"INTELLIGENCE",summary:"Stress-test price changes, demand shocks, and credit delays.",telemetry:"MONTE CARLO"},
	{code:"13",name:"AI Financial Copilot",domain:"COGNITION",summary:"Context-aware operational advisor grounded in live ledger data.",telemetry:"RAG GROUNDED"},
	{code:"14",name:"Governance Queue",domain:"GOVERNANCE",summary:"Human-in-the-loop staging area for all AI-proposed actions.",telemetry:"HUMAN SIGN-OFF"},
	{code:"15",name:"Anomaly Radar",domain:"RISK",summary:"Automated detection of duplicate bills and margin leakage.",telemetry:"24/7 SCAN"},
	{code:"16",name:"Document Vault",domain:"RECORDS",summary:"OCR extraction and cryptographic linking of source receipts.",telemetry:"SHA-256"},
	{code:"17",name:"Immutable Audit Log",domain:"GOVERNANCE",summary:"Tamper-evident chronological trail of every state mutation.",telemetry:"APPEND ONLY"},
	{code:"18",name:"Workspace Access",domain:"SECURITY",summary:"Role-based permissions, 2FA OTP verification, and session locks.",telemetry:"RBAC ACTIVE"}
];
export default function HomePage(){
	const router=useRouter();
	const[userEmail,setUserEmail]=useState<string|null>(null);
	const[checkingAuth,setCheckingAuth]=useState(true);
	const[activePillar,setActivePillar]=useState(0);
	const[heroLockedDone,setHeroLockedDone]=useState(false);
	const[pillarLockedDone,setPillarLockedDone]=useState(false);
	const activePillarRef=useRef(0);
	const heroDoneRef=useRef(false);
	const pillarDoneRef=useRef(false);
	const globalBarRef=useRef<HTMLDivElement|null>(null);
	const heroTrackRef=useRef<HTMLElement|null>(null);
	const heroWatermarkRef=useRef<HTMLDivElement|null>(null);
	const heroLeftRef=useRef<HTMLDivElement|null>(null);
	const heroRightRef=useRef<HTMLDivElement|null>(null);
	const heroBarRef=useRef<HTMLDivElement|null>(null);
	const bridgePathRef=useRef<SVGPathElement|null>(null);
	const pillarTrackContainerRef=useRef<HTMLElement|null>(null);
	const pillarWatermarkRef=useRef<HTMLDivElement|null>(null);
	const pillarStripRef=useRef<HTMLDivElement|null>(null);
	const pillarBarRef=useRef<HTMLDivElement|null>(null);
	const pillarCardRefs=useRef<Array<HTMLDivElement|null>>([]);
	const matrixSectionRef=useRef<HTMLElement|null>(null);
	const matrixWatermarkRef=useRef<HTMLDivElement|null>(null);
	const matrixCardRefs=useRef<Array<HTMLDivElement|null>>([]);
	const commandCardRef=useRef<HTMLDivElement|null>(null);
	const mouseTiltX=useMotionValue(0);
	const mouseTiltY=useMotionValue(0);
	const smoothTiltX=useSpring(mouseTiltX,{stiffness:180,damping:22});
	const smoothTiltY=useSpring(mouseTiltY,{stiffness:180,damping:22});
	useEffect(()=>{
		let cancelled=false;
		getMe()
			.then((u)=>{
				if(!cancelled&&u&&u.email){
					setUserEmail(u.email);
				}
			})
			.catch(()=>{
				if(!cancelled){
					setUserEmail(null);
				}
			})
			.finally(()=>{
				if(!cancelled){
					setCheckingAuth(false);
				}
			});
		return()=>{
			cancelled=true;
		};
	},[]);
	const triggerWorkspaceAccess=()=>{
		if(userEmail){
			router.push("/workspaces");
			return;
		}
		router.push("/login?redirect=/workspaces");
	};
	useEffect(()=>{
		let rafId=0;
		let smoothGlobalP=0;
		let smoothHeroP=0;
		let smoothPillarP=0;
		let smoothMatrixP=0;
		let smoothCmdP=0;
		const animateScroll=()=>{
			const viewH=window.innerHeight||1;
			const docH=Math.max(1,document.documentElement.scrollHeight-viewH);
			const rawGlobalP=Math.max(0,Math.min(1,(window.scrollY||0)/docH));
			smoothGlobalP+=(rawGlobalP-smoothGlobalP)*0.2;
			if(globalBarRef.current){
				globalBarRef.current.style.width=`${(smoothGlobalP*100).toFixed(2)}%`;
			}
			const heroEl=heroTrackRef.current;
			if(heroEl){
				const rect=heroEl.getBoundingClientRect();
				const scrollable=Math.max(1,rect.height-viewH);
				const rawScrollRatio=Math.max(0,Math.min(1,-rect.top/scrollable));
				const targetHeroP=Math.max(0,Math.min(1,rawScrollRatio/0.74));
				smoothHeroP+=(targetHeroP-smoothHeroP)*0.16;
				if(Math.abs(targetHeroP-smoothHeroP)<0.0015){
					smoothHeroP=targetHeroP;
				}
				const isHeroDone=smoothHeroP>=0.98;
				if(isHeroDone!==heroDoneRef.current){
					heroDoneRef.current=isHeroDone;
					setHeroLockedDone(isHeroDone);
				}
				if(heroBarRef.current){
					heroBarRef.current.style.width=`${(smoothHeroP*100).toFixed(1)}%`;
				}
				if(heroWatermarkRef.current){
					const wmShift=-smoothHeroP*240;
					heroWatermarkRef.current.style.transform=`translate3d(${wmShift.toFixed(1)}px,0px,0px)`;
				}
				const easeH=1-Math.pow(1-smoothHeroP,3);
				if(heroLeftRef.current){
					const ty=-easeH*26;
					heroLeftRef.current.style.transform=`translate3d(0px,${ty.toFixed(1)}px,0px)`;
				}
				if(heroRightRef.current){
					const sc=0.92+easeH*0.08;
					const ty=(1-easeH)*30;
					const ry=(1-easeH)*-9;
					heroRightRef.current.style.transform=`perspective(1200px) translate3d(0px,${ty.toFixed(1)}px,0px) rotateY(${ry.toFixed(2)}deg) scale(${sc.toFixed(4)})`;
				}
				if(bridgePathRef.current){
					const dash=(1-easeH)*220;
					bridgePathRef.current.style.strokeDashoffset=dash.toFixed(1);
				}
			}
			const pillarContainer=pillarTrackContainerRef.current;
			const pillarStrip=pillarStripRef.current;
			if(pillarContainer&&pillarStrip){
				const rect=pillarContainer.getBoundingClientRect();
				const scrollable=Math.max(1,rect.height-viewH);
				const rawScrollRatio=Math.max(0,Math.min(1,-rect.top/scrollable));
				const targetPillarP=Math.max(0,Math.min(1,(rawScrollRatio-0.05)/0.74));
				smoothPillarP+=(targetPillarP-smoothPillarP)*0.16;
				if(Math.abs(targetPillarP-smoothPillarP)<0.0015){
					smoothPillarP=targetPillarP;
				}
				const isPillarDone=smoothPillarP>=0.98;
				if(isPillarDone!==pillarDoneRef.current){
					pillarDoneRef.current=isPillarDone;
					setPillarLockedDone(isPillarDone);
				}
				if(pillarBarRef.current){
					pillarBarRef.current.style.width=`${(smoothPillarP*100).toFixed(1)}%`;
				}
				if(pillarWatermarkRef.current){
					const pwmX=(0.5-smoothPillarP)*320;
					pillarWatermarkRef.current.style.transform=`translate3d(${pwmX.toFixed(1)}px,0px,0px)`;
				}
				const maxShift=Math.max(0,pillarStrip.scrollWidth-window.innerWidth+128);
				const shiftX=-smoothPillarP*maxShift;
				pillarStrip.style.transform=`translate3d(${shiftX.toFixed(1)}px,0px,0px)`;
				const nextIdx=Math.min(pillarChapters.length-1,Math.max(0,Math.round(smoothPillarP*(pillarChapters.length-1))));
				if(nextIdx!==activePillarRef.current){
					activePillarRef.current=nextIdx;
					setActivePillar(nextIdx);
				}
				for(let i=0;i<pillarChapters.length;i+=1){
					const card=pillarCardRefs.current[i];
					if(!card){
						continue;
					}
					const targetCenter=i/(pillarChapters.length-1);
					const dist=smoothPillarP-targetCenter;
					const absDist=Math.min(1,Math.abs(dist)*2.2);
					const cardScale=1.0-absDist*0.06;
					const rotY=Math.max(-8,Math.min(8,dist*-12));
					card.style.transform=`perspective(1200px) rotateY(${rotY.toFixed(2)}deg) scale(${cardScale.toFixed(4)})`;
				}
			}
			const matrixEl=matrixSectionRef.current;
			if(matrixEl){
				const rect=matrixEl.getBoundingClientRect();
				const span=Math.max(1,rect.height+viewH);
				const rawMP=Math.max(0,Math.min(1,(viewH-rect.top)/span));
				smoothMatrixP+=(rawMP-smoothMatrixP)*0.16;
				if(matrixWatermarkRef.current){
					const mwmX=(smoothMatrixP-0.5)*-260;
					matrixWatermarkRef.current.style.transform=`translate3d(${mwmX.toFixed(1)}px,0px,0px)`;
				}
				for(let i=0;i<capabilityInstruments.length;i+=1){
					const mCard=matrixCardRefs.current[i];
					if(!mCard){
						continue;
					}
					const colIdx=i%3;
					const colDir=colIdx===1?-1:1;
					const parallaxY=(0.5-smoothMatrixP)*34*colDir;
					mCard.style.transform=`translate3d(0px,${parallaxY.toFixed(1)}px,0px)`;
				}
			}
			const cmdCard=commandCardRef.current;
			if(cmdCard){
				const rect=cmdCard.getBoundingClientRect();
				const rawP=Math.max(0,Math.min(1,(viewH-rect.top)/Math.max(1,viewH*0.72)));
				smoothCmdP+=(rawP-smoothCmdP)*0.16;
				const sc=0.9+smoothCmdP*0.1;
				const ty=(1-smoothCmdP)*36;
				cmdCard.style.transform=`translate3d(0px,${ty.toFixed(1)}px,0px) scale(${sc.toFixed(4)})`;
			}
			rafId=window.requestAnimationFrame(animateScroll);
		};
		rafId=window.requestAnimationFrame(animateScroll);
		return()=>{
			window.cancelAnimationFrame(rafId);
		};
	},[]);
	const handleHeroCardMove=(e:React.MouseEvent<HTMLDivElement>)=>{
		const rect=e.currentTarget.getBoundingClientRect();
		const nx=(e.clientX-rect.left)/rect.width-0.5;
		const ny=(e.clientY-rect.top)/rect.height-0.5;
		mouseTiltX.set(-ny*8);
		mouseTiltY.set(nx*8);
	};
	const resetHeroCardTilt=()=>{
		mouseTiltX.set(0);
		mouseTiltY.set(0);
	};
	const userPrefix=userEmail?userEmail.split("@")[0]:null;
	return(
		<div className="relative min-h-screen w-full bg-transparent text-[#231412] selection:bg-[#C8281E] selection:text-white">
			<header className="fixed top-0 inset-x-0 z-50 h-20 bg-[#FFFFFF] border-b-2 border-[#231412] px-6 lg:px-14 flex items-center justify-between">
				<Link href="/" className="group" title="ArthLens Sovereign Topology">
					<ArthLensBrandMark />
				</Link>
				<nav className="hidden md:flex items-center p-1.5 rounded-none bg-[#FAF7F2] border-2 border-[#231412] shadow-[3px_3px_0px_#231412] gap-1">
					{[
						{href:"#act-prologue",index:"01",label:"The Premise"},
						{href:"#act-vault",index:"02",label:"The Vault"},
						{href:"#act-pillars",index:"03",label:"Four Pillars"},
						{href:"#act-matrix",index:"04",label:"18 Instruments"}
					].map((item)=>(
						<a
							key={item.href}
							href={item.href}
							className="group flex items-center gap-2 px-3.5 py-1.5 rounded-none text-xs font-mono font-bold uppercase tracking-[0.14em] text-[#231412] hover:bg-[#FFFFFF] hover:text-[#C8281E] border border-transparent hover:border-[#231412] transition-all select-none"
						>
							<span className="text-[10px] font-mono text-[#C8281E] group-hover:text-[#231412] font-bold">
								[{item.index}]
							</span>
							<span>{item.label}</span>
						</a>
					))}
				</nav>
				<div className="flex items-center gap-3">
					{!checkingAuth&&userEmail?(
						<button
							type="button"
							data-testid="landing-enter-workspace"
							onClick={triggerWorkspaceAccess}
							className="rounded-none bg-[#C8281E] border-2 border-[#231412] px-5 py-2.5 text-xs font-mono uppercase tracking-[0.15em] text-white font-bold shadow-[4px_4px_0px_#231412] hover:bg-[#A61B12] transition-colors"
						>
							{`Enter Workspace (${userPrefix}) →`}
						</button>
					):(
						<>
							<Link className="rounded-none border-2 border-[#231412] bg-[#FAF7F2] px-4 py-2 text-xs font-mono font-bold uppercase tracking-[0.15em] text-[#231412] hover:bg-[#231412] hover:text-white transition-colors" data-testid="landing-sign-in" href="/login">
								Sign In
							</Link>
							<button
								type="button"
								data-testid="landing-auth-open"
								onClick={triggerWorkspaceAccess}
								className="rounded-none bg-[#C8281E] border-2 border-[#231412] px-5 py-2.5 text-xs font-mono uppercase tracking-[0.15em] text-white font-bold shadow-[4px_4px_0px_#231412] hover:bg-[#A61B12] transition-colors"
							>
								Authenticate & Open →
							</button>
						</>
					)}
				</div>
				<div className="absolute bottom-0 left-0 right-0 h-1 bg-[#FAF7F2]">
					<div ref={globalBarRef} className="h-full bg-[#C8281E] w-0"/>
				</div>
			</header>
			<main className="relative z-10 w-full bg-transparent pt-20">
				<section
					id="act-prologue"
					ref={heroTrackRef}
					className="relative w-full h-[210vh] bg-transparent"
				>
					<div className="sticky top-0 left-0 h-screen w-full flex flex-col justify-center px-6 lg:px-14 overflow-hidden pt-12">
						<div
							ref={heroWatermarkRef}
							aria-hidden="true"
							className="pointer-events-none select-none absolute left-8 top-24 text-[11vw] font-mono font-bold uppercase tracking-[0.14em] text-[#231412]/[0.045] whitespace-nowrap will-change-transform"
						>
							01 // ZERO-DRIFT PREMISE
						</div>
						<div className="relative z-30 mx-auto w-full max-w-7xl">
							<div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
								<div ref={heroLeftRef} className="lg:col-span-7 will-change-transform">
									<div className="inline-flex items-center gap-2 rounded-none bg-[#231412] border-2 border-[#231412] px-4 py-1.5 text-[11px] font-mono font-bold uppercase tracking-[0.18em] text-[#FFFFFF] mb-5 shadow-[4px_4px_0px_#C8281E]">
										<span className="w-2 h-2 rounded-none bg-[#C8281E] animate-pulse"/>
										<ScrambleText text="PROLOGUE | ZERO-DRIFT FINANCIAL ARCHITECTURE" />
									</div>
									<h1 className="text-4xl sm:text-6xl xl:text-7xl font-bold tracking-tight leading-[1.02] text-[#231412]">
										<MaskText delay={0.06}>Where Every Rupee</MaskText>
										<span className="block text-[#C8281E] mt-1">
											<MaskText delay={0.22}>Carries Proof.</MaskText>
										</span>
									</h1>
									<div className="mt-5 text-sm sm:text-base text-[#231412] leading-relaxed max-w-2xl bg-[#FFFFFF] rounded-none p-5 border-2 border-[#231412] shadow-[6px_6px_0px_#231412]">
										Spreadsheets guess. Disconnected tools drift. ArthLens binds your sales, purchases, FIFO inventory lots, double-entry Khata, and AI-governed decisions into one living, mathematically locked operating system.
									</div>
									<div className="mt-6 flex flex-wrap items-center gap-4">
										<motion.button
											type="button"
											data-testid="hero-primary-cta"
											onClick={triggerWorkspaceAccess}
											whileHover={{x:-3,y:-3}}
											whileTap={{x:0,y:0}}
											className="rounded-none bg-[#C8281E] border-2 border-[#231412] px-7 py-3.5 text-xs sm:text-sm font-mono uppercase tracking-[0.18em] text-white font-bold shadow-[6px_6px_0px_#231412] hover:bg-[#A61B12] transition-colors"
										>
											{userEmail?"Enter Sovereign Workspace →":"Authenticate & Enter Workspace →"}
										</motion.button>
										<Link className="rounded-none bg-[#FFFFFF] border-2 border-[#231412] px-6 py-3.5 text-xs sm:text-sm font-mono uppercase tracking-[0.16em] text-[#231412] font-bold shadow-[6px_6px_0px_#C8281E] hover:bg-[#231412] hover:text-white transition-colors" data-testid="hero-register-cta" href="/register">
											Forge New Workspace Identity
										</Link>
									</div>
								</div>
								<div ref={heroRightRef} className="lg:col-span-5 will-change-transform">
									<motion.div
										onMouseMove={handleHeroCardMove}
										onMouseLeave={resetHeroCardTilt}
										style={{
											rotateX:smoothTiltX,
											rotateY:smoothTiltY,
											transformPerspective:1200
										}}
										className="rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-6 sm:p-7 shadow-[10px_10px_0px_#231412]"
									>
										<div className="flex items-center justify-between border-b-2 border-[#231412] pb-3.5">
											<div>
												<div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#C8281E] font-bold">
													LIVE LEDGER TELEMETRY | PAISA-EXACT
												</div>
												<div className="text-xl font-bold text-[#231412] mt-1">
													Sovereign Operating Pulse
												</div>
											</div>
											<span className="px-2.5 py-1 rounded-none bg-[#065F46] text-white border border-[#231412] text-[10px] font-mono font-bold">
												RECONCILED
											</span>
										</div>
										<div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
											<div className="rounded-none bg-[#FAF7F2] border-2 border-[#231412] p-3.5">
												<div className="text-[10px] font-mono font-bold uppercase tracking-[0.16em] text-[#5C403B]">
													LIQUID TREASURY
												</div>
												<div className="text-lg font-bold font-mono text-[#231412] mt-1">
													<NumberTicker value={2480500} prefix="₹" decimals={2} />
												</div>
												<div className="text-[11px] font-mono font-bold text-[#065F46] mt-0.5">
													↑ +14.2% verified cycle
												</div>
											</div>
											<div className="rounded-none bg-[#FAF7F2] border-2 border-[#231412] p-3.5">
												<div className="text-[10px] font-mono font-bold uppercase tracking-[0.16em] text-[#5C403B]">
													FIFO LOT INTEGRITY
												</div>
												<div className="text-lg font-bold font-mono text-[#C8281E] mt-1">
													<NumberTicker value={100} suffix="%" decimals={2} />
												</div>
												<div className="text-[11px] font-mono text-[#231412] mt-0.5">
													Zero unallocated cost basis
												</div>
											</div>
										</div>
										<div className="mt-4 rounded-none bg-[#FAF7F2] border-2 border-[#231412] p-3.5">
											<div className="flex items-center justify-between text-xs font-mono font-bold text-[#231412] mb-1.5">
												<span>NET OPERATING BRIDGE</span>
												<span className="text-[#C8281E]">
													+<NumberTicker value={842000} prefix="₹" decimals={2} />
												</span>
											</div>
											<svg
												viewBox="0 0 320 64"
												width="320"
												height="56"
												style={{width:"100%",height:"56px",display:"block"}}
												className="w-full h-14 overflow-visible"
											>
												<path
													d="M 4 54 L 62 42 L 118 26 L 176 32 L 236 14 L 284 18 L 316 6"
													fill="none"
													stroke="rgba(35,20,18,0.16)"
													strokeWidth="3"
													strokeLinecap="square"
												/>
												<path
													ref={bridgePathRef}
													d="M 4 54 L 62 42 L 118 26 L 176 32 L 236 14 L 284 18 L 316 6"
													fill="none"
													stroke="#C8281E"
													strokeWidth="3"
													strokeLinecap="square"
													strokeDasharray="360"
													strokeDashoffset="220"
												/>
											</svg>
										</div>
										<div className="mt-4 pt-3 border-t-2 border-[#231412]">
											<div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.15em] text-[#231412] mb-1.5">
												<span>PROLOGUE STAGE LOCK</span>
												<span className="font-bold text-[#C8281E]">
													{heroLockedDone?"LOCKED — SCROLL TO VAULT":"CALIBRATING TELEMETRY"}
												</span>
											</div>
											<div className="w-full h-2 bg-[#FAF7F2] border border-[#231412]">
												<div ref={heroBarRef} className="h-full bg-[#C8281E] w-0"/>
											</div>
										</div>
									</motion.div>
								</div>
							</div>
							<FloatingBounceSatellites items={heroSatellites}/>
						</div>
					</div>
				</section>
				<VelocityMarquee
					duration={24}
					items={[
						"IMMUTABLE KHATA",
						"FIFO LOT TRACEABILITY",
						"DETERMINISTIC CASHFLOW",
						"HUMAN-GOVERNED AI",
						"100% PAISA-EXACT",
						"SHA-256 AUDIT LOG",
						"ZERO MUTATION DRIFT"
					]}
				/>
				<section id="act-vault" className="relative w-full bg-transparent">
					<ZoomScrollPortal ctaLabel="Inspect Live Ledger Topology →" description="Behind every executive metric lies an immutable chain of custody—from the supplier bill that created a FIFO batch, to the GST invoice that depleted it, to the Khata settlement that cleared the receivable." eyebrow="THE ARCHITECTURE OF CERTAINTY" headline="Zoom Past the Surface." highlightWord="Enter the Record Layer." metrics={vaultMetrics} onCtaClick={triggerWorkspaceAccess}/>
				</section>
				<VelocityMarquee
					reverse
					duration={22}
					items={[
						"OPERATIONAL TOPOLOGY",
						"RECONCILED VOUCHERS",
						"ATOMIC JOURNALING",
						"18-MODULE GRAPH",
						"ZERO ORPHAN BALANCES",
						"REAL-TIME LIQUIDITY"
					]}
				/>
				<section
					id="act-pillars"
					ref={pillarTrackContainerRef}
					className="relative w-full h-[380vh] bg-transparent"
				>
					<div className="sticky top-0 left-0 h-screen w-full flex flex-col justify-center overflow-hidden px-6 lg:px-14 pt-12">
						<div
							ref={pillarWatermarkRef}
							aria-hidden="true"
							className="pointer-events-none select-none absolute left-12 top-24 text-[11vw] font-mono font-bold uppercase tracking-[0.14em] text-[#231412]/[0.045] whitespace-nowrap will-change-transform"
						>
							03 // FOUR SOVEREIGN PILLARS
						</div>
						<div className="relative z-20 mx-auto w-full max-w-7xl mb-6 bg-[#FFFFFF] border-2 border-[#231412] p-5 shadow-[6px_6px_0px_#231412] flex flex-wrap items-center justify-between gap-4">
							<div>
								<div className="text-[11px] font-mono uppercase tracking-[0.2em] text-[#C8281E] font-bold">
									ACT III | FOUR PILLARS OF SOVEREIGNTY
								</div>
								<h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-[#231412] mt-1">
									Engineered for Zero-Drift Execution.
								</h2>
							</div>
							<div className="flex items-center gap-3">
								<span className="text-[10px] font-mono uppercase tracking-[0.16em] text-[#231412] font-bold hidden sm:inline">
									{pillarLockedDone?"ALL 4 PILLARS LOCKED":"HORIZONTAL STAGE ACTIVE"}
								</span>
								<div className="flex items-center gap-1.5">
									{pillarChapters.map((ch,idx)=>(
										<span
											key={ch.index}
											className={`px-3 py-1.5 rounded-none text-xs font-mono font-bold border-2 border-[#231412] transition-colors ${
												activePillar===idx
													?"bg-[#C8281E] text-white"
													:"bg-[#FAF7F2] text-[#231412]"
											}`}
										>
											{ch.index}
										</span>
									))}
								</div>
							</div>
						</div>
						<div className="w-full h-2 bg-[#FAF7F2] border border-[#231412] mt-1 mb-6">
							<div ref={pillarBarRef} className="h-full bg-[#C8281E] w-0"/>
						</div>
						<div
							ref={pillarStripRef}
							className="relative z-20 flex items-stretch gap-8 will-change-transform pr-28"
						>
							{pillarChapters.map((ch,idx)=>(
								<div
									key={ch.index}
									ref={(el)=>{
										pillarCardRefs.current[idx]=el;
									}}
									className="w-[85vw] sm:w-[540px] lg:w-[620px] shrink-0 rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-8 sm:p-10 shadow-[8px_8px_0px_#C8281E] flex flex-col justify-between will-change-transform"
								>
									<div>
										<div className="flex items-center justify-between gap-4 border-b-2 border-[#231412] pb-3">
											<span className="text-xs font-mono uppercase tracking-[0.18em] text-[#C8281E] font-bold">
												<ScrambleText text={ch.eyebrow} />
											</span>
											<span className="text-3xl font-mono font-bold text-[#231412]">
												{ch.index}
											</span>
										</div>
										<h3 className="text-2xl sm:text-3xl font-bold text-[#231412] mt-5">
											{ch.title}
										</h3>
										<p className="text-sm font-bold text-[#C8281E] mt-2 font-mono">
											{ch.subtitle}
										</p>
										<p className="text-sm sm:text-base text-[#231412] leading-relaxed mt-4">
											{ch.body}
										</p>
									</div>
									<div className="mt-6 pt-5 border-t-2 border-[#231412] grid grid-cols-1 sm:grid-cols-3 gap-2.5">
										{ch.metrics.map((m)=>(
											<div
												key={m}
												className="rounded-none bg-[#FAF7F2] border-2 border-[#231412] px-3 py-2 text-[11px] font-mono text-[#231412] font-bold"
											>
												{m}
											</div>
										))}
									</div>
								</div>
							))}
						</div>
					</div>
				</section>
				<VelocityMarquee
					duration={26}
					items={[
						"18 SPECIALIZED INSTRUMENTS",
						"UNIFIED DATA SPINE",
						"IMMUTABLE APPEND-ONLY LEDGER",
						"GOVERNED APPROVAL QUEUE",
						"REAL-TIME TREASURY"
					]}
				/>
				<section
					id="act-matrix"
					ref={matrixSectionRef}
					className="relative w-full py-28 px-6 lg:px-14 bg-transparent overflow-hidden"
				>
					<div
						ref={matrixWatermarkRef}
						aria-hidden="true"
						className="pointer-events-none select-none absolute right-8 top-10 text-[11vw] font-mono font-bold uppercase tracking-[0.14em] text-[#231412]/[0.045] whitespace-nowrap will-change-transform"
					>
						04 // 18-INSTRUMENT MATRIX
					</div>
					<div className="relative z-20 mx-auto max-w-7xl">
						<div className="max-w-3xl mb-16 bg-[#FFFFFF] rounded-none p-7 border-2 border-[#231412] shadow-[8px_8px_0px_#231412]">
							<div className="text-xs font-mono uppercase tracking-[0.2em] text-[#C8281E] font-bold">
								COMPLETE 18-MODULE OPERATING MATRIX
							</div>
							<h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#231412] mt-2">
								One Unified Spine. Eighteen Specialized Instruments.
							</h2>
							<p className="text-sm sm:text-base text-[#231412] mt-3 leading-relaxed">
								Every module shares the same underlying ledger truth—update an invoice in Sales and watch Inventory, Khata, Finance, Analytics, and Audit reflect it in real time.
							</p>
						</div>
						<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							{capabilityInstruments.map((inst,idx)=>(
								<div
									key={inst.code}
									ref={(el)=>{
										matrixCardRefs.current[idx]=el;
									}}
									className="will-change-transform"
								>
									<motion.div
										whileHover={{x:-4,y:-4}}
										whileTap={{x:0,y:0}}
										onClick={triggerWorkspaceAccess}
										data-testid={`capability-card-${inst.code}`}
										className="h-full cursor-pointer rounded-none bg-[#FFFFFF] border-2 border-[#231412] hover:border-[#C8281E] p-6 shadow-[6px_6px_0px_#231412] hover:shadow-[10px_10px_0px_#C8281E] transition-all flex flex-col justify-between"
									>
										<div>
											<div className="flex items-center justify-between text-xs font-mono border-b border-[#231412]/20 pb-2.5">
												<span className="px-2.5 py-1 rounded-none bg-[#231412] text-[#FFFFFF] font-bold">
													{`${inst.code} | ${inst.domain}`}
												</span>
												<span className="text-[11px] font-bold text-[#C8281E]">
													{inst.telemetry}
												</span>
											</div>
											<h3 className="text-xl font-bold text-[#231412] mt-4">
												{inst.name}
											</h3>
											<p className="text-sm text-[#5C403B] mt-2 leading-relaxed">
												{inst.summary}
											</p>
										</div>
										<div className="mt-5 pt-3 border-t-2 border-[#231412] flex items-center justify-between text-xs font-mono text-[#C8281E] font-bold">
											<span>LAUNCH INSTRUMENT</span>
											<span>→</span>
										</div>
									</motion.div>
								</div>
							))}
						</div>
					</div>
				</section>
				<section
					id="act-command"
					className="relative w-full py-24 px-6 lg:px-14 bg-transparent"
				>
					<div
						ref={commandCardRef}
						className="mx-auto max-w-5xl rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-10 sm:p-16 text-center shadow-[12px_12px_0px_#C8281E] will-change-transform"
					>
						<div className="inline-flex items-center gap-2 rounded-none bg-[#231412] px-4 py-1.5 text-xs font-mono font-bold uppercase tracking-[0.2em] text-[#FFFFFF] mb-5">
							READY FOR COMMAND
						</div>
						<h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-[#231412]">
							Step Into Your Financial Cockpit.
						</h2>
						<p className="mt-4 text-base text-[#231412] max-w-2xl mx-auto">
							Experience deterministic bookkeeping, real-time FIFO inventory, and governed AI intelligence in one cohesive workspace.
						</p>
						<div className="mt-8 flex flex-wrap justify-center gap-4">
							<motion.button
								type="button"
								data-testid="command-portal-cta"
								onClick={triggerWorkspaceAccess}
								whileHover={{x:-3,y:-3}}
								whileTap={{x:0,y:0}}
								className="rounded-none bg-[#C8281E] border-2 border-[#231412] px-8 py-4 text-xs sm:text-sm font-mono uppercase tracking-[0.18em] text-white font-bold shadow-[6px_6px_0px_#231412] hover:bg-[#A61B12] transition-colors"
							>
								Authenticate & Launch Workspace →
							</motion.button>
						</div>
					</div>
				</section>
			</main>
		</div>
	);
}
