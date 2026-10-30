"""Three-view diagnostic with fixed track split and held-out middle-view prediction."""
import json,csv,hashlib
from pathlib import Path
import cv2,numpy as np
from .visual_odometry import VisualOdometry
from .validation import angle_error

def tracks(images):
 sift=cv2.SIFT_create(nfeatures=2000);features=[sift.detectAndCompute(im,None) for im in images];matcher=cv2.BFMatcher(cv2.NORM_L2)
 def matches(i,j):
  a,b=features[i][1],features[j][1]
  if a is None or b is None:return {}
  def ratio(x,y):return {m.queryIdx:m.trainIdx for pair in matcher.knnMatch(x,y,k=2) if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance}
  ab=ratio(a,b);ba=ratio(b,a);return {k:v for k,v in ab.items() if ba.get(v)==k}
 a=matches(0,1);b=matches(0,2);c=matches(1,2);out=[]
 for k in sorted(set(a)&set(b)):
  if c.get(a[k])!=b[k]:continue
  pts=np.array([features[0][0][k].pt,features[1][0][a[k]].pt,features[2][0][b[k]].pt])
  if all(np.all(np.linalg.norm(pts-old,axis=1)>=2) for old in out):out.append(pts)
 return np.array(out,np.float64).reshape(-1,3,2)

def assess(pixels,K,D,limits):
 n=len(pixels);out={'cycle_tracks':n,'enough_tracks':n>=limits['minimum_cycle_tracks'],'hypotheses':[]}
 if n<15:return out
 train=np.arange(n)%3!=0;hold=~train;out.update(train=int(train.sum()),holdout=int(hold.sum()))
 norm=np.stack([cv2.undistortPoints(pixels[:,i,None,:],K,D)[:,0] for i in range(3)],axis=1);f=(K[0,0]+K[1,1])/2
 cv2.setRNGSeed(16);E,mask=cv2.findEssentialMat(norm[train,0],norm[train,2],np.eye(3),method=cv2.RANSAC,prob=.999,threshold=.5/f,maxIters=1000)
 if E is None or E.shape!=(3,3):return out
 R1,R2,t=cv2.decomposeEssentialMat(E)
 for ri,R in enumerate([R1,R2]):
  for sign in [1,-1]:
   tt=t.ravel()*sign;h=cv2.triangulatePoints(np.column_stack([np.eye(3),np.zeros(3)]),np.column_stack([R,tt]),norm[:,0].T,norm[:,2].T);xyz=(h[:3]/h[3]).T;positive=np.isfinite(xyz).all(1)&(xyz[:,2]>.1)&((xyz@R.T+tt)[:,2]>.1);item={'branch':[ri,sign],'endpoint_positive_fraction':float(positive.mean())};eligible=train&positive
   if eligible.sum()<12:out['hypotheses'].append(item);continue
   ok,r,tm,inliers=cv2.solvePnPRansac(xyz[eligible],pixels[eligible,1],K,D,iterationsCount=200,reprojectionError=1.,confidence=.999,flags=cv2.SOLVEPNP_EPNP)
   if not ok or inliers is None or len(inliers)<12:out['hypotheses'].append(item);continue
   pts=xyz[eligible][inliers.ravel()];obs=pixels[eligible,1][inliers.ravel()];r,tm=cv2.solvePnPRefineLM(pts,obs,K,D,r,tm);Rm=cv2.Rodrigues(r)[0];projected=cv2.projectPoints(xyz[hold],r,tm,K,D)[0][:,0];err=np.linalg.norm(projected-pixels[hold,1],axis=1);positive_mid=positive&((xyz@Rm.T+tm.ravel())[:,2]>.1);sv=np.linalg.svd(xyz[eligible]-xyz[eligible].mean(0),compute_uv=False);rays=np.column_stack([norm[:,0],np.ones(n)])@R.T;other=np.column_stack([norm[:,2],np.ones(n)]);rays/=np.linalg.norm(rays,axis=1)[:,None];other/=np.linalg.norm(other,axis=1)[:,None];par=float(np.median(np.degrees(np.arccos(np.clip((rays*other).sum(1),-1,1)))))
   item.update(middle_positive_fraction=float(positive_mid.mean()),heldout_middle_median_px=float(np.median(err)),heldout_middle_p95_px=float(np.percentile(err,95)),structure_ratio=float(sv[-1]/sv[0]),median_parallax_deg=par,end_rotation=R.tolist(),middle_rotation=Rm.tolist(),train_middle_inliers=len(inliers))
   item['preliminary_pass']=bool(out['enough_tracks'] and train.sum()>=60 and hold.sum()>=30 and positive.mean()>=.85 and positive_mid.mean()>=.85 and np.median(err)<=.5 and np.percentile(err,95)<=1 and sv[-1]/sv[0]>=.01 and par>=.5)
   if item['preliminary_pass']:
    spreads=[]
    ti=np.flatnonzero(train)
    for offset in range(3):
     subset=ti[np.arange(len(ti))%3==offset]
     cv2.setRNGSeed(160+offset)
     ee,mm=cv2.findEssentialMat(norm[subset,0],norm[subset,2],np.eye(3),method=cv2.RANSAC,prob=.999,threshold=.5/f,maxIters=1000)
     if ee is None or ee.shape!=(3,3):spreads.append(180.);continue
     count,rr,_,_,_=cv2.recoverPose(ee,norm[subset,0],norm[subset,2],np.eye(3),distanceThresh=1000.,mask=mm.copy())
     spreads.append(angle_error(rr,R) if count>=.85*len(subset) else 180.)
    item['fold_rotation_spread_deg']=max(spreads)
    item['accepted_experimental']=max(spreads)<=limits['gates']['fold_rotation_spread_deg_max']
   else:item['accepted_experimental']=False
   out['hypotheses'].append(item)
 return out

if __name__=='__main__':
 p=Path('results/experiments/rotation-v16');limits=json.loads((p/'preregistration.json').read_text());d=Path('data/validation/final-rotation-20261029-141705');m=json.loads((d/'manifest.json').read_text());by={int(x['frame_id']):x for x in csv.DictReader(Path(m['report']).with_suffix('.csv').open())};cal=json.loads(Path(m['calibration']).read_text());images=[]
 for f in limits['views']:
  path=d/by[f]['recorded_image'];assert hashlib.sha256(path.read_bytes()).hexdigest()==by[f]['recorded_sha256'];images.append(cv2.imread(str(path),0))
 points=tracks(images);result=assess(points,np.array(cal['camera_matrix']),np.array(cal['distortion']),limits);result['recording']=str(d);result['views']=limits['views'];np.savez_compressed(p/'tracks.npz',pixels=points);(p/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
