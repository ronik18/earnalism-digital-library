#!/usr/bin/env python3
"""Compare held Bengali chapters to recorded source revisions; never publish.

Fetches only public source pages, paced at eight seconds, and writes a separate
internal evidence/proposal tree. Canonical book packages are never mutated.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.bengali_text_compliance_audit import fetch_json, canonical_identity


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def fold(value: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC',value).replace('\u200b','').replace('\ufeff','')).strip()


def paragraphs(html: str, title: str) -> tuple[list[str],list[dict]]:
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser')
    body=soup.select_one('.mw-parser-output') or soup
    # Original literary notes can sit in a references list outside transcluded prose.
    # Keep their text separately instead of proposing deletion from the edition.
    notes=[]
    for note in soup.select('.reference-text'):
        for br in note.find_all('br'):br.replace_with('\n')
        text=note.get_text('',strip=False).strip()
        if fold(text):notes.append('↑ '+text)
    for n in body.select('table.headertemplate, table.toc, .headertemplate, .references, .ws-noexport, .noprint, .pagenum, .mw-editsection, script, style, sup.reference, .wikisource-header, .wikisource-header-template, .pagetext-header, .pagetext-footer'):
        n.decompose()
    # ProofreadPage may emit literary text directly between page markers, outside p.
    # Preserve those nodes; using find_all('p') silently truncates valid editions.
    for n in body.select('.__nop, .wst-nop, .wst-dhr'):
        n.replace_with('\n\n')
    for n in body.find_all('p'):
        n.insert_before('\n\n');n.insert_after('\n\n')
    for n in body.find_all(['td','th']):
        n.insert_before('\n');n.insert_after('\n')
    for n in body.find_all('br'):n.replace_with('\n')
    result=[p.strip() for p in re.split(r'\n\s*\n',body.get_text('',strip=False))]
    result=[p for p in result if fold(p)]
    furniture=[]
    while result and fold(result[0])==fold(title.rsplit('/',1)[-1]):
        furniture.append({'kind':'standalone_title','text':result.pop(0)})
    if result and re.fullmatch(r'[০-৯]{4}[?।]?',fold(result[-1])):
        furniture.append({'kind':'source_dateline_not_verified_first_publication','text':result.pop()})
    result.extend(notes)
    return result,furniture


def difference(canonical: str, source: list[str]) -> dict:
    canon=[p.strip() for p in re.split(r'\n\s*\n',canonical) if fold(p)]
    left=[fold(p) for p in canon];right=[fold(p) for p in source]
    sm=SequenceMatcher(a=left,b=right,autojunk=False)
    changes=[]
    for kind,a,b,c,d in sm.get_opcodes():
        if kind!='equal':
            changes.append({'operation':kind,'canonical_paragraph_range':[a,b],'source_paragraph_range':[c,d],
                'canonical':canon[a:b],'source':source[c:d]})
    return {'status':'EXACT_MATCH_FORMATTING_ONLY' if fold(canonical)==fold('\n\n'.join(source)) else 'SOURCE_RECONCILIATION_REQUIRED',
        'canonical_paragraph_count':len(left),'source_paragraph_count':len(right),
        'exact_paragraph_ratio':sm.ratio(),'changes':changes,
        'folding':'NFC, BOM/zero-width space removal and whitespace only; no letters/punctuation changed'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'internal/legal/catalogue_clearance_20261002/bengali')
    ap.add_argument('--fetch',action='store_true')
    ap.add_argument('--slug',action='append')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    baseline=json.loads((ROOT/'internal/legal/bengali_text_preparation_20261002/evidence_matrix.json').read_text())
    bankim=json.loads((ROOT/'data/title_rights_evidence/bengali-bankim-cohort-1.json').read_text())
    known={r['slug']:r for r in bankim['titles']}
    publication_facts={}
    for name,key in [('tagore-publication-facts.json','facts'),('tagore-printed-first-publication-datelines.json','verified_facts'),('tagore-volume3-printed-publication-datelines.json','facts')]:
        fact_path=args.output/name
        if fact_path.exists():
            for fact in json.loads(fact_path.read_text()).get(key,[]):
                if fact.get('publication_year') is not None:publication_facts[fact['slug']]=fact
    selected=[r for r in baseline['titles'] if r['slug']!='book-2b9853ec52' and (not args.slug or r['slug'] in args.slug)]
    repair_path=args.output/'applied-repairs.json'
    changed_slugs=set(json.loads(repair_path.read_text()).get('changed_slugs',[])) if repair_path.exists() else set()
    rows=[]
    for row in selected:
        slug=row['slug'];package=ROOT/'data/controlled_publications'/slug
        identity=canonical_identity(package);texts=identity.pop('texts')
        result={'slug':slug,'title':row['title'],'author':row['author'],'identity':identity,
            'cover_binding_deferred':row['cover_provenance']['front_binding']=='MISSING',
            'source_identity':row['source'], 'canonical_packages_mutated':slug in changed_slugs,
            'underlying_rights':'LIFETIME_PUBLICATION_EVIDENCE_COMPLETE' if slug in known or slug in publication_facts else 'TITLE_FIRST_PUBLICATION_FACT_REQUIRED',
            'edition':known.get(slug,{}).get('source_edition') or row['source'].get('page_title'),
            'original_publication_evidence':known.get(slug,{}).get('original_publication_year') or publication_facts.get(slug),
            'transcription_license':'CC-BY-SA-4.0',
            'license_conditions':['public attribution with source/permalink/contributors','license link','specific change notice','ShareAlike','no additional restrictions on licensed transcription'],
            'publication_decision_workflow':'Exact evidence-bound automated acceptance may truthfully identify executor under direct owner delegation only after all objective licence/identity conditions pass; no invented human identity.',
            'audio_authorized':False}
        snapshot=args.output/(slug+'-final-source-comparison.json')
        if not snapshot.exists():snapshot=args.output/(slug+'-complete-source-comparison.json')
        if not snapshot.exists():snapshot=args.output/(slug+'-source-comparison.json')
        if snapshot.exists():
            content=json.loads(snapshot.read_text())
            source_paragraphs=list(content.get('source_paragraphs',[]))
            chapter_titles=[c['title'] for c in identity['chapters']]
            if len(chapter_titles)>1 and all(t.isdigit() for t in chapter_titles):
                source_paragraphs=[v for v in source_paragraphs if v not in chapter_titles]
            canonical_text='\n\n'.join(texts)
            if source_paragraphs and re.sub(r'[\s-]+','',fold(source_paragraphs[0]).rstrip('।.'))==re.sub(r'[\s-]+','',fold(row['title']).rstrip('।.')) and not fold(canonical_text).startswith(fold(source_paragraphs[0])):
                source_paragraphs=source_paragraphs[1:]
            content['comparison']=difference(canonical_text,source_paragraphs)
            # Existing source files remain immutable; only the current matrix is refreshed.
        elif args.fetch and row['source'].get('revision_id') and len(identity['chapters'])<=3:
            print('Fetching pinned source '+slug,flush=True)
            try:
                data,receipt=fetch_json({'action':'parse','oldid':row['source']['revision_id'],'prop':'text|wikitext|links','format':'json','formatversion':'2'})
            except Exception as e:
                result['fetch_status']='FETCH_FAILED '+str(e);rows.append(result)
                if getattr(e,'code',None)==429:args.fetch=False  # Preserve all later audit rows without further provider requests.
                continue
            parsed=data.get('parse',{});html=parsed.get('text','')
            source,furniture=paragraphs(html,parsed.get('title',''))
            content={'slug':slug,'identity':identity,'retrieval_receipt':receipt,
                'rendered_source_sha256':digest(html),'source_wikitext':parsed.get('wikitext',''),
                'source_text_sha256':digest('\n\n'.join(source)),
                'source_paragraphs':source,'source_furniture':furniture,
                'transcription_license':'CC-BY-SA-4.0','attribution':{'title':parsed.get('title'),'author':row['author'],'source':row['source'].get('permalink'),'contributors':row['source'].get('contributors'),'license_url':'https://creativecommons.org/licenses/by-sa/4.0/'},
                'comparison':difference('\n\n'.join(texts),source),
                'exact_snapshot_scope':'Rendered response hash binds current expansion of parent oldid; parent revision alone does not freeze transcluded scan-page revisions.',
                'publication_authorized':False,'canonical_packages_mutated':False}
            snapshot.write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n')
        else:content={}
        if slug=='muchiram-gurer-jibanchorit' and (args.output/'muchiram-fourteen-chapter-source-comparison.json').exists():
            result['source_comparison']={'status':'EXACT_SAME_EDITION_14_CHAPTERS_RESTORED','artifact':str((args.output/'muchiram-fourteen-chapter-source-comparison.json').relative_to(ROOT))}
            result['noncover_status']='OBJECTIVE_SOURCE_AND_WORK_RIGHTS_COMPLETE_EDITORIAL_EVIDENCE_AND_LICENCE_IMPLEMENTATION_REQUIRED'
        elif slug=='bn-060':
            result['source_comparison']=row['source_comparison']
            result['noncover_status']='OBJECTIVE_SOURCE_AND_WORK_RIGHTS_COMPLETE_LICENCE_IMPLEMENTATION_REQUIRED'
        elif content:
            diff=content.get('comparison',{})
            result['source_comparison']={k:v for k,v in diff.items() if k!='changes'}
            result['comparison_artifact']=snapshot.relative_to(ROOT).as_posix()
            result['source_rendered_sha256']=content.get('rendered_source_sha256')
            result['noncover_status']='SOURCE_TEXT_REPAIR_REQUIRED' if diff.get('status')!='EXACT_MATCH_FORMATTING_ONLY' else 'OBJECTIVE_SOURCE_AND_WORK_RIGHTS_COMPLETE_LICENCE_IMPLEMENTATION_REQUIRED' if slug in publication_facts else 'EDITION_PUBLICATION_FACT_AND_LICENCE_IMPLEMENTATION_REQUIRED'
        else:
            result['source_comparison']=row['source_comparison']
            result['noncover_status']='MULTICHAPTER_EXACT_EDITION_RECONCILIATION_REQUIRED'
        source_current=json.loads((package/'source_evidence.json').read_text())
        result['canonical_source_sha256']=source_current.get('source_hash')
        if source_current.get('verified_lifetime_publication_year'):
            result['underlying_rights']='LIFETIME_PUBLICATION_EVIDENCE_COMPLETE'
            result['first_periodical_publication_year']='DISPUTED_NOT_INVENTED; definite lifetime book publication evidenced'
            if result['source_comparison'].get('status')=='EXACT_MATCH_FORMATTING_ONLY':result['noncover_status']='OBJECTIVE_SOURCE_AND_WORK_RIGHTS_COMPLETE_EDITION_EDITORIAL_EVIDENCE_REQUIRED'
        multi=args.output/(slug+'-multichapter-source-comparison.json')
        if multi.exists():
            m=json.loads(multi.read_text());checks=m['comparisons'];complete=all(c['comparison']['status']=='EXACT_MATCH_FORMATTING_ONLY' for c in checks)
            result['source_comparison']={'status':'EXACT_MATCH_FORMATTING_ONLY' if complete else 'SOURCE_RECONCILIATION_REQUIRED','chapters_verified':len(checks),'artifact':str(multi.relative_to(ROOT))}
            result['noncover_status']='EXACT_CURRENT_SOURCE_COMPLETE_EDITION_LAYER_EVIDENCE_REQUIRED' if complete else 'SOURCE_TEXT_REPAIR_REQUIRED'
        if source_current.get('original_edition_migration'):
            result['source_comparison']={'status':'EXACT_MATCH_FORMATTING_ONLY','scope':'Intentional original1894 edition replacement, historical variant identity preserved; not equality to oldedition','artifact':source_current['original_edition_migration']['artifact']}
            result['edition']=source_current.get('edition_evidence',{}).get('edition','Original1894 Katha-Chatushtay')
        if slug=='book-4968248842':
            result['source_comparison']={'status':'EXACT_MATCH_FORMATTING_ONLY','artifact':'internal/legal/catalogue_clearance_20261002/bengali/balai-final-full-manuscript-source.json','scope':'Actual Balai scan258–261; wrong Sanskar parent mapping corrected, later1969 edition rights separately held'}
        result['license_notice_bound']=(package/'license_notice.json').exists()
        result['remaining_gates']=[]
        if (package/'rights_decision.json').exists():
            decision=json.loads((package/'rights_decision.json').read_text())
            result['local_rights_decision']=decision.get('status')
            if decision.get('status')=='ACCEPTED':
                result['noncover_status']='LOCAL_IN_TEXT_CLEARANCE_COMPLETE_RUNTIME_ACTIVATION_HELD'
                result['remaining_gates']=['Production rights registry and runtime activation separately held']
        elif result['source_comparison'].get('status') not in ['EXACT_MATCH_FORMATTING_ONLY','EXACT_SAME_EDITION_14_CHAPTERS_RESTORED']:
            result['remaining_gates'].append('Exact source text/chapter reconciliation engineering required')
        if not result.get('local_rights_decision') and result['noncover_status'].startswith(('OBJECTIVE','EXACT_CURRENT')):
            result['remaining_gates'].append('Exact edition editorial-rights scope must be evidenced before local acceptance')
        if not result.get('local_rights_decision') and result['source_comparison'].get('status')=='EXACT_MATCH_FORMATTING_ONLY':
            result['noncover_status']='SOURCE_COMPLETE_LATER_EDITION_ORIGINAL_NARRATIVE_IDENTITY_EVIDENCE_REQUIRED'
            result['remaining_gates']=['Exact selected later printed-edition narrative must be evidenced against original/lifetime text, or independently authored editorial/transcription additions cleared; author death alone does not bind this edition.']
        if slug=='pather-panchali':
            result['noncover_status']='INCOMPLETE_EDITION_SOURCE_EXTERNAL_HOLD'
            result['remaining_gates']=['Current12sourcechapters exact; historical1952seventh-edition35chapterTOC lacks verified remaining23chaptertranscriptions and exact selected complete-edition identity. No invented source chapters.']
        if result['cover_binding_deferred']:result['cover_gate']='DEFERRED_OWNER_INSTRUCTION'
        rows.append(result)
    report={'schema_version':1,'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'BENGALI_TEXT_ONLY_SOURCE_RECONCILIATION_PROPOSALS_NO_PUBLICATION',
        'batch_definition':{'bankim':['bn-059','bn-060','bn-066','lokrahasya','mrinalini','muchiram-gurer-jibanchorit'],'tagore_single_story':'Existing pinned exact source per title','sarat':'Existing source editions independently reconciled','bibhutibhushan':'1952 seventh edition index conflict not reassigned to 1929'},
        'titles':rows,'count':len(rows),'published':0,'audio_changes':0,'canonical_package_changes':len(changed_slugs),
        'legal_clearance_not_inferred_from_cover_or_author_death':True}
    (args.output/'matrix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'titles':len(rows),'comparisons':sum('comparison_artifact'in r for r in rows),'published':0}))

if __name__=='__main__':main()
