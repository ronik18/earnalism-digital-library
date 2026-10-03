from pathlib import Path
from PIL import Image
import hashlib,sys

# Pure exact delivery verification. Source and destination supplied separately;
# never overwrites the frozen candidate assets or provenance receipts.
BASE=Path(sys.argv[1])
OUT=Path(sys.argv[2]);OUT.mkdir(parents=True,exist_ok=True)
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SOURCES={'front':'7f2e8e9fd3f6d0359b8d94cfc2198101abd64b4b78a95d035932d68bff4f2bf2','back':'83190790c57974d6dad6128dc87d5a3018e8d7fd06f41f623505320e974a1791'}
EXPECTED={'front':'5ee48b1d245c70b1b8495f9a6b98636cc798d2bea96ff54aa4c3d6fa27becb28','back':'bda88117bdb0d7208f51afa3cab6dce74875f83943ebf7c2a74409a6a29477c4'}
for side in ['front','back']:
    source=BASE/f'overlay-{side}-run1.png';assert H(source)==SOURCES[side]
    destination=OUT/f'verified-overlay-{side}-delivery.webp'
    Image.open(source).convert('RGB').resize((600,900),Image.Resampling.LANCZOS).save(destination,'WEBP',quality=64,method=6)
    assert H(destination)==EXPECTED[side]
    assert destination.stat().st_size<=80000
    print(side,H(destination),destination.stat().st_size)
