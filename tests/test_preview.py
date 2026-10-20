from __future__ import annotations
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from preview import PreviewServer


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory()
        cls.audio=Path(cls.folder.name)/'test.wav'
        cls.audio.write_bytes(b'0123456789abcdef')
        cls.server=PreviewServer(('127.0.0.1',0),audio=cls.audio)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2);cls.folder.cleanup()

    def request(self,path,method='GET',headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            conn.request(method,path,headers=headers or {})
            response=conn.getresponse()
            return response.status,dict(response.getheaders()),response.read()
        finally: conn.close()

    def test_metadata(self):
        code,headers,body=self.request('/api/info')
        self.assertEqual(code,200);self.assertEqual(len(json.loads(body)['cues']),31)
        self.assertEqual(headers['Cache-Control'],'no-store')

    def test_frame(self):
        code,_,body=self.request('/api/frame?t=151&w=100&h=36')
        self.assertEqual(code,200);self.assertEqual(len(json.loads(body)['rows']),36)

    def test_invalid_parameters(self):
        for suffix in ('?t=nan','?w=100000','?h=-1','?offset=100','?pulse=inf'):
            self.assertEqual(self.request('/api/frame'+suffix)[0],400)

    def test_private_files_and_traversal_not_served(self):
        for path in ('/../README.md','/assets/manifest.json','/.git/config','/%2e%2e/README.md'):
            self.assertEqual(self.request(path)[0],404)

    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(self.request('/api/info',headers={'Host':'attacker.invalid'})[0],403)

    def test_post_not_supported(self):
        self.assertEqual(self.request('/upload','POST')[0],501)

    def test_static_web_assets(self):
        for path in ('/','/app.js','/style.css'):
            code,headers,body=self.request(path)
            self.assertEqual(code,200);self.assertTrue(body)
            self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])

    def test_audio_range(self):
        code,headers,body=self.request('/audio',headers={'Range':'bytes=3-7'})
        self.assertEqual(code,206);self.assertEqual(body,b'34567')
        self.assertEqual(headers['Content-Range'],'bytes 3-7/16')

    def test_suffix_range(self):
        code,_,body=self.request('/audio',headers={'Range':'bytes=-4'})
        self.assertEqual(code,206);self.assertEqual(body,b'cdef')

    def test_invalid_range(self):
        self.assertEqual(self.request('/audio',headers={'Range':'bytes=999-1000'})[0],416)

    def test_head(self):
        code,headers,body=self.request('/audio','HEAD')
        self.assertEqual(code,200);self.assertEqual(headers['Content-Length'],'16');self.assertEqual(body,b'')
