#!/usr/bin/env python3
import json,sys,zipfile
from pathlib import Path
r=Path(sys.argv[1]); d=json.loads((r/'capture-results.json').read_text()); expected={'home-desktop','home-mobile','home-mobile-zoom-200','reader-mobile-390','reader-mobile-320','listener-mobile-390','listener-mobile-320','account-mobile','library-footer-mobile'}; got={x['id'] for x in d['states']}; assert got==expected,(got,expected)
for x in d['states']:
 assert (r/x['screenshot']).is_file() and (r/x['screenshot']).stat().st_size>100
 assert not x['overflow']
for n in ['owner-review.html','owner-review.pdf','contact-sheet.png','manifest.json','artifact.zip']: assert (r/n).is_file() and (r/n).stat().st_size>100,n
assert (r/'manifest.sha256').is_file() and (r/'manifest.sha256').stat().st_size>=64
with zipfile.ZipFile(r/'artifact.zip') as z: assert len(z.namelist())>=9
stats=json.loads((r/'package-statistics.json').read_text()); assert stats['tooling_test_result']=='PASS' and stats['extracted_total_bytes']>0 and stats['extracted_file_count']>0
print('PASS')
