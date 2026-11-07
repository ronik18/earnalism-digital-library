"""Exact-reference prose layout projection; canonical manuscript bytes stay unchanged.

Opt-in per chapter. Never infer paragraph boundaries from line length, case,
quotes, or punctuation. Only whitespace differs between the entire canonical
chapter and a unique excerpt of its explicitly selected prose reference.
No function supplies human approval or permits poetry/technical-text reflow.
"""
from __future__ import annotations
import bisect, hashlib, json, re

SCHEMA='earnalism.reference_narration_layout.v1'
BLANK=re.compile(r'\n[ \t\r]*\n')

def require(value, message):
    if not value: raise ValueError(message)
def sha(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()
def objhash(value): return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')))
def norm(value): return re.sub(r'\s+',' ',value).strip()
def _tokens(text): return list(re.finditer(r'\S+',text))

def _excerpt(text, reference):
    """Return one unique whole-token reference match, preserving reference offsets."""
    tokens=_tokens(reference); offsets=[]; pos=0
    for token in tokens:
        offsets.append(pos); pos+=len(token.group())+1
    hay=' '.join(m.group() for m in tokens); needle=norm(text)
    require(needle,'Empty canonical chapter')
    starts=[]; start=0
    while True:
        at=hay.find(needle,start)
        if at<0:break
        end=at+len(needle)
        if (at==0 or hay[at-1]==' ') and (end==len(hay) or hay[end]==' '):starts.append(at)
        start=at+1
    require(len(starts)==1,'Entire canonical chapter must have exactly one whitespace-only reference match')
    first=bisect.bisect_left(offsets,starts[0]); count=len(_tokens(text)); last=first+count-1
    require(first<len(tokens) and last<len(tokens),'Reference token range invalid')
    a,b=tokens[first].start(),tokens[last].end()
    require(norm(reference[a:b])==needle,'Reference excerpt differs beyond whitespace')
    return a,b,reference[a:b]

def _joins(text, reference_excerpt):
    ct,rt=_tokens(text),_tokens(reference_excerpt)
    require([m.group() for m in ct]==[m.group() for m in rt], 'Reference/canonical tokens or punctuation differ')
    joins=[]; retained=[]
    for i in range(len(ct)-1):
        a,b=ct[i].end(),ct[i+1].start();gap=text[a:b]
        x,y=rt[i].end(),rt[i+1].start();refgap=reference_excerpt[x:y]
        if BLANK.search(refgap):
            # Missing canonical paragraph break is not silently fabricated.
            require(BLANK.search(gap),'Reference has a true paragraph break absent from canonical layout; explicit editor mapping required')
        if BLANK.search(gap):
            row={'source_start':a,'source_end':b,'whitespace_sha256':sha(gap),
                 'reference_start':x,'reference_end':y,'reference_whitespace_sha256':sha(refgap)}
            if not BLANK.search(refgap):joins.append(row)
            else:retained.append({'source_start':a,'source_end':b})
    return joins,retained

def build_reference_layout(chapters, reference_bytes, reference_url, *, prose_chapter_ids):
    """Build an unapproved technical layout ledger for explicitly selected prose."""
    require(isinstance(reference_bytes,bytes),'Reference must be the downloaded raw bytes')
    require(isinstance(reference_url,str) and reference_url.startswith('https://'),'HTTPS reference URL required')
    selected=set(prose_chapter_ids); require(selected,'Explicit prose chapter IDs required')
    require(selected<={c['id'] for c in chapters},'Selected prose chapter absent')
    reference=reference_bytes.decode('utf-8-sig'); rawhash=hashlib.sha256(reference_bytes).hexdigest()
    entries={}
    for chapter in chapters:
        if chapter['id'] not in selected:continue
        text=chapter['content'];a,b,excerpt=_excerpt(text,reference);joins,retained=_joins(text,excerpt)
        entries[chapter['id']]={'canonical_content_sha256':sha(text),'content_kind':'explicitly_selected_prose',
            'reference_excerpt_start':a,'reference_excerpt_end':b,'reference_excerpt':excerpt,
            'reference_excerpt_sha256':sha(excerpt),'joins':joins,'retained_paragraph_breaks':retained,
            'canonical_paragraphs':len(list(BLANK.finditer(text)))+1,'narration_paragraphs':len(retained)+1}
    return {'schema_version':SCHEMA,'reference_url':reference_url,'reference_bytes_sha256':rawhash,
            'reference_decode':'utf-8-sig','source_sha256':sha('\n\n'.join(c['content'] for c in chapters)),
            'method':'EXACT_WHOLE_CHAPTER_TOKEN_AND_PUNCTUATION_MATCH_WHITESPACE_ONLY',
            'human_editorial_approval':False,'editorial_review_required':True,'chapters':entries}

def project_chapters(chapters, ledger):
    require(ledger.get('schema_version')==SCHEMA,'Unsupported narration layout schema')
    require(ledger.get('source_sha256')==sha('\n\n'.join(c['content'] for c in chapters)),'Stale narration layout source')
    require(re.fullmatch(r'[0-9a-f]{64}',str(ledger.get('reference_bytes_sha256',''))),'Missing reference file fingerprint')
    require(ledger.get('method')=='EXACT_WHOLE_CHAPTER_TOKEN_AND_PUNCTUATION_MATCH_WHITESPACE_ONLY','Unrecognized layout projection method')
    require(set(ledger.get('chapters',{}))<={c['id'] for c in chapters},'Layout refers to missing chapter')
    projected=[]
    for c in chapters:
        out=dict(c); entry=ledger.get('chapters',{}).get(c['id'])
        if entry:
            text=c['content'];require(entry.get('canonical_content_sha256')==sha(text),'Chapter source binding changed')
            require(entry.get('content_kind')=='explicitly_selected_prose','Only explicit prose projection is supported')
            excerpt=entry.get('reference_excerpt','');require(entry.get('reference_excerpt_sha256')==sha(excerpt),'Reference excerpt fingerprint changed')
            joins,retained=_joins(text,excerpt)
            require(entry.get('joins')==joins and entry.get('retained_paragraph_breaks')==retained,'Layout joins do not match exact reference evidence')
            chars=list(text)
            for row in joins:
                a,b=row['source_start'],row['source_end'];require(text[a:b].isspace(),'Layout edit touches source text')
                chars[a:b]=[' ']*(b-a)
            out['content']=''.join(chars)
            require(len(out['content'])==len(text) and norm(out['content'])==norm(text),'Layout changed canonical offsets or words')
        projected.append(out)
    return projected

def segment_with_layout(chapters,ledger,segmenter,**kwargs):
    """Use the existing segmenter with identity-preserving chapter-relative offsets."""
    originals={c['id']:c['content'] for c in chapters};projected=project_chapters(chapters,ledger)
    segments=segmenter(projected,**kwargs); layout_hash=objhash(ledger)
    for s in segments:
        original=originals[s['chapter_id']][s['source_start']:s['source_end']]
        require(norm(original)==s['text'],'Segment text/offset mapping changed during narration projection')
        s['canonical_text']=original;s['narration_layout_sha256']=layout_hash
        s['paragraph_basis']='REFERENCE_PROSE_PARAGRAPH' if s['chapter_id'] in ledger['chapters'] else 'CANONICAL_PARAGRAPH'
    require(norm(' '.join(s['canonical_text'] for s in segments))==norm('\n\n'.join(c['content'] for c in chapters)), 'Projection lost or duplicated source content')
    return segments

def layout_risk_flags(chapters):
    """Diagnostic only. Flags never authorize a join or mutate a manuscript."""
    flags=[]
    for c in chapters:
        blocks=[x.strip() for x in re.split(r'\n[ \t\r]*\n',c['content']) if x.strip()]
        if len(blocks)>=20:
            wrapped=sum(45<=len(x)<=85 for x in blocks)/len(blocks)
            unfinished=sum(not re.search(r'[.!?:;][\"\u201d\u2019\')\]]*$',x) for x in blocks)/len(blocks)
            if wrapped>=.5 and unfinished>=.3:
                flags.append({'chapter_id':c['id'],'code':'POSSIBLE_PHYSICAL_LINE_WRAPS_AS_PARAGRAPHS',
                              'blocks':len(blocks),'wrap_width_fraction':round(wrapped,3),'unfinished_fraction':round(unfinished,3),
                              'action':'Inspect source layout; never automatically join. Use exact-reference prose mapping or an editor-reviewed map.'})
        if re.search(r'\[Picture:|\[Illustration:',c['content'],re.I):
            flags.append({'chapter_id':c['id'],'code':'ILLUSTRATION_CAPTION_NARRATION_POLICY_REQUIRED',
                          'action':'Preserve source; explicitly review whether and how captions are spoken.'})
    return flags

def install_into(core, ledgers):
    """Install only exact-source opt-in ledgers; every other title keeps its layout.

    Call before prepare_title. Re-prepare previously prepared contexts afterward.
    Do not migrate nonempty segment-ID overrides across a changed generation plan.
    """
    original=getattr(core,'_reference_layout_original_segmenter',core.segment_chapters)
    by_source={}
    for ledger in ledgers:
        key=ledger.get('source_sha256');require(key and key not in by_source,'Duplicate/missing layout source binding')
        by_source[key]=ledger
    def bound_segmenter(chapters,max_words=65,max_chars=520,manual_boundaries=None):
        key=sha('\n\n'.join(c['content'] for c in chapters))
        kwargs={'max_words':max_words,'max_chars':max_chars,'manual_boundaries':manual_boundaries}
        if key in by_source:return segment_with_layout(chapters,by_source[key],original,**kwargs)
        return original(chapters,**kwargs)
    core._reference_layout_original_segmenter=original
    core.segment_chapters=bound_segmenter
    return core
