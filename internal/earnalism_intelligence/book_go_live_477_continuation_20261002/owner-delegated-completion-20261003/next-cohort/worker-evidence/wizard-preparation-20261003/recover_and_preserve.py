from pathlib import Path
from datetime import datetime,timezone
import urllib.request,hashlib,json,shutil
from PIL import Image
B=Path(__file__).resolve().parent;R=Path('/tmp/earnalism-main-approved-integration');S='the-wonderful-wizard-of-oz';H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,t in [('root-preimage','data/controlled_publications'),('backend-preimage','backend/data/controlled_publications')]:shutil.copytree(R/t/S,B/n)
shutil.copytree(R/'content/books'/S,B/'content-preimage')
owner=Path('/workspace/scratch/181ef0a25f05/next-owner-accepted-nine-20261003-v1/data/controlled_publications/acres-of-diamonds/owner_artwork_declaration.json');assert H(owner)=='0881001b09b5b47649f14ff289aaa7f64e98004adc3d800f67d90fab703f9264';shutil.copy2(owner,B/'owner_artwork_declaration.json')
proof=R/'internal/legal/catalogue_clearance_20261002/english/current_whole_work_boundary_verification.json';assert H(proof)=='6d5922046002670c8f26c47ae0d5ee6d1fc9c18481ef9e6750ca91496c35b90e';shutil.copy2(proof,B/'current_whole_work_boundary_verification.json');row=next(x for x in json.loads(proof.read_text())['titles'] if x['slug']==S);(B/'wizard-whole-work-proof-reuse.json').write_text(json.dumps({'scope':'UNCHANGED_EXACT_SOURCE_BOUNDARY_AND_25_CHAPTER_PROOF_REUSE_NO_SOURCE_REQUEST','proof_artifact_sha256':H(proof),'title_proof':row},ensure_ascii=False,indent=2)+'\n')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(NoRedirect)
meta=json.loads((B/'backend-preimage/public_book.json').read_text());assets={}
for side,key in [('front','cover_image_url'),('back','back_cover_image_url')]:
 url=meta[key];req=urllib.request.Request(url,headers={'User-Agent':'Earnalism-authorized-exact-cover-recovery/1.0'})
 with opener.open(req,timeout=30) as response:
  assert response.status==200;blob=response.read();headers=dict(response.headers);resolved=response.geturl()
 p=B/f'original-{side}.png';p.write_bytes(blob);im=Image.open(p);im.load();assets[side]={'kind':side,'path':str(p),'url':url,'resolved_url':resolved,'http_status':200,'sha256':H(p),'bytes':len(blob),'width':im.width,'height':im.height,'mode':im.mode,'request_count':1,'redirects_allowed':False,'retrieved_at':datetime.now(timezone.utc).isoformat(),'content_type':headers.get('Content-Type')}
(B/'original-cover-receipt.json').write_text(json.dumps({'slug':S,'source':'Exact persisted historical backend public_book URL pair; no provider, generation or fresh artwork rights research','assets':assets,'network_requests':2},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(assets,indent=2))
