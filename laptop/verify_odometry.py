"""Reproducible synthetic 3D motion checks using the measured camera model."""
import argparse
import json
import time
from pathlib import Path
import cv2
import numpy as np
from .visual_odometry import VisualOdometry


def scenario(calibration, seed=1, rotation=(.015,-.025,.01), translation=(-.3,.03,.08), noise=.15, outliers=.15, planar=False):
    rng=np.random.default_rng(seed)
    xyz=np.column_stack([rng.uniform(-2,2,300),rng.uniform(-1.4,1.4,300),rng.uniform(4,10,300)])
    if planar:xyz[:,2]=6
    r=np.array(rotation,float);t=np.array(translation,float);R=cv2.Rodrigues(r)[0]
    K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
    a=cv2.projectPoints(xyz,np.zeros(3),np.zeros(3),K,D)[0].reshape(-1,2)
    b=cv2.projectPoints(xyz,r,t,K,D)[0].reshape(-1,2)
    valid=((a>8)&(a<[632,472])&(b>8)&(b<[632,472])).all(axis=1)
    a,b=a[valid],b[valid]
    a+=rng.normal(0,noise,a.shape);b+=rng.normal(0,noise,b.shape)
    n=int(len(b)*outliers)
    if n:b[:n]=rng.uniform([8,8],[632,472],(n,2))
    return a,b,R,t


def run(calibration):
    records=[]
    for seed in range(10):
        vo=VisualOdometry(calibration);a,b,R,t=scenario(calibration,seed)
        cv2.setRNGSeed(seed)
        out=vo.update(a,b)
        if out['status']=='accepted':
            estimated=np.array(out['rotation']);direction=np.array(out['translation_direction'])
            out['rotation_error_deg']=float(np.degrees(np.arccos(np.clip((np.trace(estimated@R.T)-1)/2,-1,1))))
            out['direction_error_deg']=float(np.degrees(np.arccos(np.clip(direction@t/np.linalg.norm(t),-1,1))))
        out['seed']=seed;records.append(out)
    negatives={}
    for name,kw in [('stationary',dict(rotation=(0,0,0),translation=(0,0,0),outliers=0)),('pure_rotation',dict(translation=(0,0,0),outliers=0)),('planar',dict(planar=True,outliers=0)),('outliers_80_percent',dict(outliers=.8))]:
        a,b,_,_=scenario(calibration,**kw)
        negatives[name]=VisualOdometry(calibration).update(a,b)
    a,b,_,_=scenario(calibration)
    vo=VisualOdometry(calibration);vo.update(a,b);reset=vo.update(a,b,'frame_gap')
    return dict(source_kind='synthetic_3d_projections_not_real_motion_ground_truth',noise_sigma_px=.15,outlier_fraction=.15,records=records,negative_cases=negatives,gap_reset=reset)

def rendered_sequence(calibration):
    from PIL import Image
    from .optical_flow import OpticalFlowTracker,FlowConfig
    rng=np.random.default_rng(38)
    K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
    xyz=np.column_stack([rng.uniform(-2,2,220),rng.uniform(-1.3,1.3,220),rng.uniform(4,10,220)])
    patches=[rng.integers(50,255,(9,9),dtype=np.uint8) for _ in xyz]
    tracker=OpticalFlowTracker(FlowConfig());vo=VisualOdometry(calibration);rows=[];anchor_frame=0
    for frame in range(36):
        r=np.array([0.,-.002*frame,0.]);t=np.array([-.035*frame,0.,0.])
        pts=cv2.projectPoints(xyz,r,t,K,D)[0].reshape(-1,2)
        canvas=np.full((480,640),15,np.uint8)
        for (x,y),patch in zip(pts,patches):
            x,y=round(x),round(y)
            if 6<x<634 and 6<y<474:canvas[y-4:y+5,x-4:x+5]=patch
        image=Image.fromarray(np.repeat(canvas[:,:,None],3,axis=2))
        _,flow=tracker.update(image,'synthetic-render',frame,1_000_000_000+frame*66_666_667,render=False)
        cv2.setRNGSeed(frame)
        pose=vo.update_tracks(tracker,flow)
        if pose['status']=='accepted':
            anchor_frame=pose['anchor_frame_id']
            Ra=cv2.Rodrigues(np.array([0.,-.002*anchor_frame,0.]))[0]
            Rc=cv2.Rodrigues(r)[0];Rt=Rc@Ra.T
            ta=np.array([-.035*anchor_frame,0.,0.]);tt=t-Rt@ta
            Re=np.array(pose['rotation']);te=np.array(pose['translation_direction'])
            pose['rotation_error_deg']=float(np.degrees(np.arccos(np.clip((np.trace(Re@Rt.T)-1)/2,-1,1))))
            pose['direction_error_deg']=float(np.degrees(np.arccos(np.clip(te@tt/np.linalg.norm(tt),-1,1))))
        rows.append(dict(frame=frame,tracks=flow['tracked'],pose=pose))
    return dict(source_kind='synthetic_rendered_images',note='LK plus calibrated geometry on integer-rendered textured 3D points; not real camera ground truth',frames=rows)


def rotation_checks(calibration):
    records=[]
    for rotation in [(0.,.06,0.),(0.,-.06,0.),(.06,0.,0.),(0.,0.,.1)]:
        for seed in range(5):
            a,b,R,_=scenario(calibration,seed=seed,rotation=rotation,translation=(0,0,0),outliers=0)
            cv2.setRNGSeed(seed);vo=VisualOdometry(calibration);out=vo.update(a,b)
            error=None
            if out['status']=='rotation_only':
                error=float(np.degrees(np.linalg.norm(cv2.Rodrigues(np.array(out['rotation'])@R.T)[0])))
            records.append(dict(rotation_radians=rotation,seed=seed,status=out['status'],rotation_error_deg=error,
                                translation_observed=out['translation_observed'],center_arbitrary=out['center_arbitrary']))
    return dict(kind='synthetic known pure rotations; no independent real-world accuracy',records=records)


def rotation_sequence(calibration):
    from types import SimpleNamespace
    rng=np.random.default_rng(82)
    xyz=np.column_stack([rng.uniform(-.9,.9,300),rng.uniform(-.8,.8,300),rng.uniform(5,8,300)])
    K=np.array(calibration['camera_matrix']);D=np.array(calibration['distortion'])
    projected=[cv2.projectPoints(xyz,np.array([0.,.003*min(f,120-f),0.]),np.zeros(3),K,D)[0].reshape(-1,2) for f in range(121)]
    valid=np.logical_and.reduce([((p>[8,8])&(p<[632,472])).all(axis=1) for p in projected])
    ids=np.arange(valid.sum());vo=VisualOdometry(calibration);records=[]
    for frame,points in enumerate(projected):
        pixels=points[valid]+rng.normal(0,.03,(len(ids),2))
        tracker=SimpleNamespace(ids=ids,points=pixels,last_ids=ids,last_current=pixels,last_info=('synthetic-turn',frame,frame))
        cv2.setRNGSeed(frame);pose=vo.update_tracks(tracker,{'reset_reason':'startup' if frame==0 else ''})
        R=cv2.Rodrigues(np.array([0.,.003*min(frame,120-frame),0.]))[0]
        error=float(np.degrees(np.linalg.norm(cv2.Rodrigues(np.array(pose['orientation_camera_to_world'])@R)[0])))
        records.append(dict(frame=frame,status=pose['status'],segment=pose['segment'],orientation_error_deg=error))
    return dict(kind='synthetic projected continuous turn and return; no hardware ground truth',records=records)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    c=json.loads(args.calibration.read_text());r=run(c);r['rendered_sequence']=rendered_sequence(c);r['rotation_checks']=rotation_checks(c);r['rotation_sequence']=rotation_sequence(c)
    with args.output.open('x') as f:json.dump(r,f,indent=2)
    good=[x for x in r['records'] if x['status']=='accepted']
    print(json.dumps(dict(accepted=len(good),trials=10,max_rotation_error_deg=max((x['rotation_error_deg'] for x in good),default=None),max_direction_error_deg=max((x['direction_error_deg'] for x in good),default=None),negative_cases={k:v['status'] for k,v in r['negative_cases'].items()}),indent=2))
