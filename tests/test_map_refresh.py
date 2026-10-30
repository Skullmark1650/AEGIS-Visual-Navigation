import unittest,numpy as np
from laptop.map_refresh_candidate import VisualOdometry
from test_calibration import test_profile
from types import SimpleNamespace
class RefreshTests(unittest.TestCase):
 def setUp(self):
  c=dict(source_kind='real_camera',numerical_checks_passed=True,requires_visual_review=False,camera_profile=test_profile(),image_size=[640,480],camera_matrix=[[700,0,320],[0,700,240],[0,0,1]],distortion=[0]*5);self.v=VisualOdometry(c);self.v.map_id=1;self.v.map_reference_frame=1;self.v.map_last_frame=1;self.tr=SimpleNamespace(previous=np.zeros((480,640),np.uint8),last_info=('s',1,1));self.xyz=np.column_stack([np.arange(60),np.zeros(60),np.ones(60)*5]);self.pixels=np.column_stack([np.arange(60)+30,np.ones(60)*100]).astype(np.float32)
 def test_current_observed_stationary_view_refreshed_not_archive_age_extended(self):
  v=self.v;v.remember_map(self.tr,self.xyz,self.pixels);self.tr.last_info=('s',30,30);v.remember_map(self.tr,self.xyz,self.pixels);self.assertEqual(v.recovery_keyframes[-1]['frame'],1)
  self.tr.last_info=('s',31,31);self.tr.previous[:]=17;v.remember_map(self.tr,self.xyz+1,self.pixels+1);k=v.recovery_keyframes[-1];self.assertEqual(len(v.recovery_keyframes),1);self.assertEqual(k['frame'],31);self.assertEqual(k['reference'],1);np.testing.assert_array_equal(k['xyz'],self.xyz+1);self.assertEqual(int(k['gray'][0,0]),17)
 def test_insufficient_map_points_cannot_refresh(self):
  self.v.remember_map(self.tr,self.xyz,self.pixels);self.tr.last_info=('s',100,100);self.v.remember_map(self.tr,self.xyz[:40],self.pixels[:40]);self.assertEqual(self.v.recovery_keyframes[-1]['frame'],1)
