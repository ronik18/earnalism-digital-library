import {watermarkLayout} from '../src/branding.mjs';
import {smooth} from './model.mjs';
import {assertUiClear,portraitReviewProfile} from '../src/social-safe-area.mjs';
export {sceneKinds,requiredMarks,smooth} from './model.mjs';
export {bodyFrameCount} from '../thermal_touch/layout.mjs';
export const palette={ivory:'#fff4df',muted:'#d4d7e7',blue:'#62bfff',cyan:'#7fe4df',amber:'#ffd37d',coral:'#ff8e79',ink:'#112038',violet:'#b49cff'};
export function layoutFor(p){return p?{heading:{x:80,y:390,width:820,height:145},diagram:{x:80,y:560,width:820,height:600},support:{x:80,y:1180,width:820,height:90},captions:{x:80,y:1285,width:820,height:205},headingFont:62,captionFont:47,watermark:watermarkLayout(1080,1920),uiProfile:portraitReviewProfile}:{heading:{x:90,y:76,width:1340,height:170},diagram:{x:80,y:265,width:1760,height:570},support:{x:90,y:850,width:1740,height:75},captions:{x:100,y:950,width:1720,height:110},headingFont:72,captionFont:47};}
export function rectOverlap(a,b){return a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;}
export function assertLayout(p){const l=layoutFor(p),w=p?1080:1920,h=p?1920:1080;for(const k of ['heading','diagram','support','captions']){const a=l[k];if(a.x<0||a.y<0||a.x+a.width>w||a.y+a.height>h)throw Error('Outside composition '+k);if(p)assertUiClear(k,a,l.uiProfile);for(const j of ['heading','diagram','support','captions'])if(k<j&&rectOverlap(a,l[j]))throw Error('Overlapping regions '+k+'/'+j);}watermarkLayout(w,h,{placement:p?l.watermark:undefined,occupiedRects:['heading','diagram','support','captions'].map(k=>l[k])});return l;}
export const rayLabels={sun:{x:30,y:10,width:220,height:64},observer:{x:575,y:295,width:250,height:65},atmosphere:{x:480,y:660,width:370,height:80}};
export function supportText(kind,t,m={}){if(kind==='scattering')return t>=(m.shorter??Infinity)?'':'Scattering redirects light.';if(kind==='sky_path')return t>=(m.direct??Infinity)?'Scattered sky light ≠ direct sunlight.':'Look at the sky away from the Sun.';if(kind==='prediction')return t>=(m.predict??Infinity)?'What remains in the direct beam?':'';if(kind==='sunset_path')return t>=(m.identity??Infinity)?'Blue stays blue. The mixture changes.':'A longer path changes the remaining mixture.';if(kind==='callback')return t>=(m.callback??Infinity)?'Same Sun. Different paths.':'Clouds and particles can change real sunsets.';return '';}

// The renderer uses these same label backplates/positions, so movement checks
// cover actual component geometry rather than a disconnected test sketch.
export function labelBounds({x,y,text,size=50,anchor='middle'}){const width=Math.max(80,text.length*size*.57+24);return {x:anchor==='middle'?x-width/2:anchor==='end'?x-width:x,y:y-size*.84,width,height:size*1.2};}
export function sectionAnnotationLayout(path,title='',showOutput=false,qualify=false){const a=[{x:path.source.x<200?path.source.x+52:path.source.x-55,y:path.source.x<200?path.source.y-55:path.source.y-10,anchor:path.source.x<200?'start':'end',size:56,text:'Sun'},{x:680,y:375,size:56,text:'Receiver'},{x:740,y:175,size:56,text:'Air',color:palette.blue},{x:260,y:550,size:56,text:'Earth'}];if(title)a.push({x:title.length>12?640:685,y:65,size:56,text:title});if(showOutput)a.push({x:715,y:570,size:56,text:'Warmer mix'});if(qualify)a.push({x:480,y:680,size:56,text:'Atmosphere exaggerated'});return a;}
// Use the actual first scattering verb when supplied; old props retain their
// documented later paraphrase mark rather than acquiring estimated timing.
export function redirectionStarted(t,marks){return t>=(marks.scatter??marks.redirect??Infinity);}

// Opening and cover deliberately share only their subject artwork; each uses
// its own actual composition geometry. No atmospheric/path result is inferred.
export function openingComparisonLayout(p){return p?
 {width:900,height:760,day:{x:30,y:215,w:400,h:440},dusk:{x:470,y:215,w:400,h:440},source:{x:450,y:75,r:30},labelSize:54}:
 {width:1600,height:760,day:{x:35,y:195,w:730,h:485},dusk:{x:835,y:195,w:730,h:485},source:{x:800,y:65,r:34},labelSize:60};}
export function openingRevealState(t,marks={}){return {
 source:smooth(t,marks.question??Infinity,(marks.question??Infinity)+.65),
 travel:smooth(t,marks.light??Infinity,(marks.light??Infinity)+.35)};}
export function coverComparisonLayout(p){return p?
 {width:1080,height:1920,headline:{x:85,y:430,width:910,height:160,fontSize:134},day:{x:70,y:750,w:450,h:700},dusk:{x:560,y:750,w:450,h:700},source:{x:540,y:655,r:45},labelSize:76}:
 {width:1920,height:1080,headline:{x:100,y:85,width:1720,height:190,fontSize:155},day:{x:85,y:430,w:835,h:570},dusk:{x:1000,y:430,w:835,h:570},source:{x:960,y:340,r:45},labelSize:90};}
export function sourceRoutes(layout){return [layout.day,layout.dusk].map((card,i)=>({
 start:{x:layout.source.x+(i?1:-1)*layout.source.r*.65,y:layout.source.y+layout.source.r*.55},
 control:{x:(layout.source.x+card.x+card.w/2)/2,y:card.y-45},
 end:{x:card.x+card.w/2,y:card.y}}));}
export function pointOnSourceRoute(route,p){const q=Math.max(0,Math.min(1,p)),u=1-q;return {
 x:u*u*route.start.x+2*u*q*route.control.x+q*q*route.end.x,
 y:u*u*route.start.y+2*u*q*route.control.y+q*q*route.end.y};}
// This display pair uses uppercase labels at large cover sizes. Its generous
// bounded backplates are separate from scientific annotations in later scenes.
export function panelLabelLayout(card,size,cover=false,dusk=false){
 const text=dusk?'SUNSET':'BLUE SKY',width=Math.min(card.w-48,text.length*size*.72+48);
 const baseline=card.y+(cover?115:75);
 return {text,size,x:card.x+card.w/2,y:baseline,
  box:{x:card.x+(card.w-width)/2,y:baseline-size*.90,width,height:size*1.32}};
}

