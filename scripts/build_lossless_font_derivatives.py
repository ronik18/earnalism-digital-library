"""Non-destructive WOFF2 derivatives. Requires fonttools[woff] for asset work only.

No subsetting, new glyphs, typography change, or Bengali source modification.
"""
import hashlib
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

root = Path(__file__).resolve().parents[1] / 'frontend/src/assets/fonts'
report = []
for source in sorted(root.glob('*.ttf')):
    if source.name.startswith('noto-'):
        continue
    original_bytes = source.read_bytes()
    original = TTFont(source, recalcTimestamp=False)
    original.flavor = 'woff2'
    target = source.with_suffix('.woff2')
    original.save(target)
    restored = TTFont(target, recalcTimestamp=False)
    assert original.getBestCmap() == restored.getBestCmap()
    assert original['hmtx'].metrics == restored['hmtx'].metrics
    assert original.getGlyphOrder() == restored.getGlyphOrder()
    before_glyphs = original.getGlyphSet()
    after_glyphs = restored.getGlyphSet()
    for name in original.getGlyphOrder():
        before = RecordingPen(); after = RecordingPen()
        before_glyphs[name].draw(before); after_glyphs[name].draw(after)
        assert before.value == after.value, (source.name, name)
    for name in ['GSUB', 'GPOS', 'GDEF', 'name', 'OS/2', 'fvar']:
        if name in original:
            assert original.getTableData(name) == restored.getTableData(name), (source.name, name)
    assert source.read_bytes() == original_bytes
    report.append({'source': source.name, 'source_sha256': hashlib.sha256(original_bytes).hexdigest(),
                   'source_bytes': len(original_bytes), 'derivative': target.name,
                   'derivative_bytes': target.stat().st_size, 'glyph_count': len(original.getGlyphOrder()),
                   'glyph_outlines_metrics_shaping_equal': True})
print(json.dumps(report, indent=2))
