"""Diagnose spatial support and all essential-pose hypotheses; no board-based selection."""
import json,csv,hashlib
from pathlib import Path
import cv2,numpy as np
from .rotation_descriptor_candidate import descriptor_pairs
from .visual_odometry import VisualOdometry
from .validation import angle_error
p=Path('results/experiments/rotation-v15');d=Path('data/validation/final-rotation-20261029-141705');m=json.loads((d/'manifest.json').read_text());by={int(x['frame_id']):x for x in csv.DictReader(Path(m['report']).with_suffix('.csv').open())};cal=json.loads(Path(m['calibration']).read_text());vo=VisualOdometry(cal);refs={x['frame_id']:x for x in json.loads(Path('results/reports/phase8-final-validation/horizontal-redo-analysis.json').read_text())['board_reference_trace']};refs={x['frame_id']:x for x in json.loads(Path('results/reports/phase8-final-validation/rotation-analysis.json').read_text())['board_reference_trace']};out=[]
def image(f):
 path=d/by[f]['recorded_image'];assert hashlib.sha256(path.read_bytes()).hexdigest()==by[f]['recorded_sha256'];return cv2.imread(str(path),0)
for source,target in [(554,560),(554,570),(554,574)]:
 a,b=descriptor_pairs(image(source),image(target));x=cv2.undistortPoints(a[:,None,:],vo.K,vo.D)[:,0];y=cv2.undistortPoints(b[:,None,:],vo.K,vo.D)[:,0];f=(vo.K[0,0]+vo.K[1,1])/2;item={'source':source,'target':target,'pairs':len(a),'fits':{}}
 for name,fit in [('raw_five_point',lambda x,y,t:cv2.findEssentialMat(x,y,np.eye(3),method=cv2.RANSAC,prob=.999,threshold=t,maxIters=1000)),('all_inlier_refit',vo.fit_essential)]:
  cv2.setRNGSeed(target);E,mask=fit(x,y,.5/f);keep=mask.ravel()!=0;R1,R2,t=cv2.decomposeEssentialMat(E);hyp=[]
  for R in [R1,R2]:
   for sign in [1,-1]:
    tt=t.ravel()*sign;h=cv2.triangulatePoints(np.column_stack([np.eye(3),np.zeros(3)]),np.column_stack([R,tt]),x.T,y.T);z=h[:3]/h[3];positive=keep&np.isfinite(z).all(0)&(z[2]>0)&((R@z+tt[:,None])[2]>0);bounded=positive&(z[2]<1000)&((R@z+tt[:,None])[2]<1000);bins=np.zeros((3,4),int);failed=np.zeros_like(bins)
    for pt,ok,k in zip(a,bounded,keep):
     if k:(bins if ok else failed)[min(2,int(pt[1]*3/480)),min(3,int(pt[0]*4/640))]+=1
    expected=np.array(refs[target]['rotation_board_to_camera'])@np.array(refs[source]['rotation_board_to_camera']).T if target in refs and source in refs else None
    hyp.append({'positive_depth':int(positive.sum()),'bounded_depth':int(bounded.sum()),'positive_grid':bins.tolist(),'rejected_grid':failed.tolist(),'rotation_difference_vs_board_deg':angle_error(R,expected) if expected is not None else None})
  item['fits'][name]={'inliers':int(keep.sum()),'hypotheses':hyp}
 out.append(item)
(p/'spatial-hypotheses.json').write_text(json.dumps(out,indent=2));print([{ 'target':i['target'],'fits':{k:[h['bounded_depth'] for h in v['hypotheses']] for k,v in i['fits'].items()}} for i in out])
