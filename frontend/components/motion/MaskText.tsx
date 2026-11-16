'use client';
import React,{ReactNode}from'react';
import{motion}from'framer-motion';
export interface MaskTextProps{
	children:ReactNode;
	className?:string;
	delay?:number;
	duration?:number;
}
export function MaskText({children,className,delay=0,duration=0.75}:MaskTextProps){
	return(
		<span className={`inline-block overflow-hidden align-top ${className||''}`}>
			<motion.span
				className="inline-block will-change-transform"
				initial={{y:'105%',opacity:0.15}}
				animate={{y:0,opacity:1}}
				transition={{duration,delay,ease:[0.22,1,0.36,1]}}
			>
				{children}
			</motion.span>
		</span>
	);
}
