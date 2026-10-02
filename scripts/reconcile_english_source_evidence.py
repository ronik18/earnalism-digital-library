#!/usr/bin/env python3
"""Read-only canonical English source reconciliation; receipts confer no authority."""
import argparse, hashlib, json, re, time, urllib.request, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'internal/legal/catalogue_clearance_20261002/english'
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_text()) if p.exists() else {}
def normalized(s): return re.sub(r'\s+',' ',unicodedata.normalize('NFC',s)).strip()
def pg_id(url):
 m=re.search(r'^https://(?:www\.)?gutenberg\.org/(?:ebooks/|cache/epub/)(\d+)',str(url))
 return int(m.group(1)) if m else None
def request(url):
 req=urllib.request.Request(url,headers={'User-Agent':'EarnalismSourceReconciliation/1.0 (read-only publication evidence)'})
 with urllib.request.urlopen(req,timeout=45) as r:
  raw=r.read();return raw,{'requested_url':url,'resolved_url':r.url,'http_status':r.status,'accessed_at':datetime.now(timezone.utc).isoformat(),'response_sha256':sha(raw)}
def inventory(root=ROOT):
 live=set(load(root/'data/controlled_launch.json').get('live_approved_slugs',[]));rows=[]
 for p in sorted((root/'data/controlled_publications').iterdir()):
  reader=load(p/'reader_manifest.json')
  if reader.get('language')!='en' or p.name in live:continue
  source=load(p/'source_evidence.json'); book=load(p/'public_book.json'); chapters=[]
  for f in sorted((p/'chapters').glob('*.json'),key=lambda f:(load(f).get('order',10**9),f.name)):
   c=load(f);body=c.get('content','');chapters.append({'id':c.get('id',f.stem),'content':body,'sha256':sha(body.encode()),'declared_hash_matches':c.get('content_hash')==sha(body.encode())})
  rows.append({'slug':p.name,'title':book.get('title',reader.get('title')),'author':book.get('author',reader.get('author')),'source':source,'gutenberg_id':pg_id(source.get('source_url')),'chapters':chapters,'reader_manifest':reader,'superseded_alias':reader.get('reader_release_status')=='SUPERSEDED_ALIAS_NOT_PUBLIC','canonical_slug':reader.get('canonical_slug'),'has_publication_authorization':load(p/'publication_authorization.json').get('publication_authorized') or load(p/'approval_evidence.json').get('publication_authorization'),'rights_decision':load(p/'rights_decision.json')})
 return rows
def strip_illustration_blocks(text):
 result=[];i=0
 while i<len(text):
  if text.startswith('[Illustration',i):
   j=i;depth=0
   while j<len(text):
    if text[j]=='[':depth+=1
    if text[j]==']':
     depth-=1
     if depth==0:j+=1;break
    j+=1
   if depth:raise ValueError('unclosed illustration caption')
   i=j
  else:result.append(text[i]);i+=1
 return ''.join(result)
def extract_pride_narrative(text):
 """Verified #1342 narrative only; separately authored preface/art are excluded."""
 text=text.replace('\r\n','\n').replace('\r','\n')
 start=text.index('It is a truth universally acknowledged')
 end=text.index('*** END OF THE PROJECT GUTENBERG')
 novel=text[start:end]
 headings=list(re.finditer(r'(?im)^[ \t]*chapter[ \t]+([ivxlcdm]+)\.?[ \t]*$',novel))
 if len(headings)!=60:raise ValueError('expected chapter II through LXI')
 segments=[novel[:headings[0].start()]]+[novel[h.end():(headings[n+1].start() if n+1<len(headings) else len(novel))] for n,h in enumerate(headings)]
 return ['\n\n'.join(re.sub(r'\s*\n\s*',' ',p).strip() for p in re.split(r'\n\s*\n',strip_illustration_blocks(segment).strip()) if p.strip()) for segment in segments]
def extract_dracula_preface(text):
 start=text.index('How these papers have been placed in sequence')
 end=text.index('\n\nDRACULA',start)
 return normalized(text[start:end])
def compare(chapters, text):
 source=normalized(text);at=0;matched=[];missing=[]
 for c in chapters:
  body=normalized(c['content']); pos=source.find(body,at) if body else -1
  if pos<0:missing.append(c['id'])
  else:matched.append({'chapter_id':c['id'],'offset':pos,'length':len(body)});at=pos+len(body)
 return {'method':'NFC plus whitespace only; exact ordered whole chapter containment; no punctuation or lexical normalization','status':'ALL_CHAPTERS_MATCH_SOURCE' if chapters and not missing else 'SOURCE_TEXT_DIFFERS','matched_chapters':matched,'nonmatching_chapters':missing,'complete_edition_proven':False,'limitation':'Containment proves represented chapter text, not omitted material or full edition completeness.'}
def licensed_story_text(raw):
 soup=BeautifulSoup(raw,'html.parser'); body=soup.select_one('.prp-pages-output')
 if body is None:raise ValueError('Exact transcluded source body absent')
 paragraphs=[p.get_text().replace('\u200b','').strip() for p in body.select('p')]
 if len(paragraphs)!=216 or paragraphs[2]!='THE MOST DANGEROUS GAME' or paragraphs[3]!='By RICHARD CONNELL':raise ValueError('Verified edition/story boundaries changed')
 narrative='\n\n'.join(paragraphs[5:])
 if not narrative.startswith('OFF there to the right') or not narrative.endswith('He had never slept in a better bed, Rainsford decided.'):raise ValueError('Narrative endpoints changed')
 return narrative

def licensed_necklace_text(raw):
 """Exact signed Sturges story, retaining the drop-cap first paragraph."""
 soup=BeautifulSoup(raw,'html.parser'); body=soup.select_one('.prp-pages-output')
 if body is None or 'Translated by Jonathan Sturges.' not in body.get_text():raise ValueError('Sturges attribution absent')
 first=body.select_one('.dropinitial')
 if first is None:raise ValueError('Verified drop-cap boundary absent')
 opening=[]
 for node in [first,*first.next_siblings]:
  if getattr(node,'name',None)=='p':break
  if getattr(node,'name',None)=='style':continue
  opening.append(node.get_text() if getattr(node,'name',None)else str(node))
 paragraphs=[''.join(opening).replace('\u200b','').strip()]+[x.get_text().replace('\u200b','').strip()for x in body.select('p')]
 result='\n\n'.join(paragraphs)
 if not result.startswith('SHE was one of those pretty and charming girls')or not result.endswith('It was worth at most five hundred francs!"'):raise ValueError('Selected story endpoints changed')
 return result

def cc0_boule_text(raw):
 import xml.etree.ElementTree as ET
 root=ET.fromstring(raw);ns={'x':'http://www.w3.org/1999/xhtml'};article=root.find('.//x:article',ns)
 if article is None or article.attrib.get('id')!='boule-de-suif':raise ValueError('Verified Boule story container absent')
 paragraphs=[''.join(p.itertext()).strip()for p in article.findall('.//x:p',ns)]
 result='\n\n'.join(paragraphs)
 if len(paragraphs)!=270 or not result.startswith('For several days in succession straggling remnants')or not result.endswith('broke out between two couplets in the darkness.'):raise ValueError('Boyd story boundaries changed')
 alltext=normalized(''.join(article.itertext()))
 if alltext!=normalized('Boule de Suif '+result):raise ValueError('Source narrative outside paragraph extraction')
 return result

def main():
 a=argparse.ArgumentParser();a.add_argument('--fetch',action='store_true');a.add_argument('--output-dir',type=Path,default=DEFAULT);args=a.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
 receipts=load(args.output_dir/'source_receipts.json');cache=Path('/tmp/earnalism-english-source-reconciliation');cache.mkdir(exist_ok=True)
 rows=inventory();results=[]
 boundary_path=args.output_dir/'current_whole_work_boundary_verification.json';boundaries={r['slug']:r for r in load(boundary_path).get('titles',[])}
 for number,row in enumerate(rows,1):
  gid=row['gutenberg_id'];key=str(gid);text=None
  if gid and args.fetch and key not in receipts:
   try:
    raw,meta=request(f'https://www.gutenberg.org/ebooks/{gid}'); soup=BeautifulSoup(raw,'html.parser');facts={}
    for tr in soup.select('table.bibrec tr'):
     th=tr.find('th');td=tr.find('td')
     if th and td:facts.setdefault(th.get_text(' ',strip=True),[]).append(td.get_text(' ',strip=True))
    link=next((x.get('href') for x in soup.select('a[href]') if 'text/plain' in x.get('type','')),None)
    if not link:link=f'https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt'
    if link.startswith('//'):link='https:'+link
    if link.startswith('/'):link='https://www.gutenberg.org'+link
    time.sleep(1);content,bodymeta=request(link);(cache/f'{gid}.txt').write_bytes(content)
    receipts[key]={'metadata_receipt':meta,'bibliographic_metadata':facts,'text_receipt':bodymeta,'gutenberg_license_scope':'US status only; India territorial/component clearance independently required','approval_conferred':False}
   except Exception as e:receipts[key]={'retrieval_error':type(e).__name__+': '+str(e),'attempted_at':datetime.now(timezone.utc).isoformat()}
   (args.output_dir/'source_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n');time.sleep(1)
  receipt=receipts.get(key,{})
  if gid and(cache/f'{gid}.txt').exists():text=(cache/f'{gid}.txt').read_text(encoding='utf-8-sig')
  if not gid and row['slug']=='the-most-dangerous-game' and (cache/'wikisource-most-dangerous-game.txt').exists():
   raw=(cache/'wikisource-most-dangerous-game.txt').read_bytes(); verified=row['source'].get('actual_transcription_verification',{}).get('receipt',{})
   if sha(raw)==verified.get('response_sha256'):
    text=licensed_story_text(raw);receipt={'text_receipt':verified,'bibliographic_metadata':{'Author':['Connell, Richard, 1893-1949']}};key='wikisource-revision-'+str(row['source'].get('source_revision'))
  if not gid and row['slug']=='boule-de-suif' and (cache/'standardebooks-boule-boyd.txt').exists():
   raw=(cache/'standardebooks-boule-boyd.txt').read_bytes(); verified=row['source'].get('actual_transcription_verification',{}).get('receipt',{})
   if sha(raw)==verified.get('response_sha256'):
    text=cc0_boule_text(raw);receipt={'text_receipt':verified,'bibliographic_metadata':{'Author':['Maupassant,Guyde,1850-1893'],'Translator':['Boyd,ErnestAugustus,1887-1946']}};key='standardebooks-boule-boyd'
  if not gid and row['slug']=='the-necklace' and (cache/'wikisource-necklace-sturges.txt').exists():
   raw=(cache/'wikisource-necklace-sturges.txt').read_bytes(); verified=row['source'].get('actual_transcription_verification',{}).get('receipt',{})
   if sha(raw)==verified.get('response_sha256'):
    text=licensed_necklace_text(raw);receipt={'text_receipt':verified,'bibliographic_metadata':{'Author':['Maupassant, Guy de,1850-1893'],'Translator':['Sturges,Jonathan,1864-1911']}};key='wikisource-necklace-sturges-'+str(row['source'].get('source_revision'))
  if not gid and row['slug']=='bharat-at-the-crossroads' and (cache/'first-party-bharat.txt').exists():
   raw=(cache/'first-party-bharat.txt').read_bytes(); actual=load(args.output_dir/'first_party_source_receipts.json').get('first-party-bharat',{})
   if sha(raw)==actual.get('text_receipt',{}).get('response_sha256')==row['source'].get('source_hash'):
    text=raw.decode('utf-8');receipt=actual;key='first-party-bharat'
  comparison=compare(row['chapters'],re.sub(r'\[Picture:[^\]]*\]\s*','',text) if row['source'].get('reader_text_furniture_removal',{}).get('transformation','').startswith('Remove nonnarrative Picture') else (strip_illustration_blocks(text) if row['source'].get('edition_migration_evidence') else text)) if text else {'status':'NOT_RETRIEVED','complete_edition_proven':False}
  facts=receipt.get('bibliographic_metadata',{}); authors=facts.get('Author',[]); deaths=[int(y) for s in authors for y in re.findall(r'\b\d{4}-(\d{4})\b',s)]
  identity={'chapter_count':len(row['chapters']),'declared_chapter_count':row['reader_manifest'].get('chapter_count'),'chapter_hashes_valid':all(c['declared_hash_matches'] for c in row['chapters']),'chapters':[{'id':c['id'],'sha256':c['sha256']} for c in row['chapters']],'reader_aggregate_sha256':sha('\n\n'.join(c['content'] for c in row['chapters']).encode())}
  gaps=[]
  if not row['source']:gaps.append('CANONICAL_SOURCE_EVIDENCE_ABSENT')
  if not gid and not text:gaps.append('NON_GUTENBERG_SOURCE_REQUIRES_DISTINCT_LICENSE_AND_REVISION_WORKFLOW')
  if text and receipt.get('text_receipt',{}).get('response_sha256')!=row['source'].get('source_hash'):gaps.append('DECLARED_SOURCE_HASH_NOT_REPRODUCED_BY_CURRENT_OFFICIAL_BYTES')
  if comparison['status']!='ALL_CHAPTERS_MATCH_SOURCE':gaps.append('EXACT_CHAPTER_TEXT_RECONCILIATION_REQUIRED')
  boundary=boundaries.get(row['slug'],{});boundary_current=bool(boundary and boundary.get('raw_source_sha256')==row['source'].get('source_hash') and boundary.get('reader_aggregate_sha256')==identity['reader_aggregate_sha256'] and boundary.get('ordered_chapter_hashes')=={c['id']:c['sha256'] for c in row['chapters']})
  text_clear=bool(boundary_current and row['source'].get('text_component_clearance',{}).get('whole_narrative_coverage')=='PASS' and row['rights_decision'].get('status')=='ACCEPTED')
  if not text_clear:gaps.append('FULL_EDITION_BOUNDARY_AND_COMPONENT_REVIEW_REQUIRED')
  if not row['rights_decision']:gaps.append('ACCEPTED_EDITION_BOUND_RIGHTS_RECORD_TO_GENERATE_AFTER_OBJECTIVE_CLEARANCE')
  if not row['has_publication_authorization']:gaps.append('EDITION_BOUND_PUBLICATION_RECORD_TO_GENERATE_UNDER_OWNER_DELEGATION_AFTER_GATES')
  results.append({'slug':row['slug'],'title':row['title'],'author':row['author'],'gutenberg_id':gid,'currently_non_live':True,'source_url':row['source'].get('source_url'),'declared_source_sha256':row['source'].get('source_hash'),'declared_content_sha256':row['source'].get('content_hash'),'observed_source_receipt_key':key if text else None,'source_comparison':comparison,'independent_whole_work_boundary_evidence':{'artifact':str(boundary_path.relative_to(ROOT)),'artifact_sha256':sha(boundary_path.read_bytes()),'slug':row['slug'],'immutable_identity_current':boundary_current,'coverage_review':boundary.get('whole_narrative_coverage_review'), 'containment_alone_is_not_completeness':True} if boundary else None,'canonical_reader_identity':identity,'author_death_year_candidates_from_official_catalog':deaths,'translator_metadata':facts.get('Translator',[]),'edition_notes':facts.get('Note',[]),'cover_review':'DEFERRED_BY_OWNER_REQUEST','noncover_gaps':gaps,'local_noncover_publication_authority_created':text_clear,'production_registry_registration_created':False,'status':'SUPERSEDED_ALIAS_DO_NOT_REACTIVATE' if row['superseded_alias'] else ('NON_COVER_TEXT_READY_COVER_DEFERRED_RUNTIME_HOLD' if text_clear else 'EVIDENCE_PREPARED_RELEASE_HELD'),'canonical_slug':row['canonical_slug']})
  print(number,row['slug'],comparison['status'],flush=True)
 report={'schema_version':'earnalism.english-source-reconciliation.v1','generated_at':datetime.now(timezone.utc).isoformat(),'canonical_live_approved_slugs':load(ROOT/'data/controlled_launch.json').get('live_approved_slugs',[]),'count':len(results),'scope':'LOCAL_NON_COVER_TEXT_EVIDENCE_AND_OWNER_DELEGATED_CLEARANCE_NO_RUNTIME_REGISTRY_OR_RELEASE_MUTATION','titles':results}
 (args.output_dir/'matrix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
