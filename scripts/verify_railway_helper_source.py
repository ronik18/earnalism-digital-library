"""Admit reviewed upstream helper bytes/registry closure before CI compilation."""
import hashlib
import json
from pathlib import Path
import tomllib

UPLOAD_SHA = 'b7f670c63ef9667e6ea3d60d9b435419857b81d5bdce64d495c9c2c2677e91fa'
UPSTREAM_LOCK_SHA = '0a5087a0d781b67a205051f011998fbd8c4f585b529d8b0d037a1eef01cddd63'
FUNCTION_SHA = '135dfba8d194ed081dbcb5249617f9cae6ded958fb3367c34b50d31b6f2acf81'


def check(root):
    root = Path(root)
    pins = json.loads((root/'SOURCE-PINS.json').read_bytes())
    source = (root/'upstream-upload.rs.txt').read_bytes()
    upstream_lock = (root/'upstream-Cargo.lock').read_bytes()
    lock = (root/'Cargo.lock').read_bytes()
    if not (hashlib.sha256(source).hexdigest() == UPLOAD_SHA):
        raise ValueError("source/lock admission check 18 failed")
    if not (hashlib.sha256(upstream_lock).hexdigest() == UPSTREAM_LOCK_SHA):
        raise ValueError("source/lock admission check 19 failed")
    if not (hashlib.sha256(lock).hexdigest() == pins['derived_lock_sha256']):
        raise ValueError("source/lock admission check 20 failed")
    text = source.decode()
    function = text[text.index('pub fn create_deploy_tarball('):text.index('\n/// Upload a deploy tarball')].strip()+'\n'
    if not (hashlib.sha256(function.encode()).hexdigest() == FUNCTION_SHA):
        raise ValueError("source/lock admission check 23 failed")
    harness = (root/'src/main.rs').read_text()
    actual_function = harness[harness.index('pub fn create_deploy_tarball('):harness.index('\nfn main()')].strip()+'\n'
    if not (actual_function == function):
        raise ValueError("source/lock admission check 26 failed")
    if not (not any(x in harness for x in ['reqwest', 'GQLClient', 'upload_deploy_tarball', 'Configs', 'RAILWAY_TOKEN'])):
        raise ValueError("source/lock admission check 27 failed")
    upstream = {(p['name'],p['version']):p for p in tomllib.loads(upstream_lock.decode())['package']}
    packages = tomllib.loads(lock.decode())['package']
    registry = [p for p in packages if p.get('source')]
    if not (len(registry) == pins['registry_package_closure']):
        raise ValueError("source/lock admission check 31 failed")
    for package in registry:
        if not (package == upstream[(package['name'],package['version'])]):
            raise ValueError("source/lock admission check 33 failed")
        if not (package['source'] == 'registry+https://github.com/rust-lang/crates.io-index'):
            raise ValueError("source/lock admission check 34 failed")
        if not (len(package['checksum']) == 64):
            raise ValueError("source/lock admission check 35 failed")
    roots = [p for p in packages if not p.get('source')]
    if not (len(roots) == 1 and roots[0]['name'] == 'earnalism-railway-archiver-test'):
        raise ValueError("source/lock admission check 37 failed")
    manifest = tomllib.loads((root/'Cargo.toml').read_text())
    if not (manifest['package']['publish'] is False):
        raise ValueError("source/lock admission check 39 failed")
    expected_names = {'anyhow','gzp','ignore','num_cpus','synchronized-writer','tar'}
    if set(manifest['dependencies']) != expected_names:
        raise ValueError('exact pure-helper dependency inventory required')
    for name, value in manifest['dependencies'].items():
        version = value if isinstance(value,str) else value['version']
        if not (version.startswith('=') and (name,version[1:]) in upstream):
            raise ValueError("source/lock admission check 42 failed")
        if isinstance(value,dict):
            if not (set(value) <= {'version','default-features','features'}):
                raise ValueError("source/lock admission check 44 failed")
    return {'scope':'EXACT_UPSTREAM_HELPER_SOURCE_AND_LOCK_ADMISSION_ONLY',
            'upstream_module_sha256':UPLOAD_SHA,'function_sha256':FUNCTION_SHA,
            'registry_packages':len(registry),'helper_executed':False,'provider_calls':0}


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args()
    print(json.dumps(check(a.root),sort_keys=True))
