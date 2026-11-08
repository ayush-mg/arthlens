'use client';

import React, { useEffect, useState, useRef } from 'react';

export const TactileReticleCursor: React.FC = () => {
  const [pos, setPos] = useState({ x: -100, y: -100 });
  const [isLocked, setIsLocked] = useState(false);
  const [targetLabel, setTargetLabel] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  const reqRef = useRef<number | null>(null);

  // Position smooth interpolation
  const currentPos = useRef({ x: -100, y: -100 });
  const targetPos = useRef({ x: -100, y: -100 });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Detect touch device or reduced motion
    const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (touch || reduced) {
      setIsTouchDevice(true);
      return;
    }

    const handleMouseMove = (e: MouseEvent) => {
      targetPos.current = { x: e.clientX, y: e.clientY };
      if (!isVisible) setIsVisible(true);

      // Check if hovering over an interactive element
      const target = document.elementFromPoint(e.clientX, e.clientY);
      const interactive = target?.closest('button, a, input, select, [data-reticle="lock"]');
      if (interactive) {
        setIsLocked(true);
        const aria = interactive.getAttribute('aria-label') || interactive.getAttribute('title');
        setTargetLabel(aria ? aria.slice(0, 20) : null);
      } else {
        setIsLocked(false);
        setTargetLabel(null);
      }
    };

    const handleMouseLeave = () => {
      setIsVisible(false);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);

    // Smooth lerp loop
    const animate = () => {
      currentPos.current.x += (targetPos.current.x - currentPos.current.x) * 0.22;
      currentPos.current.y += (targetPos.current.y - currentPos.current.y) * 0.22;
      setPos({ x: currentPos.current.x, y: currentPos.current.y });
      reqRef.current = requestAnimationFrame(animate);
    };
    reqRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      if (reqRef.current) cancelAnimationFrame(reqRef.current);
    };
  }, [isVisible]);

  if (isTouchDevice || !isVisible) return null;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-50 overflow-hidden"
    >
      <div
        className="absolute -translate-x-1/2 -translate-y-1/2 transition-transform duration-75"
        style={{
          left: `${pos.x}px`,
          top: `${pos.y}px`,
        }}
      >
        {/* Reticle Crosshair */}
        <div
          className={`relative flex items-center justify-center transition-all duration-200 ${
            isLocked
              ? 'h-9 w-9 rounded border border-editorial-copper bg-editorial-copper/10 scale-110'
              : 'h-6 w-6 rounded-full border border-editorial-brass/60'
          }`}
        >
          {/* Center Point */}
          <div
            className={`h-1 w-1 rounded-full transition-colors ${
              isLocked ? 'bg-editorial-copper scale-150' : 'bg-editorial-forest'
            }`}
          />

          {/* Crosshair ticks */}
          {!isLocked && (
            <>
              <div className="absolute top-0 h-1.5 w-[1px] bg-editorial-brass/70" />
              <div className="absolute bottom-0 h-1.5 w-[1px] bg-editorial-brass/70" />
              <div className="absolute left-0 h-[1px] w-1.5 bg-editorial-brass/70" />
              <div className="absolute right-0 h-[1px] w-1.5 bg-editorial-brass/70" />
            </>
          )}

          {/* Corner marks when locked */}
          {isLocked && (
            <>
              <div className="absolute -top-1 -left-1 h-1.5 w-1.5 border-t border-l border-editorial-copper" />
              <div className="absolute -top-1 -right-1 h-1.5 w-1.5 border-t border-r border-editorial-copper" />
              <div className="absolute -bottom-1 -left-1 h-1.5 w-1.5 border-b border-l border-editorial-copper" />
              <div className="absolute -bottom-1 -right-1 h-1.5 w-1.5 border-b border-r border-editorial-copper" />
            </>
          )}
        </div>

        {/* Tactical Telemetry Badge */}
        <div className="absolute left-6 top-3 flex items-center space-x-1 whitespace-nowrap rounded border border-editorial-brass/30 bg-editorial-forest/90 px-1.5 py-0.5 font-mono text-[9px] text-editorial-ivory shadow-sm backdrop-blur-sm">
          <span className="text-editorial-brass">{isLocked ? 'TARGET_LOCK' : 'COORD'}</span>
          <span>
            {targetLabel
              ? `:: ${targetLabel}`
              : `${Math.round(pos.x)},${Math.round(pos.y)}`}
          </span>
        </div>
      </div>
    </div>
  );
};

