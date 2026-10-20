"""Original procedural food, steam, and typography primitives."""
from __future__ import annotations

import math
from .canvas import Canvas


def clamp(n: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(upper, max(lower, n))


def noise(seed: int) -> float:
    """Stateless integer mixing: seeking never depends on the previous frame."""
    x = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    x ^= x >> 11
    return (x & 65535) / 65535


def ellipse(c: Canvas, x: float, y: float, rx: float, ry: float,
            char: str = ".", style: str = "dim") -> None:
    for step in range(max(40, int(rx * 8))):
        a = step / max(40, int(rx * 8)) * math.tau
        c.text(x + math.cos(a) * rx, y + math.sin(a) * ry, char, style)


def cutlet(c: Canvas, x: float, y: float, rx: int = 17, ry: int = 4,
           t: float = 0, bite: int = 0, sliced: bool = False, reveal: float = 1.0,
           plate: bool = True) -> None:
    """Perspective cutlet with panko texture, plate, cuts, and disappearing bites."""
    if plate:
        ellipse(c, x, y + 2, rx + 5, ry + 2, "_", "ink")
    for dy in range(-ry, ry + 2):
        for dx in range(-rx, rx + 1):
            distance = (dx / max(1, rx)) ** 2 + (dy / max(1, ry)) ** 2
            if distance > 1 or (dx + rx) / max(1, 2 * rx) > reveal:
                continue
            if bite and dx > rx * (1 - bite / 3) and dy < ry * .65:
                continue
            if sliced and dx % max(3, rx // 3) == 0:
                c.text(x + dx, y + dy, "/", "white")
            else:
                n = noise((dx + 50) * 131 + (dy + 50) * 47)
                char = "#" if distance > .79 else ":*%#"[int(n * 3.999)]
                style = "darkgold" if distance > .87 else "white" if n > .91 else "gold"
                c.text(x + dx, y + dy, char, style)
    if bite:
        for i in range(9):
            phase = (t * .8 + noise(i * 7)) % 1
            c.text(x + rx + noise(i * 13) * 8, y + phase * (ry + 4), ".", "gold")


def steam(c: Canvas, x: float, y: float, t: float, strength: float = 1,
          reduced: bool = False) -> None:
    for k in range(3):
        for j in range(5):
            sway = 0 if reduced else math.sin(t * 1.7 + j * .9 + k)
            c.text(x + (k - 1) * 7 + sway * 2, y - j, ":" if j % 2 else "~", "dim" if j > 2 else "ink")


def meter(c: Canvas, x: int, y: int, width: int, value: float,
          label: str, style: str = "blue") -> None:
    width = max(5, width)
    count = round((width - 2) * clamp(value))
    c.text(x, y, "[" + "=" * count + "." * (width - 2 - count) + "]", style)
    c.text(x, y - 1, label, "ink")


# Simple original 5×5 block lettering; falls back to normal text on small terminals.
FONT = {
    'A': ["01110", "10001", "11111", "10001", "10001"],
    'E': ["11111", "10000", "11110", "10000", "11111"],
    'I': ["111", "010", "010", "010", "111"],
    'K': ["10001", "10010", "11100", "10010", "10001"],
    'M': ["10001", "11011", "10101", "10001", "10001"],
    'N': ["10001", "11001", "10101", "10011", "10001"],
    'O': ["01110", "10001", "10001", "10001", "01110"],
    'R': ["11110", "10001", "11110", "10010", "10001"],
    'S': ["01111", "10000", "01110", "00001", "11110"],
    'T': ["11111", "00100", "00100", "00100", "00100"],
    'U': ["10001", "10001", "10001", "10001", "01110"],
    '?': ["11110", "00001", "00110", "00000", "00100"],
    ' ': ["000"] * 5,
}


def lettering(text: str) -> tuple[list[tuple[int, int]], int]:
    points = []
    x = 0
    for char in text.upper():
        glyph = FONT.get(char, FONT["?"])
        for y, row in enumerate(glyph):
            points.extend((x + dx, y) for dx, pixel in enumerate(row) if pixel == "1")
        x += len(glyph[0]) + 1
    return points, max(0, x - 1)


def headline(c: Canvas, y: int, text: str, style: str = "gold") -> None:
    points, width = lettering(text)
    if width > c.width - 8:
        c.center(y + 2, text, style)
        return
    for x, dy in points:
        c.text((c.width - width) // 2 + x, y + dy, "#", style)
