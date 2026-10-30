"""Development-only mutual descriptor correspondence fallback; not live."""
import cv2,numpy as np
from .visual_odometry import VisualOdometry as Base
from .partial_orientation import orientation_from_3d

def descriptor_pairs(source,current):
 sift=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.04,edgeThreshold=10)
 ka,da=sift.detectAndCompute(source,None);kb,db=sift.detectAndCompute(current,None)
 if da is None or db is None or len(da)<2 or len(db)<2:return None
 matcher=cv2.BFMatcher(cv2.NORM_L2)
 def select(x,y):
  return {m.queryIdx:m.trainIdx for pair in matcher.knnMatch(x,y,k=2) if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance}
 ab=select(da,db);ba=select(db,da);pairs=[(i,j) for i,j in ab.items() if ba.get(j)==i]
 # SIFT octave/orientation duplicates must not masquerade as independent points.
 chosen=[]
 for i,j in pairs:
  a=np.array(ka[i].pt);b=np.array(kb[j].pt)
  if all(np.linalg.norm(a-x)>=2 and np.linalg.norm(b-y)>=2 for x,y in chosen):chosen.append((a,b))
 if len(chosen)<90:return None
 return np.array([x for x,y in chosen],np.float32),np.array([y for x,y in chosen],np.float32)
class VisualOdometry(Base):
 VERSION='experimental-descriptor-v14'
 def retrack_rotation(self,tr):
  model=super().retrack_rotation(tr)
  if model is not None:return model
  source=getattr(self,'anchor_gray',None);gray=getattr(tr,'previous',None);age=tr.last_info[1]-self.anchor_frame_id if self.anchor_frame_id is not None else 0
  if source is None or gray is None or source.shape!=gray.shape or not 0<age<=30:return None
  pairs=descriptor_pairs(source,gray)
  if pairs is None:return None
  a=cv2.undistortPoints(pairs[0][:,None,:],self.K,self.D)[:,0];b=cv2.undistortPoints(pairs[1][:,None,:],self.K,self.D)[:,0];f=float((self.K[0,0]+self.K[1,1])/2);H,mask=cv2.findHomography(a,b,cv2.RANSAC,1.5/f);model=self.rotation_model(a,b,H,mask)
  if model is None:model=orientation_from_3d(a,b,f,self.calibration['image_size'],self.fit_essential)
  if model is not None:model.update(rotation_method='experimental_mutual_sift')
  return model
