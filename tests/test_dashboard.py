import unittest
from laptop.navigation_dashboard import telemetry

class DashboardTests(unittest.TestCase):
    def test_processing_fps_and_gaps(self):
        rows=[dict(processed_elapsed_s=i*.1,sequence_gap=i,vo_status='accepted') for i in range(3)]
        d=telemetry(rows,5,5,'LIVE')
        self.assertAlmostEqual(d['fps'],10)
        self.assertEqual(d['producer_gaps'],3)
        self.assertFalse(d['stale'])
    def test_stale_and_disconnect_never_look_live(self):
        d=telemetry([dict(processed_elapsed_s=1,sequence_gap=0)],10,1,'Reconnecting')
        self.assertTrue(d['stale']);self.assertEqual(d['fps'],0)
        self.assertTrue(any('STALE' in s for s in d['warnings']))
        self.assertTrue(any('Reconnecting' in s for s in d['warnings']))
    def test_startup_has_no_fabricated_pose(self):
        d=telemetry([],0,None,'Connecting')
        self.assertEqual(d['latest'],{});self.assertEqual(d['fps'],0)
        self.assertTrue(d['stale'])

    def test_countdown_never_goes_negative(self):
        from laptop.navigation_dashboard import recording_clock
        self.assertIn('01:55 remaining',recording_clock(5,120))
        self.assertIn('00:00 remaining',recording_clock(125,120))

    def test_path_break_keeps_history_without_joining_origins(self):
        from laptop.navigation_dashboard import retain_path
        state=dict(path=[],segment=None,accepted_seen=False)
        retain_path(state,dict(vo_segment=1,vo_status='accepted',vo_center_arbitrary='[1,0,0]'))
        retain_path(state,dict(vo_segment=2,vo_status='reset_frame_gap'))
        self.assertEqual(state['history'],[[[1,0,0]]])
        self.assertEqual(state['path'],[])
        self.assertFalse(state['accepted_seen'])
        retain_path(state,dict(vo_segment=2,vo_status='accepted',vo_center_arbitrary='[0,0,1]'))
        self.assertEqual(state['path'],[[0,0,1]])
        self.assertEqual(state['history'],[[[1,0,0]]])

    def test_rotation_reports_unknown_translation_and_displays_orientation(self):
        from laptop.navigation_dashboard import retain_path
        state=dict(path=[],segment=None,accepted_seen=False)
        row=dict(vo_segment=1,vo_status='rotation_only',processed_elapsed_s=0,sequence_gap=0)
        retain_path(state,row)
        self.assertTrue(state['orientation_seen']);self.assertFalse(state['accepted_seen'])
        self.assertEqual(state['path'],[])
        data=telemetry([row],1,1,'LIVE')
        self.assertTrue(any('translation UNKNOWN' in s for s in data['warnings']))

    def test_local_map_path_and_scale_label(self):
        from laptop.navigation_dashboard import retain_path
        state=dict(path=[],segment=None,accepted_seen=False)
        row=dict(vo_segment=2,vo_status='map_tracking',vo_center_arbitrary='[0.2,0,0]',vo_scale_mode='local_map',processed_elapsed_s=0,sequence_gap=0)
        retain_path(state,row)
        self.assertEqual(state['path'],[[.2,0,0]])
        data=telemetry([row],1,1,'LIVE')
        self.assertTrue(any('Local map units' in s for s in data['warnings']))
        self.assertFalse(any('independent unit steps' in s for s in data['warnings']))

    def test_relocalized_path_starts_at_observed_position_not_zero(self):
        from laptop.navigation_dashboard import retain_path
        state=dict(path=[],segment=None,accepted_seen=False)
        retain_path(state,dict(vo_segment=2,vo_status='map_tracking',vo_center_arbitrary='[1,0,0]',vo_segment_origin='[0,0,0]'))
        retain_path(state,dict(vo_segment=3,vo_status='reset_map_lost',vo_segment_origin='[0,0,0]'))
        row=dict(vo_segment=4,vo_status='relocalized',vo_center_arbitrary='[1.2,0,0]',vo_segment_origin='[1.2,0,0]',processed_elapsed_s=0,sequence_gap=0)
        retain_path(state,row)
        self.assertEqual(state['origin'],[1.2,0,0]);self.assertEqual(state['path'],[[1.2,0,0]])
        self.assertEqual(state['history'],[[[1,0,0]]])
        self.assertTrue(any('gap is unknown' in w for w in telemetry([row],1,1,'LIVE')['warnings']))

    def test_heading_only_recovery_updates_orientation_without_a_position_path(self):
        from laptop.navigation_dashboard import retain_path
        state=dict(path=[],segment=None,accepted_seen=False)
        row=dict(vo_segment=4,vo_status='heading_relocalized',vo_center_arbitrary='[0,0,0]',processed_elapsed_s=0,sequence_gap=0)
        retain_path(state,row)
        self.assertTrue(state['orientation_seen']);self.assertFalse(state['accepted_seen'])
        self.assertEqual(state['path'],[])
        self.assertTrue(any('position' in w and 'UNKNOWN' in w for w in telemetry([row],1,1,'LIVE')['warnings']))
