"""A small terminal-cell canvas shared by terminal and browser renderers.

No terminal escape sequences or user-provided HTML are accepted as cell content.
Wide glyphs occupy two cells; the second cell is an explicit continuation.
"""
from __future__ import annotations

import math
import unicodedata

PALETTE = {
    "dim": "#597086", "ink": "#a6bfd6", "blue": "#76bfff",
    "gold": "#ffc879", "white": "#eef5ff", "pink": "#ffa8c6",
    "red": "#ff7e8a", "darkgold": "#997044",
}
ANSI = {name: f"\033[38;2;{int(value[1:3],16)};{int(value[3:5],16)};{int(value[5:7],16)}m"
        for name, value in PALETTE.items()}


def cell_width(char: str) -> int:
    if unicodedata.category(char).startswith("C") or unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def text_width(text: str) -> int:
    return sum(cell_width(c) for c in text)


def fit(text: str, columns: int) -> str:
    result = []
    used = 0
    for char in str(text):
        width = cell_width(char)
        if not width:
            continue
        if used + width > max(0, columns):
            break
        result.append(char)
        used += width
    return "".join(result)


class Canvas:
    def __init__(self, width: int, height: int):
        if not 1 <= width <= 240 or not 1 <= height <= 85:
            raise ValueError("Canvas dimensions must be within 1..240 × 1..85")
        self.width, self.height = width, height
        self.cells = [[(" ", "dim") for _ in range(width)] for _ in range(height)]
        self.clip: tuple[int, int] | None = None

    def _erase(self, x: int, y: int) -> None:
        char, _ = self.cells[y][x]
        if char == "" and x:
            self.cells[y][x - 1] = (" ", "dim")
        elif cell_width(char) == 2 and x + 1 < self.width:
            self.cells[y][x + 1] = (" ", "dim")
        self.cells[y][x] = (" ", "dim")

    def text(self, x: float, y: float, text: str, style: str = "ink") -> None:
        x, y = round(x), round(y)
        if style not in PALETTE:
            raise ValueError(f"Unknown style: {style}")
        if not 0 <= y < self.height or (self.clip and not self.clip[0] <= y <= self.clip[1]):
            return
        for char in str(text):
            n = cell_width(char)
            if not n:
                continue
            if x >= 0 and x + n <= self.width:
                for xx in range(x, x + n):
                    self._erase(xx, y)
                self.cells[y][x] = (char, style)
                if n == 2:
                    self.cells[y][x + 1] = ("", style)
            x += n

    def center(self, y: float, text: str, style: str = "ink") -> None:
        text = fit(text, self.width - 2)
        self.text((self.width - text_width(text)) // 2, y, text, style)

    def line(self, x0: float, y0: float, x1: float, y1: float,
             char: str = ".", style: str = "dim") -> None:
        steps = max(1, math.ceil(max(abs(x1 - x0), abs(y1 - y0))))
        for step in range(steps + 1):
            u = step / steps
            self.text(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, char, style)

    def box(self, x: int, y: int, width: int, height: int, style: str = "dim") -> None:
        if width < 2 or height < 2:
            return
        self.text(x, y, "+" + "-" * (width - 2) + "+", style)
        self.text(x, y + height - 1, "+" + "-" * (width - 2) + "+", style)
        for yy in range(y + 1, y + height - 1):
            self.text(x, yy, "|", style)
            self.text(x + width - 1, yy, "|", style)

    def sprite(self, x: float, y: float, rows: list[str], style: str = "blue",
               reveal: float = 1.0) -> None:
        count = int(len(rows) * max(0, min(1, reveal)))
        for dy, row in enumerate(rows[:count]):
            for dx, char in enumerate(row):
                if char != " ":
                    self.text(x + dx, y + dy, char, style)

    def plain(self) -> str:
        return "\n".join("".join(char for char, _ in row) for row in self.cells)

    def runs(self) -> list[list[list[str]]]:
        """Return JSON-friendly, HTML-free [style, text] spans for each row."""
        rows = []
        for row in self.cells:
            runs: list[list[str]] = []
            for char, style in row:
                if not char:
                    continue
                if runs and runs[-1][0] == style:
                    runs[-1][1] += char
                else:
                    runs.append([style, char])
            rows.append(runs)
        return rows

    def ansi(self) -> str:
        parts = []
        for y, row in enumerate(self.runs(), 1):
            parts.append(f"\033[{y};1H")
            parts.extend(ANSI[style] + text for style, text in row)
        parts.append("\033[0m")
        return "".join(parts)
