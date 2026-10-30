import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from laptop.ai_assistant import ReadOnlyTools,analyze,reserve_request,summarize_csv,bounded_path,ROOT,write_report

class AssistantTests(unittest.TestCase):
    def test_allowlist_rejects_shell_and_path_arguments(self):
        tools=ReadOnlyTools({'measured':{}})
        self.assertEqual(tools.call('get_selected_telemetry',{}),{'measured':{}})
        for name,args in [('shell',{}),('get_selected_telemetry',{'path':'secret'})]:
            with self.assertRaises(ValueError):tools.call(name,args)
    def test_budget_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'usage.db';reserve_request(db,1)
            with self.assertRaises(ValueError):reserve_request(db,1)
    def test_no_key_fails_before_network(self):
        from unittest.mock import patch
        with patch('laptop.ai_assistant.environment_value',return_value=None):
            with self.assertRaises(ValueError):analyze({},transport=lambda *_:self.fail('Network called'))
    def test_mocked_response_and_bounded_tool_loop(self):
        responses=[{'output':[dict(type='function_call',name='get_selected_telemetry',arguments='{}',call_id='mock-call')]},
                   {'model':'mock-model','status':'completed','usage':{'input_tokens':100,'output_tokens':20},'output':[{'type':'message','content':[{'type':'output_text','text':'MOCK ONLY: recorded gap explains a discontinuity, not a proven cause.'}]}]}]
        requests=[]
        def transport(payload,key):requests.append(payload);return responses.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            r=analyze({'measured':{'maximum_receive_gap_s':4.781}},key='test-only',model='mock-model',database=Path(tmp)/'budget.db',transport=transport)
        self.assertEqual(r['tool_calls'],['get_selected_telemetry'])
        self.assertEqual(len(requests),2);self.assertFalse(requests[0]['store'])
        self.assertIn('MOCK ONLY',r['text'])
    def test_unknown_model_tool_never_runs(self):
        def transport(*_):return {'output':[dict(type='function_call',name='run_shell',arguments='{}',call_id='bad')]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):analyze({},key='test-only',model='mock',database=Path(tmp)/'budget.db',transport=transport)
    def test_real_interruption_evidence_and_report(self):
        source=ROOT/'results/reports/viewer-20261028-231556.csv'
        if not source.exists():self.skipTest('Local real telemetry not present')
        d=summarize_csv(source,40)
        self.assertEqual(d['measured']['frames'],517)
        self.assertAlmostEqual(d['measured']['maximum_receive_gap_s'],4.781,places=2)
        self.assertIn('frame_gap',d['measured']['tracking_resets'])
        self.assertTrue(any('receipt gap' in s for s in d['local_rule_observations']))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report';r=write_report(out,d)
            self.assertEqual(r['ai']['kind'],'not_run')
            self.assertTrue((out/'pose-statuses.svg').exists())
            with self.assertRaises(FileExistsError):write_report(out,d)
    def test_read_scope_and_invalid_limits(self):
        with self.assertRaises(ValueError):bounded_path(ROOT/'README.md',[ROOT/'data'])
        with self.assertRaises(ValueError):reserve_request('unused.db',0)
        with self.assertRaises(ValueError):analyze({},key='test',model='mock',output_tokens=10000)

    def test_local_scene_does_not_need_network(self):
        from laptop.ai_assistant import local_scene
        source=ROOT/'data/calibration/session-20261028-211233/view-0012.png'
        if not source.exists():self.skipTest('Selected local image not present')
        r=local_scene(source)
        self.assertEqual(r['kind'],'local_image_measurements_not_AI')
        self.assertGreater(r['shi_tomasi_features'],0)
    def test_incomplete_provider_response_not_accepted(self):
        def transport(*_):return {'status':'incomplete','output':[{'type':'message','content':[{'type':'output_text','text':'truncated'}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):analyze({},key='test-only',model='mock',database=Path(tmp)/'budget.db',transport=transport)

    def test_provider_failure_is_sanitized(self):
        import io
        import urllib.error
        from unittest.mock import patch
        from laptop.ai_assistant import api_post,APIRequestFailure
        body=b'{"error":{"code":"credit_balance_exhausted","message":"private provider body"}}'
        error=urllib.error.HTTPError('https://api.openai.com/v1/responses',429,'quota',{},io.BytesIO(body))
        with patch('urllib.request.urlopen',side_effect=error):
            with self.assertRaises(APIRequestFailure) as caught:api_post({},'test-only')
        self.assertEqual(caught.exception.code,'credit_balance_exhausted')
        self.assertNotIn('private provider body',str(caught.exception))
