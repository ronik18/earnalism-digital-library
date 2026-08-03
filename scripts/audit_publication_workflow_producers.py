#!/usr/bin/env python3
"""Static, read-only producer/consumer audit for legacy workflow aliases."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

PATTERN = re.compile(r"rights_metadata|rights_tier|verification_status|ingestion_status|edition_generation_status|visual_status|audio_status|qa_status|is_published|isPublic|isLive")
LEGACY_WRITER_HINTS = re.compile(r"update_one|update_many|insert_one|insert_many|find_one_and_update|\$set|book\[|payload\[")

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=Path('.')); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    rows=[]
    for base in (a.root/'backend', a.root/'scripts', a.root/'frontend/src'):
        if not base.exists(): continue
        for path in sorted(base.rglob('*')):
            if path.suffix not in {'.py','.js','.jsx','.ts','.tsx'} or '/tests/' in str(path): continue
            text=path.read_text(encoding='utf-8',errors='ignore'); matches=sorted(set(m.group(0) for m in PATTERN.finditer(text)))
            if matches:
                rows.append({'file':str(path),'legacy_fields':matches,'producer_or_runtime_writer':bool(LEGACY_WRITER_HINTS.search(text))})
    report={'mode':'read_only','file_count':len(rows),'writer_count':sum(x['producer_or_runtime_writer'] for x in rows),'rows':rows}
    a.output.write_text(json.dumps(report,indent=2)+'\n'); print(f"files={report['file_count']} writers={report['writer_count']} wrote={a.output}"); return 0
if __name__=='__main__': raise SystemExit(main())
