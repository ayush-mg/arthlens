'use client';
import {MotionButton} from '@/components/ui/motion-button';
import {FormEvent,useEffect,useState} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {AnimatePresence,motion,useMotionValue,useSpring,useTransform} from 'framer-motion';
import {ArrowLeft,ArrowRight,LockKeyhole,Mail,ShieldCheck} from 'lucide-react';
import {GoogleSignIn} from '../../components/auth/GoogleSignIn';
import {OtpInput} from '../../components/auth/OtpInput';
import {ScrambleText} from '../../components/motion/ScrambleText';
import {ArthLensBrandMark} from '../../components/motion/ArthLensBrandMark';
import {authenticateWithGoogle,initiateEmailLogin,OtpChallenge,resendEmailOtp,verifyEmailLoginOtp} from '../../lib/api';

type Step='credentials'|'verification';

export default function LoginPage(){
	const router=useRouter();
	const [step,setStep]=useState<Step>('credentials');
	const [email,setEmail]=useState('');
	const [password,setPassword]=useState('');
	const [otp,setOtp]=useState('');
	const [challenge,setChallenge]=useState<OtpChallenge|null>(null);
	const [secondsLeft,setSecondsLeft]=useState(600);
	const [resendWait,setResendWait]=useState(0);
	const [error,setError]=useState('');
	const [busy,setBusy]=useState(false);

	const mouseX=useMotionValue(0);
	const mouseY=useMotionValue(0);
	const springConfig={stiffness:260,damping:28};
	const rotateX=useSpring(useTransform(mouseY,[-300,300],[6,-6]),springConfig);
	const rotateY=useSpring(useTransform(mouseX,[-300,300],[-6,6]),springConfig);
	const badgeX=useSpring(useTransform(mouseX,[-300,300],[-14,14]),springConfig);
	const badgeY=useSpring(useTransform(mouseY,[-300,300],[-14,14]),springConfig);

	const handleStageMouseMove=(event:React.MouseEvent<HTMLDivElement>)=>{
		const rect=event.currentTarget.getBoundingClientRect();
		mouseX.set(event.clientX-(rect.left+rect.width/2));
		mouseY.set(event.clientY-(rect.top+rect.height/2));
	};

	const enterWorkspaceGalaxy=async()=>{
		await new Promise((resolve)=>window.setTimeout(resolve,150));
		router.replace('/workspaces');
	};

	useEffect(()=>{
		const timer=window.setInterval(()=>{
			setSecondsLeft((seconds)=>Math.max(0,seconds-1));
			setResendWait((seconds)=>Math.max(0,seconds-1));
		},1000);
		return()=>window.clearInterval(timer);
	},[]);


	const completeGoogleSignIn=async(input:{idToken?:string;email?:string;fullName?:string})=>{
		setBusy(true);
		setError('');
		try{
			await authenticateWithGoogle({mode:'login',...input});
			await enterWorkspaceGalaxy();
		}catch(cause){
			setError(cause instanceof Error?cause.message:'Google sign-in could not be completed.');
		}finally{
			setBusy(false);
		}
	};

	const startLogin=async(event:FormEvent)=>{
		event.preventDefault();
		setBusy(true);
		setError('');
		try{
			const result=await initiateEmailLogin(email.trim(),password);
			setChallenge(result);
			setOtp('');
			setSecondsLeft(result.expires_in_seconds||600);
			setResendWait(30);
			setStep('verification');
		}catch(cause){
			setError(cause instanceof Error?cause.message:'Sign-in could not be started.');
		}finally{
			setBusy(false);
		}
	};

	const verify=async(event:FormEvent)=>{
		event.preventDefault();
		if(!challenge||otp.length!==6){
			setError('Enter the six digit code sent to your email.');
			return;
		}
		setBusy(true);
		setError('');
		try{
			await verifyEmailLoginOtp(challenge.challenge_id,challenge.email,otp);
			await enterWorkspaceGalaxy();
		}catch(cause){
			setError(cause instanceof Error?cause.message:'The verification code could not be accepted.');
			setOtp('');
		}finally{
			setBusy(false);
		}
	};

	const resend=async()=>{
		if(!challenge||resendWait>0)return;
		setBusy(true);
		setError('');
		try{
			const nextChallenge=await resendEmailOtp(challenge.challenge_id,challenge.email);
			setChallenge(nextChallenge);
			setOtp('');
			setSecondsLeft(nextChallenge.expires_in_seconds||600);
			setResendWait(30);
		}catch(cause){
			setError(cause instanceof Error?cause.message:'A new code could not be sent.');
		}finally{
			setBusy(false);
		}
	};

	const back=()=>{
		setError('');
		setOtp('');
		setStep('credentials');
	};

	return(
		<div className="relative min-h-screen w-full bg-transparent text-[#231412] select-none">
			<header className="fixed top-0 inset-x-0 z-50 h-20 bg-white/95 border-b-2 border-[#231412] px-6 lg:px-14 flex items-center justify-between shadow-sm">
				<Link href="/" className="flex items-center gap-3 group" title="Return to ArthLens landing page">
					<ArthLensBrandMark />
				</Link>
				<div className="flex items-center gap-3">
					<div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-[#FAF7F2] border-2 border-[#231412] text-[10px] font-mono font-bold text-[#231412] shadow-[2px_2px_0px_#231412]">
						<span className="w-2 h-2 bg-[#C8281E] animate-pulse" />
						<span>ACCESS PORTAL // 01</span>
					</div>
					<Link href="/" className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#FAF7F2] border-2 border-[#231412] text-xs font-mono font-bold text-[#231412] hover:bg-[#C8281E] hover:text-white transition-colors shadow-[2px_2px_0px_#231412]" title="Return to landing page">
						<ArrowLeft size={14} /> Back to Landing
					</Link>
				</div>
			</header>
			<main className="relative min-h-screen flex items-center justify-center p-4 md:p-8 pt-24 md:pt-28 bg-transparent text-[#231412] select-none" onMouseMove={handleStageMouseMove}>
			<div className="max-w-7xl mx-auto min-h-screen grid grid-cols-1 lg:grid-cols-12 gap-10 items-center px-6 py-12 relative z-10 w-full" style={{perspective:1400}}>
				<motion.div
					className="lg:col-span-7 bg-white/90 backdrop-blur-xl border border-[#C8281E]/20 rounded-3xl p-8 md:p-10 shadow-[0_24px_70px_rgba(200,40,30,0.08)] flex flex-col justify-between gap-8"
					style={{rotateX,rotateY,transformStyle:'preserve-3d'}}
				>
					<div>
						<div className="flex items-center justify-between flex-wrap gap-4 mb-6">
							<Link href="/" className="inline-block"><ArthLensBrandMark /></Link>
							<motion.span
								className="px-3.5 py-1.5 rounded-full bg-[#C8281E]/10 border border-[#C8281E]/20 text-[11px] font-mono font-bold tracking-widest text-[#C8281E]"
								style={{x:badgeX,y:badgeY}}
							>
								FINANCIAL CLARITY · ACCESS 01
							</motion.span>
						</div>
						<h1 className="text-4xl md:text-5xl font-black text-[#231412] leading-tight mb-4">
							Know the numbers.<br />
							<span className="text-[#C8281E]">Move with intent.</span>
						</h1>
						<p className="text-base text-[#5C403B] leading-relaxed max-w-lg">
							A single, trusted view of business operations, deterministic financial health, and the decisions ahead.
						</p>
					</div>

					<div className="bg-[#FAF7F2] border border-[#C8281E]/20 rounded-2xl p-6 space-y-4 shadow-inner">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-2">
								<span className="w-2.5 h-2.5 rounded-full bg-[#C8281E] animate-pulse" />
								<span className="text-xs font-extrabold tracking-widest uppercase text-[#5C403B] font-mono">OPERATING PULSE</span>
							</div>
							<span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold font-mono">↑ 12.8%</span>
						</div>
						<div className="relative w-full h-36">
							<svg viewBox="0 0 500 130" className="w-full h-36 overflow-visible" role="img" aria-label="Upward financial trend">
								<defs>
									<linearGradient id="loginSparkGradient" x1="0" y1="0" x2="0" y2="1">
										<stop offset="0%" stopColor="#C8281E" stopOpacity="0.25" />
										<stop offset="100%" stopColor="#C8281E" stopOpacity="0.0" />
									</linearGradient>
								</defs>
								<line x1="0" y1="35" x2="500" y2="35" stroke="rgba(200,40,30,0.14)" strokeDasharray="4 4" strokeWidth="1" />
								<line x1="0" y1="80" x2="500" y2="80" stroke="rgba(200,40,30,0.14)" strokeDasharray="4 4" strokeWidth="1" />
								<path
									d="M0 110 C50 100 65 78 120 86 S185 100 230 58 S300 70 340 45 S400 52 440 28 S480 38 500 14 L500 130 L0 130 Z"
									fill="url(#loginSparkGradient)"
								/>
								<motion.path
									d="M0 110 C50 100 65 78 120 86 S185 100 230 58 S300 70 340 45 S400 52 440 28 S480 38 500 14"
									fill="none"
									stroke="#C8281E"
									strokeWidth="3.2"
									strokeLinecap="round"
									initial={{pathLength:0}}
									animate={{pathLength:1}}
									transition={{duration:1.2,ease:'easeOut'}}
								/>
								<circle cx="230" cy="58" r="4" fill="#C8281E" className="animate-ping" opacity="0.6" />
								<circle cx="230" cy="58" r="3.5" fill="#C8281E" />
								<circle cx="500" cy="14" r="4.5" fill="#C8281E" />
							</svg>
						</div>
						<div className="flex items-center justify-between pt-3 border-t border-[#C8281E]/15 text-xs font-bold tracking-[0.2em] text-[#8C6D68] font-mono">
							<span>01 JUN</span>
							<span>15 JUN</span>
							<span>30 JUN</span>
						</div>
					</div>

					<div className="flex items-center gap-4 flex-wrap">
						<span className="bg-[#FAF7F2] border border-[#C8281E]/15 px-4 py-2 rounded-xl text-xs font-bold text-[#231412] flex items-center gap-2">
							<ShieldCheck className="w-4 h-4 text-[#C8281E] shrink-0" /> WORKSPACE PRIVATE
						</span>
						<span className="bg-[#FAF7F2] border border-[#C8281E]/15 px-4 py-2 rounded-xl text-xs font-bold text-[#231412] flex items-center gap-2">
							<ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" /> AUTH / 2FA READY
						</span>
					</div>
				</motion.div>

				<motion.div
					initial={{opacity:0,y:22,scale:0.98}}
					animate={{opacity:1,y:0,scale:1}}
					transition={{duration:0.55,ease:[0.22,1,0.36,1]}}
					className="lg:col-span-5 w-full max-w-md mx-auto"
				>
					<section className="bg-white/95 border border-[#C8281E]/20 rounded-3xl p-8 sm:p-10 shadow-2xl">
						<header className="mb-7">
							<div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-[#C8281E]">
								<ShieldCheck className="w-4 h-4 shrink-0" /> SECURE ACCESS
							</div>
							<h2 className="text-2xl font-black tracking-tight text-[#231412]">
								<ScrambleText text={step==='credentials'?'Welcome back':'Check your email'} />
							</h2>
							<p className="mt-1.5 text-xs text-[#6E524D] leading-relaxed">
								{step==='credentials'?'Continue to your financial and decision workspace.':'We sent a 6-digit verification code to your email address.'}
							</p>
						</header>

						<AnimatePresence mode="wait" initial={false}>
							{step==='credentials'?(
								<motion.div
									key="credentials"
									initial={{opacity:0,x:-12}}
									animate={{opacity:1,x:0}}
									exit={{opacity:0,x:12}}
									transition={{type:'spring',stiffness:360,damping:32}}
								>
									<form className="space-y-4" onSubmit={startLogin}>
										<label className="block text-xs font-bold text-[#7A5A54] uppercase tracking-wider">
											Email address
											<span className="relative mt-1.5 block">
												<Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7A5A54]" />
												<input
													type="email"
													autoComplete="email"
													required
													value={email}
													onChange={(event)=>setEmail(event.target.value)}
													placeholder="name@business.com"
													className="w-full h-11 pl-10 pr-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/20 text-sm text-[#231412] placeholder-[#7A5A54]/60 focus:outline-none focus:border-[#C8281E] focus:ring-1 focus:ring-[#C8281E] transition-all"
												/>
											</span>
										</label>

										<label className="block text-xs font-bold text-[#7A5A54] uppercase tracking-wider">
											Password
											<span className="relative mt-1.5 block">
												<LockKeyhole className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7A5A54]" />
												<input
													type="password"
													autoComplete="current-password"
													required
													value={password}
													onChange={(event)=>setPassword(event.target.value)}
													placeholder="Enter your password"
													className="w-full h-11 pl-10 pr-3.5 rounded-xl bg-[#FAF7F2] border border-[#C8281E]/20 text-sm text-[#231412] placeholder-[#7A5A54]/60 focus:outline-none focus:border-[#C8281E] focus:ring-1 focus:ring-[#C8281E] transition-all"
												/>
											</span>
										</label>

										<div className="flex justify-end">
											<Link href="/forgot-password" className="text-xs font-semibold text-[#C8281E] hover:underline">Forgot password?</Link>
										</div>

										{error&&(
											<p role="alert" className="p-3 rounded-xl border border-rose-300 bg-rose-50 text-xs text-rose-700 font-medium">{error}</p>
										)}

										<MotionButton disabled={busy} className="w-full h-12 rounded-xl bg-[#C8281E] text-white font-bold text-xs tracking-wider uppercase hover:bg-[#A81E15] transition-colors shadow-sm flex items-center justify-center gap-2">
											<span>{busy?'Sending secure code…':'Continue with Password (Send 2FA OTP)'}</span>
											{!busy&&<ArrowRight className="w-4 h-4 shrink-0" />}
										</MotionButton>
									</form>

									<div className="my-5 flex items-center gap-3 text-[10px] uppercase tracking-wider text-[#7A5A54] font-semibold">
										<span className="h-px flex-1 bg-[#C8281E]/15" />or continue with<span className="h-px flex-1 bg-[#C8281E]/15" />
									</div>

									<GoogleSignIn
										mode="login"
										onCredential={(idToken)=>void completeGoogleSignIn({idToken})}
										onLocalAccount={(localEmail,fullName)=>void completeGoogleSignIn({email:localEmail,fullName})}
									/>
								</motion.div>
							):(
								<motion.form
									key="verification"
									className="space-y-5"
									onSubmit={verify}
									initial={{opacity:0,x:12}}
									animate={{opacity:1,x:0}}
									exit={{opacity:0,x:-12}}
									transition={{type:'spring',stiffness:360,damping:32}}
								>
									<OtpInput value={otp} onChange={setOtp} />

									{challenge?.dev_otp_preview&&(
										<span className="sr-only" data-testid="dev-otp-preview">
											Local development code: {challenge.dev_otp_preview}
										</span>
									)}

									<div className="flex items-center justify-between text-xs text-[#7A5A54]">
										<span>Code expires in <strong className="font-mono tabular-nums text-[#231412] font-bold">{Math.floor(secondsLeft/60)}:{String(secondsLeft%60).padStart(2,'0')}</strong></span>
										<MotionButton type="button" disabled={busy||resendWait>0} onClick={()=>void resend()} className="font-bold text-[#C8281E] hover:underline disabled:text-[#7A5A54]/50">
											{resendWait?'Resend in '+resendWait+'s':'Resend code'}
										</MotionButton>
									</div>

									{error&&(
										<p role="alert" className="p-3 rounded-xl border border-rose-300 bg-rose-50 text-xs text-rose-700 font-medium">{error}</p>
									)}

									<MotionButton disabled={busy||otp.length!==6} className="w-full h-12 rounded-xl bg-[#C8281E] text-white font-bold text-xs tracking-wider uppercase hover:bg-[#A81E15] transition-colors shadow-sm flex items-center justify-center gap-2">
										<span>{busy?'Verifying…':'Verify 2FA & Sign In'}</span>
										<ArrowRight className="w-4 h-4 shrink-0" />
									</MotionButton>

									<MotionButton type="button" onClick={back} className="mx-auto flex items-center gap-1.5 py-1 text-xs font-semibold text-[#7A5A54] hover:text-[#C8281E]">
										<ArrowLeft className="w-3.5 h-3.5 shrink-0" /> Use a different account
									</MotionButton>
								</motion.form>
							)}
						</AnimatePresence>
					</section>

					<p className="mt-6 text-center text-xs text-[#6E524D]">
						New to ArthLens? <Link href="/register" className="font-bold text-[#C8281E] hover:underline">Create an account</Link>
					</p>
					<p className="mt-3 text-center text-[10px] text-[#7A5A54] font-medium">
						Your business records stay private to your workspace.
					</p>
				</motion.div>
			</div>
		</main>
		</div>
	);
}
