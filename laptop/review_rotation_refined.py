import json,numpy as np,cv2
from pathlib import Path
from laptop.rotation_refined_candidate import refined_pairs
from laptop.rotation_descriptor_candidate import descriptor_pairs
from laptop.partial_orientation import orientation_from_3d
from laptop.visual_odometry import VisualOdometry
from laptop.validation import angle_error
p=Path('results/experiments/rotation-v15');j=json.loads((p/'fresh-rotation.json').read_text());refs={x['frame_id']:x for x in json.loads(Path('results/reports/phase8-final-validation/rotation-analysis.json').read_text())['board_reference_trace']};R0=np.array(refs[32]['rotation_board_to_camera']);summary={}
for n,e in j['estimators'].items():
 valid=[x for x in e['rows'] if x['heading_epoch']==1 and x['heading_reference_frame_id']==32];errors=[angle_error(np.array(x['orientation_camera_to_world']),R0@np.array(refs[x['frame_id']]['rotation_board_to_camera']).T) for x in valid if x['frame_id'] in refs];summary[n]={'original_reference_fraction':len(valid)/len(e['rows']),'rms_deg':float(np.sqrt(np.mean(np.square(errors)))),'max_deg':max(errors),'fallback_frames':[x['frame_id'] for x in e['rows'] if x.get('rotation_method')=='experimental_refined_descriptors']}
(p/'comparison.json').write_text(json.dumps(summary,indent=2));rng=np.random.default_rng(155);im=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(3,3),.6);other=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(3,3),.6);blank=np.zeros_like(im);slide=cv2.warpAffine(im,np.array([[1.,0.,10.],[0.,1.,0.]]),(640,480));cal=json.loads(Path('results/calibration/phase4-reviewed-camera.json').read_text());v=VisualOdometry(cal);controls={}
for name,target in [('blank',blank),('unrelated',other),('planar_slide',slide)]:
 pairs=refined_pairs(im,target);accepted=False
 if pairs:
  a=cv2.undistortPoints(pairs[0][:,None,:],v.K,v.D)[:,0];b=cv2.undistortPoints(pairs[1][:,None,:],v.K,v.D)[:,0];model=orientation_from_3d(a,b,float((v.K[0,0]+v.K[1,1])/2),cal['image_size'],v.fit_essential);accepted=model is not None
 controls[name]={'matches':len(pairs[0]) if pairs else 0,'orientation_essential_accepted':accepted};assert not accepted
(p/'controls.json').write_text(json.dumps(controls,indent=2));print(summary);print(controls)
