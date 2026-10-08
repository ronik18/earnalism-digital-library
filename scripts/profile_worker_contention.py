"""Bounded worker/foreground contention, actual code and disposable data only.

The worker's final publication adapter is replaced by a draft-fixture write;
this measures queue/package/DB contention, not production source throughput.
"""
import asyncio
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import uuid
from pymongo import monitoring


class Commands(monitoring.CommandListener):
    def __init__(self):
        self.values = []
    def started(self, event):
        pass
    def succeeded(self, event):
        self.values.append(event.duration_micros / 1000)
    def failed(self, event):
        self.values.append(event.duration_micros / 1000)


mongo_commands = Commands()
monitoring.register(mongo_commands)

from scripts.platform_backend_benchmark import summary, server
from backend.tests.test_reading_pass_text_admission_mongo_integration import _isolated_database, _seed_retained_content
import httpx
from redis.asyncio import Redis


class TimedRedis(Redis):
    async def execute_command(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return await super().execute_command(*args, **kwargs)
        finally:
            self.timings.append((time.perf_counter() - started) * 1000)

WORKER = Path(os.environ.get('PERF_WORKER_WORKTREE', '')).resolve()
if not os.environ.get('PERF_WORKER_WORKTREE') or not (WORKER / 'backend/catalogue_worker.py').exists():
    raise SystemExit('Explicit existing worker worktree required')

CHILD = r'''
import json,os,sys,tempfile,time,resource
from pathlib import Path
from pymongo import MongoClient
from pymongo import monitoring
class Commands(monitoring.CommandListener):
 def __init__(self): self.values=[]
 def started(self,event): pass
 def succeeded(self,event): self.values.append(event.duration_micros/1000)
 def failed(self,event): self.values.append(event.duration_micros/1000)
commands=Commands()
from backend.catalogue_worker import Config,Worker
from backend.tests.test_catalogue_worker import package
database=sys.argv[1];enabled=sys.argv[2];concurrency=sys.argv[3];batch=sys.argv[4]
assert database.startswith('rpadmit_it_')
client=MongoClient(os.environ['MONGODB_URL'],tz_aware=True,event_listeners=[commands])
db=client[database]
with tempfile.TemporaryDirectory(prefix='performance-worker-packages-') as root:
 for i in range(200):
  Path(root,f'{i:03}.json').write_text(json.dumps(package(f'performance-owned-{i}')))
 config=Config({'CATALOGUE_WORKER_ENABLED':enabled,'CATALOGUE_CONCURRENCY':concurrency,
  'CATALOGUE_BATCH_SIZE':batch,'CATALOGUE_PACKAGE_DIR':root,'CATALOGUE_REQUESTS_PER_MINUTE':'6',
  'CATALOGUE_DISCOVERY_INTERVAL':'1',
  'CATALOGUE_MEMORY_LIMIT_MB':'512','CATALOGUE_ACTIVATION_ENABLED':'false'})
 def processor(book,job):
  db.performance_worker_drafts.update_one({'slug':book['slug']},{'$set':{
   'slug':book['slug'],'source_hash':book['source_hash'],'is_published':False}},upsert=True)
 worker=Worker(config,db,processor)
 cpu=time.process_time();start=time.monotonic();cycles=0
 print('READY',flush=True)
 # Parent closes stdin after bounded foreground measurements.
 import threading
 stop=threading.Event()
 threading.Thread(target=lambda:(sys.stdin.read(),stop.set()),daemon=True).start()
 while not stop.is_set() and time.monotonic()-start<30:
  worker.cycle();cycles+=1;time.sleep(.01)
 elapsed=time.monotonic()-start
 completed=db.catalogue_jobs.count_documents({'state':'complete'})
 print(json.dumps({'elapsed_s':elapsed,'completed':completed,'jobs_per_s':completed/elapsed,
  'cycles':cycles,'cpu_ms':(time.process_time()-cpu)*1000,
  'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'queue_depth':db.catalogue_jobs.count_documents({'state':{'$in':['queued','processing','retry']}}),
  'queue_states':{row['_id']:row['n'] for row in db.catalogue_jobs.aggregate([{'$group':{'_id':'$state','n':{'$sum':1}}}])},
  'mongo_commands':len(commands.values),'mongo_command_ms_total':sum(commands.values),
  'mongo_command_ms_max':max(commands.values,default=0),
  'redis_operations':0,'external_source_requests':0,'activation':False}),flush=True)
client.close()
'''


async def main():
    cache = TimedRedis(host='127.0.0.1', port=27019, db=15)
    cache.timings = []
    prefix = 'performance-worker:' + uuid.uuid4().hex
    server.ENVIRONMENT = 'uat'
    server.RATE_LIMIT_ENABLED = False
    server.READING_PASS_V2_ENABLED = True
    server._redis_client = cache
    server._redis_available = True
    server.REDIS_KEY_PREFIX = prefix
    original_authority = server._reader_book_access_doc
    slug = 'worker-foreground-owned-fixture'
    async def authority(requested, *, admin_preview=False):
        if requested == slug:
            return {'slug':slug,'chapters':[{'id':'chapter-001','title':'Fixture','order':1}]}
        return await original_authority(requested, admin_preview=admin_preview)
    server._reader_book_access_doc = authority
    rows = []
    try:
        async with _isolated_database() as database:
            await _seed_retained_content(database, slug)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='https://localhost') as api:
                signup = await api.post('/api/users/signup',json={'name':'Disposable performance reader',
                    'email':'performance-worker@example.com','password':'local-only-performance-password'})
                assert signup.status_code == 200, signup.text
                api.headers['Authorization'] = 'Bearer ' + signup.json()['token']
                await database.users.update_one({'id':signup.json()['user']['id']},
                    {'$set':{'reading_seconds_balance':600,'wallet_seconds':600}})
                start = await api.post('/api/reading-pass/sessions/start',json={
                    'device_id':'performance-disposable-device','device_label':'Isolated performance',
                    'content_type':'text','content_id':slug,'canonical_page_index':4})
                assert start.status_code == 200, start.text
                api.headers['X-Reading-Pass-Session'] = start.json()['session_id']
                api.headers['X-Reading-Pass-Lease'] = start.json()['lease_token']
                books = await api.get('/api/books?view=library-v1')
                assert books.status_code == 200 and books.json()
                detail = '/api/books/' + books.json()[0]['slug']
                routes = ['/api/books?view=library-v1',detail,
                    f'/api/reading-pass/books/{slug}/pages/4','/api/analytics/event']
                modes = [('OFF','false',1,1),('ON_1','true',1,1),
                    ('CANARY','true',1,2),('SAFE_STRESS','true',4,8)]
                for repetition, (name, enabled, concurrency, batch) in [
                    (rep, mode) for rep in range(3) for mode in (modes if rep % 2 == 0 else list(reversed(modes)))]:
                    # Exercise genuine renewal by ending/reopening the disposable
                    # session between samples; never extend stored expiry by hand.
                    ended = await api.post('/api/reading-pass/sessions/end', json={'session_id':start.json()['session_id']})
                    assert ended.status_code == 200, ended.text
                    start = await api.post('/api/reading-pass/sessions/start',json={
                        'device_id':'performance-disposable-device','device_label':'Isolated performance',
                        'content_type':'text','content_id':slug,'canonical_page_index':4})
                    assert start.status_code == 200, start.text
                    api.headers['X-Reading-Pass-Session'] = start.json()['session_id']
                    api.headers['X-Reading-Pass-Lease'] = start.json()['lease_token']
                    # Reuse only this generated namespace, resetting fixture work.
                    for collection in await database.list_collection_names():
                        if collection.startswith('catalogue_') or collection == 'performance_worker_drafts':
                            await database.drop_collection(collection)
                    child = subprocess.Popen([sys.executable,'-c',CHILD,database.name,enabled,str(concurrency),str(batch)],
                        cwd=WORKER,env={**os.environ,'PYTHONPATH':str(WORKER)},stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    try:
                        ready = await asyncio.wait_for(asyncio.to_thread(child.stdout.readline), 20)
                        if ready != 'READY\n':
                            raise RuntimeError('Worker fixture failed before readiness: ' + child.stderr.read()[-2000:])
                        timings = {route:[] for route in routes};statuses=[]
                        route_statuses = {route:{} for route in routes}
                        mongo_commands.values.clear();cache.timings.clear()
                        cpu=time.process_time();began=time.perf_counter()
                        async def request(route):
                            before=time.perf_counter()
                            if route == '/api/analytics/event':
                                response=await api.post(route,json={'event':'page_view','route':'/library',
                                    'anonymous_session_id':'performance-disposable'})
                            else:
                                response=await api.get(route)
                            timings[route].append((time.perf_counter()-before)*1000)
                            statuses.append(response.status_code)
                            counts = route_statuses[route]
                            counts[response.status_code] = counts.get(response.status_code, 0) + 1
                        for _ in range(40):
                            await asyncio.gather(*(request(route) for route in routes for _ in range(2)))
                            await asyncio.sleep(.03)
                        duration=time.perf_counter()-began
                        child.stdin.close()
                        output=await asyncio.to_thread(child.stdout.read)
                        await asyncio.to_thread(child.wait,10)
                        assert child.returncode == 0, child.stderr.read()
                        rows.append({'mode':name,'repetition':repetition+1,'foreground':{route:summary(values) for route,values in timings.items()},
                            'errors':sum(status!=200 for status in statuses),'requests':len(statuses),
                            'route_statuses':route_statuses,
                            'throughput_rps':len(statuses)/duration,'foreground_cpu_ms':(time.process_time()-cpu)*1000,
                            'foreground_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                            'mongo_command_latency':summary(mongo_commands.values) if mongo_commands.values else None,
                            'redis_command_latency':summary(cache.timings) if cache.timings else None,
                            'worker':json.loads(output)})
                    finally:
                        if child.poll() is None:
                            child.terminate();await asyncio.to_thread(child.wait,10)
        print(json.dumps({'scope':'DISPOSABLE_ASGI_AUTHORIZED_READER_REAL_WORKER_QUEUE_DRAFT_ADAPTER',
            'worker_revision':subprocess.check_output(['git','-C',str(WORKER),'rev-parse','HEAD'],text=True).strip(),
            'rows':rows,'limitations':['No external source fetch; 6/min source budget not exercised.',
                'Draft fixture adapter is not production publication throughput.',
                'DB/cache command timings are aggregate overlapping I/O, not exclusive request stage time.',
                'Short local sample, not production SLO or saturation test.'],'production_changed':False},indent=2))
    finally:
        keys = [key async for key in cache.scan_iter(prefix+'*')]
        if keys:
            await cache.delete(*keys)
        await cache.aclose()
        server._reader_book_access_doc = original_authority


if __name__ == '__main__':
    asyncio.run(main())
