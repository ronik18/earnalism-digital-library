import {assertUiClear, reviewProfileForFrame} from './social-safe-area.mjs';
// Exact approved production emblem, clipped without altering its source pixels.
export const watermarkAsset={path:'brand-sting/production-lockup.png',sha256:'951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919',sourceWidth:2400,sourceHeight:720,crop:{x:112,y:79,width:592,height:592}};
export function watermarkLayout(width,height,{surface='video',placement,occupiedRects=[]}={}){
 if(![width,height].every(Number.isFinite)||width<=0||height<=0)throw Error('Invalid composition dimensions');
 if(!['video','cover'].includes(surface))throw Error('Unknown watermark surface');
 const portrait=height>width,profile=portrait&&surface==='video'?reviewProfileForFrame(width,height):null;
 const factor=Math.min(width/1080,height/1920);
 const size=profile?56*factor:portrait?72:82;
 const right=profile?profile.right+12*width/1080:portrait?65:70;
 const top=profile?profile.top+22*height/1920:portrait?44:48;
 const q=placement?{...placement}:{left:width-right-size,top,size};
 const rect={x:q.left,y:q.top,width:q.size,height:q.size};
 if(![q.left,q.top,q.size].every(Number.isFinite)||q.size<=0||q.left<0||q.top<0||q.left+q.size>width||q.top+q.size>height)
  throw Error('Watermark outside composition');
 if(profile)assertUiClear('complete Earnalism emblem',rect,profile);
 if(!Array.isArray(occupiedRects))throw Error('Invalid watermark protected regions');
 for(const a of occupiedRects){
  if(!a||![a.x,a.y,a.width,a.height].every(Number.isFinite)||a.width<=0||a.height<=0)
   throw Error('Invalid watermark protected region');
  if(rect.x<a.x+a.width&&rect.x+rect.width>a.x&&rect.y<a.y+a.height&&rect.y+rect.height>a.y)
   throw Error('Watermark meets protected content; reflow the adapter');
 }
 return {size:q.size,right:width-q.left-q.size,top:q.top,left:q.left,opacity:.48,scale:q.size/watermarkAsset.crop.width};
}
export function schematicContext(scene,time){
 const age=time-scene.start;
 if(!['orbit','eclipse'].includes(scene.diagram)||age<0||age>=3.6)return null;
 return {text:'Illustrative schematic · not to scale',opacity:Math.min(1,age/.25,(3.6-age)/.4)};
}
