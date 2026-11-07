import tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from . import release
class PrivateReleaseTests(unittest.TestCase):
 def test_private_checker_never_infers_publication(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);c=root/'candidate';c.mkdir()
   (c/'delivery-manifest.json').write_text(json.dumps({'schema':'earnalism.condensation-private-kit.v1','publication_approved':False,'files':{}}))
   with patch.object(release,'sha',return_value=release.ORIGINAL_SHA),patch.object(release,'validate_inputs'):
    result=release.check_private(c,root)
    self.assertEqual(result['state'],'PRIVATE_REVIEW_REQUIRES_ACCEPTANCE');self.assertFalse(result['publication_approved']);self.assertFalse(result['uploads'])
    v=json.loads((c/'delivery-manifest.json').read_text());v['publication_approved']=True;(c/'delivery-manifest.json').write_text(json.dumps(v))
    with self.assertRaises(ValueError):release.check_private(c,root)
 def test_traversal_manifest_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);c=root/'candidate';c.mkdir()
   (c/'delivery-manifest.json').write_text(json.dumps({'schema':'earnalism.condensation-private-kit.v1','publication_approved':False,'files':{'../outside':'any'}}))
   with patch.object(release,'sha',return_value=release.ORIGINAL_SHA):
    with self.assertRaises(ValueError):release.check_private(c,root)
