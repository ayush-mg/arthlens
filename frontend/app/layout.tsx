import"./globals.css";
import React from"react";
import type{Metadata}from"next";
import{PageTransitionPortal}from"@/components/motion/PageTransitionPortal";
import{VirtualNetBackground}from"@/components/motion/VirtualNetBackground";
export const metadata:Metadata={
	title:"ArthLens — Sovereign Financial & Decision Topology",
	description:"Deterministic double-entry Khata, FIFO lot traceability, cashflow bridge, and human-governed AI."
};
export default function RootLayout({children}:{children:React.ReactNode}){
	return(
		<html lang="en">
			<body className="min-h-screen bg-transparent text-[#231412] antialiased selection:bg-[#C8281E] selection:text-white">
				<VirtualNetBackground/>
				<div className="relative z-10 min-h-screen w-full bg-transparent">
					<PageTransitionPortal>
						{children}
					</PageTransitionPortal>
				</div>
			</body>
		</html>
	);
}
