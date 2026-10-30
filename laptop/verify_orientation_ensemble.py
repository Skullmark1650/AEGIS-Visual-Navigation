import json,numpy as np,cv2
from pathlib import Path
from laptop.rotation_orientation_ensemble import pair_model
from laptop.validation import angle_error
p=Path('results/experiments/rotation-v18');limits=json.loads((p/'preregistration.json').read_text());K=np.array([[700.,0,320],[0,700,240],[0,0,1]]);D=np.zeros(5);out=[]
for planar in [True,False]:
 for noise in [0,.05,.2,.5]:
  for seed in range(10):
   rng=np.random.default_rng(seed);xyz=np.column_stack([rng.uniform(-2,2,180),rng.uniform(-1.4,1.4,180),np.full(180,7.) if planar else rng.uniform(4,10,180)]);R=cv2.Rodrigues(np.array([.01,.05,-.005]))[0];t=np.array([.03,.005,0]);a=cv2.projectPoints(xyz,np.zeros(3),np.zeros(3),K,D)[0][:,0];b=cv2.projectPoints(xyz,cv2.Rodrigues(R)[0],t,K,D)[0][:,0];a+=rng.normal(0,noise,a.shape);b+=rng.normal(0,noise,b.shape);r=pair_model(a,b,K,D,limits);out.append({'planar':planar,'noise':noise,'seed':seed,'accepted':r.get('accepted',False),'rejections':r.get('rejections'),'rotation_error_deg':angle_error(np.array(r['rotation']),R) if r.get('rotation') is not None else None})
(p/'geometry-controls.json').write_text(json.dumps(out,indent=2));print({str(planar):{'accepted':sum(x['accepted'] for x in out if x['planar']==planar),'total':40,'max_accepted_error_deg':max((x['rotation_error_deg'] for x in out if x['planar']==planar and x['accepted']),default=None)} for planar in [True,False]})
