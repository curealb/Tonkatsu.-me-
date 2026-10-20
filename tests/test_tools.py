from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tonkatsu.timeline import ROOT
from tools.import_art import convert


class ToolTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('PIL'),'optional Pillow is not installed')
    def test_image_converter_respects_alpha_and_aspect(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'artist.png'
            img=Image.new('RGBA',(100,100),(255,255,255,255))
            for x in range(20):
                for y in range(100): img.putpixel((x,y),(255,255,255,0))
            img.save(p)
            rows=convert(p,20).splitlines()
            self.assertEqual(len(rows),10)
            self.assertTrue(all(r.startswith('   ') for r in rows))
            self.assertTrue(any('@' in r for r in rows))

    def test_publish_dry_run_has_no_git_side_effect(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/publish_github.py'),'--dry-run'],
                              capture_output=True,encoding='utf-8',check=True)
        self.assertIn('--private',result.stdout)
        self.assertIn('curealb/tonkatsu-me',result.stdout)
        self.assertIn('No GitHub repository has been created',result.stdout)
