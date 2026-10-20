"""Optional mpv audio clock over a private Unix-domain JSON IPC socket.

Browser playback does not require mpv. This backend targets macOS and Linux.
No audio is decoded, downloaded, or uploaded by this module.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from .clock import State


class MpvClock:
    def __init__(self, path: Path, timeout: float = 10.0):
        if os.name != 'posix':
            raise RuntimeError('终端音频后端目前支持 macOS/Linux；Windows 请运行 preview.py。')
        executable = shutil.which('mpv')
        if not executable:
            raise RuntimeError('未找到 mpv。可安装 mpv，或运行 python3 preview.py 使用浏览器音频。')
        if not path.is_file():
            raise FileNotFoundError(f'找不到音频：{path}；使用 --demo 可无声预览。')
        self._lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._position, self._duration, self._paused = 0.0, 0.0, True
        self.error = ''
        self._closed = False
        self._socket: socket.socket | None = None
        self._reader = None
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._temporary = tempfile.TemporaryDirectory(prefix='tonkatsu-audio-')
        self._log = open(Path(self._temporary.name) / 'mpv.log', 'w+b')
        ipc = str(Path(self._temporary.name) / 'ipc.sock')
        try:
            self._process = subprocess.Popen(
                [executable, '--no-config', '--video=no', '--audio-display=no', '--terminal=no',
                 '--input-terminal=no', '--idle=yes', '--keep-open=yes', '--pause=yes',
                 '--volume=75', f'--input-ipc-server={ipc}', str(path.resolve())],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=self._log)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self._process.poll() is not None:
                    raise RuntimeError(self._failure_message())
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    sock.connect(ipc)
                    self._socket = sock
                    break
                except (FileNotFoundError, ConnectionRefusedError):
                    sock.close()
                    time.sleep(.025)
            if self._socket is None:
                raise RuntimeError('mpv IPC 启动超时。')
            self._reader = self._socket.makefile('r', encoding='utf-8')
            self._thread = threading.Thread(target=self._receive, daemon=True)
            self._thread.start()
            for i, prop in enumerate(('time-pos', 'duration', 'pause', 'eof-reached'), 1):
                self._command(['observe_property', i, prop])
            while time.monotonic() < deadline:
                if self.error:
                    raise RuntimeError(self.error)
                if self._duration > 0:
                    return
                if self._process.poll() is not None:
                    raise RuntimeError(self._failure_message())
                time.sleep(.025)
            raise RuntimeError('音频载入超时：请确认文件有效且 mpv 可播放该文件。')
        except BaseException:
            self.close()
            raise

    def _failure_message(self) -> str:
        self._log.flush()
        self._log.seek(0)
        return 'mpv 音频错误：' + self._log.read(4096).decode('utf-8', errors='replace')

    def _receive(self) -> None:
        try:
            for line in self._reader:
                try:
                    event = json.loads(line)
                except (ValueError, TypeError):
                    continue
                self._event(event)
        except (OSError, ValueError):
            if not self._closed:
                self.error = 'mpv 音频连接中断。'

    def _event(self, event: dict) -> None:
        with self._lock:
            if event.get('event') == 'property-change':
                name, data = event.get('name'), event.get('data')
                if name == 'time-pos' and isinstance(data, (float, int)):
                    self._position = max(0.0, float(data))
                elif name == 'duration' and isinstance(data, (float, int)):
                    self._duration = max(0.0, float(data))
                elif name == 'pause' and isinstance(data, bool):
                    self._paused = data
                elif name == 'eof-reached' and data is True:
                    self._paused = True
                    self._position = self._duration
            elif event.get('event') == 'end-file' and event.get('reason') == 'error':
                self.error = 'mpv 无法解码音频：' + str(event.get('file_error', 'unknown'))

    def _command(self, command: list) -> None:
        if self._socket is None:
            return
        with self._send_lock:
            self._socket.sendall((json.dumps({'command': command}) + '\n').encode('utf-8'))

    def state(self) -> State:
        if self._process is not None and self._process.poll() is not None and not self._closed:
            self.error = 'mpv 已退出。'
        with self._lock:
            return State(self._position, self._duration, self._paused)

    def pause(self, paused: bool) -> None:
        self._command(['set_property', 'pause', paused])

    def seek(self, position: float) -> None:
        self._command(['seek', max(0.0, min(max(0, self._duration-.01), position)), 'absolute+exact'])

    def volume(self, value: float) -> None:
        self._command(['set_property', 'volume', max(0, min(100, value))])

    def close(self) -> None:
        self._closed = True
        try:
            self._command(['quit'])
        except (OSError, ValueError):
            pass
        if self._process is not None:
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=1)
        if self._reader is not None:
            self._reader.close()
        if self._socket is not None:
            self._socket.close()
        self._log.close()
        self._temporary.cleanup()
