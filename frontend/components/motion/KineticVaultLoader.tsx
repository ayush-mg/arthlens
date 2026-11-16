'use client';
import {motion} from 'framer-motion';
import {ShieldCheck} from 'lucide-react';
import {ArthLensBrandMark} from './ArthLensBrandMark';

export function KineticVaultLoader({label='VERIFYING SECURE SESSION...'}:{label?:string}){
	return(
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-[#FAF7F2]/95 backdrop-blur-xl">
			<div className="flex flex-col items-center text-center p-8 max-w-sm w-full mx-4 rounded-3xl bg-white/90 border border-[#C8281E]/20 shadow-[0_24px_60px_rgba(200,40,30,0.12)]">
				<div className="relative mb-6 flex items-center justify-center">
					<motion.div
						className="absolute w-24 h-24 rounded-full border-2 border-dashed border-[#C8281E]/30"
						animate={{rotate:360}}
						transition={{repeat:Infinity,duration:8,ease:'linear'}}
					/>
					<motion.div
						className="absolute w-20 h-20 rounded-full border border-[#C8281E]/20"
						animate={{scale:[1,1.1,1],opacity:[0.4,0.8,0.4]}}
						transition={{repeat:Infinity,duration:2.5,ease:'easeInOut'}}
					/>
					<div className="relative z-10 p-4 rounded-2xl bg-[#C8281E]/10 text-[#C8281E] border border-[#C8281E]/20 shadow-sm">
						<ShieldCheck className="w-8 h-8 shrink-0 text-[#C8281E]" />
					</div>
				</div>
				<ArthLensBrandMark compact />
				<div className="mt-4 flex items-center gap-2">
					<span className="w-2 h-2 rounded-full bg-[#C8281E] animate-ping" />
					<span className="text-[10px] font-mono font-bold tracking-widest text-[#C8281E]">VAULT ACCESS GATE</span>
				</div>
				<p className="mt-2 text-xs font-semibold text-[#7A5A54] font-mono tracking-wider">{label}</p>
			</div>
		</div>
	);
}

export default KineticVaultLoader;
