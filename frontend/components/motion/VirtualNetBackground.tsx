"use client";
import React,{useEffect,useRef}from"react";
interface NetNode{
	baseX:number;
	baseY:number;
	x:number;
	y:number;
	vx:number;
	vy:number;
	radius:number;
	depth:number;
	pulsePhase:number;
	isHub:boolean;
	pulseRingRadius:number;
	pulseRingAlpha:number;
	tag:string;
}
interface SignalPacket{
	sourceIdx:number;
	targetIdx:number;
	progress:number;
	speed:number;
	color:string;
	size:number;
}
const nodeTags=[
	"01 | KHATA",
	"02 | FIFO",
	"03 | BRIDGE",
	"04 | GOVERN",
	"05 | SYNC",
	"06 | AUDIT",
	"07 | LOT_409",
	"08 | PAISA"
];
export function VirtualNetBackground(){
	const canvasRef=useRef<HTMLCanvasElement|null>(null);
	useEffect(()=>{
		const canvas=canvasRef.current;
		if(!canvas){
			return;
		}
		let ctx:CanvasRenderingContext2D|null=null;
		try{
			ctx=canvas.getContext("2d");
		}catch{
			ctx=null;
		}
		if(!ctx){
			return;
		}
		let width=window.innerWidth||1440;
		let height=window.innerHeight||900;
		const dpr=Math.min(window.devicePixelRatio||1,2);
		const applySize=()=>{
			width=window.innerWidth||1440;
			height=window.innerHeight||900;
			canvas.width=width*dpr;
			canvas.height=height*dpr;
			canvas.style.width=`${width}px`;
			canvas.style.height=`${height}px`;
			if(ctx){
				ctx.setTransform(dpr,0,0,dpr,0,0);
			}
		};
		applySize();
		const pointer={
			x:width*0.5,
			y:height*0.35,
			tx:width*0.5,
			ty:height*0.35,
			active:false,
			down:false
		};
		let rawScrollY=window.scrollY||0;
		let smoothScrollY=rawScrollY;
		let scrollVel=0;
		const count=Math.min(105,Math.max(65,Math.floor((width*height)/15000)));
		const nodes:NetNode[]=[];
		for(let i=0;i<count;i+=1){
			const bx=((i*137.5)%100)/100*width;
			const by=((i*293.7)%100)/100*height;
			const isHub=i%5===0;
			nodes.push({
				baseX:bx,
				baseY:by,
				x:bx,
				y:by,
				vx:(Math.cos(i*1.9)*0.45),
				vy:(Math.sin(i*2.4)*0.45),
				radius:isHub?4.2:2.4,
				depth:isHub?0.55:0.2+(i%4)*0.08,
				pulsePhase:i*0.7,
				isHub,
				pulseRingRadius:0,
				pulseRingAlpha:0,
				tag:nodeTags[i%nodeTags.length]
			});
		}
		const packets:SignalPacket[]=[];
		const spawnPacket=()=>{
			if(nodes.length<2){
				return;
			}
			const sourceIdx=Math.floor(Math.random()*nodes.length);
			let bestTarget=-1;
			let bestDist=999999;
			const sNode=nodes[sourceIdx];
			for(let j=0;j<nodes.length;j+=1){
				if(j===sourceIdx){
					continue;
				}
				const tNode=nodes[j];
				const dx=sNode.x-tNode.x;
				const dy=sNode.y-tNode.y;
				const d=dx*dx+dy*dy;
				if(d<45000&&d>400&&d<bestDist){
					bestDist=d;
					bestTarget=j;
				}
			}
			if(bestTarget!==-1){
				packets.push({
					sourceIdx,
					targetIdx:bestTarget,
					progress:0,
					speed:0.012+Math.random()*0.02,
					color:Math.random()>0.35?"#C8281E":"#E64833",
					size:sNode.isHub?3.5:2.5
				});
			}
		};
		for(let p=0;p<18;p+=1){
			spawnPacket();
		}
		const handleResize=()=>{
			applySize();
		};
		const handlePointerMove=(e:MouseEvent)=>{
			pointer.tx=e.clientX;
			pointer.ty=e.clientY;
			pointer.active=true;
		};
		const handlePointerDown=()=>{
			pointer.down=true;
			for(let i=0;i<nodes.length;i+=1){
				const n=nodes[i];
				const dx=pointer.x-n.x;
				const dy=pointer.y-n.y;
				const dSq=dx*dx+dy*dy;
				if(dSq<65000){
					n.pulseRingRadius=n.radius;
					n.pulseRingAlpha=0.85;
				}
			}
		};
		const handlePointerUp=()=>{
			pointer.down=false;
		};
		const handleScroll=()=>{
			rawScrollY=window.scrollY||0;
		};
		window.addEventListener("resize",handleResize,{passive:true});
		window.addEventListener("mousemove",handlePointerMove,{passive:true});
		window.addEventListener("mousedown",handlePointerDown,{passive:true});
		window.addEventListener("mouseup",handlePointerUp,{passive:true});
		window.addEventListener("scroll",handleScroll,{passive:true});
		let rafId=0;
		let tickCount=0;
		const render=()=>{
			tickCount+=0.022;
			const deltaScroll=rawScrollY-smoothScrollY;
			smoothScrollY+=deltaScroll*0.14;
			scrollVel+=(deltaScroll-scrollVel)*0.2;
			pointer.x+=(pointer.tx-pointer.x)*0.12;
			pointer.y+=(pointer.ty-pointer.y)*0.12;
			ctx.clearRect(0,0,width,height);
			const gridStep=80;
			const gridOffsetY=((smoothScrollY*0.2)%gridStep+gridStep)%gridStep;
			ctx.strokeStyle="rgba(200,40,30,0.045)";
			ctx.lineWidth=1;
			ctx.beginPath();
			for(let gx=0;gx<width;gx+=gridStep){
				ctx.moveTo(gx,0);
				ctx.lineTo(gx,height);
			}
			for(let gy=-gridStep+gridOffsetY;gy<height;gy+=gridStep){
				ctx.moveTo(0,gy);
				ctx.lineTo(width,gy);
			}
			ctx.stroke();
			const wrapH=height+180;
			for(let i=0;i<nodes.length;i+=1){
				const n=nodes[i];
				n.baseX+=n.vx;
				n.baseY+=n.vy;
				if(n.baseX<-80){
					n.baseX=width+80;
				}
				if(n.baseX>width+80){
					n.baseX=-80;
				}
				if(n.baseY<-90){
					n.baseY=height+90;
				}
				if(n.baseY>height+90){
					n.baseY=-90;
				}
				const parallaxShift=(smoothScrollY*n.depth)%wrapH;
				let py=n.baseY-parallaxShift;
				if(py<-90){
					py+=wrapH;
				}
				if(py>height+90){
					py-=wrapH;
				}
				const waveX=Math.sin(tickCount+n.pulsePhase)*7;
				const velShiftY=Math.max(-36,Math.min(36,scrollVel*n.depth*0.42));
				let px=n.baseX+waveX;
				py+=velShiftY;
				if(pointer.active){
					const dx=pointer.x-px;
					const dy=pointer.y-py;
					const distSq=dx*dx+dy*dy;
					if(distSq<64000&&distSq>1){
						const dist=Math.sqrt(distSq);
						const pull=(1-dist/253)*24*n.depth*(pointer.down?1.8:1);
						px+=(dx/dist)*pull;
						py+=(dy/dist)*pull;
					}
				}
				n.x=px;
				n.y=py;
				if(n.pulseRingAlpha>0.01){
					n.pulseRingRadius+=1.4;
					n.pulseRingAlpha*=0.94;
					ctx.strokeStyle=`rgba(200,40,30,${n.pulseRingAlpha.toFixed(3)})`;
					ctx.lineWidth=1.5;
					ctx.beginPath();
					ctx.strokeRect(n.x-n.pulseRingRadius,n.y-n.pulseRingRadius,n.pulseRingRadius*2,n.pulseRingRadius*2);
				}else if(n.isHub&&Math.sin(tickCount*1.4+n.pulsePhase)>0.985){
					n.pulseRingRadius=n.radius;
					n.pulseRingAlpha=0.65;
				}
			}
			const maxDist=Math.min(245,Math.max(175,width*0.145));
			const maxDistSq=maxDist*maxDist;
			for(let i=0;i<nodes.length;i+=1){
				const a=nodes[i];
				for(let j=i+1;j<nodes.length;j+=1){
					const b=nodes[j];
					const dx=a.x-b.x;
					const dy=a.y-b.y;
					const dSq=dx*dx+dy*dy;
					if(dSq<maxDistSq){
						const ratio=1-Math.sqrt(dSq)/maxDist;
						const alpha=(a.isHub||b.isHub)?ratio*0.42:ratio*0.24;
						ctx.strokeStyle=`rgba(200,40,30,${alpha.toFixed(3)})`;
						ctx.lineWidth=(a.isHub&&b.isHub)?1.65:1.0;
						ctx.beginPath();
						ctx.moveTo(a.x,a.y);
						ctx.lineTo(b.x,b.y);
						ctx.stroke();
					}
				}
			}
			if(pointer.active){
				ctx.fillStyle="#C8281E";
				ctx.fillRect(pointer.x-3,pointer.y-3,6,6);
				const cursorRingSize=12+Math.sin(tickCount*3)*3;
				ctx.strokeStyle="rgba(200,40,30,0.35)";
				ctx.lineWidth=1.2;
				ctx.strokeRect(pointer.x-cursorRingSize*0.5,pointer.y-cursorRingSize*0.5,cursorRingSize,cursorRingSize);
				let connected=0;
				for(let i=0;i<nodes.length&&connected<5;i+=1){
					const n=nodes[i];
					const dx=pointer.x-n.x;
					const dy=pointer.y-n.y;
					const dSq=dx*dx+dy*dy;
					if(dSq<48000){
						const dist=Math.sqrt(dSq);
						const alpha=(1-dist/220)*0.52;
						ctx.strokeStyle=`rgba(230,72,51,${alpha.toFixed(3)})`;
						ctx.lineWidth=1.3;
						ctx.beginPath();
						ctx.moveTo(pointer.x,pointer.y);
						ctx.lineTo(n.x,n.y);
						ctx.stroke();
						connected+=1;
					}
				}
			}
			if(packets.length<24&&Math.random()>0.3){
				spawnPacket();
			}
			for(let p=packets.length-1;p>=0;p-=1){
				const pkt=packets[p];
				pkt.progress+=pkt.speed;
				const source=nodes[pkt.sourceIdx];
				const target=nodes[pkt.targetIdx];
				if(!source||!target||pkt.progress>=1){
					if(target){
						target.pulseRingRadius=target.radius;
						target.pulseRingAlpha=0.7;
					}
					packets.splice(p,1);
					continue;
				}
				const curX=source.x+(target.x-source.x)*pkt.progress;
				const curY=source.y+(target.y-source.y)*pkt.progress;
				ctx.fillStyle=pkt.color;
				ctx.fillRect(curX-pkt.size*0.5,curY-pkt.size*0.5,pkt.size,pkt.size);
				const trailLen=0.15;
				const trailProgress=Math.max(0,pkt.progress-trailLen);
				const prevX=source.x+(target.x-source.x)*trailProgress;
				const prevY=source.y+(target.y-source.y)*trailProgress;
				ctx.strokeStyle=`rgba(230,72,51,${(0.5*(1-pkt.progress)).toFixed(3)})`;
				ctx.lineWidth=1.8;
				ctx.beginPath();
				ctx.moveTo(prevX,prevY);
				ctx.lineTo(curX,curY);
				ctx.stroke();
			}
			for(let i=0;i<nodes.length;i+=1){
				const n=nodes[i];
				if(n.isHub){
					const ringSize=n.radius+4+Math.sin(tickCount*2.2+n.pulsePhase)*2.2;
					ctx.fillStyle="rgba(200,40,30,0.18)";
					ctx.fillRect(n.x-ringSize,n.y-ringSize,ringSize*2,ringSize*2);
					ctx.fillStyle="#C8281E";
					ctx.fillRect(n.x-n.radius,n.y-n.radius,n.radius*2,n.radius*2);
					ctx.strokeStyle="#231412";
					ctx.lineWidth=1.2;
					ctx.strokeRect(n.x-n.radius,n.y-n.radius,n.radius*2,n.radius*2);
					if(i%10===0){
						ctx.fillStyle="rgba(200,40,30,0.65)";
						ctx.font="9px monospace";
						ctx.fillText(n.tag,n.x+n.radius+5,n.y+3);
					}
				}else{
					ctx.fillStyle="#231412";
					ctx.fillRect(n.x-n.radius,n.y-n.radius,n.radius*2,n.radius*2);
				}
			}
			rafId=window.requestAnimationFrame(render);
		};
		rafId=window.requestAnimationFrame(render);
		return()=>{
			window.cancelAnimationFrame(rafId);
			window.removeEventListener("resize",handleResize);
			window.removeEventListener("mousemove",handlePointerMove);
			window.removeEventListener("mousedown",handlePointerDown);
			window.removeEventListener("mouseup",handlePointerUp);
			window.removeEventListener("scroll",handleScroll);
		};
	},[]);
	return(
		<canvas
			ref={canvasRef}
			aria-hidden="true"
			className="pointer-events-none fixed inset-0 z-0 h-full w-full"
		/>
	);
}
