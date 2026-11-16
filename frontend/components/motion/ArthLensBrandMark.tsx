'use client';
import React,{useState}from'react';
import{motion}from'framer-motion';

export interface ArthLensBrandMarkProps{
	className?:string;
	compact?:boolean;
}

export function ArthLensBrandMark({className,compact=false}:ArthLensBrandMarkProps){
	const [isHovered,setIsHovered]=useState(false);

	return(
		<div
			className={`flex items-center gap-3.5 select-none group cursor-pointer ${className||''}`}
			onMouseEnter={()=>setIsHovered(true)}
			onMouseLeave={()=>setIsHovered(false)}
		>
			<motion.div
				whileHover={{scale:1.08,rotate:3}}
				whileTap={{scale:0.95}}
				className="relative w-12 h-12 flex items-center justify-center shrink-0"
			>
				<svg
					viewBox="0 0 64 64"
					className="w-full h-full overflow-visible"
					fill="none"
					xmlns="http://www.w3.org/2000/svg"
				>
					<motion.g
						animate={{rotate:isHovered?180:360}}
						transition={{duration:isHovered?6:36,repeat:Infinity,ease:"linear"}}
						style={{originX:"32px",originY:"32px"}}
					>
						<circle
							cx="32"
							cy="32"
							r="30"
							stroke="#231412"
							strokeWidth="1.2"
							strokeDasharray="3 4"
							strokeOpacity="0.4"
						/>
						<circle
							cx="32"
							cy="32"
							r="26"
							stroke="#C8281E"
							strokeWidth="0.8"
							strokeDasharray="1 5"
							strokeOpacity="0.6"
						/>
						<line x1="32" y1="0" x2="32" y2="4" stroke="#231412" strokeWidth="1.8" />
						<line x1="32" y1="60" x2="32" y2="64" stroke="#231412" strokeWidth="1.8" />
						<line x1="0" y1="32" x2="4" y2="32" stroke="#231412" strokeWidth="1.8" />
						<line x1="60" y1="32" x2="64" y2="32" stroke="#231412" strokeWidth="1.8" />
						<circle cx="32" cy="0" r="1.5" fill="#C8281E" />
						<circle cx="64" cy="32" r="1.5" fill="#C8281E" />
						<circle cx="32" cy="64" r="1.5" fill="#C8281E" />
						<circle cx="0" cy="32" r="1.5" fill="#C8281E" />
					</motion.g>

					<polygon
						points="32,4 60,32 32,60 4,32"
						fill="#231412"
						stroke="#231412"
						strokeWidth="1.5"
						strokeLinejoin="miter"
					/>
					<polygon
						points="32,9 55,32 32,55 9,32"
						fill="#FAF7F2"
						stroke="#231412"
						strokeWidth="1"
					/>

					<polygon
						points="32,12 18,48 26,48 32,34"
						fill="#231412"
					/>
					<polygon
						points="32,12 46,48 38,48 32,34"
						fill="#C8281E"
					/>

					<path
						d="M20 32 C24 22 40 22 44 32 C40 42 24 42 20 32 Z"
						fill="#C8281E"
						fillOpacity={isHovered?1:0.9}
						stroke="#231412"
						strokeWidth="1.2"
					/>

					<polygon
						points="32,24 38,32 32,40 26,32"
						fill="#FFFFFF"
						stroke="#231412"
						strokeWidth="1"
					/>

					<line x1="32" y1="16" x2="32" y2="48" stroke="#231412" strokeWidth="0.8" strokeDasharray="2 2" />
					<line x1="16" y1="32" x2="48" y2="32" stroke="#231412" strokeWidth="0.8" strokeDasharray="2 2" />

					<circle cx="32" cy="32" r="3" fill="#C8281E" stroke="#FFFFFF" strokeWidth="1" />
					<circle cx="32" cy="32" r="1" fill="#FFFFFF" />

					<line x1="14" y1="52" x2="50" y2="52" stroke="#231412" strokeWidth="2" strokeLinecap="square" />
					<rect x="29" y="50" width="6" height="4" fill="#C8281E" />
				</svg>
			</motion.div>

			<div className="flex flex-col justify-center leading-none">
				<div className="flex items-center">
					<span className="text-2xl font-black tracking-tight text-[#231412]">
						ARTH
					</span>
					<span className="text-2xl font-black tracking-tight text-[#C8281E] ml-1">
						LENS
					</span>
					<div className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-[#FAF7F2] border border-[#231412] shadow-[1.5px_1.5px_0px_#231412] ml-2 self-center">
						<span className="w-1.5 h-1.5 rounded-none bg-[#C8281E]" />
						<span className="text-[9px] font-mono font-black text-[#231412] leading-none">
							°01
						</span>
					</div>
				</div>

				{!compact?(
					<div className="flex items-center gap-2 mt-1.5">
						<span className="text-xs font-serif font-black text-[#C8281E] leading-none tracking-wide">
							अर्थ
						</span>
						<span className="h-2.5 w-px bg-[#231412]/30" />
						<span className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-[#5C403B] leading-none">
							SOVEREIGN FINANCIAL TOPOLOGY
						</span>
						<span className="w-1.5 h-1.5 rounded-none bg-[#065F46] animate-pulse ml-0.5" />
					</div>
				):(
					<div className="flex items-center gap-1.5 mt-1">
						<span className="text-[10px] font-serif font-bold text-[#C8281E] leading-none">
							अर्थ
						</span>
						<span className="h-2 w-px bg-[#231412]/30" />
						<span className="text-[8px] font-mono font-bold uppercase tracking-[0.16em] text-[#5C403B] leading-none">
							KHATA TOPOLOGY
						</span>
					</div>
				)}
			</div>
		</div>
	);
}