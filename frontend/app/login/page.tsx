'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Compass, Eye, EyeOff, Lock, Mail, ArrowRight, ShieldCheck, Key } from 'lucide-react';
import { loginUser } from '../../lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginUser(email.trim(), password);
      router.push('/app');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = (roleEmail: string, rolePwd: string) => {
    setEmail(roleEmail);
    setPassword(rolePwd);
    setError(null);
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
          Sign In to Your Workspace
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded border border-editorial-brass/40 bg-editorial-paper px-6 py-8 shadow-editorial-md sm:px-10">
          <form className="space-y-5" onSubmit={handleLogin}>
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

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-mono font-semibold text-editorial-charcoal">
                  Password
                </label>
                <Link
                  href="/forgot-password"
                  className="text-[11px] font-mono text-editorial-copper hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative rounded">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-editorial-charcoal-light">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
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
                <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
                {!loading && <ArrowRight className="h-3.5 w-3.5" />}
              </button>
            </div>
          </form>

          {/* Quick Demo Credentials in Dev Mode Only (Never exposed in production) */}
          {process.env.NODE_ENV !== 'production' && (
            <div className="mt-6 pt-5 border-t border-editorial-brass/20">
              <p className="text-[11px] font-mono font-bold text-editorial-charcoal-light uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                <Key className="h-3.5 w-3.5 text-editorial-brass" />
                <span>Development Demo Credentials</span>
              </p>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleDemoFill('demo.entrepreneur@arthlens.local', 'Entrepreneur123!')}
                  className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2 text-left font-mono text-[10px] hover:border-editorial-copper transition-colors cursor-pointer"
                >
                  <div className="font-bold text-editorial-charcoal">Entrepreneur</div>
                  <div className="text-editorial-charcoal-light text-[9px] truncate">demo.entrepreneur@</div>
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoFill('demo.steward@arthlens.local', 'Steward123!')}
                  className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2 text-left font-mono text-[10px] hover:border-editorial-copper transition-colors cursor-pointer"
                >
                  <div className="font-bold text-editorial-charcoal">Steward</div>
                  <div className="text-editorial-charcoal-light text-[9px] truncate">demo.steward@</div>
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoFill('demo.admin@arthlens.local', 'Administrator123!')}
                  className="rounded border border-editorial-brass/30 bg-editorial-ivory p-2 text-left font-mono text-[10px] hover:border-editorial-copper transition-colors cursor-pointer"
                >
                  <div className="font-bold text-editorial-charcoal">Admin</div>
                  <div className="text-editorial-charcoal-light text-[9px] truncate">demo.admin@</div>
                </button>
              </div>
            </div>
          )}

          <div className="mt-6 text-center">
            <p className="text-xs font-mono text-editorial-charcoal-light">
              Do not have an account?{' '}
              <Link href="/register" className="font-bold text-editorial-forest hover:underline">
                Create entrepreneur account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

