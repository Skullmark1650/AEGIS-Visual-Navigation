"""Full-state integrity checked replay: tracker mutations persist across frames."""
import argparse,csv,json,importlib.util,time
from pathlib import Path
from collections import Counter
import cv2,numpy as np
from PIL import Image
from .optical_flow import OpticalFlowTracker,FlowConfig
from .visual_odometry import VisualOdometry
from .replay_cached import digest

def replay(directory,baseline):
 m=json.loads((directory/'manifest.json').read_text());rows=list(csv.DictReader(Path(m['report']).with_suffix('.csv').open()));cal=json.loads(Path(m['calibration']).read_text());spec=importlib.util.spec_from_file_location('laptop._baseline_real',baseline);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);states={n:(cls(cal),OpticalFlowTracker(FlowConfig()),[]) for n,cls in [('baseline',mod.VisualOdometry),('candidate',VisualOdometry)]};start=time.perf_counter()
 for i,row in enumerate(rows):
  p=directory/row['recorded_image']
  if digest(p)!=row['recorded_sha256']:raise ValueError('Image integrity')
  with Image.open(p) as im:image=im.convert('RGB')
  for name,(vo,tr,out) in states.items():
   _,flow=tr.update(image,row['session'],int(row['frame_id']),int(row['sensor_ns']),render=False);vo.validate_frame({'camera_profile_id':row['camera_profile_id'],'focus_mode':row['focus_mode'],'lens_position':float(row['lens_position'])},image.size);cv2.setRNGSeed(i);pose=vo.update_tracks(tr,flow);out.append(dict(frame_id=int(row['frame_id']),elapsed_s=float(row['elapsed_s']),**pose))
 result={'recording':str(directory.resolve()),'frames':len(rows),'csv_sha256':digest(Path(m['report']).with_suffix('.csv')),'source_hashes':{str(p):digest(p) for p in [Path('laptop/visual_odometry.py'),Path('laptop/optical_flow.py'),baseline]},'calibration_sha256':digest(Path(m['calibration'])),'wall_s':time.perf_counter()-start,'estimators':{n:{'statuses':dict(Counter(x['status'] for x in out)),'rows':out} for n,(_,_,out) in states.items()}};print(directory.name,{n:v['statuses'] for n,v in result['estimators'].items()},flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--recording',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();assert not a.output.exists();a.output.write_text(json.dumps(replay(a.recording,Path('results/backups/improvements-v7/visual_odometry.py')),indent=2))
