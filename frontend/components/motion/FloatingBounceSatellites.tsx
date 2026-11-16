"use client";
import React,{useEffect,useRef}from"react";
import{motion}from"framer-motion";
export interface SatelliteBoxItem{
	id:string;
	eyebrow:string;
	metric:string;
	delta:string;
	badgeTone:"crimson"|"emerald"|"amber";
	positionClass:string;
	parallaxSpeed:number;
	floatDelay:number;
}
export type SatelliteItem=SatelliteBoxItem;
export interface FloatingBounceSatellitesProps{
	items:SatelliteBoxItem[];
}
export function FloatingBounceSatellites({items}:FloatingBounceSatellitesProps){
	const layerRefs=useRef<Array<HTMLDivElement|null>>([]);
	useEffect(()=>{
		let rafId=0;
		let smoothY=window.scrollY||0;
		let smoothVel=0;
		let prevY=smoothY;
		let phase=0;
		const tick=()=>{
			phase+=0.025;
			const rawY=window.scrollY||0;
			const targetVel=Math.max(-22,Math.min(22,(rawY-prevY)*0.32));
			prevY=rawY;
			smoothY+=(rawY-smoothY)*0.15;
			smoothVel+=(targetVel-smoothVel)*0.14;
			for(let i=0;i<items.length;i+=1){
				const el=layerRefs.current[i];
				if(!el){
					continue;
				}
				const item=items[i];
				const idleY=Math.sin(phase+item.floatDelay*1.5)*4.5;
				const parallaxY=Math.max(-26,Math.min(26,smoothY*item.parallaxSpeed*0.09));
				const bounceY=smoothVel*(i%2===0?0.35:-0.35);
				const totalY=parallaxY+idleY+bounceY;
				el.style.transform=`translate3d(0px,${totalY.toFixed(2)}px,0px)`;
			}
			rafId=window.requestAnimationFrame(tick);
		};
		rafId=window.requestAnimationFrame(tick);
		return()=>{
			window.cancelAnimationFrame(rafId);
		};
	},[items]);
	const toneClasses=(tone:SatelliteBoxItem["badgeTone"])=>{
		if(tone==="emerald"){
			return"bg-[#065F46] text-white border-[#231412]";
		}
		if(tone==="amber"){
			return"bg-[#92400E] text-white border-[#231412]";
		}
		return"bg-[#C8281E] text-white border-[#231412]";
	};
	return(
		<div className="relative z-20 w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
			{items.map((item,idx)=>(
				<div
					key={item.id}
					ref={(el)=>{
						layerRefs.current[idx]=el;
					}}
					className="will-change-transform"
				>
					<motion.div
						whileHover={{x:-3,y:-3}}
						transition={{type:"spring",stiffness:280,damping:22}}
						className="w-full rounded-none bg-[#FFFFFF] border-2 border-[#231412] p-3.5 shadow-[5px_5px_0px_#C8281E]"
					>
						<div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b-2 border-[#231412]/15">
							<span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-[0.16em] text-[#231412]">
								<span className="w-2 h-2 rounded-none bg-[#C8281E]"/>
								{item.eyebrow}
							</span>
							<span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-none border ${toneClasses(item.badgeTone)}`}>
								{item.delta}
							</span>
						</div>
						<div className="text-sm font-bold tracking-tight text-[#231412] font-mono">
							{item.metric}
						</div>
					</motion.div>
				</div>
			))}
		</div>
	);
}
