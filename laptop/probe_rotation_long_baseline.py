"""One predeclared longer-baseline experiment, unchanged v16 assessor."""
import json,csv,hashlib
from pathlib import Path
import cv2,numpy as np
from .rotation_multiview_probe import tracks,assess
from .validation import angle_error
p=Path('results/experiments/rotation-v17');limits=json.loads((p/'preregistration.json').read_text());assert not (p/'result.json').exists();assert hashlib.sha256(Path('laptop/rotation_multiview_probe.py').read_bytes()).hexdigest()==limits['assessor_sha256'];d=Path('data/validation/final-rotation-20261029-141705');m=json.loads((d/'manifest.json').read_text());by={int(x['frame_id']):x for x in csv.DictReader(Path(m['report']).with_suffix('.csv').open())};cal=json.loads(Path(m['calibration']).read_text());images=[];integrity={}
for f in limits['views']:
 path=d/by[f]['recorded_image'];h=hashlib.sha256(path.read_bytes()).hexdigest();assert h==by[f]['recorded_sha256'];integrity[f]=h;images.append(cv2.imread(str(path),0))
points=tracks(images);result=assess(points,np.array(cal['camera_matrix']),np.array(cal['distortion']),limits);result.update(recording=str(d),views=limits['views'],source_hashes=integrity,elapsed_s=[float(by[f]['elapsed_s']) for f in limits['views']],span_s=float(by[620]['elapsed_s'])-float(by[542]['elapsed_s']));np.savez_compressed(p/'tracks.npz',pixels=points);(p/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
