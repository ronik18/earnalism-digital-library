import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from scripts.frontend_public_build import F,public_inputs,build_environment,output_identity,digest,run
from scripts.test_manual_production_release_workflow import ROOT,parse_workflow

class PublicBuildTests(unittest.TestCase):
    def setUp(self):
        self.reference = mock.patch('scripts.frontend_public_build.PUBLIC_REFERENCE')
        reference = self.reference.start();self.addCleanup(self.reference.stop)
        reference.read_text.return_value=json.dumps({'REACT_APP_BACKEND_URL':'https://api.theearnalism.com','REACT_APP_ENABLE_LAUNCH_ANALYTICS':'true','REACT_APP_GOOGLE_CLIENT_ID':'synthetic-public.apps.googleusercontent.com'})
        self.approval={'controller_sha':'a'*40,'frontend_sha':F,'public_build_inputs':{
          'all_values_public':True,'operator':'SYNTHETIC_TEST_ONLY','excluded_client_inputs':['REACT_APP_API_URL'],
          'env':{'REACT_APP_BACKEND_URL':'https://api.theearnalism.com','REACT_APP_ENABLE_LAUNCH_ANALYTICS':'true',
                 'REACT_APP_GOOGLE_CLIENT_ID':'synthetic-public.apps.googleusercontent.com'}}}

    def test_only_exact_public_projection_and_real_source_binding_pass(self):
        self.assertEqual(public_inputs(self.approval,'a'*40),self.approval['public_build_inputs']['env'])
        for key,value in [('all_values_public',False),('operator',''),('excluded_client_inputs',[])]:
            a=copy.deepcopy(self.approval);a['public_build_inputs'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):public_inputs(a,'a'*40)
        with self.assertRaises(ValueError):public_inputs(self.approval,'b'*40)
        for key,value in [('UNREVIEWED_SECRET','synthetic-private'),('REACT_APP_API_URL','synthetic-private'),('REACT_APP_GOOGLE_CLIENT_ID',''),('REACT_APP_BACKEND_URL','https://other.example'),('REACT_APP_ENABLE_LAUNCH_ANALYTICS','false')]:
            a=copy.deepcopy(self.approval);a['public_build_inputs']['env'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):public_inputs(a,'a'*40)

    def test_build_does_not_inherit_credentials_or_unreviewed_client_values(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ,{'VERCEL_TOKEN':'SYNTHETIC_PRIVATE','NODE_OPTIONS':'SYNTHETIC_PRIVATE','REACT_APP_API_URL':'SYNTHETIC_PRIVATE','REACT_APP_EXTRA':'SYNTHETIC_PRIVATE'}):
            env=build_environment(temp,public_inputs(self.approval,'a'*40),Path(temp)/'seo')
            self.assertNotIn('SYNTHETIC_PRIVATE',env.values())
            self.assertNotIn('REACT_APP_API_URL',env);self.assertNotIn('REACT_APP_EXTRA',env)
            self.assertEqual(env['REACT_APP_ENABLE_LAUNCH_ANALYTICS'],'true')
            self.assertEqual(env['NPM_CONFIG_SAVE'],'false')

    def test_predeploy_rejects_changed_output_or_projection(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'.vercel/output';out.mkdir(parents=True);(out/'config.json').write_text('{"fixture":true}')
            receipt=root/'receipt.json';projection=public_inputs(self.approval,'a'*40)
            from scripts.frontend_public_build import SETTINGS
            receipt.write_text(json.dumps({'controller_sha':'a'*40,'frontend_sha':F,'public_inputs_sha256':digest(projection),'settings':SETTINGS,'output':output_identity(root)}))
            with mock.patch('scripts.frontend_public_build.exact_clean_source'),mock.patch('scripts.frontend_public_build.subprocess.check_output',return_value='frontend/package.json\n'):
                run(root,None,receipt,self.approval,'a'*40,True)
                (out/'config.json').write_text('{"fixture":false}')
                with self.assertRaisesRegex(ValueError,'changed'):run(root,None,receipt,self.approval,'a'*40,True)

    def test_real_builder_boundary_uses_private_env_and_binds_actual_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp).resolve();root=base/'source';(root/'frontend').mkdir(parents=True)
            cli=base/'tooling/vc.js';cli.parent.mkdir();cli.write_text('fixture never executed')
            receipt=base/'receipt.json'
            def build(command,**kwargs):
                self.assertEqual(command,['node',str(cli),'build','--prod','--yes'])
                self.assertEqual(kwargs['cwd'],root);self.assertEqual(kwargs['timeout'],900)
                self.assertEqual(kwargs['env']['SEO_ASSETS_OUTPUT_DIR'],str(base/'seo'))
                self.assertNotIn('VERCEL_TOKEN',kwargs['env']);self.assertNotIn('REACT_APP_API_URL',kwargs['env'])
                self.assertEqual(kwargs['env']['REACT_APP_ENABLE_LAUNCH_ANALYTICS'],'true')
                out=root/'.vercel/output';out.mkdir();(out/'config.json').write_text('synthetic output')
            with mock.patch('scripts.frontend_public_build.exact_clean_source'),mock.patch('scripts.frontend_public_build.subprocess.check_output',return_value='frontend/package.json\n'),mock.patch('scripts.frontend_public_build.shutil.which',return_value=str(cli)),mock.patch('scripts.frontend_public_build.subprocess.run',side_effect=build):
                result=run(root,base/'seo',receipt,self.approval,'a'*40)
                self.assertEqual(result['output'][0]['path'],'.vercel/output/config.json')
                self.assertEqual((root/'.vercel/.env.production.local').stat().st_size,0)
                self.assertNotIn('REACT_APP_API_URL',result['public_inputs'])

    def test_external_output_link_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'root';out=root/'.vercel/output';out.mkdir(parents=True)
            external=Path(temp)/'external';external.write_text('synthetic');(out/'external').symlink_to(external)
            with self.assertRaisesRegex(ValueError,'External'):output_identity(root)

    def test_production_removes_pull_and_rechecks_public_binding_before_mutation(self):
        source=(ROOT/'.github/workflows/reader-frontend-production.yml').read_text()
        workflow=parse_workflow(source);steps=workflow['jobs']['deploy_frontend']['steps']
        self.assertNotIn('Pull Vercel production environment',source)
        build=next(x for x in steps if x['name']=='Build frontend for Vercel')
        self.assertIn('scripts.frontend_public_build',build['run']);self.assertIn('RELEASE_APPROVAL_JSON',build['env'])
        deploy=next(x for x in steps if x['name']=='Deploy frontend to Vercel production')
        self.assertLess(deploy['run'].index('--verify-only'),deploy['run'].index('args=(deploy --prebuilt --prod'))
        self.assertIn('RAILWAY_TOKEN',deploy['env']);self.assertIn('RELEASE_APPROVAL_JSON',deploy['env'])
        self.assertEqual(next(x for x in steps if x['name']=='Set up Node')['with']['node-version'],'20.20.2')

class PublicQualificationWiringTests(unittest.TestCase):
    def test_public_projection_qualification_is_ordinary_readonly_PR_CI(self):
        workflow=parse_workflow((ROOT/'.github/workflows/vercel-packaging.yml').read_text())
        self.assertEqual(workflow['permissions'],{'contents':'read'})
        job=workflow['jobs']['public_build_qualification'];text=json.dumps(job)
        self.assertEqual(job['timeout-minutes'],25);self.assertNotIn('environment',job);self.assertNotIn('secrets.',text)
        self.assertIn('--public-profile',text);self.assertNotIn('workflow_dispatch',text)
        self.assertEqual(job['steps'][0]['with']['persist-credentials'],False)
        upload=job['steps'][-1]['with'];self.assertEqual(upload['retention-days'],3);self.assertEqual(upload['compression-level'],0)
        source=(ROOT/'scripts/qualify_frontend_build_only.py').read_text()
        self.assertIn('public_profile=False',source);self.assertIn("env.pop('REACT_APP_API_URL', None)",source)
        self.assertIn("'dependency-identity-gate.json'",source);self.assertIn('runtime_identity(cli_path=',source)
        self.assertIn('UNCHANGED_T_EMPTY_APP_ENV_STATIC_SETTINGS',source)

if __name__=='__main__':unittest.main()
