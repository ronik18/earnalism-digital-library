import React from 'react';
import {AbsoluteFill,Composition,Sequence,OffthreadVideo,registerRoot,useCurrentFrame,useVideoConfig,staticFile} from 'remotion';
import {BrandWatermark} from '../src/BrandWatermark';
import {assertLayout,bodyFrameCount,palette as P,smooth,vaporPath,dropletPoint,wholeDropPoint,coalescedDrop,sourceFootnote,supportText,openingWallVisible,liquidRecallAnchor,portraitCondition,sceneKinds} from './layout.mjs';
type Props={duration:number;scenes:any[];captions:any[];outro?:boolean;burnCaptions?:boolean};
const titles:any={question:'Where did the water\ncome from?',source:'The source is in the air.',cooling:'Cool the air beside the glass.',droplets:'Gas becomes liquid.',conditions:'Cold alone is not enough.',callback:'It came from the air.'};
function Drop({x,y,r=15,opacity=1}:any){return <g transform={`translate(${x} ${y})`} opacity={opacity}><path d={`M0 ${-r*1.3}C${-r*.25} ${-r*.6} ${-r} 0 ${-r} ${r*.35}A${r} ${r} 0 0 0 ${r} ${r*.35}C${r} 0 ${r*.25} ${-r*.6} 0 ${-r*1.3}Z`} fill="url(#drop)" stroke="#d5ffff" strokeWidth="2"/><ellipse cx={-r*.3} cy={r*.15} rx={r*.14} ry={r*.3} fill="#fff" opacity=".8"/></g>}
function Defs(){return <defs><linearGradient id="glass" x1="0" y1="0" x2="1" y2=".5"><stop stopColor="#b9fbff" stopOpacity=".28"/><stop offset=".4" stopColor="#98e9fa" stopOpacity=".05"/><stop offset="1" stopColor="#d9ffff" stopOpacity=".27"/></linearGradient><linearGradient id="drink" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#e9b46d"/><stop offset="1" stopColor="#a05b47"/></linearGradient><radialGradient id="drop"><stop stopColor="#e9ffff" stopOpacity=".8"/><stop offset=".55" stopColor="#5ec8de" stopOpacity=".65"/><stop offset="1" stopColor="#b9f7ff" stopOpacity=".9"/></radialGradient><marker id="heat" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="3" markerHeight="3" orient="auto"><path d="M0 0L10 5L0 10Z" fill={P.amber}/></marker></defs>}
// Intact wall and exterior drops share fixed coordinates across wide/close views.
function Glass({wet=0,vapor=0,drift=0}:any){return <g>
 <ellipse cx="410" cy="635" rx="205" ry="25" fill="#0a0910" opacity=".5"/>
 <path d="M270 120L290 600Q410 644 530 600L550 120Z" fill="url(#glass)" stroke="#c7f6ff" strokeWidth="5"/>
 <path d="M288 285L304 588Q410 620 516 588L532 285Z" fill="url(#drink)" opacity=".88"/>
 <ellipse cx="410" cy="285" rx="122" ry="21" fill="#f1c58a" opacity=".9"/>
 {[0,1,2].map(i=><rect key={i} x={315+i*60} y={220+(i%2)*14} width="66" height="65" rx="12" fill="#d7fdff" opacity=".64" stroke="#fff7e9" strokeWidth="3" transform={`rotate(${i*13-12} ${345+i*60} 253)`}/>)}
 <ellipse cx="410" cy="120" rx="140" ry="24" fill="#35263b" fillOpacity=".8" stroke="#d6ffff" strokeWidth="5"/>
 <path d="M286 154L303 575" stroke="#fff" strokeWidth="8" opacity=".25" strokeLinecap="round"/>
 {Array.from({length:6},(_,i)=>{const d=wholeDropPoint(i);return <Drop key={i} x={d.x} y={d.y} r={d.r} opacity={wet*smooth(wet, i*.10, i*.10+.25)}/>})}
 {Array.from({length:6},(_,i)=>{const v=vaporPath(i,drift);return <g key={i} opacity={vapor}><circle cx={v.x} cy={v.y} r="10" fill={P.water}/><circle cx={v.x+12} cy={v.y-6} r="4" fill={P.ivory}/></g>})}
 </g>}
function Heat({t=0}:any){const x=760-(t%2)/2*175;return <g><path d="M780 400H573" stroke={P.amber} strokeWidth="9" markerEnd="url(#heat)"/><circle cx={x} cy="400" r="8" fill={P.ivory}/><text x="690" y="360" textAnchor="middle" fill={P.amber} fontSize="52" fontWeight="700">Heat</text></g>}
function Whole({portrait,kind,t,marks,cover=false}:any){const w=portrait?900:1600;let wet=cover?1:kind==='question'?smooth(t,marks.drops??Infinity,(marks.drops??Infinity)+2):kind==='callback'?smooth(t,(marks.air??Infinity),(marks.air??Infinity)+2):1;
 const source=kind==='source',callback=kind==='callback';const v=source?smooth(t,marks.symbols??Infinity,(marks.symbols??Infinity)+1):callback?smooth(t,marks.air??Infinity,(marks.air??Infinity)+.6):0;
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%" aria-label="An intact glass with condensation on its outside; schematic water vapor originates in the external air"><Defs/>
 <g transform={portrait?'translate(0 20)':'translate(40 10)'}><Glass wet={source?0:wet} vapor={v} drift={callback?smooth(t,marks.air??Infinity,(marks.visible??Infinity)):0}/></g>
 {!portrait&&openingWallVisible(kind,t,marks)&&<g><text x="1030" y="250" textAnchor="middle" fill={P.ivory} fontSize="66" fontWeight="700">{source?'Water vapor':callback?'Outside the glass':'Intact glass wall'}</text><text x="1030" y="330" textAnchor="middle" fill={P.water} fontSize="56">{source?'Invisible gas':callback?'From the air':'No leak path'}</text>{source&&v>0&&<text x={sourceFootnote.x} y={sourceFootnote.y} textAnchor="middle" fill={P.muted} fontSize={sourceFootnote.fontSize}>{sourceFootnote.text}</text>}{callback&&<path d="M1060 475Q850 600 610 420" stroke={P.water} strokeWidth="6" fill="none" strokeDasharray="12 12"/>}</g>}
 {portrait&&source&&t>=(marks.invisible??Infinity)&&<text x="450" y="725" textAnchor="middle" fill={P.water} fontSize="52">Invisible gas · symbolic dots</text>}
 </svg>}
function TemperatureScale({x,y,below,showDew=true,drier=false,airProgress=null}:any){const sy=y+185,dy=drier?y+260:y+125;return <g>
 <path d={`M${x} ${y}V${y+305}`} stroke="#90849e" strokeWidth="8" strokeLinecap="round"/>
 {showDew&&<><path d={`M${x-25} ${dy}H${x+25}`} stroke={P.amber} strokeWidth="7"/><text x={x+45} y={dy+14} fill={P.amber} fontSize="44">Dew point</text></>}
 {airProgress!==null&&<><path d={`M${x-45} ${y+35}V${y+125}`} stroke={P.amber} strokeWidth="5"/><circle cx={x-45} cy={y+35+90*airProgress} r="12" fill={P.amber}/><text x={x-65} y={y+45} textAnchor="end" fill={P.amber} fontSize="44">Air</text></>}<circle cx={x} cy={sy} r="13" fill={P.cold}/><text x={x+45} y={sy+14} fill={P.cold} fontSize="44">Glass</text>
 </g>}
function Patch({portrait,t,marks,kind}:any){const droplets=kind==='droplets',at=marks.liquid??Infinity;const wet=droplets?smooth(t,at,at+2):0;const p=droplets?smooth(t,at,at+3):0;const w=portrait?900:1600;
 return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%" aria-label="Schematic exterior wall: heat transfers into colder glass, and outside vapor forms liquid only after the below-dew-point condition"><Defs/>
 <g transform={portrait?'translate(0 20)':'translate(40 0)'}>
 <rect x="175" y="140" width="265" height="480" rx="18" fill="#8ddbe8" fillOpacity=".14"/>
 <rect x="440" y="140" width="100" height="480" rx="8" fill="url(#glass)" stroke="#bdeefa" strokeWidth="4"/>
 <text x="310" y="100" textAnchor="middle" fill={P.cold} fontSize="54">Colder side</text>
 <text x="697" y="100" textAnchor="middle" fill={P.ivory} fontSize="54">Outside air</text>
 {Array.from({length:6},(_,i)=>{const v=vaporPath(i,p);return <circle key={i} cx={v.x} cy={v.y} r={10} fill={P.water} opacity={droplets?1-wet*.8:.8}/>})}
 {t>=(marks.heat??0)&&!droplets&&<Heat t={t}/>}
 {droplets&&Array.from({length:6},(_,i)=>{const d=coalescedDrop(i,smooth(t,marks.join??Infinity,(marks.join??Infinity)+2));return <Drop key={i} {...d} opacity={wet*d.opacity}/>})}
 <text x="490" y="685" textAnchor="middle" fill={P.muted} fontSize="49">Intact glass wall</text>
 </g>
 {!portrait&&<g><TemperatureScale x={1040} y={210} below showDew={droplets||t>=(marks.dewpoint??Infinity)} airProgress={droplets?null:smooth(t,marks.heat??Infinity,marks.dewpoint??Infinity)}/><text x="1230" y="150" textAnchor="middle" fill={P.ivory} fontSize="62">{droplets?'Below dew point':'Cooling beside the wall'}</text><text x="1220" y="640" textAnchor="middle" fill={P.water} fontSize="48">{droplets?'Gas → liquid':'Qualitative temperature scale'}</text></g>}

 </svg>}
function Conditions({portrait,t,marks}:any){const drier=t>=(marks.drier??Infinity),w=portrait?900:1600,recall=portraitCondition(t,marks);const panels=portrait?[{x:40,y:40,dry:recall.dry}]:[{x:30,y:80,dry:false},{x:820,y:80,dry:true}];return <svg viewBox={`0 0 ${w} 760`} width="100%" height="100%" aria-label="Same glass temperature, two different dew points: more humid air forms drops; drier air can leave the glass dry"><Defs/>{panels.map(({x,y,dry})=><g key={String(dry)} transform={`translate(${x} ${y})`} opacity={dry&&!drier?.16:1}>
 <rect width={portrait?820:750} height="650" rx="28" fill={dry?'#38304e':'#173f48'} stroke={dry?'#bc9cd9':'#78cbd5'} strokeWidth="3"/>
 <text x={portrait?410:375} y="70" textAnchor="middle" fill={P.ivory} fontSize="58" fontWeight="700">{portrait&&recall.recall?'Liquid-water example':dry?'Drier air':'More humid air'}</text>
 <g transform="translate(-95 60) scale(.65)"><Glass wet={dry?0:1}/></g>
 <TemperatureScale x={portrait?420:360} y={180} below showDew drier={dry}/>
 <text x={portrait?410:375} y="590" textAnchor="middle" fill={dry?P.muted:P.water} fontSize="52">{dry?'Can stay dry':'Drops grow'}</text>
 </g>)}</svg>}

function Body(p:Props){const {width,height,fps}=useVideoConfig(),portrait=height>width,l=assertLayout(portrait),time=useCurrentFrame()/fps;const s=p.scenes.find(s=>time>=s.start&&time<s.end)||p.scenes.at(-1);if(!s)return null;const kind=s.scene,t=time-s.start,marks=s.marks||{},cue=p.captions.find(c=>time>=c.start&&time<c.end);const rect=(r:any)=>({position:'absolute' as const,left:r.x,top:r.y,width:r.width,height:r.height});const support=supportText(kind,t,marks);
 return <AbsoluteFill style={{background:'radial-gradient(ellipse at 23% 34%,#433451 0%,#1d263a 53%,#101929 100%)',color:P.ivory,fontFamily:'Arial,sans-serif'}}><div style={{...rect(l.heading),fontSize:l.headingFont,fontWeight:750,lineHeight:1.08,whiteSpace:'pre-line'}}>{titles[kind]}</div><div style={rect(l.diagram)}>{['question','source','callback'].includes(kind)?<Whole {...{portrait,kind,t,marks}}/>:kind==='conditions'?<Conditions {...{portrait,t}} marks={{...marks,liquid_recall:liquidRecallAnchor(p.captions,s.start)}}/>:<Patch {...{portrait,t,marks,kind}}/>}</div><div style={{...rect(l.support),fontSize:portrait?40:43,lineHeight:1.15,color:P.muted}}>{support}</div>{cue&&p.burnCaptions&&<div style={{...rect(l.captions),display:'flex',alignItems:'center',justifyContent:'center',background:'rgba(8,13,26,.94)',padding:16,borderRadius:14,fontSize:l.captionFont,lineHeight:1.2,textAlign:'center'}}>{cue.text}</div>}<BrandWatermark/></AbsoluteFill>}
function Film(p:Props){const {fps,width,height}=useVideoConfig(),n=bodyFrameCount(p.duration,fps);return <AbsoluteFill><Sequence durationInFrames={n}><Body {...p}/></Sequence>{p.outro&&<Sequence from={n} durationInFrames={90}><OffthreadVideo muted src={staticFile(height>width?'outro-portrait.mp4':'outro-landscape.mp4')} style={{width,height}}/></Sequence>}</AbsoluteFill>}
const Clean=(p:Props)=><Film {...p} burnCaptions={false}/>;const Captioned=(p:Props)=><Film {...p} burnCaptions/>;
function Cover(){const {height,width}=useVideoConfig(),p=height>width;return <AbsoluteFill style={{background:'radial-gradient(ellipse at 40% 45%,#514361,#14273a 75%)',fontFamily:'Arial,sans-serif',color:P.ivory}}><div style={{position:'absolute',left:p?85:110,top:p?310:110,fontSize:p?104:125,fontWeight:800,lineHeight:1.04}}>A DRY GLASS.<br/><span style={{color:P.water}}>THEN THIS.</span></div><div style={{position:'absolute',left:p?20:900,top:p?740:225,width:p?1000:930,height:p?920:790}}><Whole portrait kind="question" t={0} marks={{}} cover/></div><BrandWatermark surface="cover"/></AbsoluteFill>}
const defaults:Props={duration:90,scenes:[],captions:[],outro:true,burnCaptions:false};
registerRoot(()=> <>{(['Landscape','Shorts','CleanShorts'] as const).map(f=><Composition key={f} id={'Condensation'+f} component={f==='CleanShorts'?Clean:f==='Shorts'?Captioned:Film} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={2790} defaultProps={defaults} calculateMetadata={({props})=>({durationInFrames:bodyFrameCount(props.duration,30)+(props.outro?90:0)})}/>)}{(['Landscape','Shorts'] as const).map(f=><Composition key={f} id={'Cover'+f} component={Cover} width={f==='Landscape'?1920:1080} height={f==='Landscape'?1080:1920} fps={30} durationInFrames={1}/>)}</>);
