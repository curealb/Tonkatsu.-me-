"""Validated, data-driven scene intervals. Timings are editable in timeline.json."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    scene: str
    title: str
    thought: str
    expression: str
    params: dict


class Timeline:
    def __init__(self, path: Path | None = None):
        raw = json.loads((path or ROOT / "timeline.json").read_text(encoding="utf-8"))
        self.duration = float(raw["duration"])
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError("duration must be finite and positive")
        self.title = raw["title"]
        self.cues = tuple(Cue(float(c["start"]), float(c["end"]), c["scene"],
                              c["title"], c["thought"], c["expression"], c.get("params", {}))
                          for c in raw["cues"])
        previous = 0.0
        for cue in self.cues:
            if not (math.isfinite(cue.start) and math.isfinite(cue.end)):
                raise ValueError("Non-finite scene interval")
            if abs(cue.start - previous) > 1e-6 or cue.end <= cue.start:
                raise ValueError(f"Non-contiguous or empty scene: {cue.title}")
            previous = cue.end
        if not self.cues or abs(previous - self.duration) > 1e-6:
            raise ValueError("Timeline must cover the complete duration")
        self.starts = [c.start for c in self.cues]

    def at(self, time: float) -> Cue:
        if not math.isfinite(time):
            raise ValueError("Playback time must be finite")
        i = bisect_right(self.starts, max(0, min(time, self.duration))) - 1
        return self.cues[max(0, i)]

    def metadata(self) -> dict:
        return {"title": self.title, "duration": self.duration,
                "cues": [{"start": c.start, "end": c.end, "title": c.title,
                          "scene": c.scene} for c in self.cues]}
