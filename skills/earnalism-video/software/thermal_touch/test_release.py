"""Read-only gate regressions; synthetic values never authorize publication."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import release

class ReleaseTests(unittest.TestCase):
    def test_evidence_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Exception):
                release.inside(Path(d), '../outside')

    def test_platform_requires_each_verified_format_and_exact_assets(self):
        with tempfile.TemporaryDirectory() as d:
            kit = Path(d)
            settings = dict(made_for_kids=False, age_restricted=False, video_language='English',
                ai_disclosure=True, paid_promotion=False, automatic_chapters=False,
                automatic_places=False, automatic_concepts=False, automatic_dubbing=False,
                visual_enhancement=False, audio_enhancement=False, remixing='audio_only')
            item = dict(video_id='SYNTHETIC', uploaded_media_sha256='digest',
                manual_english_captions_sha256='digest', reviewed_cover_sha256='digest',
                cover_verified=True, copyright_check='NO_ISSUES', community_check='NO_ISSUES',
                playback_verified=True, caption_display_verified=True, settings=settings,
                saved_title='SYNTHETIC', saved_description='#earnalism #learnalism')
            value = dict(delivery_manifest_sha256='manifest',
                formats={'landscape':copy.deepcopy(item),'shorts':copy.deepcopy(item)})
            owner={'audience': {'selfDeclaredMadeForKids':False,'ageRestriction':False}}
            with patch.object(release, 'sha', return_value='digest'):
                release.platform_check(value, kit, owner, 'manifest')
                for field, bad in [('caption_display_verified',False),('uploaded_media_sha256','wrong'),
                                   ('cover_verified',False),('copyright_check','PENDING')]:
                    wrong=copy.deepcopy(value); wrong['formats']['shorts'][field]=bad
                    with self.assertRaises(Exception):
                        release.platform_check(wrong, kit, owner, 'manifest')
                wrong=copy.deepcopy(value); del wrong['formats']['shorts']
                with self.assertRaises(Exception):
                    release.platform_check(wrong, kit, owner, 'manifest')
                wrong=copy.deepcopy(value); wrong['formats']['landscape']['settings']['audio_enhancement']=True
                with self.assertRaises(Exception):
                    release.platform_check(wrong, kit, owner, 'manifest')
