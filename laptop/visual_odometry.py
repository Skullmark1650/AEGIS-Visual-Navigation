"""Conservative calibrated two-view odometry; unit steps are illustrative, not distance."""
import json
import time
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
if __package__:
    from .camera_calibration import verify_profile
else:
    from camera_calibration import verify_profile

class VisualOdometry:
    VERSION = 'retained-map-recovery-v10'
    def __init__(self, calibration):
        self.calibration = calibration
        verify_profile(calibration['camera_profile'])
        if calibration.get('source_kind') != 'real_camera' or not calibration.get('numerical_checks_passed') or calibration.get('requires_visual_review', True):
            raise ValueError('Reviewed real-camera calibration required')
        self.K = np.asarray(calibration['camera_matrix'], float)
        self.D = np.asarray(calibration['distortion'], float)
        if self.K.shape != (3,3) or not np.isfinite(self.K).all() or not np.isfinite(self.D).all():
            raise ValueError('Invalid calibration')
        self.recovery_keyframes=[];self.recovery_pending=None;self.map_id=0
        self.heading_epoch=-1;self.heading_serial=-1;self.heading_root=None;self.heading_keyframes=[];self.heading_pending=[]
        self.reset()
        self.segment = 0

    def reset(self):
        self.heading_serial+=1;self.heading_epoch=self.heading_serial;self.heading_root=None;self.heading_pending=[]
        self.Rwc = np.eye(3)
        self.center = np.zeros(3)
        self.path = [self.center.copy()]
        self.motion_mode = 'unknown'
        self.landmarks={}
        self.landmark_seeds={}
        self.map_extensions_total=0
        self.segment_origin=np.zeros(3)

    def remember_heading(self,tracker):
        gray=getattr(tracker,'previous',None)
        if gray is None or len(tracker.points)<90:return
        if self.heading_keyframes:
            if self.heading_epoch!=self.heading_keyframes[0]['epoch']:return
            last=self.heading_keyframes[-1]
            angle=np.degrees(np.linalg.norm(cv2.Rodrigues(last['Rwc'].T@self.Rwc)[0]))
            if tracker.last_info[1]-last['frame']<30 or angle<5:return
        keyframe=dict(gray=gray.copy(),points=tracker.points.copy(),Rwc=self.Rwc.copy(),frame=tracker.last_info[1],session=tracker.last_info[0],epoch=self.heading_epoch,root=self.heading_root)
        self.heading_keyframes.append(keyframe)
        if len(self.heading_keyframes)>3:self.heading_keyframes=[self.heading_keyframes[0]]+self.heading_keyframes[-2:]

    def recover_heading(self,tracker):
        if __package__:
            from .partial_orientation import image_correspondences,orientation_from_3d
        else:
            from partial_orientation import image_correspondences,orientation_from_3d
        gray=getattr(tracker,'previous',None);frame=tracker.last_info[1]
        if gray is None or frame%5:return None
        for key in self.heading_keyframes:
            if key['epoch']==self.heading_epoch or key['session']!=tracker.last_info[0] or gray.shape!=key['gray'].shape or not 0<frame-key['frame']<=1800:continue
            pairs=image_correspondences(key['gray'],gray,key['points'])
            if pairs is None:continue
            a=cv2.undistortPoints(pairs[0],self.K,self.D)[:,0]
            b=cv2.undistortPoints(pairs[1],self.K,self.D)[:,0]
            focal=float((self.K[0,0]+self.K[1,1])/2)
            H,mask=cv2.findHomography(a,b,cv2.RANSAC,1.5/focal)
            model=self.rotation_model(a,b,H,mask)
            if model is not None:model.update(rotation_method='heading_homography_recovery',homography_ratio=float(np.mean(mask!=0)))
            else:model=orientation_from_3d(a,b,focal,self.calibration['image_size'],self.fit_essential)
            if model is None:continue
            Rwc=key['Rwc']@np.array(model['rotation']).T
            self.heading_pending=[p for p in self.heading_pending if p['epoch']==key['epoch'] and 0<=frame-p['frame']<=30 and p['frame']!=frame]
            self.heading_pending.append(dict(epoch=key['epoch'],frame=frame,Rwc=Rwc))
            consistent=[p for p in self.heading_pending if np.degrees(np.linalg.norm(cv2.Rodrigues(p['Rwc'].T@Rwc)[0]))<=.2]
            if len(consistent)<3:
                return self.pose_fields(dict(status='heading_relocalizing',inliers=model['inliers'],inlier_ratio=model['inlier_ratio'],parallax_deg=0.,homography_ratio=0.,estimate_ms=0.))
            self.Rwc=Rwc;self.heading_epoch=key['epoch'];self.heading_root=key['root'];self.heading_pending=[]
            self.segment+=1;self.center=np.zeros(3);self.path=[self.center.copy()];self.segment_origin=np.zeros(3);self.motion_mode='rotation_only'
            self.anchor={int(i):p.copy() for i,p in zip(tracker.ids,tracker.points)};self.anchor_gray=gray;self.anchor_frame_id=frame;self.anchor_attempts=0;self.attempt_positions={}
            return self.pose_fields(dict(model,status='heading_relocalized',anchor_frame_id=key['frame'],parallax_deg=0.,estimate_ms=0.))
        self.heading_pending=[p for p in self.heading_pending if 0<=frame-p['frame']<=30]
        return None

    def extend_map(self,tracker):
        """Triangulate newly seeded IDs using two already-known map poses."""
        frame=tracker.last_info[1]
        current={int(i):p for i,p in zip(tracker.ids,tracker.points)}
        self.landmarks={i:p for i,p in self.landmarks.items() if i in current}
        self.landmark_seeds={i:s for i,s in self.landmark_seeds.items() if i in current and i not in self.landmarks and frame-s[3]<=150}
        Rwc=self.Rwc.copy();center=self.center.copy()
        for i,p in current.items():
            if i not in self.landmarks and i not in self.landmark_seeds:
                self.landmark_seeds[i]=(p.copy(),Rwc,center,frame)
        if frame%5:return 0
        groups={}
        for i,seed in self.landmark_seeds.items():
            if frame-seed[3]>=5 and np.linalg.norm(center-seed[2])>=.1:
                groups.setdefault(seed[3],[]).append(i)
        added=0
        for ids in groups.values():
            seeds=[self.landmark_seeds[i] for i in ids];R0,C0=seeds[0][1:3]
            a=np.array([s[0] for s in seeds]);b=np.array([current[i] for i in ids])
            x=cv2.undistortPoints(a[:,None,:],self.K,self.D)[:,0]
            y=cv2.undistortPoints(b[:,None,:],self.K,self.D)[:,0]
            R1=Rwc.T;R0=R0.T
            h=cv2.triangulatePoints(np.column_stack([R0,-R0@C0]),np.column_stack([R1,-R1@center]),x.T,y.T)
            good=np.abs(h[3])>1e-10
            xyz=np.zeros((len(ids),3));xyz[good]=(h[:3,good]/h[3,good]).T
            for R,C,observed in [(R0,C0,x),(R1,center,y)]:
                camera=(xyz-C)@R.T
                good &= (camera[:,2]>.1)&(camera[:,2]<1000)
                projection=camera[:,:2]/np.maximum(camera[:,2,None],1e-10)
                good &= np.linalg.norm((projection-observed)*[self.K[0,0],self.K[1,1]],axis=1)<.5
            rays0=np.column_stack([x,np.ones(len(x))])@R0
            rays1=np.column_stack([y,np.ones(len(y))])@R1
            rays0/=np.linalg.norm(rays0,axis=1)[:,None];rays1/=np.linalg.norm(rays1,axis=1)[:,None]
            good &= np.degrees(np.arccos(np.clip(np.sum(rays0*rays1,axis=1),-1,1)))>.75
            for i,p,valid in zip(ids,xyz,good):
                if valid:self.landmarks[i]=p;del self.landmark_seeds[i];added+=1
        self.map_extensions_total+=added
        return added

    def apply_rotation(self,R):
        if self.motion_mode!='rotation_only':
            self.segment+=1;self.center=np.zeros(3);self.path=[self.center.copy()]
        self.Rwc=self.Rwc@R.T;self.motion_mode='rotation_only'

    def retrack_rotation(self,tracker):
        """Recheck a recent rotation anchor directly in the images, never extrapolate."""
        gray=getattr(tracker,'previous',None)
        source=getattr(self,'anchor_gray',None)
        age=tracker.last_info[1]-self.anchor_frame_id if self.anchor_frame_id is not None else 0
        if gray is None or source is None or source.shape!=gray.shape or not 0<age<=30 or len(self.anchor)<60:return None
        points=np.array(list(self.anchor.values()),np.float32).reshape(-1,1,2)
        current,valid,error=cv2.calcOpticalFlowPyrLK(source,gray,points,None,winSize=(31,31),maxLevel=4)
        if current is None:return None
        back,valid_back,_=cv2.calcOpticalFlowPyrLK(gray,source,current,None,winSize=(31,31),maxLevel=4)
        if back is None:return None
        fb=np.linalg.norm(back[:,0]-points[:,0],axis=1)
        good=(valid.ravel()!=0)&(valid_back.ravel()!=0)&(error.ravel()<5)&(fb<.5)
        height,width=gray.shape
        good &= (current[:,0,0]>=0)&(current[:,0,0]<width)&(current[:,0,1]>=0)&(current[:,0,1]<height)
        if good.sum()<60 or good.mean()<.7:return None
        a=cv2.undistortPoints(points[good],self.K,self.D)[:,0]
        b=cv2.undistortPoints(current[good],self.K,self.D)[:,0]
        H,mask=cv2.findHomography(a,b,cv2.RANSAC,1.5/float((self.K[0,0]+self.K[1,1])/2))
        model=self.rotation_model(a,b,H,mask)
        if model is None:return None
        return dict(model,homography_ratio=float(np.mean(mask!=0)),rotation_method='photometric_retrack',rotation_retrack_ratio=float(good.mean()),rotation_retrack_fb_px=float(np.median(fb[good])))

    def initialize_map(self,a,b,ids,R,t,Rwc,center):
        """Triangulate a temporary local map in the initial baseline's units."""
        x=cv2.undistortPoints(a[:,None,:],self.K,self.D)[:,0]
        y=cv2.undistortPoints(b[:,None,:],self.K,self.D)[:,0]
        homogeneous=cv2.triangulatePoints(np.column_stack([np.eye(3),np.zeros(3)]),np.column_stack([R,t]),x.T,y.T)
        good=np.abs(homogeneous[3])>1e-10
        xyz=np.zeros((len(x),3));xyz[good]=(homogeneous[:3,good]/homogeneous[3,good]).T
        current=xyz@R.T+t
        good &= (xyz[:,2]>.1)&(current[:,2]>.1)&(xyz[:,2]<1000)&(current[:,2]<1000)
        for points,observed in [(xyz,x),(current,y)]:
            projected=points[:,:2]/np.maximum(points[:,2,None],1e-10)
            good &= np.linalg.norm((projected-observed)*[self.K[0,0],self.K[1,1]],axis=1)<.75
        aa=np.column_stack([x,np.ones(len(x))])@R.T;bb=np.column_stack([y,np.ones(len(y))])
        aa/=np.linalg.norm(aa,axis=1)[:,None];bb/=np.linalg.norm(bb,axis=1)[:,None]
        good &= np.degrees(np.arccos(np.clip(np.sum(aa*bb,axis=1),-1,1)))>.5
        if good.sum()<50:return
        singular=np.linalg.svd(xyz[good]-np.mean(xyz[good],axis=0),compute_uv=False)
        if singular[-1]/singular[0]<.01:return
        self.landmarks={int(i):Rwc@p+center for i,p in zip(np.asarray(ids)[good],xyz[good])}

    def solve_map_pose(self,xyz,pixels,reference_R=None,reference_C=None,max_step=1):
        ok,r,t,inliers=cv2.solvePnPRansac(xyz,pixels,self.K,self.D,iterationsCount=100,reprojectionError=1.,confidence=.999,flags=cv2.SOLVEPNP_EPNP)
        if not ok or inliers is None or len(inliers)<40 or len(inliers)/len(xyz)<.7:return None
        keep=inliers.ravel();r,t=cv2.solvePnPRefineLM(xyz[keep],pixels[keep],self.K,self.D,r,t)
        R=cv2.Rodrigues(r)[0];C=-R.T@t.ravel()
        projected=cv2.projectPoints(xyz[keep],r,t,self.K,self.D)[0].reshape(-1,2)
        residual=float(np.median(np.linalg.norm(projected-pixels[keep],axis=1)))
        w,h=self.calibration['image_size']
        coverage=cv2.contourArea(cv2.convexHull(pixels[keep].astype(np.float32)))/(w*h)
        if residual>.5 or coverage<.1 or np.any((xyz[keep]@R.T+t.ravel())[:,2]<=0):return None
        previous_R=self.Rwc if reference_R is None else reference_R
        previous_C=self.center if reference_C is None else reference_C
        if np.linalg.norm(C-previous_C)>max_step or np.degrees(np.linalg.norm(cv2.Rodrigues(previous_R@R)[0]))>20:return None
        return R,C,keep,residual

    def remember_map(self,tracker,xyz,pixels):
        gray=getattr(tracker,'previous',None)
        if gray is None or len(xyz)<60:return
        frame=tracker.last_info[1]
        if self.recovery_keyframes:
            previous=self.recovery_keyframes[-1]
            previous['extensions']=self.map_extensions_total
            angle=np.degrees(np.linalg.norm(cv2.Rodrigues(previous['Rwc'].T@self.Rwc)[0]))
            if frame-previous['frame']<30:return
            if np.linalg.norm(self.center-previous['center'])<.2 and angle<5:
                self.recovery_keyframes[-1]=dict(gray=gray.copy(),xyz=xyz.copy(),pixels=pixels.astype(np.float32).copy(),Rwc=self.Rwc.copy(),center=self.center.copy(),frame=frame,session=tracker.last_info[0],reference=self.map_reference_frame,map_id=self.map_id,extensions=self.map_extensions_total,heading_epoch=self.heading_epoch,heading_root=self.heading_root)
                return
        self.recovery_keyframes.append(dict(gray=gray.copy(),xyz=xyz.copy(),pixels=pixels.astype(np.float32).copy(),Rwc=self.Rwc.copy(),center=self.center.copy(),frame=frame,session=tracker.last_info[0],reference=self.map_reference_frame,map_id=self.map_id,extensions=self.map_extensions_total,heading_epoch=self.heading_epoch,heading_root=self.heading_root))
        self.recovery_keyframes=self.recovery_keyframes[-3:]

    def track_map(self,tracker):
        """Absolute PnP in one local map; no bridging when mapped IDs disappear."""
        pairs=[(self.landmarks[int(i)],p) for i,p in zip(tracker.last_ids,tracker.last_current) if int(i) in self.landmarks]
        if len(pairs)<50:return None
        xyz=np.array([p[0] for p in pairs],float);pixels=np.array([p[1] for p in pairs],float)
        solution=self.solve_map_pose(xyz,pixels)
        if solution is None:return None
        R,C,keep,residual=solution
        previous_R=self.Rwc.copy();previous_C=self.center.copy()
        relative=R@previous_R;translation=R@(previous_C-C)
        self.Rwc=R.T;self.center=C;self.path.append(C.copy())
        added=self.extend_map(tracker) if residual<.3 and len(keep)/len(pairs)>=.85 and hasattr(tracker,'ids') else 0
        out=dict(status='map_tracking',anchor_frame_id=self.map_last_frame,inliers=len(keep),inlier_ratio=len(keep)/len(pairs),parallax_deg=0.,homography_ratio=0.,estimate_ms=0.,rotation=relative.tolist(),translation_direction=(translation/np.linalg.norm(translation)).tolist() if np.linalg.norm(translation)>1e-8 else None,translation_map=translation.tolist(),map_reprojection_px=residual,map_added=added)
        self.map_last_frame=tracker.last_info[1]
        self.remember_map(tracker,xyz[keep],pixels[keep])
        return self.pose_fields(out)

    def recover_map(self,tracker):
        """Reacquire frozen map points by bidirectional keyframe LK, then PnP.

        Two independent current frames must confirm the same map. The unseen
        interval remains a path break even when origin and scale are recovered.
        """
        if __package__:
            from .map_correspondence import guided_flow
        else:
            from map_correspondence import guided_flow
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
            # Preserve the larger verified set even when incidental tracker
            # coincidences already exceed the minimum recovery threshold.
            # Otherwise a successful recovery can starve future keyframes.
            if adopt is not None and len(selected)>=50 and len(selected)>len(restored):
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



    @staticmethod
    def fit_essential(a,b,threshold):
        """Use RANSAC for outliers, then fit all its inliers instead of a minimal sample."""
        E,mask=cv2.findEssentialMat(a,b,np.eye(3),method=cv2.RANSAC,prob=.999,threshold=threshold,maxIters=1000)
        if E is None or E.shape!=(3,3) or mask is None:return E,mask
        keep=mask.ravel()!=0
        if keep.sum()<30:return E,mask
        refined,_=cv2.findFundamentalMat(a[keep],b[keep],cv2.FM_8POINT)
        if refined is None or refined.shape!=(3,3):return E,mask
        u,s,vt=np.linalg.svd(refined)
        refined=u@np.diag([(s[0]+s[1])/2]*2+[0.])@vt
        x=np.column_stack([a,np.ones(len(a))]);y=np.column_stack([b,np.ones(len(b))])
        ex=x@refined.T;ey=y@refined
        residual=np.abs(np.sum(y*ex,axis=1))/np.sqrt(np.maximum(1e-20,np.sum(ex[:,:2]**2+ey[:,:2]**2,axis=1)))
        refined_mask=(keep & (residual<threshold)).astype(np.uint8).reshape(-1,1)
        if refined_mask.sum()<.9*keep.sum():return E,mask
        return refined,refined_mask

    def rotation_model(self, a, b, H, mask):
        """Accept only a well-supported near-orthogonal calibrated homography.

        This is a rotation-compatible image model, not proof of zero translation.
        In particular, a distant/planar scene can hide translation.
        """
        if H is None or mask is None:return None
        keep=mask.ravel()!=0
        if keep.sum()<60 or keep.mean()<.9:return None
        H=H/np.cbrt(np.linalg.det(H)) if np.linalg.det(H)>0 else H
        u,s,vt=np.linalg.svd(H)
        spread=float(s.max()/s.min()-1)
        if np.linalg.det(u@vt)<0:return None
        rays_a=np.column_stack([a,np.ones(len(a))]);rays_b=np.column_stack([b,np.ones(len(b))])
        rays_a/=np.linalg.norm(rays_a,axis=1)[:,None]
        rays_b/=np.linalg.norm(rays_b,axis=1)[:,None]
        u,_,vt=np.linalg.svd(rays_a[keep].T@rays_b[keep])
        R=vt.T@np.diag([1,1,np.linalg.det(vt.T@u.T)])@u.T
        # Require features spread across the image, not one small moving patch.
        pixels=(a[keep]*[self.K[0,0],self.K[1,1]])
        w,h=self.calibration['image_size']
        area=cv2.contourArea(cv2.convexHull(pixels.astype(np.float32)))
        if area/(w*h)<.1:return None
        projected=np.column_stack([a,np.ones(len(a))])@R.T
        if np.any(projected[:,2]<=0):return None
        error=np.linalg.norm((projected[:,:2]/projected[:,2,None]-b)*[self.K[0,0],self.K[1,1]],axis=1)
        if np.median(error[keep])>.4 or np.mean(error<1.)<.9:return None
        degrees=float(np.degrees(np.linalg.norm(cv2.Rodrigues(R)[0])))
        if not .05<degrees<20:return None
        _,rotations,_,_=cv2.decomposeHomographyMat(H,np.eye(3))
        gap=max((float(np.degrees(np.linalg.norm(cv2.Rodrigues(p@q.T)[0]))) for p in rotations for q in rotations),default=float('inf'))
        # A planar slide has different admissible rotations; a genuine turn
        # must dominate that ambiguity rather than selecting a convenient branch.
        if gap>.3 or degrees<2*gap:return None
        return dict(rotation=R.tolist(),rotation_residual_px=float(np.median(error[keep])),rotation_model_spread=spread,
                    rotation_ambiguity_deg=gap,
                    inliers=int(keep.sum()),inlier_ratio=float(keep.mean()))

    def estimate(self, previous, current):
        started = time.perf_counter()
        out = dict(status='insufficient_tracks', inliers=0, inlier_ratio=0., parallax_deg=0., homography_ratio=0., direction_spread_deg=0.)
        def finish():
            out['estimate_ms'] = (time.perf_counter()-started)*1000
            return out
        a,b = np.asarray(previous, float).reshape(-1,2),np.asarray(current,float).reshape(-1,2)
        if len(a)!=len(b) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Invalid correspondences')
        if len(a)<30: return finish()
        if np.median(np.linalg.norm(b-a,axis=1)) < 1.0:
            out['status']='low_motion'; return finish()
        a=cv2.undistortPoints(a.reshape(-1,1,2),self.K,self.D).reshape(-1,2)
        b=cv2.undistortPoints(b.reshape(-1,1,2),self.K,self.D).reshape(-1,2)
        threshold=1.0 / float((self.K[0,0]+self.K[1,1])/2)
        try:
            H,hm=cv2.findHomography(a,b,cv2.RANSAC,threshold*1.5)
            out['homography_ratio']=float(np.mean(hm!=0)) if hm is not None else 0.
            if out['homography_ratio']>.85:
                model=self.rotation_model(a,b,H,hm)
                if model is not None:
                    out.update(model,status='rotation_only');return finish()
                out['status']='planar_or_rotation'; return finish()
            E,mask=self.fit_essential(a,b,threshold*.5)
            if E is None or E.shape!=(3,3) or mask is None:
                out['status']='essential_failed'; return finish()
            count,R,t,posemask,_=cv2.recoverPose(E,a,b,np.eye(3),distanceThresh=1000.,mask=mask.copy())
            out.update(inliers=int(count),inlier_ratio=float(count/len(a)))
            if count<30 or count/len(a)<.6:
                out['status']='pose_support_failed'; return finish()
            rays_a=np.column_stack([a,np.ones(len(a))]); rays_b=np.column_stack([b,np.ones(len(b))])
            rays_a=rays_a@R.T
            rays_a/=np.linalg.norm(rays_a,axis=1)[:,None];rays_b/=np.linalg.norm(rays_b,axis=1)[:,None]
            angle=np.degrees(np.arccos(np.clip(np.sum(rays_a*rays_b,axis=1),-1,1)))
            out['parallax_deg']=float(np.median(angle[posemask.ravel()!=0]))
            if out['parallax_deg']<.75:
                out['status']='low_parallax'; return finish()
            if np.degrees(np.linalg.norm(cv2.Rodrigues(R)[0]))>20:
                out['status']='excess_rotation'; return finish()
            # A plausible essential matrix can still have an unstable signed
            # translation. Require independent, interleaved subsets to agree.
            directions=[]
            for offset in range(3):
                aa,bb=a[offset::3],b[offset::3]
                if len(aa)<30:
                    out['status']='insufficient_validation_tracks'; return finish()
                ee,mm=self.fit_essential(aa,bb,threshold*.5)
                if ee is None or ee.shape!=(3,3) or mm is None:
                    out['status']='unstable_direction'; return finish()
                nn,rr,tt,_,_=cv2.recoverPose(ee,aa,bb,np.eye(3),distanceThresh=1000.,mask=mm.copy())
                if nn<20 or nn/len(aa)<.6:
                    out['status']='unstable_direction'; return finish()
                directions.append(tt.ravel())
            out['direction_spread_deg']=float(max(np.degrees(np.arccos(np.clip(d@t.ravel(),-1,1))) for d in directions))
            if out['direction_spread_deg']>15:
                out['status']='unstable_direction'; return finish()
            out.update(status='accepted',rotation=R.tolist(),translation_direction=t.ravel().tolist())
        except cv2.error:
            out['status']='geometry_error'
        return finish()

    def update(self, previous, current, reset_reason='', defer_rejection=False):
        if reset_reason:
            self.segment+=1;self.reset()
            out=dict(status='reset_'+reset_reason,inliers=0,inlier_ratio=0.,parallax_deg=0.,homography_ratio=0.,estimate_ms=0.)
        else:
            out=self.estimate(previous,current)
            if out['status']=='accepted':
                if self.motion_mode=='rotation_only':
                    self.segment+=1;self.center=np.zeros(3);self.path=[self.center.copy()]
                R=np.asarray(out['rotation']);t=np.asarray(out['translation_direction'])
                self.Rwc=self.Rwc@R.T
                self.center=self.center-self.Rwc@t
                self.path.append(self.center.copy())
                self.motion_mode='translation'
            elif out['status']=='rotation_only':
                self.apply_rotation(np.asarray(out['rotation']))
            elif out['status']!='low_motion' and not defer_rejection:
                # Never bridge a failed pair with an invented displacement.
                self.segment+=1;self.reset()
        return self.pose_fields(out)

    def pose_fields(self,out):
        out.setdefault('anchor_frame_id',None)
        out['estimator_version']=self.VERSION
        out.setdefault('direction_spread_deg',0.)
        out.setdefault('rotation_residual_px',None)
        out.setdefault('rotation_model_spread',None)
        out.setdefault('rotation_ambiguity_deg',None)
        out.setdefault('rotation_method',None)
        out.setdefault('rotation_retrack_ratio',None)
        out.setdefault('rotation_retrack_fb_px',None)
        out['translation_observed']=out['status'] in ('accepted','map_tracking','relocalized')
        out['orientation_observed']=out['status'] in ('accepted','rotation_only','map_tracking','relocalized','heading_relocalized')
        out['heading_epoch']=self.heading_epoch;out['heading_reference_frame_id']=self.heading_root
        for key in ('rotation_subset_spread_deg','essential_null_ratio','essential_rank_ratio','rotation_epipolar_px'):out.setdefault(key,None)
        out.setdefault('map_reprojection_px',None)
        out.setdefault('translation_map',None)
        out.setdefault('map_added',0)
        out['map_extensions_total']=self.map_extensions_total
        out['map_id']=self.map_id if self.landmarks else None
        out['segment_origin']=self.segment_origin.tolist()
        out['map_reference_frame_id']=getattr(self,'map_reference_frame',None) if self.landmarks else None
        out['map_landmarks']=len(self.landmarks)
        out['scale_mode']='local_map' if self.landmarks else 'independent_unit_steps'
        out.setdefault('rotation',None)
        out.setdefault('translation_direction',None)
        out.update(segment=self.segment,center_arbitrary=self.center.tolist(),orientation_camera_to_world=self.Rwc.tolist())
        return out

    def update_tracks(self, tracker, flow):
        """Keep an anchor until sufficient image displacement; match only retained IDs."""
        all_started=time.perf_counter()
        def done(out):
            if self.heading_root is None:self.heading_root=frame_id
            if out['status'].startswith('reset_') or out['orientation_observed']:self.remember_heading(tracker)
            out=self.pose_fields(out)
            out['estimate_ms']=(time.perf_counter()-all_started)*1000
            return out
        current={int(i):p.copy() for i,p in zip(tracker.ids,tracker.points)}
        reset=flow['reset_reason']
        frame_id=tracker.last_info[1] if hasattr(tracker,'last_info') and tracker.last_info else None
        if reset or not hasattr(self,'anchor'):
            self.recovery_pending=None
            if reset in ('session_change','resolution_change','nonmonotonic_frame'):
                self.recovery_keyframes=[];self.recovery_pending=None
                self.heading_keyframes=[];self.heading_pending=[]
            self.anchor=current
            self.anchor_gray=getattr(tracker,'previous',None)
            self.anchor_frame_id=frame_id
            self.anchor_attempts=0
            self.attempt_positions={}
            return done(self.update([],[],reset or 'anchor_start'))
        if not self.landmarks and self.recovery_keyframes:
            started=time.perf_counter()
            try:recovered=self.recover_map(tracker)
            except cv2.error:recovered=None
            if recovered is not None:
                recovered['estimate_ms']=(time.perf_counter()-started)*1000
                return done(recovered)
        if not self.landmarks and self.heading_keyframes and self.heading_epoch!=self.heading_keyframes[0]['epoch']:
            try:recovered=self.recover_heading(tracker)
            except cv2.error:recovered=None
            if recovered is not None:return done(recovered)
        if self.landmarks:
            started=time.perf_counter()
            try:out=self.track_map(tracker)
            except cv2.error:out=None
            if out is None:
                self.recovery_pending=None
                self.anchor=current;self.anchor_frame_id=frame_id;self.anchor_attempts=0;self.attempt_positions={}
                self.anchor_gray=getattr(tracker,'previous',None)
                return done(self.update([],[],'map_lost'))
            out['estimate_ms']=(time.perf_counter()-started)*1000
            return done(out)
        ids=[int(i) for i in tracker.last_ids if int(i) in self.anchor]
        latest={int(i):p for i,p in zip(tracker.last_ids,tracker.last_current)}
        a=np.array([self.anchor[i] for i in ids]).reshape(-1,2)
        b=np.array([latest[i] for i in ids]).reshape(-1,2)
        motion=float(np.median(np.linalg.norm(b-a,axis=1))) if len(ids) else 0.
        if len(ids)>=60 and 4<=motion<12:
            started=time.perf_counter()
            x=cv2.undistortPoints(a[:,None,:],self.K,self.D)[:,0]
            y=cv2.undistortPoints(b[:,None,:],self.K,self.D)[:,0]
            try:
                H,mask=cv2.findHomography(x,y,cv2.RANSAC,1.5/float((self.K[0,0]+self.K[1,1])/2))
                model=self.rotation_model(x,y,H,mask)
            except cv2.error:model=None
            if model is not None:
                self.apply_rotation(np.array(model['rotation']))
                out=dict(status='rotation_only',anchor_frame_id=self.anchor_frame_id,parallax_deg=0.,homography_ratio=float(np.mean(mask!=0)),direction_spread_deg=0.,estimate_ms=(time.perf_counter()-started)*1000,**model)
                self.anchor=current;self.anchor_frame_id=frame_id;self.anchor_attempts=0;self.attempt_positions={}
                self.anchor_gray=getattr(tracker,'previous',None)
                return done(self.pose_fields(out))
        if self.motion_mode=='rotation_only' and motion>=4:
            try:model=self.retrack_rotation(tracker)
            except cv2.error:model=None
            if model is not None:
                self.apply_rotation(np.array(model['rotation']))
                out=dict(status='rotation_only',anchor_frame_id=self.anchor_frame_id,parallax_deg=0.,direction_spread_deg=0.,estimate_ms=0.,**model)
                self.anchor=current;self.anchor_gray=getattr(tracker,'previous',None)
                self.anchor_frame_id=frame_id;self.anchor_attempts=0;self.attempt_positions={}
                return done(self.pose_fields(out))
        if len(ids)>=30 and motion<12:
            # Avoid inventing a tiny-baseline pose; retain the same anchor.
            out=dict(status='waiting_baseline',anchor_frame_id=getattr(self,'anchor_frame_id',None),inliers=0,inlier_ratio=0.,parallax_deg=0.,homography_ratio=0.,estimate_ms=0.)
            return done(self.pose_fields(out))
        attempted=getattr(self,'attempt_positions',{})
        changes=[np.linalg.norm(latest[i]-attempted[i]) for i in ids if i in attempted]
        if len(changes)>=90 and np.median(changes)<1:
            # Retrying the same noisy pair adds no geometric evidence. Wait
            # for actual image movement without spending the retry allowance.
            out=dict(status='waiting_geometry',anchor_frame_id=self.anchor_frame_id,inliers=0,inlier_ratio=0.,parallax_deg=0.,homography_ratio=0.,estimate_ms=0.)
            return done(self.pose_fields(out))
        self.anchor_attempts=getattr(self,'anchor_attempts',0)+1
        # Retry a weak geometric pair against the same retained IDs, allowing
        # parallax to grow. Never bridge tracker resets or insufficient matches.
        deferred=len(ids)>=90 and self.anchor_attempts<=16
        previous_R=self.Rwc.copy();previous_C=self.center.copy()
        out=self.update(a,b,defer_rejection=deferred)
        if out['status']=='accepted':
            self.initialize_map(a,b,ids,np.array(out['rotation']),np.array(out['translation_direction']),previous_R,previous_C)
            if self.landmarks:
                # A map has one consistent scale. Do not attach it to older,
                # independently scaled unit steps as though their scales match.
                self.landmarks={k:v-previous_C for k,v in self.landmarks.items()}
                self.center-=previous_C;self.path=[np.zeros(3),self.center.copy()];self.segment+=1
                self.map_last_frame=frame_id;self.map_reference_frame=self.anchor_frame_id
                self.map_id+=1;self.recovery_keyframes=[];self.recovery_pending=None
                pairs=[(self.landmarks[int(i)],p) for i,p in zip(tracker.ids,tracker.points) if int(i) in self.landmarks]
                if pairs:self.remember_map(tracker,np.array([p[0] for p in pairs]),np.array([p[1] for p in pairs]))
            out=self.pose_fields(out)
        self.attempt_positions={i:latest[i].copy() for i in ids}
        out["anchor_frame_id"]=getattr(self,"anchor_frame_id",None)
        if deferred and out['status'] not in ('accepted','rotation_only','low_motion'):
            return done(out)
        self.anchor_frame_id=frame_id
        self.anchor=current
        self.anchor_gray=getattr(tracker,'previous',None)
        self.anchor_attempts=0
        self.attempt_positions={}
        return done(out)

    def validate_frame(self, row, size):
        p=self.calibration['camera_profile']
        if list(size)!=self.calibration['image_size'] or row.get('camera_profile_id')!=p['profile_id'] or row.get('focus_mode')!='manual' or row.get('lens_position') is None or abs(row['lens_position']-p['profile']['lens_position'])>.05:
            raise ValueError('Odometry frame calibration/profile mismatch')

    def overlay(self,image,out):
        rgb=np.asarray(image).copy()
        cv2.putText(rgb,'VO: '+out['status'],(8,100),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,210,80),1)
        panel=np.full((220,rgb.shape[1],3),20,np.uint8)
        cv2.putText(panel,'X/Z local units: NOT METERS',(8,20),cv2.FONT_HERSHEY_SIMPLEX,.43,(240,220,120),1)
        cv2.putText(panel,'Segment '+str(self.segment)+('; local map scale' if self.landmarks else '; independent unit steps')+'; resets break path',(8,40),cv2.FONT_HERSHEY_SIMPLEX,.4,(200,200,200),1)
        pts=np.array(self.path)[:,[0,2]]
        scale=80/max(1,float(np.abs(pts).max()))
        pixels=np.rint(pts*scale+[rgb.shape[1]/2,130]).astype(np.int32)
        if len(pixels)>1:cv2.polylines(panel,[pixels],False,(60,220,120),2)
        cv2.circle(panel,tuple(pixels[-1]),3,(255,200,40),-1)
        return Image.fromarray(np.concatenate([rgb,panel],axis=0))
