from __future__ import annotations
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tonkatsu.canvas import Canvas, text_width, fit
from tonkatsu.clock import DemoClock
from tonkatsu.film import Film
from tonkatsu.timeline import Timeline, ROOT
from tonkatsu.art import Artwork


class CanvasTests(unittest.TestCase):
    def test_chinese_cell_width(self):
        self.assertEqual(text_width('炸猪排 A'),8)
        self.assertEqual(fit('炸猪排',5),'炸猪')

    def test_wide_glyph_overwrite_is_well_formed(self):
        c=Canvas(8,2)
        c.text(0,0,'炸猪')
        c.text(1,0,'a')
        self.assertEqual(c.plain().splitlines()[0],' a猪    ')
        self.assertEqual(text_width(c.plain().splitlines()[0]),8)
        c.text(2,0,'b')
        self.assertEqual(c.plain().splitlines()[0],' ab     ')

    def test_control_sequences_cannot_enter_cells(self):
        c=Canvas(12,1)
        c.text(0,0,'abc\x1b\n\t')
        self.assertNotIn('\x1b',c.plain())
        self.assertEqual(len(c.plain().splitlines()),1)

    def test_json_runs_reconstruct_plain_text(self):
        c=Canvas(10,2)
        c.text(0,0,'猪排!','gold')
        self.assertEqual('\n'.join(''.join(r[1] for r in row) for row in c.runs()),c.plain())

    def test_clipping(self):
        c=Canvas(10,5); c.clip=(1,2)
        c.text(0,0,'hidden'); c.text(0,1,'visible')
        self.assertNotIn('hidden',c.plain()); self.assertIn('visible',c.plain())

    def test_invalid_sizes(self):
        for w,h in [(0,1),(1,0),(241,2),(2,86)]:
            with self.assertRaises(ValueError): Canvas(w,h)


class FilmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.film=Film()

    def test_complete_contiguous_timeline(self):
        t=self.film.timeline
        self.assertEqual(len(t.cues),31)
        self.assertEqual(t.cues[0].start,0)
        self.assertEqual(t.cues[-1].end,t.duration)
        for a,b in zip(t.cues,t.cues[1:]): self.assertEqual(a.end,b.start)

    def test_every_boundary_and_midpoint_renders_at_all_supported_sizes(self):
        points={0,self.film.timeline.duration,205.811}
        for cue in self.film.timeline.cues:
            points.update((cue.start, max(0,cue.start-.001),cue.end-.001,(cue.start+cue.end)/2))
        for w,h in [(64,24),(80,28),(120,42),(180,60)]:
            for t in sorted(points):
                c=self.film.render(t,w,h)
                rows=c.plain().splitlines()
                self.assertEqual(len(rows),h,(w,h,t))
                self.assertTrue(all(text_width(row)==w for row in rows),(w,h,t))

    def test_random_access_is_deterministic(self):
        first=self.film.render(180.3).plain()
        for t in (69,113,0,212,24): self.film.render(t)
        self.assertEqual(first,self.film.render(180.3).plain())

    def test_reduced_motion_is_deterministic(self):
        self.assertEqual(self.film.render(133,reduced=True).plain(),self.film.render(133,reduced=True).plain())

    def test_offset_changes_selected_scene(self):
        self.assertIn('创建炸猪排',self.film.render(0,offset=6).plain())

    def test_small_terminal_does_not_crash(self):
        self.assertIn('resize',self.film.render(69,50,20).plain())

    def test_non_finite_input_is_rejected(self):
        for t in (math.nan,math.inf,-math.inf):
            with self.assertRaises(ValueError): self.film.render(t)

    def test_invalid_timeline_rejected(self):
        data=json.loads((ROOT/'timeline.json').read_text(encoding='utf-8'))
        data['cues'][1]['start']+=.1
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'timeline.json';p.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError): Timeline(p)

    def test_placeholder_status_is_explicit(self):
        self.assertEqual(self.film.art.status['temari_calm'],'placeholder')
        self.assertIn('ART: PLACEHOLDER',self.film.render(69).plain())

    def test_ready_food_slot_replaces_procedural_food(self):
        film=Film()
        film.art.sprites['tonkatsu_slice']=['ART_REPLACEMENT']
        film.art.status['tonkatsu_slice']='ready'
        self.assertIn('ART_REPLACEMENT',film.render(35).plain())

    def test_missing_art_has_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            art=Artwork(Path(td));c=Canvas(50,10)
            art.draw(c,'temari_calm',0,0)
            self.assertIn('ART PENDING',c.plain())

    def test_snapshot_cli_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as td:
            result=subprocess.run([sys.executable,str(ROOT/'player.py'),'--snapshot','69','--plain'],
                                  cwd=td,capture_output=True,encoding='utf-8',check=True)
        self.assertIn('Tonkatsu.(me)',result.stdout)
        self.assertNotIn('\x1b',result.stdout)

    def test_cli_rejects_nan(self):
        result=subprocess.run([sys.executable,str(ROOT/'player.py'),'--snapshot','nan'],capture_output=True)
        self.assertNotEqual(result.returncode,0)


class ClockTests(unittest.TestCase):
    def test_pause_resume_seek_and_end(self):
        now=[100.0];clock=DemoClock(212,lambda:now[0])
        self.assertEqual(clock.state().position,0)
        clock.pause(False);now[0]+=2
        self.assertEqual(clock.state().position,2)
        clock.pause(True);now[0]+=10
        self.assertEqual(clock.state().position,2)
        clock.seek(100);clock.pause(False);now[0]+=3
        self.assertEqual(clock.state().position,103)
        now[0]+=500
        self.assertEqual(clock.state().position,212)
        self.assertTrue(clock.state().paused)

    def test_seek_clamps_and_rejects_nan(self):
        c=DemoClock(212)
        c.seek(-5);self.assertEqual(c.state().position,0)
        c.seek(999);self.assertEqual(c.state().position,212)
        with self.assertRaises(ValueError): c.seek(math.nan)
