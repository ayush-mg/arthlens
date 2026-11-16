'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring } from 'framer-motion';
import { Activity, Crosshair, Database, Radio } from 'lucide-react';

const pulses = [
  { label: 'PACKET_SYNC', value: 'OK', tone: 'gold' },
  { label: 'LEDGER_NODE', value: 'LIVE', tone: 'cobalt' },
  { label: 'COST_TRACE', value: 'CLEAR', tone: 'positive' },
  { label: 'SIGNAL_PATH', value: 'STABLE', tone: 'gold' },
];

export function FloatingTelemetryPods() {
  const boundary = useRef<HTMLDivElement>(null);
  const [pulse, setPulse] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [reticleVisible, setReticleVisible] = useState(false);
  const reduceMotion = useReducedMotion();
  const pointerX = useMotionValue(-60);
  const pointerY = useMotionValue(-60);
  const reticleX = useSpring(pointerX, { stiffness: 180, damping: 24, mass: 0.4 });
  const reticleY = useSpring(pointerY, { stiffness: 180, damping: 24, mass: 0.4 });

  useEffect(() => {
    const timer = window.setInterval(() => setPulse((current) => (current + 1 + Math.floor(Math.random() * 2)) % pulses.length), 1900);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const move = (event: PointerEvent) => {
      if (event.pointerType === 'touch' || window.innerWidth < 900) return;
      pointerX.set(event.clientX);
      pointerY.set(event.clientY);
      setReticleVisible(true);
    };
    const leave = () => setReticleVisible(false);
    window.addEventListener('pointermove', move, { passive: true });
    window.addEventListener('pointerleave', leave, { passive: true });
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerleave', leave);
    };
  }, [pointerX, pointerY]);

  const current = pulses[pulse];
  return (
    <div ref={boundary} className="telemetry-pods" aria-label="Live system telemetry">
      <AnimatePresence>{reticleVisible && !reduceMotion && <motion.div className="telemetry-reticle" aria-hidden="true" style={{ x: reticleX, y: reticleY }} initial={{ opacity: 0, scale: .65 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}><i /><b /></motion.div>}</AnimatePresence>
      <motion.aside layout className="telemetry-pod telemetry-pod-coordinates" drag dragConstraints={boundary} dragElastic={0.25} dragMomentum={false} whileDrag={{ scale: 1.025, cursor: 'grabbing' }}>
        <div className="telemetry-pod-heading"><Crosshair size={13} /><span>FIELD COORDINATES</span><i className="telemetry-live-indicator" /></div>
        <strong>LAT <span>{'//'}</span> 25.4358° N</strong>
        <strong>LON <span>{'//'}</span> 81.8463° E</strong>
        <small>NODE / PRY-04</small>
        <motion.i className="telemetry-radar" animate={{ rotate: 360 }} transition={{ duration: 7, repeat: Infinity, ease: 'linear' }} />
      </motion.aside>
      <motion.aside layout className={'telemetry-pod telemetry-pod-status ' + (expanded ? 'telemetry-pod-expanded' : '')} drag dragConstraints={boundary} dragElastic={0.25} dragMomentum={false} whileDrag={{ scale: 1.025, cursor: 'grabbing' }}>
        <div className="telemetry-pod-heading"><Radio size={13} /><span>VIRTUAL NET / 01</span><MotionButton type="button" className="telemetry-expand" aria-label={expanded ? 'Collapse node telemetry' : 'Expand node telemetry'} aria-expanded={expanded} onClick={() => setExpanded((value) => !value)}>{expanded ? '−' : '+'}</MotionButton></div>
        <div className="telemetry-pod-readout"><Activity size={15} /><span>{current.label}</span><motion.strong key={current.value} className={`tone-${current.tone}`} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>{current.value}</motion.strong></div>
        <div className="telemetry-memory"><Database size={13} /><span>MEM // 99.98%</span><i><b /></i></div>
        <div className="telemetry-pulse-bars" aria-hidden="true">{Array.from({ length: 12 }, (_, index) => <motion.i key={index} animate={{ scaleY: [0.25, 0.45 + ((index + pulse) % 5) / 7, 0.25] }} transition={{ duration: 0.8 + index * 0.06, repeat: Infinity, delay: index * 0.035 }} />)}</div>
        <AnimatePresence initial={false}>{expanded && <motion.div className="telemetry-expanded-readout" layout initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}><span>NODE_ID <b>PRY-04-018</b></span><span>LATENCY <b>08.4 MS</b></span><span>TRACE <b>VERIFIED</b></span></motion.div>}</AnimatePresence>
      </motion.aside>
    </div>
  );
}
