'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, ArrowUpRight, Boxes, GitBranch, Receipt } from 'lucide-react';
import { NumberTicker } from './NumberTicker';
import { SpotlightCard } from './SpotlightCard';

const stages = [
  { id: 0, number: '01', name: 'INGESTION', detail: 'Source records captured and tenant-scoped.', value: 128, suffix: ' records', icon: Receipt },
  { id: 1, number: '02', name: 'LEDGER POSTING', detail: 'Balanced entries linked to each transaction.', value: 42, suffix: ' entries', icon: Activity },
  { id: 2, number: '03', name: 'FIFO RECONCILIATION', detail: 'Inventory costs follow lots, returns, and sales.', value: 96, suffix: '% traced', icon: Boxes },
  { id: 3, number: '04', name: 'DECISION GRAPH', detail: 'Models and outcomes stay reproducible.', value: 6, suffix: ' versions', icon: GitBranch },
];

export interface MorphoEvolutionBannerProps {
  activeStage?: number;
  className?: string;
}

export function MorphoEvolutionBanner({ activeStage = 0, className = '' }: MorphoEvolutionBannerProps) {
  const [selectedStage, setSelectedStage] = useState(activeStage);
  useEffect(() => setSelectedStage(activeStage), [activeStage]);
  const selected = stages[Math.max(0, Math.min(stages.length - 1, selectedStage))];

  return (
    <SpotlightCard className={`morpho-evolution-banner ${className}`}>
      <div className="morpho-banner-head"><div><span>BUSINESS EVOLUTION</span><strong>Source to decision</strong></div><span className="morpho-banner-live"><i /> RECORD FLOW</span></div>
      <div className="morpho-stage-strip" role="tablist" aria-label="Evolution stages">
        <svg className="morpho-stage-connector" viewBox="0 0 1000 20" preserveAspectRatio="none" aria-hidden="true"><motion.path d="M0 10H1000" initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: .9, ease: 'easeOut' }} /></svg>
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return <MotionButton key={stage.id} type="button" role="tab" aria-selected={selectedStage === stage.id} onClick={() => setSelectedStage(stage.id)} className={selectedStage === stage.id ? 'is-selected' : ''} whileTap={{ scale: .97 }}>
            {selectedStage === stage.id && <motion.i layoutId="morpho-stage-active" transition={{ type: 'spring', stiffness: 460, damping: 34 }} />}
            <span className="morpho-stage-node"><Icon size={13} /></span><span className="morpho-stage-label"><small>{stage.number}</small><b>{stage.name}</b></span>
            {index < stages.length - 1 && <span className="morpho-stage-arrow"><ArrowUpRight size={11} /></span>}
          </MotionButton>;
        })}
      </div>
      <motion.div className="morpho-stage-inspection" key={selected.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .2 }}>
        <span><small>{selected.name}</small><b>{selected.detail}</b></span>
        <strong><NumberTicker value={selected.value} suffix={selected.suffix} /></strong>
      </motion.div>
    </SpotlightCard>
  );
}
