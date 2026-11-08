'use client';

import React, { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Compass, Eye, EyeOff, Lock, ArrowRight, CheckCircle2, ShieldAlert } from 'lucide-react';
import { confirmPasswordReset } from '../../lib/api';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialToken = searchParams.get('token') || '';

  const [token, setToken] = useState(initialToken);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!token.trim()) {
      setError('Password reset token is required.');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must contain at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(token.trim(), newPassword);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Password reset failed. Token may be expired or already used.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded border border-editorial-brass/40 bg-editorial-paper px-6 py-8 shadow-editorial-md sm:px-10">
      {!success ? (
        <form className="space-y-5" onSubmit={handleSubmit}>
          {!initialToken && (
            <div>
              <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
                Reset Token
              </label>
              <input
                type="text"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste your reset token"
                className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory px-3 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
              New Password
            </label>
            <div className="relative rounded">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-editorial-charcoal-light">
                <Lock className="h-4 w-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory pl-10 pr-10 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-editorial-charcoal-light hover:text-editorial-charcoal cursor-pointer"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
              Confirm New Password
            </label>
            <div className="relative rounded">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-editorial-charcoal-light">
                <Lock className="h-4 w-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory pl-10 pr-3 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
              />
            </div>
          </div>

          {error && (
            <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3 text-xs font-mono text-editorial-copper flex items-start space-x-2">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center space-x-2 rounded border border-editorial-forest bg-editorial-forest py-2.5 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer disabled:opacity-60"
            >
              <span>{loading ? 'Updating Credentials...' : 'Set New Password'}</span>
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
            Password Successfully Updated
          </h3>
          <p className="font-mono text-xs text-editorial-charcoal leading-relaxed">
            Your new password is now active. All previous sessions have been invalidated for security. Please sign in with your new credentials.
          </p>
          <div className="pt-2">
            <Link
              href="/login"
              className="inline-flex items-center space-x-1.5 rounded border border-editorial-forest bg-editorial-forest px-4 py-2 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark"
            >
              <span>Proceed to Sign In</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResetPasswordPage() {
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
          Reset Account Password
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <Suspense fallback={<div className="font-mono text-xs text-center p-6 text-editorial-charcoal-light">Loading recovery details...</div>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}

