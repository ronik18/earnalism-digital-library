"""Focused offline tests. Synthetic audio/art fixtures are not production evidence."""
from pathlib import Path
import copy
import json
import os
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw, features

from .pipeline import (bound, caption_overlay, compile_plan, packet_hashes, prepare_audio,
                       probe, render, run, sha, write)


def existing_font(env_name, candidates):
    override = os.environ.get(env_name)
    if override:
        path = Path(override).expanduser()
        if not path.is_file():
            raise RuntimeError(f'{env_name} points to a missing font: {path}')
        return path
    return next((Path(p) for p in candidates if Path(p).is_file()), None)


EN_FONT = existing_font('EARNALISM_TEST_EN_FONT', [
    '/System/Library/Fonts/Supplemental/Arial.ttf',
    '/Library/Fonts/Arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans.ttf',
])
BN_FONT = existing_font('EARNALISM_TEST_BN_FONT', [
    '/System/Library/Fonts/KohinoorBangla.ttc',
    '/System/Library/Fonts/Supplemental/KohinoorBangla.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf',
    '/usr/share/fonts/noto/NotoSansBengali-Regular.ttf',
])


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = {'ffmpeg': shutil.which('ffmpeg'), 'ffprobe': shutil.which('ffprobe'),
                    'Pillow RAQM': features.check_feature('raqm'),
                    'English font': EN_FONT, 'Bengali font': BN_FONT}
        missing = [name for name, available in required.items() if not available]
        if missing:
            raise RuntimeError('Missing offline test prerequisites: ' + ', '.join(missing) +
                '. CI must install fonts-dejavu-core and fonts-noto-core plus existing FFmpeg/RAQM, '
                'or bind EARNALISM_TEST_EN_FONT/EARNALISM_TEST_BN_FONT. Tests never download them.')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.p = Path(self.temp.name)
        run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=0.25',
             '-af', 'apad', '-t', '0.5', '-c:a', 'pcm_s16le', self.p / 'original.wav'])
        run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=220:sample_rate=48000:duration=3',
             '-c:a', 'aac', self.p / 'end.m4a'])
        logo = Image.new('RGBA', (100, 30)); ImageDraw.Draw(logo).rectangle((5, 5, 95, 25), fill='navy')
        logo.save(self.p / 'fixture-logo.png')
        assets = {}; ends = {}
        for name, dims, color in [('landscape', (480, 270), '#75a69e'), ('portrait', (270, 480), '#d0a380')]:
            still = self.p / (name + '.png'); Image.new('RGB', dims, color).save(still)
            assets[name] = bound(still, kind='still', composition='independently_composed',
                                  rights='Synthetic test fixture', content_note='Independent synthetic canvas')
            end = self.p / (name + '-end.mp4')
            run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', f'color=c=black:s={dims[0]}x{dims[1]}:r=24:d=3',
                 '-i', self.p / 'end.m4a', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                 '-bf', '0', '-c:a', 'copy', end])
            ends[name] = bound(end, role='approved_end')
        self.timed = {'timing_status': 'estimated', 'timing_method': 'Synthetic test positions; no listening claim',
                      'cues': [{'id': 'c1', 'kind': 'narration', 'start_ms': 0, 'end_ms': 250, 'text': 'Hello spring.'},
                               {'id': 'c2', 'kind': 'silence', 'start_ms': 250, 'end_ms': 500, 'text': ''}]}
        write(self.p / 'cues.json', self.timed)
        self.plan = {'schema': 'earnalism.audiobook-visuals.v1', 'private': True, 'publication_approved': False,
                     'title': 'Synthetic pipeline fixture', 'language': 'en', 'fps': 24, 'caption_mode': 'on',
                     'preview_only': True,
                     'audio': bound(self.p / 'original.wav', actual_duration_seconds=.5),
                     'source_cues': bound(self.p / 'cues.json'), 'font': bound(EN_FONT),
                     'brand': {'logo': bound(self.p / 'fixture-logo.png', role='full_earnalism_lockup'), 'end': ends},
                     'layouts': {'landscape': {'width': 480, 'height': 270}, 'portrait': {'width': 270, 'height': 480}},
                     'scenes': [{'id': 's1', 'cue_ids': ['c1', 'c2'], 'source_quote': 'Hello spring.\n',
                                 'visual': 'Synthetic source-bound fixture', 'semantic_review': 'pending', 'assets': assets}]}

    def tearDown(self):
        self.temp.cleanup()

    def save(self, plan=None):
        path = self.p / 'plan.json'; write(path, self.plan if plan is None else plan); return path

    def rebind_cues(self, timed):
        write(self.p / 'cues.json', timed); self.plan['source_cues'] = bound(self.p / 'cues.json')

    def test_cue_gap_overlap_and_changed_exact_text_rejected(self):
        for wrong_start in (249, 251):
            timed = copy.deepcopy(self.timed); timed['cues'][1]['start_ms'] = wrong_start
            self.rebind_cues(timed)
            with self.assertRaisesRegex(ValueError, 'gap, overlap'):
                compile_plan(self.save(), _test_scope=True)
        self.rebind_cues(self.timed)
        self.plan['scenes'][0]['source_quote'] = 'A fabricated paraphrase.'
        with self.assertRaisesRegex(ValueError, 'exact source text'):
            compile_plan(self.save(), _test_scope=True)

    def test_omission_reordering_source_hash_and_motion_coverage_rejected(self):
        for ids in (['c1'], ['c2', 'c1']):
            plan = copy.deepcopy(self.plan); plan['scenes'][0]['cue_ids'] = ids
            plan['scenes'][0]['source_quote'] = 'Hello spring.' if len(ids) == 1 else '\nHello spring.'
            with self.assertRaises(ValueError): compile_plan(self.save(plan), _test_scope=True)
        self.plan['source_cues']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Changed or missing'):
            compile_plan(self.save(), _test_scope=True)
        self.plan['source_cues'] = bound(self.p / 'cues.json')
        short = self.p / 'short-motion.mp4'
        run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=480x270:r=24:d=0.125',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p', short])
        self.plan['scenes'][0]['assets']['landscape'] = bound(short, kind='motion',
            composition='independently_composed', rights='Synthetic fixture', content_note='Too short')
        with self.assertRaisesRegex(ValueError, 'cover the complete scene'):
            compile_plan(self.save(), _test_scope=True)
        misleading = self.p / 'short-video-long-audio.mp4'
        run(['ffmpeg', '-v', 'error', '-i', short, '-i', self.p / 'end.m4a',
             '-map', '0:v', '-map', '1:a', '-c', 'copy', misleading])
        self.assertGreater(float(probe(misleading)['format']['duration']), .5)
        self.plan['scenes'][0]['assets']['landscape'] = bound(misleading, kind='motion',
            composition='independently_composed', rights='Synthetic fixture', content_note='Audio exceeds video span')
        with self.assertRaisesRegex(ValueError, 'cover the complete scene'):
            compile_plan(self.save(), _test_scope=True)

    def test_production_rejects_arbitrary_logo_and_overlong_caption(self):
        with self.assertRaisesRegex(ValueError, 'canonical watermarkAsset'):
            compile_plan(self.save())
        text = 'An intentionally overlong source caption ' * 30
        timed = copy.deepcopy(self.timed); timed['cues'][0]['text'] = text
        self.rebind_cues(timed); self.plan['scenes'][0]['source_quote'] = text + '\n'
        c = compile_plan(self.save(), _test_scope=True)
        with self.assertRaisesRegex(ValueError, 'phone-scale minimum'):
            caption_overlay(c, 'portrait', c['cues'][0], self.p / 'too-long.png')

    def test_compatible_aac_is_packet_copied(self):
        source = self.p / 'source.m4a'
        run(['ffmpeg', '-v', 'error', '-i', self.p / 'original.wav', '-c:a', 'aac', source])
        self.plan['audio'] = bound(source, actual_duration_seconds=float(probe(source)['format']['duration']))
        c = compile_plan(self.save(), _test_scope=True); out = self.p / 'aac-copy'; out.mkdir()
        rec = prepare_audio(c, out)
        self.assertEqual(rec['mode'], 'AAC_PACKET_COPY')
        self.assertEqual(packet_hashes(source), packet_hashes(out / 'body-audio.m4a'))

    def test_full_dual_render_original_audio_shared_payload_and_end(self):
        original = sha(self.p / 'original.wav')
        report = render(self.save(), self.p / 'private-review', _test_scope=True)
        self.assertEqual(sha(self.p / 'original.wav'), original)
        self.assertEqual(report['final_release_qualification'], 'HELD_TEST_FIXTURE')
        self.assertEqual(report['draft_timing_state'], 'PRIVATE_DRAFT_TIMING_UNVERIFIED')
        self.assertTrue(all(x['shared_audio_packet_payload_identical'] for x in report['outputs'].values()))
        self.assertTrue(all(x['decoded_END_reference_frames_identical'] for x in report['outputs'].values()))
        self.assertEqual(report['audio']['source_sha256'], original)
        self.assertEqual(report['audio']['trailing_frame_alignment_pad_seconds'], 0)
        self.assertIn('Hello spring.', (self.p / 'private-review/captions.srt').read_text())
        # A changed final file must invalidate the technical evidence.
        from .pipeline import check
        with (self.p / 'private-review/portrait-review.mp4').open('ab') as f: f.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed final MP4'):
            check(self.p / 'private-review')

    def test_explicit_60_to_30_end_normalization_records_loss_and_preserves_sound(self):
        self.plan['fps'] = 30
        for name, dims in [('landscape', (480, 270)), ('portrait', (270, 480))]:
            end = self.p / (name + '-60fps-end.mp4')
            run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                 f'testsrc2=s={dims[0]}x{dims[1]}:r=60:d=3', '-i', self.p / 'end.m4a',
                 '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                 '-color_range', 'tv', '-colorspace', 'bt709', '-color_trc', 'bt709', '-color_primaries', 'bt709',
                 '-c:a', 'copy', end])
            self.plan['brand']['end'][name] = bound(end, role='approved_end')
        report = render(self.save(), self.p / 'normalized-private-review', _test_scope=True)
        for receipt in report['end_treatments'].values():
            self.assertEqual(receipt['frame_stride'], 2)
            self.assertEqual(receipt['source_decoded_pixel_identity'], 'NOT_CLAIMED_LOSSY_NORMALIZATION')
            self.assertIn('average', receipt['selected_source_frame_comparison_psnr_dB'])
            self.assertTrue(receipt['source_END_audio_packet_payload_identical'])
            self.assertFalse(receipt['source_MP4_bytes_identical'])
        self.assertTrue(all(x['full_decode'] for x in report['outputs'].values()))
        self.assertTrue(all(x['decoded_END_reference_frames_identical'] for x in report['outputs'].values()))

    def test_bengali_unicode_raqm_and_caption_off_private_preview(self):
        self.plan['language'] = 'bn'; self.plan['font'] = bound(BN_FONT)
        text = 'আকাশ নীল কেন?'; timed = copy.deepcopy(self.timed); timed['cues'][0]['text'] = text
        self.rebind_cues(timed); self.plan['scenes'][0]['source_quote'] = text + '\n'
        c = compile_plan(self.save(), _test_scope=True)
        rec = caption_overlay(c, 'portrait', c['cues'][0], self.p / 'bn.png')
        self.assertEqual(rec['shape_engine'], 'Pillow RAQM')
        self.assertEqual(rec['source_text'], text)
        self.assertTrue(rec['caption_ink'])
        self.assertEqual(rec['visible_draft_status'], 'PRIVATE_DRAFT_TIMING_UNVERIFIED')
        self.plan['caption_mode'] = 'off'; c = compile_plan(self.save(), _test_scope=True)
        rec = caption_overlay(c, 'portrait', c['cues'][0], self.p / 'bn-off.png')
        self.assertEqual(rec['caption_check'], 'NOT_APPLICABLE')
        self.assertEqual(rec['caption_ink'], [])


if __name__ == '__main__':
    unittest.main()
