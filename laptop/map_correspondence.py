"""Independent feature-guided map matching; no calibration-target input."""
import cv2
import numpy as np

def descriptor_pairs(source,current):
 sift=cv2.SIFT_create(nfeatures=2000,contrastThreshold=.04,edgeThreshold=10)
 ka,da=sift.detectAndCompute(source,None);kb,db=sift.detectAndCompute(current,None)
 if da is None or db is None or len(da)<2 or len(db)<2:return None
 matcher=cv2.BFMatcher(cv2.NORM_L2)
 def select(x,y):
  return {m.queryIdx:m.trainIdx for pair in matcher.knnMatch(x,y,k=2) if len(pair)==2 for m,n in [pair] if m.distance<.7*n.distance}
 ab=select(da,db);ba=select(db,da);pairs=[(i,j) for i,j in ab.items() if ba.get(j)==i]
 # SIFT octave/orientation duplicates must not masquerade as independent points.
 selected_a=np.empty((len(pairs),2),float);selected_b=np.empty_like(selected_a);count=0
 for i,j in pairs:
  a=np.array(ka[i].pt);b=np.array(kb[j].pt)
  if count and (np.any(np.sum((selected_a[:count]-a)**2,axis=1)<4) or np.any(np.sum((selected_b[:count]-b)**2,axis=1)<4)):continue
  selected_a[count]=a;selected_b[count]=b;count+=1
 if count<90:return None
 return selected_a[:count].astype(np.float32),selected_b[:count].astype(np.float32)

def guided_flow(source,current,points):
 pairs=descriptor_pairs(source,current)
 if pairs is None:return None
 H,mask=cv2.findHomography(pairs[0],pairs[1],cv2.RANSAC,2.)
 if H is None or mask is None or np.mean(mask!=0)<.75:return None
 prediction=cv2.perspectiveTransform(points,H)
 if not np.isfinite(prediction).all():return None
 b,v,e=cv2.calcOpticalFlowPyrLK(source,current,points,prediction.copy(),winSize=(31,31),maxLevel=4,flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
 if b is None:return None
 back,vb,eb=cv2.calcOpticalFlowPyrLK(current,source,b,points.copy(),winSize=(31,31),maxLevel=4,flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
 if back is None:return None
 h,w=current.shape
 good=(v.ravel()!=0)&(vb.ravel()!=0)&(e.ravel()<25)&(eb.ravel()<25)&(np.linalg.norm(back[:,0]-points[:,0],axis=1)<1)&(np.linalg.norm(b[:,0]-prediction[:,0],axis=1)<=2)
 good &= np.isfinite(b[:,0]).all(1)&(b[:,0,0]>=0)&(b[:,0,0]<w)&(b[:,0,1]>=0)&(b[:,0,1]<h)
 return b,good
