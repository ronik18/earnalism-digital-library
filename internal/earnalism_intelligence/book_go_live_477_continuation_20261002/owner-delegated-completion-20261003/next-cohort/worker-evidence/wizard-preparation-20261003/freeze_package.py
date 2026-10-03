from pathlib import Path
import json,hashlib,shutil
from PIL import Image
B=Path(__file__).resolve().parent;S='the-wonderful-wizard-of-oz';stage=B/'proposed-package';P=stage/'data/controlled_publications'/S;Q=stage/'backend/data/controlled_publications'/S;H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();W=lambda p,o:p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n');C=lambda o:hashlib.sha256(json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
E=P/'evidence';E.mkdir(exist_ok=True);cover=P/'covers';cover.mkdir(exist_ok=True)
for n in ['wizard-whole-work-proof-reuse.json','current_whole_work_boundary_verification.json','original-cover-receipt.json','delivery-receipt.json','render_delivery.py','preimage-inventory.json']:shutil.copy2(B/n,E/n)
shutil.copy2(B/'owner_artwork_declaration.json',P/'owner_artwork_declaration.json')
for side in ['front','back']:shutil.copy2(B/f'original-{side}.png',cover/f'original-{side}.png')
check=json.loads((P/'checksum_manifest.json').read_text());names={e['file'] for e in check['files']}
for f in [P/'owner_artwork_declaration.json',*E.iterdir(),*cover.iterdir()]:
 n=str(f.relative_to(P));assert n not in names;check['files'].append({'file':n,'sha256':H(f)})
W(P/'checksum_manifest.json',check)
manifest=json.loads((P/'publication_manifest.json').read_text());manifest['artifacts']['checksum_manifest']=H(P/'checksum_manifest.json');manifest.pop('manifest_sha256',None);manifest['manifest_sha256']=C(manifest);W(P/'publication_manifest.json',manifest)
decision=json.loads((P/'rights_decision.json').read_text());decision['components']['checksum_manifest']=H(P/'checksum_manifest.json');decision['components']['publication_manifest']=H(P/'publication_manifest.json');decision['components']['owner_artwork_declaration']=H(P/'owner_artwork_declaration.json');W(P/'rights_decision.json',decision)
shutil.copytree(P,Q,dirs_exist_ok=True)
validation=json.loads((stage/'validation.json').read_text());validation.update({'decision_file_sha256':H(P/'rights_decision.json'),'decision_canonical_sha256':C(decision),'controlled_checksums':len(check['files']),'controlled_checksums_pass':all(H(P/e['file'])==e['sha256'] for e in check['files']),'root_backend_byte_identity':all((Q/f.relative_to(P)).read_bytes()==f.read_bytes() for f in P.rglob('*') if f.is_file()),'decision_components':len(decision['components']),'owner_artwork_declaration_sha256':H(P/'owner_artwork_declaration.json'),'originals_archived_exact':True,'source_requests':0,'original_cover_requests':2,'art_repairs':0,'paid_calls':0,'all_source_license_highlight_and_chapters_unchanged':all((P/n).read_bytes()==(B/'root-preimage'/n).read_bytes() for n in ['source_evidence.json','license_notice.json','highlight_sync.json'] if (B/'root-preimage'/n).exists()) and all(f.read_bytes()==(B/'root-preimage/chapters'/f.name).read_bytes() for f in (P/'chapters').glob('*.json'))});assert validation['controlled_checksums_pass'] and validation['root_backend_byte_identity'] and validation['all_source_license_highlight_and_chapters_unchanged'];W(stage/'validation.json',validation)
for side,a in json.loads((B/'delivery-receipt.json').read_text())['assets'].items():assert H(Path(a['path']))==a['sha256'];Image.open(a['path']).load()
print(json.dumps({'binding':H(B/'proposed-cover-binding.json'),'validation':H(stage/'validation.json'),'decision_raw':H(P/'rights_decision.json'),'decision_canonical':C(decision),'components':len(decision['components']),'checksums':len(check['files']),'package':str(P)},indent=2))
