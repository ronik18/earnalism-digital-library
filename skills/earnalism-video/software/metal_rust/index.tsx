import React,{useLayoutEffect,useRef} from 'react';
import {AbsoluteFill,Composition,registerRoot,useCurrentFrame,useVideoConfig} from 'remotion';
import {BrandWatermark} from '../src/BrandWatermark';
import contract from './contract.json';
import {layout,stateFor,oxygenContact,validateProps,bodyFrameCount} from './layout.mjs';

const headings:any={gate:'Why does iron turn orange?',wet:'Rain and air reach bare iron.',rust:'The iron itself changes.',salt:'Salt can speed the change.',paint:'An intact barrier helps.',callback:'Rust comes from iron.'};
const css=(r:any)=>({position:'absolute' as const,left:r.x,top:r.y,width:r.width,height:r.height});
function Reading({region,children,style}:any){
 const box=useRef<HTMLDivElement>(null),ink=useRef<HTMLSpanElement>(null);
 useLayoutEffect(()=>{if(!box.current||!ink.current)return;const a=box.current.getBoundingClientRect(),b=ink.current.getBoundingClientRect();
  if(b.left<a.left-.5||b.top<a.top-.5||b.right>a.right+.5||b.bottom>a.bottom+.5)throw Error('Actual Rust text exceeds its destination reading region; reflow before delivery');
 },[children,region.width,region.height]);
 return <div ref={box} style={{...css(region),display:'flex',alignItems:'center',...style}}><span ref={ink} style={{maxWidth:'100%',boxSizing:'border-box'}}>{children}</span></div>;
}
function Metal({x,y,w,h,paint=false,scratch=0,rust=0}:any){
 const scratchPath=`M${x+w*.48},${y+h*.15}l${w*.12},${h*.22}l${-w*.16},${h*.24}l${w*.14},${h*.22}`;
 return <g><rect x={x+12} y={y+13} width={w} height={h} rx={w*.15} fill="#082d35" opacity=".45"/>
 <rect x={x} y={y} width={w} height={h} rx={w*.15} fill={paint?'url(#paint)':'url(#metal)'} stroke="#d9e4d9" strokeWidth="3"/>
 <path d={`M${x+w*.16},${y+15}V${y+h-15}`} stroke="#f0ffff" strokeWidth="5" opacity=".4"/>
 <defs><clipPath id="exposed-scratch"><path d={scratchPath} stroke="white" strokeWidth="12" fill="none"/></clipPath></defs>
 {scratch>0&&<path d={scratchPath} stroke="#a7b3b3" strokeWidth={12*scratch} fill="none"/>}
 <g clipPath={paint?'url(#exposed-scratch)':undefined}>{Array.from({length:19},(_,i)=>{const u=(i*37%83)/100,v=(i*23%79)/100;
  const cx=paint?x+w*(.48+.05*Math.sin(i)):x+w*(.19+u*.64),cy=y+h*(.18+v*.64);
  return <path key={i} d={`M${cx-10},${cy-13}q17,-13 28,4l-3,21q-20,9 -27,-4Z`} fill={i%2?'#d6893f':'#a5512a'} stroke="#f0b96d" strokeWidth="1.5" opacity={Math.min(1,Math.max(0,rust*22-i))}/>;})}</g>
 <ellipse cx={x+w*.5} cy={y+h*.10} rx={w*.12} ry={w*.08} fill="#d2d9c8" stroke="#567179" strokeWidth="4"/>
 <ellipse cx={x+w*.5} cy={y+h*.90} rx={w*.12} ry={w*.08} fill="#d2d9c8" stroke="#567179" strokeWidth="4"/>
 </g>;
}
function Picture({l,kind,state}:any){
 const W=l.picture.width,H=l.picture.height,p=l.portrait;
 const whole=['gate','callback'].includes(kind),s=l.subject;
 const hinge={x:s.x*W,y:s.y*H,w:s.width*W,h:s.height*H};
 const oxygenTarget=oxygenContact(hinge,state,H);
 const label=kind==='salt'?'Another wet area · with salt':kind==='paint'?(state.scratch>0?'Fresh scratch · exposed iron':'Clean iron · intact paint'):'';
 return <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{overflow:'hidden',borderRadius:24}}>
 <defs><linearGradient id="garden" x2="0" y2="1"><stop stopColor="#a8cfb5"/><stop offset=".6" stopColor="#377b70"/><stop offset="1" stopColor="#143f46"/></linearGradient>
 <linearGradient id="metal"><stop stopColor="#596d73"/><stop offset=".35" stopColor="#bdcfca"/><stop offset=".55" stopColor="#839799"/><stop offset="1" stopColor="#3e5964"/></linearGradient>
 <linearGradient id="paint"><stop stopColor="#177a79"/><stop offset=".4" stopColor="#62bea7"/><stop offset="1" stopColor="#176769"/></linearGradient>
 <linearGradient id="water" x2="0" y2="1"><stop stopColor="#c4ffff" stopOpacity=".55"/><stop offset="1" stopColor="#39c4df" stopOpacity=".3"/></linearGradient>
 <marker id="air" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="3" markerHeight="3" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#f4df96"/></marker></defs>
 <rect width={W} height={H} fill="url(#garden)"/>
 {[0,1,2,3,4,5].map(i=><g key={i} opacity=".45"><ellipse cx={(i*.19%1)*W} cy={H*.82} rx={W*.18} ry={H*.2} fill={i%2?'#b4c876':'#3e9c7d'}/><path d={`M${W*i/5},${H}Q${W*(i/5+.1)},${H*.5} ${W*(i/5+.17)},${H*.65}`} stroke="#c4d79a" strokeWidth="7" fill="none"/></g>)}
 {whole&&<g opacity=".75">{[0,1,2,3,4,5,6].map(i=><rect key={i} x={W*(.05+i*.145)} y={H*.15} width={W*.025} height={H*.8} rx="8" fill="url(#paint)"/>)}<path d={`M0 ${H*.3}H${W}M0 ${H*.74}H${W}`} stroke="#2d8c7e" strokeWidth={H*.055}/></g>}
 <Metal {...hinge} paint={state.paint} scratch={state.scratch} rust={whole ? .7 : state.rust}/>
 {!whole&&state.water>0&&<rect x={hinge.x-8} y={hinge.y+hinge.h*.15} width={hinge.w+16} height={hinge.h*.7} rx={hinge.w*.13} fill="url(#water)" opacity={state.water*.65}/>}
 {!whole&&state.oxygen>0&&<g opacity={state.oxygen}><path d={`M${W*.88},${H*.3}Q${W*.74},${H*.3} ${oxygenTarget[0]},${oxygenTarget[1]}`} stroke="#f4df96" strokeWidth="6" fill="none" markerEnd="url(#air)"/><text x={W*.72} y={H*.22} fontSize={p?34:38} fill="#fff6d8">Oxygen</text></g>}
 {whole&&<g><path d={`M${hinge.x+hinge.w*.69},${hinge.y+hinge.h*.28}q-20,28 0,44q22,-12 0,-44Z`} fill="#72e0ec" stroke="#e2ffff" strokeWidth="3"/></g>}
 {state.salt>0&&<g opacity={state.salt}><text x={W*.06} y={H*.2} fontSize={p?34:38} fill="#fff3ca">Dissolved salt</text><path d={`M${W*.17},${H*.25}Q${W*.25},${H*.4} ${hinge.x},${H*.47}`} stroke="#f4df96" strokeWidth="5" fill="none" markerEnd="url(#air)"/></g>}
 {label&&<text x={W*.04} y={H*.96} fontSize={p?26:30} fill="#fff8e7">{label}</text>}
 </svg>;
}
function Film(props:any){
 validateProps(props,contract);
 const {width,height,fps}=useVideoConfig(),frame=useCurrentFrame(),l=layout(width,height),seconds=Math.min(props.duration-1e-6,frame/fps);
 const scene=props.scenes.find((s:any)=>seconds>=s.start&&seconds<s.end)??props.scenes.at(-1);
 const state=stateFor(scene.scene,seconds-scene.start,scene.marks);
 const cue=props.captions.find((c:any)=>seconds>=c.start&&seconds<c.end);
 return <AbsoluteFill style={{background:'linear-gradient(#cfdfbf 0%,#9cc7b0 35%,#1c5558 75%,#0a303f 100%)',fontFamily:'Arial, sans-serif'}}>
  <BrandWatermark occupiedRects={l.occupied}/>
  <Reading region={l.heading} style={{fontSize:(l.portrait?53:60)*l.fontScale,fontWeight:700,lineHeight:1.06,color:'#103c43'}}>{headings[scene.scene]}</Reading>
  <div style={css(l.picture)}><Picture l={l} kind={scene.scene} state={state}/></div>
  <Reading region={l.qualifier} style={{fontSize:26*l.fontScale,color:'#d2e6d6'}}>Illustrative enlargement · change over time{scene.scene==='salt'?' · no fixed rate':''}</Reading>
  {props.burnCaptions&&cue&&<Reading region={l.captions} style={{justifyContent:'center',fontSize:(l.portrait?47:48)*l.fontScale,lineHeight:1.2,color:'#fff9ec',textAlign:'center'}}><span style={{display:'inline-block',background:'#092d3eea',padding:'12px 20px',borderRadius:14,boxSizing:'border-box',maxWidth:'100%'}}>{cue.text}</span></Reading>}
 </AbsoluteFill>;
}
const defaults:any={topic_id:contract.topic_id,source_sha256:contract.script_sha256,duration:1,scenes:[],words:[],captions:[],outro:false};
registerRoot(()=><>{['Landscape','Shorts','CleanShorts'].map(f=><Composition key={f} id={'MetalRust'+f} component={Film} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={1} defaultProps={defaults} calculateMetadata={({props})=>{validateProps(props,contract);return {durationInFrames:bodyFrameCount(props.duration)};}}/>)}</>);
