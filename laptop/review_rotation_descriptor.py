import json,csv,sys,cv2,numpy as np
from pathlib import Path
from laptop.rotation_descriptor_candidate import descriptor_pairs
from laptop.partial_orientation import orientation_from_3d
from laptop.visual_odometry import VisualOdometry
from laptop.validation import angle_error
p=Path('results/experiments/rotation-v14');j=json.loads((p/'fresh-rotation.json').read_text());d=Path(j['recording']);m=json.loads((d/'manifest.json').read_text());by={int(x['frame_id']):x for x in csv.DictReader(Path(m['report']).with_suffix('.csv').open())};cal=json.loads(Path(m['calibration']).read_text());vo=VisualOdometry(cal);gates=[]
for anchor,frame in [(554,560),(554,570),(554,574)]:
 a,b=descriptor_pairs(cv2.imread(str(d/by[anchor]['recorded_image']),0),cv2.imread(str(d/by[frame]['recorded_image']),0));x=cv2.undistortPoints(a[:,None,:],vo.K,vo.D)[:,0];y=cv2.undistortPoints(b[:,None,:],vo.K,vo.D)[:,0];trace={'source':anchor,'target':frame,'pairs':len(a)}
 def tracing(f,event,arg):
  if f.f_code is orientation_from_3d.__code__:
   if event=='line':trace['last_line']=f.f_lineno
   if event=='return':
    for key in ['null_ratio','rank_ratio','count','degrees','spread']:
     if key in f.f_locals:trace[key]=float(f.f_locals[key])
    if 'keep' in f.f_locals:trace['inlier_fraction']=float(np.mean(f.f_locals['keep']))
  return tracing
 cv2.setRNGSeed(frame);sys.settrace(tracing)
 try:model=orientation_from_3d(x,y,float((vo.K[0,0]+vo.K[1,1])/2),cal['image_size'],vo.fit_essential)
 finally:sys.settrace(None)
 trace['accepted']=model is not None;trace['gate']=Path('laptop/partial_orientation.py').read_text().splitlines()[trace['last_line']-1].strip();gates.append(trace)
(p/'gate-diagnostics.json').write_text(json.dumps(gates,indent=2));print(json.dumps(gates,indent=2));refs={x['frame_id']:x for x in json.loads(Path('results/reports/phase8-final-validation/rotation-analysis.json').read_text())['board_reference_trace']};R0=np.array(refs[32]['rotation_board_to_camera']);summary={}
for name,e in j['estimators'].items():
 valid=[x for x in e['rows'] if x['heading_epoch']==1 and x['heading_reference_frame_id']==32];err=[angle_error(np.array(x['orientation_camera_to_world']),R0@np.array(refs[x['frame_id']]['rotation_board_to_camera']).T) for x in valid if x['frame_id'] in refs];summary[name]={'original_reference_fraction':len(valid)/len(e['rows']),'rms_deg':float(np.sqrt(np.mean(np.square(err)))),'max_deg':max(err),'fallback_frames':[x['frame_id'] for x in e['rows'] if x.get('rotation_method')=='experimental_mutual_sift']}
(p/'comparison.json').write_text(json.dumps(summary,indent=2));print(summary)
