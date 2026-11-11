"""Default-off private Sredni metadata operator. No automatic provisioning.

An immutable externally selected genuine owner/identity/source/execution packet
and separate scope permission are required before profile or network access.
"""
import argparse,asyncio,hashlib,json,os,stat
from datetime import datetime,timezone
from pathlib import Path
try:
    from . import sredni_initial_review_authority as proof
except ImportError:
    import sredni_initial_review_authority as proof

def local_source_sha256():
    root=Path(__file__).parent
    names=['sredni_initial_review_profile.py','sredni_initial_review_scope.py','sredni_initial_review_authority.py',
           'sredni_initial_review_operator.py','sredni_initial_review_operator_cli.py','reading_pass_service.py','server.py',
           'data/sredni_initial_review_authority.json']
    return proof.digest([{'path':n,'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in names])

def safe_output(result):
    safe={key:result[key] for key in ['status','schema','qualified','operation_id','authority_sha256','state_sha256',
        'receipt_sha256','actual_remaining_seconds','counter_only_remaining_seconds','starts_used','replay_permitted'] if key in result}
    if result.get('schema')=='earnalism.sredni_initial_review_namespace_status.v1' and type(result.get('qualified')) is bool:
        safe['status']='SREDNI_METADATA_NAMESPACES_QUALIFIED' if result['qualified'] else 'SREDNI_METADATA_NAMESPACES_UNQUALIFIED'
        safe['actual_remaining_seconds']=None
    return safe

def seal(directory,name,value):
    directory=Path(directory);info=directory.lstat()
    proof.need(stat.S_ISDIR(info.st_mode) and not directory.is_symlink() and info.st_uid==os.getuid()
               and stat.S_IMODE(info.st_mode)==0o700,'PRIVATE_EXISTING_JOURNAL_REQUIRED')
    proof.need(isinstance(name,str) and name==Path(name).name,'EXACT_JOURNAL_FILENAME_REQUIRED')
    fd=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(json.dumps(proof.normalized(value),sort_keys=True,separators=(',',':')).encode());stream.flush();os.fsync(stream.fileno())
        dfd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
    except Exception:raise proof.AdmissionStop('JOURNAL_UNKNOWN_OUTCOME_NO_REPLAY') from None

async def runtime(args,admitted,bundle,receipts):
    # All imports below follow actual local admission and exclusive intent.
    proof.files.qualify_journal(admitted.journal)
    proof.need(args.journal and str(args.journal)==admitted.journal['path'],'EXACT_RUNTIME_JOURNAL_REQUIRED')
    proof.need(args.database and hashlib.sha256(args.database.encode()).hexdigest()==receipts['execution']['database_name_sha256'],
               'EXACT_PRIVATE_DATABASE_TARGET_REQUIRED')
    is_status=args.status
    if not is_status:
        proof.current(admitted)
        seal(args.journal,admitted.operation_id+'.attempt.json',{
            'schema':'earnalism.sredni_initial_review_permanent_attempt.v1','operation_id':admitted.operation_id,
            'authority_sha256':admitted.authority_sha256,'action':admitted.action,
            'status':'DURABLE_INTENT_OUTCOME_NOT_YET_KNOWN','created_at':datetime.now(timezone.utc).isoformat()})
    else:
        # Status is reconciliation of the same admitted prior intent, never a
        # new free-form database reader or a permission to replay that write.
        path=args.journal/(admitted.operation_id+'.attempt.json')
        proof.need(path.is_file() and not path.is_symlink(),'PRIOR_EXACT_INTENT_REQUIRED_FOR_STATUS')
        intent=json.loads(path.read_text())
        proof.need(intent.get('authority_sha256')==admitted.authority_sha256
                   and intent.get('operation_id')==admitted.operation_id,'STATUS_INTENT_IDENTITY_CHANGED')
    profile=proof.private_json(args.mongo_profile,receipts['execution']['mongo_profile_sha256'])
    proof.need(set(profile)=={'uri'} and isinstance(profile['uri'],str)
               and profile['uri'].startswith(('mongodb://','mongodb+srv://')),'EXACT_PRIVATE_MONGO_PROFILE_REQUIRED')
    from motor.motor_asyncio import AsyncIOMotorClient
    try:
        from . import sredni_initial_review_operator as operator
        from .catalog_truth import load_controlled_artifact_book
    except ImportError:
        import sredni_initial_review_operator as operator
        from catalog_truth import load_controlled_artifact_book
    # No driver reads/writes retries. Outer Root wallclock bound is additional.
    client=AsyncIOMotorClient(profile['uri'],retryWrites=False,retryReads=False,tz_aware=True,
        serverSelectionTimeoutMS=5000,connectTimeoutMS=5000,socketTimeoutMS=10000,maxPoolSize=2)
    try:
        db=client[args.database]
        if is_status:
            if admitted.action=='prepare-namespace':
                await operator.member(db,admitted,current_auth=False,no_cap=False)
                return await operator.namespace_status(db)
            return await operator.status(db,client,admitted)
        proof.current(admitted)
        book=load_controlled_artifact_book('sredni-vashtar',include_content=False)
        proof.need(isinstance(book,dict) and book.get('slug')=='sredni-vashtar','EXACT_CONTROLLED_SOURCE_BOOK_REQUIRED')
        if admitted.action=='observe':result=await operator.observe_initial(db,client,admitted,book)
        elif admitted.action=='prepare-namespace':result=await operator.prepare_namespace_one_shot(db,client,admitted,book)
        else:result=await operator.execute_one_shot(db,client,admitted,book)
        seal(args.journal,admitted.operation_id+'.result.json',result)
        return result
    finally:client.close()

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group()
    m.add_argument('--check-local',action='store_true');m.add_argument('--execute',action='store_true');m.add_argument('--status',action='store_true')
    m.add_argument('--observe-initial',action='store_true')
    p.add_argument('--authority',type=Path);p.add_argument('--authority-sha256');p.add_argument('--mongo-profile',type=Path)
    p.add_argument('--database');p.add_argument('--journal',type=Path)
    args=p.parse_args(argv)
    if not args.authority:
        proof.need(not args.execute and not args.status and not args.observe_initial,'REAL_AUTHORITY_REQUIRED')
        print(json.dumps({'status':'LOCAL_SOURCE_PREPARATION_ONLY_NO_AUTHORITY_NO_DB','actual_remaining_seconds':None,'database_access':False}))
        return 0
    try:
        a,b,r=proof.admit(args.authority,args.authority_sha256,now=datetime.now(timezone.utc),allow_expired_status=args.status)
        # An abort-only observer may be reviewed independently of the running
        # application. Its own code and the actual serving source remain
        # separately pinned; this never qualifies either for a metadata write.
        observer_only = (a.action=='observe'
                         and r['source'].get('scope')==proof.READ_ONLY_SOURCE_SCOPE)
        expected_local = (r['execution']['observer_source_files_sha256'] if observer_only
                          else r['source']['source_files_sha256'])
        proof.need(expected_local==local_source_sha256(),'LOCAL_SOURCE_NOT_ACTUAL_QUALIFIED_SERVING_SOURCE')
        if not args.execute and not args.status and not args.observe_initial:
            print(json.dumps({'status':'LOCAL_RECEIPTS_PARSED_CURRENT_METADATA_UNVERIFIED','actual_remaining_seconds':None,'database_access':False}))
            return 0
        proof.need(args.mongo_profile and args.database and args.journal,'EXPLICIT_PRIVATE_RUNTIME_INPUTS_REQUIRED')
        proof.need((a.action=='observe') is args.observe_initial,'READONLY_OBSERVATION_AND_WRITE_ACTIONS_MUST_BE_EXPLICITLY_SEPARATE')
        result=asyncio.run(asyncio.wait_for(runtime(args,a,b,r),timeout=50))
        # Full own-state observation is exclusive0600 in the approved journal.
        # Stdout never includes raw identities, account data or private rows.
        print(json.dumps(safe_output(result),sort_keys=True));return 0
    except Exception as exc:
        # Never emit URI, raw driver diagnostics, account identities or secrets.
        print(json.dumps({'status':'HOLD_RECONCILE_UNKNOWN_OUTCOME_NO_REPLAY','error_class':type(exc).__name__,
                          'actual_remaining_seconds':None,'replay_permitted':False}));return 2

if __name__=='__main__':raise SystemExit(main())
