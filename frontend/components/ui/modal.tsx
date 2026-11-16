'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { clsx } from 'clsx';
import { X } from 'lucide-react';
export interface ModalProps {
	isOpen: boolean;
	onClose: () => void;
	title?: string;
	description?: string;
	children: React.ReactNode;
	maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}
export function Modal({ isOpen, onClose, title, description, children, maxWidth = 'md' }: ModalProps) {
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
	const widths = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-xl', '2xl': 'max-w-2xl' };
	return (
		<AnimatePresence>
			{isOpen && (
				<motion.div
					key="modal-overlay"
					role="dialog"
					aria-modal="true"
					className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#231412]/30 backdrop-blur-sm"
					initial={{ opacity: 0 }}
					animate={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					transition={{ duration: 0.18, ease: 'easeOut' }}
				>
					<MotionButton
						type="button"
						aria-label="Dismiss dialog overlay"
						onClick={onClose}
						className="fixed inset-0 border-0 bg-transparent p-0"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
					/>
					<motion.section
						aria-label={title || 'Dialog'}
						className={clsx('relative z-10 w-full overflow-hidden rounded-3xl border border-[#C8281E]/20 bg-white p-6 text-[#231412] backdrop-blur-2xl shadow-[0_25px_70px_rgba(200,40,30,0.12)]', widths[maxWidth])}
						initial={{ opacity: 0, y: 14, scale: 0.98 }}
						animate={{ opacity: 1, y: 0, scale: 1 }}
						exit={{ opacity: 0, y: 8, scale: 0.99 }}
						transition={{ type: 'spring', stiffness: 340, damping: 28 }}
					>
						<MotionButton
							type="button"
							aria-label="Close dialog"
							onClick={onClose}
							className="absolute top-4 right-4 p-2 rounded-xl text-[#6E524D] hover:text-[#C8281E] hover:bg-[#C8281E]/[0.08] transition-colors"
						>
							<X size={16} />
						</MotionButton>
						{title && (
							<div className="mb-4 pr-8">
								<h2 className="text-base font-bold text-[#231412] tracking-tight">{title}</h2>
								{description && (
									<p className="text-xs text-[#6E524D] mt-1 leading-relaxed">{description}</p>
								)}
							</div>
						)}
						{children}
					</motion.section>
				</motion.div>
			)}
		</AnimatePresence>
	);
}
