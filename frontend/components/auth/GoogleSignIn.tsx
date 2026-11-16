'use client';
import { MotionButton } from '@/components/ui/motion-button';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import Script from 'next/script';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (element: HTMLElement, options: Record<string, string>) => void;
        };
      };
    };
  }
}

export function GoogleSignIn({
  mode,
  onCredential,
  onLocalAccount,
}: {
  mode: 'login' | 'register';
  onCredential: (token: string) => void;
  onLocalAccount: (email: string, fullName: string) => void;
}) {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim();
  const [mounted, setMounted] = useState(false);
  const [isLocalHost, setIsLocalHost] = useState(true);
  useEffect(() => {
    setMounted(true);
    if (typeof window !== 'undefined') {
      setIsLocalHost(window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    }
  }, []);
  const showLiveGoogle = mounted && Boolean(clientId) && !isLocalHost && process.env.NODE_ENV === 'production';
  const [scriptReady, setScriptReady] = useState(false);
  const [chooserOpen, setChooserOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [validationError, setValidationError] = useState('');
  const buttonRef = useCallback((element: HTMLDivElement | null) => {
    if (!element || !clientId || !scriptReady || !window.google) return;
    element.replaceChildren();
    window.google.accounts.id.initialize({ client_id: clientId, callback: ({ credential }) => onCredential(credential) });
    window.google.accounts.id.renderButton(element, {
      type: 'standard', theme: 'filled_black', size: 'large', shape: 'pill',
      text: mode === 'register' ? 'signup_with' : 'signin_with', width: '360',
    });
  }, [clientId, mode, onCredential, scriptReady]);

  const submitLocalAccount = (event: FormEvent) => {
    event.preventDefault();
    if (!email.includes('@') || fullName.trim().length < 2) {
      setValidationError('Enter a valid email and your name to continue.');
      return;
    }
    setValidationError('');
    onLocalAccount(email.trim(), fullName.trim());
    setChooserOpen(false);
  };

  return (
    <>
      {showLiveGoogle ? (
        <>
          <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onLoad={() => setScriptReady(true)} />
          <div ref={buttonRef} className="flex min-h-11 justify-center" aria-label="Continue with Google" />
          {!scriptReady && <div className="text-center text-xs text-slate-400">Loading secure Google sign-in…</div>}
        </>
      ) : (
        <MotionButton
          type="button"
          onClick={() => setChooserOpen(true)}
          className="flex h-12 w-full items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/[0.045] text-sm font-medium text-slate-100 transition hover:border-white/20 hover:bg-white/[0.08] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-300/50"
        >
          <GoogleMark />
          {mode === 'register' ? 'Register with Google' : 'Continue with Google'}
          <span className="ml-1 rounded-full border border-emerald-300/20 px-2 py-0.5 text-[9px] uppercase tracking-wider text-emerald-200">Local</span>
        </MotionButton>
      )}

      <AnimatePresence>
        {chooserOpen && (
          <motion.div
            className="fixed inset-0 z-[100] grid place-items-center bg-[#231412]/30 p-4 backdrop-blur-md"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onMouseDown={(event) => { if (event.target === event.currentTarget) setChooserOpen(false); }}
          >
            <motion.section
              role="dialog" aria-modal="true" aria-labelledby="google-chooser-title"
              className="relative w-full max-w-md rounded-3xl border border-[#C8281E]/20 bg-white p-7 shadow-2xl text-[#231412]"
              initial={{ opacity: 0, y: 16, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12 }}
            >
              <MotionButton type="button" aria-label="Close account chooser" onClick={() => setChooserOpen(false)} className="absolute right-5 top-5 rounded-xl p-2 text-[#6E524D] hover:bg-[#FAF7F2] hover:text-[#231412]"><X className="h-4 w-4" /></MotionButton>
              <div className="mb-6 flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-2xl border border-[#C8281E]/20 bg-[#C8281E]/10"><GoogleMark /></span><div><p className="text-xs font-medium uppercase tracking-[.2em] text-[#C8281E]">ArthLens identity</p><h2 id="google-chooser-title" className="mt-1 text-lg font-bold text-[#231412]">Choose a Google account</h2></div></div>
              <p className="mb-5 text-sm leading-relaxed text-[#6E524D]">Local sign-in simulates the Google account chooser for development. Configure a Google client ID to use Google’s verified identity flow.</p>
              <form className="space-y-4" onSubmit={submitLocalAccount}>
                <label className="block text-xs font-semibold text-[#231412]">Name<input autoComplete="name" required minLength={2} value={fullName} onChange={(event) => setFullName(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] px-3 text-sm text-[#231412] placeholder-[#9A7E78] outline-none focus:border-[#C8281E]" placeholder="Aarav Sharma" /></label>
                <label className="block text-xs font-semibold text-[#231412]">Google account email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] px-3 text-sm text-[#231412] placeholder-[#9A7E78] outline-none focus:border-[#C8281E]" placeholder="you@example.com" /></label>
                {validationError && <p role="alert" className="text-xs text-rose-700">{validationError}</p>}
                <MotionButton className="h-11 w-full rounded-xl bg-[#C8281E] font-semibold text-white transition hover:bg-[#A81E15] shadow-md shadow-[#C8281E]/20">Continue securely</MotionButton>
              </form>
              <p className="mt-4 text-center text-[10px] text-[#9A7E78]">Development account chooser · not a Google authentication assertion</p>
            </motion.section>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function GoogleMark() {
  return <svg aria-hidden="true" viewBox="0 0 48 48" className="h-4 w-4"><path fill="#FFC107" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5.1h6.6c3.9-3.6 6.1-8.9 6.1-15Z"/><path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.9l-6.6-5.1c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.4H5.8v5.3A20 20 0 0 0 24 44Z"/><path fill="#4A90E2" d="M12.6 27.6a12 12 0 0 1 0-7.2v-5.3H5.8a20 20 0 0 0 0 17.8l6.8-5.3Z"/><path fill="#EA4335" d="M24 12c3 0 5.7 1 7.8 3.1l5.8-5.8C34.1 5.9 29.5 4 24 4A20 20 0 0 0 5.8 15.1l6.8 5.3C14.2 15.6 18.7 12 24 12Z"/></svg>;
}
