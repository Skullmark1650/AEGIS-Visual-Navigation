import json
from pathlib import Path
import cv2,numpy as np
import laptop.replay_cached as replay
from laptop.visual_odometry import VisualOdometry
log=[]
class Diagnostic(VisualOdometry):
 def recover_map(self,tr):
  frame=tr.last_info[1]
  if frame in (1150,1200,1300,1400):
   for k in self.recovery_keyframes:
    d={'frame':frame,'key':k['frame'],'age':frame-k['frame'],'map':k['map_id'],'points':len(k['xyz'])};a=k['pixels'].reshape(-1,1,2);b,v,e=cv2.calcOpticalFlowPyrLK(k['gray'],tr.previous,a,None,winSize=(31,31),maxLevel=4)
    if b is not None:
     back,vb,_=cv2.calcOpticalFlowPyrLK(tr.previous,k['gray'],b,None,winSize=(31,31),maxLevel=4);good=(v.ravel()!=0)&(vb.ravel()!=0)&(e.ravel()<25)&(np.linalg.norm(back[:,0]-a[:,0],axis=1)<1);d['lk_good']=int(good.sum());xyz=k['xyz'][good];pix=b[good,0].astype(float)
     sol=self.solve_map_pose(xyz,pix,k['Rwc'],k['center'],max_step=2) if len(xyz)>=60 else None;d['pnp_pass']=sol is not None
     if sol is not None:
      R,C,keep,res=sol;dist=((pix[keep,None,:]-tr.points[None,:,:])**2).sum(2);near=dist.argmin(1);order=np.argsort(dist[np.arange(len(keep)),near]);used=set()
      for idx in order:
       j=int(near[idx])
       if j not in used and dist[idx,j]<=.75**2:used.add(j)
      d.update(pnp_inliers=len(keep),associations=len(used),residual=res)
    log.append(d)
  return super().recover_map(tr)
replay.VisualOdometry=Diagnostic
r=Path('results/reports/phase8-final-validation');cfg=json.loads((r/'horizontal-redo-current.json').read_text());out=replay.compare(Path(cfg['recording']),Path('results/cache/final-horizontal-redo.npz'));Path('results/reports/v8-horizontal-diagnostic.json').write_text(json.dumps({'diagnostics':log,'replay':out},indent=2));print(json.dumps(log))
