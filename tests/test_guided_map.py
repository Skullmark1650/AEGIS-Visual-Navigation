import unittest,numpy as np,cv2
from laptop.map_correspondence import guided_flow
class GuidedFlowTests(unittest.TestCase):
 def setUp(self):
  rng=np.random.default_rng(210);self.im=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(3,3),.6);self.points=cv2.goodFeaturesToTrack(self.im,180,.01,12).reshape(-1,1,2)
 def test_known_large_slide_is_observed_not_invented(self):
  shifted=cv2.warpAffine(self.im,np.array([[1.,0.,36.],[0.,1.,0.]]),(640,480));result=guided_flow(self.im,shifted,self.points);self.assertIsNotNone(result);b,good=result;self.assertGreater(good.sum(),100);self.assertLess(np.median(np.linalg.norm(b[good,0]-self.points[good,0]-[36,0],axis=1)),.1)
 def test_blank_wrong_and_repeated_only_scene_reject(self):
  rng=np.random.default_rng(211);wrong=cv2.GaussianBlur(rng.integers(0,256,self.im.shape,dtype=np.uint8),(3,3),.6)
  for scene in [np.zeros_like(self.im),wrong]:self.assertIsNone(guided_flow(self.im,scene,self.points))
  y,x=np.indices(self.im.shape);board=(((x//24+y//24)%2)*255).astype(np.uint8);shifted=cv2.warpAffine(board,np.array([[1.,0.,48.],[0.,1.,0.]]),(640,480));self.assertIsNone(guided_flow(board,shifted,self.points))

