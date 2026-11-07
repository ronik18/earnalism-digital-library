"""Read-only release/quality snapshot. Engineering checks never grant owner approval."""
import pathlib,json,argparse,hashlib

def assess(episode,balance,automation,review,manifest_current):
 holds=[]
 if not manifest_current:holds.append('Stale or incomplete delivery manifest')
 if episode.get('private_test'):holds.append('Private fixture cannot publish; qualify a separate real release candidate')
 if balance.get('issues'):holds.append('Open music-balance findings')
 transition=automation.get('transition_check',{})
 if not transition or transition.get('issues') or transition.get('maximum_phrase_gain_rate_db_per_second',999)>1.001:holds.append('Missing or failed slow-transition evidence')
 if not review.get('reviewer') or not all(review.get(k) is True for k in ['factual','rights','voice','audiovisual','technical','delivery']):holds.append('Final artifact-bound human review incomplete')
 next_action=('Repair and rebind the delivery manifest' if not manifest_current else 'Keep the fixture private; prepare a separate production candidate' if episode.get('private_test') else 'Resolve musical balance and listen before another release candidate' if balance.get('issues') else 'Resolve slow-transition evidence' if not transition or transition.get('issues') or transition.get('maximum_phrase_gain_rate_db_per_second',999)>1.001 else 'Collect current artifact-bound human review; keep private' if holds else 'Run existing strict release gate and Integration Lane handoff')
 return {'status':'RED_HOLD' if holds else 'READY_FOR_EXISTING_RELEASE_GATE','holds':holds,'engineering_pass_is_not_publication_approval':True,'next_action':next_action,'autopublish':False}

def inspect(folder):
 folder=pathlib.Path(folder).resolve();load=lambda n:json.loads((folder/n).read_text());manifest=load('delivery-manifest.json')
 digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 current=bool(manifest) and all((folder/n).is_file() and digest(folder/n)==h for n,h in manifest.items())
 review=load('review.json');bound=review.get('delivery_manifest_sha256')==digest(folder/'delivery-manifest.json')
 if not bound:review={**review,'reviewer':''}
 r=assess(load('episode.json'),load('music-balance.json'),load('music-automation.json'),review,current)
 episode=load('episode.json')
 try:
  from learning_acceptance import validate_release_findings,validate
  record=load('acceptance-review.json') if (folder/'acceptance-review.json').exists() else None
  r['optional_learning_research']=validate_release_findings(record,digest(folder/'delivery-manifest.json'),review,folder)
  if episode.get('requires_independent_learning_study') is True:
   if record is None:raise ValueError('Explicitly required independent learning study missing')
   if record.get('schema')!='earnalism.learning-acceptance.v2':raise ValueError('Explicit independent study needs current topic-bound v2 evidence')
   validate(record,digest(folder/'delivery-manifest.json'),plan=load('audience-plan.json') if record.get('schema')=='earnalism.learning-acceptance.v2' else None)
 except (ValueError,FileNotFoundError) as ex:
  r['holds'].append(str(ex));r['status']='RED_HOLD'
  r['next_action']='Resolve known primary findings or the explicitly requested study; keep private'
 try:
  from strict_quality import validate as validate_strict
  validate_strict(folder)
 except (ValueError,FileNotFoundError) as ex:
  r['holds'].append('Mandatory factual/graphical review: '+str(ex));r['status']='RED_HOLD'
  if r['next_action']=='Run existing strict release gate and Integration Lane handoff':r['next_action']='Complete strict factual and graphical evidence review; keep private'
 r.update({'candidate':str(folder),'delivery_manifest_sha256':digest(folder/'delivery-manifest.json'),'manifest_current':current,'human_review_bound':bound,'music_median_gap_db':load('music-balance.json').get('median_music_below_voice_db'),'local_music_findings':load('music-balance.json').get('passage_issues',[])})
 return r
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('candidate');args=parser.parse_args();print(json.dumps(inspect(args.candidate),indent=2))
