"""Correlated board-reference comparison for a local map, with one scale alignment."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from .board_reference import planar_reference
from .validation import angle_error


def review(replay):
    directory=Path(replay['recording']);manifest=json.loads((directory/'manifest.json').read_text())
    calibration=json.loads(Path(manifest['calibration']).read_text());K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
    with Path(manifest['report']).with_suffix('.csv').open(newline='') as source:rows={int(r['frame_id']):r for r in csv.DictReader(source)}
    poses=replay['estimators']['candidate']['rows']
    initial=next((p for p in poses if p['status']=='accepted' and p['scale_mode']=='local_map'),None)
    if initial is None:return dict(status='no_local_map',comparisons=[],limits='No mapped trajectory available to compare.')
    same=[p for p in poses if (p.get('map_id')==initial['map_id'] if initial.get('map_id') is not None else p['segment']==initial['segment']) and p['status'] in ('accepted','map_tracking','relocalized')]
    selected=same[::15]
    if selected[-1]['frame_id']!=same[-1]['frame_id']:selected.append(same[-1])
    reference_id=initial['map_reference_frame_id']
    objects=np.zeros((54,3));objects[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*20
    references={};diagnostics=[]
    for frame in sorted({reference_id,initial['frame_id']}|{p['frame_id'] for p in selected}):
        row=rows[frame];path=directory/row['recorded_image']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['recorded_sha256']:raise ValueError('Raw integrity mismatch')
        gray=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
        found,corners=cv2.findChessboardCornersSB(gray,(9,6),flags=cv2.CALIB_CB_NORMALIZE_IMAGE)
        if not found:diagnostics.append(dict(frame_id=frame,usable=False));continue
        corners=corners.reshape(-1,2)
        if corners[0].sum()>corners[-1].sum():corners=corners[::-1].copy()
        result=planar_reference(objects,corners,K,D)
        diagnostics.append(dict(frame_id=frame,**{k:v for k,v in result.items() if k!='pose'}))
        if result['usable']:references[frame]=result['pose']
    result=dict(limits='Same camera/calibration/corresponding scene; one initial board-derived scale alignment, not independent metric VO validation.',reference_diagnostics=diagnostics,comparisons=[])
    anchor=references.get(reference_id);start=references.get(initial['frame_id'])
    if anchor is None or start is None:return result
    # The first map is aligned to its anchor camera axes. Do not apply to a
    # later map whose orientation already includes arbitrary earlier segments.
    previous=next(p for p in poses if p['frame_id']==reference_id)
    axis=np.array(previous['orientation_camera_to_world'])
    reference_start=axis@anchor['R']@(start['center']-anchor['center'])
    scale=float(np.linalg.norm(reference_start)/np.linalg.norm(initial['center_arbitrary']))
    result['initial_scale_mm_per_map_unit']=scale
    for pose in selected:
        ref=references.get(pose['frame_id'])
        if ref is None:continue
        expected=axis@anchor['R']@(ref['center']-anchor['center'])
        estimated=np.array(pose['center_arbitrary'])*scale
        Rexpected=axis@anchor['R']@ref['R'].T
        result['comparisons'].append(dict(frame_id=pose['frame_id'],elapsed_s=pose['elapsed_s'],reference_center_mm=expected.tolist(),scaled_map_center_mm=estimated.tolist(),center_difference_mm=float(np.linalg.norm(expected-estimated)),rotation_difference_deg=angle_error(np.array(pose['orientation_camera_to_world']),Rexpected)))
    differences=[x['center_difference_mm'] for x in result['comparisons']]
    result.update(map_samples=len(same),map_segment=initial['segment'],rms_center_difference_mm=float(np.sqrt(np.mean(np.square(differences)))) if differences else None,max_center_difference_mm=max(differences,default=None))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    result=review(json.loads(args.replay.read_text()))
    with args.output.open('x') as output:json.dump(result,output,indent=2)
    print({k:v for k,v in result.items() if k not in ('reference_diagnostics','comparisons')})
