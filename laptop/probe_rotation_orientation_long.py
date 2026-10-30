import json,csv,hashlib
from pathlib import Path
import cv2,numpy as np
from .rotation_descriptor_candidate import descriptor_pairs
from .rotation_orientation_ensemble import pair_model
from .validation import angle_error
p=Path('results/experiments/rotation-v18');limits=json.loads((p/'long-preregistration.json').read_text());d=Path('data/validation/final-rotation-20261029-141705');m=json.loads((d/'manifest.json').read_text());by={int(x['frame_id']):x for x in csv.DictReader(Path(m['report']).with_suffix('.csv').open())};cal=json.loads(Path(m['calibration']).read_text());images={}
for f in limits['views']:
 path=d/by[f]['recorded_image'];assert hashlib.sha256(path.read_bytes()).hexdigest()==by[f]['recorded_sha256'];images[f]=cv2.imread(str(path),0)
out={}
for a,b in [(542,574),(574,620),(542,620)]:
 pairs=descriptor_pairs(images[a],images[b]);out[f'{a}-{b}']=pair_model(*pairs,np.array(cal['camera_matrix']),np.array(cal['distortion']),limits) if pairs else {'accepted':False,'rejections':['insufficient_matches']}
if all('rotation' in x for x in out.values()):cycle=angle_error(np.array(out['574-620']['rotation'])@np.array(out['542-574']['rotation']),np.array(out['542-620']['rotation']))
else:cycle=None
result={'edges':out,'cycle_deg_diagnostic':cycle,'accepted':all(x.get('accepted',False) for x in out.values()) and cycle is not None and cycle<=limits['cycle_rotation_max_deg']};assert not (p/'long-result.json').exists();(p/'long-result.json').write_text(json.dumps(result,indent=2));print(json.dumps({'accepted':result['accepted'],'cycle_deg':cycle,'edges':{k:{f:v.get(f) for f in ['matches','accepted','rejections','fold_spread_deg']} for k,v in out.items()}},indent=2))
