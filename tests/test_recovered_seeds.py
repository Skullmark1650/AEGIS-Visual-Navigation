import unittest
import numpy as np
from laptop.optical_flow import OpticalFlowTracker,FlowConfig

class RecoveredSeedsTests(unittest.TestCase):
 def test_adoption_is_bounded_unique_and_not_a_flow_observation(self):
  t=OpticalFlowTracker(FlowConfig());t.previous=np.zeros((480,640),np.uint8);t.points=np.array([[20,20],[100,100]],np.float32);t.ids=np.array([0,1]);t.next_id=2;t.last_ids=t.ids.copy();t.last_current=t.points.copy();new=t.adopt_verified_points([[21,21],[200,200]])
  self.assertEqual(list(new),[2,3]);self.assertEqual(list(t.ids),[2,3,1]);self.assertEqual(list(t.last_ids),[0,1]);np.testing.assert_array_equal(t.last_current,[[20,20],[100,100]])
  before=t.points.copy()
  for bad in [[[np.nan,2]],[[640,2]],[[-1,2]],[[2,2],[2.5,2.5]]]:
   with self.assertRaises(ValueError):t.adopt_verified_points(bad)
   np.testing.assert_array_equal(before,t.points)
 def test_recovery_does_not_survive_stale_or_resolution_change(self):
  # Reuse a real map fixture supplied by the integration test via direct gate:
  from laptop.visual_odometry import VisualOdometry
  from test_calibration import test_profile
  from types import SimpleNamespace
  c=dict(source_kind='real_camera',numerical_checks_passed=True,requires_visual_review=False,camera_profile=test_profile(),image_size=[640,480],camera_matrix=[[700,0,320],[0,700,240],[0,0,1]],distortion=[0]*5)
  v=VisualOdometry(c);key={'frame':1,'session':'a','gray':np.zeros((480,640),np.uint8)};v.recovery_keyframes=[key]
  tr=SimpleNamespace(last_info=('a',905,905),previous=key['gray'])
  self.assertIsNone(v.recover_map(tr));tr.last_info=('a',5,5);tr.previous=np.zeros((240,320),np.uint8);self.assertIsNone(v.recover_map(tr))
