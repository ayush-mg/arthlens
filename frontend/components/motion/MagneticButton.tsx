'use client';

import React, { useRef, useState, useEffect } from 'react';
import { audioEngine } from '@/lib/audio';

interface MagneticButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  strength?: number; // Distance pull multiplier
  className?: string;
  playAudio?: boolean;
}

export const MagneticButton: React.FC<MagneticButtonProps> = ({
  children,
  strength = 0.28,
  className = '',
  playAudio = true,
  onClick,
  onMouseEnter,
  ...props
}) => {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const media = window.matchMedia('(prefers-reduced-motion: reduce)');
      setPrefersReducedMotion(media.matches);
    }
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (prefersReducedMotion || !buttonRef.current) return;

    const rect = buttonRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const distanceX = (e.clientX - centerX) * strength;
    const distanceY = (e.clientY - centerY) * strength;

    setPosition({ x: distanceX, y: distanceY });
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    setIsHovered(true);
    if (playAudio) audioEngine.playTick();
    if (onMouseEnter) onMouseEnter(e);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setPosition({ x: 0, y: 0 });
  };

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (playAudio) audioEngine.playClick();
    if (onClick) onClick(e);
  };

  return (
    <button
      ref={buttonRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      style={{
        transform: prefersReducedMotion
          ? undefined
          : `translate3d(${position.x}px, ${position.y}px, 0)`,
        transition: isHovered
          ? 'transform 0.12s cubic-bezier(0.25, 1, 0.5, 1)'
          : 'transform 0.4s cubic-bezier(0.25, 1, 0.5, 1)',
      }}
      className={`relative inline-flex items-center justify-center cursor-pointer select-none ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

