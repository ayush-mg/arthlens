'use client';
import React, { forwardRef } from 'react';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
export const Table = forwardRef<HTMLTableElement, React.TableHTMLAttributes<HTMLTableElement>>(
	({ className, children, ...props }, ref) => (
		<div className="w-full overflow-x-auto rounded-2xl border border-[#C8281E]/[0.18] bg-white/95 backdrop-blur-xl shadow-[0_16px_45px_rgba(200,40,30,0.06)]">
			<table
				ref={ref}
				className={clsx('w-full text-left text-xs text-[#231412]', className)}
				{...props}
			>
				{children}
			</table>
		</div>
	)
);
Table.displayName = 'Table';
export const TableHeader = forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
	({ className, children, ...props }, ref) => (
		<thead
			ref={ref}
			className={clsx('bg-[#C8281E]/[0.04] border-b border-[#C8281E]/[0.14] text-[10px] uppercase font-mono tracking-wider font-semibold text-[#6E524D]', className)}
			{...props}
		>
			{children}
		</thead>
	)
);
TableHeader.displayName = 'TableHeader';
export const TableBody = forwardRef<HTMLTableSectionElement, React.ComponentPropsWithoutRef<typeof motion.tbody>>(
	({ className, children, ...props }, ref) => (
		<motion.tbody
			ref={ref}
			className={clsx('divide-y divide-[#C8281E]/[0.08]', className)}
			variants={{ hidden: { opacity: 1 }, visible: { opacity: 1, transition: { staggerChildren: 0.04, delayChildren: 0.02 } } }}
			initial="hidden"
			animate="visible"
			{...props}
		>
			{children}
		</motion.tbody>
	)
);
TableBody.displayName = 'TableBody';
export const TableRow = forwardRef<HTMLTableRowElement, React.ComponentPropsWithoutRef<typeof motion.tr>>(
	({ className, children, ...props }, ref) => (
		<motion.tr
			ref={ref}
			className={clsx('table-motion-row transition-colors hover:bg-[#C8281E]/[0.035]', className)}
			variants={{ hidden: { opacity: 0, y: 8 }, visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 360, damping: 30 } } }}
			whileHover={{ backgroundColor: 'rgba(200,40,30,0.035)' }}
			{...props}
		>
			{children}
		</motion.tr>
	)
);
TableRow.displayName = 'TableRow';
export const TableHead = forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
	({ className, children, ...props }, ref) => (
		<th
			ref={ref}
			className={clsx('px-6 py-3.5 font-semibold tracking-wider font-mono text-[10px]', className)}
			{...props}
		>
			{children}
		</th>
	)
);
TableHead.displayName = 'TableHead';
export const TableCell = forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
	({ className, children, ...props }, ref) => (
		<td
			ref={ref}
			className={clsx('px-6 py-4 align-middle font-medium', className)}
			{...props}
		>
			{children}
		</td>
	)
);
TableCell.displayName = 'TableCell';
