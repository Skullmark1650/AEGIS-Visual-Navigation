"""Correlated absolute-heading comparison; never compare across an unknown epoch."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from .board_reference import planar_reference
from .validation import angle_error


def review(replay):
    directory=Path(replay['recording']);manifest=json.loads((directory/'manifest.json').read_text())
    calibration=json.loads(Path(manifest['calibration']).read_text());K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
    with Path(manifest['report']).with_suffix('.csv').open(newline='') as source:raw={int(r['frame_id']):r for r in csv.DictReader(source)}
    poses=replay['estimators']['candidate']['rows'];selected=poses[::15]
    if selected[-1]['frame_id']!=poses[-1]['frame_id']:selected.append(poses[-1])
    objects=np.zeros((54,3));objects[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*20
    references={};diagnostics=[]
    for pose in selected:
        frame=pose['frame_id'];row=raw[frame];path=directory/row['recorded_image']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['recorded_sha256']:raise ValueError('Integrity mismatch')
        with Image.open(path) as source:
            image=cv2.cvtColor(np.asarray(source.convert('RGB')),cv2.COLOR_RGB2GRAY)
        found,corners=cv2.findChessboardCornersSB(image,(9,6),flags=cv2.CALIB_CB_NORMALIZE_IMAGE)
        if not found:diagnostics.append(dict(frame_id=frame,usable=False,reason='pattern_not_found'));continue
        corners=corners.reshape(-1,2)
        if corners[0].sum()>corners[-1].sum():corners=corners[::-1].copy()
        result=planar_reference(objects,corners,K,D)
        diagnostics.append(dict(frame_id=frame,**{k:v for k,v in result.items() if k!='pose'}))
        if result['usable']:references[frame]=result['pose']
    result=dict(limits='Same camera/calibration and planar target; not independent angular ground truth. Missing board samples leave portions of the turn unscored.',reference_diagnostics=diagnostics,comparisons=[])
    anchor=references.get(poses[0]['frame_id'])
    result['reference_samples']=len(references);result['initial_reference_usable']=anchor is not None
    if 'heading_epoch' in poses[0]:
        initial=poses[0]
        original=lambda p:p['heading_epoch']==initial['heading_epoch'] and p.get('heading_reference_frame_id')==initial.get('heading_reference_frame_id')
        result['final_heading_same_epoch']=original(poses[-1])
        result['unrestored_heading_frames']=sum(not original(p) for p in poses)
        result['heading_recoveries']=[dict(frame_id=p['frame_id'],elapsed_s=p['elapsed_s'],reference_frame_id=p.get('heading_reference_frame_id')) for p in poses if p['status']=='heading_relocalized']
    if anchor is None:return result
    epoch_valid=True;valid_frames=set();previous=None
    for pose in poses:
        if 'heading_epoch' in pose:
            if pose['heading_epoch']==poses[0]['heading_epoch'] and pose.get('heading_reference_frame_id')==poses[0].get('heading_reference_frame_id'):valid_frames.add(pose['frame_id'])
            previous=pose
            continue
        if previous is not None and pose['segment']!=previous['segment'] and pose['status'] not in ('rotation_only','accepted'):
            epoch_valid=False
        if epoch_valid:valid_frames.add(pose['frame_id'])
        previous=pose
    if 'heading_epoch' in poses[0]:epoch_valid=poses[-1]['frame_id'] in valid_frames
    result['unrestored_heading_frames']=len(poses)-len(valid_frames)
    result['heading_recoveries']=[dict(frame_id=p['frame_id'],elapsed_s=p['elapsed_s'],reference_frame_id=p.get('heading_reference_frame_id')) for p in poses if p['status']=='heading_relocalized']
    for pose in selected:
        ref=references.get(pose['frame_id'])
        if ref is None or pose['frame_id'] not in valid_frames:continue
        reference=anchor['R']@ref['R'].T
        result['comparisons'].append(dict(frame_id=pose['frame_id'],elapsed_s=pose['elapsed_s'],rotation_difference_deg=angle_error(np.array(pose['orientation_camera_to_world']),reference)))
    errors=[r['rotation_difference_deg'] for r in result['comparisons']]
    result.update(reference_samples=len(references),rms_rotation_difference_deg=float(np.sqrt(np.mean(np.square(errors)))) if errors else None,max_rotation_difference_deg=max(errors,default=None),final_heading_same_epoch=epoch_valid)
    updates=[p for p in poses if p['status']=='rotation_only']
    if updates:
        start,end=updates[0]['elapsed_s'],updates[-1]['elapsed_s']
        window=[r['rotation_difference_deg'] for r in result['comparisons'] if start<=r['elapsed_s']<=end]
        result.update(rotation_update_window_s=[start,end],window_reference_samples=len(window),window_rms_rotation_difference_deg=float(np.sqrt(np.mean(np.square(window)))) if window else None)
    if poses[-1]['frame_id'] in references and epoch_valid:
        result['final_rotation_difference_deg']=result['comparisons'][-1]['rotation_difference_deg']
        result['board_endpoint_rotation_deg']=angle_error(anchor['R'],references[poses[-1]['frame_id']]['R'])
        result['estimated_endpoint_rotation_deg']=angle_error(np.array(poses[-1]['orientation_camera_to_world']),np.eye(3))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=review(json.loads(args.replay.read_text()))
    with args.output.open('x') as output:json.dump(result,output,indent=2)
    print({k:v for k,v in result.items() if k not in ('reference_diagnostics','comparisons')})
