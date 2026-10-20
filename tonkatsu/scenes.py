"""Original Tonkatsu.(me) choreography. Every frame is a pure function of time.

The portrait slots are explicitly placeholders, not claimed character likenesses.
Narrative text is fan-created, not quoted game dialogue or song subtitles.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from .art import Artwork
from .canvas import Canvas, fit
from .primitives import clamp, noise, ellipse, cutlet, steam, meter, headline, lettering
from .timeline import Cue


@dataclass(frozen=True)
class Stage:
    canvas: Canvas
    art: Artwork
    cue: Cue
    time: float
    pulse: float
    reduced: bool

    @property
    def local(self) -> float:
        return max(0, self.time - self.cue.start)

    @property
    def progress(self) -> float:
        return clamp(self.local / max(.001, self.cue.end - self.cue.start))

    @property
    def top(self) -> int:
        return 5

    @property
    def bottom(self) -> int:
        return self.canvas.height - 8

    @property
    def cy(self) -> int:
        return (self.top + self.bottom) // 2

    @property
    def food_x(self) -> int:
        return int(self.canvas.width * .66)

    @property
    def radius(self) -> int:
        return min(20, max(10, self.canvas.width // 6))

    def portrait(self, expression: str | None = None) -> None:
        c = self.canvas
        available_h = self.bottom - self.top - 2
        self.art.draw(c, "temari_" + (expression or self.cue.expression), 4, self.cy - 5,
                      width=min(40, c.width // 3 - 6), height=max(7, available_h))
        c.text(4, self.top, "TEMARI / POV", "blue")
        c.text(4, min(self.bottom, self.cy + 8),
               "ART: PLACEHOLDER" if self.art.status.get("temari_" + (expression or self.cue.expression)) != "ready"
               else "ART: LOADED", "dim")

    def food(self, **kwargs) -> None:
        name = "tonkatsu_slice" if kwargs.get("sliced") else "tonkatsu_hero"
        if self.art.status.get(name) == "ready" and name in self.art.sprites:
            rows = self.art.sprites[name]
            source_w = max((len(row) for row in rows), default=1)
            source_h = max(1, len(rows))
            factor = min(1.0, (self.radius*2+1)/source_w, max(7, self.bottom-self.top-4)/source_h)
            w, h = max(1,int(source_w*factor)), max(1,int(source_h*factor))
            left, top = self.food_x-w//2, self.cy+2-h//2
            self.art.draw(self.canvas, name, left, top, "gold", w, h)
            # A replaceable still can participate in a simple bite/reveal animation.
            visible = clamp(kwargs.get("reveal", 1))
            if kwargs.get("bite"):
                visible = min(visible, max(.15, 1-kwargs["bite"]*.19))
            for y in range(top, top+h):
                self.canvas.text(left+int(w*visible), y, " "*(w-int(w*visible)), "dim")
        else:
            cutlet(self.canvas, self.food_x, self.cy + 2, self.radius, min(5, max(3, (self.bottom-self.top)//4)),
                   t=self.time, **kwargs)


def kitchen(s: Stage) -> None:
    c = s.canvas
    s.portrait("calm")
    x, y = max(30, c.width // 3 + 2), s.top + 1
    mode = s.cue.params.get("mode", "boot")
    messages = {
        "boot": ["TEMARI.APP / STARTING", "sense.smell .... online", "sense.taste .... online", "self.control ... online", "target ......... TONKATSU"],
        "coat": ["recipe.load()", "flour .......... attached", "egg ............ attached", "panko .......... attached", "cutlet.object .. created"],
        "heat": ["pan.preheat()", "oil.temperature .. ready", "panko.colour ..... GOLD", "crunch.expected .. HIGH", "hunger.actual .... HIGHER"],
    }[mode]
    for i, message in enumerate(messages):
        if s.progress >= i / 6:
            c.text(x, y + i * 2, fit(message, c.width - x - 3), "gold" if i == 4 else "ink")
    if c.height > 33:
        cutlet(c, s.food_x, s.bottom - 3, max(9, s.radius - 5), 2,
               t=s.time, reveal=clamp(s.progress * 1.3), plate=False)
    meter(c, x, s.bottom, min(33, c.width - x - 3), s.progress, "recipe.compile()", "gold")


def title(s: Stage) -> None:
    c = s.canvas
    points, title_w = lettering("TONKATSU")
    left = (c.width - title_w) // 2
    target_y = s.cy - 3
    u = 1.0 if s.reduced else clamp(s.local / 3.5)
    smooth = u * u * (3 - 2 * u)
    for i, (x, y) in enumerate(points):
        sx = noise(i * 47) * (c.width - 4) + 2
        sy = s.top + noise(i * 89 + 1) * (s.bottom - s.top)
        c.text(sx * (1 - smooth) + (left + x) * smooth,
               sy * (1 - smooth) + (target_y + y) * smooth, "#", "gold")
    c.center(target_y + 6, ".(me)", "blue")
    c.center(s.top, "INSIDE TEMARI'S MIND", "dim")
    if s.local > 4:
        c.center(s.bottom - 1, "a perfectly reasonable amount of tonkatsu", "ink")
    if s.local > 7 and c.height >= 32:
        for side in (-1, 1):
            ellipse(c, c.width/2 + side * 34, s.cy + 3, 6, 2, ":", "darkgold")


def sensory(s: Stage) -> None:
    c = s.canvas
    s.portrait("tempted")
    mode = s.cue.params.get("mode", "points")
    x, y, rx = s.food_x, s.cy + 2, s.radius
    if mode == "points":
        u = 1 if s.reduced else clamp(s.progress * 1.6)
        for i in range(150):
            angle = noise(i * 11) * math.tau
            radius = math.sqrt(noise(i * 79))
            tx, ty = x + math.cos(angle) * rx * radius, y + math.sin(angle) * 4 * radius
            sx = c.width // 3 + noise(i * 113) * (c.width * .64 - 4)
            sy = s.top + noise(i * 71) * (s.bottom - s.top)
            c.text(sx * (1-u) + tx*u, sy*(1-u)+ty*u, ".:*#"[i % 4], "gold")
        c.center(s.top + 1, "POINT CLOUD -> PANKO CLOUD", "gold")
    elif mode == "circle":
        s.food(sliced=True)
        ellipse(c, x, y, rx + 7, 6, ".", "blue")
        a = 0 if s.reduced else s.local * 1.6
        c.text(x + math.cos(a)*(rx+7), y + math.sin(a)*6, "*", "white")
        c.text(c.width//3 + 2, s.top + 1, "PLATE.CIRCUMFERENCE = ALL MINE", "gold")
    elif mode == "sine":
        s.food(sliced=True)
        for i in range(max(2, x - 24)):
            xx = x - i
            yy = s.cy - 3 + math.sin(i * .23 + (0 if s.reduced else s.local*3)) * 2
            c.text(xx, yy, "~", "gold" if i % 3 else "white")
        c.text(c.width//3 + 2, s.top + 1, "AROMA -> TEMARI", "gold")
    elif mode == "infinite":
        for i in range(180):
            a = i / 180 * math.tau
            denominator = 1 + math.cos(a) ** 2
            xx = x + math.sin(a) / denominator * (rx + 9)
            yy = y + math.sin(a)*math.cos(a)/denominator*12
            c.text(xx, yy, "." if i % 3 else "#", "gold")
        c.text(x - 8, y, "ONE MORE", "white")
        c.text(c.width//3 + 2, s.top + 1, "APPETITE.LIMIT = UNDEFINED", "gold")
    elif mode == "fry":
        s.food(plate=False)
        c.line(x-rx-3, y+5, x+rx+3, y+5, "=", "ink")
        for i in range(28):
            xx = x-rx + noise(i*31)*rx*2
            yy = y + 4 - ((s.local * (1 + noise(i*7)) + noise(i*41)*6) % 8)
            c.text(xx, yy, "o" if i % 3 == 0 else ".", "gold")
        c.text(c.width//3 + 2, s.top+1, "sizzle.signal() -> CRUNCH", "gold")
    elif mode == "sauce":
        s.food(sliced=True)
        for i in range(36):
            a = i*.3 + (0 if s.reduced else s.time*.7)
            r = i*.36
            c.text(x + math.cos(a)*r, y + math.sin(a)*r*.25, "~", "darkgold")
        c.text(c.width//3+2, s.top+1, "SAUCE.TRAJECTORY / LOCKED", "gold")
    elif mode == "rewind":
        cycle = (s.local / 1.5) % 2
        s.food(bite=int(cycle*2) if cycle < 1 else int((2-cycle)*2))
        c.text(c.width//3+2, s.top+1, "<< REPLAY FIRST BITE", "gold")
        c.center(s.bottom, "crunch.cache / never delete", "dim")
    else:
        s.food(sliced=True)
        c.line(24, s.cy, x-rx, s.cy, ".", "blue")
        c.text((x+24)//2 - 2, s.cy-1, "<3", "pink")
        c.text(c.width//3+2, s.top+1, "pair(TEMARI, TONKATSU)", "gold")


def happiness(s: Stage) -> None:
    c = s.canvas
    s.portrait("happy" if s.progress > .3 else "tempted")
    s.food(sliced=True, bite=1 if s.cue.params.get("bite") else 0)
    steam(c, s.food_x, s.cy - 4, s.time, reduced=s.reduced)
    x = c.width//3 + 3
    for i, (label, value) in enumerate((('CRUNCH', .9), ('JUICINESS', .83), ('HAPPINESS', .99))):
        meter(c, x, s.top + 2 + i*2, min(20, max(10, c.width//5)),
              clamp(value * min(1, s.progress*3) + s.pulse*.1), label, "gold" if i < 2 else "pink")
    if s.cue.params.get("loop"):
        c.center(s.bottom, "while (delicious) { another_bite(); }", "pink")


def preferences(s: Stage) -> None:
    c = s.canvas
    s.portrait()
    s.food(sliced=True)
    mode = s.cue.params.get("mode", "sides")
    x = c.width//3+2
    if mode == "sides":
        c.text(x, s.top + 1, "ATTENTION ALLOCATION", "ink")
        c.text(x, s.top + 3, "cabbage ... visible", "dim")
        c.text(x, s.top + 4, "tomato .... visible", "dim")
        c.text(x, s.top + 5, "tonkatsu .. SELECTED", "gold")
        c.text(s.food_x-s.radius-3, s.cy+7, "/// cabbage ///", "dim")
    elif mode == "deny":
        c.text(x, s.top+1, "public:  I AM NOT HUNGRY", "blue")
        c.text(x, s.top+3, "private: TONKATSU TONKATSU", "gold")
        c.text(x, s.top+5, "access denied -> appetite", "pink")
    elif mode == "clock":
        angle = 0 if s.reduced else s.local*2
        ellipse(c, x+8, s.cy-2, 8, 4, ".", "blue")
        c.line(x+8, s.cy-2, x+8+math.sin(angle)*6, s.cy-2-math.cos(angle)*3, ":", "white")
        c.text(x, s.top+1, "AM / PM / TONKATSU", "gold")
    elif mode == "focus":
        c.box(s.food_x-s.radius-2, s.cy-4, s.radius*2+5, 12, "gold")
        c.text(x, s.top+1, "TARGET RECOGNIZED", "gold")
        c.text(x, s.top+3, "other thoughts -> background", "dim")
    else:
        c.text(x, s.top+1, "VOICE: CALM / MIND: LOUD", "blue")
        for i in range(18):
            xx = x + i*2
            yy = s.top+4 + math.sin(i*.7+s.local*2)*1.5
            c.text(xx, yy, "*", "gold")


def heartbeat(s: Stage) -> None:
    c = s.canvas
    s.portrait("happy")
    s.food(sliced=True)
    left = c.width//3+1
    length = c.width-left-4
    for i in range(length):
        p = (i/13 - (0 if s.reduced else s.local*1.1)) % 1
        amplitude = 0 if p > .38 else math.sin(p/.38*math.tau) * 3
        c.text(left+i, s.top+4+amplitude, "-" if abs(amplitude) < .4 else "|", "pink")
    c.text(left, s.top+1, "HEARTBEAT <-> FRYING RHYTHM", "pink")


def separation(s: Stage) -> None:
    c = s.canvas
    s.portrait("tempted")
    departing = s.progress
    x = s.food_x + (c.width-s.food_x+s.radius+6)*departing
    cutlet(c, x, s.cy+2, s.radius, 4, t=s.time, sliced=True)
    for xx in range(28, min(c.width-3, s.food_x)):
        if xx % 7 > int(departing*7):
            c.text(xx, s.cy, ".", "blue")
    c.text(c.width//3+2, s.top+1, "TONKATSU: CONNECTION LOST", "red")
    if s.progress > .65:
        c.text(s.food_x-11, s.cy+2, "[ EMPTY PLATE ]", "ink")
    c.center(s.bottom, "reconnect() ... reconnect() ...", "gold")


def memory(s: Stage) -> None:
    c = s.canvas
    s.portrait("tempted")
    x = c.width//3+2
    c.text(x, s.top+1, "clear_memory(tonkatsu)", "blue")
    for i in range(6):
        yy = s.top+3+i*2
        text = "0000 0000 0000" if (i + int(s.local*2)) % 3 else "TONKATSU RESTORED"
        c.text(x, yy, text, "dim" if text.startswith('0') else "gold")
    cutlet(c, c.width-18, s.cy+1, 10, 3, plate=False)
    c.center(s.bottom, "ERROR: delicious memory is read-only", "red")


def exceptions(s: Stage) -> None:
    c = s.canvas
    s.portrait("tempted")
    x = c.width//3+2
    lines = ["SelfControlError: target too crispy", "retry -> smell -> distracted", "assert(portions == 1) ... FAILED",
             "permission: just one more", "stack.push(TONKATSU)", "reason: 'I am only tasting it.'"]
    count = min(len(lines), 1+int(s.local/2))
    for i, line in enumerate(lines[:count]):
        c.text(x, s.top+1+i*2, fit(line, c.width-x-3), "red" if i%3==0 else "gold")
    if c.height > 32:
        cutlet(c, s.food_x, s.bottom-2, 12, 2, t=s.time, plate=False)
    meter(c, x, s.bottom, min(35, c.width-x-3), 1-s.progress*.95, "SELF.CONTROL", "blue")


def feast(s: Stage) -> None:
    c = s.canvas
    s.portrait("bite" if int(s.local*2)%3 else "happy")
    cycle = (s.local / 1.3) % 1
    s.food(sliced=True, bite=int(cycle*4))
    c.text(c.width//3+2, s.top+1, "eat.execute(me)", "gold")
    c.text(c.width//3+2, s.top+3, f"BITE QUEUE / {int(s.local/1.3)+1:02d}", "pink")
    if cycle > .3:
        c.text(s.food_x+s.radius-9, s.cy-4, "* CRUNCH *", "white")
    c.center(s.bottom, "not a crash. a very delicious exception.", "ink")


def count_portions(s: Stage) -> None:
    c = s.canvas
    s.portrait("happy")
    count = min(6, int(s.progress*6)+1)
    x = c.width//3+3
    for i in range(count):
        column, row = i%3, i//3
        cutlet(c, x+9+column*max(11, (c.width-x-6)//3), s.top+5+row*7,
               max(4, min(7, (c.width-x)//7)), 2, t=s.time, plate=False)
    c.text(x, s.top+1, f"ONE? TWO? ... {count:02d} MORE REASONS", "gold")
    c.center(s.bottom, "PORTION COUNT / OVERFLOW", "pink")


def obsession(s: Stage) -> None:
    c = s.canvas
    s.portrait("tempted")
    s.food(sliced=True)
    x = c.width//3+2
    for i in range(5):
        y = s.top+1+i*3
        if y < s.bottom:
            c.text(x, y, "TONKATSU "*(max(1, (c.width-x-3)//9)), "darkgold")
    # Repaint food in front: the background becomes a thought pattern, not visual noise.
    s.food(sliced=True)
    c.center(s.bottom, "attention.weights = {tonkatsu: 1.0}", "pink")


def love(s: Stage) -> None:
    c = s.canvas
    s.portrait("happy")
    x, y = s.food_x, s.cy
    rx = min(21, c.width//5)
    ry = max(4, (s.bottom-s.top)//2-1)
    for yy in range(-ry, ry+1):
        for xx in range(-rx, rx+1):
            a = xx/max(1, rx)*1.4
            b = -yy/max(1, ry)*1.35
            if (a*a+b*b-1)**3 - a*a*b*b*b <= 0:
                c.text(x+xx, y+yy, ":#%"[int(noise(xx*89+yy*23)*2.999)], "gold" if (xx+yy)%4 else "pink")
    c.text(x-9, y, "TEMARI + TONKATSU", "white")
    c.center(s.top, "LOVE IS NOT A SOLVABLE EQUATION", "pink")
    c.center(s.bottom, "but this one tastes right.", "ink")


def loop(s: Stage) -> None:
    c = s.canvas
    s.portrait("happy")
    s.food(bite=1)
    for i in range(7):
        a = i/7*math.tau+(0 if s.reduced else s.local*.6)
        xx = s.food_x+math.cos(a)*(s.radius+8)
        yy = s.cy+math.sin(a)*7
        c.text(xx, yy, "<3" if i%2 else "+1", "pink" if i%2 else "gold")
    c.text(c.width//3+2, s.top, "for (;;) { delicious(); }", "gold")


def ending(s: Stage) -> None:
    c = s.canvas
    s.portrait("happy")
    x = c.width//3+3
    if s.time < 205.811:
        value = min(.99, s.local/5*.99)
        meter(c, x, s.cy-1, max(20, c.width-x-5), value, "SATISFACTION", "gold")
        c.text(x, s.cy+2, f"{int(value*100):02d}% / {'ONE MORE?' if value >= .99 else 'SAVOURING...'}", "pink")
        c.text(x, s.cy+5, "pending: another perfect bite", "ink")
    else:
        # Keep the final title readable; no full-screen flashing.
        c.text(x, s.top+1, "REQUEST ACCEPTED", "gold")
        c.text(x, s.cy-2, "Tonkatsu.(me)", "white")
        c.text(x, s.cy, "+1 / ONE MORE", "pink")
        cutlet(c, s.food_x, s.cy+5, 12, 2, t=s.time, sliced=True)
        c.center(s.bottom, "THE LOOP IS DELICIOUS.", "gold")


SCENES = {
    "kitchen": kitchen, "title": title, "sensory": sensory, "happiness": happiness,
    "preferences": preferences, "heartbeat": heartbeat, "separation": separation,
    "memory": memory, "exceptions": exceptions, "feast": feast, "count": count_portions,
    "obsession": obsession, "love": love, "loop": loop, "ending": ending,
}
