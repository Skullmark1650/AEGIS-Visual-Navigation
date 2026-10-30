"""Offline controlled-run validation. Board PnP is a correlated reference, not ground truth."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time


def resources():
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ['peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile']]
        c=Counters();c.cb=ctypes.sizeof(c)
        kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):raise OSError('Cannot read process memory')
        return {'process_rss_bytes':c.rss,'process_peak_rss_bytes':c.peak_rss,'scope':'Laptop receiver process only; peak includes process initialization'}
    import resource
    import sys
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'process_peak_rss_bytes':peak if sys.platform=='darwin' else peak*1024,'scope':'Laptop receiver process lifetime peak only'}


def recovery_events(rows):
    """Tracking recovery requires non-reset retained matches, not merely newly seeded points."""
    events=[]
    for i,row in enumerate(rows):
        reason=row.get('flow_reset_reason','')
        if not reason or reason=='startup':continue
        recovered=next((r for r in rows[i+1:] if not r.get('flow_reset_reason') and int(r.get('flow_tracked') or 0)>=30),None)
        accepted=next((r for r in rows[i+1:] if r.get('vo_status') in ('accepted','map_tracking','relocalized')),None)
        events.append({'reset_frame_id':int(row['frame_id']),'reason':reason,
            'tracking_recovery_s':float(recovered['elapsed_s'])-float(row['elapsed_s']) if recovered else None,
            'next_accepted_pose_s':float(accepted['elapsed_s'])-float(row['elapsed_s']) if accepted else None,
            'note':'Next accepted pose may belong to a later segment; not continuous trajectory recovery'})
    return events


def angle_error(estimate,reference):
    import numpy as np
    return float(np.degrees(np.arccos(np.clip((np.trace(estimate@reference.T)-1)/2,-1,1))))


def analyze(directory,output,stride=15,exhaustive_board=False):
    import cv2
    import numpy as np
    from PIL import Image
    if stride<1:raise ValueError('Stride must be positive')
    directory=Path(directory).resolve();output=Path(output)
    manifest=json.loads((directory/'manifest.json').read_text())
    report=Path(manifest['report']);summary=json.loads(report.read_text())
    rows=list(csv.DictReader(report.with_suffix('.csv').open(newline='',encoding='utf-8')))
    if not rows:raise ValueError('Empty recorded experiment')
    if len({r['session'] for r in rows})!=1:raise ValueError('Analyze one producer session per controlled run')
    if output.exists() or output.with_suffix('.svg').exists():raise FileExistsError('Choose unused validation outputs')
    # Verify every raw frame, even those not selected for board estimation.
    for row in rows:
        p=(directory/row['recorded_image']).resolve()
        if p.parent!=directory or hashlib.sha256(p.read_bytes()).hexdigest()!=row['recorded_sha256']:
            raise ValueError('Recorded image integrity mismatch')
    calibration=json.loads(Path(manifest['calibration']).read_text())
    from .camera_calibration import verify_profile
    profile=verify_profile(calibration['camera_profile'])
    if any(r['camera_profile_id']!=calibration['camera_profile']['profile_id'] for r in rows):raise ValueError('Profile mismatch')
    K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
    objects=np.zeros((54,3),np.float32);objects[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*20
    by_id={int(r['frame_id']):r for r in rows}
    selected={int(r['frame_id']) for r in rows[::stride]}|{int(rows[-1]['frame_id'])}
    for row in rows:
        if row.get('vo_status') in ('accepted','rotation_only') or (row.get('vo_status')=='map_tracking' and int(row['frame_id']) in selected):
            selected.add(int(row['frame_id']))
            if row.get('vo_anchor_frame_id'):selected.add(int(row['vo_anchor_frame_id']))
    from .board_reference import planar_reference
    reference={};rejected=0;reference_diagnostics=[]
    for frame in sorted(selected):
        if frame not in by_id:continue
        row=by_id[frame]
        with Image.open(directory/row['recorded_image']) as image:
            if list(image.size)!=profile['image_size']:raise ValueError('Image dimensions changed')
            gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
        found,corners=cv2.findChessboardCornersSB(gray,(9,6),flags=cv2.CALIB_CB_NORMALIZE_IMAGE | ((cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY) if exhaustive_board else 0))
        if not found:rejected+=1;continue
        corners=corners.reshape(-1,2)
        if corners[0].sum()>corners[-1].sum():corners=corners[::-1].copy()
        hypotheses=planar_reference(objects,corners,K,D)
        reference_diagnostics.append(dict(frame_id=frame,**{k:v for k,v in hypotheses.items() if k!='pose'}))
        if not hypotheses['usable']:rejected+=1;continue
        reference[frame]=hypotheses['pose']
    comparisons=[]
    for row in rows:
        if row.get('vo_status') not in ('accepted','rotation_only','map_tracking') or not row.get('vo_anchor_frame_id'):continue
        current=reference.get(int(row['frame_id']));anchor=reference.get(int(row['vo_anchor_frame_id']))
        if current is None or anchor is None:continue
        R=current['R']@anchor['R'].T;t=current['t']-R@anchor['t']
        estimate=np.array(json.loads(row['vo_rotation']));direction=np.array(json.loads(row['vo_translation_direction'])) if row.get('vo_translation_direction') else None
        item={'frame_id':int(row['frame_id']),'anchor_frame_id':int(row['vo_anchor_frame_id']),
            'rotation_error_vs_board_deg':angle_error(estimate,R),'reference_baseline_mm':float(np.linalg.norm(t))}
        item['translation_direction_error_vs_board_deg']=float(np.degrees(np.arccos(np.clip(direction@t/np.linalg.norm(t),-1,1)))) if direction is not None and np.linalg.norm(t)>=10 else None
        comparisons.append(item)
    refs=list(reference.values());centers=np.array([r['center'] for r in refs])
    accepted=sum(r.get('vo_status')=='accepted' for r in rows)
    endpoints={}
    if int(rows[0]['frame_id']) in reference and int(rows[-1]['frame_id']) in reference:
        a=reference[int(rows[0]['frame_id'])];b=reference[int(rows[-1]['frame_id'])]
        endpoints={'board_reference_endpoint_displacement_mm':float(np.linalg.norm(b['center']-a['center'])),
            'board_reference_endpoint_rotation_deg':angle_error(b['R'],a['R'])}
    result={'kind':'controlled_validation','experiment':manifest['experiment'],'recording':str(directory),'frames':len(rows),
        'source_report':str(report),'receive_fps':summary['receive_fps'],'processing_fps':summary['processing_fps'],
        'processing_ms':summary['processing_ms'],'resources':summary.get('validation_resources'),
        'weighted_track_acceptance':sum(int(r.get('flow_tracked') or 0) for r in rows)/max(1,sum(int(r.get('flow_attempted') or 0) for r in rows)),
        'accepted_pose_count':accepted,'accepted_pose_fraction_of_received_frames':accepted/len(rows),
        'map_pose_count':sum(r.get('vo_status')=='map_tracking' for r in rows),
        'rotation_only_pose_count':sum(r.get('vo_status')=='rotation_only' for r in rows),
        'relocalization_count':sum(r.get('vo_status')=='relocalized' for r in rows),
        'heading_relocalization_count':sum(r.get('vo_status')=='heading_relocalized' for r in rows),
        'maximum_receipt_gap_s':max((float(rows[i]['elapsed_s'])-float(rows[i-1]['elapsed_s']) for i in range(1,len(rows))),default=0),
        'recovery_events':recovery_events(rows),'board_reference_samples':len(reference),'board_detection_failures':rejected,
        'board_center_spread_mm':np.ptp(centers,axis=0).tolist() if len(centers) else None,
        'board_detector_mode':'exhaustive_accuracy' if exhaustive_board else 'standard','board_reference_method':'IPPE two-hypothesis ambiguity gate; a unique branch is not independent truth',
        'board_reference_diagnostics':reference_diagnostics,
        'board_reference_trace':[dict(frame_id=frame,elapsed_s=float(by_id[frame]['elapsed_s']),rotation_board_to_camera=ref['R'].tolist(),translation_board_to_camera_mm=ref['t'].tolist(),camera_center_board_mm=ref['center'].tolist(),reprojection_rms_px=ref['reprojection_rms_px']) for frame,ref in reference.items()],
        'endpoint_checks':endpoints,'pose_comparisons':comparisons,
        'metric_vo_drift':'Unavailable in meters or across resets. Local maps share an arbitrary scale within one map; two-view fallback uses independent unit steps. Endpoint resets do not imply zero drift.',
        'reference_limits':'Fixed flat 20 mm checkerboard and same calibration assumed. PnP is a correlated image-derived reference, not independent ground truth. Ruler movements must be separately recorded. No metric VO scale/ATE/RPE claim.'}
    with output.open('x',encoding='utf-8') as file:json.dump(result,file,indent=2)
    # Standalone scientific trace of measured image-derived reference displacement.
    samples=[(float(by_id[f]['elapsed_s']),float(np.linalg.norm(r['center']-refs[0]['center']))) for f,r in reference.items()] if refs else []
    span=max(.001,float(rows[-1]['elapsed_s'])-float(rows[0]['elapsed_s']))
    limit=max(1.,max((y for x,y in samples),default=0))
    pts=' '.join(f"{60+660*(x-float(rows[0]['elapsed_s']))/span:.2f},{250-180*y/limit:.2f}" for x,y in samples)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="320"><rect width="100%" height="100%" fill="white"/><text x="25" y="25">Checkerboard-derived reference displacement (mm); not VO drift</text><path d="M60 60 V250 H730" stroke="black" fill="none"/><polyline points="{pts}" stroke="#126b8a" fill="none" stroke-width="2"/><text x="60" y="285">Elapsed time: 0 to {span:.2f} seconds</text><text x="60" y="307">Reference range: 0 to {limit:.3f} mm; shared calibration, no independent ground truth</text></svg>'
    output.with_suffix('.svg').write_text(svg,encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recording',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--stride',type=int,default=15)
    p.add_argument('--exhaustive-board',action='store_true')
    a=p.parse_args();r=analyze(a.recording,a.output,a.stride,a.exhaustive_board)
    print(json.dumps({k:r[k] for k in ['frames','board_reference_samples','accepted_pose_count','endpoint_checks']}))
