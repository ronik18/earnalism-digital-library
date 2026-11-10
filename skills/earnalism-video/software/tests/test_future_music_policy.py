"""Portable compatibility tests; no private pilot, synthesis or media writes."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import studio
from future_music_policy import FUTURE_PROFILE, require_supported_assembly_music


class FutureMusicPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'music': {'enabled': True, 'palette': 'acoustic_editorial_v12',
                                'future_profile': {'id': FUTURE_PROFILE}}}

    def test_enabled_historical_fallback_and_partial_job_override_refuse(self):
        original = copy.deepcopy(self.policy)
        for episode in ({}, {'music': {'enabled': True}}, {'music': {'palette': 'acoustic_v8'}}):
            with self.subTest(episode=episode), self.assertRaisesRegex(ValueError, 'supported full-body composer'):
                require_supported_assembly_music(episode, self.policy)
        self.assertEqual(self.policy, original)

    def test_relabeling_palette_or_self_claimed_qualification_cannot_pass(self):
        episode = {'music': {'enabled': True, 'palette': FUTURE_PROFILE,
                             'continuous_body_qualified': True, 'future_profile': {}}}
        with self.assertRaisesRegex(ValueError, 'Relabeling a palette'):
            require_supported_assembly_music(episode, self.policy)
        unknown = copy.deepcopy(self.policy); unknown['music']['future_profile']['id'] = 'unreviewed'
        with self.assertRaisesRegex(ValueError, 'Unknown future music profile'):
            require_supported_assembly_music({}, unknown)

    def test_disabling_new_main_bed_cannot_bypass_future_profile(self):
        with self.assertRaisesRegex(ValueError, 'disabling the main-video bed'):
            require_supported_assembly_music({'music': {'enabled': False}}, self.policy)
        self.assertIsNone(require_supported_assembly_music({}, {'music': {'enabled': True, 'palette': 'legacy'}}))

    def test_generic_assembly_refuses_before_any_assembly_write_or_external_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'config').mkdir(); folder = root / 'candidate'; folder.mkdir()
            (root / 'config/defaults.json').write_text(json.dumps(self.policy))
            # Empty scenes would otherwise proceed directly to concat.txt writes.
            episode = folder / 'episode.json'; episode.write_text(json.dumps({'scenes': []}))
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch.object(studio, 'BASE', root), patch.object(studio, 'run') as external:
                with self.assertRaisesRegex(ValueError, 'supported full-body composer'):
                    studio.assemble(folder)
                external.assert_not_called()
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})


if __name__ == '__main__': unittest.main()
