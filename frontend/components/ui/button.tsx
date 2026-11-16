'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React, { forwardRef } from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onDrag' | 'onDragStart' | 'onDragEnd'> {
	variant?: 'primary' | 'secondary' | 'glass' | 'danger' | 'ghost' | 'brass';
	size?: 'sm' | 'md' | 'lg';
	isLoading?: boolean;
	leftIcon?: React.ReactNode;
	rightIcon?: React.ReactNode;
}
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
	(
		{
			className,
			variant = 'glass',
			size = 'md',
			isLoading = false,
			disabled,
			leftIcon,
			rightIcon,
			children,
			...props
		},
		ref
	) => {
		const motionButtonProps = props as unknown as React.ComponentProps<typeof motion.button>;
		const baseStyles = 'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#C8281E]/30 disabled:opacity-50 disabled:cursor-not-allowed select-none';
		const sizeStyles = {
			sm: 'text-xs px-3 py-1.5 gap-1.5 h-8',
			md: 'text-xs px-4 py-2 gap-2 h-10',
			lg: 'text-sm px-6 py-2.5 gap-2.5 h-12',
		};
		const variantStyles = {
			primary: 'bg-gradient-to-r from-[#C8281E] to-[#E03E32] text-white shadow-[0_8px_24px_rgba(200,40,30,0.28)] border border-[#C8281E]/30 hover:brightness-110 font-bold',
			secondary: 'bg-white text-[#231412] hover:bg-[#FAF7F2] border border-[#C8281E]/20 shadow-sm',
			glass: 'bg-white/90 text-[#231412] border border-[#C8281E]/20 hover:border-[#C8281E]/50 hover:bg-white backdrop-blur-lg shadow-sm',
			brass: 'bg-[#FAF7F2] text-[#C8281E] border border-[#C8281E]/25 hover:bg-white',
			danger: 'bg-[#C8281E]/10 text-[#C8281E] hover:bg-[#C8281E]/20 border border-[#C8281E]/30',
			ghost: 'bg-transparent text-[#6E524D] hover:text-[#C8281E] hover:bg-[#C8281E]/[0.05]',
		};
		return (
			<MotionButton
				ref={ref}
				disabled={disabled || isLoading}
				className={clsx(baseStyles, sizeStyles[size], variantStyles[variant], className)}
				whileHover={disabled || isLoading ? undefined : { y: -2, scale: 1.015 }}
				whileTap={disabled || isLoading ? undefined : { y: 1, scale: 0.98 }}
				transition={{ type: 'spring', stiffness: 420, damping: 28 }}
				{...motionButtonProps}
			>
				{isLoading && <Loader2 className="w-4 h-4 animate-spin text-current" />}
				{!isLoading && leftIcon}
				<span>{children}</span>
				{!isLoading && rightIcon}
			</MotionButton>
		);
	}
);
Button.displayName = 'Button';
