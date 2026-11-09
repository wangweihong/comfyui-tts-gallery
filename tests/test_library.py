import concurrent.futures
import json
import os
import tempfile
import unittest
import wave
from pathlib import Path

from support import ROOT, plugin, catalog, nodes, workflows, audio


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.lib = catalog.Library(user=self.root / 'user')
        self.sample = self.root / 'sample.wav'
        import numpy as np
        pcm = (np.sin(np.arange(24000) * .08) * 10000).astype('<i2')
        with wave.open(str(self.sample), 'wb') as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(24000); out.writeframes(pcm.tobytes())
        self.meta = {'name_zh': '测试声音', 'reference_text': '这是准确的逐字稿。', 'language': 'zh', 'tags': ['温暖', '温暖']}

    def tearDown(self):
        self.tmp.cleanup()

    def test_entrypoint_and_actual_audio_outputs(self):
        self.assertEqual(set(plugin.NODE_CLASS_MAPPINGS), {'TTSExampleGallery', 'TTSVoiceGallery'})
        old = nodes.library; nodes.library = self.lib
        try:
            result = nodes.TTSVoiceGallery().load_reference('huola-dachu')
            self.assertEqual(result[0]['waveform'].shape[0:2], (1, 1))
            self.assertEqual(result[0]['sample_rate'], 24000)
            self.assertIn('火辣大厨', result[1])
            sample = nodes.TTSExampleGallery().load_reference('breeze-design-zh-female', 'en')
            self.assertEqual(len(sample), 5)
            self.assertIn('generation', json.loads(sample[3]))
            self.assertIsInstance(nodes.TTSVoiceGallery.VALIDATE_INPUTS('missing'), str)
            with self.assertRaises(ValueError): nodes.TTSVoiceGallery().load_reference('huola-dachu', 'fr')
        finally: nodes.library = old

    def test_import_original_preview_edit_delete_and_stale_revision(self):
        row = self.lib.add(self.sample, '../../voice.wav', self.meta)
        self.assertEqual(self.lib.asset(row['id']).read_bytes(), self.sample.read_bytes())
        self.assertEqual(row['original_filename'], 'voice.wav')
        self.assertEqual(row['tags'], ['温暖'])
        self.assertTrue(self.lib.asset(row['id'], 'preview').read_bytes().startswith(b'RIFF'))
        before = self.lib.fingerprint(row['id'])
        edited = self.lib.update(row['id'], {**self.meta, 'reference_text': '修改后的逐字稿。', 'revision': 1})
        self.assertEqual(edited['revision'], 2)
        self.assertNotEqual(before, self.lib.fingerprint(row['id']))
        with self.assertRaises(catalog.LibraryError) as error: self.lib.update(row['id'], {**self.meta, 'revision': 1})
        self.assertEqual(error.exception.status, 409)
        self.lib.delete(row['id'], 2)
        self.assertFalse((self.lib.user / row['audio']).exists())
        with self.assertRaises(catalog.LibraryError): self.lib.record(row['id'])
        self.assertEqual(self.lib.catalog()['revision'], 3)

    def test_builtin_read_only_and_type_validation(self):
        with self.assertRaises(catalog.LibraryError): self.lib.update('huola-dachu', {**self.meta, 'revision': 1})
        with self.assertRaises(catalog.LibraryError): self.lib.delete('huola-dachu', 1)
        with self.assertRaises(catalog.LibraryError): self.lib.record('huola-dachu', 'example')
        for invalid in ['../../etc/passwd', '', '/etc/passwd', 'x/y']:
            with self.assertRaises(catalog.LibraryError): self.lib.record(invalid)
        with self.assertRaises(catalog.LibraryError): self.lib.asset('huola-dachu', '../original')

    def test_corruption_limits_and_symlinks(self):
        corrupt = self.root / 'bad.wav'; corrupt.write_bytes(b'not an audio file')
        with self.assertRaises(ValueError): self.lib.add(corrupt, 'bad.wav', self.meta)
        with self.assertRaises(catalog.LibraryError): self.lib.add(self.sample, 'bad.exe', self.meta)
        with self.assertRaises(catalog.LibraryError): self.lib.add(self.sample, 'a.wav', {**self.meta, 'reference_text': ''})
        with self.assertRaises(catalog.LibraryError): self.lib.add(self.sample, 'a.wav', {**self.meta, 'tags': 'string'})
        target = self.root / 'outside.wav'; target.write_bytes(self.sample.read_bytes())
        self.lib.user.mkdir(); (self.lib.user / 'audio').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(catalog.LibraryError): self.lib.add(self.sample, 'a.wav', self.meta)
        with self.assertRaises(catalog.LibraryError): catalog.checked_file(self.root, '../outside.wav')
        link = self.root / 'link.wav'; link.symlink_to(target)
        with self.assertRaises(catalog.LibraryError): catalog.checked_file(self.root, 'link.wav')
        with self.assertRaises(ValueError): audio.decode(self.sample, max_seconds=.5)

    def test_concurrent_independent_instances_no_lost_updates(self):
        def add(index):
            lib = catalog.Library(user=self.lib.user)
            return lib.add(self.sample, 'test.wav', {**self.meta, 'name_zh': str(index)})
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(add, range(12)))
        index = self.lib._index()
        self.assertEqual(index['revision'], 12)
        self.assertEqual(len(index['records']), 12)
        self.assertEqual(len({r['id'] for r in rows}), 12)
        # A new plugin instance still sees the user library.
        self.assertEqual(len(catalog.Library(user=self.lib.user)._index()['records']), 12)

    def test_all_bundled_assets_hash_and_decode(self):
        rows = self.lib.catalog()['records']
        self.assertEqual({r['id'] for r in rows if r['kind']=='voice'}, {'huola-dachu','warm-female-zh'})
        self.assertEqual({r.get('model') for r in rows if r['kind'] == 'example'}, {'breeze', 'drama3'})
        for row in rows:
            with self.subTest(id=row['id']):
                self.assertTrue(row['available'])
                self.assertEqual(catalog.sha256(self.lib.asset(row['id'])), row['sha256'])
                samples, rate = audio.decode(self.lib.asset(row['id']))
                self.assertAlmostEqual(samples.shape[1] / rate, row['duration'], places=3)
                self.assertEqual(len(row['waveform']), 48)

    def test_all_workflows_have_exact_settings_and_valid_links(self):
        schema = json.loads((ROOT / 'library' / 'schemas.json').read_text())
        for row in self.lib.catalog()['records']:
            models = ['breeze', 'drama3'] if row['kind'] == 'voice' else [None]
            for model in models:
                with self.subTest(id=row['id'], model=model):
                    api = workflows.export(row['id'], model, 'api', lib=self.lib)
                    graph = workflows.export(row['id'], model, lib=self.lib)
                    self.assertEqual(api['1']['inputs']['value'], row.get('text', api['1']['inputs']['value']))
                    ids = {node['id']: node for node in graph['nodes']}
                    for link in graph['links']:
                        number, origin, slot, target, target_slot, typ = link
                        self.assertEqual(ids[target]['inputs'][target_slot]['link'], number)
                        self.assertIn(number, ids[origin]['outputs'][slot]['links'])
                        self.assertEqual(ids[origin]['outputs'][slot]['type'], typ)
                    self.assertTrue(all(' - ' in n['title'] for n in graph['nodes']))
                    self.assertTrue(api['30']['inputs']['filename_prefix'].startswith('audio/'))
                    if row['kind'] == 'example':
                        controls = row['parameters']['generation']
                        self.assertEqual(api['2']['inputs']['value'], controls['seed'])
                        self.assertEqual(api['3']['inputs']['value'], controls['temperature'])
                        for key, value in controls.items():
                            if key not in ('seed', 'temperature', 'cfg_scale'):
                                self.assertEqual(api['20']['inputs'][key], value)
                    for entry in api.values():
                        required = schema[entry['class_type']]['input']['required']
                        self.assertEqual(set(required), set(entry['inputs']))
        user = self.lib.add(self.sample, 'user.wav', self.meta)
        exported = workflows.export(user['id'], 'drama3', 'api', lib=self.lib)
        self.assertEqual(exported['4']['inputs']['reference_id'], user['id'])


if __name__ == '__main__': unittest.main()
