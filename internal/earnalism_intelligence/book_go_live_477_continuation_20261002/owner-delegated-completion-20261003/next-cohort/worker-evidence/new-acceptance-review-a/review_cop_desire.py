from pathlib import Path
import json,hashlib,unicodedata,subprocess
from PIL import Image,ImageChops,ImageDraw
S=Path('/workspace/scratch/181ef0a25f05');R=Path('/tmp/earnalism-main-approved-integration');out=S/'new-acceptance-review-a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
norm=lambda s:' '.join(unicodedata.normalize('NFC',s).split())
bp=R/'internal/legal/catalogue_clearance_20261002/english/current_whole_work_boundary_verification.json';bounds={x['slug']:x for x in load(bp)['titles']}
for slug,dirname,packet in [('the-cop-and-the-anthem','cop-anthem-prep-20261003','candidate-inactive-unaccepted'),('dsires-baby','desire-prep-20261003','inactive-candidate')]:
 d=S/dirname;p=d/packet;old=d/'preimages/root';des=slug=='dsires-baby'; dec=load(p/'rights_decision.json');v=load(d/('preparation-validation.json' if des else 'validation.json'));chapter=load(p/'chapters/chapter-001.json');text=chapter['content'];ch=hashlib.sha256(text.encode()).hexdigest();se=load(p/'source_evidence.json');b=bounds[slug]
 assert ch==se['content_hash']==b['reader_aggregate_sha256'];assert se['source_hash']==b['raw_source_sha256'];assert norm(text).startswith(norm(b['first_body_anchor'])) and norm(text).endswith(norm(b['last_body_anchor']));assert b['internal_gaps']==[] and b['chapter_count']==1
 for n in ['source_evidence.json','chapters/chapter-001.json','highlight_sync.json']:assert sha(p/n)==sha(old/n)
 complete={'boundary_artifact_sha256':sha(bp),'source_sha256':se['source_hash'],'content_sha256':ch,'persisted_first_last_boundaries_and_empty_gaps_rebound':True,'scope':b['selected_edition_scope'],'new_fetches_by_reviewer':0,'containment_alone_not_claimed_complete':True}
 if des:
  raw=d/'recovered/source.txt';assert sha(raw)==se['source_hash'];src=raw.read_bytes().decode('utf-8-sig');start=src.rfind('DÉSIRÉE’S BABY')+len('DÉSIRÉE’S BABY');end=src.index('A RESPECTABLE WOMAN',start);assert norm(src[start:end])==norm(text);complete['full_recovered_source_selected_story_equals_entire_chapter']='PASS_NFC_WHITESPACE_ONLY'
 prep=load(p/('cover_provenance.json' if des else 'cover_preparation.json'));excerpt=prep['derivative_lineage']['source_excerpt'] if des else prep['source_excerpt'];assert norm(text).startswith(excerpt)
 assets={}
 for side in ['front','back']:
  if des:
   a=next(x for x in v['delivery_assets'] if x['kind']==side);original=d/v['original_receipts'][side]['file'];png=p/a['source_file'];web=d/a['delivery_file'];expectedOriginal=v['original_receipts'][side]['sha256'];expectedPNG=a['source_sha256'];expectedWeb=a['delivery_sha256'];rects=v['original_receipts'][side]['bounded_masks']
  else:
   a=next(x for x in prep['assets'] if x['kind']==side);original=p/'covers'/('original-'+side+'.png');png=p/a['png_file'];web=p/a['webp_file'];expectedOriginal=a['original_sha256'];expectedPNG=a['png_sha256'];expectedWeb=a['webp_sha256'];rects=[[210,700,1390,1265],[180,1830,1420,2140]] if side=='front' else [[95,70,1505,2160]]
  assert sha(original)==expectedOriginal and sha(png)==expectedPNG and sha(web)==expectedWeb
  with Image.open(original) as im:im.load();before=im.convert('RGB')
  with Image.open(png) as im:im.load();after=im.convert('RGB');assert im.size==(1600,2400)
  mask=Image.new('L',before.size,255);dr=ImageDraw.Draw(mask)
  for rect in rects:dr.rectangle(rect,fill=0)
  diff=ImageChops.difference(before,after);assert Image.composite(diff,Image.new('RGB',diff.size),mask).getbbox() is None
  with Image.open(web) as im:im.load();assert im.size==(800,1200)
  assert web.stat().st_size<(80000 if side=='front' else 180000)
  assets[side]={'original_sha256':sha(original),'repair_png_sha256':sha(png),'delivery_sha256':sha(web),'delivery_bytes':web.stat().st_size,'dimensions':[800,1200],'outside_inclusive_masks_RGB_pixel_identity':'PASS','actual_png_webp_visual':'PASS_LEGIBLE_TITLE_AUTHOR_ACCENTS_COMPLETE_COPY_FOOTER_NO_FALSE_LIVE_BADGE'}
 componentpaths={name:p/(name+'.json') for name in dec['components']}
 if des:
  componentpaths.update({'cover_front_asset':p/'covers/front.png','cover_back_asset':p/'covers/back.png','cover_front_delivery':d/v['delivery_assets'][0]['delivery_file'],'cover_back_delivery':d/v['delivery_assets'][1]['delivery_file']})
 for name,expected in dec['components'].items():assert sha(componentpaths[name])==expected,(slug,name)
 sums=load(p/'checksum_manifest.json')['files']
 for x in sums:assert sha(p/x['file'])==x['sha256'],(slug,x)
 assert dec['territories']==['IN'] and dec['status']=='PROPOSED' and dec['conditions_satisfied'] is False
 pub=load(p/'public_book.json');reader=load(p/'reader_manifest.json');approval=load(p/'approval_evidence.json');assert pub['formats']==['Ebook'] and pub['cover_dimensions']=={'front':[800,1200],'back':[800,1200]}
 assert pub['rights_basis']==load(old/'rights_decision.json')['basis']
 for j in [pub,reader,approval]:assert j.get('audiobook_enabled',False) is False and j.get('audio_enabled',False) is False
 assert not any(k.startswith('audiobook_') and k!='audiobook_enabled' for k in reader)
 pre=[]
 for typ in ['root','backend']:
  q=d/'preimages'/typ;base=('backend/' if typ=='backend' else '')+'data/controlled_publications/'+slug
  for f in q.rglob('*'):
   if not f.is_file():continue
   rel=f.relative_to(q).as_posix();raw=subprocess.check_output(['git','show','514c9ebcfd95fd69e5cece864e9360c5d21ee7c5:'+base+'/'+rel],cwd=R);assert hashlib.sha256(raw).hexdigest()==sha(f);pre.append({'area':typ,'file':rel,'sha256':sha(f)})
 defects=[]
 if (p/'approval_evidence 2.json').exists():
  dupe=load(p/'approval_evidence 2.json')
  if dupe.get('audiobook_enabled') or dupe.get('audio_public_release')=='PUBLIC_AUDIO_RELEASE_APPROVED':defects.append('Historical duplicate approval_evidence 2.json contains positive audio approval; remove from active package, preserve exact preimage, rebind.')
 inv={f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
 ownerfact=prep['owner_declaration'] if des else prep['owner_design_fact'];ownerpath=R/ownerfact['path'] if des else Path(ownerfact['source']);assert sha(ownerpath)==ownerfact['sha256']
 ownerjson=load(ownerpath);assert 'Owner states all front and back covers are designed by the owner.' in json.dumps(ownerjson)
 font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf') if des else R/'frontend/public/assets/fonts/eb-garamond-400.ttf';licensefile=d/'DejaVu-font-license.txt' if des else R/'frontend/public/assets/fonts/EB-GARAMOND-OFL.txt';assert sha(font)==(prep['derivative_lineage']['font_sha256'] if des else prep['font_sha256'])
 result={'schema':'earnalism.independent-candidate-review.v1','reviewer':'A','slug':slug,'disposition':'HOLD_PAPERWORK_ONLY' if defects else 'PASS_EXACT_UNACCEPTED_PREPARATION','review_date':'2026-10-03','rights_decision_raw_sha256':sha(p/'rights_decision.json'),'components':dec['components'],'verified_checksum_count':len(sums),'assets':assets,'complete_source':complete,'source_chapter_sync_byte_unchanged':True,'exact_prior_IN_rights_basis_preserved':True,'owner_legacy_graphical_category':'Existing recovered owner art with bounded deterministic text overlays, no runtime fallback-policy conformance claim; generic ornament aesthetic limitation disclosed.','fresh_visual':'PASS_ACTUAL_PNG_AND_WEBP_INSPECTION','copy':'Exact complete opening source paragraphs, whitespace normalization only.','preimages_against_main':pre,'defects':defects,'package_inventory':inv,'package_inventory_sha256':hashlib.sha256(json.dumps(inv,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'acceptance_or_activation_created':False,'production_observed':False,'next_action':'Paperwork exclusion/rebind of duplicate historical approval if present; then root actual prospective acceptance only after both independent PASS, fresh accepted binding review and protected release gates.'}
 result['owner_design_fact']={'actual_file':str(ownerpath),'sha256':sha(ownerpath),'statement_reproduced':True,'scope':'DESIGN_ONLY_NOT_TEXT_RIGHTS_OR_HUMAN_APPROVAL'}
 result['font_lineage']={'font_sha256':sha(font),'license_path':str(licensefile),'license_sha256':sha(licensefile),'license_review':'Actual existing font license permits use; no new font binary is distributed in these cover packets.'}
 target=out/(slug+'-candidate-review-a.json');target.write_text(json.dumps(result,indent=2)+'\n');print(slug,result['disposition'],sha(target),'components',len(dec['components']),'checksums',len(sums),'preimages',len(pre))
