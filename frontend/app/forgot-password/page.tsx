'use client';
import {MotionButton} from '@/components/ui/motion-button';
import React,{useState} from 'react';
import Link from 'next/link';
import {AnimatePresence,motion} from 'framer-motion';
import {Mail,ArrowRight,CheckCircle2,ArrowLeft,ShieldCheck} from 'lucide-react';
import {requestPasswordReset} from '../../lib/api';
import {ArthLensBrandMark} from '../../components/motion/ArthLensBrandMark';

export default function ForgotPasswordPage(){
	const [email,setEmail]=useState('');
	const [loading,setLoading]=useState(false);
	const [error,setError]=useState<string|null>(null);
	const [submitted,setSubmitted]=useState(false);
	const [devUrl,setDevUrl]=useState<string|null>(null);

	const handleSubmit=async(event:React.FormEvent)=>{
		event.preventDefault();
		setError(null);
		setLoading(true);
		try{
			const res=await requestPasswordReset(email.trim());
			if(res.dev_reset_url){
				setDevUrl(res.dev_reset_url);
			}else if(res.dev_recovery_token){
				setDevUrl(`/reset-password?token=${res.dev_recovery_token}`);
			}
			setSubmitted(true);
		}catch(err:unknown){
			setError(err instanceof Error?err.message:'Failed to submit password recovery request.');
		}finally{
			setLoading(false);
		}
	};

	return(
		<main className="relative min-h-screen flex items-center justify-center p-4 md:p-8 bg-transparent text-[#231412] select-none">
			<div className="max-w-xl mx-auto w-full px-4 py-12 relative z-10">
				<div className="text-center mb-8">
					<Link href="/" className="inline-block mb-3">
						<ArthLensBrandMark />
					</Link>
					<p className="font-mono text-xs text-[#7A5A54] uppercase tracking-wider">
						SOVEREIGN TOPOLOGY // PASSWORD RECOVERY
					</p>
					<h1 className="mt-2 text-3xl font-black text-[#231412] tracking-tight">
						Recover Your Access
					</h1>
				</div>

				<div className="bg-white/95 border border-[#C8281E]/20 rounded-3xl p-8 sm:p-10 shadow-2xl">
					<AnimatePresence mode="wait">
						{!submitted?(
							<form className="space-y-5" onSubmit={handleSubmit}>
								<p className="text-xs text-[#6E524D] leading-relaxed">
									Enter your account email address below. If an active account matches, we will issue an expiring single-use recovery link.
								</p>

								<div>
									<label htmlFor="recovery-email" className="block text-xs font-bold text-[#7A5A54] uppercase tracking-wider mb-1.5">
										Email Address
									</label>
									<div className="relative">
										<Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7A5A54]" />
										<input
											id="recovery-email"
											type="email"
											required
											value={email}
											onChange={(event)=>setEmail(event.target.value)}
											placeholder="name@business.com"
											className="w-full h-11 pl-10 pr-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/20 text-sm text-[#231412] placeholder-[#7A5A54]/60 focus:outline-none focus:border-[#C8281E] focus:ring-1 focus:ring-[#C8281E] transition-all"
										/>
									</div>
								</div>

								{error&&(
									<div className="rounded-xl border border-rose-300 bg-rose-50 p-3 text-xs text-rose-700 font-medium">
										{error}
									</div>
								)}

								<MotionButton
									type="submit"
									disabled={loading}
									className="w-full h-12 rounded-xl bg-[#C8281E] text-white font-bold text-xs tracking-wider uppercase hover:bg-[#A81E15] transition-colors shadow-sm flex items-center justify-center gap-2"
								>
									<span>{loading?'Submitting...':'Send Recovery Instructions'}</span>
									{!loading&&<ArrowRight className="w-4 h-4 shrink-0" />}
								</MotionButton>
							</form>
						):(
							<div className="space-y-5 text-center">
								<div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#C8281E]/10 text-[#C8281E] border border-[#C8281E]/20">
									<CheckCircle2 className="h-8 w-8" />
								</div>
								<h2 className="font-extrabold text-xl text-[#231412]">
									Instructions Dispatched
								</h2>
								<p className="text-xs text-[#6E524D] leading-relaxed max-w-sm mx-auto">
									If an active account is associated with <strong className="text-[#231412] font-mono">{email}</strong>, we have sent password reset instructions to that address.
								</p>
								<div className="p-4 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/15 text-xs text-[#5C403B] text-left space-y-1.5">
									<p className="font-bold text-[#231412]">Next Steps:</p>
									<p>1. Check your email inbox (including spam or junk folders).</p>
									<p>2. Open the email message and click the single-use recovery link.</p>
									<p>3. The link remains valid for 15 minutes.</p>
								</div>
								<div className="pt-2 flex flex-col gap-2">
									{devUrl&&(
										<Link
											href={devUrl}
											className="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl bg-emerald-700 text-white text-xs font-bold uppercase tracking-wider hover:bg-emerald-800 transition-colors shadow-sm"
										>
											<span>Proceed with reset now (Dev)</span>
											<ArrowRight className="w-3.5 h-3.5 shrink-0" />
										</Link>
									)}
									<Link
										href="/login"
										className="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl bg-[#C8281E] text-white text-xs font-bold uppercase tracking-wider hover:bg-[#A81E15] transition-colors shadow-sm"
									>
										<span>Return to Sign In</span>
										<ArrowRight className="w-3.5 h-3.5 shrink-0" />
									</Link>
									<button
										type="button"
										onClick={()=>{setSubmitted(false);setEmail('');}}
										className="text-xs font-semibold text-[#7A5A54] hover:text-[#C8281E] transition-colors cursor-pointer py-1"
									>
										Check a different email address
									</button>
								</div>
							</div>
						)}
					</AnimatePresence>
				</div>
			</div>
		</main>
	);
}
