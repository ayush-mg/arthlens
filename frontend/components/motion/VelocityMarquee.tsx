'use client';
import React from 'react';
import {motion,useReducedMotion} from 'framer-motion';
export interface VelocityMarqueeProps{
	items:string[];
	className?:string;
	duration?:number;
	reverse?:boolean;
}
export function VelocityMarquee({items,className,duration=28,reverse=false}:VelocityMarqueeProps){
	const reducedMotion=useReducedMotion();
	const repeated=[...items,...items,...items];
	return(
		<div className={`w-full overflow-hidden whitespace-nowrap py-3.5 bg-[#FFFFFF] border-y-2 border-[#231412] select-none ${className||''}`}>
			<motion.div
				className="flex items-center gap-8 w-max will-change-transform"
				animate={reducedMotion?undefined:{x:reverse?['-33.33%','0%']:['0%','-33.33%']}}
				transition={{duration,ease:'linear',repeat:Infinity}}
			>
				{repeated.map((item,index)=>(
					<span
						key={`${item}-${index}`}
						className="inline-flex items-center gap-3 text-xs sm:text-sm font-mono font-bold uppercase tracking-[0.2em] text-[#231412]"
					>
						<span className="w-2 h-2 rounded-none bg-[#C8281E]" />
						<span>{item}</span>
						<span className="text-[#C8281E] font-bold">❖</span>
					</span>
				))}
			</motion.div>
		</div>
	);
}
