"""Copied conformed takes keep a locally verifiable source tree."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audio_derivation import check_unit, sha
from delivery_conform import render_scene
from narration_edit import _copy_unit, edit


class CopyDeliveryProvenanceTests(unittest.TestCase):
    def make_conformed(self, root):
        source = root / 'generated'
        (source / 'raw').mkdir(parents=True)
        for sid, frequency in [('first', 140), ('second', 180)]:
            wav = source / 'raw' / (sid + '.wav')
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                f'sine=frequency={frequency}:duration=1.5', '-ar', '24000',
                '-c:a', 'pcm_f32le', str(wav)], check=True)
            wav.with_suffix('.wav.json').write_text(json.dumps({
                'status': 'GENERATED_REQUIRES_REVIEW', 'wav_sha256': sha(wav),
                'settings': {'speaker': 'Ryan', 'instruct': 'source-binding fixture'},
                'audio': {'duration_seconds': 1.5, 'mechanical_checks': 'PASS'},
                'provenance': {'model_id': 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
                    'model_revision': 'fixture-model', 'worker_sha256': 'fixture-worker'}}))
        conformed = root / 'conformed'
        text = 'A complete thought keeps its original source identity.'
        render_scene(conformed, source, {'scene': 's01', 'text': text, 'phrases': [{
            'text': text, 'tempo': 1.0, 'pad_after': 0,
            'parts': [{'source': sid, 'start': 0, 'end': 1.4}
                for sid in ('first', 'second')]}]}, {'first': 0, 'second': 0})
        return source, conformed, text

    def test_copied_conform_validates_with_all_local_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, conformed, _ = self.make_conformed(root)
            destination = root / 'copied'
            _copy_unit(conformed, destination, 's01')
            meta = check_unit(destination, 's01')
            self.assertEqual(set(meta['derivation']['sources']), {'first', 'second'})
            for sid in ('first', 'second'):
                for suffix in ('.wav', '.wav.json'):
                    self.assertEqual((destination / 'delivery-source/raw' / (sid + suffix)).read_bytes(),
                        (conformed / 'delivery-source/raw' / (sid + suffix)).read_bytes())
                self.assertEqual(sha(source / 'raw' / (sid + '.wav')),
                    meta['derivation']['sources'][sid]['wav_sha256'])

    def test_tampered_copied_source_is_rejected_without_changing_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, conformed, _ = self.make_conformed(root)
            destination = root / 'copied'
            before = sha(source / 'raw/second.wav')
            _copy_unit(conformed, destination, 's01')
            (destination / 'delivery-source/raw/second.wav').write_bytes(b'changed copied source')
            with self.assertRaisesRegex(ValueError, 'binding'):
                check_unit(destination, 's01')
            self.assertEqual(sha(source / 'raw/second.wav'), before)
            self.assertEqual(check_unit(conformed, 's01')['derivation']['sources']['second']['wav_sha256'], before)

    def test_content_edit_copy_recurses_into_conform_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, conformed, text = self.make_conformed(root)
            edited = root / 'edited'
            # Content-only reuse of the complete conformed take adds no tempo pass.
            duration = check_unit(conformed, 's01')['audio']['duration_seconds']
            edit({'id': 's02', 'text': text}, edited,
                [{'folder': conformed, 'scene': 's01', 'start': 0, 'end': duration}])
            destination = root / 'copied-edit'
            _copy_unit(edited, destination, 's02')
            self.assertEqual(check_unit(destination, 's02')['derivation']['kind'], 'sentence_content_edit')
            nested = destination / 'edit-sources/input-0/delivery-source/raw/first.wav'
            self.assertTrue(nested.is_file())
            nested.write_bytes(b'tampered nested source')
            with self.assertRaisesRegex(ValueError, 'binding'):
                check_unit(destination, 's02')


if __name__ == '__main__':
    unittest.main()
