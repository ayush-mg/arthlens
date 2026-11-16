'use client';
import {ReactNode,useEffect,useRef} from 'react';
import {usePathname} from 'next/navigation';
import {AnimatePresence,motion,useReducedMotion,useScroll,useSpring,useTransform,useVelocity} from 'framer-motion';
import gsap from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';

type WorkspaceKineticSurfacesProps={children:ReactNode};

const cardSelector='[data-kinetic-card], .kpi-card, .surface-card, [data-parallax-tile="true"], section, article';

export function WorkspaceKineticSurfaces({children}:WorkspaceKineticSurfacesProps){
	const rootRef=useRef<HTMLDivElement>(null);
	const pathname=usePathname();
	const reducedMotion=useReducedMotion();

	const {scrollY}=useScroll();
	const scrollVelocity=useVelocity(scrollY);
	const velocitySpring=useSpring(scrollVelocity,{stiffness:220,damping:24});
	const skewY=useTransform(velocitySpring,[-2000,2000],reducedMotion?[0,0]:[-1.4,1.4]);

	useEffect(()=>{
		const root=rootRef.current;
		if(!root||reducedMotion)return;
		gsap.registerPlugin(ScrollTrigger);
		const scroller=root.closest('.workspace-content')??undefined;
		const reveals=new Map<HTMLElement,gsap.Context>();
		let scanFrame=0;

		const attachParallax=(element:HTMLElement)=>{
			if(reveals.has(element)||element.dataset.gsapScrollBound==='true')return;
			if(element.tagName==='FORM'||element.tagName==='TABLE'||element.tagName==='INPUT'||element.closest('table, form'))return;
			element.dataset.gsapScrollBound='true';
			const context=gsap.context(()=>{
				gsap.fromTo(element,
					{
						y:44,
						rotateX:7,
						scale:0.96,
					},
					{
						y:0,
						rotateX:0,
						scale:1,
						duration:0.6,
						ease:'power3.out',
						clearProps:'transform',
						scrollTrigger:{
							trigger:element,
							scroller,
							start:'top 94%',
							once:true,
						},
					},
				);
			},element);
			reveals.set(element,context);
		};

		const scan=()=>{
			scanFrame=0;
			root.querySelectorAll<HTMLElement>(cardSelector).forEach(attachParallax);
			ScrollTrigger.refresh();
		};

		scan();

		const observer=new MutationObserver(()=>{
			if(!scanFrame)scanFrame=window.requestAnimationFrame(scan);
		});
		observer.observe(root,{childList:true,subtree:true});

		return()=>{
			observer.disconnect();
			if(scanFrame)window.cancelAnimationFrame(scanFrame);
			reveals.forEach((context,element)=>{
				context.revert();
				delete element.dataset.gsapScrollBound;
			});
			reveals.clear();
			ScrollTrigger.refresh();
		};
	},[reducedMotion,pathname]);

	return(
		<div className="relative w-full min-h-full overflow-hidden" ref={rootRef}>
			<AnimatePresence mode="wait">
				<motion.div
					key={pathname}
					initial={{opacity:0,scale:0.94,y:28,rotateX:4}}
					animate={{opacity:1,scale:1,y:0,rotateX:0}}
					exit={{opacity:0,scale:1.04,y:-20}}
					transition={{duration:0.55,ease:[0.16,1,0.3,1]}}
					style={{perspective:1200,skewY}}
					className="relative z-10 w-full"
				>
					{children}
				</motion.div>
			</AnimatePresence>
		</div>
	);
}

export const WorkspaceKineticStage=WorkspaceKineticSurfaces;
export default WorkspaceKineticStage;
