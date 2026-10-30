"""Expose both planar PnP hypotheses instead of hiding a near tie."""
import cv2
import numpy as np


def planar_reference(objects, corners, K, D):
    objects=np.ascontiguousarray(objects,dtype=np.float64)
    corners=np.ascontiguousarray(corners,dtype=np.float64).reshape(-1,2)
    count,rotations,translations,_=cv2.solvePnPGeneric(objects,corners,K,D,flags=cv2.SOLVEPNP_IPPE)
    candidates=[]
    for r,t in zip(rotations,translations):
        R=cv2.Rodrigues(r)[0]
        if np.min((objects@R.T+t.ravel())[:,2])<=0:continue
        pixels=cv2.projectPoints(objects,r,t,K,D)[0].reshape(-1,2)
        error=float(np.sqrt(np.mean(np.sum((pixels-corners)**2,axis=1))))
        candidates.append(dict(R=R,t=t.ravel(),center=-R.T@t.ravel(),reprojection_rms_px=error))
    candidates.sort(key=lambda x:x['reprojection_rms_px'])
    result=dict(usable=False,ambiguous=False,candidate_count=len(candidates),reprojection_gap_px=None,
                candidate_center_gap_mm=None,candidate_rotation_gap_deg=None,pose=None,
                sensitivity_center_radius_mm=None,sensitivity_rotation_radius_deg=None,
                sensitivity_pixel_sigma=.15,sensitivity_unstable=False)
    if not candidates:return result
    if len(candidates)>1:
        a,b=candidates[:2]
        gap=b['reprojection_rms_px']-a['reprojection_rms_px']
        center=float(np.linalg.norm(a['center']-b['center']))
        angle=float(np.degrees(np.arccos(np.clip((np.trace(a['R']@b['R'].T)-1)/2,-1,1))))
        result.update(reprojection_gap_px=gap,candidate_center_gap_mm=center,candidate_rotation_gap_deg=angle,
                      ambiguous=gap<.15 and (center>5 or angle>.5))
    if not result['ambiguous'] and candidates[0]['reprojection_rms_px']<=1.5:
        # A numerical sensitivity probe, NOT a measured uncertainty interval.
        # A decisive best branch can still jump under tiny corner perturbations.
        rng=np.random.default_rng(731);centers=[];angles=[]
        for _ in range(16):
            perturbed=corners+rng.normal(0,.15,corners.shape)
            _,rs,ts,_=cv2.solvePnPGeneric(objects,perturbed,K,D,flags=cv2.SOLVEPNP_IPPE)
            options=[]
            for r,t in zip(rs,ts):
                R=cv2.Rodrigues(r)[0]
                if np.min((objects@R.T+t.ravel())[:,2])<=0:continue
                projected=cv2.projectPoints(objects,r,t,K,D)[0].reshape(-1,2)
                options.append((float(np.mean(np.sum((projected-perturbed)**2,axis=1))),R,t.ravel()))
            if not options:continue
            _,R,t=min(options,key=lambda item:item[0])
            centers.append(float(np.linalg.norm(-R.T@t-candidates[0]['center'])))
            angles.append(float(np.degrees(np.arccos(np.clip((np.trace(R@candidates[0]['R'].T)-1)/2,-1,1)))))
        result['sensitivity_center_radius_mm']=max(centers) if centers else None
        result['sensitivity_rotation_radius_deg']=max(angles) if angles else None
        result['sensitivity_unstable']=len(centers)!=16 or max(centers,default=float('inf'))>5 or max(angles,default=float('inf'))>.5
    result['usable']=not result['ambiguous'] and not result['sensitivity_unstable'] and candidates[0]['reprojection_rms_px']<=1.5
    # Keep the best hypothesis available for diagnostics, but callers must gate usable.
    result['pose']=candidates[0]
    return result
