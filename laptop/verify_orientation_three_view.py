import json,numpy as np,cv2
from pathlib import Path
from laptop.rotation_orientation_ensemble import pair_model
from laptop.validation import angle_error
p=Path('results/experiments/rotation-v18');limits=json.loads((p/'preregistration.json').read_text());K=np.array([[700.,0,320],[0,700,240],[0,0,1]]);D=np.zeros(5);out=[]
for planar in [True,False]:
 for noise in [0,.05,.2,.5]:
  for seed in range(5):
   rng=np.random.default_rng(seed+1800);xyz=np.column_stack([rng.uniform(-2,2,180),rng.uniform(-1.4,1.4,180),np.full(180,7.) if planar else rng.uniform(4,10,180)]);rot=[np.eye(3),cv2.Rodrigues(np.array([.005,.025,-.0025]))[0],cv2.Rodrigues(np.array([.01,.05,-.005]))[0]];trans=[np.zeros(3),np.array([.015,.0025,0]),np.array([.03,.005,0])];pixels=[cv2.projectPoints(xyz,cv2.Rodrigues(R)[0],t,K,D)[0][:,0]+rng.normal(0,noise,(180,2)) for R,t in zip(rot,trans)];edges=[pair_model(pixels[a],pixels[b],K,D,limits) for a,b in [(0,1),(1,2),(0,2)]];cycle=angle_error(np.array(edges[1]['rotation'])@np.array(edges[0]['rotation']),np.array(edges[2]['rotation'])) if all('rotation' in e for e in edges) else None;accepted=all(e.get('accepted',False) for e in edges) and cycle is not None and cycle<=.2;out.append({'planar':planar,'noise':noise,'seed':seed,'accepted':accepted,'cycle_deg':cycle,'end_error_deg':angle_error(np.array(edges[2]['rotation']),rot[2]) if 'rotation' in edges[2] else None})
(p/'three-view-controls.json').write_text(json.dumps(out,indent=2));print({str(pl):{'accepted':sum(x['accepted'] for x in out if x['planar']==pl),'total':20,'max_accepted_error_deg':max((x['end_error_deg'] for x in out if x['planar']==pl and x['accepted']),default=None)} for pl in [True,False]})
