"""Owner-scoped, bounded keyset paging for wallet usage, without lease secrets."""
import base64
import json

FIELDS = {key: 1 for key in ('id', 'type', 'seconds', 'reason', 'created_at', 'actor', 'session_id', 'content_type', 'content_id')}
FIELDS['_id'] = 0


def history_query(user_id, cursor=''):
    query = {'user_id': user_id}
    if cursor:
        try:
            if len(cursor) > 2048:
                raise ValueError()
            at, row_id = json.loads(base64.urlsafe_b64decode(cursor).decode())
            if not all(isinstance(x, str) and 0 < len(x) <= 200 for x in (at, row_id)):
                raise ValueError()
        except Exception as exc:
            raise ValueError('Invalid usage cursor') from exc
        query['$or'] = [{'created_at': {'$lt': at}}, {'created_at': at, 'id': {'$lt': row_id}}]
    return query


def history_page(rows, limit):
    visible = rows[:limit]
    more = len(rows) > limit
    cursor = ''
    if more and visible:
        last = visible[-1]
        cursor = base64.urlsafe_b64encode(json.dumps([last['created_at'], last['id']]).encode()).decode()
    return {'items': visible, 'next_cursor': cursor, 'has_more': more}
