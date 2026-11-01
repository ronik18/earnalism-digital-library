"""Fixed native queries/transport are tested using synthetic metadata, never APIs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch
from scripts import reader612_native_observer as m

ROOT=Path(__file__).resolve().parents[1]


class Tests(unittest.TestCase):
    def setUp(self):
        self.binding=json.loads((ROOT/'internal/release/reader612_native_preparation.json').read_text())
        self.now=datetime(2026,11,1,12,tzinfo=timezone.utc)
        b=self.binding
        self.backend={'id':b['retained_backend'],'status':'SUCCESS','projectId':m.RAILWAY_PROJECT,
            'serviceId':m.SERVICE,'environmentId':m.ENVIRONMENT,'snapshotId':b['retained_snapshot'],
            'canRollback':True,'canRedeploy':True,'retained_image_digest':b['retained_image']}
        self.runtime={'observed_sha256':'a'*64,'snapshot_cached_for_process':True}
        self.receipt={'observed_at':self.now.isoformat(),
            'scope':'ACTUAL_READ_ONLY_PROVIDER_CONFIG_ALIASES_AND_JOURNAL_NOT_NATIVE_EXERCISE',
            'backend':self.backend,'serving_runtime_source':self.runtime,'config_sha256':'b'*64,
            'staged_changes':False,'volumes':0}
        self.receipt['receipt_sha256']=m.digest(self.receipt)
        self.health={'status':'ok','deployment':{'deployment_id':b['retained_backend']},'runtime_source':self.runtime}

    def observer(self):
        o=m.Reader612MetadataObserver(ROOT,clock=lambda:self.now)
        o.verify_versions=Mock()
        dep={k:v for k,v in self.backend.items() if k!='retained_image_digest'}
        dep['meta']={'imageDigest':self.binding['retained_image'],'private_other_field':'DO_NOT_EXPORT'}
        o._read=Mock(side_effect=[{'data':{'deployment':dep,'serviceInstance':{'latestDeployment':{'id':self.binding['retained_backend'],'status':'SUCCESS'}},'deploymentTriggers':{'edges':[],'pageInfo':{'hasNextPage':False}}}},
            {'id':m.PROJECT,'accountId':m.TEAM,'gitProviderOptions':{'createDeployments':'disabled'}},
            {'deploymentId':self.binding['retained_frontend']},{'deploymentId':self.binding['retained_frontend']},
            {'readyState':'READY','gitSource':{'sha':self.binding['retained_frontend_source']}}])
        return o

    def test_actual_fixed_read_shape_does_not_claim_native_acceptance(self):
        o=self.observer(); result=o.collect_baseline(self.binding,self.receipt,self.receipt['receipt_sha256'],health_read=lambda:self.health)
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['native_qualified'])
        self.assertNotIn('DO_NOT_EXPORT',json.dumps(result));self.assertEqual(o._read.call_count,5)
        query=o._read.call_args_list[0].args[0]
        self.assertEqual(query[:2],['railway','api']);self.assertTrue(query[2].startswith('query {'))
        self.assertNotIn('variables',query[2]);self.assertNotIn('mutation',query[2])

    def test_mismatched_connector_receipt_stops_before_calls(self):
        o=self.observer()
        with self.assertRaises(ValueError):o.collect_baseline(self.binding,self.receipt,'0'*64,health_read=lambda:self.health)
        o._read.assert_not_called()

    def test_backend_or_health_drift_holds(self):
        for changes in ({'status':'bad'},{'deployment':{'deployment_id':'wrong'}},{'runtime_source':{'observed_sha256':'wrong'}}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.observer().collect_baseline(self.binding,self.receipt,self.receipt['receipt_sha256'],health_read=lambda:{**self.health,**changes})

    def test_native_transport_is_exact_and_bounded(self):
        argv=['railway','api','mutation { deploymentRollback(id:"'+self.binding['retained_backend']+'") }','--compact']
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess(argv,0,'{}','')) as run:
            m.native_restore_transport(argv,timeout=60)
            run.assert_called_once_with(argv,capture_output=True,text=True,timeout=60,check=False)
        for bad in ([*argv,'--debug'],['railway','variables'],['sh','-c','anything']):
            with self.subTest(bad=bad),patch.object(m.subprocess,'run') as run:
                with self.assertRaises(ValueError):m.native_restore_transport(bad,timeout=60)
                run.assert_not_called()


if __name__=='__main__':unittest.main()
