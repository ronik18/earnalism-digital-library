from pathlib import Path
import json,hashlib,unicodedata,subprocess
from PIL import Image,ImageChops,ImageDraw

repo=Path('/tmp/earnalism-main-approved-integration')
scratch=Path('/workspace/scratch/181ef0a25f05')
out=scratch/'new-acceptance-review-a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
norm=lambda s:' '.join(unicodedata.normalize('NFC',s).split())
load=lambda p:json.loads(Path(p).read_text())
boundarypath=repo/'internal/legal/catalogue_clearance_20261002/english/current_whole_work_boundary_verification.json'
boundaries={x['slug']:x for x in load(boundarypath)['titles']}
policy=repo/'internal/earnalism_intelligence/cover_acceptance_policy.json'
owner=repo/'internal/legal/bengali_text_preparation_20261002/evidence_matrix.json'

for slug,dirname in [('the-open-window','open-window-next-cohort'),('the-selfish-giant','selfish-giant-next-cohort'),('sredni-vashtar','sredni-preparation-20261003')]:
 d=scratch/dirname; sredni=slug=='sredni-vashtar'
 p=d/'proposed-package/data/controlled_publications'/slug if sredni else d/'proposal/data/controlled_publications'/slug
 old=d/'root-preimage' if sredni else d/'preimages/root'
 dec=load(p/'rights_decision.json'); checks=[]
 for name,expected in dec['components'].items():
  assetpaths={'cover_front_original_asset':d/'front-cover-current.png','cover_back_original_asset':d/'back-cover-current.png','cover_front_delivery_asset':d/'delivery-front.webp','cover_back_delivery_asset':d/'delivery-back.webp'}
  f=assetpaths.get(name,p/(name+'.json')); assert sha(f)==expected,(slug,name); checks.append({'component':name,'sha256':expected})
 sums=load(p/'checksum_manifest.json'); checked=[]
 for x in sums['files']:
  f=p/x['file']; assert sha(f)==x['sha256'],(slug,x); checked.append(x)
 chapter=load(p/'chapters/chapter-001.json'); text=chapter['content']; content=hashlib.sha256(text.encode()).hexdigest()
 b=boundaries[slug]; se=load(p/'source_evidence.json')
 assert content==b['reader_aggregate_sha256']==b['ordered_chapter_hashes']['chapter-001']==se['content_hash']
 assert se['source_hash']==b['raw_source_sha256']
 assert norm(text).startswith(norm(b['first_body_anchor'])) and norm(text).endswith(norm(b['last_body_anchor']))
 assert b['internal_gaps']==[] and b['chapter_count']==1
 assert sha(p/'source_evidence.json')==sha(old/'source_evidence.json')
 assert sha(p/'chapters/chapter-001.json')==sha(old/'chapters/chapter-001.json')
 assert sha(p/'highlight_sync.json')==sha(old/'highlight_sync.json')
 preimages=[]
 dirs=[('root',d/'root-preimage'),('backend',d/'backend-preimage'),('content',d/'content-preimage')] if sredni else [('root',d/'preimages/root'),('backend',d/'preimages/backend')]
 for typ,pre in dirs:
  base={'root':'data/controlled_publications/'+slug,'backend':'backend/data/controlled_publications/'+slug,'content':'content/books/'+slug}[typ]
  for f in sorted(pre.rglob('*')):
   if not f.is_file():continue
   rel=f.relative_to(pre).as_posix()
   mainbytes=subprocess.check_output(['git','show','514c9ebcfd95fd69e5cece864e9360c5d21ee7c5:'+base+'/'+rel],cwd=repo)
   assert hashlib.sha256(mainbytes).hexdigest()==sha(f),(slug,typ,rel)
   preimages.append({'area':typ,'file':rel,'sha256':sha(f)})
 assets={}
 if sredni:
  receipt=load(d/'candidate-cover-receipt.json'); proposed=load(d/'proposed-cover-binding.json')
  excerpt=receipt['copy']['short_description']; assert norm(text).startswith(excerpt)
  assert proposed['proposed_public_metadata_correction']['description']==excerpt
 else:
  receipt=load(d/'repair-receipt.json'); excerpt=receipt['source_excerpt'];assert norm(text).startswith(excerpt)
 for side in ['front','back']:
  if sredni:
   original=d/(side+'-cover-current.png'); new=d/('candidate-'+side+'-run1.png'); delivery=d/('delivery-'+side+'.webp')
   expectedOriginal=receipt['originals'][side]['sha256'];expectedNew=receipt['renders'][side]['sha256'];expectedDelivery=proposed['delivery'][side]['sha256'];rects=receipt['renders'][side]['changed_region_rectangles']
   assert sha(new)==sha(d/('candidate-'+side+'-run2.png'))
  else:
   a=receipt['assets'][side];original=d/(side+'-original.png');new=d/(side+'-layout-repair.png');delivery=d/(side+'-delivery.webp');expectedOriginal=a['original_sha256'];expectedNew=a['layout_png']['sha256'];expectedDelivery=a['delivery']['sha256'];rects=a['repair_zones']
  assert sha(original)==expectedOriginal and sha(new)==expectedNew and sha(delivery)==expectedDelivery
  with Image.open(original) as im: im.load();before=im.convert('RGB')
  with Image.open(new) as im: im.load();after=im.convert('RGB');assert im.size==(1600,2400)
  mask=Image.new('L',before.size,255);draw=ImageDraw.Draw(mask)
  for x1,y1,x2,y2 in rects: draw.rectangle((x1,y1,x2,y2),fill=0)
  diff=ImageChops.difference(before,after);masked=Image.composite(diff,Image.new('RGB',diff.size),mask)
  assert masked.getbbox() is None,(slug,side,'pixels outside masks')
  with Image.open(delivery) as im:im.load();assert im.size==(800,1200)
  assert delivery.stat().st_size < (80000 if side=='front' else 180000)
  assets[side]={'original_sha256':sha(original),'repaired_png_sha256':sha(new),'delivery_sha256':sha(delivery),'delivery_bytes':delivery.stat().st_size,'dimensions':[800,1200],'outside_mask_rgb_pixels_unchanged':True,'actual_png_and_webp_visual_inspection':'PASS_LEGIBLE_COMPLETE_COPY_TITLE_AUTHOR_FOOTER_NO_FALSE_LIVE_BADGE'}
 reader=load(p/'reader_manifest.json'); pub=load(p/'public_book.json')
 assert reader.get('audio_enabled') is False and reader.get('audiobook_enabled') is False
 assert not any(k.startswith('audiobook_') and k!='audiobook_enabled' for k in reader)
 assert pub['formats']==['Ebook']
 assert dec['status'] in ['PROPOSED','PENDING_REVIEW'] and dec['conditions_satisfied'] is False
 if sredni:
  assert proposed['artwork_category']=='RECOVERED_OWNER_DESIGNED_LEGACY_GRAPHICAL_COMPONENT_WITH_LAYOUT_AND_TEXT_OVERLAY_DERIVATIVE'
  assert 'no runtime graphical-fallback policy conformance is claimed' in proposed['substantive_review_issue']
  assert pub['description']==excerpt
  for f in p.rglob('*'):
   if f.is_file():assert sha(f)==sha(d/'proposed-package/backend/data/controlled_publications'/slug/f.relative_to(p))
 inv={f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
 result={'schema':'earnalism.independent-next-cohort-review.v1','reviewer':'A','slug':slug,'disposition':'PASS_EXACT_VISUAL_LINEAGE_SOURCE_AND_PREPARATION_BINDING_PENDING_POLICY_CLASSIFICATION_CLARIFICATION','review_date':'2026-10-03','authority':'Prospective Oct3 owner delegation; this reviewer does not accept, register or activate anything.','package_stage':'UNACCEPTED_PROPOSAL' if not sredni else 'UNACCEPTED_PROPOSED_COVER_BINDING_TO_UNCHANGED_TEXT_PREIMAGE','components_checked':checks,'checksums_checked':checked,'source_and_complete_selected_narrative':{'status':'PASS_REUSED_IMMUTABLE_BOUNDARY_EVIDENCE','boundary_artifact':str(boundarypath.relative_to(repo)),'boundary_artifact_sha256':sha(boundarypath),'source_sha256':b['raw_source_sha256'],'content_sha256':content,'first_last_anchors_match_current_chapter':True,'internal_gaps':[],'source_evidence_chapter_and_highlight_byte_unchanged':True,'new_source_fetches':0,'containment_alone_is_not_completeness':True,'coverage_scope':b['selected_edition_scope']},'assets':assets,'copy':'Exact whitespace-normalized complete existing opening copy; no invented narrative fact.','provenance':{'owner_declaration_path':str(owner.relative_to(repo)),'owner_declaration_sha256':sha(owner),'actual_category':'Existing owner-designed legacy graphical artwork with bounded deterministic text overlay and disclosed derivative lineage. This is not a runtime graphical fallback image.','rights_not_inferred_from_visual_review':True},'policy':{'path':str(policy.relative_to(repo)),'sha256':sha(policy),'graphical_not_typography_only':True,'deterministic_title_author_overlay':True,'generic_theme_aesthetic_limitation':'Generic gold ornament lacks a story-specific motif; prior Sredni criticism preserved. As owner legacy graphical derivative this aesthetic limitation does not independently create a missing-rights finding.','required_paperwork_delta':'Remove any unsupported assertion that baked-title/author asset satisfies literal runtime fallback_policy; name actual legacy-owner-derived graphical category. Preserve all prior reviews.','build_performance_runtime_gates':'Remain pending exact integration and normal checks; no Lighthouse regression observed or claimed.'},'preservation_preimages_verified_against_main':preimages,'package_inventory_sha256':hashlib.sha256(json.dumps(inv,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'package_inventory':inv,'audio':'DISABLED_NO_NEW_AUDIO_AUTHORIZATION; historical audio materials preserved as preimages.','production_observed':False,'registry_allowlist_release_mutations':False,'next_action':'After both independent PASS and policy classification paperwork correction, root may record actual prospective automated acceptance and rebind every changed component, followed by fresh exact accepted-package/integrated-tree review.'}
 if sredni:result['proposed_cover_binding_sha256']=sha(d/'proposed-cover-binding.json')
 else:result['rights_decision_raw_sha256']=sha(p/'rights_decision.json');result['audio_correction_sha256']=sha(d/'audio-metadata-correction.json')
 result['disposition']='PASS_EXACT_UNACCEPTED_PREPARATION_VISUAL_LINEAGE_SOURCE_AND_PACKAGE_BINDING'
 result['rights_decision_raw_sha256']=sha(p/'rights_decision.json')
 result['package_stage']='UNACCEPTED_PROPOSAL'
 result['policy']['required_paperwork_delta']='NONE: actual owner legacy graphical derivative is reviewed; literal runtime fallback conformance is not claimed. Exact accepted bindings still require fresh serialized review.'
 result['next_action']='After both independent preparation PASS, root may create actual prospective automated acceptance and rebind all changed components. Fresh exact accepted-package/integrated-tree review then protected checks, deployment/canary and truthful readback are required before release.'
 target=out/(slug+'-next-review-a.json');target.write_text(json.dumps(result,indent=2)+'\n')
 print(slug,sha(target),'components',len(checks),'checksums',len(checked),'preimages',len(preimages))
