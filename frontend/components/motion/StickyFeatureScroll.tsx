'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { useEffect, useId, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowDownRight, Check } from 'lucide-react';
import { ScrambleText } from './ScrambleText';

gsap.registerPlugin(ScrollTrigger);

export interface StickyFeature {
  eyebrow: string;
  title: string;
  text: string;
  metric: string;
  icon: LucideIcon;
}

export function StickyFeatureScroll({ features }: { features: StickyFeature[] }) {
  const sectionRef = useRef<HTMLElement>(null);
  const cardRefs = useRef<Array<HTMLElement | null>>([]);
  const [active, setActive] = useState(0);
  const id = useId().replace(/:/g, '');
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const section = sectionRef.current;
    const cards = cardRefs.current.filter((card): card is HTMLElement => card !== null);
    if (!section || reduceMotion || cards.length < 2) return;

    const context = gsap.context(() => {
      cards.forEach((card, index) => {
        const next = cards[index + 1];
        ScrollTrigger.create({
          id: `deck-active-${id}-${index}`,
          trigger: card,
          start: 'top 60%',
          end: 'bottom 40%',
          onEnter: () => setActive(index),
          onEnterBack: () => setActive(index),
        });
        if (!next) return;
        gsap.to(card, {
          scale: 0.91,
          rotateX: 6,
          yPercent: -5,
          opacity: 0.4,
          transformOrigin: 'center top',
          ease: 'none',
          scrollTrigger: {
            id: `deck-depth-${id}-${index}`,
            trigger: next,
            start: 'top 88%',
            end: 'top 18%',
            scrub: 0.8,
          },
        });
      });
    }, section);
    return () => context.revert();
  }, [features.length, id, reduceMotion]);

  const selectFeature = (index: number) => {
    setActive(index);
    cardRefs.current[index]?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  };

  return (
    <section ref={sectionRef} className="sticky-feature-section" aria-label="Platform pillars">
      <div className="sticky-feature-heading">
        <span className="section-kicker"><ScrambleText text="FROM RECORDS TO BETTER DECISIONS" /></span>
        <h2>One ledger.<br /><i>Four ways forward.</i></h2>
        <p>Each operating layer stays connected to the same evidence.</p>
      </div>
      <div className="sticky-feature-tabs" role="tablist" aria-label="Platform pillars">
        {features.map((item, index) => <MotionButton key={item.eyebrow} type="button" role="tab" aria-selected={active === index} onClick={() => selectFeature(index)} className={active === index ? 'is-active' : ''}>
          <span>{item.eyebrow}</span><i><b style={{ transform: `scaleX(${active === index ? 1 : 0})` }} /></i>
        </MotionButton>)}
      </div>
      <div className="sticky-deck" style={{ perspective: '1400px' }}>
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return <motion.article
            ref={(node) => { cardRefs.current[index] = node; }}
            key={feature.eyebrow}
            className="sticky-deck-card"
            style={{ zIndex: index + 1, top: `calc(96px + ${index * 12}px)`, transformStyle: 'preserve-3d' }}
            initial={reduceMotion ? false : { opacity: 0, y: 30, rotateX: -2 }}
            whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.6, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="sticky-deck-card-meta"><span>{feature.eyebrow}</span><span>{String(index + 1).padStart(2, '0')} <i>/ {String(features.length).padStart(2, '0')}</i></span></div>
            <div className="sticky-deck-card-body">
              <span className="sticky-feature-orbit"><Icon size={35} strokeWidth={1.2} /></span>
              <div><h3><ScrambleText text={feature.title} /></h3><p>{feature.text}</p><div className="sticky-feature-metric"><Check size={14} />{feature.metric}</div></div>
              <ArrowDownRight className="sticky-deck-arrow" size={24} />
            </div>
          </motion.article>;
        })}
      </div>
    </section>
  );
}
