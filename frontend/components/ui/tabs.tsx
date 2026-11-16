'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React from 'react';
import { clsx } from 'clsx';
import { AnimatePresence, motion } from 'framer-motion';
export interface TabItem {
	id: string;
	label: string;
	count?: number;
	icon?: React.ReactNode;
}
export interface TabsProps {
	items: TabItem[];
	activeId: string;
	onChange: (id: string) => void;
	className?: string;
}
export function Tabs({ items, activeId, onChange, className }: TabsProps) {
	const activeTabLayoutId = React.useId();
	return (
		<div
			role="tablist"
			className={clsx(
				'inline-flex items-center gap-1.5 p-1.5 rounded-full bg-white/95 border border-[#C8281E]/20 backdrop-blur-2xl shadow-[0_10px_30px_rgba(200,40,30,0.08)]',
				className
			)}
		>
			{items.map((tab) => {
				const isActive = tab.id === activeId;
				return (
					<MotionButton
						key={tab.id}
						type="button"
						role="tab"
						aria-selected={isActive}
						onClick={() => onChange(tab.id)}
						className={clsx(
							'relative flex items-center gap-2 px-4 py-2 rounded-full text-xs font-semibold transition-colors duration-200 select-none',
							isActive ? 'text-white' : 'text-[#6E524D] hover:text-[#231412]'
						)}
						whileTap={{ scale: 0.97 }}
						transition={{ type: 'spring', stiffness: 380, damping: 28 }}
					>
						<AnimatePresence initial={false}>
							{isActive && (
								<motion.div
									layoutId={'arthlens-active-tab-' + activeTabLayoutId}
									className="absolute inset-0 -z-0 rounded-full bg-gradient-to-r from-[#C8281E] to-[#E03E32] shadow-[0_4px_14px_rgba(200,40,30,0.3)]"
									transition={{ type: 'spring', stiffness: 420, damping: 32 }}
								/>
							)}
						</AnimatePresence>
						{tab.icon}
						<span className="relative z-10">{tab.label}</span>
						{tab.count !== undefined && (
							<span
								className={clsx(
									'relative z-10 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold',
									isActive ? 'bg-white/20 text-white' : 'bg-[#C8281E]/10 text-[#C8281E]'
								)}
							>
								{tab.count}
							</span>
						)}
					</MotionButton>
				);
			})}
		</div>
	);
}
