"""Audit all paired regressions, including false-map and negative controls."""
import json
from pathlib import Path
p=Path('results/experiments/retained-landmarks-v22');idx=json.loads((p/'regression-index.json').read_text());assert len(idx)==16,'Regressions incomplete';out=[]
for entry in idx:
 j=json.loads(Path(entry['report']).read_text());item={'recording':Path(j['recording']).name,'frames':j['frames'],'estimators':{}}
 for name,e in j['estimators'].items():
  rows=e['rows'];root=rows[0]['heading_reference_frame_id'];epoch=rows[0]['heading_epoch'];item['estimators'][name]={'statuses':e['statuses'],'initializations':[(x['frame_id'],x['map_id']) for x in rows if x['status']=='accepted'],'recoveries':[(x['frame_id'],x['elapsed_s'],x['map_id']) for x in rows if x['status']=='relocalized'],'original_heading_fraction':sum(x['heading_epoch']==epoch and x['heading_reference_frame_id']==root for x in rows)/len(rows),'position_observations':sum(x['translation_observed'] for x in rows),'rotation_observations':sum(x['status']=='rotation_only' for x in rows)}
 name=item['recording']
 if any(name.startswith(n) for n in ['stationary-','low-light-','low-texture-','feature-loss-','network-interruption-']):assert item['estimators']['candidate']['position_observations']==0 and item['estimators']['candidate']['rotation_observations']==0,name
 if name.startswith('prototype-v2-'):assert not any(x['status']=='relocalized' and x['map_id']==1 for x in j['estimators']['candidate']['rows']),'False original map returned'
 out.append(item)
result={'earlier_recordings':len(idx),'unique_frames_including_primary':sum(x['frames'] for x in idx)+3722,'cases':out,'status':'All scripted control/identity assertions passed; compare numeric status/pose changes case-by-case, not an independent accuracy claim.'};(p/'regression-summary.json').write_text(json.dumps(result,indent=2));print('frames',result['unique_frames_including_primary']);print([(x['recording'],x['estimators']['baseline']['statuses'].get('map_tracking',0),x['estimators']['candidate']['statuses'].get('map_tracking',0),x['estimators']['candidate']['recoveries']) for x in out])
