"""Experimental globally guided map re-matching and fresh observed archive."""
import cv2,numpy as np
from .map_refresh_candidate import VisualOdometry as RefreshBase
from .rotation_descriptor_candidate import descriptor_pairs

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
class VisualOdometry(RefreshBase):
    VERSION='experimental-guided-map-v21'
    def recover_map(self,tracker):
        """Reacquire frozen map points by bidirectional keyframe LK, then PnP.

        Two independent current frames must confirm the same map. The unseen
        interval remains a path break even when origin and scale are recovered.
        """
        gray=getattr(tracker,'previous',None)
        frame=tracker.last_info[1]
        if gray is None or frame%5:return None
        for keyframe in reversed(self.recovery_keyframes):
            if tracker.last_info[0]!=keyframe['session'] or gray.shape!=keyframe['gray'].shape or not 0<frame-keyframe['frame']<=900:continue
            a=keyframe['pixels'].reshape(-1,1,2)
            matched=guided_flow(keyframe['gray'],gray,a)
            if matched is None:continue
            b,good=matched
            if good.sum()<60:continue
            xyz=keyframe['xyz'][good];pixels=b[good,0].astype(float)
            solution=self.solve_map_pose(xyz,pixels,keyframe['Rwc'],keyframe['center'],max_step=2)
            if solution is None:continue
            R,C,keep,residual=solution
            # Associate only subpixel-near new tracker points, with one-to-one IDs.
            if not len(tracker.ids):continue
            distances=np.sum((pixels[keep,None,:]-tracker.points[None,:,:])**2,axis=2)
            nearest=np.argmin(distances,axis=1);order=np.argsort(distances[np.arange(len(keep)),nearest])
            used=set();restored={}
            for index in order:
                j=int(nearest[index])
                if j not in used and distances[index,j]<=.75**2:
                    restored[int(tracker.ids[j])]=xyz[keep[index]].copy();used.add(j)
            # A reseeded tracker need not select exactly the old mapped corners.
            # Keep real verified map-image measurements, with fresh identities,
            # only after the same two-frame pose confirmation used previously.
            adopt=getattr(tracker,'adopt_verified_points',None)
            selected=[]
            h,w=gray.shape
            for index in keep:
                point=pixels[index]
                if not np.isfinite(point).all() or not (0<=point[0]<w and 0<=point[1]<h):continue
                if all(np.linalg.norm(point-pixels[j])>=2 for j in selected):selected.append(index)
            if len(restored)<50 and (adopt is None or len(selected)<50):continue
            pending=self.recovery_pending
            self.recovery_pending=dict(R=R,C=C,map_id=keyframe['map_id'],frame=frame)
            if pending is None or pending['map_id']!=keyframe['map_id'] or frame==pending['frame'] or np.linalg.norm(C-pending['C'])>.2 or np.degrees(np.linalg.norm(cv2.Rodrigues(R@pending['R'].T)[0]))>2:
                return self.pose_fields(dict(status='relocalizing',inliers=len(keep),inlier_ratio=len(keep)/len(xyz),parallax_deg=0.,homography_ratio=0.,estimate_ms=0.))
            if len(restored)<50:
                restored_ids=adopt(pixels[selected])
                restored={int(i):xyz[j].copy() for i,j in zip(restored_ids,selected)}
            self.landmarks=restored;self.Rwc=R.T;self.center=C;self.path=[C.copy()]
            self.segment+=1;self.segment_origin=C.copy();self.motion_mode='translation'
            self.map_id=keyframe['map_id'];self.map_reference_frame=keyframe['reference'];self.map_last_frame=frame
            self.heading_epoch=keyframe['heading_epoch'];self.heading_root=keyframe['heading_root']
            self.map_extensions_total=max(k['extensions'] for k in self.recovery_keyframes if k['map_id']==self.map_id);self.recovery_pending=None
            return self.pose_fields(dict(status='relocalized',inliers=len(keep),inlier_ratio=len(keep)/len(xyz),parallax_deg=0.,homography_ratio=0.,estimate_ms=0.,map_reprojection_px=residual))
        self.recovery_pending=None
        return None


