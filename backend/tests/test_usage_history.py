import pytest
from backend.usage_history import history_page, history_query, FIELDS


def test_paging_beyond_100_preserves_tied_timestamps_and_account_scope():
    rows = [{'id': f'{i:04d}', 'created_at': '2026-10-26T00:00:00Z'} for i in range(151, 0, -1)]
    seen=[]; cursor=''
    while rows:
        assert history_query('owner', cursor)['user_id']=='owner'
        page=history_page(rows[:51],50)
        seen.extend(r['id'] for r in page['items'])
        cursor=page['next_cursor'];rows=rows[50:]
        if cursor:
            q=history_query('different-owner',cursor)
            assert q['user_id']=='different-owner'
            assert q['$or'][1]['id']['$lt']==seen[-1]
    assert len(seen)==len(set(seen))==151


@pytest.mark.parametrize('cursor',['garbage','WzEsMl0=','e30=','a'*2049])
def test_invalid_cursor_is_rejected(cursor):
    with pytest.raises(ValueError):history_query('owner',cursor)


def test_output_projection_excludes_authentication_and_private_account_fields():
    assert not {'user_id','lease_token','lease_token_hash','auth_session_id'} & FIELDS.keys()
