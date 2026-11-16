'use client';

import React, { forwardRef, type ComponentProps } from 'react';
import { motion } from 'framer-motion';

export type MotionButtonProps = ComponentProps<typeof motion.button>;

export const MotionButton = forwardRef<HTMLButtonElement, MotionButtonProps>(function MotionButton({
  disabled,
  whileHover,
  whileTap,
  transition,
  ...props
}, ref) {
  return (
    <motion.button
      ref={ref}
      data-motion-control="button"
      disabled={disabled}
      whileHover={disabled ? undefined : whileHover ?? { scale: 1.018, y: -1 }}
      whileTap={disabled ? undefined : whileTap ?? { scale: 0.975, y: 1 }}
      transition={transition ?? { type: 'spring', stiffness: 480, damping: 28, mass: 0.32 }}
      {...props}
    />
  );
});

MotionButton.displayName = 'MotionButton';
