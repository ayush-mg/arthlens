'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';

const CIPHER = '0123456789ABCDEF/#*+';

export interface ScrambleTextProps {
  text: string;
  className?: string;
  duration?: number;
  characters?: string;
}

export function ScrambleText({ text, className, duration = 520, characters = CIPHER }: ScrambleTextProps) {
  const [display, setDisplay] = useState(text);
  const timer = useRef<number | null>(null);
  const scramble = useCallback(() => {
    if (timer.current !== null) window.clearInterval(timer.current);
    let step = 0;
    const steps = Math.max(text.length, 8);
    const tick = Math.max(18, duration / steps);
    timer.current = window.setInterval(() => {
      step += 1;
      setDisplay(text.split('').map((character, index) => {
        if (character === ' ' || index < step) return character;
        return characters[Math.floor(Math.random() * characters.length)];
      }).join(''));
      if (step >= text.length) {
        if (timer.current !== null) window.clearInterval(timer.current);
        timer.current = null;
        setDisplay(text);
      }
    }, tick);
  }, [characters, duration, text]);

  useEffect(() => () => { if (timer.current !== null) window.clearInterval(timer.current); }, []);

  return (
    <motion.span className={clsx('scramble-text', className)} onViewportEnter={scramble} onHoverStart={scramble}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">{display}</span>
    </motion.span>
  );
}
