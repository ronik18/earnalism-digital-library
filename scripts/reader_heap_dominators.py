"""Compute strong-edge heap dominators; heap snapshots stay local and private."""
import json,sys
from pathlib import Path

def retained(snapshot):
 m=snapshot['snapshot']['meta'];nf=m['node_fields'];nw=len(nf);n=snapshot['nodes'];e=snapshot['edges'];ew=len(m['edge_fields']);et=m['edge_types'][0];N=len(n)//nw;adj=[[] for _ in range(N)];pos=0
 for i in range(N):
  for _ in range(n[i*nw+nf.index('edge_count')]):
   if et[e[pos]]!='weak':adj[i].append(e[pos+2]//nw)
   pos+=ew
 number=[0]*N;vertex=[None,0];number[0]=1;parent=[0,0];stack=[(0,iter(adj[0]))]
 while stack:
  src,it=stack[-1]
  try:dst=next(it)
  except StopIteration:stack.pop();continue
  if not number[dst]:number[dst]=len(vertex);vertex.append(dst);parent.append(number[src]);stack.append((dst,iter(adj[dst])))
 count=len(vertex)-1;pred=[[] for _ in range(count+1)]
 for src in range(N):
  if number[src]:
   for dst in adj[src]:
    if number[dst]:pred[number[dst]].append(number[src])
 semi=list(range(count+1));label=list(range(count+1));ancestor=[0]*(count+1);dom=[0]*(count+1);bucket=[[] for _ in range(count+1)]
 def evaluate(v):
  if not ancestor[v]:return label[v]
  chain=[];x=v
  while ancestor[x] and ancestor[ancestor[x]]:chain.append(x);x=ancestor[x]
  for x in reversed(chain):
   if semi[label[ancestor[x]]]<semi[label[x]]:label[x]=label[ancestor[x]]
   ancestor[x]=ancestor[ancestor[x]]
  return label[v]
 for w in range(count,1,-1):
  for v in pred[w]:semi[w]=min(semi[w],semi[evaluate(v)])
  bucket[semi[w]].append(w);ancestor[w]=parent[w]
  for v in bucket[parent[w]]:
   u=evaluate(v);dom[v]=u if semi[u]<semi[v] else parent[w]
  bucket[parent[w]]=[]
 for w in range(2,count+1):
  if dom[w]!=semi[w]:dom[w]=dom[dom[w]]
 size=[0]+[n[vertex[i]*nw+nf.index('self_size')] for i in range(1,count+1)]
 for i in range(count,1,-1):size[dom[i]]+=size[i]
 s=snapshot['strings'];types=m['node_types'][0];out=[]
 for i in range(1,count+1):
  at=vertex[i]*nw;name=s[n[at+1]]
  if 'reader-v2__visual-viewport' in name or name=='(Global handles)' or name.startswith('<main'):
   out.append({'name':name,'type':types[n[at]],'id':n[at+2],'retained_bytes':size[i],'dominator':s[n[vertex[dom[i]]*nw+1]] if dom[i] else None})
 return sorted(out,key=lambda x:x['retained_bytes'],reverse=True)
if __name__=='__main__':
 root=Path(sys.argv[1]);files=['reader-handles-5.heapsnapshot','reader-handles-20.heapsnapshot','reader-handles-21.heapsnapshot','reader-nohandles-20.heapsnapshot'];out=[]
 for name in files:
  p=root/name
  if p.exists():out.append({'snapshot':name,'dominators':retained(json.loads(p.read_text()))[:12]})
 (root/'dominator-analysis.json').write_text(json.dumps(out,indent=2));print('Computed',len(out),'dominator snapshots')
