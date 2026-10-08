import asyncio, json, os, uuid
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
assert os.environ['ENVIRONMENT']=='uat'
assert os.environ['MONGODB_URL']=='mongodb://127.0.0.1:27018/?replicaSet=earnalism-uat-rs0'
from backend import server

async def main():
    mongo=AsyncIOMotorClient(os.environ['MONGODB_URL'])
    db=mongo['perf_security_'+uuid.uuid4().hex]
    redis=Redis(host='127.0.0.1',port=27019,db=14)
    prefix='performance-security:'+uuid.uuid4().hex
    server.db=db
    server._redis_client=redis
    server._redis_available=True
    server.REDIS_KEY_PREFIX=prefix
    transport=httpx.ASGITransport(app=server.app,client=('127.0.0.1',49103))
    clients=[httpx.AsyncClient(transport=transport,base_url='https://localhost') for _ in range(4)]
    result={}
    try:
        await db.analytics_events.create_index('event_id',unique=True,sparse=True)
        for i,c in enumerate(clients[2:]):
            response=await c.post('/api/users/signup',json={'name':'Disposable performance user','email':f'performance-{i}@example.com','password':'Local-fixture-only-password!'} )
            assert response.status_code==200, response.status_code
            c.headers['authorization']='Bearer '+response.json()['token']
        profiles=[await c.get('/api/users/me') for c in clients]
        assert [p.status_code for p in profiles]==[401,401,200,200]
        assert profiles[2].json()['id']!=profiles[3].json()['id']
        projections=[await c.get('/api/books') for c in clients]
        assert all(p.status_code==200 for p in projections)
        assert all(p.json()==projections[0].json() for p in projections)
        serialized=json.dumps(projections[0].json())
        assert all(p.json()['id'] not in serialized for p in profiles[2:])
        assert 'password_hash' not in serialized and 'reading_seconds_balance' not in serialized
        assert all('public' not in p.headers.get('cache-control','') for p in projections[2:])
        result.update(cache_user_crossover=0,cache_entitlement_crossover=0,public_representation_equal=True)
        events=['page_view','homepage_view','library_view','title_view']
        for event in events:
            response=await clients[0].post('/api/analytics/events',json={'event':event,'route':'/library','deployment_environment':'uat'})
            assert response.status_code==200,(event,response.status_code)
        response=await clients[2].post('/api/analytics/events',json={'event':'library_view','route':'/library','deployment_environment':'uat'})
        assert response.status_code==200
        assert await db.analytics_events.count_documents({})==5
        result.update(analytics_delivery_status=200,analytics_records=5)
        logout=await clients[2].post('/api/users/logout')
        assert logout.status_code==200
        assert (await clients[2].get('/api/users/me')).status_code==401
        assert (await clients[3].get('/api/users/me')).status_code==200
        result.update(session_logout_revoked=True,other_session_unaffected=True)
        print(json.dumps(result))
    finally:
        for c in clients: await c.aclose()
        keys=[k async for k in redis.scan_iter(prefix+'*')]
        if keys: await redis.delete(*keys)
        await redis.aclose()
        await mongo.drop_database(db.name)
        mongo.close()

asyncio.run(main())
