'use client';
import { MotionButton } from '@/components/ui/motion-button';
import React, { Suspense, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Eye, EyeOff, Lock, ArrowRight, CheckCircle2, ShieldAlert } from 'lucide-react';
import { confirmPasswordReset } from '../../lib/api';
import { ArthLensBrandMark } from '../../components/motion/ArthLensBrandMark';
import { SpotlightCard } from '../../components/motion/SpotlightCard';

function ResetPasswordForm() {
	const searchParams = useSearchParams();
	const initialToken = searchParams?.get('token') || '';

	const [token, setToken] = useState(initialToken);
	const [newPassword, setNewPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [showPassword, setShowPassword] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState(false);

	React.useEffect(() => {
		const paramToken = searchParams?.get('token');
		if (paramToken) {
			setToken(paramToken.trim());
		}
	}, [searchParams]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		const cleanToken = token.trim();
		if (!cleanToken) {
			setError('Password reset token is required. Please paste your token or click the recovery link.');
			return;
		}
		if (newPassword.length < 8) {
			setError('Password must contain at least 8 characters.');
			return;
		}
		if (newPassword.length > 128) {
			setError('Password cannot exceed 128 characters.');
			return;
		}
		if (newPassword !== confirmPassword) {
			setError('Passwords do not match.');
			return;
		}

		setLoading(true);
		try {
			await confirmPasswordReset(cleanToken, newPassword);
			setSuccess(true);
		} catch (err: any) {
			setError(err.message || 'Password reset failed. Token may be expired or already used.');
		} finally {
			setLoading(false);
		}
	};

	return (
		<SpotlightCard className="auth-glass-card rounded-2xl border border-[#C8281E]/18 bg-white/95 p-8 shadow-xl">
			{!success ? (
				<form className="space-y-5" onSubmit={handleSubmit}>
					{!token ? (
						<div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200/80 text-xs text-amber-900 space-y-2">
							<p className="font-bold flex items-center gap-1.5">
								<ShieldAlert className="w-4 h-4 text-amber-700" />
								<span>Recovery Link or Token Required</span>
							</p>
							<p className="text-[11px] leading-relaxed text-amber-800">
								Password resets must be initiated through the secure link dispatched to your email address. If you haven&apos;t requested one yet, please request instructions first.
							</p>
							<div className="pt-1 flex items-center justify-between">
								<Link
									href="/forgot-password"
									className="inline-flex items-center gap-1 font-bold text-[#C8281E] hover:underline"
								>
									<span>Request Recovery Link</span>
									<ArrowRight className="w-3 h-3" />
								</Link>
							</div>
						</div>
					) : (
						<div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200/80 text-xs text-emerald-800 flex items-center justify-between">
							<div className="flex items-center gap-2">
								<CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
								<span className="font-semibold">Valid Recovery Token Attached</span>
							</div>
							<span className="font-mono text-[10px] text-emerald-600 bg-emerald-100/60 px-2 py-0.5 rounded">
								Verified
							</span>
						</div>
					)}

					{!token && (
						<div>
							<label className="block text-xs font-semibold text-[#231412] mb-1">
								Or Paste Recovery Token Manually
							</label>
							<input
								type="text"
								value={token}
								onChange={(e) => setToken(e.target.value)}
								placeholder="Paste your reset token"
								className="w-full rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] px-3.5 py-2 text-xs font-mono text-[#231412] placeholder-[#9A7E78] focus:border-[#C8281E] focus:outline-none"
							/>
						</div>
					)}

					<div>
						<label className="block text-xs font-semibold text-[#231412] mb-1">
							New Password
						</label>
						<div className="relative rounded">
							<div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9A7E78]">
								<Lock className="h-4 w-4" />
							</div>
							<input
								type={showPassword ? 'text' : 'password'}
								required
								minLength={8}
								value={newPassword}
								onChange={(e) => setNewPassword(e.target.value)}
								placeholder="At least 8 characters"
								className="w-full rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] pl-10 pr-10 py-2 text-xs text-[#231412] placeholder-[#9A7E78] focus:border-[#C8281E] focus:outline-none"
							/>
							<MotionButton
								type="button"
								onClick={() => setShowPassword(!showPassword)}
								className="absolute inset-y-0 right-0 pr-3 flex items-center text-[#9A7E78] hover:text-[#231412] cursor-pointer"
							>
								{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
							</MotionButton>
						</div>
					</div>

					<div>
						<label className="block text-xs font-semibold text-[#231412] mb-1">
							Confirm New Password
						</label>
						<div className="relative rounded">
							<div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9A7E78]">
								<Lock className="h-4 w-4" />
							</div>
							<input
								type={showPassword ? 'text' : 'password'}
								required
								minLength={8}
								value={confirmPassword}
								onChange={(e) => setConfirmPassword(e.target.value)}
								placeholder="Re-enter new password"
								className="w-full rounded-xl border border-[#C8281E]/20 bg-[#FAF7F2] pl-10 pr-3 py-2 text-xs text-[#231412] placeholder-[#9A7E78] focus:border-[#C8281E] focus:outline-none"
							/>
						</div>
					</div>

					{error && (
						<div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 flex items-start space-x-2">
							<ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
							<span>{error}</span>
						</div>
					)}

					<div>
						<MotionButton
							type="submit"
							disabled={loading}
							className="w-full flex items-center justify-center space-x-2 rounded-xl bg-[#C8281E] py-2.5 text-xs font-bold text-white hover:bg-[#A81E15] transition-colors cursor-pointer disabled:opacity-60 shadow-md shadow-[#C8281E]/20"
						>
							<span>{loading ? 'Updating Credentials...' : 'Set New Password'}</span>
							{!loading && <ArrowRight className="h-3.5 w-3.5" />}
						</MotionButton>
					</div>
				</form>
			) : (
				<div className="space-y-4 text-center">
					<div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#2D7D52]/10 text-[#2D7D52]">
						<CheckCircle2 className="h-6 w-6" />
					</div>
					<h3 className="font-bold text-base text-[#231412]">
						Password Successfully Updated
					</h3>
					<p className="text-xs text-[#6E524D] leading-relaxed">
						Your new password is now active. All previous sessions have been invalidated for security. Please sign in with your new credentials.
					</p>
					<div className="pt-2">
						<Link
							href="/login"
							className="inline-flex items-center space-x-1.5 rounded-xl bg-[#C8281E] px-4 py-2 text-xs font-bold text-white hover:bg-[#A81E15] shadow-md shadow-[#C8281E]/20"
						>
							<span>Proceed to Sign In</span>
							<ArrowRight className="h-3.5 w-3.5" />
						</Link>
					</div>
				</div>
			)}
		</SpotlightCard>
	);
}

export default function ResetPasswordPage() {
	return (
		<div className="auth-scene min-h-screen bg-[#FAF7F2] text-[#231412] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
			<div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
				<Link href="/" className="mb-3 inline-flex justify-center">
					<ArthLensBrandMark />
				</Link>
				<p className="font-mono text-xs text-[#9A7E78] uppercase tracking-wider">
					Sovereign Economic Operating System
				</p>
				<h2 className="mt-2 text-2xl font-bold text-[#231412]">
					Reset Account Password
				</h2>
			</div>

			<div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
				<Suspense fallback={<div className="font-mono text-xs text-center p-6 text-[#9A7E78]">Loading recovery details...</div>}>
					<ResetPasswordForm />
				</Suspense>
			</div>
		</div>
	);
}