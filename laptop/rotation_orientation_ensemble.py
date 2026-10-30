"""Experimental orientation identifiability without translation/depth output."""
import cv2,numpy as np
from .visual_odometry import VisualOdometry
from .partial_orientation import normalized_design
from .validation import angle_error

def pair_model(p,q,K,D,limits):
 a=cv2.undistortPoints(p[:,None,:],K,D)[:,0];b=cv2.undistortPoints(q[:,None,:],K,D)[:,0];f=float((K[0,0]+K[1,1])/2);n=len(a);result={'matches':n,'rejections':[]};models=[]
 if n<limits['minimum_pair_matches']:result['rejections'].append('insufficient_matches');return result
 for fold in [-1,0,1,2]:
  train=np.ones(n,bool) if fold==-1 else np.arange(n)%3!=fold;held=~train
  cv2.setRNGSeed(180+fold);E,mask=VisualOdometry.fit_essential(a[train],b[train],.5/f)
  if E is None or E.shape!=(3,3) or mask is None:result['rejections'].append('fit_failed');return result
  fraction=float(np.mean(mask!=0));x,y=a[train][mask.ravel()!=0],b[train][mask.ravel()!=0];X,Y=normalized_design(x),normalized_design(y);design=np.column_stack([Y[:,0]*X[:,0],Y[:,0]*X[:,1],Y[:,0],Y[:,1]*X[:,0],Y[:,1]*X[:,1],Y[:,1],X[:,0],X[:,1],np.ones(len(x))]);sv=np.linalg.svd(design,compute_uv=False);null=float(sv[-1]/max(sv[-2],1e-12));rank=float(sv[-2]/sv[0]);r1,r2,_=cv2.decomposeEssentialMat(E);rotations=[R for R in [r1,r2] if angle_error(R,np.eye(3))<limits['rotation_hypothesis_bound_deg']]
  if len(rotations)!=1:result['rejections'].append('ambiguous_small_rotation');return result
  R=rotations[0];model={'fold':fold,'fraction':fraction,'null_ratio':null,'rank_ratio':rank,'rotation':R.tolist()};models.append(model)
  if fraction<limits['inlier_fraction_min']:result['rejections'].append('low_inlier_support')
  if null>limits['design_null_max'] or rank<limits['design_rank_min']:result['rejections'].append('nonunique_epipolar_geometry')
  if held.any():
   ah=np.column_stack([a[held],np.ones(held.sum())]);bh=np.column_stack([b[held],np.ones(held.sum())]);ex=ah@E.T;ey=bh@E;err=np.abs(np.sum(bh*ex,axis=1))/np.sqrt(np.maximum(1e-20,np.sum(ex[:,:2]**2+ey[:,:2]**2,axis=1)))*f;model['heldout_epipolar_p95_px']=float(np.percentile(err,95))
   if np.percentile(err,95)>limits['heldout_epipolar_p95_max_px']:result['rejections'].append('heldout_error')
 result['models']=models;spread=max(angle_error(np.array(x['rotation']),np.array(models[0]['rotation'])) for x in models[1:]);result['fold_spread_deg']=spread
 if spread>limits['fold_rotation_spread_max_deg']:result['rejections'].append('rotation_instability')
 result['rejections']=sorted(set(result['rejections']));result['accepted']=not result['rejections'];result['rotation']=models[0]['rotation'];return result
