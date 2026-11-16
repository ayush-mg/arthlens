export const arthlensTheme = {
  colors: {
    canvas: '#06080B',
    surface: '#0B0F17',
    elevated: '#111824',
    emerald: '#10B981',
    cyan: '#06B6D4',
    amber: '#F59E0B',
    ink: '#F8FAFC',
    muted: '#94A3B8',
  },
  motion: {
    spring: { type: 'spring' as const, stiffness: 240, damping: 26 },
    reveal: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
  },
};
