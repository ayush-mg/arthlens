"use client";
import React,{useEffect,useRef,useState}from"react";
import{motion}from"framer-motion";
export interface ZoomPortalMetric{
	label:string;
	value:string;
	detail:string;
}
export type ZoomMetricItem=ZoomPortalMetric;
export interface ZoomScrollPortalProps{
	eyebrow:string;
	headline:string;
	highlightWord:string;
	description:string;
	metrics:ZoomPortalMetric[];
	ctaLabel:string;
	onCtaClick:()=>void;
}
export function ZoomScrollPortal({
	eyebrow,
	headline,
	highlightWord,
	description,
	metrics,
	ctaLabel,
	onCtaClick
}:ZoomScrollPortalProps){
	const trackRef=useRef<HTMLDivElement|null>(null);
	const vaultRef=useRef<HTMLDivElement|null>(null);
	const watermarkRef=useRef<HTMLDivElement|null>(null);
	const progressFillRef=useRef<HTMLDivElement|null>(null);
	const satelliteRefs=useRef<Array<HTMLDivElement|null>>([]);
	const pathRefs=useRef<Array<SVGPathElement|null>>([]);
	const[lockedComplete,setLockedComplete]=useState(false);
	const lockedRef=useRef(false);
	useEffect(()=>{
		let rafId=0;
		let smoothProgress=0;
		const entryOffsets=[
			{x:140,y:75},
			{x:-140,y:75},
			{x:140,y:-75},
			{x:-140,y:-75}
		];
		const updateFrame=()=>{
			const track=trackRef.current;
			if(track){
				const rect=track.getBoundingClientRect();
				const viewH=window.innerHeight||1;
				const scrollable=Math.max(1,rect.height-viewH);
				const rawScrollRatio=Math.max(0,Math.min(1,-rect.top/scrollable));
				const activeTarget=Math.max(0,Math.min(1,(rawScrollRatio-0.04)/0.72));
				smoothProgress+=(activeTarget-smoothProgress)*0.16;
				if(Math.abs(activeTarget-smoothProgress)<0.0015){
					smoothProgress=activeTarget;
				}
				const isDone=smoothProgress>=0.98;
				if(isDone!==lockedRef.current){
					lockedRef.current=isDone;
					setLockedComplete(isDone);
				}
				if(progressFillRef.current){
					progressFillRef.current.style.width=`${(smoothProgress*100).toFixed(1)}%`;
				}
				if(watermarkRef.current){
					const wmX=(0.5-smoothProgress)*180;
					const wmY=(smoothProgress-0.5)*-55;
					watermarkRef.current.style.transform=`translate3d(${wmX.toFixed(1)}px,${wmY.toFixed(1)}px,0px)`;
				}
				const easeVault=1-Math.pow(1-smoothProgress,3);
				if(vaultRef.current){
					const scale=0.84+easeVault*0.16;
					const translateY=(1-easeVault)*44;
					const rotX=(1-easeVault)*9;
					vaultRef.current.style.transform=`perspective(1200px) translate3d(0px,${translateY.toFixed(1)}px,0px) rotateX(${rotX.toFixed(2)}deg) scale(${scale.toFixed(4)})`;
				}
				const satWindow=Math.min(1,Math.max(0,(smoothProgress-0.12)/0.78));
				const satEase=1-Math.pow(1-satWindow,3);
				for(let i=0;i<4;i+=1){
					const sat=satelliteRefs.current[i];
					if(sat){
						const offset=entryOffsets[i];
						const tx=offset.x*(1-satEase);
						const ty=offset.y*(1-satEase);
						const sc=0.78+satEase*0.22;
						const op=0.12+satEase*0.88;
						sat.style.transform=`translate3d(${tx.toFixed(1)}px,${ty.toFixed(1)}px,0px) scale(${sc.toFixed(3)})`;
						sat.style.opacity=op.toFixed(3);
					}
					const wire=pathRefs.current[i];
					if(wire){
						const dashOffset=(1-satEase)*360;
						wire.style.strokeDashoffset=dashOffset.toFixed(1);
					}
				}
			}
			rafId=window.requestAnimationFrame(updateFrame);
		};
		rafId=window.requestAnimationFrame(updateFrame);
		return()=>{
			window.cancelAnimationFrame(rafId);
		};
	},[]);
	const leftTop=metrics[0];
	const rightTop=metrics[1];
	const leftBottom=metrics[2];
	const rightBottom=metrics[3];
	return(
		<div ref={trackRef} className="relative w-full h-[270vh] bg-transparent">
			<div className="sticky top-0 left-0 h-screen w-full flex flex-col items-center justify-center overflow-hidden px-6 lg:px-12 pt-16">
				<div
					ref={watermarkRef}
					aria-hidden="true"
					className="pointer-events-none select-none absolute inset-x-0 top-24 flex justify-center text-[11vw] font-mono font-bold uppercase tracking-[0.14em] text-[#231412]/[0.045] whitespace-nowrap will-change-transform"
				>
					02 // RECORD TOPOLOGY VAULT
				</div>
				<svg
					viewBox="0 0 1200 540"
					aria-hidden="true"
					className="pointer-events-none hidden lg:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-7xl h-[540px] z-10"
				>
					<path
						ref={(el)=>{
							pathRefs.current[0]=el;
						}}
						d="M 430 210 L 310 135 L 220 135"
						fill="none"
						stroke="#C8281E"
						strokeWidth="2.5"
						strokeDasharray="360"
						strokeDashoffset="360"
					/>
					<path
						ref={(el)=>{
							pathRefs.current[1]=el;
						}}
						d="M 770 210 L 890 135 L 980 135"
						fill="none"
						stroke="#C8281E"
						strokeWidth="2.5"
						strokeDasharray="360"
						strokeDashoffset="360"
					/>
					<path
						ref={(el)=>{
							pathRefs.current[2]=el;
						}}
						d="M 430 330 L 310 405 L 220 405"
						fill="none"
						stroke="#C8281E"
						strokeWidth="2.5"
						strokeDasharray="360"
						strokeDashoffset="360"
					/>
					<path
						ref={(el)=>{
							pathRefs.current[3]=el;
						}}
						d="M 770 330 L 890 405 L 980 405"
						fill="none"
						stroke="#C8281E"
						strokeWidth="2.5"
						strokeDasharray="360"
						strokeDashoffset="360"
					/>
				</svg>
				<div className="relative z-20 mx-auto w-full max-w-7xl grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
					<div className="hidden lg:flex lg:col-span-3 flex-col justify-between gap-16 z-10">
						{leftTop&&(
							<div
								ref={(el)=>{
									satelliteRefs.current[0]=el;
								}}
								className="w-full rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-4 shadow-[6px_6px_0px_#C8281E] will-change-transform"
							>
								<div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#C8281E] font-bold border-b-2 border-[#231412]/15 pb-1.5">
									{leftTop.label}
								</div>
								<div className="text-base font-bold text-[#231412] mt-2 font-mono">
									{leftTop.value}
								</div>
								<div className="text-xs text-[#5C403B] mt-1 leading-relaxed">
									{leftTop.detail}
								</div>
							</div>
						)}
						{leftBottom&&(
							<div
								ref={(el)=>{
									satelliteRefs.current[2]=el;
								}}
								className="w-full rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-4 shadow-[6px_6px_0px_#C8281E] will-change-transform"
							>
								<div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#C8281E] font-bold border-b-2 border-[#231412]/15 pb-1.5">
									{leftBottom.label}
								</div>
								<div className="text-base font-bold text-[#231412] mt-2 font-mono">
									{leftBottom.value}
								</div>
								<div className="text-xs text-[#5C403B] mt-1 leading-relaxed">
									{leftBottom.detail}
								</div>
							</div>
						)}
					</div>
					<div className="lg:col-span-6 flex justify-center z-20">
						<div
							ref={vaultRef}
							className="relative w-full rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-8 sm:p-10 text-center shadow-[10px_10px_0px_#231412] will-change-transform"
						>
							<div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-none bg-[#231412] text-[#FFFFFF] text-[11px] font-mono uppercase tracking-[0.2em] mb-5">
								<span className="w-2 h-2 rounded-none bg-[#C8281E]"/>
								{eyebrow}
							</div>
							<h2 className="text-3xl sm:text-4xl xl:text-5xl font-bold tracking-tight text-[#231412] leading-[1.06]">
								{headline}
								<span className="block text-[#C8281E] mt-1">
									{highlightWord}
								</span>
							</h2>
							<p className="mt-4 text-sm sm:text-base text-[#5C403B] leading-relaxed max-w-xl mx-auto">
								{description}
							</p>
							<div className="mt-6 grid grid-cols-2 gap-3 lg:hidden text-left">
								{metrics.slice(0,4).map((m)=>(
									<div key={m.label} className="rounded-none bg-[#FAF7F2] border-2 border-[#231412] p-3">
										<div className="text-[10px] font-mono font-bold text-[#C8281E]">{m.label}</div>
										<div className="text-sm font-bold text-[#231412] mt-0.5">{m.value}</div>
									</div>
								))}
							</div>
							<div className="mt-7">
								<motion.button
									type="button"
									onClick={onCtaClick}
									whileHover={{x:-2,y:-2}}
									whileTap={{x:0,y:0}}
									className="inline-flex items-center gap-2 rounded-none bg-[#C8281E] border-2 border-[#231412] px-7 py-3.5 text-xs font-mono uppercase tracking-[0.18em] text-white font-bold shadow-[5px_5px_0px_#231412] hover:bg-[#A61B12] transition-colors"
								>
									{ctaLabel}
								</motion.button>
							</div>
							<div className="mt-7 pt-4 border-t-2 border-[#231412]/15">
								<div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.16em] text-[#231412] mb-1.5">
									<span>STAGE LOCK TELEMETRY</span>
									<span className="font-bold text-[#C8281E]">
										{lockedComplete?"100% LOCKED — READY TO ADVANCE":"SCROLL TO LOCK RECORD LAYER"}
									</span>
								</div>
								<div className="w-full h-2 bg-[#FAF7F2] border border-[#231412]">
									<div ref={progressFillRef} className="h-full bg-[#C8281E] w-0"/>
								</div>
							</div>
						</div>
					</div>
					<div className="hidden lg:flex lg:col-span-3 flex-col justify-between gap-16 z-10">
						{rightTop&&(
							<div
								ref={(el)=>{
									satelliteRefs.current[1]=el;
								}}
								className="w-full rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-4 shadow-[6px_6px_0px_#C8281E] will-change-transform"
							>
								<div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#C8281E] font-bold border-b-2 border-[#231412]/15 pb-1.5">
									{rightTop.label}
								</div>
								<div className="text-base font-bold text-[#231412] mt-2 font-mono">
									{rightTop.value}
								</div>
								<div className="text-xs text-[#5C403B] mt-1 leading-relaxed">
									{rightTop.detail}
								</div>
							</div>
						)}
						{rightBottom&&(
							<div
								ref={(el)=>{
									satelliteRefs.current[3]=el;
								}}
								className="w-full rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-4 shadow-[6px_6px_0px_#C8281E] will-change-transform"
							>
								<div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#C8281E] font-bold border-b-2 border-[#231412]/15 pb-1.5">
									{rightBottom.label}
								</div>
								<div className="text-base font-bold text-[#231412] mt-2 font-mono">
									{rightBottom.value}
								</div>
								<div className="text-xs text-[#5C403B] mt-1 leading-relaxed">
									{rightBottom.detail}
								</div>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
