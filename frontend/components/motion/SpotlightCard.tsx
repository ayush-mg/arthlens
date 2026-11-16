'use client';
import { useEffect, useRef } from 'react';
import type { CSSProperties, HTMLAttributes, PointerEvent } from 'react';
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'framer-motion';
import { clsx } from 'clsx';
export interface SpotlightCardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart' | 'onAnimationEnd'> {
	spotlightColor?: string;
	delay?: number;
}
export function SpotlightCard({ children, className, spotlightColor = 'rgba(200,40,30,.12)', delay = 0, onPointerMove, onPointerLeave, ...props }: SpotlightCardProps) {
	const cardRef = useRef<HTMLDivElement>(null);
	const tiltX = useMotionValue(0);
	const tiltY = useMotionValue(0);
	const springX = useSpring(tiltX, { stiffness: 220, damping: 24, mass: 0.42 });
	const springY = useSpring(tiltY, { stiffness: 220, damping: 24, mass: 0.42 });
	const rotateX = useTransform(springY, [-0.5, 0.5], [8, -8]);
	const rotateY = useTransform(springX, [-0.5, 0.5], [-9, 9]);
	const reduceMotion = useReducedMotion();
	useEffect(() => {
		if (cardRef.current) cardRef.current.style.setProperty('--scan-delay', `${Math.random() * -5}s`);
	}, []);
	const moveSpotlight = (event: PointerEvent<HTMLDivElement>) => {
		const bounds = event.currentTarget.getBoundingClientRect();
		const localX = event.clientX - bounds.left;
		const localY = event.clientY - bounds.top;
		event.currentTarget.style.setProperty('--spot-x', `${localX}px`);
		event.currentTarget.style.setProperty('--spot-y', `${localY}px`);
		if (!reduceMotion && event.pointerType !== 'touch') {
			tiltX.set(localY / Math.max(bounds.height, 1) - 0.5);
			tiltY.set(localX / Math.max(bounds.width, 1) - 0.5);
		}
		onPointerMove?.(event);
	};
	const resetTilt = (event: PointerEvent<HTMLDivElement>) => {
		tiltX.set(0);
		tiltY.set(0);
		onPointerLeave?.(event);
	};
	return (
		<motion.div
			ref={cardRef}
			className={clsx('spotlight-card', className)}
			style={{ '--spotlight-color': spotlightColor, '--spotlight-amber': 'rgba(230,72,51,.08)', rotateX, rotateY, transformPerspective: 1200, transformStyle: 'preserve-3d' } as CSSProperties}
			onPointerMove={moveSpotlight}
			onPointerLeave={resetTilt}
			initial={{ opacity: 0, y: 20 }}
			whileInView={{ opacity: 1, y: 0 }}
			viewport={{ once: true, amount: 0.16 }}
			transition={{ duration: 0.62, delay, ease: [0.22, 1, 0.36, 1] }}
			{...props}
		>
			<span className="spotlight-card-glow" aria-hidden="true" />
			<div className="spotlight-card-content">{children}</div>
		</motion.div>
	);
}
export default SpotlightCard;
