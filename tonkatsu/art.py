"""Load small ASCII art assets once; missing artwork uses a labelled fallback."""
from __future__ import annotations

import json
from pathlib import Path
from .canvas import Canvas
from .timeline import ROOT


class Artwork:
    def __init__(self, directory: Path | None = None):
        directory = directory or ROOT / "assets" / "ascii"
        self.sprites: dict[str, list[str]] = {}
        self.status: dict[str, str] = {}
        manifest_path = directory.parent / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        for name in ("temari_calm", "temari_tempted", "temari_bite", "temari_happy",
                     "tonkatsu_hero", "tonkatsu_slice"):
            path = directory / f"{name}.txt"
            if path.is_file():
                rows = path.read_text(encoding="utf-8").splitlines()
                # Converter outputs ASCII only; reject control sequences and oversized art.
                if len(rows) > 60 or any(len(r) > 100 or any(not 32 <= ord(c) <= 126 for c in r) for r in rows):
                    raise ValueError(f"Invalid ASCII asset: {path.name}")
                self.sprites[name] = rows
            self.status[name] = manifest.get(name, {}).get("status", "placeholder")

    def draw(self, canvas: Canvas, name: str, x: float, y: float,
             style: str = "blue", width: int | None = None, height: int | None = None) -> None:
        rows = self.sprites.get(name, ["[ ART PENDING ]"])
        source_w = max((len(row) for row in rows), default=1)
        source_h = max(1, len(rows))
        # Nearest-cell fitting preserves the aspect of the converted text asset.
        ratio = min(1.0, (width or source_w) / source_w, (height or source_h) / source_h)
        if ratio < 1:
            target_w, target_h = max(1, int(source_w * ratio)), max(1, int(source_h * ratio))
            rows = ["".join(rows[min(source_h - 1, int(yy / ratio))].ljust(source_w)
                            [min(source_w - 1, int(xx / ratio))] for xx in range(target_w))
                    for yy in range(target_h)]
        canvas.sprite(x, y, rows, style)
