import React from 'react';
import { clsx } from 'clsx';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'rectangular' | 'circular' | 'rounded';
}

export function Skeleton({ className, variant = 'rounded', ...props }: SkeletonProps) {
  const variantStyles = {
    rectangular: 'rounded-none',
    circular: 'rounded-none',
    rounded: 'rounded-none',
  };

  return (
    <div
      className={clsx(
        'animate-pulse bg-[#C8281E]/[0.06]',
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
