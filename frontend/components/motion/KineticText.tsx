'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

interface KineticTextProps {
  text: string;
  className?: string;
  scrambleOnMount?: boolean;
  scrambleOnHover?: boolean;
  speed?: number; // Milliseconds per cycle (default 30)
}

const GLYPHS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ#$@%&*+=~';

export const KineticText: React.FC<KineticTextProps> = ({
  text,
  className = '',
  scrambleOnMount = true,
  scrambleOnHover = true,
  speed = 25,
}) => {
  const [displayText, setDisplayText] = useState(text);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isScramblingRef = useRef(false);

  const triggerScramble = useCallback(() => {
    if (isScramblingRef.current) return;
    isScramblingRef.current = true;

    let iteration = 0;
    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(() => {
      setDisplayText(() =>
        text
          .split('')
          .map((char, index) => {
            if (char === ' ') return ' ';
            if (index < iteration) {
              return text[index];
            }
            return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
          })
          .join('')
      );

      if (iteration >= text.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        isScramblingRef.current = false;
        setDisplayText(text);
      }

      iteration += 1 / 2.5;
    }, speed);
  }, [text, speed]);

  useEffect(() => {
    if (scrambleOnMount) {
      triggerScramble();
    } else {
      setDisplayText(text);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [text, scrambleOnMount, triggerScramble]);

  return (
    <span
      onMouseEnter={() => {
        if (scrambleOnHover) triggerScramble();
      }}
      className={`font-mono select-none transition-colors ${className}`}
    >
      {displayText}
    </span>
  );
};

