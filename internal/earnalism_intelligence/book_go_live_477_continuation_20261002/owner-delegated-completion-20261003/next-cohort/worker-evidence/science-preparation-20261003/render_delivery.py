from pathlib import Path
from PIL import Image
import hashlib, json

BASE=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ORIGINALS={'front':'9fa719df44b5348b2dd694674fb7e4ba38438dd1e652ca70559081d67e88da15','back':'49cf4eb533e11cc92d253496e2945d700468b2a2e42b7aabf4c7d8dd3b590f09'}
EXPECTED={'front':'a4c48d8fb10c382fa9337185bcbdba42c677c9d6e1cae7aa6c66f25306454d9c','back':'2679cedd18d25db4d97f38962cc17671714c72e37e16235fe257956e692adb49'}

for side in ['front','back']:
    source=BASE/f'original-{side}.png';assert H(source)==ORIGINALS[side]
    destination=BASE/f'verification-{side}-card.webp'
    Image.open(source).convert('RGB').resize((600,900),Image.Resampling.LANCZOS).save(destination,'WEBP',quality=64,method=6)
    assert H(destination)==EXPECTED[side]
print('PASS exact delivery rerender; original art/copy untouched')
