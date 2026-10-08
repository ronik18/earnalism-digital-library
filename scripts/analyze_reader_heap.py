import json,collections,sys
from pathlib import Path
root=Path(sys.argv[1]);out=[]
for file in sorted(root.glob('*.heapsnapshot')):
 p=json.loads(file.read_text());m=p['snapshot']['meta'];nf=m['node_fields'];nw=len(nf);ef=m['edge_fields'];ew=len(ef);nodes=p['nodes'];edges=p['edges'];strings=p['strings'];types=m['node_types'][0];et=m['edge_types'][0];N=len(nodes)//nw;di=nf.index('detachedness');starts=[];pos=0
 for i in range(N):starts.append(pos);pos+=nodes[i*nw+nf.index('edge_count')]*ew
 parent=[None]*N;parent[0]=(-1,'root');q=collections.deque([0])
 while q:
  src=q.popleft();end=starts[src]+nodes[src*nw+nf.index('edge_count')]*ew
  for j in range(starts[src],end,ew):
   if et[edges[j]]=='weak':continue
   dst=edges[j+2]//nw
   if parent[dst] is None:
    name=str(edges[j+1]) if et[edges[j]] in ('element','hidden') else strings[edges[j+1]]
    parent[dst]=(src,name);q.append(dst)
 detached=[i for i in range(N) if nodes[i*nw+di]==2];families=collections.Counter(strings[nodes[i*nw+1]] for i in detached)
 targets=[i for i in detached if 'reader-v2' in strings[nodes[i*nw+1]]][:2];paths=[]
 for target in targets:
  path=[];i=target
  for _ in range(24):
   if parent[i] is None:break
   par,edge=parent[i];path.append({'node':strings[nodes[i*nw+1]],'via':edge,'type':types[nodes[i*nw]],'id':nodes[i*nw+2]})
   if par<0:break
   i=par
  paths.append(list(reversed(path)))
 sizes=collections.Counter()
 for i in range(N):sizes[(types[nodes[i*nw]],strings[nodes[i*nw+1]])]+=nodes[i*nw+3]
 out.append({'snapshot':file.name,'detached_nodes':len(detached),'detached_families':families.most_common(10),'top_shallow_bytes':[(a,b,v) for (a,b),v in sizes.most_common(10)],'strong_retainer_paths':paths})
Path(root/'heap-analysis.json').write_text(json.dumps(out,indent=2));print('Analyzed',len(out),'snapshots')
