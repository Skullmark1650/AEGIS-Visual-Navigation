"""Experimental orientation-only fallback; not installed in production."""
import cv2
from .visual_odometry import VisualOdometry as Base
from .partial_orientation import orientation_from_3d
class VisualOdometry(Base):
 VERSION='experimental-orientation-v9'
 def estimate(self,previous,current):
  out=super().estimate(previous,current)
  if self.motion_mode!='rotation_only' or out['status'] in ('accepted','rotation_only','low_motion') or len(previous)<90:return out
  a=cv2.undistortPoints(previous[:,None,:],self.K,self.D)[:,0];b=cv2.undistortPoints(current[:,None,:],self.K,self.D)[:,0]
  model=orientation_from_3d(a,b,float((self.K[0,0]+self.K[1,1])/2),self.calibration['image_size'],self.fit_essential)
  if model is None:return out
  out.update(model);out.update(status='rotation_only',translation_direction=None,rotation_method='experimental_active_essential');return out
