"""Inert atomic control collection; no network, customer or persistence proof."""
import asyncio
import copy
from types import SimpleNamespace
from pymongo.errors import DuplicateKeyError

class Collection:
    def __init__(self):
        self.row = None; self.options = {}; self.fail_read = False; self.fail_finish = False; self.calls = []
    def with_options(self, **kwargs):
        self.options = kwargs
        return self
    async def find_one(self, query, **kwargs):
        self.calls.append(('read',query,kwargs))
        if self.fail_read: raise TimeoutError('synthetic authority unavailable')
        return copy.deepcopy(self.row)
    async def insert_one(self, row):
        self.calls.append(('insert',row))
        if self.row is not None:raise DuplicateKeyError('synthetic race')
        self.row=copy.deepcopy(row)
    async def find_one_and_update(self, query, update, **kwargs):
        self.calls.append(('cas',query,kwargs))
        if self.fail_finish and update['$set'].get('state')=='ACTIVE':raise TimeoutError('synthetic finish reply lost')
        if self.row is None or any(self.row.get(k)!=v for k,v in query.items()):return None
        self.row.update(copy.deepcopy(update['$set']))
        return copy.deepcopy(self.row)

def database():
    return SimpleNamespace(public_metadata_cache_control=Collection())
