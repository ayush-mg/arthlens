import React, { forwardRef } from 'react';
import { clsx } from 'clsx';
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
	label?: string;
	error?: string;
	helperText?: string;
	leftIcon?: React.ReactNode;
	rightIcon?: React.ReactNode;
}
export const Input = forwardRef<HTMLInputElement, InputProps>(
	({ className, label, error, helperText, leftIcon, rightIcon, id, ...props }, ref) => {
		const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
		return (
			<div className="w-full space-y-1.5">
				{label && (
					<label
						htmlFor={inputId}
						className="block text-xs font-semibold text-[#6E524D] tracking-wide"
					>
						{label}
					</label>
				)}
				<div className="relative flex items-center">
					{leftIcon && (
						<div className="absolute left-3.5 text-[#9A7E78] pointer-events-none flex items-center">
							{leftIcon}
						</div>
					)}
					<input
						ref={ref}
						id={inputId}
						className={clsx(
							'w-full rounded-xl bg-white text-[#231412] text-xs px-3.5 py-2.5 border border-[#C8281E]/20 focus:outline-none focus:ring-2 focus:ring-[#C8281E]/20 focus:border-[#C8281E] shadow-sm transition-all placeholder:text-[#9A7E78] disabled:opacity-50 disabled:cursor-not-allowed',
							leftIcon && '!pl-11 pr-4',
							rightIcon && 'pr-9',
							error && 'border-[#C8281E] focus:ring-[#C8281E]/30',
							className
						)}
						{...props}
					/>
					{rightIcon && (
						<div className="absolute right-3.5 text-[#9A7E78] flex items-center">
							{rightIcon}
						</div>
					)}
				</div>
				{error && <p className="text-[11px] font-medium text-[#C8281E] mt-1">{error}</p>}
				{!error && helperText && (
					<p className="text-[11px] text-[#9A7E78] mt-1">{helperText}</p>
				)}
			</div>
		);
	}
);
Input.displayName = 'Input';
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
	label?: string;
	error?: string;
	helperText?: string;
	options: { label: string; value: string | number }[];
}
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
	({ className, label, error, helperText, options, id, ...props }, ref) => {
		const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
		return (
			<div className="w-full space-y-1.5">
				{label && (
					<label
						htmlFor={selectId}
						className="block text-xs font-semibold text-[#6E524D] tracking-wide"
					>
						{label}
					</label>
				)}
				<select
					ref={ref}
					id={selectId}
					className={clsx(
						'w-full rounded-xl bg-white text-[#231412] text-xs px-3.5 py-2.5 border border-[#C8281E]/20 focus:outline-none focus:ring-2 focus:ring-[#C8281E]/20 focus:border-[#C8281E] shadow-sm transition-all disabled:opacity-50',
						error && 'border-[#C8281E] focus:ring-[#C8281E]/30',
						className
					)}
					{...props}
				>
					{options.map((opt) => (
						<option key={opt.value} value={opt.value} className="bg-white text-[#231412]">
							{opt.label}
						</option>
					))}
				</select>
				{error && <p className="text-[11px] font-medium text-[#C8281E] mt-1">{error}</p>}
				{!error && helperText && (
					<p className="text-[11px] text-[#9A7E78] mt-1">{helperText}</p>
				)}
			</div>
		);
	}
);
Select.displayName = 'Select';
