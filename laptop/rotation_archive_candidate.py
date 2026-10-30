"""Experimental denser trusted heading views; geometry unchanged."""
import cv2,numpy as np
from .visual_odometry import VisualOdometry as Base
class VisualOdometry(Base):
 VERSION='experimental-heading-archive-v11'
 def remember_heading(self,tracker):
  gray=getattr(tracker,'previous',None)
  if gray is None or len(tracker.points)<90:return
  if self.heading_keyframes:
   if self.heading_epoch!=self.heading_keyframes[0]['epoch']:return
   last=self.heading_keyframes[-1];angle=np.degrees(np.linalg.norm(cv2.Rodrigues(last['Rwc'].T@self.Rwc)[0]))
   if tracker.last_info[1]-last['frame']<30 or angle<1:return
  key=dict(gray=gray.copy(),points=tracker.points.copy(),Rwc=self.Rwc.copy(),frame=tracker.last_info[1],session=tracker.last_info[0],epoch=self.heading_epoch,root=self.heading_root)
  self.heading_keyframes.append(key)
  if len(self.heading_keyframes)>3:self.heading_keyframes=[self.heading_keyframes[0]]+self.heading_keyframes[-2:]
