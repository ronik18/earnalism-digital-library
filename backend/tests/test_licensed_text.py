import hashlib
import json
from backend.licensed_text import public_license_notice

def package(tmp_path):
    (tmp_path/'chapters').mkdir()
    (tmp_path/'chapters'/'c1.json').write_text(json.dumps({'content':'Actual text'}))
    notice={'schema_version':'earnalism.text-license.v1','slug':'test','license':'CC-BY-SA-4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','attribution':'Wikisource contributors','changes':'Formatting only','scope':'Transcription only','disclaimer':'No warranties','source_url':'https://bn.wikisource.org/w/index.php?oldid=123','contributors_url':'https://bn.wikisource.org/w/index.php?action=history','chapter_sha256':[hashlib.sha256(b'Actual text').hexdigest()]}
    raw=json.dumps(notice).encode();(tmp_path/'license_notice.json').write_bytes(raw)
    (tmp_path/'public_book.json').write_text(json.dumps({'slug':'test','chapters':[{'id':'c1','order':1}],'license_notice_sha256':hashlib.sha256(raw).hexdigest()}))
    return notice

def test_bound_notice(tmp_path):
    notice=package(tmp_path)
    result=public_license_notice(tmp_path)
    assert result['attribution']==notice['attribution']
    assert 'chapter_sha256' not in result

def test_missing_notice(tmp_path):
    assert public_license_notice(tmp_path) is None

def test_tampered_notice(tmp_path):
    package(tmp_path);(tmp_path/'license_notice.json').write_text('{}')
    assert public_license_notice(tmp_path) is None

def test_content_mismatch(tmp_path):
    package(tmp_path);(tmp_path/'chapters'/'c1.json').write_text(json.dumps({'content':'Other edition'}))
    assert public_license_notice(tmp_path) is None
