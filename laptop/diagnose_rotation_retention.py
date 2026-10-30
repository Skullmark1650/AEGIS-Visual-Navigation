"""Explain strict LK rejection counts with integrity checked source images."""
import json,csv,hashlib
from pathlib import Path
import cv2,numpy as np
from .replay_cached import read_cache
p=Path('results/experiments/rotation-v12');d=Path('data/validation/final-rotation-20261029-141705');m=json.loads((d/'manifest.json').read_text());rows=list(csv.DictReader(Path(m['report']).with_suffix('.csv').open()));by={int(x['frame_id']):x for x in rows};ix={int(x['frame_id']):i for i,x in enumerate(rows)};cache=read_cache(Path('results/cache/v9-final-rotation.npz'));out=[]
def image(f):
 path=d/by[f]['recorded_image'];assert hashlib.sha256(path.read_bytes()).hexdigest()==by[f]['recorded_sha256'];return cv2.imread(str(path),0)
for source,target in [(554,560),(554,570),(554,574),(861,880),(861,890),(861,892)]:
 a=image(source);b=image(target);i=ix[source];pts=cache['points'][i,:cache['count'][i]].reshape(-1,1,2);q,v,e=cv2.calcOpticalFlowPyrLK(a,b,pts,None,winSize=(21,21),maxLevel=4);back,vb,_=cv2.calcOpticalFlowPyrLK(b,a,q,None,winSize=(21,21),maxLevel=4);fb=np.linalg.norm(back[:,0]-pts[:,0],axis=1);h,w=b.shape;flags=(v.ravel()!=0)&(vb.ravel()!=0);bounds=(q[:,0,0]>=0)&(q[:,0,0]<w)&(q[:,0,1]>=0)&(q[:,0,1]<h);good=flags&bounds&(e.ravel()<5)&(fb<.5)
 out.append(dict(source=source,target=target,points=len(pts),status_pass=int(flags.sum()),bounds_pass=int(bounds.sum()),photo_under5=int((flags&(e.ravel()<5)).sum()),fb_under_half=int((flags&(fb<.5)).sum()),all_pass=int(good.sum()),retained_fraction=float(good.mean()),photo_error_p50_p95=np.percentile(e.ravel()[flags],[50,95]).tolist(),fb_error_p50_p95=np.percentile(fb[flags],[50,95]).tolist()))
(p/'match-diagnostics.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
