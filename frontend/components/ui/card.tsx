'use client';
import React,{forwardRef,useRef,useState}from 'react';
import{clsx}from 'clsx';
import{motion,useMotionValue,useReducedMotion,useSpring,useTransform}from 'framer-motion';

export interface CardProps extends React.ComponentPropsWithoutRef<typeof motion.div>{
	children?:React.ReactNode;
	variant?:'glass'|'dark'|'outline'|'flat';
	isHoverable?:boolean;
	progress?:number;
}

export const Card=forwardRef<HTMLDivElement,CardProps>(
	({className,variant='glass',isHoverable=true,progress,children,style,onPointerMove,onPointerLeave,onFocusCapture,onBlurCapture,...props},ref)=>{
		const cardRef=useRef<HTMLDivElement|null>(null);
		const reducedMotion=useReducedMotion();
		const [isFocused,setIsFocused]=useState(false);

		const mouseX=useMotionValue(0);
		const mouseY=useMotionValue(0);
		const springConfig={stiffness:300,damping:30};
		const tiltX=useSpring(useTransform(mouseY,[-150,150],[4,-4]),springConfig);
		const tiltY=useSpring(useTransform(mouseX,[-150,150],[-4,4]),springConfig);

		const baseStyles='relative overflow-visible rounded-2xl border border-[#C8281E]/15 transition-shadow duration-300';
		const variantStyles={
			glass:'bg-white/95 shadow-[0_12px_32px_rgba(200,40,30,0.06)] text-[#231412]',
			dark:'bg-[#FAF7F2] border-[#C8281E]/12 shadow-sm text-[#231412]',
			outline:'bg-white border-[#C8281E]/20 text-[#231412]',
			flat:'bg-white text-[#231412] border-transparent shadow-none',
		};
		const hoverStyles=isHoverable?'hover:shadow-[0_18px_40px_rgba(200,40,30,0.1)] hover:border-[#C8281E]/35 cursor-pointer':'';

		const trackPointer=(event:React.PointerEvent<HTMLDivElement>)=>{
			const bounds=event.currentTarget.getBoundingClientRect();
			const xPos=event.clientX-bounds.left;
			const yPos=event.clientY-bounds.top;
			event.currentTarget.style.setProperty('--card-glow-x',`${xPos}px`);
			event.currentTarget.style.setProperty('--card-glow-y',`${yPos}px`);
			if(!isFocused&&isHoverable&&!reducedMotion){
				mouseX.set(xPos-bounds.width/2);
				mouseY.set(yPos-bounds.height/2);
			}
			onPointerMove?.(event);
		};

		const handlePointerLeave=(event:React.PointerEvent<HTMLDivElement>)=>{
			mouseX.set(0);
			mouseY.set(0);
			onPointerLeave?.(event);
		};

		const handleFocusCapture=(event:React.FocusEvent<HTMLDivElement>)=>{
			setIsFocused(true);
			mouseX.set(0);
			mouseY.set(0);
			onFocusCapture?.(event);
		};

		const handleBlurCapture=(event:React.FocusEvent<HTMLDivElement>)=>{
			setIsFocused(false);
			onBlurCapture?.(event);
		};

		return(
			<motion.div
				ref={(node)=>{cardRef.current=node;if(typeof ref==='function')ref(node);else if(ref)ref.current=node;}}
				data-kinetic-card="true"
				className={clsx(baseStyles,variantStyles[variant],hoverStyles,className)}
				style={{
					rotateX:isFocused||reducedMotion?0:tiltX,
					rotateY:isFocused||reducedMotion?0:tiltY,
					transformStyle:'preserve-3d',
					...style,
				}}
				onPointerMove={trackPointer}
				onPointerLeave={handlePointerLeave}
				onFocusCapture={handleFocusCapture}
				onBlurCapture={handleBlurCapture}
				initial={false}
				animate={{opacity:1,y:0}}
				transition={{type:'spring',stiffness:380,damping:28}}
				{...props}
			>
				<span
					className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition-opacity duration-300 hover:opacity-100"
					style={{
						background:'radial-gradient(420px circle at var(--card-glow-x,50%) var(--card-glow-y,50%), rgba(200,40,30,0.08), rgba(230,72,51,0.03) 40%, transparent 70%)',
					}}
					aria-hidden="true"
				/>
				{progress!==undefined&&(
					<motion.span
						className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#C8281E] to-[#E03E32] origin-left rounded-t-2xl"
						aria-hidden="true"
						initial={{scaleX:0}}
						animate={{scaleX:Math.max(0,Math.min(100,progress))/100}}
						transition={{duration:0.9,ease:'easeOut'}}
					/>
				)}
				<div className="relative z-10">{children}</div>
			</motion.div>
		);
	}
);

Card.displayName='Card';

export const CardHeader=forwardRef<HTMLDivElement,React.HTMLAttributes<HTMLDivElement>>(
	({className,children,...props},ref)=>(
		<div
			ref={ref}
			className={clsx('px-6 py-4 border-b border-[#C8281E]/12 flex items-center justify-between',className)}
			{...props}
		>
			{children}
		</div>
	)
);
CardHeader.displayName='CardHeader';

export const CardTitle=forwardRef<HTMLHeadingElement,React.HTMLAttributes<HTMLHeadingElement>>(
	({className,children,...props},ref)=>(
		<h3
			ref={ref}
			className={clsx('text-base font-bold tracking-tight text-[#231412]',className)}
			{...props}
		>
			{children}
		</h3>
	)
);
CardTitle.displayName='CardTitle';

export const CardDescription=forwardRef<HTMLParagraphElement,React.HTMLAttributes<HTMLParagraphElement>>(
	({className,children,...props},ref)=>(
		<p
			ref={ref}
			className={clsx('text-sm text-[#6E524D]',className)}
			{...props}
		>
			{children}
		</p>
	)
);
CardDescription.displayName='CardDescription';

export const CardContent=forwardRef<HTMLDivElement,React.HTMLAttributes<HTMLDivElement>>(
	({className,children,...props},ref)=>(
		<div
			ref={ref}
			className={clsx('p-6',className)}
			{...props}
		>
			{children}
		</div>
	)
);
CardContent.displayName='CardContent';

export const CardFooter=forwardRef<HTMLDivElement,React.HTMLAttributes<HTMLDivElement>>(
	({className,children,...props},ref)=>(
		<div
			ref={ref}
			className={clsx('px-6 py-4 border-t border-[#C8281E]/12 flex items-center',className)}
			{...props}
		>
			{children}
		</div>
	)
);
CardFooter.displayName='CardFooter';
