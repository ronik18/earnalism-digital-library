#!/usr/bin/env python3
"""Deterministically repair The Great Gatsby reader package, without release."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SLUG="the-great-gatsby"
SOURCE=Path("/private/tmp/pg64317.txt"); CONTENT=ROOT/"content/books"/SLUG
RAW=CONTENT/"raw/pg64317.txt"; PACK=ROOT/"data/controlled_publications"/SLUG
BACKEND=ROOT/"backend/data/controlled_publications"/SLUG
SOURCE_URL="https://www.gutenberg.org/cache/epub/64317/pg64317.txt"
SOURCE_SHA="ce760ec377accd352b41bb8f64504a72d7aa18ab3afb42ded2b56cecacf29e35"
RIGHTS_URL="https://www.indiacode.nic.in/show-data?actid=AC_CEN_9_30_00006_195714_1517807321712&orderno=23&sectionId=14525&sectionno=22"
RIGHTS=("F. Scott Fitzgerald died in 1940. Under Section 22 of the Copyright Act, "
"1957 (India), copyright in a literary work subsists until sixty years from the "
"beginning of the calendar year following the author's death; the term therefore "
"expired in India at the end of 2000 and the work entered the public domain "
"there on 1 January 2001. Territory: IN.")
ROMANS=("I","II","III","IV","V","VI","VII","VIII","IX")
OPENING="In my younger and more vulnerable years my father gave me some advice"
ENDING="So we beat on, boats against the current, borne back ceaselessly into the past."
WORDS=re.compile(r"\b\w+[’'\-]?\w*\b",re.UNICODE); REPAIR_ID="great-gatsby-reader-repair-20260816"
OLD_SHAS=("d218001185b771b32754f701301f4c5eb64f22bf8b6b37086363b6aedcc3dceb","1325e8b7f8ef0e06ffc5a6b62077acd9eedfcbac2a73b6b2cf9ae296ba65c32f","57a09e87e20eb95be216c4b96875f883694c0377a6b818d252b135f90c9c3c60","12318e42406496f94784d779bc3f72eae93169d86b6928bb2e0325d4efbf9ea3","058c3f3b6edd3f1a7c7be9519da71cf4461271f17c551c26acd57df6299dde8a","31a7c600d18f8bca6592adc9ce7c9ed70018278548f4b03cec04a0ffc0c40e8e","f635d8be814636bbb2c68846ac8a1c7691818793acf77f7b767d5bfc86dcf006","cd3f60d307f7e5445c047656ba18cb3d3a1471876c02067e6882a35921f92659","56d9d5542f11bc37649e4aa8a1d8e9d1745dec327993cea63e036a5ccdeceeef")

def sha(b): return hashlib.sha256(b).hexdigest()
def shat(s): return sha(s.encode())
def jb(v): return (json.dumps(v,ensure_ascii=False,indent=2)+"\n").encode()
def rj(p): return json.loads(p.read_text())
def norm(s): return re.sub(r"\s+"," ",s).strip()
def src():
    b=SOURCE.read_bytes()
    if sha(b)!=SOURCE_SHA: raise ValueError(f"official source checksum changed: {sha(b)}")
    return b

def chapters():
    raw=src().decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n"); lines=raw.splitlines()
    hs=[(i,l.strip()) for i,l in enumerate(lines) if l.strip() in ROMANS and len(l)-len(l.lstrip())>=20 and i>50]
    if [x[1] for x in hs]!=list(ROMANS): raise ValueError(f"unexpected headings: {hs}")
    end=next(i for i,l in enumerate(lines) if l.startswith("*** END OF THE PROJECT GUTENBERG EBOOK"))
    out=[]
    for n,(start,title) in enumerate(hs):
        stop=hs[n+1][0] if n<8 else end; body="\n".join(lines[start+1:stop]).strip(); blocks=[]
        for block in re.split(r"\n\s*\n",body):
            ls=[x.rstrip() for x in block.splitlines()]; ss=[x.strip() for x in ls if x.strip()]
            if not ss: continue
            if len(ls)>1 and all(x.startswith("  ") for x in ls if x.strip()): blocks.append("\n".join(ss))
            else: blocks.append(" ".join(ss))
        text="\n\n".join(blocks)
        old=rj(PACK/f"chapters/chapter-{n+1:03d}.json")["content"]
        if norm(text)!=norm(old): raise ValueError(f"chapter {title} changed narrative")
        out.append({"title":title,"text":text,"old_sha256":OLD_SHAS[n],"sha256":shat(text),
                    "word_count":len(WORDS.findall(text)),"semantic_blocks":len(blocks)})
    if not out[0]["text"].startswith(OPENING) or not out[-1]["text"].endswith(ENDING): raise ValueError("boundary changed")
    return out

def private(d):
    d=copy.deepcopy(d); d.update({"verification_status":"reader_repair_verified",
      "qa_status":"READER_REPAIR_PASSED_COVER_BLOCKED","approved_to_publish":False,
      "publication_status":"READER_APPROVAL_REQUIRED","readerStatus":"reader_approval_required",
      "publicationStatus":"draft","isPublic":False,"isLive":False,"showInPublicLibrary":False,
      "showInHomepage":False,"allowPublicReading":False,"is_published":False,
      "audio_enabled":False,"audiobook_enabled":False,"generate_audiobook":False,
      "audiobook_provider":"","audiobook_voice":"","audio_asset_slug":""}); return d

def manifest(rep,at):
    paths={p for p in PACK.rglob("*") if p.is_file()}|{p for p in rep if p.is_relative_to(PACK)}
    rows=[]
    for p in sorted(paths):
        if p.name in {"checksum_manifest.json","publication_manifest.json"}: continue
        payload=rep[p] if p in rep else p.read_bytes()
        rows.append({"file":p.relative_to(PACK).as_posix(),"sha256":sha(payload)})
    return jb({"slug":SLUG,"generated_at":at,"files":rows})

def plan(at):
    ch=chapters(); digest=shat("\n\n".join(x["text"] for x in ch)); wc=sum(x["word_count"] for x in ch)
    blocks=sum(x["semantic_blocks"] for x in ch); minutes=math.ceil(wc/240); rep={RAW:src()}
    fingerprint=shat(json.dumps({"slug":SLUG,"source_sha256":SOURCE_SHA,"chapter_sha256":[x["sha256"] for x in ch],"rights_basis":RIGHTS,"audio_enabled":False,"cover_gate":"BLOCKED_LOCAL_PROVENANCE_MISSING"},ensure_ascii=False,sort_keys=True,separators=(",",":")))
    book=rj(CONTENT/"book.json"); book.update({"rightsTerritoryBasis":RIGHTS,"readerStatus":"reader_approval_required",
      "publicationStatus":"draft","isPublic":False,"isLive":False,"showInPublicLibrary":False,
      "showInHomepage":False,"allowPublicReading":False,"is_published":False,"wordCountApprox":wc,
      "readingTimeMinutesApprox":minutes,"updatedAt":at,"readerPackageFingerprint":fingerprint,
      "coverVerificationStatus":"BLOCKED_LOCAL_PROVENANCE_MISSING"}); rep[CONTENT/"book.json"]=jb(book)
    rep[CONTENT/"source-rights.md"]=f"""# Source Rights Note: The Great Gatsby

- Title: The Great Gatsby
- Author: F. Scott Fitzgerald
- Author death year: 1940
- Original publication year: 1925
- Source URL: https://www.gutenberg.org/ebooks/64317
- Controlled source download: {SOURCE_URL}
- Controlled source SHA-256: {SOURCE_SHA}
- India commercial-use rights basis: {RIGHTS}
- Commercial use allowed in publication territory IN: yes
- Reader-facing boilerplate removed: Gutenberg header, footer, license, title-page furniture, dedication, and epigraph are outside the nine narrative chapter payloads.
- Updated at UTC: {at}
- Status: reader_repair_ready_for_owner_approval
- Blocker: Exact-title cover lacks repository-local checksum and provenance evidence; inherited URLs must not satisfy the cover gate.
""".encode()
    pub=private(rj(PACK/"public_book.json")); pub.update({"source_hash":SOURCE_SHA,"source_hash_domain":"exact_download_bytes",
      "content_hash":digest,"content_hash_domain":"chapter_text_utf8_joined_by_double_lf","rights_basis":RIGHTS,
      "rights_territory":"IN","cover_status":"BLOCKED_UNVERIFIED_REMOTE_LEGACY_COVER","cover_gate_passed":False,
      "release_blockers":["exact_slug_graphical_cover_not_proven"],"estimated_reading_time":f"{minutes} min","updated_at":at,
      "reader_package_fingerprint":fingerprint})
    rdr=rj(PACK/"reader_manifest.json"); pc=copy.deepcopy(pub["chapters"]); rc=copy.deepcopy(rdr["chapters"])
    for n,x in enumerate(ch,1):
        cp=CONTENT/f"chapters/{n:03d}-{x['title'].lower()}.json"; c=rj(cp); rm=max(1,math.ceil(x["word_count"]/240))
        c.update({"content":x["text"],"sourceSha256":SOURCE_SHA,"sourceSha256Domain":"exact_download_bytes",
          "sanitizedSha256":x["sha256"],"wordCountApprox":x["word_count"],"characterCount":len(x["text"]),
          "readingTimeMinutesApprox":rm}); rep[cp]=jb(c)
        pp=PACK/f"chapters/chapter-{n:03d}.json"; c=rj(pp); c.update({"content":x["text"],
          "content_hash":x["sha256"],"sanitizedSha256":x["sha256"],"word_count":x["word_count"],
          "reading_minutes":rm,"updated_at":at}); rep[pp]=jb(c)
        for rows in (pc,rc): rows[n-1].update({"word_count":x["word_count"],"reading_minutes":rm,"updated_at":at})
    pub["chapters"]=pc; rep[PACK/"public_book.json"]=jb(pub)
    rdr.update({"chapters":rc,"chapter_count":9,"reader_status":"reader_approval_required","cover_gate_passed":False,
      "release_blockers":["exact_slug_graphical_cover_not_proven"],"audio_enabled":False,"audiobook_enabled":False,
      "generated_at":at,"reader_package_fingerprint":fingerprint}); rep[PACK/"reader_manifest.json"]=jb(rdr)
    se=rj(PACK/"source_evidence.json"); se.update({"source_url":SOURCE_URL,"source_download_url":SOURCE_URL,
      "source_hash":SOURCE_SHA,"source_hash_domain":"exact_download_bytes","content_hash":digest,
      "content_hash_domain":"chapter_text_utf8_joined_by_double_lf","rights_basis":RIGHTS,
      "rights_statute":"Copyright Act, 1957 (India), Section 22","rights_statute_url":RIGHTS_URL,
      "publication_region":"IN","author_death_year":1940,"original_publication_year":1925,
      "verification_status":"reader_repair_verified","qa_status":"READER_REPAIR_PASSED_COVER_BLOCKED",
      "verified_at":at,"official_download_sha256":SOURCE_SHA,"reader_package_fingerprint":fingerprint,
      "raw_source_archive":"content/books/the-great-gatsby/raw/pg64317.txt",
      "reader_facing_boilerplate_removed":True}); rep[PACK/"source_evidence.json"]=jb(se)
    ae=rj(PACK/"approval_evidence.json"); ae.update({"approved_to_publish":False,
      "verification_status":"reader_repair_verified","qa_status":"READER_REPAIR_PASSED_COVER_BLOCKED",
      "approval_scope":"fresh_checksum_bound_reader_approval_required","reader_approval":"NOT_REQUESTED_COVER_BLOCKED",
      "cover_gate_passed":False,"release_blockers":["exact_slug_graphical_cover_not_proven"],
      "audio_public_release":"PUBLIC_AUDIO_RELEASE_NOT_APPROVED","audio_enabled":False,"audiobook_enabled":False,
      "reader_package_fingerprint":fingerprint})
    rep[PACK/"approval_evidence.json"]=jb(ae)
    rep[PACK/"highlight_sync.json"]=jb({"slug":SLUG,"status":"INVALIDATED_STALE_ESTIMATED_SYNC",
      "generatedAt":at,"source":"great_gatsby_reader_repair","chapters":[],"totalDurationMs":0,
      "audio_enabled":False,"audiobook_enabled":False,
      "note":"Legacy pipeline_gate3 timing was estimated and is not admissible. Future audio requires measured synchronization bound to approved audio bytes."})
    ev={"schema":"earnalism.great_gatsby_reader_repair.v1","repair_id":REPAIR_ID,"slug":SLUG,"repaired_at":at,
      "official_source_url":SOURCE_URL,"official_source_sha256":SOURCE_SHA,"raw_source_archived_exactly":True,
      "rights_territory":"IN","rights_statute":"Copyright Act, 1957 (India), Section 22","author_death_year":1940,
      "reader_package_fingerprint":fingerprint,"chapter_titles":list(ROMANS),"chapter_count":9,"word_count":wc,"semantic_blocks":blocks,
      "content_sha256":digest,"opening":OPENING,"ending":ENDING,"normalized_chapter_equality":True,
      "chapter_evidence":ch,"narrative_words_order_unchanged":True,"legacy_estimated_sync_invalidated":True,"audio_enabled":False,
      "root_backend_byte_parity":True,"cover_gate_passed":False,
      "cover_gate":"BLOCKED_LOCAL_PROVENANCE_MISSING","release_blockers":["exact_slug_graphical_cover_not_proven"],"preview_rendered":False}
    ev["evidence_sha256"]=shat(json.dumps(ev,ensure_ascii=False,sort_keys=True,separators=(",",":")))
    rep[PACK/"reader_repair_evidence.json"]=jb(ev); rep[PACK/"checksum_manifest.json"]=manifest(rep,at)
    rel={p.relative_to(PACK) for p in rep if p.is_relative_to(PACK)}|{p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file()}
    for r in sorted(rel):
        b=rep[PACK/r] if PACK/r in rep else (PACK/r).read_bytes()
        rep[PACK/r]=b; rep[BACKEND/r]=b
    intelligence(rep,ev,at); return rep,ev

def intelligence(rep,ev,at):
    base=ROOT/"internal/earnalism_intelligence"; lp=base/"decision_ledger.jsonl"; text=lp.read_text()
    if REPAIR_ID not in text:
        row={"timestamp":at,"workstream":"english_25_title_controlled_release","slug_or_area":SLUG,
          "decision":REPAIR_ID,"evidence":{"official_source_sha256":SOURCE_SHA,"content_sha256":ev["content_sha256"],
          "chapter_count":9,"word_count":ev["word_count"],"semantic_blocks":ev["semantic_blocks"],
          "normalized_chapter_equality":True,"root_backend_byte_parity":True,"cover_gate_passed":False,
          "audio_enabled":False},"selected_option":"Restore semantic paragraphs from the exact official source and stop at the unproven-cover gate.",
          "customer_experience_reason":"Readers should receive coherent literary paragraphs, never print-line fragments or an unverified cover.",
          "release_gate_reason":"India rights, source parity, checksums, mirrors, and text structure pass; exact-slug graphical cover proof is still absent.",
          "result":"READER_REPAIRED_COVER_BLOCKED_NO_PREVIEW",
          "next_action":"Audit or create an approved exact-slug graphical cover, then rerun all reader gates and render a checksum-bound private preview."}
        text=text.rstrip()+"\n"+json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n"
    rep[lp]=text.encode()
    hp=base/"title_decision_history.json"; h=rj(hp); h.setdefault("titles",{})[SLUG]={
      "latest_decision":"READER_REPAIRED_COVER_BLOCKED_NO_PREVIEW",
      "decision_reason":"Exact source, India rights, semantic structure, checksums, and mirrors pass; exact-slug graphical cover proof is absent.",
      "updated_at":at,"language":"en","territory":"IN","public_reader_status":"PRIVATE_READER_APPROVAL_BLOCKED_BY_COVER",
      "public_audio_status":"AUDIO_HIDDEN_NOT_REQUESTED","source_sha256":SOURCE_SHA,"content_sha256":ev["content_sha256"],
      "next_action":"Prove an exact-slug graphical cover, rerun reader gates, and render a fresh private preview."}; rep[hp]=jb(h)
    sp=base/"sprint_learnings.md"; s=sp.read_text(); marker="## Great Gatsby deterministic reader repair - 2026-08-16"
    if marker not in s: s=s.rstrip()+"\n\n"+marker+"""\n
- Centered Roman chapter headings in the official Gutenberg plain-text edition provide deterministic nine-chapter boundaries; blank-line blocks restore semantic paragraphs while whitespace-normalized equality guards every word, punctuation mark, and ordering decision.
- A historical remote cover URL is not exact-slug graphical-cover proof. Keep the reader private and do not render an approval preview until the cover passes the active cover policy.
- India release evidence for Fitzgerald must cite Copyright Act 1957 Section 22 and the 1940 death year, not rely solely on United States public-domain reasoning.
"""
    rep[sp]=s.encode()
    rep[base/"great_gatsby_reader_repair_20260816.json"]=jb(ev)

def verify(rep):
    for p,b in rep.items():
        if p.read_bytes()!=b: raise ValueError(f"written bytes differ: {p}")
    for package in (PACK,BACKEND):
        files={x["file"]:x["sha256"] for x in rj(package/"checksum_manifest.json")["files"]}
        managed={p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file() and p.name not in {"checksum_manifest.json","publication_manifest.json"}}
        if "checksum_manifest.json" in files or set(files)!=managed: raise ValueError(f"manifest coverage differs: {package}")
        for r,d in files.items():
            if sha((package/r).read_bytes())!=d: raise ValueError(f"checksum differs: {package/r}")
    rf={p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file()}; bf={p.relative_to(BACKEND) for p in BACKEND.rglob("*") if p.is_file()}
    if rf!=bf: raise ValueError("mirror file sets differ")
    for r in rf:
        if (PACK/r).read_bytes()!=(BACKEND/r).read_bytes(): raise ValueError(f"mirror differs: {r}")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--write",action="store_true"); ap.add_argument("--repaired-at",default="2026-08-16T00:00:00Z"); a=ap.parse_args()
    rep,ev=plan(a.repaired_at); changed=[str(p.relative_to(ROOT)) for p,b in rep.items() if not p.exists() or p.read_bytes()!=b]
    if a.write:
        for p,b in rep.items(): p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)
        verify(rep)
    print(json.dumps({**ev,"mode":"write" if a.write else "dry-run","changed_files":changed},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
