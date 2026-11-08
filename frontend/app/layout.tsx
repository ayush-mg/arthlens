import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ArthLens — Interactive Economic Atlas & Epistemic Ledger',
  description:
    'Evidence-gated geospatial economic intelligence and verifiable provenance for Indian micro-enterprises.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface-ground text-slate-100 antialiased selection:bg-brand-sky selection:text-slate-950 overflow-x-hidden">
        {children}
      </body>
    </html>
  );
}
