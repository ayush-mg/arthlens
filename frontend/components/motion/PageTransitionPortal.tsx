"use client";
import React,{useEffect,useRef,useState}from"react";
import{usePathname}from"next/navigation";
import{motion,AnimatePresence}from"framer-motion";
export function PageTransitionPortal({children}:{children:React.ReactNode}){
	const pathname=usePathname();
	const prevPathRef=useRef<string|null>(null);
	const[showSweep,setShowSweep]=useState(false);
	useEffect(()=>{
		if(prevPathRef.current===null){
			prevPathRef.current=pathname;
			return;
		}
		if(prevPathRef.current!==pathname){
			prevPathRef.current=pathname;
			setShowSweep(true);
			const timer=window.setTimeout(()=>{
				setShowSweep(false);
			},420);
			return()=>window.clearTimeout(timer);
		}
	},[pathname]);
	return(
		<div className="relative min-h-screen w-full bg-transparent">
			<AnimatePresence>
				{showSweep&&(
					<motion.div
						key={`sweep-${pathname}`}
						initial={{scaleX:0,originX:0}}
						animate={{scaleX:[0,1,0],originX:[0,0,1]}}
						exit={{opacity:0}}
						transition={{duration:0.42,ease:[0.22,1,0.36,1]}}
						className="fixed inset-0 z-[90] pointer-events-none bg-gradient-to-r from-[#C8281E]/20 via-[#E64833]/25 to-transparent backdrop-blur-[2px]"
					/>
				)}
			</AnimatePresence>
			<div className="relative z-[10] w-full bg-transparent">
				{children}
			</div>
		</div>
	);
}
