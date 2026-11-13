// Read-only bridge to the installed project branding/safe-area implementation.
import {watermarkLayout, watermarkAsset} from '../src/branding.mjs';
import {reviewProfileForFrame, safeContentRect, portraitReviewProfile,
  landscapeReviewProfile, assertUiClear} from '../src/social-safe-area.mjs';

let input='';for await(const part of process.stdin)input+=part;
const layouts=JSON.parse(input), result={};
for(const [name,{width,height}] of Object.entries(layouts)){
  const portrait=name==='portrait', factor=Math.min(width/(portrait?1080:1920),height/(portrait?1920:1080));
  const profile=reviewProfileForFrame(width,height,portrait?portraitReviewProfile:landscapeReviewProfile);
  const safe=safeContentRect(profile), q=watermarkLayout(width,height);
  const gap=(portrait?32:28)*factor, captionHeight=(portrait?252:192)*factor;
  const caption={x:safe.x,y:safe.y+safe.height-captionHeight,width:safe.width,height:captionHeight};
  const even=v=>Math.ceil(v/2)*2, down=v=>Math.floor(v/2)*2;
  const x=even(safe.x), y=even(q.protectedRect.y+q.protectedRect.height+gap);
  const picture={x,y,width:down(safe.x+safe.width)-x,height:down(caption.y-gap)-y};
  const draft={x:safe.x,y:q.top,width:q.protectedRect.x-safe.x-gap,height:q.height};
  for(const [label,rect]of Object.entries({caption,picture,draft}))assertUiClear(label,rect,profile);
  watermarkLayout(width,height,{occupiedRects:[caption,picture,draft]});
  const xyxy=r=>[r.x,r.y,r.x+r.width,r.y+r.height];
  result[name]={safe:xyxy(safe),logo:[q.left,q.top,q.left+q.width,q.top+q.height],
    logoProtected:xyxy(q.protectedRect),picture:xyxy(picture),caption:xyxy(caption),
    draft:xyxy(draft),brand:q,brandAsset:watermarkAsset,reviewProfile:profile,scale:factor,
    captionMinPx:(portrait?43:36)*factor,captionPreferredPx:(portrait?48:44)*factor,
    captionReference:'Existing 1080p src/index.tsx caption sizes; no below-reference shrinking'};
}
process.stdout.write(JSON.stringify(result));
