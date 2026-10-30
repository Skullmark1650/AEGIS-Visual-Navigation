import unittest
from laptop.validation import recovery_events,resources,angle_error

class ValidationTests(unittest.TestCase):
    def test_planar_reference_exposes_near_tied_hypotheses(self):
        import cv2
        import numpy as np
        from laptop.board_reference import planar_reference
        obj=np.zeros((54,3));obj[:,:2]=np.mgrid[0:9,0:6].T.reshape(-1,2)*20-[80,50]
        K=np.array([[973.,0,320],[0,973.,240],[0,0,1.]])
        results=[]
        for r in [[0.,0,0],[.3,.3,.05]]:
            corners=cv2.projectPoints(obj,np.array(r),np.array([0.,0.,600.]),K,None)[0].reshape(-1,2)
            corners+=np.random.default_rng(2).normal(0,.12,(54,2))
            results.append(planar_reference(obj,corners,K,None))
        self.assertTrue(results[0]['ambiguous']);self.assertFalse(results[0]['usable'])
        self.assertGreater(results[0]['candidate_center_gap_mm'],5)
        self.assertTrue(results[1]['usable']);self.assertFalse(results[1]['ambiguous'])
        self.assertLess(results[1]['sensitivity_center_radius_mm'],5)
        corners=cv2.projectPoints(obj,np.array([.02,.02,0.]),np.array([0.,0.,600.]),K,None)[0].reshape(-1,2)
        corners+=np.random.default_rng(2).normal(0,.12,(54,2))
        sensitive=planar_reference(obj,corners,K,None)
        self.assertFalse(sensitive['ambiguous'])
        self.assertTrue(sensitive['sensitivity_unstable']);self.assertFalse(sensitive['usable'])
    def test_recovery_requires_retained_matches_not_new_seeds(self):
        rows=[dict(frame_id=1,elapsed_s=0,flow_reset_reason='startup',flow_tracked=0,vo_status='reset_startup'),
              dict(frame_id=2,elapsed_s=1,flow_reset_reason='tracking_quality',flow_tracked=0,vo_status='reset_tracking_quality'),
              dict(frame_id=3,elapsed_s=1.1,flow_reset_reason='',flow_tracked=0,vo_status='waiting_baseline'),
              dict(frame_id=4,elapsed_s=1.2,flow_reset_reason='',flow_tracked=50,vo_status='waiting_baseline'),
              dict(frame_id=5,elapsed_s=2,flow_reset_reason='',flow_tracked=50,vo_status='accepted')]
        events=recovery_events(rows)
        self.assertEqual(len(events),1)
        self.assertAlmostEqual(events[0]['tracking_recovery_s'],.2)
        self.assertEqual(events[0]['next_accepted_pose_s'],1)
    def test_unrecovered_is_censored_not_zero(self):
        rows=[dict(frame_id=1,elapsed_s=0,flow_reset_reason='frame_gap',flow_tracked=0,vo_status='reset_frame_gap')]
        r=recovery_events(rows)[0]
        self.assertIsNone(r['tracking_recovery_s']);self.assertIsNone(r['next_accepted_pose_s'])
    def test_resources_and_rotation(self):
        import numpy as np
        memory=resources();self.assertGreater(memory['process_peak_rss_bytes'],0)
        R=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        self.assertAlmostEqual(angle_error(R,np.eye(3)),90)

    def test_summary_does_not_count_waiting_as_pose_attempt(self):
        import json,tempfile
        from pathlib import Path
        from laptop.validation_summary import summarize
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);record=root/'record';record.mkdir()
            (record/'operator_notes.json').write_text(json.dumps({'protocol_status':'synthetic_test_fixture'}))
            transport=root/'transport.json'
            transport.write_text(json.dumps({'odometry':{'statuses':{'waiting_baseline':100,'reset_startup':1,'accepted':2,'low_parallax':2}},'connection_errors':0,'sequence_gaps':0}))
            transport.with_suffix('.csv').write_text('frame_id\n1\n')
            validation=root/'case.json'
            validation.write_text(json.dumps({'source_report':str(transport),'frames':1,'receive_fps':15,'processing_ms':{'mean':1,'p95':2},'weighted_track_acceptance':1,'accepted_pose_count':2,'resources':{'cpu_percent_one_core':10,'process_peak_rss_bytes':1000},'pose_comparisons':[],'recovery_events':[],'metric_vo_drift':'unavailable'}))
            study=root/'study.json';study.write_text(json.dumps({'cases':[{'case':'fixture','validation':str(validation),'recording':str(record)}],'limits':'Synthetic unit-test fixture only'}))
            r=summarize(study,root/'out')
            self.assertEqual(r['cases'][0]['accepted_fraction_of_evaluations'],.5)
            self.assertEqual(r['cases'][0]['metric_vo_drift'],'unavailable')
