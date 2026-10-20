"""Silent preview clock. Real audio backends must provide their own playback time."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class State:
    position: float
    duration: float
    paused: bool


class DemoClock:
    def __init__(self, duration: float, now: Callable[[], float] = time.monotonic):
        self.duration = duration
        self._now = now
        self._base = 0.0
        self._anchor = now()
        self._paused = True
        self.error = ""

    def state(self) -> State:
        position = self._base if self._paused else self._base + self._now() - self._anchor
        if position >= self.duration:
            self._base, self._paused = self.duration, True
        return State(min(self.duration, position), self.duration, self._paused)

    def pause(self, paused: bool) -> None:
        self._base = self.state().position
        self._anchor = self._now()
        self._paused = paused

    def seek(self, position: float) -> None:
        if not math.isfinite(position):
            raise ValueError("Seek must be finite")
        self._base = max(0.0, min(self.duration, position))
        self._anchor = self._now()

    def volume(self, value: float) -> None:
        pass

    def close(self) -> None:
        pass
