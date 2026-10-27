"""Exercise the real streaming iterator without importing application startup."""
import ast
from pathlib import Path
import pytest

def iterator():
 source=Path(__file__).resolve().parents[1]/'server.py'
 fn=next(x for x in ast.parse(source.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='_streaming_body_iterator')
 scope={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),scope)
 return scope['_streaming_body_iterator']
class Body:
 def __init__(self,size):self.data=b'x'*size;self.closed=False;self.requests=[]
 def read(self,size):self.requests.append(size);result=self.data[:size];self.data=self.data[size:];return result
 def close(self):self.closed=True
@pytest.mark.parametrize('size',[0,1,65535,65536,65537,200000,1048576])
def test_stream_preserves_all_bytes_with_bounded_reads(size):
 body=Body(size);chunks=list(iterator()(body));assert b''.join(chunks)==b'x'*size;assert all(0<len(c)<=65536 for c in chunks);assert all(n<=65536 for n in body.requests);assert body.closed

def test_first_yield_does_not_require_full_segment_and_cancellation_closes():
 body=Body(200000);stream=iterator()(body);assert len(next(stream))==65536;assert len(body.data)==134464;stream.close();assert body.closed

def test_storage_read_failure_closes_body():
 body=Body(1)
 def broken(size):raise OSError('synthetic read error')
 body.read=broken
 with pytest.raises(OSError):list(iterator()(body))
 assert body.closed
