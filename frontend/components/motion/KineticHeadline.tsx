'use client';

import React, { useRef, useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

interface KineticHeadlineProps {
  text: string;
  tagline?: string;
  className?: string;
}

export const KineticHeadline: React.FC<KineticHeadlineProps> = ({
  text,
  tagline,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion || !containerRef.current || !titleRef.current) return;

    const ctx = gsap.context(() => {
      // Split words and animate in
      const words = titleRef.current?.querySelectorAll('.kinetic-word');
      if (words && words.length > 0) {
        gsap.fromTo(
          words,
          {
            yPercent: 120,
            opacity: 0,
            rotateX: -40,
          },
          {
            yPercent: 0,
            opacity: 1,
            rotateX: 0,
            duration: 1.1,
            stagger: 0.08,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: containerRef.current,
              start: 'top 85%',
              toggleActions: 'play none none none',
            },
          }
        );
      }
    }, containerRef);

    return () => ctx.revert();
  }, []);

  const words = text.split(' ');

  return (
    <div ref={containerRef} className={`overflow-hidden select-none ${className}`}>
      {tagline && (
        <div className="flex items-center space-x-2 text-[11px] font-mono uppercase tracking-widest text-brand-sky/80 mb-2">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-sky animate-ping" />
          <span>{tagline}</span>
        </div>
      )}
      <h1
        ref={titleRef}
        className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-black font-display tracking-tight text-white leading-[0.95]"
      >
        {words.map((word, i) => (
          <span key={i} className="inline-block overflow-hidden mr-[0.25em] last:mr-0">
            <span className="kinetic-word inline-block will-change-transform">
              {word}
            </span>
          </span>
        ))}
      </h1>
    </div>
  );
};

