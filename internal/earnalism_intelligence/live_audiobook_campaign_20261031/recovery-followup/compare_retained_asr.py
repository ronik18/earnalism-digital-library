from pathlib import Path
import json,hashlib,re,difflib
R=Path('/tmp/earnalism-audiobook-recovery-followup-20261031');S=Path('/tmp/earnalism-main-approved-integration/backend/data/controlled_publications/sredni-vashtar/chapters/chapter-001.json');T=Path('/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/audiobook_lab/release_gate/sredni-vashtar_20260705T195720Z/timestamps.json');assert not T.stat().st_flags&0x40000000
def tok(x):return re.findall(r"[a-z0-9]+(?:'[a-z]+)?",x.lower().replace('’',"'"))
a=tok(json.loads(S.read_text())['content']);d=json.loads(T.read_text());b=tok(' '.join(w['word'] for w in d['words']));changes=[]
for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
 if tag!='equal':changes.append({'kind':tag,'source_word_index':i,'expected':' '.join(a[i:j]),'historical_ASR':' '.join(b[k:l]),'context':' '.join(a[max(0,i-4):min(len(a),j+4)])})
report={'source_content_sha256':hashlib.sha256(json.loads(S.read_text())['content'].encode()).hexdigest(),'timestamp_sha256':hashlib.sha256(T.read_bytes()).hexdigest(),'audio_hash':d['audio_hash'],'generation_source_hash':d['source_text_hash'],'current_canonical_plus_LF_equals_generation_hash':hashlib.sha256((json.loads(S.read_text())['content']+'\n').encode()).hexdigest()==d['source_text_hash'],'comparison':'Exact retained audio-derived historical words versus current canonical; no source spelling correction or transcript rewrite.','historical_ASR_disagreements':changes,'decision':'Disagreements are review locators, not adjudication or listening PASS','release_ready':False}
(R/'sredni-historical-asr-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'historical_difference_groups':len(changes),'differences':changes[:15]},indent=2))
