#!/usr/bin/env python3
"""Inactive bounded typography repair; preserve original pixels outside panels."""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features

ROOT=Path('/workspace/scratch/181ef0a25f05')
REPO=Path('/tmp/earnalism-main-approved-integration')
META=REPO/'data/controlled_publications/bn-060/public_book.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 assert features.check('raqm')
 assert sha(META)=='860d1efe328898188179a4257709cecdd2795359160f94865b0cc40682e2da34'
 m=json.loads(META.read_text());assert m['title']=='ইন্দিরা';assert m['author']=='বঙ্কিমচন্দ্র চট্টোপাধ্যায়'
 assert m['short_description']=='স্বামীর কাছে পরিচয় হারানো ইন্দিরার পুনরায় নিজেকে প্রতিষ্ঠিত করার রোমাঞ্চকর কাহিনি।'
 fonts=REPO/'frontend/src/assets/fonts'
 def font(name,size):return ImageFont.truetype(str(fonts/name),size,layout_engine=ImageFont.Layout.RAQM)
 title=font('noto-serif-bengali-600.ttf',150);author=font('noto-sans-bengali-500.ttf',64);body=font('noto-serif-bengali-600.ttf',74)
 receipt={'scope':'INACTIVE_ONLY_NO_NEW_APPROVAL_OR_PUBLICATION_FACT','source_metadata_sha256':sha(META),'metadata':{k:m[k] for k in ('title','author','short_description')},'raqm':True,'outputs':{},'preservation':'All original pixels outside listed opaque repair panels remain byte-identical in decoded RGB. Art behind defective typography within panels is covered; no new illustration is introduced.'}
 for side in ('front','back'):
  src=ROOT/f'bn060-recovery/{side}.png'
  assert sha(src)=={'front':'dcbfc2996987baae482523e355aefa218a3d422c027127237daccbc700c34b88','back':'b5ed699a3ff0fbcee904ead6b2825904621fdb74165762a685a456f1a376aeed'}[side]
  im=Image.open(src).convert('RGB');original=im.copy();d=ImageDraw.Draw(im)
  panels=[(300,740,1300,1160),(225,1875,1370,2040)] if side=='front' else [(185,195,1415,1720)]
  for index,box in enumerate(panels):
   if side=='front' and index==1:
    d.rectangle(box,fill=(63,20,29));continue
   d.rounded_rectangle(box,radius=36,fill=(63,20,29),outline=(216,179,91),width=5)
   inset=(box[0]+22,box[1]+22,box[2]-22,box[3]-22)
   d.rounded_rectangle(inset,radius=22,outline=(216,179,91),width=1)
  boxes=[]
  def center(txt,y,f):
   b=d.textbbox((0,0),txt,font=f,direction='ltr',language='bn');x=(1600-(b[2]-b[0]))//2-b[0];y0=y-b[1]
   d.text((x,y0),txt,font=f,fill=(255,235,185),direction='ltr',language='bn');boxes.append([x+b[0],y,x+b[2],y+b[3]-b[1]])
  if side=='front':center(m['title'],820,title);center(m['author'],1030,author)
  else:
   center(m['title'],340,title);center(m['author'],590,author)
   words=m['short_description'].split();lines=[];line=''
   for w in words:
    trial=(line+' '+w).strip();b=d.textbbox((0,0),trial,font=body,direction='ltr',language='bn')
    if b[2]-b[0]>1050:lines.append(line);line=w
    else:line=trial
   lines.append(line)
   assert ' '.join(lines)==m['short_description']
   for n,line in enumerate(lines):center(line,890+n*145,body)
  assert all(any(b[0]>=q[0] and b[1]>=q[1] and b[2]<=q[2] and b[3]<=q[3] for q in panels) for b in boxes)
  # Verify decoded original pixels outside explicitly listed repair zones.
  import numpy as np
  old=np.asarray(original);new=np.asarray(im);mask=np.ones(old.shape[:2],dtype=bool)
  for x0,y0,x1,y1 in panels:mask[y0:y1+1,x0:x1+1]=False
  assert np.array_equal(old[mask],new[mask])
  dst=a.output/f'bn-060-{side}-inactive.png';im.save(dst,compress_level=9,optimize=False)
  receipt['outputs'][side]={'sha256':sha(dst),'bytes':dst.stat().st_size,'original_sha256':sha(src),'repair_panels':panels,'text_boxes':boxes,'outside_pixels_identical':True,'dimensions':list(im.size)}
 (a.output/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
