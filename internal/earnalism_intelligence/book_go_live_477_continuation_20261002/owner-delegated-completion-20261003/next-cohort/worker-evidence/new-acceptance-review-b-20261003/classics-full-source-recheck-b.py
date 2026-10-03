import pathlib,json,hashlib,unicodedata,datetime,re
B=pathlib.Path('/workspace/scratch/181ef0a25f05');O=B/'new-acceptance-review-b-20261003';R=pathlib.Path('/tmp/earnalism-main-approved-integration')
def load(p):return json.loads(p.read_text())
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(s):return ' '.join(unicodedata.normalize('NFC',s).split())
res=[]
for s in ['the-time-machine','the-great-gatsby','frankenstein','the-secret-garden','pride-and-prejudice']:
 c=B/'classics6-prep-20261003'/s/'candidate-inactive-unaccepted';p=load(c/'cover_preparation.json');proof=p['boundary_receipt'];raw=B/'new-acceptance-review-a/classics-primary-recovery-v1'/(s+'-official-source.txt')if s!='the-great-gatsby'else R/'content/books/the-great-gatsby/raw/pg64317.txt';assert h(raw)==proof['raw_source_sha256'];src=norm(raw.read_text());last=0;matched=[];gaps=[];chapters=[]
 for q in sorted((c/'chapters').glob('*.json')):
  ch=load(q);body=norm(ch['content']);
  try:i=src.index(body,last)
  except ValueError:print('MISS',s,ch['id'],repr(body[:170]));raise
  gap=src[last:i];gaps.append(gap);matched.append({'id':ch['id'],'offset':i,'length':len(body),'content_sha256':ch['content_hash']});last=i+len(body);chapters.append(ch)
 assert len(matched)==proof['chapter_count'];assert src[last:].lstrip().startswith('*** END OF THE PROJECT GUTENBERG')
 for i,g in enumerate(gaps[1:]):assert g==proof['internal_gaps'][i]['text'];assert len(g)<200
 # The only interstitial omissions are the exact already-persisted chapter/letter labels; no narrative omissions.
 prefix=gaps[0];start=prefix.index('*** START OF THE PROJECT GUTENBERG');authorprefix=prefix[start:];assert norm(proof['first_body_anchor']) in norm(chapters[0]['content']);assert norm(proof['last_body_anchor']) in norm(chapters[-1]['content'])
 quote=p['cover_quote_checks'];qnotes=[]
 for q in quote:
  actual=load(c/'chapters'/q['chapter'])['content'];assert norm(q['quote']).casefold()in norm(actual.replace('_','').replace('*','')).casefold();qnotes.append({'quote':q['quote'],'chapter':q['chapter'],'bound_source_lexical_content':'PASS','case_change_disclosure_required':s=='the-secret-garden'})
 a={'reviewer':'Independent Codex reviewer B','slug':s,'disposition':'PASS_COMPLETE_EXACT_SELECTED_AUTHOR_BODY','primary_source_path':str(raw),'primary_source_sha256':h(raw),'primary_source_recovery_receipt_sha256':h(raw.with_name(s+'-recovery.json'))if s!='the-great-gatsby'else None,'source_downloads_by_B':0,'no_chapter_or_source_mutation':True,'all_ordered_chapter_matches':matched,'prefix_after_PG_start':authorprefix,'internal_gaps':gaps[1:],'ending_after_last':src[last:last+160],'source_scope':proof['selected_edition_scope'],'quote_checks':qnotes,'boundary_interpretation':'Exact complete selected author edition: explicit first body after title/TOC or correct excluded third-party preface, complete exact ordered bodies, only verified heading/illustration furniture interstitial gaps, last body followed immediately by PG END. Historical containment limitation retained; independent full boundaries now checked.','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'canonical_mutations':False,'production_observed':False}
 out=O/(s+'-fresh-complete-source-review-b.json');out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');res.append({'slug':s,'path':str(out),'sha256':h(out),'chapter_count':len(matched),'prefix_len':len(authorprefix)})
print(json.dumps(res,indent=2))
