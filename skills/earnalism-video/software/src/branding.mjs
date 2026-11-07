import {assertUiClear, reviewProfileForFrame} from './social-safe-area.mjs';
// Byte-verified against the live website header on 2026-11-05. Never crop lettering.
export const watermarkAsset={path:'brand-sting/production-lockup.png',sha256:'951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919',sourceWidth:2400,sourceHeight:720,crop:{x:0,y:0,width:2400,height:720}};
export function watermarkLayout(width,height,{surface='video',placement,occupiedRects=[]}={}){
 if(![width,height].every(Number.isFinite)||width<=0||height<=0)throw Error('Invalid composition dimensions');
 if(!['video','cover'].includes(surface))throw Error('Unknown watermark surface');
 const portrait=height>width,profile=portrait&&surface==='video'?reviewProfileForFrame(width,height):null;
 const factor=portrait?Math.min(width/1080,height/1920):Math.min(width/1920,height/1080);
 const defaults=portrait?{left:surface==='video'?width-180*width/1080-300*factor:80*width/1080,top:(surface==='video'?280:250)*height/1920,width:300*factor}:{left:1510*factor,top:48*factor,width:340*factor};
 const q=placement?{...placement,width:placement.width??placement.size}:defaults;
 const h=q.width*watermarkAsset.sourceHeight/watermarkAsset.sourceWidth;
 if(![q.left,q.top,q.width].every(Number.isFinite)||q.width<180*factor||q.left<0||q.top<0||q.left+q.width>width||q.top+h>height)throw Error('Full lockup outside composition or too small; reflow legacy icon placement');
 const rect={x:q.left,y:q.top,width:q.width,height:h};
 if(profile)assertUiClear('complete Earnalism logo and lettering',rect,profile);
 if(!Array.isArray(occupiedRects))throw Error('Invalid watermark protected regions');
 for(const a of occupiedRects){
  if(!a||![a.x,a.y,a.width,a.height].every(Number.isFinite)||a.width<=0||a.height<=0)throw Error('Invalid watermark protected region');
  if(rect.x<a.x+a.width&&rect.x+rect.width>a.x&&rect.y<a.y+a.height&&rect.y+rect.height>a.y)throw Error('Watermark meets protected content; reflow the adapter');
 }
 return {width:q.width,height:h,size:q.width,right:width-q.left-q.width,top:q.top,left:q.left,opacity:.9,scale:q.width/watermarkAsset.sourceWidth,background:'#fff9ed'};
}
export function schematicContext(scene,time){
 const age=time-scene.start;
 if(!['orbit','eclipse'].includes(scene.diagram)||age<0||age>=3.6)return null;
 return {text:'Illustrative schematic · not to scale',opacity:Math.min(1,age/.25,(3.6-age)/.4)};
}
