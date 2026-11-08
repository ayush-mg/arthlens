'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Compass, Mail, ArrowRight, CheckCircle2, ArrowLeft, Terminal } from 'lucide-react';
import { requestPasswordReset } from '../../lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [devRecoveryUrl, setDevRecoveryUrl] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await requestPasswordReset(email.trim());
      setSubmitted(true);
      if (res && (res as any).dev_recovery_url) {
        setDevRecoveryUrl((res as any).dev_recovery_url);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to submit password recovery request.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-editorial-ivory flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link href="/" className="flex items-center justify-center space-x-2.5 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded border border-editorial-forest bg-editorial-forest/10 text-editorial-forest shadow-editorial-sm">
            <Compass className="h-5 w-5" />
          </div>
          <span className="font-serif font-black tracking-widest text-editorial-forest text-2xl uppercase">
            ArthLens
          </span>
        </Link>
        <p className="text-center font-mono text-xs text-editorial-charcoal-light uppercase tracking-wider">
          Epistemic Economic Intelligence
        </p>
        <h2 className="mt-4 text-center text-xl font-serif font-bold text-editorial-charcoal">
          Recover Your Password
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded border border-editorial-brass/40 bg-editorial-paper px-6 py-8 shadow-editorial-md sm:px-10">
          {!submitted ? (
            <form className="space-y-5" onSubmit={handleSubmit}>
              <p className="font-mono text-xs text-editorial-charcoal leading-relaxed">
                Enter your account email address below. If an active account matches, we will issue an expiring single-use recovery link.
              </p>

              <div>
                <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
                  Email Address
                </label>
                <div className="relative rounded">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-editorial-charcoal-light">
                    <Mail className="h-4 w-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@organization.in"
                    className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory pl-10 pr-3 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
                  />
                </div>
              </div>

              {error && (
                <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3 text-xs font-mono text-editorial-copper">
                  {error}
                </div>
              )}

              <div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center space-x-2 rounded border border-editorial-forest bg-editorial-forest py-2.5 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer disabled:opacity-60"
                >
                  <span>{loading ? 'Submitting...' : 'Send Recovery Instructions'}</span>
                  {!loading && <ArrowRight className="h-3.5 w-3.5" />}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-editorial-forest/10 text-editorial-forest">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h3 className="font-serif font-bold text-base text-editorial-charcoal">
                Instructions Dispatched
              </h3>
              <p className="font-mono text-xs text-editorial-charcoal leading-relaxed">
                If an account exists for <span className="font-bold text-editorial-forest">{email}</span>, password reset instructions have been dispatched. The single-use link is valid for 15 minutes.
              </p>

              {devRecoveryUrl && (
                <div className="mt-4 rounded border border-editorial-brass/40 bg-editorial-ivory p-3.5 text-left space-y-2">
                  <div className="flex items-center space-x-1.5 text-[11px] font-mono font-bold text-editorial-copper uppercase tracking-wider">
                    <Terminal className="h-3.5 w-3.5" />
                    <span>Local Development Recovery Link</span>
                  </div>
                  <p className="text-[11px] font-mono text-editorial-charcoal-light break-all">
                    {devRecoveryUrl}
                  </p>
                  <Link
                    href={devRecoveryUrl.replace('http://localhost:3000', '')}
                    className="inline-flex items-center space-x-1.5 font-mono text-xs font-bold text-editorial-forest hover:underline"
                  >
                    <span>Proceed with reset now</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              )}
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-editorial-brass/20 text-center">
            <Link
              href="/login"
              className="inline-flex items-center space-x-1.5 font-mono text-xs font-bold text-editorial-charcoal hover:text-editorial-forest"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Return to Sign In</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

