import React from 'react';
import {AbsoluteFill,Composition,Sequence,OffthreadVideo,registerRoot,useCurrentFrame,useVideoConfig,staticFile} from 'remotion';
import {BrandWatermark} from '../src/BrandWatermark';
import {assertLayout,bodyFrameCount,palette as P,headingFor,supportText,labelBounds,conditionLabels,coneLabels} from './layout.mjs';
import {smooth,clamp,mix,spectrum,displayRay,exitDetail,magnifiedExitPoint,polylinePoint,movingEye,approachingEye,projectFixedDrop,fixedDropField,dropLight,coneSlice,arcPoints,circleReveal} from './model.mjs';
type Props={duration:number;scenes:any[];captions:any[];outro?:boolean;burnCaptions?:boolean};
type VisualProps={portrait:boolean;t:number;marks:any};
const path=(points:any[])=>'M'+points.map(p=>`${p.x},${p.y}`).join('L');
function Defs(){return <defs>
 <linearGradient id="rainbow-sky" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#65577c"/><stop offset=".44" stopColor="#2d6381"/><stop offset="1" stopColor="#133e5c"/></linearGradient>
 <linearGradient id="rainbow-land" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#286066"/><stop offset="1" stopColor="#132d43"/></linearGradient>
 <radialGradient id="drop-glass" cx=".3" cy=".25"><stop stopColor="#adf0f1" stopOpacity=".42"/><stop offset=".7" stopColor="#64b6d7" stopOpacity=".19"/><stop offset="1" stopColor="#6fa8d5" stopOpacity=".33"/></radialGradient>
 <radialGradient id="sun-glow"><stop stopColor="#fff9d8"/><stop offset=".55" stopColor="#ffd885" stopOpacity=".7"/><stop offset="1" stopColor="#ffd885" stopOpacity="0"/></radialGradient>
 <marker id="rain-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0 0L10 5L0 10Z" fill={P.ivory}/></marker>
 <marker id="rain-red-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="3" markerHeight="3" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#ff7a83"/></marker>
 <marker id="rain-violet-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="3" markerHeight="3" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#b49cff"/></marker>
 </defs>}
function Label(a:any){const {x,y,text,size=48,anchor='middle',colour=P.ivory}=a,b=labelBounds(a);return <g><rect {...b} rx="10" fill="#15243a" fillOpacity=".94"/><text x={anchor==='start'?x+12:anchor==='end'?x-12:x} y={y} textAnchor={anchor} fontSize={size} fontWeight="650" fill={colour}>{text}</text></g>}
function Sun({x,y,r=40}:any){return <g><circle cx={x} cy={y} r={r*1.8} fill="url(#sun-glow)"/><circle cx={x} cy={y} r={r} fill="#ffe4a0" stroke="#fff7d7" strokeWidth="3"/></g>}
function Drop({x,y,size=10,colour=P.cyan,opacity=.8}:any){return <g transform={`translate(${x} ${y})`} opacity={opacity}><path d={`M0 ${-size}C${size*.45} ${-size*.3} ${size*.8} ${size*.15} ${size*.65} ${size*.6}Q0 ${size*1.5} ${-size*.65} ${size*.6}C${-size*.8} ${size*.15} ${-size*.45} ${-size*.3} 0 ${-size}Z`} fill={colour}/><path d={`M${-size*.27} ${size*.15}Q${-size*.36} ${size*.57} ${-size*.08} ${size*.7}`} fill="none" stroke="#fff" strokeOpacity=".6" strokeWidth={size*.15}/></g>}
// A neutral whole-body observer, with arms down and both legs attached.
function Observer({x,y,size=1,colour=P.ivory,opacity=1}:any){return <g transform={`translate(${x} ${y}) scale(${size})`} opacity={opacity} aria-label="Neutral human observer, arms down">
 <circle cy="0" r="24" fill={colour}/><path d="M-16 28Q0 20 17 28L26 98H-25Z" fill={colour}/><path d="M-14 90L-21 155M15 90L25 155M-20 37L-39 92M21 37L40 92" stroke={colour} strokeWidth="14" strokeLinecap="round"/><circle cx="12" cy="-3" r="4" fill="#173449"/>
 </g>}
function Rainbow({cx,cy,r,start=180,end=360,opacity=1,width=43}:any){return <g opacity={opacity} aria-label="Continuous spectrum, red on the outer edge and violet inside">{spectrum.map((s,i)=>{const rr=r-s.fraction*width;return <path key={i} d={path(arcPoints(cx,cy,rr,start,end))} fill="none" stroke={s.colour} strokeWidth={width/48+1.4} opacity=".88"/>})}</g>}
function Sky({w=900}:any){return <><rect x="12" y="12" width={w-24} height="722" rx="35" fill="url(#rainbow-sky)"/><path d={`M12 636Q${w*.25} 585 ${w*.48} 641T${w-12} 625V705Q${w-12} 734 ${w-45} 734H45Q12 734 12 700Z`} fill="url(#rainbow-land)"/></>}
function Opening({portrait,t,marks,callback=false}:VisualProps&{callback?:boolean}){
 const w=portrait?900:1600,cx=portrait?450:1000,cy=610,r=portrait?335:470;
 const step=smooth(t,marks.step??Infinity,(marks.step??Infinity)+.9),change=smooth(t,marks.change??Infinity,(marks.change??Infinity)+.5);
 const eye=approachingEye(callback?0:step),field=fixedDropField();
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%"><Defs/><Sky w={w}/><Rainbow {...{cx,cy,r}}/>
  <defs><clipPath id="opening-rain-view"><rect x="20" y="20" width={w-40} height="595" rx="25"/></clipPath></defs>
  <g clipPath="url(#opening-rain-view)" aria-label="Fixed droplets reproject and a different set sends colour as the observer approaches">{field.map((p,i)=>{const screen=projectFixedDrop(eye,p,{cx,cy,r}),light=dropLight(eye,p);return <Drop key={i} {...screen} size={light.selected?7.5:4} colour={light.selected?light.colour:'#c5e1df'} opacity={light.selected?.94:.12}/>})}</g>
  <Observer x={portrait?180:255} y={535} size={.7}/>
  {step>0&&<path d={`M${portrait?150:200} 704H${portrait?265:390}`} stroke={P.ivory} strokeWidth="5" markerEnd="url(#rain-arrow)" opacity={step}/>}
  {!callback&&<Label x={portrait?640:1250} y={710} text={change>.5?'Different drops':'Your view'} size={portrait?46:62}/>}
  {callback&&<><Label x={portrait?450:800} y={100} text="Sunlight · drops · you" size={portrait?48:64}/><path d={`M${portrait?450:800} 125V180`} stroke={P.ivory} strokeWidth="4" opacity=".5"/></>}
 </svg>;
}
function Conditions({portrait,t,marks}:VisualProps){
 const w=portrait?900:1600,labels=conditionLabels(portrait),sunX=portrait?125:250,eyeX=portrait?390:700,rainX=portrait?720:1250;
 const behind=smooth(t,marks.behind??Infinity,(marks.behind??Infinity)+.45),rain=smooth(t,marks.rain??Infinity,(marks.rain??Infinity)+.45);
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%"><Defs/>
  <rect x="15" y="25" width={w-30} height="680" rx="35" fill="url(#rainbow-sky)"/>
  <Sun x={sunX} y={225} r={portrait?55:68}/><Observer x={eyeX} y={330} size={1.35}/>
  {Array.from({length:24},(_,i)=><Drop key={i} x={rainX-95+(i%4)*60} y={210+Math.floor(i/4)*70+((i%2)*17)} size={portrait?13:16} opacity={.55+.35*rain}/>)}
  <g opacity={.2+.8*behind}>{[175,225,275].map((y,i)=><path key={i} d={`M${sunX+85} ${y}H${rainX+95}`} stroke={P.ivory} strokeWidth="5" markerEnd="url(#rain-arrow)"/>)}</g>
  <path d={`M${eyeX+35} 330L${rainX-70} 250`} stroke={P.cyan} strokeWidth="5" strokeDasharray="9 12" opacity={rain}/>
  {labels.map((a,i)=><Label key={i} {...a}/>)}
  <Label x={portrait?370:720} y={690} text="Look away from the Sun" size={portrait?42:56}/>
 </svg>;
}
function Droplet({portrait,t,marks}:VisualProps){
 const w=portrait?900:1600,q=displayRay(1.331,portrait),enter=smooth(t,marks.enter??Infinity,(marks.enter??Infinity)+.65),bounce=smooth(t,marks.reflect??Infinity,(marks.reflect??Infinity)+.55),leave=smooth(t,marks.leave??Infinity,(marks.leave??Infinity)+.65),spread=smooth(t,marks.dispersion??Infinity,(marks.dispersion??Infinity)+.7);
 const full=[q.start,q.entry,q.reflection,q.exit,q.end],packet=polylinePoint(full,((t*.16)%1+1)%1),detail=exitDetail(portrait),frame=detail.frame;
 const tag=(x:number,y:number,n:number)=> <g><circle cx={x} cy={y} r="24" fill="#fff2cd"/><text x={x} y={y+9} textAnchor="middle" fontSize="28" fontWeight="800" fill="#22354c">{n}</text></g>;
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%"><Defs/>
  <circle cx={q.cx} cy={q.cy} r={q.r} fill="url(#drop-glass)" stroke="#b9f0f2" strokeWidth="5"/>
  <ellipse cx={q.cx-70} cy={q.cy-95} rx="65" ry="26" fill="#c4fcff" opacity=".16" transform={`rotate(-38 ${q.cx-70} ${q.cy-95})`}/>
  <path d={path([q.start,q.entry])} stroke={P.ivory} strokeWidth="9" fill="none" markerEnd="url(#rain-arrow)"/>
  {spectrum.filter((_,i)=>i%4===0).map((s,i)=>{const r=displayRay(s.n,portrait),colour=spread?s.colour:P.ivory;return <g key={i} opacity={spread?.83:(i===0?.95:0)}>
   <path d={path([r.entry,r.reflection])} stroke={colour} strokeWidth={spread?3.4:7} fill="none" pathLength="1" strokeDasharray="1" strokeDashoffset={1-enter}/>
   <path d={path([r.reflection,r.exit])} stroke={colour} strokeWidth={spread?3.4:7} fill="none" pathLength="1" strokeDasharray="1" strokeDashoffset={1-bounce}/>
   <path d={path([r.exit,r.end])} stroke={colour} strokeWidth={spread?3.4:7} fill="none" pathLength="1" strokeDasharray="1" strokeDashoffset={1-leave}/>
  </g>})}
  {enter>0&&tag(q.entry.x-25,q.entry.y-28,1)}{bounce>0&&tag(q.reflection.x+28,q.reflection.y,2)}{leave>0&&tag(q.exit.x+20,q.exit.y+27,3)}
  {leave>0&&<circle cx={packet.x} cy={packet.y} r="9" fill={P.ivory} opacity=".85"/>}
  <Label x={portrait?170:410} y={80} text="Sunlight" size={portrait?48:62}/>
  <Label x={portrait?710:1250} y={100} text="Water drop" size={portrait?43:62}/>
  {spread===0&&<Label x={leave>0?(portrait?180:480):(portrait?535:930)} y={leave>0?590:700} text={leave>0?'3  Bend out':bounce>0?'2  Some light reflects':enter>0?'1  Bend in':'Enlarged view'} size={portrait?44:58}/>}
  {spread>0&&<g opacity={spread} aria-label="Eight-times spatial magnification of the same computed exit rays; no angle exaggeration">
   <rect {...detail.source} fill="none" stroke={P.cyan} strokeWidth="2.5"/>
   <path d={`M${detail.source.x+detail.source.width} ${detail.centre.y}L${frame.x} ${detail.target.y+detail.target.height/2}`} fill="none" stroke={P.cyan} strokeWidth="2.5" strokeDasharray="7 9"/>
   <rect {...frame} rx="16" fill="#163048" stroke="#88cbd7" strokeWidth="2"/>
   <Label x={frame.x+frame.width/2} y={portrait?410:285} text="Exit ×8" size={portrait?36:50}/>
   <defs><clipPath id="exit-detail-crop"><rect {...detail.target}/></clipPath></defs>
   <g clipPath="url(#exit-detail-crop)">{spectrum.filter((_,i)=>i%4===0).map((s,i)=>{const r=displayRay(s.n,portrait);return <path key={i} d={path([magnifiedExitPoint(r.exit,detail),magnifiedExitPoint(r.end,detail)])} fill="none" stroke={s.colour} strokeWidth="4"/>})}</g>
   <Label x={frame.x+frame.width/2} y={portrait?665:635} text="Red" colour="#ff929a" size={portrait?43:56}/>
   <Label x={frame.x+frame.width/2} y={portrait?725:710} text="Violet" colour="#c6adff" size={portrait?43:56}/>
  </g>}
 </svg>;
}
function Cone({portrait,t,marks}:VisualProps){
 const w=portrait?900:1600,g=coneSlice(portrait),axis=smooth(t,marks.axis??Infinity,(marks.axis??Infinity)+.6),angle=smooth(t,marks.angle??Infinity,(marks.angle??Infinity)+.5),violet=smooth(t,marks.violet??Infinity,(marks.violet??Infinity)+.5),cone=smooth(t,marks.cone??Infinity,(marks.cone??Infinity)+.6),many=smooth(t,marks.many??Infinity,(marks.many??Infinity)+.5),labels=coneLabels(portrait),violetRadius=330*Math.tan(40*Math.PI/180);
 const arc=arcPoints(g.eye.x,g.eye.y,112,-42,0,32);
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%"><Defs/>
  <path d={`M${g.eye.x} ${g.eye.y}L${g.upper.x} ${g.upper.y}A75 ${g.radius} 0 0 1 ${g.lower.x} ${g.lower.y}Z`} fill="#7bd8d0" fillOpacity={.08*cone} stroke="none"/>
  <ellipse cx={g.plane.x} cy={g.plane.y} rx="75" ry={g.radius} fill="none" stroke="#b7d5df" strokeWidth="3" strokeDasharray="8 10" opacity={cone}/>
  <path d={`M${g.eye.x} ${g.eye.y}H${portrait?850:1450}`} stroke={P.ivory} strokeWidth="4" strokeDasharray="12 12" opacity={axis} markerEnd="url(#rain-arrow)"/>
  <path d={path([g.upper,g.eye])} stroke="#ff7a83" strokeWidth="6" fill="none" opacity={angle} markerEnd="url(#rain-red-arrow)"/>
  <path d={path([g.eye,g.lower])} stroke="#ff7a83" strokeWidth="5" fill="none" opacity={cone}/>
  <path d={`M${g.plane.x} ${g.plane.y-violetRadius}L${g.eye.x} ${g.eye.y}`} stroke="#b49cff" strokeWidth="5" fill="none" opacity={violet} markerEnd="url(#rain-violet-arrow)"/>
  <path d={path(arc)} stroke={P.gold} strokeWidth="5" fill="none" opacity={angle}/>
  <Observer x={g.eye.x} y={g.eye.y} size={.86}/>
  {Array.from({length:25},(_,i)=>{const a=i/25*Math.PI*2;return <g key={i}><Drop x={g.plane.x+Math.cos(a)*75} y={g.plane.y+Math.sin(a)*g.radius} size={9} colour="#ff929a" opacity={many}/><Drop x={g.plane.x+Math.cos(a)*70} y={g.plane.y+Math.sin(a)*violetRadius} size={7} colour="#b49cff" opacity={many*violet}/></g>})}
  <Label {...labels[0]}/>{axis>0&&<Label {...labels[4]}/>}{angle>0&&<><Label {...labels[1]}/><Label {...labels[2]} colour="#ffb1ab"/></>}{violet>0&&<Label {...labels[3]} colour="#cab7ff"/>}
 </svg>;
}
function Moving({portrait,t,marks}:VisualProps){
 const w=portrait?900:1600,progress=smooth(t,marks.move??Infinity,(marks.move??Infinity)+2.6),eye=movingEye(progress),change=smooth(t,marks.different??Infinity,(marks.different??Infinity)+.55),cx=w/2,cy=545,k=portrait?.85:1.25,points=fixedDropField(),radius=390*Math.tan(42*Math.PI/180)*k;
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%"><Defs/>
  <rect x="15" y="20" width={w-30} height="560" rx="32" fill="url(#rainbow-sky)"/>
  <g aria-label="Fixed rain plane; observer changes position, not the droplets' coordinates">{points.map((p,i)=>{const s=dropLight(eye,p);return <Drop key={i} x={cx+p.x*k} y={cy+p.y*k} size={s.selected?8:5} colour={s.selected?s.colour:'#aacbd0'} opacity={s.selected?.95:.17}/>})}</g>
  <Rainbow cx={cx+eye.x*k} cy={cy} r={radius} width={22} opacity={.26}/>
  <path d={`M30 580H${w-30}`} stroke="#81a8ac" strokeWidth="3"/>
  <Label x={w/2} y={portrait?70:80} text="Fixed rain field" size={portrait?43:58}/>
  <rect x={portrait?110:320} y="610" width={portrait?680:960} height="135" rx="22" fill="#173849" stroke="#6aa6af" strokeWidth="2"/>
  <path d={`M${cx-160} 680H${cx+160}`} stroke={P.ivory} strokeWidth="4" markerEnd="url(#rain-arrow)"/>
  <Observer x={cx+eye.x*k} y={632} size={.50}/>
  <Label x={portrait?230:440} y={718} text="You move" size={portrait?40:52}/>
 </svg>;
}
function Circle({portrait,t,marks}:VisualProps){
 const w=portrait?900:1600,cx=w/2,cy=370,r=portrait?292:310,reveal=circleReveal(t,marks),ground=smooth(t,marks.ground??Infinity,(marks.ground??Infinity)+.5);
 const maskY=mix(405,740,reveal);
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%"><Defs/>
  <rect x="12" y="12" width={w-24} height="722" rx="35" fill="url(#rainbow-sky)"/>
  <Rainbow {...{cx,cy,r}} start={0} end={360}/>
  <g>{Array.from({length:18},(_,i)=>{const a=i/18*Math.PI*2;return <Drop key={i} x={cx+Math.cos(a)*(r-16)} y={cy+Math.sin(a)*(r-16)} size={9} opacity=".6"/>})}</g>
  <rect x="12" y={maskY} width={w-24} height={Math.max(0,734-maskY)} rx="15" fill="url(#rainbow-land)"/>
  {reveal<.99&&<><path d={`M25 ${maskY}H${w-25}`} stroke="#a3c9be" strokeWidth="4"/><Label x={portrait?450:800} y={650} text={ground>0?'The ground hides this part':'A circle can be partly hidden'} size={portrait?40:58}/></>}
  <circle cx={cx} cy={cy} r="7" fill={P.ivory}/><path d={`M${cx-25} ${cy}H${cx+25}M${cx} ${cy-25}V${cy+25}`} stroke={P.ivory} strokeWidth="2" opacity=".6"/>
  {reveal>.3&&<Label x={w/2} y={portrait?730:725} text="Unobstructed elevated view" size={portrait?43:58}/>}
 </svg>;
}
function Body(p:Props){
 const {width,height,fps}=useVideoConfig(),portrait=height>width,l=assertLayout(portrait),time=useCurrentFrame()/fps,s=p.scenes.find(s=>time>=s.start&&time<s.end)||p.scenes.at(-1);if(!s)return null;
 const kind=s.scene,t=time-s.start,marks=s.marks||{},cue=p.captions.find(c=>time>=c.start&&time<c.end),rect=(r:any)=>({position:'absolute' as const,left:r.x,top:r.y,width:r.width,height:r.height});
 const a={portrait,t,marks};let visual:React.ReactNode;
 if(kind==='question'||kind==='callback')visual=<Opening {...a} callback={kind==='callback'}/>;else if(kind==='conditions')visual=<Conditions {...a}/>;else if(kind==='droplet')visual=<Droplet {...a}/>;else if(kind==='cone')visual=<Cone {...a}/>;else if(kind==='move')visual=<Moving {...a}/>;else visual=<Circle {...a}/>;
 return <AbsoluteFill style={{background:'radial-gradient(ellipse at 12% 28%,#40355b 0%,#1c344e 48%,#112437 100%)',fontFamily:'Arial,sans-serif',color:P.ivory}}>
  <div style={{...rect(l.heading),fontSize:l.headingFont,lineHeight:1.08,fontWeight:750,whiteSpace:'pre-line'}}>{headingFor(kind,portrait)}</div>
  <div style={rect(l.diagram)}>{visual}</div>
  <div style={{...rect(l.support),fontSize:portrait?38:43,lineHeight:1.15,color:P.muted}}>{supportText(kind,t,marks)}</div>
  {cue&&p.burnCaptions&&<div style={{...rect(l.captions),display:'flex',alignItems:'center',justifyContent:'center',padding:16,background:'rgba(9,16,29,.95)',borderRadius:14,fontSize:l.captionFont,lineHeight:1.2,textAlign:'center'}}>{cue.text}</div>}
  <BrandWatermark placement={portrait?l.watermark:undefined} occupiedRects={[l.heading,l.diagram,l.support,l.captions]}/>
 </AbsoluteFill>;
}
function Film(p:Props){const {width,height,fps}=useVideoConfig(),n=bodyFrameCount(p.duration,fps);return <AbsoluteFill><Sequence durationInFrames={n}><Body {...p}/></Sequence>{p.outro&&<Sequence from={n} durationInFrames={90}>{height>width?<AbsoluteFill style={{background:'#fff9ed'}}><OffthreadVideo muted src={staticFile('outro-portrait.mp4')} style={{position:'absolute',left:80,top:270,width:820,height:1230,objectFit:'contain'}}/></AbsoluteFill>:<OffthreadVideo muted src={staticFile('outro-landscape.mp4')} style={{width,height}}/>}</Sequence>}</AbsoluteFill>}
const Clean=(p:Props)=><Film {...p} burnCaptions={false}/>;
const Captioned=(p:Props)=><Film {...p} burnCaptions/>;
function Cover(){const {width,height}=useVideoConfig(),p=height>width,cx=p?540:1210,cy=p?1370:880,r=p?455:640;return <AbsoluteFill style={{background:'radial-gradient(ellipse at 25% 20%,#6c5378,#244963 52%,#15283f)',fontFamily:'Arial,sans-serif',color:P.ivory}}>
 <div style={{position:'absolute',left:p?90:100,top:p?390:100,width:p?900:800,fontSize:p?130:130,lineHeight:1.02,fontWeight:800}}>CAN YOU<br/>REACH IT?</div>
 <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%"><Defs/><Rainbow cx={cx} cy={cy} r={r} width={p?58:62}/><path d={`M${p?60:560} ${cy+20}Q${cx} ${cy-70} ${width-40} ${cy+20}V${height}H0Z`} fill="#173c48"/><Rainbow cx={cx} cy={cy} r={r} width={p?58:62}/><Observer x={p?260:440} y={p?1420:750} size={p?1.2:1.1}/><path d={`M${p?350:530} ${p?1560:920}H${p?620:870}`} stroke={P.ivory} strokeWidth="8" markerEnd="url(#rain-arrow)"/></svg>
 <BrandWatermark surface="cover"/>
 </AbsoluteFill>}
const defaults:Props={duration:90,scenes:[],captions:[],outro:true,burnCaptions:false};
registerRoot(()=> <>{(['Landscape','Shorts','CleanShorts'] as const).map(f=><Composition key={f} id={'Rainbow'+f} component={f==='CleanShorts'?Clean:f==='Shorts'?Captioned:Film} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={2790} defaultProps={defaults} calculateMetadata={({props})=>({durationInFrames:bodyFrameCount(props.duration,30)+(props.outro?90:0)})}/>)}{(['Landscape','Shorts'] as const).map(f=><Composition key={f} id={'Cover'+f} component={Cover} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={1}/>)}</>);
