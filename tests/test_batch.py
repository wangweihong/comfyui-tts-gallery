import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import ROOT
import sys
sys.path.insert(0,str(ROOT/'scripts'))
import drama3_batch as batch
from drama3_presets import presets


class BatchTests(unittest.TestCase):
    def test_enqueue_always_appends_and_resumes_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory); manifest=state/'batch.json'; recipes=presets()[:2]; calls=[]
            class Factory:
                def prompt_for(self, row): return {'1':{'class_type':'Fixture','inputs':{}}},'drama3','tags'
            def api(path,data=None):
                calls.append((path,data));return {'prompt_id':f'job-{len(calls)}','number':1000+len(calls)}
            with patch.multiple(batch,STATE=state,MANIFEST=manifest),patch.object(batch,'presets',return_value=recipes),patch.object(batch,'load_factory',return_value=Factory()),patch.object(batch,'api',side_effect=api):
                batch.enqueue(); batch.enqueue()
            self.assertEqual(len(calls),2)
            self.assertTrue(all(path=='/prompt' and data['front'] is False for path,data in calls))
            self.assertEqual(json.loads(manifest.read_text())['ids'],[row['id'] for row in recipes])

    def test_watcher_defers_deployment_until_queue_is_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory);manifest=state/'batch.json';identifier='drama3-extra-test'
            (state/(identifier+'.json')).write_text(json.dumps({'id':identifier,'status':'completed','transcript_review':{'status':'asr_checked'}}))
            manifest.write_text(json.dumps({'ids':[identifier],'total':1}))
            events=[]; remaining=iter([3,0,0])
            def api(path,data=None):
                self.assertEqual(path,'/prompt'); self.assertIsNone(data)
                value=next(remaining);events.append(('queue',value));return {'exec_info':{'queue_remaining':value}}
            def deploy():events.append(('install',0))
            with patch.multiple(batch,STATE=state,MANIFEST=manifest),patch.object(batch,'api',side_effect=api),patch.object(batch,'install_catalog',side_effect=deploy),patch.object(batch.time,'sleep'),patch.object(batch.subprocess,'run') as restart:
                batch.watch()
            self.assertLess(events.index(('queue',0)),events.index(('install',0)))
            restart.assert_called_once_with(['docker','restart',batch.CONTAINER],check=True)
            self.assertEqual(json.loads(manifest.read_text())['stage'],'complete')
