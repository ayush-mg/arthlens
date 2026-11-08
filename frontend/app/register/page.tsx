'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Compass, Eye, EyeOff, Lock, Mail, User, ArrowRight, CheckCircle2 } from 'lucide-react';
import { registerUser } from '../../lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await registerUser(fullName.trim(), email.trim(), password);
      router.push('/app');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
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
          Create Entrepreneur Account
        </h2>
        <p className="mt-1 text-center font-mono text-xs text-editorial-charcoal-light">
          Public registration automatically grants Entrepreneur privileges.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="rounded border border-editorial-brass/40 bg-editorial-paper px-6 py-8 shadow-editorial-md sm:px-10">
          <form className="space-y-4" onSubmit={handleRegister}>
            <div>
              <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
                Full Name
              </label>
              <div className="relative rounded">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-editorial-charcoal-light">
                  <User className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Aarav Sharma"
                  className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory pl-10 pr-3 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
                />
              </div>
            </div>

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
                  placeholder="name@business.in"
                  className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory pl-10 pr-3 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
                Password (minimum 8 characters)
              </label>
              <div className="relative rounded">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-editorial-charcoal-light">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
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

            <div>
              <label className="block text-xs font-mono font-semibold text-editorial-charcoal mb-1">
                Confirm Password
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
                  placeholder="••••••••••••"
                  className="w-full rounded border border-editorial-brass/40 bg-editorial-ivory pl-10 pr-3 py-2 font-mono text-xs text-editorial-charcoal placeholder-editorial-charcoal-light/60 focus:border-editorial-copper focus:outline-none"
                />
              </div>
            </div>

            {error && (
              <div className="rounded border border-editorial-copper/40 bg-editorial-copper/10 p-3 text-xs font-mono text-editorial-copper">
                {error}
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center space-x-2 rounded border border-editorial-forest bg-editorial-forest py-2.5 font-mono text-xs font-bold text-editorial-ivory hover:bg-editorial-forest-dark transition-colors cursor-pointer disabled:opacity-60"
              >
                <span>{loading ? 'Creating Account...' : 'Register & Start Workspace'}</span>
                {!loading && <ArrowRight className="h-3.5 w-3.5" />}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center border-t border-editorial-brass/20 pt-4">
            <p className="text-xs font-mono text-editorial-charcoal-light">
              Already have an account?{' '}
              <Link href="/login" className="font-bold text-editorial-forest hover:underline">
                Sign in here
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

