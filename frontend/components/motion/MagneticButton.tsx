'use client';
import { MotionButton } from '@/components/ui/motion-button';

import type { ButtonHTMLAttributes, PointerEvent } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { clsx } from 'clsx';

export interface MagneticButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onDrag' | 'onDragStart' | 'onDragEnd' | 'onAnimationStart' | 'onAnimationEnd'> {
  strength?: number;
  index?: string;
}

export function MagneticButton({ children, className, strength = 0.16, index, onPointerMove, onPointerLeave, ...props }: MagneticButtonProps) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 260, damping: 18, mass: 0.3 });
  const springY = useSpring(y, { stiffness: 260, damping: 18, mass: 0.3 });

  const handlePointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX - bounds.left - bounds.width / 2) * strength);
    y.set((event.clientY - bounds.top - bounds.height / 2) * strength);
    onPointerMove?.(event);
  };
  const handlePointerLeave = (event: PointerEvent<HTMLButtonElement>) => {
    x.set(0);
    y.set(0);
    onPointerLeave?.(event);
  };

  return (
    <MotionButton
      {...props}
      className={clsx('magnetic-button', className)}
      style={{ x: springX, y: springY }}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 340, damping: 24 }}
    >
      {index && <span className="magnetic-button-index">[{index}]</span>}
      {children}
    </MotionButton>
  );
}
