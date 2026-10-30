"""Experimental subpixel refinement of mutual descriptor matches; not live."""
import cv2,numpy as np
from .rotation_descriptor_candidate import descriptor_pairs as raw_pairs, VisualOdometry as DescriptorBase
from .visual_odometry import VisualOdometry as ProductionBase
from .partial_orientation import orientation_from_3d

def refined_pairs(source,current):
 pairs=raw_pairs(source,current)
 if pairs is None:return None
 a,b=pairs;a=a[:,None,:];b=b[:,None,:]
 q,v,e=cv2.calcOpticalFlowPyrLK(source,current,a,b.copy(),winSize=(21,21),maxLevel=0,flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
 if q is None:return None
 back,vb,eb=cv2.calcOpticalFlowPyrLK(current,source,q,a.copy(),winSize=(21,21),maxLevel=0,flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
 if back is None:return None
 good=(v.ravel()!=0)&(vb.ravel()!=0)&(e.ravel()<25)&(eb.ravel()<25)&(np.linalg.norm(back[:,0]-a[:,0],axis=1)<.5)&(np.linalg.norm(q[:,0]-b[:,0],axis=1)<=2)
 h,w=current.shape;good &= np.isfinite(q[:,0]).all(1)&(q[:,0,0]>=0)&(q[:,0,0]<w)&(q[:,0,1]>=0)&(q[:,0,1]<h)
 if good.sum()<90:return None
 return a[good,0],q[good,0]
class VisualOdometry(ProductionBase):
 VERSION='experimental-refined-descriptors-v15'
 def retrack_rotation(self,tr):
  model=super().retrack_rotation(tr)
  if model is not None:return model
  source=getattr(self,'anchor_gray',None);gray=getattr(tr,'previous',None);age=tr.last_info[1]-self.anchor_frame_id if self.anchor_frame_id is not None else 0
  if source is None or gray is None or source.shape!=gray.shape or not 0<age<=30:return None
  pairs=refined_pairs(source,gray)
  if pairs is None:return None
  a=cv2.undistortPoints(pairs[0][:,None,:],self.K,self.D)[:,0];b=cv2.undistortPoints(pairs[1][:,None,:],self.K,self.D)[:,0];f=float((self.K[0,0]+self.K[1,1])/2);H,mask=cv2.findHomography(a,b,cv2.RANSAC,1.5/f);model=self.rotation_model(a,b,H,mask)
  if model is None:model=orientation_from_3d(a,b,f,self.calibration['image_size'],self.fit_essential)
  if model is not None:model.update(rotation_method='experimental_refined_descriptors')
  return model
