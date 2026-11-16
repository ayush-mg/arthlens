'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { clsx } from 'clsx';
import { X } from 'lucide-react';
export interface DrawerProps {
	isOpen: boolean;
	onClose: () => void;
	title?: string;
	description?: string;
	children: React.ReactNode;
	position?: 'right' | 'left' | 'bottom';
	size?: 'sm' | 'md' | 'lg' | 'xl';
}
export function Drawer({ isOpen, onClose, title, description, children, position = 'right', size = 'md' }: DrawerProps) {
	useEffect(() => {
		if (!isOpen) return;
		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') onClose();
		};
		document.body.style.overflow = 'hidden';
		window.addEventListener('keydown', handleKeyDown);
		return () => {
			document.body.style.overflow = '';
			window.removeEventListener('keydown', handleKeyDown);
		};
	}, [isOpen, onClose]);
	const widths = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-xl' };
	const heights = { sm: 'h-64', md: 'h-96', lg: 'h-[500px]', xl: 'h-[650px]' };
	const enter = position === 'left' ? { x: '-100%' } : position === 'bottom' ? { y: '100%' } : { x: '100%' };
	const positionClass = position === 'left' ? 'inset-y-0 left-0 border-r border-[#C8281E]/20' : position === 'bottom' ? 'inset-x-0 bottom-0 border-t border-[#C8281E]/20 rounded-t-3xl' : 'inset-y-0 right-0 border-l border-[#C8281E]/20';
	return (
		<AnimatePresence>
			{isOpen && (
				<motion.div
					key="drawer-overlay"
					role="dialog"
					aria-modal="true"
					className="fixed inset-0 z-50 overflow-hidden bg-[#231412]/30 backdrop-blur-sm"
					initial={{ opacity: 0 }}
					animate={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					transition={{ duration: 0.18, ease: 'easeOut' }}
				>
					<MotionButton
						type="button"
						aria-label="Dismiss drawer overlay"
						onClick={onClose}
						className="fixed inset-0 border-0 bg-transparent p-0"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
					/>
					<motion.section
						aria-label={title || 'Drawer'}
						className={clsx('fixed z-10 flex w-full flex-col bg-white text-[#231412] backdrop-blur-2xl shadow-[0_25px_70px_rgba(200,40,30,0.12)]', positionClass, position === 'bottom' ? heights[size] : widths[size])}
						initial={enter}
						animate={{ x: 0, y: 0 }}
						exit={enter}
						transition={{ type: 'spring', stiffness: 360, damping: 32 }}
					>
						<div className="flex items-center justify-between border-b border-[#C8281E]/15 p-6">
							<div>
								{title && <h2 className="text-base font-bold text-[#231412] tracking-tight">{title}</h2>}
								{description && (
									<p className="text-xs text-[#6E524D] mt-1 leading-relaxed">{description}</p>
								)}
							</div>
							<MotionButton
								type="button"
								aria-label="Close drawer"
								onClick={onClose}
								className="p-2 rounded-xl text-[#6E524D] hover:text-[#C8281E] hover:bg-[#C8281E]/[0.08] transition-colors"
							>
								<X size={16} />
							</MotionButton>
						</div>
						<div className="flex-1 overflow-y-auto p-6">{children}</div>
					</motion.section>
				</motion.div>
			)}
		</AnimatePresence>
	);
}
