"""Compare replay events only when both planar reference poses are unambiguous."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from .board_reference import planar_reference
from .validation import angle_error


def review(root, replay):
    study=json.loads((root/'configs/phase8_study.json').read_text())
    recordings={c['case']:root/c['recording'] for c in study['cases']}
    K,D=None,None
    objects=np.zeros((54,3));objects[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*20
    result={'limits':'Shared-calibration board reference; ambiguity and pixel-perturbation sensitivity rejection do not establish independent truth. No metric drift claim.',
            'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['laptop/board_reference.py','laptop/review_replay_reference.py']},'cases':[]}
    for case in replay['cases']:
        directory=recordings[case['case']]
        manifest=json.loads((directory/'manifest.json').read_text())
        calibration=json.loads(Path(manifest['calibration']).read_text())
        K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
        with Path(manifest['report']).with_suffix('.csv').open(newline='') as source:
            rows={int(r['frame_id']):r for r in csv.DictReader(source)}
        events=case['orientation_events']
        selected={e[k] for e in events for k in ('frame_id','anchor_frame_id')}
        refs={};diagnostics=[]
        for frame in sorted(selected):
            row=rows[frame];raw=(directory/row['recorded_image']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=row['recorded_sha256']:raise ValueError('Integrity mismatch')
            image=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_GRAYSCALE)
            found,corners=cv2.findChessboardCornersSB(image,(9,6),flags=cv2.CALIB_CB_NORMALIZE_IMAGE)
            if not found:
                diagnostics.append(dict(frame_id=frame,usable=False,reason='pattern_not_found'));continue
            corners=corners.reshape(-1,2)
            if corners[0].sum()>corners[-1].sum():corners=corners[::-1].copy()
            hypotheses=planar_reference(objects,corners,K,D)
            diagnostics.append(dict(frame_id=frame,**{k:v for k,v in hypotheses.items() if k!='pose'}))
            if hypotheses['usable']:refs[frame]=hypotheses['pose']
        comparisons=[]
        directions={e['frame_id']:e['direction'] for e in case['accepted']}
        for event in events:
            a=refs.get(event['anchor_frame_id']);b=refs.get(event['frame_id'])
            if a is None or b is None:continue
            R=b['R']@a['R'].T;t=b['t']-R@a['t']
            item=dict(frame_id=event['frame_id'],status=event['status'],rotation_error_vs_board_deg=angle_error(np.array(event['rotation']),R))
            direction=directions.get(event['frame_id'])
            item['reference_baseline_mm']=float(np.linalg.norm(t))
            item['direction_error_vs_board_deg']=float(np.degrees(np.arccos(np.clip(np.array(direction)@t/np.linalg.norm(t),-1,1)))) if direction is not None and np.linalg.norm(t)>=10 else None
            comparisons.append(item)
        result['cases'].append(dict(case=case['case'],events=len(events),reference_diagnostics=diagnostics,comparisons=comparisons))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=review(Path(__file__).resolve().parents[1],json.loads(args.replay.read_text()))
    with args.output.open('x') as output:json.dump(result,output,indent=2)
    print([(c['case'],c['events'],len(c['comparisons'])) for c in result['cases']])
