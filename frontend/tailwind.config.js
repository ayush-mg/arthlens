/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        quality: {
          current: '#22C55E',
          incomplete: '#EAB308',
          stale: '#F97316',
          estimated: '#3B82F6',
          unavailable: '#94A3B8',
        },
        surface: {
          ground: '#070A12',
          base: '#0B0F19',
          card: '#111827',
          panel: '#151D30',
          hover: '#1E293B',
          border: 'rgba(255, 255, 255, 0.08)',
          'border-active': 'rgba(56, 189, 248, 0.4)',
        },
        brand: {
          cyan: '#06B6D4',
          sky: '#38BDF8',
          indigo: '#6366F1',
          amber: '#F59E0B',
          emerald: '#10B981',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          '"Fira Code"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        'glow-sky': '0 0 24px -4px rgba(56, 189, 248, 0.25)',
        'glow-indigo': '0 0 24px -4px rgba(99, 102, 241, 0.25)',
        'glow-emerald': '0 0 24px -4px rgba(34, 197, 94, 0.25)',
        'glow-amber': '0 0 24px -4px rgba(245, 158, 11, 0.25)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.25s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
