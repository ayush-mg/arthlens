'use client';
import React,{useEffect,useState,useRef}from'react';
import{animate,useInView,useMotionValue,useReducedMotion}from'framer-motion';
export interface NumberTickerProps{
	value:number;
	prefix?:string;
	suffix?:string;
	decimals?:number;
	duration?:number;
	locale?:string;
	className?:string;
}
export function NumberTicker({value,prefix='',suffix='',decimals=0,duration=1.25,locale='en-IN',className=''}:NumberTickerProps){
	const ref=useRef<HTMLSpanElement|null>(null);
	const isInView=useInView(ref,{once:true,margin:'-40px'});
	const counter=useMotionValue(0);
	const prefersReducedMotion=useReducedMotion();
	const [display,setDisplay]=useState(()=>(0).toLocaleString(locale,{minimumFractionDigits:decimals,maximumFractionDigits:decimals}));
	useEffect(()=>{
		if(!isInView)return;
		const unsubscribe=counter.on('change',(latest)=>{
			setDisplay(latest.toLocaleString(locale,{minimumFractionDigits:decimals,maximumFractionDigits:decimals}));
		});
		const controls=animate(counter,value,{duration:prefersReducedMotion?0:duration,ease:[0.22,1,0.36,1]});
		return()=>{unsubscribe();controls.stop();};
	},[isInView,counter,decimals,duration,locale,prefersReducedMotion,value]);
	return <span ref={ref} className={`font-mono tabular-nums ${className}`}>{prefix}{display}{suffix}</span>;
}
