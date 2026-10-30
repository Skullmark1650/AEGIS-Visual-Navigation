"""Trace recovery archive ages and board-plane correspondence errors, diagnostic only."""
import json,csv,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
import importlib.util
spec=importlib.util.spec_from_file_location('laptop._identity_v8','results/backups/improvements-v8/visual_odometry.py');baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline);VisualOdometry=baseline.VisualOdometry
from .optical_flow import OpticalFlowTracker,FlowConfig
p=Path('results/experiments/map-diagnosis-v21');cur=json.loads(Path('results/reports/phase8-v2-current.json').read_text());d=Path(cur['recording']);m=json.loads((d/'manifest.json').read_text());rows=list(csv.DictReader(Path(m['report']).with_suffix('.csv').open()));cal=json.loads(Path(m['calibration']).read_text());refs={x['frame_id']:x for x in json.loads((Path(cur['control'])/'analysis.json').read_text())['board_reference_trace']};vo=VisualOdometry(cal);tr=OpticalFlowTracker(FlowConfig());out=[]
for i,row in enumerate(rows):
 f=int(row['frame_id']);path=d/row['recorded_image'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['recorded_sha256']
 with Image.open(path) as image:_,flow=tr.update(image.convert('RGB'),row['session'],f,int(row['sensor_ns']),render=False)
 if f in [1265,1285,1665,2515,2540]:
  item={'frame':f,'keys':[]}
  for k in vo.recovery_keyframes:
   key={'frame':k['frame'],'age':f-k['frame'],'eligible_age':0<f-k['frame']<=900,'map':k['map_id'],'count':len(k['pixels'])};a=k['pixels'].reshape(-1,1,2);b,v,e=cv2.calcOpticalFlowPyrLK(k['gray'],tr.previous,a,None,winSize=(31,31),maxLevel=4);back,vb,_=cv2.calcOpticalFlowPyrLK(tr.previous,k['gray'],b,None,winSize=(31,31),maxLevel=4);good=(v.ravel()!=0)&(vb.ravel()!=0)&(e.ravel()<25)&(np.linalg.norm(back[:,0]-a[:,0],axis=1)<1);key['lk_good']=int(good.sum())
   if k['frame'] in refs and f in refs:
    sr=refs[k['frame']];R=np.array(sr['rotation_board_to_camera']);t=np.array(sr['translation_board_to_camera_mm']);ray=np.column_stack([cv2.undistortPoints(a,vo.K,vo.D)[:,0],np.ones(len(a))]);directions=ray@R;origin=-R.T@t;lam=-origin[2]/directions[:,2];board=origin+lam[:,None]*directions;inside=good&(board[:,0]>=-20)&(board[:,0]<=180)&(board[:,1]>=-20)&(board[:,1]<=120);cr=refs[f];rr=np.array(cr['rotation_board_to_camera']);tt=np.array(cr['translation_board_to_camera_mm']);expected=cv2.projectPoints(board,cv2.Rodrigues(rr)[0],tt,vo.K,vo.D)[0][:,0];error=b[:,0]-expected
    key.update(board_pairs=int(inside.sum()),board_lk_error_px_median=float(np.median(np.linalg.norm(error[inside],axis=1))) if inside.any() else None,board_lk_error_vector_median=np.median(error[inside],axis=0).tolist() if inside.any() else None)
   item['keys'].append(key)
  out.append(item)
 cv2.setRNGSeed(i);pose=vo.update_tracks(tr,flow)
(p/'archive-and-matches.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
