from pathlib import Path
import sys,json,hashlib
R=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'internal/audiobook_lab/scripts/factory_hooks'))
import asr_sync_hook as hook
source=json.loads((R/'backend/data/controlled_publications/sredni-vashtar/chapters/chapter-001.json').read_text())['content']
rows={}
for n in ['sredni-local-asr.json','sredni-turbo-local-asr.json']:
 d=json.loads((D/n).read_text());rows[n]=hook.transcript_similarity(source,d['transcript'])
p=R/'internal/audiobook_lab/scripts/factory_hooks/asr_sync_hook.py'
out={'scorer':str(p.relative_to(R))+':transcript_similarity','scorer_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'Existing complete local transcripts only; no inference/network/provider operation','results':rows,'raw_word_error_rate_scores_are_a_separate_diagnostic':True,'wording_omission_adjudication':'PENDING','release_ready':False}
(D/'sredni-repository-asr-metric.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(rows,indent=2))
