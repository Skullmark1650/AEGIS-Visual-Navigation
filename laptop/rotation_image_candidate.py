"""Development-only strict image correspondence orientation fallback."""
import cv2,numpy as np
from .visual_odometry import VisualOdometry as Base
from .partial_orientation import image_correspondences,orientation_from_3d
class VisualOdometry(Base):
 VERSION='experimental-image-orientation-v10'
 def retrack_rotation(self,tracker):
  model=super().retrack_rotation(tracker)
  if model is not None:return model
  gray=getattr(tracker,'previous',None);source=getattr(self,'anchor_gray',None)
  age=tracker.last_info[1]-self.anchor_frame_id if self.anchor_frame_id is not None else 0
  if gray is None or source is None or source.shape!=gray.shape or not 0<age<=30 or len(self.anchor)<90:return None
  pairs=image_correspondences(source,gray,np.array(list(self.anchor.values()),np.float32))
  if pairs is None:return None
  a=cv2.undistortPoints(pairs[0],self.K,self.D)[:,0];b=cv2.undistortPoints(pairs[1],self.K,self.D)[:,0]
  model=orientation_from_3d(a,b,float((self.K[0,0]+self.K[1,1])/2),self.calibration['image_size'],self.fit_essential)
  if model is not None:model['rotation_method']='experimental_image_essential'
  return model
