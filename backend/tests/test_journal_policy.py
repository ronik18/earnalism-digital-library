from backend.journal_policy import sanitize_journal_html


def test_preserves_editorial_links_images_and_headings():
    result = sanitize_journal_html('<h2>Reading</h2><p><a href="https://theearnalism.com/library">Library</a></p><img src="https://example.com/photo.jpg" alt="A book">')
    assert '<h2>Reading</h2>' in result
    assert 'href="https://theearnalism.com/library"' in result
    assert 'alt="A book"' in result


def test_removes_executable_markup_and_unsafe_urls():
    result = sanitize_journal_html('<script>alert(1)</script><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">click</a><iframe src="https://example.com"></iframe>')
    assert '<script' not in result
    assert 'onerror' not in result
    assert 'javascript:' not in result
    assert '<iframe' not in result

# Extract narrow handlers without starting the production server or connecting DB.
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import uuid
from datetime import datetime, timezone, timedelta


def handlers():
    tree = ast.parse(Path('backend/server.py').read_text())
    names = {'journal_like', 'journal_unlike', 'journal_comment'}
    nodes = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name in names]
    for node in nodes:
        node.decorator_list = []
        node.args.defaults = []
    namespace = {'uuid': uuid, 'now_iso': lambda: 'actual-test-time', 'JournalCommentIn': object, 'datetime': datetime, 'timezone': timezone, 'timedelta': timedelta}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<journal-handlers>', 'exec'), namespace)
    return namespace


def test_like_retry_does_not_duplicate_and_comments_do_not_expose_identity():
    class Likes:
        rows = {}
        async def update_one(self, key, update, upsert=False):
            self.rows.setdefault(key['_id'], update['$setOnInsert'])
        async def count_documents(self, query):
            return len(self.rows)
        async def delete_one(self, key):
            self.rows.pop(key['_id'], None)
    class Comments:
        rows = []
        async def count_documents(self, query):
            return 0
        async def insert_one(self, row):
            self.rows.append(row)
    async def published(slug):
        assert slug == 'real-post'
    ns = handlers()
    ns.update(db=SimpleNamespace(journal_likes=Likes(), journal_comments=Comments()), _published_journal=published)
    async def run():
        user = {'id': 'private-id', 'name': 'Reader', 'email': 'private@example.com'}
        assert (await ns['journal_like']('real-post', user))['likes'] == 1
        assert (await ns['journal_like']('real-post', user))['likes'] == 1
        comment = await ns['journal_comment']('real-post', SimpleNamespace(text='  Thoughtful response  '), user)
        assert comment['text'] == 'Thoughtful response'
        assert 'user_id' not in comment and 'email' not in comment
        assert (await ns['journal_unlike']('real-post', user))['likes'] == 0
    asyncio.run(run())

def test_every_social_write_requires_reader_or_admin_authorization():
    source = Path('backend/server.py').read_text()
    tree = ast.parse(source)
    reader_writes = {'journal_like', 'journal_unlike', 'journal_comment', 'journal_delete_own_comment'}
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name in reader_writes:
            assert 'Depends(require_user)' in ast.get_source_segment(source, node)
    moderator = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'journal_moderate_comment')
    assert 'Depends(require_admin)' in ast.get_source_segment(source, moderator)


def test_draft_and_retired_posts_are_not_open_for_engagement():
    from fastapi import HTTPException
    tree = ast.parse(Path('backend/server.py').read_text())
    node = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == '_published_journal')
    namespace = {'HTTPException': HTTPException, 'RETIRED_PUBLIC_BLOG_SLUGS': {'retired'}}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<journal-published>', 'exec'), namespace)
    class Posts:
        async def find_one(self, query):
            assert query['is_published'] is True
            return None
    namespace['db'] = SimpleNamespace(blog_posts=Posts())
    async def run():
        for slug in ['draft', 'missing', 'retired']:
            try:
                await namespace['_published_journal'](slug)
            except HTTPException as error:
                assert error.status_code == 404
            else:
                raise AssertionError('unpublished discussion unexpectedly available')
    asyncio.run(run())

def test_http_routes_auth_fail_closed_and_idempotent_like():
    from fastapi import FastAPI, APIRouter, Depends, HTTPException, Response
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, Field
    app = FastAPI(); router = APIRouter(prefix='/api')
    async def deny():
        raise HTTPException(401, 'Not authenticated')
    class Posts:
        async def find_one(self, query):
            return {'slug': 'published'} if query['slug'] == 'published' else None
    class Likes:
        def __init__(self): self.rows = {}
        async def update_one(self, query, update, upsert=False): self.rows.setdefault(query['_id'], update['$setOnInsert'])
        async def delete_one(self, query): self.rows.pop(query['_id'], None)
        async def count_documents(self, query): return len(self.rows)
        async def find_one(self, query): return self.rows.get(query['_id'])
    class Comments:
        def __init__(self): self.rows = []
        async def count_documents(self, query): return len(self.rows)
        async def insert_one(self, row): self.rows.append(row)
    source = ast.parse(Path('backend/server.py').read_text())
    names = {'JournalCommentIn', '_published_journal', 'journal_like', 'journal_unlike', 'journal_comment', 'journal_my_like'}
    nodes = [n for n in source.body if getattr(n, 'name', '') in names]
    ns = dict(api=router, BaseModel=BaseModel, Field=Field, Depends=Depends, require_user=deny, HTTPException=HTTPException, Response=Response, RETIRED_PUBLIC_BLOG_SLUGS={'retired'}, db=SimpleNamespace(blog_posts=Posts(), journal_likes=Likes(), journal_comments=Comments()), uuid=uuid, datetime=datetime, timezone=timezone, timedelta=timedelta, now_iso=lambda: datetime.now(timezone.utc).isoformat())
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<journal-http>', 'exec'), ns)
    app.include_router(router)
    with TestClient(app) as client:
        assert client.put('/api/blog/published/like').status_code == 401
        assert client.post('/api/blog/published/comments', json={'text': 'hello'}).status_code == 401
        app.dependency_overrides[deny] = lambda: {'id': 'user'}
        assert client.put('/api/blog/draft/like').status_code == 404
        assert client.put('/api/blog/retired/like').status_code == 404
        assert client.put('/api/blog/published/like').json() == {'liked': True, 'likes': 1}
        assert client.put('/api/blog/published/like').json() == {'liked': True, 'likes': 1}
        personal = client.get('/api/blog/published/my-like')
        assert personal.json() == {'liked': True}
        assert personal.headers['cache-control'] == 'private, no-store'
        assert client.delete('/api/blog/published/like').json() == {'liked': False, 'likes': 0}
        assert client.post('/api/blog/draft/comments', json={'text': 'hello'}).status_code == 404
        assert client.post('/api/blog/published/comments', json={'text': '   '}).status_code == 422
        response = client.post('/api/blog/published/comments', json={'text': '<img onerror="bad">'})
        assert response.status_code == 201
        assert response.json()['text'] == '<img onerror="bad">'
        assert 'user_id' not in response.json()
        for _ in range(2):
            assert client.post('/api/blog/published/comments', json={'text': 'next comment'}).status_code == 201
        assert client.post('/api/blog/published/comments', json={'text': 'too fast'}).status_code == 429
