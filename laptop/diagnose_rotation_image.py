import json,numpy as np,cv2,sys,inspect,csv
from pathlib import Path
from laptop.partial_orientation import image_correspondences,orientation_from_3d
from laptop.visual_odometry import VisualOdometry
from laptop.replay_cached import read_cache
p=Path('results/experiments/rotation-v10');j=json.loads((p/'fresh-rotation.json').read_text());cal=json.loads(Path('results/calibration/phase4-reviewed-camera.json').read_text());vo=VisualOdometry(cal);d=Path(j['recording']);m=json.loads((d/'manifest.json').read_text());rows=list(csv.DictReader(Path(m['report']).with_suffix('.csv').open()));by={int(x['frame_id']):x for x in rows};idx={int(x['frame_id']):i for i,x in enumerate(rows)};cache=read_cache(Path('results/cache/v9-final-rotation.npz'));out=[]
for anchor,frame in [(554,560),(554,570),(554,574),(861,880),(861,890),(861,892)]:
 a=cv2.imread(str(d/by[anchor]['recorded_image']),0);b=cv2.imread(str(d/by[frame]['recorded_image']),0);i=idx[anchor];points=cache['points'][i,:cache['count'][i]];pairs=image_correspondences(a,b,points);item={'anchor':anchor,'frame':frame,'age':frame-anchor,'eligible_age':frame-anchor<=30,'strict_image_matches':len(pairs[0]) if pairs else 0}
 if pairs:
  x=cv2.undistortPoints(pairs[0],vo.K,vo.D)[:,0];y=cv2.undistortPoints(pairs[1],vo.K,vo.D)[:,0];trace={}
  def tracer(f,event,arg):
   if f.f_code is orientation_from_3d.__code__:
    if event=='line':trace['last_line']=f.f_lineno
    if event=='return':
     for k in ['null_ratio','rank_ratio','count','degrees','spread']:
      if k in f.f_locals:trace[k]=float(f.f_locals[k])
     if 'keep' in f.f_locals:trace['inlier_fraction']=float(np.mean(f.f_locals['keep']))
   return tracer
  cv2.setRNGSeed(frame);sys.settrace(tracer)
  try:model=orientation_from_3d(x,y,float((vo.K[0,0]+vo.K[1,1])/2),cal['image_size'],vo.fit_essential)
  finally:sys.settrace(None)
  item.update(trace);item['accepted']=model is not None;item['return_gate_source']=Path('laptop/partial_orientation.py').read_text().splitlines()[trace['last_line']-1].strip()
 out.append(item)
(p/'gate-diagnostics.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
