"""Experimental bounded global brightness compensation, strict geometry unchanged."""
import cv2,numpy as np
from .visual_odometry import VisualOdometry as Base
from .partial_orientation import image_correspondences,orientation_from_3d
class VisualOdometry(Base):
 VERSION='experimental-brightness-v13'
 def retrack_rotation(self,tr):
  out=super().retrack_rotation(tr)
  if out is not None:return out
  source=getattr(self,'anchor_gray',None);gray=getattr(tr,'previous',None);age=tr.last_info[1]-self.anchor_frame_id if self.anchor_frame_id is not None else 0
  if source is None or gray is None or source.shape!=gray.shape or not 0<age<=30 or len(self.anchor)<90:return None
  # One global additive offset only, bounded before matching. No spatial warp,
  # per-point brightness fitting, threshold relaxation or translation output.
  offset=float(np.median(source))-float(np.median(gray))
  if not .5<=abs(offset)<=10:return None
  adjusted=np.clip(gray.astype(np.float32)+offset,0,255).astype(np.uint8)
  pairs=image_correspondences(source,adjusted,np.array(list(self.anchor.values()),np.float32))
  if pairs is None:return None
  a=cv2.undistortPoints(pairs[0],self.K,self.D)[:,0];b=cv2.undistortPoints(pairs[1],self.K,self.D)[:,0];f=float((self.K[0,0]+self.K[1,1])/2);H,mask=cv2.findHomography(a,b,cv2.RANSAC,1.5/f);model=self.rotation_model(a,b,H,mask)
  if model is None:model=orientation_from_3d(a,b,f,self.calibration['image_size'],self.fit_essential)
  if model is not None:model.update(rotation_method='experimental_brightness',brightness_offset=offset)
  return model
