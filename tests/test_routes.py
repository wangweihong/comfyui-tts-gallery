import json
import tempfile
import unittest
from pathlib import Path
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer
from support import ROOT, catalog, routes


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = catalog.Library(user=Path(self.tmp.name) / 'user')
        table = web.RouteTableDef(); routes.register_routes(table, self.lib)
        app = web.Application(client_max_size=30 * 1024 * 1024); app.add_routes(table)
        self.client = TestClient(TestServer(app)); await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close(); self.tmp.cleanup()

    async def upload(self, filename='voice.flac', content=None, origin=None):
        form = FormData()
        form.add_field('audio', content if content is not None else (ROOT/'library/audio/huola-dachu.flac').read_bytes(), filename=filename)
        form.add_field('metadata', json.dumps({'name_zh': '测试音色', 'reference_text': '大家好，我是火辣大厨。', 'language': 'zh'}))
        return await self.client.post('/tts_gallery/voices', data=form, headers={'Origin': origin} if origin else {})

    async def test_gallery_catalog_audio_range_and_workflow(self):
        for path in ['/gallery', '/static/gallery.css', '/static/gallery.mjs', '/static/core.mjs', '/catalog']:
            response = await self.client.get('/tts_gallery' + path); self.assertEqual(response.status, 200, path); await response.read()
        response = await self.client.get('/tts_gallery/audio/huola-dachu/preview', headers={'Range': 'bytes=0-15'})
        self.assertEqual(response.status, 206); self.assertEqual(len(await response.read()), 16)
        response = await self.client.get('/tts_gallery/workflow/huola-dachu?model=drama3')
        graph = await response.json(); self.assertEqual(response.status, 200)
        self.assertIn('Drama3EncodeVoice', {n['type'] for n in graph['nodes']})
        response = await self.client.get('/tts_gallery/workflow/huola-dachu?download=1')
        self.assertIn('attachment', response.headers['Content-Disposition']); await response.read()
        response = await self.client.get('/tts_gallery/workflow/huola-dachu?model=bad')
        self.assertEqual(response.status, 400)
        response = await self.client.get('/tts_gallery/audio/missing/original')
        self.assertEqual(response.status, 404)
        response = await self.client.get('/tts_gallery/static/catalog.py')
        self.assertEqual(response.status, 404)

    async def test_crud_and_cross_origin(self):
        response = await self.upload(origin='https://evil.example'); self.assertEqual(response.status, 403)
        response = await self.upload(); self.assertEqual(response.status, 201)
        row = (await response.json())['record']; path='/tts_gallery/voices/'+row['id']
        response = await self.client.patch(path, json={**row, 'reference_text': '修改逐字稿。'})
        self.assertEqual(response.status, 200); edited=(await response.json())['record']
        response = await self.client.patch(path, json=row); self.assertEqual(response.status, 409)
        response = await self.client.delete(path, json={'revision': edited['revision']}, headers={'Origin':'https://evil.example'})
        self.assertEqual(response.status, 403)
        response = await self.client.delete(path, json={'revision': edited['revision']}); self.assertEqual(response.status, 200)
        self.assertFalse((self.lib.user / row['audio']).exists())
        response = await self.client.delete('/tts_gallery/voices/huola-dachu', json={'revision':1}); self.assertEqual(response.status, 404)

    async def test_broken_upload_json_and_wrong_content_type(self):
        response = await self.upload(content=b'broken'); self.assertEqual(response.status, 400)
        response = await self.upload(filename='voice.exe'); self.assertEqual(response.status, 400)
        response = await self.client.patch('/tts_gallery/voices/u-test', data='{}'); self.assertEqual(response.status, 400)
        response = await self.client.patch('/tts_gallery/voices/u-test', data='{', headers={'Content-Type':'application/json'}); self.assertEqual(response.status, 400)
        self.assertEqual(self.lib._index()['records'], [])


if __name__ == '__main__': unittest.main()
