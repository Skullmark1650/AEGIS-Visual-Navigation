import copy
import json
import unittest
from pathlib import Path
try:
    import cv2
    import numpy as np
    from laptop.visual_odometry import VisualOdometry
    from laptop.verify_odometry import scenario
    from test_calibration import test_profile
    AVAILABLE=True
except ModuleNotFoundError:
    AVAILABLE=False

@unittest.skipUnless(AVAILABLE,'Requires optional laptop vision dependencies')
class OdometryTests(unittest.TestCase):
    def setUp(self):
        # Explicit test-only calibration fixture; never installed on a camera.
        self.c=dict(source_kind='real_camera',numerical_checks_passed=True,requires_visual_review=False,
            camera_profile=test_profile(),image_size=[640,480],camera_matrix=[[700,0,320],[0,700,240],[0,0,1]],distortion=[0,0,0,0,0])
    def test_known_motion_outliers_and_inverse_composition(self):
        a,b,R,t=scenario(self.c,seed=3)
        vo=VisualOdometry(self.c);cv2.setRNGSeed(3);out=vo.update(a,b)
        self.assertEqual(out['status'],'accepted')
        Re=np.array(out['rotation']);te=np.array(out['translation_direction'])
        self.assertLess(np.degrees(np.arccos(np.clip((np.trace(Re@R.T)-1)/2,-1,1))),1)
        self.assertGreater(te@t/np.linalg.norm(t),.98)
        np.testing.assert_allclose(vo.center,-Re.T@te,atol=1e-8)
        np.testing.assert_allclose(vo.Rwc,Re.T)
    def test_stationary_rotation_planar_and_insufficient_rejected(self):
        for kw in [dict(rotation=(0,0,0),translation=(0,0,0)),dict(translation=(0,0,0)),dict(planar=True)]:
            a,b,_,_=scenario(self.c,outliers=0,**kw)
            vo=VisualOdometry(self.c);self.assertNotEqual(vo.update(a,b)['status'],'accepted')
            np.testing.assert_array_equal(vo.center,np.zeros(3))
        self.assertEqual(VisualOdometry(self.c).update([],[])['status'],'insufficient_tracks')
    def test_gap_and_quality_failures_break_segment(self):
        a,b,_,_=scenario(self.c)
        vo=VisualOdometry(self.c);vo.update(a,b);old=vo.segment
        out=vo.update(a,b,'frame_gap');self.assertEqual(out['segment'],old+1)
        np.testing.assert_array_equal(vo.center,np.zeros(3))
    def test_profile_and_review_gates(self):
        for key,value in [('source_kind','synthetic'),('requires_visual_review',True),('numerical_checks_passed',False)]:
            c=copy.deepcopy(self.c);c[key]=value
            with self.assertRaises(ValueError):VisualOdometry(c)
        vo=VisualOdometry(self.c)
        with self.assertRaises(ValueError):vo.validate_frame({},(640,480))
        with self.assertRaises(ValueError):vo.update([[float('nan'),0]],[[1,1]])

    def test_rendered_tracking_pipeline_and_baseline_wait(self):
        from laptop.verify_odometry import rendered_sequence
        r=rendered_sequence(self.c)
        statuses=[x['pose']['status'] for x in r['frames']]
        self.assertIn('accepted',statuses)
        self.assertIn('waiting_baseline',statuses)
        good=[x['pose'] for x in r['frames'] if x['pose']['status']=='accepted']
        self.assertLess(max(x['direction_error_deg'] for x in good),15)
    def test_csv_schema_stable_across_accepted_and_waiting(self):
        from types import SimpleNamespace
        a,b,_,_=scenario(self.c,seed=3)
        vo=VisualOdometry(self.c);accepted=vo.update(a,b)
        tracker=SimpleNamespace(ids=np.arange(len(a)),points=a,last_ids=np.arange(len(a)),last_current=a)
        vo.update_tracks(tracker,{'reset_reason':'startup'})
        waiting=vo.update_tracks(tracker,{'reset_reason':''})
        self.assertEqual(waiting['status'],'waiting_baseline')
        self.assertEqual(set(accepted),set(waiting))

    def test_validation_rejects_uncertain_direction_without_advancing_pose(self):
        # Real camera intrinsics, synthetic nonplanar scene and known motion.
        # A short, noisy baseline can disagree across feature subsets even
        # after the all-inlier refit; it must not advance position.
        c=copy.deepcopy(self.c)
        c['camera_matrix']=[[973.5994789,0,291.4574285],[0,971.2865467,236.5939505],[0,0,1]]
        c['distortion']=[.03711729,.32390670,-.000562858,-.01318757,-2.00660479]
        rejected=[]
        for seed in range(10):
            a,b,_,_=scenario(c,seed,translation=(-.12,.01,.03),noise=.3)
            cv2.setRNGSeed(seed);vo=VisualOdometry(c);out=vo.update(a,b)
            if out['status']=='unstable_direction':
                rejected.append(out)
                np.testing.assert_array_equal(vo.center,np.zeros(3))
                self.assertIsNone(out['translation_direction'])
        self.assertTrue(rejected)

    def test_rotation_updates_orientation_without_claiming_translation(self):
        for seed in range(5):
            a,b,R,_=scenario(self.c,seed=seed,translation=(0,0,0),outliers=0)
            cv2.setRNGSeed(seed);vo=VisualOdometry(self.c);out=vo.update(a,b)
            self.assertEqual(out['status'],'rotation_only')
            self.assertFalse(out['translation_observed'])
            self.assertTrue(out['orientation_observed'])
            self.assertIsNone(out['translation_direction'])
            np.testing.assert_array_equal(vo.center,np.zeros(3))
            error=np.degrees(np.linalg.norm(cv2.Rodrigues(vo.Rwc@R)[0]))
            self.assertLess(error,.1)
            self.assertEqual(set(out),set(vo.update([],[],'frame_gap')))

    def test_planar_slide_is_not_called_rotation(self):
        a,b,_,_=scenario(self.c,translation=(.3,0,0),rotation=(0,0,0),planar=True,outliers=0)
        out=VisualOdometry(self.c).update(a,b)
        self.assertEqual(out['status'],'planar_or_rotation')
        self.assertFalse(out['orientation_observed'])

    def test_rotation_shape_tolerance_does_not_admit_planar_slides(self):
        for distance in [.04,.06,.08,.12,.2,.3,.4]:
            for seed in range(10):
                a,b,_,_=scenario(self.c,seed=seed,translation=(distance,0,0),rotation=(0,0,0),planar=True,outliers=0)
                cv2.setRNGSeed(seed);out=VisualOdometry(self.c).update(a,b)
                self.assertEqual(out['status'],'planar_or_rotation')

    def test_weak_pair_retries_same_anchor_without_double_integration(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        points=np.array([[x,y] for x in range(50,600,50) for y in range(50,450,40)],dtype=float)
        tracker=SimpleNamespace(ids=np.arange(len(points)),points=points,last_ids=np.arange(len(points)),last_current=points,last_info=('test',1,1))
        vo=VisualOdometry(self.c);vo.update_tracks(tracker,{'reset_reason':'startup'})
        segment=vo.segment
        tracker.points=tracker.last_current=points+[25,0];tracker.last_info=('test',2,2)
        base=dict(inliers=100,inlier_ratio=1.,parallax_deg=.1,homography_ratio=.1,estimate_ms=0.)
        with patch.object(vo,'estimate',return_value=dict(base,status='low_parallax')):
            out=vo.update_tracks(tracker,{'reset_reason':''})
        self.assertEqual(vo.anchor_frame_id,1);self.assertEqual(vo.segment,segment)
        np.testing.assert_array_equal(vo.center,np.zeros(3))

        tracker.points=tracker.last_current=points+[27,0]
        with patch.object(vo,'estimate',return_value=dict(base,status='accepted',rotation=np.eye(3).tolist(),translation_direction=[1,0,0])):
            out=vo.update_tracks(tracker,{'reset_reason':''})
        self.assertEqual(out['anchor_frame_id'],1);self.assertEqual(vo.anchor_frame_id,2)
        np.testing.assert_array_equal(vo.center,[-1,0,0])
        tracker.last_info=('test',3,3)
        out=vo.update_tracks(tracker,{'reset_reason':'frame_gap'})
        self.assertGreater(out['segment'],segment)
        self.assertEqual(vo.anchor_frame_id,3)
        np.testing.assert_array_equal(vo.Rwc,np.eye(3))
        tracker.points=tracker.last_current=points+[50,0]
        for frame in range(4,21):
            tracker.points=tracker.last_current=points+[50+2*(frame-4),0]
            tracker.last_info=('test',frame,frame)
            with patch.object(vo,'estimate',return_value=dict(base,status='low_parallax')):
                out=vo.update_tracks(tracker,{'reset_reason':''})
        self.assertEqual(vo.anchor_frame_id,20)
        self.assertEqual(vo.segment,segment+2)

    def test_map_replenishes_new_ids_with_the_existing_scale(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(51);n=220
        xyz=np.column_stack([rng.uniform(-1,1,n),rng.uniform(-.8,.8,n),rng.uniform(4,8,n)])
        K=np.array(self.c['camera_matrix'],float);D=np.zeros(5)
        vo=VisualOdometry(self.c);vo.landmarks={i:p.copy() for i,p in enumerate(xyz[:110])}
        vo.map_reference_frame=0;vo.map_last_frame=0
        for frame,C in [(5,np.zeros(3)),(10,np.array([.25,0,0]))]:
            pixels=cv2.projectPoints(xyz,np.zeros(3),-C,K,D)[0].reshape(-1,2)
            tracker=SimpleNamespace(ids=np.arange(n),points=pixels,last_ids=np.arange(n),last_current=pixels,last_info=('test',frame,frame))
            out=vo.track_map(tracker);self.assertIsNotNone(out)
        self.assertGreater(vo.map_extensions_total,90)
        np.testing.assert_allclose(vo.landmarks[150],xyz[150],atol=.001)
        tracker.ids=tracker.last_ids=np.arange(110,n)
        tracker.points=tracker.last_current=pixels[110:]
        tracker.last_info=('test',11,11)
        self.assertIsNotNone(vo.track_map(tracker))
        np.testing.assert_allclose(vo.center,[.25,0,0],atol=.001)

    def test_keyframe_recovery_requires_two_frames_and_rejects_wrong_scene(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(61)
        gray=np.full((480,640),20,np.uint8)
        depth=np.full(gray.shape,6.,float)
        for y in range(60,430,35):
            for x in range(60,590,35):
                gray[y-5:y+6,x-5:x+6]=rng.integers(40,240,(11,11),dtype=np.uint8)
                depth[y-6:y+7,x-6:x+7]=rng.uniform(4,9)
        pixels=cv2.goodFeaturesToTrack(gray,200,.01,10).reshape(-1,2)
        rays=cv2.undistortPoints(pixels[:,None,:],np.array(self.c['camera_matrix'],float),np.zeros(5))[:,0]
        z=np.array([depth[int(y),int(x)] for x,y in pixels])
        xyz=np.column_stack([rays,np.ones(len(rays))])*z[:,None]
        tracker=SimpleNamespace(ids=np.arange(len(pixels)),points=pixels,last_ids=np.arange(len(pixels)),last_current=pixels,last_info=('test',1,1),previous=gray)
        vo=VisualOdometry(self.c);vo.map_id=1;vo.map_reference_frame=0;vo.map_last_frame=1
        vo.landmarks={i:p for i,p in enumerate(xyz)};vo.remember_map(tracker,xyz,pixels)
        vo.update([],[],'map_lost')
        tracker.previous=np.zeros_like(gray);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_map(tracker))
        tracker.ids=tracker.last_ids=tracker.ids+1000;tracker.previous=rng.integers(0,255,gray.shape,dtype=np.uint8);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_map(tracker))
        self.assertFalse(vo.landmarks)
        tracker.previous=gray;tracker.last_info=('test',10,10)
        first=vo.recover_map(tracker);self.assertEqual(first['status'],'relocalizing');self.assertFalse(first['translation_observed'])
        self.assertEqual(vo.recover_map(tracker)['status'],'relocalizing')
        tracker.last_info=('test',15,15)
        second=vo.recover_map(tracker);self.assertEqual(second['status'],'relocalized')
        self.assertEqual(second['map_id'],1);self.assertGreater(len(vo.landmarks),100)
        np.testing.assert_allclose(vo.center,np.zeros(3),atol=.005)
        np.testing.assert_allclose(second['segment_origin'],vo.center)
        tracker.last_info=('different-session',20,20)
        vo.update_tracks(tracker,{'reset_reason':'session_change'})
        self.assertEqual(vo.recovery_keyframes,[])

    def test_continuous_synthetic_turn_returns_without_heading_reset(self):
        from laptop.verify_odometry import rotation_sequence
        result=rotation_sequence(self.c)['records']
        self.assertLess(result[-1]['orientation_error_deg'],.2)
        self.assertLess(max(r['orientation_error_deg'] for r in result),.5)
        self.assertLessEqual(len({r['segment'] for r in result}),2)
        self.assertGreater(sum(r['status']=='rotation_only' for r in result),40)


    def test_local_map_tracks_return_with_one_scale_and_rejects_lost_ids(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(17)
        xyz=np.column_stack([rng.uniform(-1,1,200),rng.uniform(-.8,.8,200),rng.uniform(4,8,200)])
        K=np.array(self.c['camera_matrix'],float);D=np.zeros(5)
        R=cv2.Rodrigues(np.array([0.,.02,0.]))[0];C=np.array([.4,0,0]);t=-R@C
        a=cv2.projectPoints(xyz,np.zeros(3),np.zeros(3),K,D)[0].reshape(-1,2)
        b=cv2.projectPoints(xyz,cv2.Rodrigues(R)[0],t,K,D)[0].reshape(-1,2)
        vo=VisualOdometry(self.c);vo.initialize_map(a,b,np.arange(len(a)),R,t/.4,np.eye(3),np.zeros(3))
        self.assertGreater(len(vo.landmarks),100)
        vo.Rwc=R.T;vo.center=C/.4;vo.map_last_frame=1;vo.map_reference_frame=0
        for frame,fraction in enumerate([.8,.5,.2,0.],2):
            pixels=cv2.projectPoints(xyz,np.zeros(3),-C*fraction,K,D)[0].reshape(-1,2)
            pixels[:15]=rng.uniform([0,0],[640,480],(15,2))
            tracker=SimpleNamespace(last_ids=np.arange(len(a)),last_current=pixels,last_info=('test',frame,frame))
            cv2.setRNGSeed(frame);out=vo.track_map(tracker)
            self.assertEqual(out['status'],'map_tracking')
            np.testing.assert_allclose(vo.center,C/.4*fraction,atol=.003)
        np.testing.assert_allclose(vo.center,np.zeros(3),atol=.003)
        tracker.last_ids=np.arange(1000,1200)
        self.assertIsNone(vo.track_map(tracker))
        self.assertEqual(set(out),set(vo.update([],[],'frame_gap')))
        self.assertEqual(vo.landmarks,{})
        np.testing.assert_array_equal(vo.center,np.zeros(3))


    def test_rotation_rematch_repairs_bad_tracks_using_image_evidence(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(93)
        gray=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(5,5),1.)
        points=cv2.goodFeaturesToTrack(gray,240,.01,12).reshape(-1,2)
        K=np.array(self.c['camera_matrix'],float)
        R=cv2.Rodrigues(np.array([0.,.012,0.]))[0];H=K@R@np.linalg.inv(K)
        image=cv2.warpPerspective(gray,H,(640,480))
        actual=cv2.perspectiveTransform(points[:,None,:],H)[:,0]
        noisy=actual.copy();noisy[::2,1]+=2.;noisy[1::2,1]-=2.
        tracker=SimpleNamespace(ids=np.arange(len(points)),points=noisy,last_ids=np.arange(len(points)),last_current=noisy,last_info=('test',2,2),previous=image)
        vo=VisualOdometry(self.c);vo.anchor={i:p.copy() for i,p in enumerate(points)}
        vo.anchor_frame_id=1;vo.anchor_gray=gray;vo.motion_mode='rotation_only'
        cv2.setRNGSeed(2);out=vo.update_tracks(tracker,{'reset_reason':''})
        self.assertEqual(out['status'],'rotation_only')
        self.assertEqual(out['rotation_method'],'photometric_retrack')
        self.assertGreaterEqual(out['rotation_retrack_ratio'],.7)
        error=np.degrees(np.linalg.norm(cv2.Rodrigues(vo.Rwc@R)[0]))
        self.assertLess(error,.1)
        self.assertFalse(out['translation_observed'])
        self.assertEqual(out['anchor_frame_id'],1)

    def test_rotation_rematch_rejects_planar_slides_blank_images_and_stale_views(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(94)
        gray=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(5,5),1.)
        points=cv2.goodFeaturesToTrack(gray,240,.01,12).reshape(-1,2)
        vo=VisualOdometry(self.c);vo.anchor={i:p.copy() for i,p in enumerate(points)}
        vo.anchor_frame_id=1;vo.anchor_gray=gray;vo.motion_mode='rotation_only'
        for shift in [5.,12.,25.]:
            image=cv2.warpAffine(gray,np.array([[1.,0,shift],[0,1.,0]]),(640,480))
            tracker=SimpleNamespace(previous=image,last_info=('test',2,2))
            cv2.setRNGSeed(2);self.assertIsNone(vo.retrack_rotation(tracker))
        tracker.previous=np.zeros_like(gray)
        self.assertIsNone(vo.retrack_rotation(tracker))
        tracker.previous=gray;tracker.last_info=('test',32,32)
        self.assertIsNone(vo.retrack_rotation(tracker))


    def test_partial_orientation_rejects_planar_degeneracy(self):
        from laptop.partial_orientation import orientation_from_3d
        focal=(self.c['camera_matrix'][0][0]+self.c['camera_matrix'][1][1])/2
        good=0
        for planar in [False,True]:
            for noise in [.03,.1,.15,.3]:
                for seed in range(20):
                    a,b,R,_=scenario(self.c,seed=seed,noise=noise,outliers=0,planar=planar,rotation=(.01,-.025,.005),translation=(.1,.02,.03))
                    a=cv2.undistortPoints(a[:,None,:],np.array(self.c['camera_matrix'],float),np.zeros(5))[:,0]
                    b=cv2.undistortPoints(b[:,None,:],np.array(self.c['camera_matrix'],float),np.zeros(5))[:,0]
                    cv2.setRNGSeed(seed);out=orientation_from_3d(a,b,focal,[640,480],VisualOdometry.fit_essential)
                    if planar:self.assertIsNone(out)
                    elif out is not None:
                        good+=1
                        self.assertIsNone(out['translation_direction'])
                        error=np.degrees(np.linalg.norm(cv2.Rodrigues(np.array(out['rotation'])@R.T)[0]))
                        self.assertLess(error,.3)
        self.assertGreater(good,0)

    def test_heading_recovery_restores_reference_without_position(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(104)
        gray=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(7,7),2.)
        points=cv2.goodFeaturesToTrack(gray,240,.01,12).reshape(-1,2)
        ids=np.arange(len(points));tracker=SimpleNamespace(ids=ids,points=points,last_ids=ids,last_current=points,last_info=('test',1,1),previous=gray)
        vo=VisualOdometry(self.c);first=vo.update_tracks(tracker,{'reset_reason':'startup'});epoch=first['heading_epoch']
        K=np.array(self.c['camera_matrix'],float);R=cv2.Rodrigues(np.array([0.,.012,0.]))[0];H=K@R@np.linalg.inv(K)
        image=cv2.warpPerspective(gray,H,(640,480));pixels=cv2.perspectiveTransform(points[:,None,:],H)[:,0]
        tracker.previous=image;tracker.points=tracker.last_current=pixels;tracker.last_info=('test',2,2)
        vo.update_tracks(tracker,{'reset_reason':'frame_gap'})
        tracker.previous=np.zeros_like(gray);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_heading(tracker))
        tracker.previous=rng.integers(0,256,gray.shape,dtype=np.uint8)
        self.assertIsNone(vo.recover_heading(tracker))
        tracker.previous=image
        for frame in [10,10,15]:
            tracker.last_info=('test',frame,frame)
            out=vo.recover_heading(tracker)
            self.assertEqual(out['status'],'heading_relocalizing')
            self.assertFalse(out['orientation_observed'])
        tracker.last_info=('test',20,20);out=vo.recover_heading(tracker)
        self.assertEqual(out['status'],'heading_relocalized')
        self.assertEqual(out['heading_epoch'],epoch);self.assertEqual(out['heading_reference_frame_id'],1)
        self.assertTrue(out['orientation_observed']);self.assertFalse(out['translation_observed'])
        np.testing.assert_array_equal(vo.center,np.zeros(3))
        self.assertFalse(vo.landmarks)
        self.assertLess(np.degrees(np.linalg.norm(cv2.Rodrigues(vo.Rwc@R)[0])),.1)
        vo.update([],[],'frame_gap');self.assertGreater(vo.heading_epoch,epoch+1)
        tracker.last_info=('other-session',25,25);self.assertIsNone(vo.recover_heading(tracker))
        tracker.last_info=('test',1900,1900)
        self.assertIsNone(vo.recover_heading(tracker))

    def test_heading_recovery_does_not_turn_planar_slide_into_heading(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(105)
        gray=cv2.GaussianBlur(rng.integers(0,256,(480,640),dtype=np.uint8),(5,5),1.)
        points=cv2.goodFeaturesToTrack(gray,240,.01,12).reshape(-1,2);ids=np.arange(len(points))
        tracker=SimpleNamespace(ids=ids,points=points,last_ids=ids,last_current=points,last_info=('test',1,1),previous=gray)
        vo=VisualOdometry(self.c);vo.update_tracks(tracker,{'reset_reason':'startup'});vo.update([],[],'frame_gap')
        tracker.previous=cv2.warpAffine(gray,np.array([[1.,0.,12.],[0.,1.,0.]]),(640,480))
        for frame in [5,10,15,20]:
            tracker.last_info=('test',frame,frame)
            self.assertIsNone(vo.recover_heading(tracker))

    def test_recovery_adopts_verified_landmarks_without_seed_coincidence(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(61)
        gray=np.full((480,640),20,np.uint8)
        depth=np.full(gray.shape,6.,float)
        for y in range(60,430,35):
            for x in range(60,590,35):
                gray[y-5:y+6,x-5:x+6]=rng.integers(40,240,(11,11),dtype=np.uint8)
                depth[y-6:y+7,x-6:x+7]=rng.uniform(4,9)
        pixels=cv2.goodFeaturesToTrack(gray,200,.01,10).reshape(-1,2)
        rays=cv2.undistortPoints(pixels[:,None,:],np.array(self.c['camera_matrix'],float),np.zeros(5))[:,0]
        z=np.array([depth[int(y),int(x)] for x,y in pixels])
        xyz=np.column_stack([rays,np.ones(len(rays))])*z[:,None]
        tracker=SimpleNamespace(ids=np.arange(len(pixels)),points=pixels,last_ids=np.arange(len(pixels)),last_current=pixels,last_info=('test',1,1),previous=gray)
        vo=VisualOdometry(self.c);vo.map_id=1;vo.map_reference_frame=0;vo.map_last_frame=1
        vo.landmarks={i:p for i,p in enumerate(xyz)};vo.remember_map(tracker,xyz,pixels)
        from laptop.optical_flow import OpticalFlowTracker,FlowConfig
        tracker=OpticalFlowTracker(FlowConfig())
        tracker.previous=gray;tracker.last_info=('test',1,1)
        tracker.points=pixels+np.array([3.,3.],np.float32)
        tracker.ids=np.arange(1000,1000+len(pixels));tracker.next_id=10000
        tracker.last_ids=tracker.ids.copy();tracker.last_current=tracker.points.copy()
        original_points=tracker.points.copy()
        vo.update([],[],'map_lost')
        tracker.previous=np.zeros_like(gray);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_map(tracker))
        tracker.ids=tracker.last_ids=tracker.ids+1000;tracker.previous=rng.integers(0,255,gray.shape,dtype=np.uint8);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_map(tracker))
        self.assertFalse(vo.landmarks)
        tracker.previous=gray;tracker.last_info=('test',10,10)
        first=vo.recover_map(tracker);self.assertEqual(first['status'],'relocalizing');self.assertFalse(first['translation_observed'])
        np.testing.assert_array_equal(tracker.points,original_points)
        self.assertEqual(vo.recover_map(tracker)['status'],'relocalizing')
        tracker.last_info=('test',15,15)
        second=vo.recover_map(tracker);self.assertEqual(second['status'],'relocalized')
        self.assertEqual(second['map_id'],1);self.assertGreater(len(vo.landmarks),100)
        self.assertTrue(all(k>=10000 for k in vo.landmarks))
        self.assertLessEqual(len(tracker.points),300)
        self.assertEqual(len(set(tracker.ids)),len(tracker.ids))
        self.assertFalse(any(k in vo.landmarks for k in tracker.last_ids))
        from PIL import Image
        tracker.update(Image.fromarray(np.repeat(gray[:,:,None],3,axis=2)),'test',16,16,render=False)
        tracker.last_info=('test',16,16)
        self.assertIsNotNone(vo.track_map(tracker))
        np.testing.assert_allclose(vo.center,np.zeros(3),atol=.005)
        np.testing.assert_allclose(second['segment_origin'],vo.center)
        tracker.last_info=('different-session',20,20)
        vo.update_tracks(tracker,{'reset_reason':'session_change'})
        self.assertEqual(vo.recovery_keyframes,[])




    def test_recovery_preserves_full_set_even_with_61_seed_coincidences(self):
        from types import SimpleNamespace
        rng=np.random.default_rng(61)
        gray=np.full((480,640),20,np.uint8)
        depth=np.full(gray.shape,6.,float)
        for y in range(60,430,35):
            for x in range(60,590,35):
                gray[y-5:y+6,x-5:x+6]=rng.integers(40,240,(11,11),dtype=np.uint8)
                depth[y-6:y+7,x-6:x+7]=rng.uniform(4,9)
        pixels=cv2.goodFeaturesToTrack(gray,200,.01,10).reshape(-1,2)
        rays=cv2.undistortPoints(pixels[:,None,:],np.array(self.c['camera_matrix'],float),np.zeros(5))[:,0]
        z=np.array([depth[int(y),int(x)] for x,y in pixels])
        xyz=np.column_stack([rays,np.ones(len(rays))])*z[:,None]
        tracker=SimpleNamespace(ids=np.arange(len(pixels)),points=pixels,last_ids=np.arange(len(pixels)),last_current=pixels,last_info=('test',1,1),previous=gray)
        vo=VisualOdometry(self.c);vo.map_id=1;vo.map_reference_frame=0;vo.map_last_frame=1
        vo.landmarks={i:p for i,p in enumerate(xyz)};vo.remember_map(tracker,xyz,pixels)
        from laptop.optical_flow import OpticalFlowTracker,FlowConfig
        tracker=OpticalFlowTracker(FlowConfig())
        tracker.previous=gray;tracker.last_info=('test',1,1)
        tracker.points=np.concatenate([pixels[:61],pixels[61:]+np.array([3.,3.],np.float32)])
        tracker.ids=np.arange(1000,1000+len(pixels));tracker.next_id=10000
        tracker.last_ids=tracker.ids.copy();tracker.last_current=tracker.points.copy()
        original_points=tracker.points.copy()
        vo.update([],[],'map_lost')
        tracker.previous=np.zeros_like(gray);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_map(tracker))
        tracker.ids=tracker.last_ids=tracker.ids+1000;tracker.previous=rng.integers(0,255,gray.shape,dtype=np.uint8);tracker.last_info=('test',5,5)
        self.assertIsNone(vo.recover_map(tracker))
        self.assertFalse(vo.landmarks)
        tracker.previous=gray;tracker.last_info=('test',10,10)
        first=vo.recover_map(tracker);self.assertEqual(first['status'],'relocalizing');self.assertFalse(first['translation_observed'])
        np.testing.assert_array_equal(tracker.points,original_points)
        self.assertEqual(vo.recover_map(tracker)['status'],'relocalizing')
        tracker.last_info=('test',15,15)
        second=vo.recover_map(tracker);self.assertEqual(second['status'],'relocalized')
        self.assertEqual(second['map_id'],1);self.assertGreater(len(vo.landmarks),100)
        self.assertTrue(all(k>=10000 for k in vo.landmarks))
        self.assertLessEqual(len(tracker.points),300)
        self.assertEqual(len(set(tracker.ids)),len(tracker.ids))
        self.assertFalse(any(k in vo.landmarks for k in tracker.last_ids))
        from PIL import Image
        tracker.update(Image.fromarray(np.repeat(gray[:,:,None],3,axis=2)),'test',16,16,render=False)
        tracker.last_info=('test',16,16)
        self.assertIsNotNone(vo.track_map(tracker))
        np.testing.assert_allclose(vo.center,np.zeros(3),atol=.005)
        np.testing.assert_allclose(second['segment_origin'],vo.center)
        tracker.last_info=('different-session',20,20)
        vo.update_tracks(tracker,{'reset_reason':'session_change'})
        self.assertEqual(vo.recovery_keyframes,[])
