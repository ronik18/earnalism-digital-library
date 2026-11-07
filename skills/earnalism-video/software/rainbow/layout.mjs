import {assertUiClear,portraitReviewProfile} from '../src/social-safe-area.mjs';
import {watermarkLayout} from '../src/branding.mjs';
export {sceneKinds,requiredMarks} from './model.mjs';
export const palette={ivory:'#fff6e9',muted:'#d8e5e3',ink:'#132037',cyan:'#7be7d5',gold:'#ffd480',pink:'#f5a5bb',violet:'#c7abff'};
export const bodyFrameCount=(duration,fps=30)=>Math.ceil(duration*fps);
export function rectOverlap(a,b){return a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y;}
export function layoutFor(portrait){return portrait?{
 heading:{x:80,y:390,width:820,height:145},diagram:{x:80,y:560,width:820,height:600},
 support:{x:80,y:1180,width:820,height:90},captions:{x:80,y:1285,width:820,height:205},
 headingFont:62,captionFont:47,watermark:{left:600,top:280,width:300},uiProfile:portraitReviewProfile,
}:{
 heading:{x:90,y:76,width:1340,height:170},diagram:{x:80,y:265,width:1760,height:570},
 support:{x:90,y:850,width:1740,height:75},captions:{x:100,y:950,width:1720,height:110},
 headingFont:72,captionFont:47,
};}
export function assertLayout(portrait){
 const l=layoutFor(portrait),w=portrait?1080:1920,h=portrait?1920:1080;
 const names=['heading','diagram','support','captions'];
 for(const name of names){const r=l[name];if(r.x<0||r.y<0||r.x+r.width>w||r.y+r.height>h)throw Error('Outside composition '+name);if(portrait)assertUiClear(name,r,l.uiProfile);}
 for(let i=0;i<names.length;i++)for(let j=i+1;j<names.length;j++)if(rectOverlap(l[names[i]],l[names[j]]))throw Error('Content regions overlap');
 watermarkLayout(w,h,{placement:portrait?l.watermark:undefined,occupiedRects:names.map(k=>l[k])});
 return l;
}
export const titles={
 question:'Why can’t you reach a rainbow’s end?', conditions:'Sun behind.\nDrops ahead.', droplet:'Follow light through a drop.',
 cone:'A view built around you.', move:'You move. The drops change.', circle:'The missing part of the circle.', callback:'Real light. A changing view.',
};
export function headingFor(kind,portrait){
 if(portrait)return ({question:'Why can’t you reach\na rainbow’s end?',conditions:'Sun behind.\nDrops ahead.',droplet:'Follow light\nthrough a drop.',cone:'A view built\naround you.',move:'You move.\nThe drops change.',circle:'The missing part\nof the circle.',callback:'Real light.\nA changing view.'})[kind];
 return kind==='question'?'Why can’t you reach\na rainbow’s end?':kind==='conditions'?'Sun behind. Drops ahead.':titles[kind];
}
export function supportText(kind,t,m={}){
 if(kind==='conditions')return t>=(m.behind??Infinity)?'Schematic · positions not to scale':'';
 if(kind==='droplet')return t>=(m.dispersion??Infinity)?'Spherical-drop schematic · enlarged':t>=(m.reflect??Infinity)?'One internal reflection':'Spherical-drop schematic · enlarged';
 if(kind==='cone')return t>=(m.angle??Infinity)?'Primary rainbow · angles are approximate.':'';
 if(kind==='move')return '';
 if(kind==='circle')return '';
 return '';
}
export function labelBounds({x,y,text,size=48,anchor='middle'}){
 const width=Math.max(75,text.length*size*.57+24);
 return {x:anchor==='middle'?x-width/2:anchor==='end'?x-width:x,y:y-size*.87,width,height:size*1.2};
}
export function assertLabels(labels,width,height){
 const rects=labels.map(labelBounds);
 for(let i=0;i<rects.length;i++){const r=rects[i];if(r.x<0||r.y<0||r.x+r.width>width||r.y+r.height>height)throw Error('Label outside diagram '+labels[i].text);for(let j=0;j<i;j++)if(rectOverlap(r,rects[j]))throw Error('Diagram labels overlap '+labels[j].text+'/'+labels[i].text);}
 return labels;
}
export function conditionLabels(p){const w=p?900:1600;return assertLabels([
 {x:p?125:250,y:125,text:'Sun',size:p?50:60},
 {x:p?390:700,y:610,text:'You',size:p?50:60},
 {x:p?720:1250,y:125,text:'Sunlit drops',size:p?48:60},
 ],w,760);}
export function coneLabels(p){return assertLabels([
 {x:p?170:330,y:580,text:'Your eye',size:p?47:58},
 {x:p?715:1180,y:220,text:'Red edge',size:p?50:62},
 {x:p?715:1180,y:315,text:'≈ 42°',size:p?62:74},
 {x:p?715:1180,y:435,text:'Violet',size:p?50:60},
 {x:p?610:1050,y:730,text:'Opposite the Sun',size:p?44:56},
 ],p?900:1600,760);}

// Exactly one explanation label for each reveal stage. Keep the complete ring
// clear, including its actual stroke and an eight-unit visual safety margin.
export function circleSceneLayout(portrait,reveal,ground=0){
 if(!Number.isFinite(reveal)||reveal<0||reveal>1||!Number.isFinite(ground))throw Error('Invalid circle label stage');
 const w=portrait?900:1600,cx=w/2,cy=370,r=portrait?292:310,maskY=405+(740-405)*reveal;
 const initial=reveal<=.3;
 const labels=assertLabels([initial?
  {x:cx,y:650,text:ground>0?'The ground hides this part':'A circle can be partly hidden',size:portrait?40:58}:
  {x:cx,y:portrait?730:735,text:'Unobstructed elevated view',size:portrait?43:50}
 ],w,760);
 const strokeHalf=(43/48+1.4)/2,pad=8,outer=r+strokeHalf;
 const visibleBottom=initial?Math.min(cy+outer,maskY):cy+outer;
 const protectedCircle={x:cx-outer-pad,y:cy-outer-pad,width:2*(outer+pad),height:visibleBottom+pad-(cy-outer-pad)};
 for(const label of labels)if(rectOverlap(labelBounds(label),protectedCircle))throw Error('Circle explanation label covers visible ring');
 return {w,cx,cy,r,maskY,labels,protectedCircle};
}
