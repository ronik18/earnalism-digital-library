import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {layout,stateFor,oxygenContact,sceneKinds,bodyFrameCount,validateProps} from './layout.mjs';
import {validateRenderInput} from './render-input.mjs';
const contract=JSON.parse(fs.readFileSync(new URL('./contract.json',import.meta.url),'utf8'));
function fixture(){
 const c=structuredClone(contract),words=Array.from({length:c.word_count},(_,i)=>({word:'synthetic',start:i*.4,end:i*.4+.3})),duration=words.at(-1).end+.2;
 c.normalized_tokens_sha256=createHash('sha256').update(words.map(w=>w.word).join(' ')).digest('hex');
 const scenes=c.scenes.map(s=>{const start=s.word_start===0?0:words[s.word_start].start;return {scene:s.id,start,end:s.word_end===words.length?duration:words[s.word_end].start,word_start:s.word_start,word_end:s.word_end,marks:Object.fromEntries(Object.entries(c.anchors[s.id]).map(([k,i])=>[k,words[i].start-start]))};});
 const captions=[];for(let first=0;first<words.length;first+=5){const last=Math.min(first+5,words.length);captions.push({word_start:first,word_end:last,text:words.slice(first,last).map(w=>w.word).join(' '),start:words[first].start,end:words[last-1].end});}
 return {c,p:{topic_id:c.topic_id,source_sha256:c.script_sha256,audio_sha256:'a'.repeat(64),timing_status:'actual_audio_aligned',method:'measured_word_alignment',duration,words,scenes,captions,outro:false,burnCaptions:false}};
}
test('independent aspect geometry protects full alpha lockup halo at actual frame sizes',()=>{
 for(const [w,h] of [[1920,1080],[1080,1920],[1280,720],[720,1280]]){
  const l=layout(w,h);assert.equal(l.brand.background,undefined);assert.ok(l.picture.height>0);assert.ok(l.brand.protectedRect.y+l.brand.protectedRect.height<l.heading.y);
  assert.ok(l.picture.y+l.picture.height<=l.qualifier.y);assert.ok(l.qualifier.y+l.qualifier.height<=l.captions.y);
  if(l.portrait){assert.ok(l.subject.height>.8);assert.ok(l.picture.height*l.subject.height>h*.3);assert.equal(l.hingeAspect,'tall-close');}
  const again=layout(w,h);assert.deepEqual(again.brand,l.brand,'anchor is stable through every scene');
 }
 assert.notDeepEqual(layout(1920,1080).subject,layout(1080,1920).subject);
});
test('ordinary wet-iron state has optional salt, no kinetic rate and no charge in the wrong medium',()=>{
 for(const kind of sceneKinds)for(let t=0;t<8;t+=.1){const s=stateFor(kind,t,{drop:.2,water:.1,oxygen:.7,change:.8,salt:.2,barrier:.1,scratch:2,iron:.1});
  assert.equal(s.rateMultiplier,null);assert.equal(s.saltRequired,false);assert.equal(s.electronMedium,'metal');assert.equal(s.ionMedium,'water');
  if(kind==='rust'){assert.equal(s.salt,0);assert.equal(s.water,1);assert.equal(s.oxygen,1);}
  if(kind==='paint'&&s.rust>0){assert.equal(s.scratch,1);assert.equal(s.rustLocation,'exposed-scratch-only');}
  if(kind==='paint'&&t<=2){assert.equal(s.rust,0);assert.equal(s.ironContact,false);assert.equal(s.water,1,'water can meet intact paint while iron stays isolated');}
 }
});
test('oxygen reaches the actual exposed scratch, while intact-paint contact stays a barrier',()=>{
 for(const [w,h] of [[1920,1080],[1080,1920]]){
  const l=layout(w,h),r=l.picture,s=l.subject,hinge={x:s.x*r.width,y:s.y*r.height,w:s.width*r.width,h:s.height*r.height};
  for(const scratch of [.01,.5,1]){
   const [x,y]=oxygenContact(hinge,{paint:true,scratch},r.height);
   assert.equal(x,hinge.x+hinge.w*.60);assert.equal(y,hinge.y+hinge.h*.37);
   assert.ok(x>=0&&x<=r.width&&y>=0&&y<=r.height);
  }
  assert.notDeepEqual(oxygenContact(hinge,{paint:true,scratch:0},r.height),oxygenContact(hinge,{paint:true,scratch:1},r.height));
 }
});
test('real word/source checks reject illustrative study clocks, script substitutions and fixture modes',()=>{
 const {p,c}=fixture();assert.equal(validateRenderInput(p,c),p);
 assert.throws(()=>validateRenderInput(p,contract),/script digest/,'synthetic test words never qualify the real script');
 for(const change of [{fixture_mode:true},{timing_status:'illustrative'},{method:'synthetic_fixture'},{topic_id:'19-tides'},{outro:true},{duration:18}])assert.throws(()=>validateRenderInput({...p,...change},c));
 const old=structuredClone(p);old.scenes[4].marks.scratch+=.2;assert.throws(()=>validateProps(old,c),/spoken words/);
 const caption=structuredClone(p);caption.captions[0].text='unspoken preview';assert.throws(()=>validateProps(caption,c),/Verbatim/);
});
test('content source exposes hashes/ranges only, preserves exact script identity and correct body padding',()=>{
 assert.equal(contract.script_sha256,'04ee78aaf17f7a35b2627b52af9698185d128d9eb304b0b4aa72b67b44c56abc');
 assert.equal(contract.script,undefined);assert.equal(contract.scenes[0].word_start,0);assert.equal(contract.scenes.at(-1).word_end,contract.word_count);
 assert.equal(bodyFrameCount(10.01),301);assert.throws(()=>bodyFrameCount(true));assert.throws(()=>bodyFrameCount(Infinity));
});
