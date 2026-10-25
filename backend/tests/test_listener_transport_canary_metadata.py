"""Exercise the real helper AST without importing provider or DB clients."""
import ast,copy
from pathlib import Path
from types import SimpleNamespace

def helper(*,cohort=True,approved=True):
    source=Path(__file__).resolve().parents[1]/'server.py'
    tree=ast.parse(source.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_listener_transport_canary_audio')
    package={'package_version':'sha256-'+'a'*64,'duration_ms':491436}
    namespace={'_controlled_artifact_doc':lambda *a,**kw:{'audiobook_package_canary':{'rollout_percentage':5}},'_can_expose_audiobook_package_canary':lambda *a:approved,'_selected_audiobook_package':lambda *a,**kw:(package if cohort else None,'b'*64,'DUMMY_PUBLIC_ROLLOUT')}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    return namespace['_listener_transport_canary_audio']
def test_no_guest_reader_or_noncanary_presentation():
    audio={'enabled':False,'assets':{}}
    for params,principal in [({}, {'role':'user'}),({'transport_canary':'1'},None),({'transport_canary':'1'},{'role':'admin'})]:
        actual,cookie=helper()(audio,'the-open-window',SimpleNamespace(query_params=params),principal)
        assert actual is audio and cookie==''
def test_cohort_is_metadata_only_cached_audio_unchanged():
    audio={'enabled':False,'assets':{}};original=copy.deepcopy(audio)
    actual,cookie=helper()(audio,'the-open-window',SimpleNamespace(query_params={'transport_canary':'1'}),{'role':'user'})
    assert audio==original and actual['enabled'] is False and actual['assets']=={}
    assert actual['transport_canary']['package_version']=='sha256-'+'a'*64
    assert cookie=='DUMMY_PUBLIC_ROLLOUT'
def test_noncohort_or_unapproved_never_gets_controls():
    audio={'enabled':False}
    for cohort,approved in [(False,True),(True,False)]:
        actual,cookie=helper(cohort=cohort,approved=approved)(audio,'the-open-window',SimpleNamespace(query_params={'transport_canary':'1'}),{'role':'user'})
        assert 'transport_canary' not in actual
