export const sceneKinds=['question','source','cooling','droplets','conditions','callback'];
export {bodyFrameCount} from '../thermal_touch/layout.mjs';
export const palette={ivory:'#fff4df',muted:'#d0c9df',amber:'#ffd07d',water:'#64d9df',plum:'#251c39',cold:'#81d4ed'};
export function layoutFor(p){return p?{heading:{x:70,y:125,width:870,height:180},diagram:{x:55,y:515,width:890,height:770},support:{x:70,y:1305,width:870,height:85},captions:{x:70,y:1420,width:870,height:185},headingFont:70,captionFont:47}:{heading:{x:100,y:78,width:1630,height:150},diagram:{x:85,y:245,width:1750,height:620},support:{x:100,y:880,width:1700,height:75},captions:{x:110,y:965,width:1700,height:95},headingFont:78,captionFont:48};}
export const smooth=(t,a,b)=>{const x=Math.max(0,Math.min(1,(t-a)/(b-a)));return x*x*(3-2*x);};
export function belowDewPoint(surface,dew){if(!Number.isFinite(surface)||!Number.isFinite(dew))throw Error('Finite temperatures required');return surface<dew;}
// Schematic coordinates only, not simulated molecule motion or condensation yield.
export function vaporPath(i,progress){const p=Math.max(0,Math.min(1,progress));return {x:770-(770-568)*p,y:210+i*53+Math.sin(p*Math.PI*2+i)*12};}
export function dropletPoint(i){return {x:559,y:215+i*57};}
export function conditionState(drier){const surface=8,dew=drier?3:16;return {surface,dew,wet:belowDewPoint(surface,dew)};}
export function assertLayout(p){const l=layoutFor(p);for(const a of ['heading','diagram','support','captions'])for(const b of ['heading','diagram','support','captions'])if(a<b){const x=l[a],y=l[b];if(x.x<y.x+y.width&&x.x+x.width>y.x&&x.y<y.y+y.height&&x.y+x.height>y.y)throw Error('Overlapping layout '+a+' '+b);}return l;}
export function coalescedDrop(i,progress){const p=Math.max(0,Math.min(1,progress)),a=dropletPoint(i),target=215+(Math.floor(i/2)*2+.5)*57;return {x:559+7*p,y:a.y+(target-a.y)*p,r:18+7*p,opacity:i%2?1-p:1};}
export function wholeDropPoint(i){const y=215+i*57,r=12+(i%3)*3,wallX=550-20*(y-120)/480;return {x:wallX+r+1,y,r,wallX};}
export const sourceFootnote={x:1230,y:425,fontSize:43,maxWidth:620,particleRight:824,text:'Dots are schematic symbols.'};

// Supporting copy occupies its own tested region, never the SVG wall-label baseline.
export function supportText(kind,t,marks={}){
 if(kind==='question')return t>=(marks.question??Infinity)?'Through the wall—or from somewhere unseen?':'';
 if(kind==='source')return '';
 if(kind==='cooling')return t>=(marks.dewpoint??Infinity)?'Cooling to the dew point.':'Heat flows from warmer to colder.';
 if(kind==='droplets')return t>=(marks.conservation??Infinity)?'A change of state—not new water.':'Below dew point: liquid can grow.';
 if(kind==='conditions')return 'Same glass temperature · above-freezing liquid case';
 return 'From invisible vapor to visible drops.';
}

// Reveal the wall qualification at the actual spoken leak question, not before it.
export function openingWallVisible(kind,t,marks={}){return kind!=='question'||t>=(marks.question??Infinity);}

// Actual caption onset, not the later above-freezing phrase or a fixed offset.
export function liquidRecallAnchor(captions,sceneStart){const cue=captions.find(c=>/^Here,? we are showing liquid droplets/.test(c.text));return cue?cue.start-sceneStart:Infinity;}
export function portraitCondition(t,marks){const recall=t>=(marks.liquid_recall??Infinity);return {dry:t>=(marks.drier??Infinity)&&!recall,recall};}
