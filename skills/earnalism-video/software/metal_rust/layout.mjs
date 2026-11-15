import {watermarkLayout} from '../src/branding.mjs';
import {assertUiClear,reviewProfileForFrame,portraitReviewProfile,landscapeReviewProfile} from '../src/social-safe-area.mjs';
export const sceneKinds=Object.freeze(['gate','wet','rust','salt','paint','callback']);
export const smooth=x=>{x=Math.min(1,Math.max(0,x));return x*x*(3-2*x);};
export function bodyFrameCount(seconds,fps=30){
 if(typeof seconds!=='number'||!Number.isFinite(seconds)||seconds<=0||typeof fps!=='number'||!Number.isFinite(fps)||fps<=0||!Number.isSafeInteger(Math.ceil(seconds*fps)))throw Error('Finite actual body clock required');
 return Math.max(1,Math.ceil(seconds*fps));
}
export function layout(width,height){
 const portrait=height>width,base=portrait?portraitReviewProfile:landscapeReviewProfile;
 const profile=reviewProfileForFrame(width,height,base),sx=width/base.width,sy=height/base.height;
 const scale=r=>({x:r[0]*sx,y:r[1]*sy,width:r[2]*sx,height:r[3]*sy});
 const heading=scale(portrait?[76,395,824,108]:[90,174,1430,78]);
 const picture=scale(portrait?[76,535,824,685]:[90,275,1740,535]);
 const qualifier=scale(portrait?[76,1230,824,40]:[90,815,1740,36]);
 const captions=scale(portrait?[76,1285,824,195]:[150,875,1620,140]);
 const occupied=[heading,picture,qualifier,captions];
 occupied.forEach((r,i)=>assertUiClear(['heading','full picture/action/glow envelope','qualifier','captions'][i],r,profile));
 const brand=watermarkLayout(width,height,{occupiedRects:occupied});
 // Entire camera/action/arrow envelopes are clipped inside this occupied SVG.
 // Portrait deliberately uses a tall hinge; it is not a landscape postcard.
 const subject=portrait?{x:.22,y:.06,width:.56,height:.88}:{x:.37,y:.05,width:.32,height:.90};
 return {portrait,profile,heading,picture,qualifier,captions,brand,occupied,subject,
  fontScale:Math.min(sx,sy),hingeAspect:portrait?'tall-close':'wide-context'};
}
export function stateFor(kind,seconds,marks){
 if(!sceneKinds.includes(kind)||!Number.isFinite(seconds)||!marks)throw Error('Current Rust beat and actual word anchors required');
 const after=(name,span=.7)=>smooth((seconds-marks[name])/span);
 const wet=['rust','salt','paint'].includes(kind)?1:kind==='wet'?after('water'):0;
 const oxygen=['rust','salt','paint'].includes(kind)?1:kind==='wet'?after('oxygen'):0;
 const scratch=kind==='paint'?after('scratch',.45):0;
 const rust=kind==='rust'?after('change',1.4):kind==='salt'?after('salt',1.4):kind==='paint'?scratch*smooth((seconds-marks.scratch-.5)/1.1):0;
 return {water:wet,oxygen,rust,scratch,paint:kind==='paint',ironContact:kind!=='paint'||scratch>0,salt:kind==='salt'?after('salt'):0,
  saltRequired:false,rateMultiplier:null,rustLocation:kind==='paint'?'exposed-scratch-only':'attached-iron-surface',
  electronMedium:'metal',ionMedium:'water',mechanism:'oxygenated-neutral-water-iron',time:'illustrative-not-kinetics'};
}
export function oxygenContact(hinge,state,pictureHeight){
 // The scratch path's first bend is exactly (.60,.37) in the hinge box.
 // Once exposed, oxygen's arrow must meet that opening, not intact coating.
 return state.paint&&state.scratch>0
  ?[hinge.x+hinge.w*.60,hinge.y+hinge.h*.37]
  :[hinge.x+hinge.w*.85,pictureHeight*.42];
}
export function validateProps(props,contract){
 if(props.topic_id!==contract.topic_id||props.source_sha256!==contract.script_sha256||
  !/^[a-f0-9]{64}$/.test(props.audio_sha256??'')||props.timing_status!=='actual_audio_aligned'||
  !['measured_word_alignment','human_verified_audio'].includes(props.method)||props.fixture_mode||props.outro!==false)
  throw Error('Actual source-bound Rust body only; no fixture clock or END in this renderer');
 bodyFrameCount(props.duration);
 const tokens=s=>(s.toLowerCase().replaceAll('’',"'").match(/[a-z]+(?:'[a-z]+)?|\d+/g)??[]);
 const words=props.words;
 if(!Array.isArray(words)||words.some(w=>typeof w.word!=='string'||tokens(w.word).length!==1)||
  words.length!==contract.word_count)throw Error('Complete exact current spoken words required');
 let end=0;for(const w of words){if(!Number.isFinite(w.start)||!Number.isFinite(w.end)||w.start<end||w.end<=w.start||w.end>props.duration)throw Error('Invalid actual word times');end=w.end;}
 if(!Array.isArray(props.scenes)||props.scenes.map(s=>s.scene).join('|')!==sceneKinds.join('|'))throw Error('Exact Rust thoughts required');
 end=0;let cursor=0;for(const [i,s] of props.scenes.entries()){
  const expected=contract.scenes[i],last=expected.word_end;
  if(s.word_start!==cursor||s.word_end!==last||!Number.isFinite(s.start)||!Number.isFinite(s.end)||Math.abs(s.start-end)>.001||s.end<=s.start||
   Math.abs(s.start-(cursor===0?0:words[cursor].start))>.001||Math.abs(s.end-(last===words.length?props.duration:words[last].start))>.001)throw Error('Rust scenes must follow current measured words');
  const expectedMarks=Object.fromEntries(Object.entries(contract.anchors[s.scene]).map(([k,v])=>[k,words[v].start-s.start]));
  if(Object.keys(s.marks??{}).sort().join('|')!==Object.keys(expectedMarks).sort().join('|')||Object.entries(expectedMarks).some(([k,v])=>!Number.isFinite(s.marks[k])||Math.abs(s.marks[k]-v)>.001))throw Error('Rust action marks must follow actual spoken words');
  cursor=last;end=s.end;
 }
 if(Math.abs(end-props.duration)>.001)throw Error('Incomplete actual body');
 if(!Array.isArray(props.captions)||!props.captions.length)throw Error('Actual captions required');
 cursor=0;for(const c of props.captions){if(c.word_start!==cursor||!Number.isInteger(c.word_end)||c.word_end<=cursor||c.word_end>words.length||
  tokens(c.text).join(' ')!==words.slice(cursor,c.word_end).flatMap(w=>tokens(w.word)).join(' ')||
  !Number.isFinite(c.start)||!Number.isFinite(c.end)||Math.abs(c.start-words[cursor].start)>.001||Math.abs(c.end-words[c.word_end-1].end)>.001)throw Error('Verbatim measured caption boundaries required');cursor=c.word_end;}
 if(cursor!==words.length)throw Error('Incomplete captions');
 return props;
}
