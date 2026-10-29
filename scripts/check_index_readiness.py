#!/usr/bin/env python3
"""Offline declaration/metadata comparison; cannot create, drop, or alter indexes."""
import argparse,json
from pathlib import Path
SEMANTICS=('unique','sparse','partialFilterExpression','expireAfterSeconds','collation')
def normalize(spec):
    key=spec.get('key');options=spec.get('options',spec)
    if isinstance(key,str):key=[[key,1]]
    if not isinstance(key,(list,tuple)) or not key:return None
    try:keys=tuple((str(k),d) for k,d in key)
    except (ValueError,TypeError):return None
    if any(not isinstance(d,(int,str)) or type(d) is bool for _,d in keys):return None
    collation=options.get('collation')
    if collation == {'locale':'simple'}:collation=None
    return (keys,bool(options.get('unique',False)),bool(options.get('sparse',False)),json.dumps(options.get('partialFilterExpression'),sort_keys=True,separators=(',',':')),options.get('expireAfterSeconds'),json.dumps(collation,sort_keys=True,separators=(',',':')))
def assess(declarations,metadata):
    result={'scope':'OFFLINE_INDEX_METADATA_ADMISSION','writes':0,'documentReads':0,'missing':[],'matched':[],'unknown':[],'potentialRedundantPrefixes':[],'queryPlanner':'UNVERIFIED_NO_EXPLAIN_EXECUTION','coverage':'SELECTED_COLLECTIONS_ONLY'}
    collections=metadata.get('collections') or {}
    for d in declarations:
        collection=d['collection'];sig=normalize(d)
        if collection not in collections:
            result['unknown'].append({'collection':collection,'line':d.get('line'),'reason':'NO_ACTUAL_METADATA'});continue
        if sig is None:
            result['unknown'].append({'collection':collection,'line':d.get('line'),'reason':'DYNAMIC_OR_INVALID_DECLARATION'});continue
        same=[i for i in collections[collection] if normalize(i)==sig]
        row={k:d.get(k) for k in ('collection','key','options','file','line')}
        if same:row['actualNames']=[x['name'] for x in same];result['matched'].append(row)
        else:row['state']='HOLD_UNIQUE_OR_RETENTION' if sig[1] or sig[4] is not None else 'PERFORMANCE_DRIFT';result['missing'].append(row)
    for collection,indexes in collections.items():
        for a in indexes:
            sa=normalize(a)
            if not sa or sa[1] or sa[4] is not None or a.get('name')=='_id_':continue
            for b in indexes:
                sb=normalize(b)
                if sb and len(sb[0])>len(sa[0]) and sb[0][:len(sa[0])]==sa[0] and sb[1:]==sa[1:]:
                    result['potentialRedundantPrefixes'].append({'collection':collection,'prefixIndex':a['name'],'longerIndex':b['name'],'action':'REVIEW_USAGE_AND_COST_ONLY_NO_DROP_AUTHORITY'})
    result['status']='HOLD' if result['missing'] else 'UNQUALIFIED' if result['unknown'] else 'DECLARATIONS_MATCH_NOT_PERFORMANCE_PROOF'
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--declared',required=True,type=Path);p.add_argument('--actual',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    d=json.loads(a.declared.read_text());m=json.loads(a.actual.read_text())
    declarations=d.get('indexes') if isinstance(d,dict) else d
    if not isinstance(declarations,list) or any(not isinstance(row,dict) or not isinstance(row.get('collection'),str) for row in declarations):
        p.error('declarations must be an array of index objects or an object with an indexes array')
    r=assess(declarations,m);a.output.write_text(json.dumps(r,indent=2)+'\n');print(r['status']);raise SystemExit(2 if r['missing'] else 3 if r['unknown'] else 0)
