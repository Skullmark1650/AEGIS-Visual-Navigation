"""Repeatable offline regression on immutable Phase 8 JPEG recordings."""
import csv
import argparse
import importlib.util
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
import cv2
from PIL import Image
from .optical_flow import OpticalFlowTracker, FlowConfig
from .visual_odometry import VisualOdometry


def run(root, baseline=None):
    calibration=json.loads((root/'results/calibration/phase4-reviewed-camera.json').read_text())
    study=json.loads((root/'configs/phase8_study.json').read_text())
    sources=['laptop/visual_odometry.py','laptop/optical_flow.py','laptop/replay_improvements.py','configs/phase8_study.json','results/calibration/phase4-reviewed-camera.json']
    if (root/'laptop/partial_orientation.py').exists():sources.append('laptop/partial_orientation.py')
    result={'kind':'offline replay; development data, not independent ground truth',
            'estimator_version':VisualOdometry.VERSION,
            'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources},'cases':[]}
    baseline_class=None
    if baseline:
        spec=importlib.util.spec_from_file_location('laptop._replay_baseline',baseline)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        baseline_class=module.VisualOdometry
        result['paired_baseline_sha256']=hashlib.sha256(baseline.read_bytes()).hexdigest()
    for case in study['cases']:
        directory=root/case['recording']
        manifest=json.loads((directory/'manifest.json').read_text())
        rows=list(csv.DictReader(Path(manifest['report']).with_suffix('.csv').open(newline='')))
        tracker=OpticalFlowTracker(FlowConfig());vo=VisualOdometry(calibration)
        counts=Counter();accepted=[];rotations=[];timings=[];started=time.perf_counter()
        old=baseline_class(calibration) if baseline_class else None
        old_counts=Counter();segments=Counter();old_segments=Counter()
        for index,row in enumerate(rows):
            raw=(directory/row['recorded_image']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=row['recorded_sha256']:
                raise ValueError('Recording integrity failure')
            with Image.open(directory/row['recorded_image']) as source:image=source.convert('RGB')
            _,flow=tracker.update(image,row['session'],int(row['frame_id']),int(row['sensor_ns']),render=False)
            if old:
                cv2.setRNGSeed(index);old_pose=old.update_tracks(tracker,flow)
                old_counts[old_pose['status']]+=1
                if old_pose['status']=='accepted':old_segments[old_pose['segment']]+=1
            cv2.setRNGSeed(index)
            pose=vo.update_tracks(tracker,flow);counts[pose['status']]+=1
            timings.append(pose['estimate_ms'])
            if pose['status']=='accepted':
                segments[pose['segment']]+=1
                accepted.append(dict(frame_id=int(row['frame_id']),anchor_frame_id=pose['anchor_frame_id'],direction=pose['translation_direction'],spread_deg=pose['direction_spread_deg']))
            if pose['status'] in ('accepted','rotation_only'):
                rotations.append(dict(frame_id=int(row['frame_id']),anchor_frame_id=pose['anchor_frame_id'],rotation=pose['rotation'],status=pose['status'],segment=pose['segment'],orientation=pose['orientation_camera_to_world'],residual_px=pose.get('rotation_residual_px')))
        result['cases'].append(dict(case=case['case'],frames=len(rows),original_statuses=dict(Counter(r['vo_status'] for r in rows)),paired_baseline_statuses=dict(old_counts),baseline_translation_segments=dict(old_segments),translation_segments=dict(segments),statuses=dict(counts),accepted=accepted,orientation_events=rotations,mean_geometry_ms=sum(timings)/len(timings),wall_seconds=time.perf_counter()-started))
        print(case['case'],dict(counts),flush=True)
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=run(root,args.baseline)
    with args.output.open('x') as output:json.dump(result,output,indent=2)
