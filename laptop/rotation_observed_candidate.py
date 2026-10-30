"""Experimental recent observed-view fallback; no unobserved anchor pose."""
import cv2,numpy as np
from .visual_odometry import VisualOdometry as Base
from .partial_orientation import image_correspondences,orientation_from_3d
class VisualOdometry(Base):
 VERSION='experimental-observed-anchors-v12'
 def __init__(self,*a,**kw):
  self.observed_views=[]
  super().__init__(*a,**kw)
 def update_tracks(self,tr,flow):
  if flow['reset_reason'] in ('session_change','resolution_change','nonmonotonic_frame'):self.observed_views=[]
  out=super().update_tracks(tr,flow)
  if out['orientation_observed'] and not out['translation_observed'] and getattr(tr,'previous',None) is not None:
   if not self.observed_views or tr.last_info[1]-self.observed_views[-1]['frame']>=5:
    self.observed_views.append(dict(gray=tr.previous.copy(),points=tr.points.copy(),Rwc=self.Rwc.copy(),frame=tr.last_info[1],session=tr.last_info[0],epoch=self.heading_epoch))
    self.observed_views=self.observed_views[-3:]
  return out
 def retrack_rotation(self,tr):
  out=super().retrack_rotation(tr)
  if out is not None:return out
  for key in reversed(self.observed_views):
   if key['epoch']!=self.heading_epoch or key['session']!=tr.last_info[0] or not 0<tr.last_info[1]-key['frame']<=30 or key['gray'].shape!=tr.previous.shape:continue
   pairs=image_correspondences(key['gray'],tr.previous,key['points'])
   if pairs is None:continue
   a=cv2.undistortPoints(pairs[0],self.K,self.D)[:,0];b=cv2.undistortPoints(pairs[1],self.K,self.D)[:,0];f=float((self.K[0,0]+self.K[1,1])/2);H,mask=cv2.findHomography(a,b,cv2.RANSAC,1.5/f);model=self.rotation_model(a,b,H,mask)
   if model is None:model=orientation_from_3d(a,b,f,self.calibration['image_size'],self.fit_essential)
   if model is None:continue
   model['rotation']=(np.array(model['rotation'])@key['Rwc'].T@self.Rwc).tolist();model['rotation_method']='experimental_observed_anchor';return model
  return None
