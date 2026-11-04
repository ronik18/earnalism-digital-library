"""Nonqualifying CI-only Cargo lock diagnostic. Never builds or edits source."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib
from verify_railway_helper_source import _edges as edges, EXPECTED_DIRECT as DIRECT

UPSTREAM_SHA = '0a5087a0d781b67a205051f011998fbd8c4f585b529d8b0d037a1eef01cddd63'
REGISTRY = 'registry+https://github.com/rust-lang/crates.io-index'
ROOT = ('earnalism-railway-archiver-test', '0.1.0')


def need(ok, message):
    if not ok: raise ValueError(message)


def packages(raw):
    d=tomllib.loads(raw.decode());need(d.get('version')==4,'lock format differs')
    rows={}
    for p in d['package']:
        key=(p['name'],p['version']);need(key not in rows,'duplicate package identity');rows[key]=p
    return rows


def validate_candidate(original, candidate, upstream):
    need(hashlib.sha256(upstream).hexdigest()==UPSTREAM_SHA,'frozen upstream lock differs')
    old,new,up=packages(original),packages(candidate),packages(upstream)
    need(ROOT in old and ROOT in new,'workspace identity differs')
    need(edges(old[ROOT],old)==DIRECT,'original direct pins differ')
    for key,p in old.items():
        if key!=ROOT:
            original = up.get(key)
            need(original is not None and {k:v for k,v in p.items() if k!='dependencies'}=={k:v for k,v in original.items() if k!='dependencies'},'original registry coordinates differ')
            need(edges(p,old)<=edges(original,up),'original dependency edge differs from upstream')
    need(set(new)<=set(old),'new package/version forbidden')
    need({k:v for k,v in new[ROOT].items() if k!='dependencies'}==
         {k:v for k,v in old[ROOT].items() if k!='dependencies'},'workspace fields changed')
    need(edges(old[ROOT],old)==edges(new[ROOT],new),'direct dependencies changed')
    changes=[]
    for key,p in new.items():
        if key==ROOT:continue
        need(p.get('source')==REGISTRY and key in up,'new nonregistry package forbidden')
        for field in ('name','version','source','checksum'):
            need(p.get(field)==old[key].get(field)==up[key].get(field),'registry coordinate/checksum changed')
        need(set(p)<= {'name','version','source','checksum','dependencies'},'unexpected package fields')
        before,after=edges(old[key],old),edges(p,new)
        need(after<=before,'new dependency edge forbidden')
        if before!=after:changes.append({'package':list(key),'removed_edges':[list(x) for x in sorted(before-after)]})
    reachable=set();todo=[ROOT]
    while todo:
        key=todo.pop()
        if key in reachable:continue
        reachable.add(key);todo.extend(edges(new[key],new))
    need(reachable==set(new),'unreachable packages remain')
    return {'status':'PINNED_SUBSET_CANDIDATE_ONLY_NOT_BUILD_OR_HELPER_PASS',
            'old_registry_packages':len(old)-1,'candidate_registry_packages':len(new)-1,
            'removed_packages':[list(x) for x in sorted(set(old)-set(new))],
            'dependency_edge_removals':changes,'versions_sources_checksums_unchanged':True,
            'candidate_lock_sha256':hashlib.sha256(candidate).hexdigest(),
            'requires_independent_review_and_source_pinning':True,'helper_executed':False}


def _hash_inputs(package):
    names=['Cargo.toml','Cargo.lock','SOURCE-PINS.json','upstream-Cargo.lock','src/main.rs']
    values={}
    for name in names:
        p=package/name;need(p.is_file() and not p.is_symlink(),'regular pinned input required')
        values[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return values


def diagnose(package, output, *, run=subprocess.run, env=None):
    env=os.environ if env is None else env
    need(env.get('GITHUB_ACTIONS')=='true' and env.get('GITHUB_EVENT_NAME')!='workflow_dispatch', 'ordinary CI only')
    need(env.get('GITHUB_REPOSITORY')=='ronik18/earnalism-digital-library','wrong repository')
    package=Path(package).resolve(strict=True);output=Path(output)
    temp=Path(env['RUNNER_TEMP']).resolve(strict=True)
    need(output.is_absolute() and not output.exists(),'fresh absolute diagnostic directory required')
    parent=output.parent.resolve(strict=True)
    need(parent==temp or parent.is_relative_to(temp),'diagnostic must stay in RUNNER_TEMP')
    need(not output.is_relative_to(package),'diagnostic cannot use source checkout')
    before=_hash_inputs(package)
    output.mkdir(mode=0o700);copy=output/'package';(copy/'src').mkdir(parents=True,mode=0o700)
    for name in ['Cargo.toml','Cargo.lock','src/main.rs']:
        shutil.copyfile(package/name,copy/name)
    (output/'original-Cargo.lock').write_bytes((package/'Cargo.lock').read_bytes())
    command=['cargo','update','--offline','--workspace','--manifest-path',str(copy/'Cargo.toml')]
    result={'schema':'earnalism.cargo-lock-diagnostic.v1','scope':'QUARANTINED_CANDIDATE_NOT_SOURCE_ADOPTION_OR_BUILD',
            'observed_at':datetime.now(timezone.utc).isoformat(),'command':command,'input_sha256':before,
            'ci_context':{k:env.get(k) for k in ['GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB','GITHUB_REPOSITORY','GITHUB_EVENT_NAME']},
            'helper_executed':False,'locked_build_passed':False,'native_qualified':False,'provider_calls':0,
            'original_gate_must_remain_failed':True,'status':'NOT_EXECUTED'}
    child={k:env[k] for k in ['PATH','HOME','CARGO_HOME','RUSTUP_HOME'] if k in env}
    child.update({'CARGO_NET_OFFLINE':'true','CARGO_TERM_COLOR':'never'})
    try:
        r=run(command,cwd=copy,env=child,capture_output=True,timeout=120,check=False)
        stdout=r.stdout if isinstance(r.stdout,bytes) else (r.stdout or '').encode()
        stderr=r.stderr if isinstance(r.stderr,bytes) else (r.stderr or '').encode()
        result.update({'exit_code':r.returncode,'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
                       'stderr_sha256':hashlib.sha256(stderr).hexdigest()})
        if r.returncode:
            match=re.search(rb'no matching package named `([A-Za-z0-9_-]{1,80})`',stderr)
            result['status']='OFFLINE_METADATA_UNAVAILABLE' if match else 'OFFLINE_WORKSPACE_UPDATE_FAILED'
            if match:result['missing_public_crate']=match[1].decode()
        else:
            need((copy/'Cargo.lock').is_file() and not (copy/'Cargo.lock').is_symlink(),'regular candidate lock required')
            result['candidate_validation']=validate_candidate((package/'Cargo.lock').read_bytes(),
                (copy/'Cargo.lock').read_bytes(),(package/'upstream-Cargo.lock').read_bytes())
            result['status']='CANDIDATE_READY_FOR_REVIEW_GATE_STILL_FAILED'
    except (subprocess.TimeoutExpired,OSError,ValueError,KeyError,tomllib.TOMLDecodeError) as e:
        result.update({'status':'DIAGNOSTIC_FAILED_NOT_QUALIFIED','error_type':type(e).__name__})
    finally:
        candidate_path=copy/'Cargo.lock'
        result['candidate_lock_exists']=candidate_path.is_file() and not candidate_path.is_symlink()
        candidate=candidate_path.read_bytes() if result['candidate_lock_exists'] else b''
        if result['candidate_lock_exists']:(output/'candidate-Cargo.lock').write_bytes(candidate)
        else:result['status']='CANDIDATE_LOCK_UNAVAILABLE_REJECTED'
        try:result['quarantine_code_unchanged']=all(hashlib.sha256((copy/n).read_bytes()).hexdigest()==before[n] for n in ['Cargo.toml','src/main.rs'])
        except OSError:result['quarantine_code_unchanged']=False
        if not result['quarantine_code_unchanged']:result['status']='QUARANTINE_CODE_CHANGED_REJECTED'
        diff=difflib.unified_diff((package/'Cargo.lock').read_text().splitlines(True),
            candidate.decode(errors='replace').splitlines(True),fromfile='original-Cargo.lock',tofile='candidate-Cargo.lock')
        (output/'lock.diff').write_text(''.join(diff))
        try:result['source_inputs_unchanged']=_hash_inputs(package)==before
        except (OSError,ValueError):result['source_inputs_unchanged']=False
        if not result['source_inputs_unchanged']:result['status']='SOURCE_CHANGED_REJECTED'
        (output/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--package-root',required=True);p.add_argument('--output-dir',required=True)
    a=p.parse_args();r=diagnose(a.package_root,a.output_dir)
    print(json.dumps({'scope':r['scope'],'status':r['status'],'original_gate_must_remain_failed':True}))
    raise SystemExit(1)  # Diagnostic success never makes the original locked build pass.
