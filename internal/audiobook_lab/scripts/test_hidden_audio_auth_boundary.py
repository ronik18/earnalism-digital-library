"""Hidden proof compatibility only; never an authentication or playback bypass."""
import unittest,copy,json
from pathlib import Path
import audiobook_active_release_v2 as m
class Tests(unittest.TestCase):
    def proof(self):
        slug='the-open-window'
        return {'schema_version':'audiobook_hidden_before_proof.v2','slug':slug,'status':'PUBLIC_AUDIO_HIDDEN_AUTH_BOUNDARY_VERIFIED','reader_url':f'https://www.theearnalism.com/reader/{slug}','reader_http_status':200,'public_book_url':f'https://theearnalism.com/api/books/{slug}','public_book_http_status':200,'legacy_audio_url':f'https://theearnalism.com/api/reader/book/{slug}/audiobook','legacy_audio_http_status':404,'package_manifest_url':f'https://theearnalism.com/api/reader/book/{slug}/audiobook/manifest','package_manifest_http_status':401,'package_manifest_denial_code':'AUTH_REQUIRED','public_audio_enabled':False,'public_audiobook_enabled':False,'public_audio_status':'NOT_AVAILABLE','public_audio_url_present':False,'browser_listen_control_count':0,'browser_audio_request_count':None,'network_silence_claimed':False,'checked_at':'2026-10-25T15:00:00Z','browser_observation':'synthetic no-listen control','note':'Synthetic fixture, not production evidence'}
    def test_valid(self):
        m.validate_hidden_before_proof(self.proof(),slug='the-open-window',reference_time='2026-10-25T15:01:00Z')
    def test_denial_alone_flags_wrong_urls_age_or_unobserved_never_suffice(self):
        for change in [{'public_audio_enabled':True},{'public_audiobook_enabled':True},{'public_audio_url_present':True},{'browser_listen_control_count':1},{'package_manifest_http_status':200},{'package_manifest_denial_code':'OTHER'},{'package_manifest_url':'https://other.example/'},{'browser_observation':''},{'checked_at':'2026-10-23T15:00:00Z'},{'network_silence_claimed':True}]:
            with self.subTest(change=change),self.assertRaises(m.ReleasePointerError):m.validate_hidden_before_proof({**self.proof(),**change},slug='the-open-window',reference_time='2026-10-25T15:01:00Z')
    def test_legacy401_remains_rejected(self):
        p=self.proof();p['schema_version']=m.HIDDEN_BEFORE_PROOF_SCHEMA
        with self.assertRaises(m.ReleasePointerError):m.validate_hidden_before_proof(p,slug='the-open-window',reference_time='2026-10-25T15:01:00Z')
if __name__=='__main__':unittest.main()

class ExactRetainedDescriptorTitleTests(unittest.TestCase):
    def test_exact_owner_adopted_omitted_display_fields(self):
        root=Path(__file__).resolve().parent.parent/'release_gate/open_window_listened_successor_v2'
        d=json.loads((root/'release-descriptor.json').read_text());p=json.loads((root/'package-identity.json').read_text())
        context={'public_book':{'slug':'the-open-window','title':'The Open Window','author':'Saki'},'reader_manifest':{'language':'en'}}
        m._validate_canary_title_author(context,d,p)
        context['public_book']['author']='Other'
        with self.assertRaises(m.ReleasePointerError):m._validate_canary_title_author(context,d,p)
    def test_no_other_descriptor_gets_exception(self):
        context={'public_book':{'slug':'the-open-window','title':'The Open Window','author':'Saki'},'reader_manifest':{'language':'en'}}
        with self.assertRaises(m.ReleasePointerError):m._validate_canary_title_author(context,{'book_uuid':'other'}, {})
