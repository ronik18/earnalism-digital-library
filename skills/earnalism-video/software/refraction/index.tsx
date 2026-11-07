import React from 'react';
import {AbsoluteFill,Composition,Sequence,OffthreadVideo,registerRoot,useCurrentFrame,useVideoConfig,staticFile} from 'remotion';
import {BrandWatermark} from '../src/BrandWatermark';
import {ray,virtualPoint,liftedSpoon} from './geometry.mjs';
const bg='#160e2b',ink='#fff5e8',gold='#ffcd72',violet='#e2b9ff',muted='#c1b7ca';
const titles:any={question:'Why does it look bent?',path:'Follow the light.',normal:'Which way does light bend?',image:'Where does the point appear?',spoon:'One spoon. A shifted image.',callback:'The spoon never bent.'};
const smooth=(t:number,a:number,b:number)=>{const x=Math.max(0,Math.min(1,(t-a)/(b-a)));return x*x*(3-2*x)};
const pt=(a:any)=>`${a[0]},${a[1]}`;
function direction(kind:string,t:number,marks:any){
 if(kind==='question')return t<2.9?['It looks bent.','Look at the waterline.']:t<7?['One straight spoon.','Copper = actual position']:['The path changes.','Follow the gold ray.'];
 if(kind==='path')return t<(marks.surface??5.86)?['From the submerged point','Light travels to the surface.']:t<(marks.refraction??11.28)?['Through water. Into air.','The direction changes.']:['Refraction','A change in the light’s path.'];
 if(kind==='normal')return t<4.7?['Water → air','Light travels faster.']:t<(marks.straight??9.82)?['Away from the normal','The dashed guide is perpendicular.']:['Straight through','No change of direction.'];
 if(kind==='image')return t<(marks.trace??4.3)?['Light reaches your eye.','Gold = actual light path']:['An apparent position','Violet dashes = backward tracing'];
 if(kind==='spoon')return t<3?['Above water: unchanged','Below water: shifted image']:['The two parts look misaligned.','The physical spoon is straight.'];
 return t<2.4?['Change the viewing angle.','The apparent position changes.']:t<5.86?['Lift it through the surface.','The apparent kink disappears.']:t<10.26?['Same spoon. Different light path.','A familiar view, explained.']:['Next question · planned','Why does metal feel colder?'];
}
function Diagram({kind,t,marks={},cover=false}:any){
 const {height,width}=useVideoConfig(),portrait=height>width;
 const eyeMove=kind==='callback'?smooth(t,.2,Math.max(.7,(marks.lift??2.4)-.3)):0;
 const eye:[number,number]=[500-180*eyeMove,-340-120*eyeMove],tip:[number,number]=[170,280];
 const lift=kind==='callback'?smooth(t,marks.lift??2.4,(marks.lift??2.4)+1.3):0;
 const r:any=ray(tip,eye),v:any=virtualPoint(tip,eye),spoon:any=liftedSpoon(eye,lift);
 const opening=kind==='question',openingWide=cover?0:smooth(t,6.55,7.45);
 const viewBox=opening?[-230-70*openingWide,-355-165*openingWide,820+230*openingWide,810+190*openingWide].join(' '):'-300 -520 1050 1000';
 const actualOpacity=cover?0:opening?.4*smooth(t,2.9,3.5):['image','spoon','callback'].includes(kind)?.42:1;
 const showImage=cover||['question','spoon','callback'].includes(kind)||(kind==='image'&&t>=(marks.trace??4.3));
 const showRays=!cover&&(['path','normal','image'].includes(kind)||(opening&&t>=(marks.path??7)));
 const showEye=!cover&&(!opening||t>=(marks.path??7));
 const surfaceReveal=kind==='path'?smooth(t,marks.surface??5.86,(marks.surface??5.86)+1.2):1;
 const lw=Math.hypot(r.surface[0]-tip[0],tip[1]),la=Math.hypot(eye[0]-r.surface[0],eye[1]);
 const split=1.333*lw/(1.333*lw+la),phase=(t*.38)%1,rayT=phase<split?phase/split:1+(phase-split)/(1-split);
 const light=rayT<1?[tip[0]+(r.surface[0]-tip[0])*rayT,tip[1]*(1-rayT)]:[r.surface[0]+(eye[0]-r.surface[0])*(rayT-1),eye[1]*(rayT-1)];
 const trace=kind==='image'?smooth(t,marks.trace??4.3,(marks.trace??4.3)+1.2):1;
 const labelSize=portrait?61:65;
 return <svg viewBox={viewBox} width="100%" height="100%" aria-label="Flat water-air interface: actual spoon in copper, apparent image in violet, actual light in gold">
 <defs>
 <linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#087d86" stopOpacity=".92"/><stop offset="1" stopColor="#073d59"/></linearGradient>
 <linearGradient id="metal"><stop stopColor="#ffe3b8"/><stop offset=".45" stopColor="#df9c61"/><stop offset="1" stopColor="#a55932"/></linearGradient>
 <radialGradient id="surface-glow"><stop stopColor={gold} stopOpacity=".16"/><stop offset="1" stopColor={gold} stopOpacity="0"/></radialGradient>
 <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill={gold}/></marker>
 </defs>
 <rect x="-320" y="0" width="1090" height="490" fill="url(#water)" rx="10"/>
 <path d="M-320 0H770" stroke="#5ed6dd" strokeWidth="3"/>
 {opening&&<ellipse cx="0" cy="0" rx="140" ry="140" fill="url(#surface-glow)" opacity={.7+.3*Math.sin(t*1.7)}/>}
 {!cover&&<><text x={opening?-200:-275} y="-30" fill={muted} fontSize={labelSize}>AIR</text><text x={opening?-200:-275} y="68" fill="#b4f5f2" fontSize={labelSize}>WATER</text></>}
 <g opacity={actualOpacity}>
 <path d={'M'+spoon.actual.map(pt).join(' L')} stroke="url(#metal)" strokeWidth="24" strokeLinecap="round" fill="none"/>
 <ellipse cx={spoon.bowl[0]} cy={spoon.bowl[1]} rx="33" ry="49" transform={`rotate(${spoon.bowlAngle} ${pt(spoon.bowl).replace(',',' ')})`} fill="url(#metal)"/>
 </g>
 {showImage&&<g>
 <path d={'M'+spoon.apparent.map(pt).join(' L')} stroke={violet} strokeWidth="24" strokeLinecap="round" fill="none"/>
 <ellipse cx={spoon.apparentBowl[0]} cy={spoon.apparentBowl[1]} rx="31" ry={spoon.bowl[1]>0?37:49} transform={`rotate(${spoon.bowlAngle} ${pt(spoon.apparentBowl).replace(',',' ')})`} fill={violet}/>
 </g>}
 {opening&&t>=2.9&&!cover&&<g opacity={smooth(t,2.9,3.5)*(1-smooth(t,6.4,7))}><path d="M210 275H360" stroke={gold} strokeWidth="2"/><text x="370" y="291" fill={gold} fontSize={labelSize-5}>Actual</text></g>}
 {showRays&&<g>
 <circle cx={tip[0]} cy={tip[1]} r="11" fill={gold}/>
 <path d={`M${pt(tip)}L${pt(r.surface)}`} stroke={gold} strokeWidth="6" fill="none" markerEnd="url(#arrow)"/>
 <path d={`M${pt(r.surface)}L${pt(eye)}`} stroke={gold} strokeWidth="6" fill="none" opacity={surfaceReveal} markerEnd="url(#arrow)"/>
 {kind==='path'&&(surfaceReveal>0||rayT<1)&&<circle cx={light[0]} cy={light[1]} r="11" fill={ink}/>}
 {kind==='normal'&&<g opacity={smooth(t,4.7,5.3)}>
 <path d={`M${r.surface[0]} -240V230`} stroke={muted} strokeWidth="3" strokeDasharray="12 10"/>
 <text x={r.surface[0]+24} y="220" fill={ink} fontSize={labelSize}>Normal</text>
 <path d={`M${r.surface[0]} -85 A85 85 0 0 1 ${r.surface[0]+85*Math.sin(r.thetaAir)} ${-85*Math.cos(r.thetaAir)}`} fill="none" stroke={violet} strokeWidth="6"/>
 {t>(marks.straight??9.82)&&<g><path d="M640 280V-215" stroke={gold} strokeWidth="6" markerEnd="url(#arrow)"/><text x="480" y="385" fill={ink} fontSize={labelSize}>No turn</text></g>}
 </g>}
 {kind==='image'&&trace>0&&<g opacity={trace}>
 <path d={`M${pt(r.surface)}L${pt(v)}`} stroke={violet} strokeWidth="5" strokeDasharray="12 10"/>
 <circle cx={v[0]} cy={v[1]} r="12" fill={violet}/>
 <path d={`M${v[0]+35} ${v[1]-25}H650`} stroke={violet} strokeWidth="2"/>
 <text x="405" y={v[1]-46} fill={violet} fontSize={labelSize}>Apparent</text>
 <text x="235" y="365" fill={gold} fontSize={labelSize}>Actual point</text>
 </g>}
 </g>}
 {showEye&&<g transform={`translate(${pt(eye).replace(',',' ')})`}><path d="M-48 0Q0 -38 48 0Q0 38 -48 0" fill={ink}/><circle r="14" fill="#087e82"/><circle r="7" fill={bg}/><text x={kind==='callback'?65:-35} y={kind==='callback'?18:-55} fill={ink} fontSize={labelSize}>Eye</text></g>}
 </svg>;
}
function Body(p:any){
 const {width,height,fps}=useVideoConfig(),time=useCurrentFrame()/fps,portrait=height>width;
 const scene=p.scenes.find((s:any)=>time>=s.start&&time<s.end)||p.scenes.at(-1);if(!scene)return <AbsoluteFill style={{background:bg}}/>;
 const kind=scene.scene,t=time-scene.start,marks=scene.marks||{},pair=direction(kind,t,marks),cue=p.captions?.find((c:any)=>time>=c.start&&time<c.end);
 return <AbsoluteFill style={{background:'radial-gradient(ellipse at 32% 36%, #342342 0%, #160e2b 72%)',color:ink,fontFamily:'Arial,sans-serif'}}>
 <div style={{position:'absolute',left:portrait?70:90,top:portrait?135:72,width:portrait?900:1550,fontSize:portrait?64:72,lineHeight:1.12,fontWeight:750}}>{titles[kind]}</div>
 <div style={{position:'absolute',left:portrait?72:94,top:portrait?305:176,fontSize:portrait?27:27,color:muted}}>Schematic · flat water surface · glass sides omitted</div>
 <div style={{position:'absolute',left:portrait?50:70,top:portrait?355:235,width:portrait?980:1240,height:portrait?900:660}}><Diagram kind={kind} t={t} marks={marks}/></div>
 <div style={{position:'absolute',left:portrait?76:1360,top:portrait?1285:410,width:portrait?880:455,fontSize:portrait?43:48,lineHeight:1.24,borderLeft:`4px solid ${gold}`,paddingLeft:24}}><div>{pair[0]}</div><div style={{color:violet,marginTop:18,fontSize:portrait?34:35}}>{pair[1]}</div></div>
 {cue&&p.burnCaptions&&<div style={{position:'absolute',left:portrait?78:180,right:portrait?88:180,top:portrait?1460:916,height:portrait?140:125,display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',fontSize:portrait?43:46,lineHeight:1.22,background:'rgba(7,8,20,.88)',padding:'10px 20px',borderRadius:12}}>{cue.text}</div>}
 <BrandWatermark/>
 </AbsoluteFill>;
}
function Film(p:any){const {fps,height,width}=useVideoConfig(),bodyFrames=Math.round((p.visualBodySeconds??p.duration)*fps);return <AbsoluteFill><Sequence durationInFrames={bodyFrames}><Body {...p}/></Sequence>{p.outro&&<Sequence from={bodyFrames} durationInFrames={90}><OffthreadVideo muted src={staticFile(height>width?'outro-portrait.mp4':'outro-landscape.mp4')} style={{width,height}}/></Sequence>}</AbsoluteFill>}
function Cover(){const {height,width}=useVideoConfig(),portrait=height>width;return <AbsoluteFill style={{background:'radial-gradient(ellipse at 45% 46%, #463051, #160e2b 78%)',color:ink,fontFamily:'Arial,sans-serif'}}>
 <div style={{position:'absolute',top:portrait?450:150,left:portrait?95:110,width:portrait?890:760,fontSize:portrait?105:104,fontWeight:800,lineHeight:1.04}}>STRAIGHT.<br/><span style={{color:gold}}>LOOKS BENT.</span></div>
 <div style={{position:'absolute',left:portrait?15:800,top:portrait?710:120,width:portrait?1050:1060,height:portrait?700:850}}><Diagram kind="question" t={0} cover/></div>
 <div style={{position:'absolute',left:portrait?100:115,top:portrait?1460:570,fontSize:portrait?35:42,letterSpacing:2,color:muted}}>FOLLOW THE LIGHT</div>
 <BrandWatermark surface="cover"/>
 </AbsoluteFill>}
const defaults={duration:100,scenes:[],captions:[],burnCaptions:true};
registerRoot(()=> <>{['Landscape','Shorts'].map(f=><Composition key={f} id={'Refraction'+f} component={Film} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={3000} defaultProps={defaults} calculateMetadata={({props})=>({durationInFrames:Math.round((props.visualBodySeconds??props.duration)*30)+(props.outro?90:0)})}/>)}{['Landscape','Shorts'].map(f=><Composition key={'cover'+f} id={'Cover'+f} component={Cover} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={1}/>)}</>);
