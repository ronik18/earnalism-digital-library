"""Exact committed native source-QA adoption, not storage/release or listening fiction."""
from pathlib import Path
import hashlib,json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import native_scored_package as native
from rights_decision_gate import load_audio_package_binding,record_sha256

class ExactCedarAdoptionTests(unittest.TestCase):
    def test_exact_committed_native_adoption_and_evidence(self):
        folder=native.REGISTRY.parent/'selfish-giant-cedar-20261102'
        descriptor=json.loads((folder/'release-descriptor.json').read_text())
        package=json.loads((folder/'delivery-mapping.json').read_text())
        self.assertEqual(native.validate(descriptor,package,'en',native.legacy.DOWNSTREAM),descriptor)
        adoption=native.load_adoption({key:descriptor[key] for key in native.IDENTITY_KEYS})
        for role,digest in adoption['evidence_sha256'].items():
            self.assertEqual(hashlib.sha256((folder/'evidence'/(role+'.json')).read_bytes()).hexdigest(),digest)
        self.assertEqual(descriptor['master_mp3_sha256'],'543117b5c47f0459d0d194156949904d84ecf37107bf7076e679f038c08da817')
        self.assertFalse(descriptor['release_candidate_evidence']['all_release_gates_passed'])
        self.assertEqual(descriptor['known_release_blockers'],native.legacy.DOWNSTREAM)
        binding=load_audio_package_binding('the-selfish-giant',native.sha(native.canonical(descriptor)))
        self.assertEqual(binding['record_sha256'],record_sha256(adoption['audio_use_decision']))

if __name__=='__main__':unittest.main()
