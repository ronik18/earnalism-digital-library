import {assertUiClear, reviewProfileForFrame, safeContentRect, portraitReviewProfile, landscapeReviewProfile} from './social-safe-area.mjs';
// Byte-verified against the live website header on 2026-11-05. Never crop lettering.
export const watermarkAsset={path:'brand-sting/production-lockup.png',sha256:'951d21e89cbcab58e0f9aed60778a8966d920e2fba464d1cade7bc37fb3ee919',sourceWidth:2400,sourceHeight:720,crop:{x:0,y:0,width:2400,height:720}};
export function watermarkLayout(width,height,{surface='video',placement,occupiedRects=[]}={}){
 if(![width,height].every(Number.isFinite)||width<=0||height<=0)throw Error('Invalid composition dimensions');
 if(!['video','cover'].includes(surface))throw Error('Unknown watermark surface');
 const portrait=height>width,profile=surface==='video'?reviewProfileForFrame(width,height,portrait?portraitReviewProfile:landscapeReviewProfile):null;
 const factor=portrait?Math.min(width/1080,height/1920):Math.min(width/1920,height/1080);
 // Blur is in source-composition pixels, never a change to the full lockup asset.
 const blurPx=surface==='video'?.45*factor:0,blurOutset=Math.ceil(3*blurPx);
 const logoWidth=(portrait?300:340)*factor,safe=profile?safeContentRect(profile):null;
 const defaults=safe?{left:safe.x+safe.width-logoWidth-blurOutset,top:safe.y+blurOutset,width:logoWidth}:portrait?{left:80*width/1080,top:250*height/1920,width:logoWidth}:{left:1510*factor,top:48*factor,width:logoWidth};
 const q=placement?{...placement,width:placement.width??placement.size}:defaults;
 const h=q.width*watermarkAsset.sourceHeight/watermarkAsset.sourceWidth;
 if(![q.left,q.top,q.width].every(Number.isFinite)||q.width<180*factor||q.left<0||q.top<0||q.left+q.width>width||q.top+h>height)throw Error('Full lockup outside composition or too small; reflow legacy icon placement');
 const rect={x:q.left-blurOutset,y:q.top-blurOutset,width:q.width+2*blurOutset,height:h+2*blurOutset};
 if(profile)assertUiClear('complete Earnalism logo and lettering',rect,profile);
 if(profile&&(Math.abs(rect.y-safe.y)>1e-8||Math.abs(rect.x+rect.width-safe.x-safe.width)>1e-8))throw Error('Video watermark must reach the destination-safe top-right halo boundary; reflow the adapter');
 if(!Array.isArray(occupiedRects))throw Error('Invalid watermark protected regions');
 for(const a of occupiedRects){
  if(!a||![a.x,a.y,a.width,a.height].every(Number.isFinite)||a.width<=0||a.height<=0)throw Error('Invalid watermark protected region');
  if(rect.x<a.x+a.width&&rect.x+rect.width>a.x&&rect.y<a.y+a.height&&rect.y+rect.height>a.y)throw Error('Watermark meets protected content; reflow the adapter');
 }
 return {width:q.width,height:h,size:q.width,right:width-q.left-q.width,top:q.top,left:q.left,opacity:.9,scale:q.width/watermarkAsset.sourceWidth,background:surface==='cover'?'#fff9ed':undefined,blurPx,blurOutset,protectedRect:rect,reviewProfile:profile?.id??null};
}
export function schematicContext(scene,time){
 const age=time-scene.start;
 if(!['orbit','eclipse'].includes(scene.diagram)||age<0||age>=3.6)return null;
 return {text:'Illustrative schematic · not to scale',opacity:Math.min(1,age/.25,(3.6-age)/.4)};
}
