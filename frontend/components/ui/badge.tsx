'use client';
import React from 'react';
import { clsx } from 'clsx';
import { motion, useReducedMotion } from 'framer-motion';
export interface BadgeProps extends Omit<React.HTMLAttributes<HTMLSpanElement>, 'onAnimationStart' | 'onAnimationEnd' | 'onDrag' | 'onDragStart' | 'onDragEnd'> {
	variant?: 'success' | 'warning' | 'error' | 'info' | 'brass' | 'neutral';
	size?: 'sm' | 'md';
	dot?: boolean;
}
export function Badge({
	className,
	variant = 'neutral',
	size = 'md',
	dot = false,
	children,
	...props
}: BadgeProps) {
	const reducedMotion = useReducedMotion();
	const baseStyles = 'inline-flex items-center font-medium rounded-full tracking-wide select-none';
	const sizeStyles = {
		sm: 'text-[10px] px-2 py-0.5 gap-1',
		md: 'text-xs px-2.5 py-1 gap-1.5',
	};
	const variantStyles = {
		success: 'bg-[#2D7D52]/10 text-[#2D7D52] border border-[#2D7D52]/25',
		warning: 'bg-[#D4A359]/15 text-[#9A6218] border border-[#D4A359]/30',
		error: 'bg-[#C8281E]/10 text-[#C8281E] border border-[#C8281E]/25',
		info: 'bg-[#FAF7F2] text-[#231412] border border-[#C8281E]/20',
		brass: 'bg-[#C8281E]/[0.08] text-[#C8281E] border border-[#C8281E]/20',
		neutral: 'bg-[#FAF7F2] text-[#6E524D] border border-[#C8281E]/15',
	};
	const dotColors = {
		success: 'bg-[#2D7D52]',
		warning: 'bg-[#D4A359]',
		error: 'bg-[#C8281E]',
		info: 'bg-[#C8281E]',
		brass: 'bg-[#C8281E]',
		neutral: 'bg-[#9A7E78]',
	};
	return (
		<motion.span
			className={clsx(baseStyles, sizeStyles[size], variantStyles[variant], className)}
			whileHover={reducedMotion ? undefined : { scale: 1.05 }}
			transition={{ type: 'spring', stiffness: 500, damping: 25 }}
			{...(props as any)}
		>
			{dot && (
				<span
					className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', dotColors[variant])}
					aria-hidden="true"
				/>
			)}
			{children}
		</motion.span>
	);
}
