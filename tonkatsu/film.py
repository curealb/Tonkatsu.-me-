"""Compose one scene, character thoughts, and transport status into a frame."""
from __future__ import annotations

import math
from .art import Artwork
from .canvas import Canvas, fit
from .primitives import clamp, noise
from .scenes import SCENES, Stage
from .timeline import Timeline


class Film:
    def __init__(self):
        self.timeline = Timeline()
        self.art = Artwork()
        unknown = {c.scene for c in self.timeline.cues} - SCENES.keys()
        if unknown:
            raise ValueError(f"Unknown scene renderers: {sorted(unknown)}")

    def render(self, time: float, width: int = 120, height: int = 42,
               reduced: bool = False, pulse: float = 0.0,
               paused: bool = False, offset: float = 0.0) -> Canvas:
        if not all(math.isfinite(v) for v in (time, pulse, offset)):
            raise ValueError("Non-finite render parameter")
        t = clamp(time + offset, 0.0, self.timeline.duration)
        c = Canvas(width, height)
        if width < 64 or height < 24:
            c.center(max(0, height//2-1), "Tonkatsu.(me)", "gold")
            c.center(height//2+1, "Please resize to 64 x 24 or larger", "ink")
            return c
        cue = self.timeline.at(t)
        c.clip = (4, height-7)
        stage = Stage(c, self.art, cue, t, clamp(pulse), reduced)
        SCENES[cue.scene](stage)
        # Localised, low-amplitude interference only; no full-screen flashes.
        if not reduced and 110.9 <= t < 177.246:
            count = 1 + int((t-110.9)/25)
            for i in range(count):
                x = 2+int(noise(int(t*4)+i*43)*(width-18))
                y = 5+int(noise(int(t*3)+i*61)*(height-14))
                c.text(x, y, "...tonkatsu...", "darkgold")
        c.clip = None
        c.text(2, 0, "Tonkatsu.(me)", "gold")
        status = "PAUSED" if paused else "PREVIEW"
        clock = f"{int(t)//60:02}:{t%60:04.1f} / 03:31.9  {status}"
        c.text(width-len(clock)-2, 0, clock, "ink")
        c.text(2, 1, "="*(width-4), "dim")
        c.text(2, 2, fit("TEMARI // " + cue.title, width-4), "blue")
        c.text(2, 3, "-"*(width-4), "dim")
        c.text(2, height-6, "-"*(width-4), "dim")
        c.center(height-5, cue.thought, "white")
        c.center(height-3, "FAN-CREATED INNER MONOLOGUE / NOT ORIGINAL LYRICS", "dim")
        filled = min(width-4, round((width-4)*t/self.timeline.duration))
        c.text(2, height-2, "="*filled + "."*(width-4-filled), "gold")
        c.center(height-1, "SPACE pause | arrows seek | R restart | M reduced motion | Q exit", "dim")
        return c
