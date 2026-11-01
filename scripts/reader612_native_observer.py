"""Fixed native read/transport implementations; no approval resolver or entrypoint.

Config evidence must be supplied from the existing authenticated describe_service
connector, pinned by an independently reviewed receipt digest. This module cannot
authenticate an arbitrary local JSON as a connector response or an owner approval.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import urllib.request
from scripts.india_release_observer import NativeMetadataObserver
from scripts.india_release_provider_adapter import (
    PROJECT, TEAM, RAILWAY_PROJECT, SERVICE, ENVIRONMENT, digest,
)


def native_restore_transport(argv, *, timeout):
    # No arbitrary native mutation/query or shell, headers, tokens or debug flags.
    pattern=r'mutation \{ deploymentRollback\(id:"[0-9a-f-]{36}"\) \}'
    if (len(argv)!=4 or argv[:2]!=['railway','api'] or argv[3]!='--compact'
            or not re.fullmatch(pattern,argv[2]) or timeout!=60):
        raise ValueError('Only exact bounded native restore transport admitted')
    return subprocess.run(argv,capture_output=True,text=True,timeout=timeout,check=False)


def public_health():
    # Fixed normal anonymous GET; no country or authorization headers.
    with urllib.request.urlopen('https://api.theearnalism.com/api/healthz', timeout=30) as response:
        if response.status!=200:raise ValueError('Healthy baseline required')
        return json.load(response)


class Reader612MetadataObserver(NativeMetadataObserver):
    def collect_baseline(self, binding, config_receipt, receipt_sha256, *, health_read=public_health):
        self.verify_versions()
        r={k:v for k,v in config_receipt.items() if k!='receipt_sha256'}
        if (digest(r)!=receipt_sha256 or config_receipt.get('receipt_sha256')!=receipt_sha256
                or config_receipt.get('scope')!='ACTUAL_READ_ONLY_PROVIDER_CONFIG_ALIASES_AND_JOURNAL_NOT_NATIVE_EXERCISE'):
            raise ValueError('Reviewed authenticated connector evidence required')
        from scripts.reader612_native_restore import fresh
        fresh(config_receipt['observed_at'],self.clock())
        baseline=binding['retained_backend']
        if not re.fullmatch('[0-9a-f-]{36}',baseline):raise ValueError('Exact baseline required')
        query=('query { deployment(id:"'+baseline+'") '
            '{id status projectId serviceId environmentId snapshotId canRollback canRedeploy meta} '
            'serviceInstance(environmentId:"'+ENVIRONMENT+'",serviceId:"'+SERVICE+'") '
            '{latestDeployment {id status}} '
            'deploymentTriggers(projectId:"'+RAILWAY_PROJECT+'",environmentId:"'+ENVIRONMENT+'",'
            'serviceId:"'+SERVICE+'",first:100) {edges {node {id}} pageInfo {hasNextPage}} }')
        raw=self._read(['railway','api',query,'--compact'])
        if raw.get('errors'):raise ValueError('Native metadata unavailable; no retry')
        data=raw['data'];dep=data['deployment']
        # Raw meta is never logged or persisted, and only imageDigest survives.
        projected={k:dep.get(k) for k in ('id','status','projectId','serviceId','environmentId','snapshotId','canRollback','canRedeploy')}
        projected['retained_image_digest']=(dep.get('meta') or {}).get('imageDigest')
        if (projected!=config_receipt['backend'] or projected['id']!=baseline
                or projected['snapshotId']!=binding['retained_snapshot']
                or projected['retained_image_digest']!=binding['retained_image']
                or (projected['projectId'],projected['serviceId'],projected['environmentId'])!=(RAILWAY_PROJECT,SERVICE,ENVIRONMENT)
                or projected['status']!='SUCCESS' or projected['canRollback'] is not True
                or data['serviceInstance']['latestDeployment']!={'id':baseline,'status':'SUCCESS'}):
            raise ValueError('Retained backend/image/config baseline drift')
        triggers=data['deploymentTriggers']
        if triggers['edges'] or triggers['pageInfo']['hasNextPage']:raise ValueError('Auto-deploy trigger state unqualified')
        project=self._read(['vercel','api','/v9/projects/'+PROJECT,'--method','GET','--raw','--scope',TEAM])
        if (project.get('id')!=PROJECT or project.get('accountId')!=TEAM
                or (project.get('gitProviderOptions') or {}).get('createDeployments')!='disabled'
                or json.loads((self.source_root/'frontend/vercel.json').read_text())['git']['deploymentEnabled'] is not False):
            raise ValueError('Both frontend auto-deploy controls required OFF')
        aliases={host:self._read(['vercel','api','/v4/aliases/'+host,'--method','GET','--raw','--scope',TEAM])['deploymentId'] for host in ('theearnalism.com','www.theearnalism.com')}
        front=self._read(['vercel','api','/v13/deployments/'+binding['retained_frontend'],'--method','GET','--raw','--scope',TEAM])
        if (set(aliases.values())!={binding['retained_frontend']} or front.get('readyState')!='READY'
                or front.get('gitSource',{}).get('sha')!=binding['retained_frontend_source']):
            raise ValueError('Serving frontend/source drift')
        health=health_read()
        if (health.get('status')!='ok' or health.get('deployment',{}).get('deployment_id')!=baseline
                or health.get('runtime_source',{}).get('observed_sha256')!=config_receipt['serving_runtime_source']['observed_sha256']
                or config_receipt.get('staged_changes') is not False or config_receipt.get('volumes')!=0):
            raise ValueError('Source/health/config drift')
        return {'scope':'ACTUAL_FIXED_READ_ONLY_METADATA_NOT_NATIVE_QUALIFICATION',
            'observed_at':self.clock().isoformat(),'backend':projected,'aliases':aliases,
            'config_receipt_sha256':receipt_sha256,'config_sha256':config_receipt['config_sha256'],
            'runtime_source':health['runtime_source'],'provider_mutations':0,
            'execution_authorized':False,'native_qualified':False,
            'holds':['AUTHENTIC_OWNER_PROTECTED_RESOLVER_REQUIRED','ACTUAL_REDIS_STARTUP_PROOF_REQUIRED','NATIVE_ROLE_QUALIFICATION_NOT_PERFORMED']}
