/**
 * ArthLens Design System & Motion Tokens.
 *
 * Authoritative styling and interaction metrics across all views and subsequent phases.
 */

export const THEME_COLORS = {
  forest: '#0d1a15',
  forestDark: '#08100d',
  forestSurface: '#162820',
  ivory: '#fbf8f2',
  paper: '#f3eedf',
  paperLight: '#fdfbf7',
  brass: '#b89758',
  brassLight: '#d4b77d',
  copper: '#c86446',
  copperDark: '#a3482f',
  copperLight: '#de856b',
  charcoal: '#222825',
  charcoalLight: '#596560',
  charcoalMuted: '#8b9691',
  sage: '#889c8d',
  sageLight: '#b0c2b4',
} as const;

export const MOTION_EASINGS = {
  // Iconic Apple/Linear precision ease
  cubicOut: [0.16, 1, 0.3, 1] as const,
  // Mechanical snap
  snappy: [0.25, 0.1, 0.25, 1] as const,
  // Smooth cinematic ease
  cinematic: [0.65, 0, 0.35, 1] as const,
  // Bouncy spring
  springGentle: { type: 'spring', stiffness: 260, damping: 24 } as const,
  springSnappy: { type: 'spring', stiffness: 450, damping: 30 } as const,
  springTight: { type: 'spring', stiffness: 700, damping: 38 } as const,
} as const;

export const Z_INDEX_SCALE = {
  canvas: 0,
  content: 10,
  controls: 20,
  stickyBar: 30,
  drawer: 40,
  modal: 50,
  reticleCursor: 60,
  tooltip: 70,
} as const;

