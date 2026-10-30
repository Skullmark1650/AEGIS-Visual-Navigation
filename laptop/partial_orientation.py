"""Orientation-only recovery from identifiable, nonplanar epipolar geometry."""
import cv2
import numpy as np


def normalized_design(points):
    centered=points-np.mean(points,axis=0)
    scale=float(np.sqrt(np.mean(np.sum(centered**2,axis=1))))
    return centered*np.sqrt(2)/max(scale,1e-12)


def orientation_from_3d(a,b,focal,image_size,fit):
    if len(a)<90:return None
    # Precisely homographic observations do not identify general 3D epipolar
    # geometry. A valid pure rotation is handled separately, not forced into E.
    H,hm=cv2.findHomography(a,b,cv2.RANSAC,.3/focal)
    if H is not None and hm is not None and np.mean(hm!=0)>.95:
        rays=np.column_stack([a,np.ones(len(a))])@H.T
        error=np.linalg.norm((rays[:,:2]/rays[:,2,None]-b)*focal,axis=1)
        if np.median(error)<.05:return None
    E,mask=fit(a,b,.5/focal)
    if E is None or E.shape!=(3,3) or mask is None:return None
    keep=mask.ravel()!=0
    if keep.sum()<90 or keep.mean()<.85:return None
    x,y=a[keep],b[keep]
    X,Y=normalized_design(x),normalized_design(y)
    design=np.column_stack([Y[:,0]*X[:,0],Y[:,0]*X[:,1],Y[:,0],Y[:,1]*X[:,0],Y[:,1]*X[:,1],Y[:,1],X[:,0],X[:,1],np.ones(len(x))])
    singular=np.linalg.svd(design,compute_uv=False)
    null_ratio=float(singular[-1]/max(singular[-2],1e-12))
    rank_ratio=float(singular[-2]/singular[0])
    # A single homography has multiple epipolar null directions. It must not
    # become an apparently unique rotation merely because a solver chose one.
    if null_ratio>.5 or rank_ratio<.0004:return None
    width,height=image_size
    if cv2.contourArea(cv2.convexHull((x*focal).astype(np.float32)))/(width*height)<.1:return None
    count,R,t,posemask,_=cv2.recoverPose(E,a,b,np.eye(3),distanceThresh=1000.,mask=mask.copy())
    if count<60 or count/len(a)<.85:return None
    degrees=float(np.degrees(np.linalg.norm(cv2.Rodrigues(R)[0])))
    if not .1<degrees<20:return None
    spread=0.
    for offset in range(3):
        # Define validation folds before full-fit inlier selection, so their
        # membership cannot depend on which observations the full model liked.
        aa,bb=a[offset::3],b[offset::3]
        ee,mm=fit(aa,bb,.5/focal)
        if ee is None or ee.shape!=(3,3) or mm is None:return None
        n,rr,_,_,_=cv2.recoverPose(ee,aa,bb,np.eye(3),distanceThresh=1000.,mask=mm.copy())
        if n<20 or n/len(aa)<.8:return None
        spread=max(spread,float(np.degrees(np.linalg.norm(cv2.Rodrigues(rr@R.T)[0]))))
    if spread>.15:return None
    ah=np.column_stack([a,np.ones(len(a))]);bh=np.column_stack([b,np.ones(len(b))])
    ex=ah@E.T;ey=bh@E
    error=np.abs(np.sum(bh*ex,axis=1))/np.sqrt(np.maximum(1e-20,np.sum(ex[:,:2]**2+ey[:,:2]**2,axis=1)))*focal
    return dict(rotation=R.tolist(),translation_direction=None,inliers=int(count),inlier_ratio=float(count/len(a)),
                rotation_method='essential_orientation',rotation_subset_spread_deg=spread,essential_null_ratio=null_ratio,
                essential_rank_ratio=rank_ratio,rotation_epipolar_px=float(np.median(error[posemask.ravel()!=0])),homography_ratio=0.)


def image_correspondences(source,current,points):
    points=np.asarray(points,np.float32).reshape(-1,1,2)
    b,valid,error=cv2.calcOpticalFlowPyrLK(source,current,points,None,winSize=(21,21),maxLevel=4)
    if b is None:return None
    back,back_valid,_=cv2.calcOpticalFlowPyrLK(current,source,b,None,winSize=(21,21),maxLevel=4)
    if back is None:return None
    good=(valid.ravel()!=0)&(back_valid.ravel()!=0)&(error.ravel()<5)&(np.linalg.norm(back[:,0]-points[:,0],axis=1)<.5)
    h,w=current.shape
    good &= (b[:,0,0]>=0)&(b[:,0,0]<w)&(b[:,0,1]>=0)&(b[:,0,1]<h)
    if good.sum()<90 or good.mean()<.7:return None
    return points[good],b[good]
