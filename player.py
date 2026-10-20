#!/usr/bin/env python3
"""Terminal entry point; snapshots work without an audio file or interactive TTY."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import math
import os
from pathlib import Path
import select
import shutil
import signal
import sys
import time
from tonkatsu.clock import DemoClock
from tonkatsu.film import Film
from tonkatsu.timeline import ROOT


def finite(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise argparse.ArgumentTypeError('请输入有限数值。')
    return result


@contextmanager
def terminal():
    if os.name != 'posix':
        raise RuntimeError('交互终端目前支持 macOS/Linux；Windows 可使用 preview.py 或 --snapshot。')
    import termios
    import tty
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    handlers = {}
    def interrupt(*_):
        raise KeyboardInterrupt
    try:
        handlers = {s: signal.signal(s, interrupt) for s in (signal.SIGTERM, signal.SIGHUP)}
        tty.setcbreak(fd)
        sys.stdout.write('\033[?1049h\033[?25l\033[?7l\033[2J')
        sys.stdout.flush()
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original)
        sys.stdout.write('\033[0m\033[?7h\033[?25h\033[?1049l')
        sys.stdout.flush()
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


def keys(timeout: float) -> str:
    if select.select([sys.stdin], [], [], timeout)[0]:
        data = os.read(sys.stdin.fileno(), 128)
        if data.startswith(b'\x1b') and len(data) < 3:
            if select.select([sys.stdin], [], [], .03)[0]:
                data += os.read(sys.stdin.fileno(), 128)
        return data.decode('utf-8', errors='ignore')
    return ''


def play(args, film: Film) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError('交互播放需要真实终端。无终端时使用 --snapshot 69 --plain。')
    if os.name != 'posix':
        raise RuntimeError('Windows 请使用 python preview.py；终端交互版目前针对 macOS/Linux。')
    if args.demo:
        clock = DemoClock(film.timeline.duration)
    else:
        from tonkatsu.audio import MpvClock
        clock = MpvClock(args.audio)
    try:
        clock.seek(args.start)
        clock.pause(not args.autoplay)
        reduced, volume = args.reduced_motion, 75
        last_size = None
        with terminal():
            while True:
                begun = time.monotonic()
                state = clock.state()
                if clock.error:
                    raise RuntimeError(clock.error)
                width, height = shutil.get_terminal_size((120, 42))
                width, height = max(1, min(width-1, 240)), max(1, min(height, 85))
                if last_size != (width, height):
                    sys.stdout.write('\033[2J')
                    last_size = width, height
                frame = film.render(state.position, width, height, reduced, paused=state.paused, offset=args.offset)
                sys.stdout.write(frame.ansi())
                sys.stdout.flush()
                pending = keys(max(0, 1/args.fps-(time.monotonic()-begun)))
                while pending:
                    if pending.startswith(('\x1b[C', '\x1b[D')):
                        clock.seek(clock.state().position + (5 if pending[2]=='C' else -5))
                        pending = pending[3:]
                        continue
                    key, pending = pending[0], pending[1:]
                    if key in ('q','Q','\x03','\x1b'):
                        return
                    if key in (' ', '\r', '\n'):
                        state = clock.state()
                        if state.position >= state.duration-.05:
                            clock.seek(0)
                        clock.pause(not state.paused)
                    elif key in ('r','R'):
                        clock.seek(0)
                        clock.pause(False)
                    elif key in ('m','M'):
                        reduced = not reduced
                    elif key in ('+','=', '-'):
                        volume = max(0, min(100, volume + (-5 if key=='-' else 5)))
                        clock.volume(volume)
                    elif key in '12345':
                        clock.seek((0,29.709,110.9,147.66,177.246)[int(key)-1])
                    elif key in '[]':
                        args.offset += -.1 if key=='[' else .1
    finally:
        clock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description='Tonkatsu.(me) / 月村手毬的炸猪排幻想')
    parser.add_argument('--demo', action='store_true', help='无声演示，不冒充真实音频时钟')
    parser.add_argument('--audio', type=Path, default=ROOT/'media/song.mp3')
    parser.add_argument('--autoplay', action='store_true')
    parser.add_argument('--start', type=finite, default=0)
    parser.add_argument('--offset', type=finite, default=0, help='画面相对音频的偏移（秒）；正值提前画面')
    parser.add_argument('--fps', type=int, default=24)
    parser.add_argument('--snapshot', type=finite, metavar='SECONDS')
    parser.add_argument('--width', type=int, default=120)
    parser.add_argument('--height', type=int, default=42)
    parser.add_argument('--plain', action='store_true')
    parser.add_argument('--reduced-motion', action='store_true')
    parser.add_argument('--output', type=Path, help='保存快照文本，不用于实时播放')
    args = parser.parse_args()
    if not 5 <= args.fps <= 60:
        parser.error('--fps 应在 5 到 60 之间。')
    if not 1 <= args.width <= 240 or not 1 <= args.height <= 85:
        parser.error('快照尺寸范围：宽 1..240，高 1..85。')
    if args.output and args.snapshot is None:
        parser.error('--output 仅用于 --snapshot。')
    try:
        film = Film()
        if args.snapshot is not None:
            frame = film.render(args.snapshot, args.width, args.height, args.reduced_motion, offset=args.offset)
            result = frame.plain() if args.plain else frame.ansi()
            if args.output:
                args.output.write_text(result+'\n', encoding='utf-8')
            else:
                print(result)
        else:
            play(args, film)
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f'播放失败：{error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
