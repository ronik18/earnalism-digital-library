"""Wrong immutable identity/payload/authority fails before native execution exists."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts import reader612_recovery_source as r

ROOT = Path(__file__).resolve().parents[1]


class Tests(unittest.TestCase):
    def setUp(self):
        self.binding = json.loads((ROOT/'internal/release/reader612_native_preparation.json').read_text())

    def test_source_preparation_never_claims_native_authority(self):
        self.assertIs(self.binding['execution_authorized'], False)
        self.assertIs(self.binding['native_qualified'], False)
        self.assertEqual(self.binding['application_base'], r.BASE)
        self.assertEqual(self.binding['prior_reader_source'], r.PRIOR)

    def test_bad_source_refs_never_invoke_git(self):
        for ref in ('HEAD', 'main', 'a'*39, 'a'*40+';true', '../secret'):
            with self.subTest(ref=ref), patch.object(r.subprocess,'check_output') as run:
                with self.assertRaisesRegex(ValueError,'Immutable'):r.blob(ROOT,ref,'backend/server.py')
                run.assert_not_called()

    def test_wrong_role_and_authority_denied_before_source_read(self):
        for key, value in [('role','CURRENT_OPEN'), ('schema','other'),
            ('application_base','a'*40), ('prior_reader_source','a'*40),
            ('execution_authorized',True), ('native_qualified',True)]:
            with self.subTest(key=key), patch.object(r,'qualify') as source:
                with self.assertRaisesRegex(ValueError,'not execution authority'):
                    r.qualify_binding(ROOT,{**self.binding,key:value},environment={})
                source.assert_not_called()

    def test_wrong_commit_or_tree_denied(self):
        for identity in [('a'*40,self.binding['tree_sha']), (self.binding['source_sha'],'b'*40)]:
            with self.subTest(identity=identity), patch.object(r,'qualify',return_value={}), patch.object(r.subprocess,'check_output',return_value='\n'.join(identity)):
                with self.assertRaisesRegex(ValueError,'source/tree mismatch'):
                    r.qualify_binding(ROOT,self.binding,environment={})

    def test_dirty_candidate_denied(self):
        with patch.object(r,'qualify',return_value={}), patch.object(r.subprocess,'check_output',side_effect=[self.binding['source_sha']+'\n'+self.binding['tree_sha'],b' M backend/server.py']):
            with self.assertRaisesRegex(ValueError,'Clean recovery'):
                r.qualify_binding(ROOT,self.binding,environment={})

    def test_ast_comparison_includes_transaction_methods(self):
        source='class S:\n def transaction(self):\n  return 1\n'
        self.assertNotEqual(r.definitions(source),r.definitions(source.replace('return 1','return 2')))

    def test_changed_payload_membership_runtime_and_count_denied(self):
        identity=self.binding['source_sha']+'\n'+self.binding['tree_sha']
        for rows, count, runtime in [([],0,self.binding['runtime_sha256']),
            ([],self.binding['payload_files'],'f'*64)]:
            with self.subTest(runtime=runtime), patch.object(r,'qualify',return_value={'runtime_sha256':runtime}), patch.object(r.subprocess,'check_output',side_effect=[identity,b'']), patch('scripts.backend_upload_payload.qualify',return_value={'files':rows}):
                with self.assertRaisesRegex(ValueError,'payload binding mismatch'):
                    r.qualify_binding(ROOT,self.binding,environment={})


if __name__ == '__main__':unittest.main()
