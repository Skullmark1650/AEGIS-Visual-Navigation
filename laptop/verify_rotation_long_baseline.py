import json,numpy as np,cv2
from pathlib import Path
from laptop.rotation_multiview_probe import assess,tracks
from laptop.validation import angle_error
p=Path('results/experiments/rotation-v17');limits=json.loads((p/'preregistration.json').read_text());rng=np.random.default_rng(160);K=np.array([[700.,0,320],[0,700,240],[0,0,1]]);D=np.zeros(5);xyz=np.column_stack([rng.uniform(-2,2,240),rng.uniform(-1.4,1.4,240),rng.uniform(5,10,240)]);Rmid=cv2.Rodrigues(np.array([.01,.03,-.005]))[0];Rend=cv2.Rodrigues(np.array([.015,.07,-.01]))[0]
def project(points,R,C):return cv2.projectPoints(points,cv2.Rodrigues(R)[0],-R@C,K,D)[0][:,0]
def run(name,points,centers,noise=.02):
 pixels=np.stack([project(points,R,C) for R,C in zip([np.eye(3),Rmid,Rend],centers)],axis=1);pixels+=rng.normal(0,noise,pixels.shape);r=assess(pixels,K,D,limits);accepted=[x for x in r['hypotheses'] if x.get('accepted_experimental')];r['control']=name
 if accepted:r['rotation_error_deg']=angle_error(np.array(accepted[0]['end_rotation']),Rend)
 return r
out=[run('known_nonplanar',xyz,[np.zeros(3),np.array([.2,0,0]),np.array([.5,0,0])]),run('single_plane',np.column_stack([xyz[:,:2],np.full(240,7.)]),[np.zeros(3),np.array([.2,0,0]),np.array([.5,0,0])]),run('pure_rotation',xyz,[np.zeros(3)]*3)]
blank=np.zeros((480,640),np.uint8);out.append({'control':'blank_images','cycle_tracks':len(tracks([blank]*3))})
(p/'controls.json').write_text(json.dumps(out,indent=2));print([(r['control'],sum(bool(h.get('accepted_experimental')) for h in r.get('hypotheses',[])),r.get('rotation_error_deg'),r['cycle_tracks']) for r in out])
assert any(h.get('accepted_experimental') for h in out[0]['hypotheses']),'Positive control failed'
assert all(not h.get('accepted_experimental') for r in out[1:3] for h in r['hypotheses']),'Negative accepted'
