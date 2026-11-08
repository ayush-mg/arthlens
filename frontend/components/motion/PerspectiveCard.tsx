'use client';

import React, { useRef, useState, useEffect } from 'react';

interface PerspectiveCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number; // max tilt in degrees
  spotlightColor?: string;
}

export const PerspectiveCard: React.FC<PerspectiveCardProps> = ({
  children,
  className = '',
  maxTilt = 6,
  spotlightColor = 'rgba(184, 151, 88, 0.15)', // Antique brass specular reflection
  ...props
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotate, setRotate] = useState({ x: 0, y: 0 });
  const [spotlight, setSpotlight] = useState({ x: 50, y: 50, opacity: 0 });
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const media = window.matchMedia('(prefers-reduced-motion: reduce)');
      setPrefersReducedMotion(media.matches);
    }
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion || !cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    // Calculate rotation: moving right tilts around Y (positive), moving down tilts around X (negative)
    const rotX = -((y - rect.height / 2) / (rect.height / 2)) * maxTilt;
    const rotY = ((x - rect.width / 2) / (rect.width / 2)) * maxTilt;

    setRotate({ x: rotX, y: rotY });
    setSpotlight({ x: percentX, y: percentY, opacity: 1 });
  };

  const handleMouseLeave = () => {
    setRotate({ x: 0, y: 0 });
    setSpotlight((prev) => ({ ...prev, opacity: 0 }));
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: prefersReducedMotion
          ? undefined
          : `perspective(1000px) rotateX(${rotate.x}deg) rotateY(${rotate.y}deg)`,
        transition: rotate.x === 0 && rotate.y === 0
          ? 'transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1)'
          : 'transform 0.1s cubic-bezier(0.2, 0.8, 0.2, 1)',
      }}
      className={`relative rounded-xl border border-surface-border bg-surface-card overflow-hidden transition-shadow duration-300 hover:shadow-telemetry-panel ${className}`}
      {...props}
    >
      {/* Subtle radial proximity spotlight */}
      {!prefersReducedMotion && (
        <div
          className="pointer-events-none absolute -inset-px rounded-xl transition-opacity duration-300 z-10"
          style={{
            opacity: spotlight.opacity,
            background: `radial-gradient(circle 320px at ${spotlight.x}% ${spotlight.y}%, ${spotlightColor}, transparent 70%)`,
          }}
        />
      )}
      <div className="relative z-20 h-full">{children}</div>
    </div>
  );
};

