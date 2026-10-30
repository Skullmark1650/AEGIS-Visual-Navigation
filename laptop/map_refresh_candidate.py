"""Candidate: refresh latest successfully observed stationary map view, age cap unchanged."""
from .visual_odometry import VisualOdometry as Base
class VisualOdometry(Base):
 VERSION='experimental-map-refresh-v20'
 def remember_map(self,tracker,xyz,pixels):
  old=self.recovery_keyframes[-1] if self.recovery_keyframes else None
  super().remember_map(tracker,xyz,pixels)
  if old is None or self.recovery_keyframes[-1] is not old or len(xyz)<60:return
  gray=getattr(tracker,'previous',None);frame=tracker.last_info[1]
  if gray is None or frame-old['frame']<30 or old['map_id']!=self.map_id:return
  self.recovery_keyframes[-1]=dict(gray=gray.copy(),xyz=xyz.copy(),pixels=pixels.astype('float32').copy(),Rwc=self.Rwc.copy(),center=self.center.copy(),frame=frame,session=tracker.last_info[0],reference=self.map_reference_frame,map_id=self.map_id,extensions=self.map_extensions_total,heading_epoch=self.heading_epoch,heading_root=self.heading_root)
