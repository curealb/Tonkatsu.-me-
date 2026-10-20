#!/usr/bin/env python3
"""Loopback-only browser preview. One Python renderer serves both frontends.

No upload endpoint, external network requests, or directory listing is exposed.
The browser may use a local Blob URL for music without sending audio to Python.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
import webbrowser
from tonkatsu.film import Film
from tonkatsu.timeline import ROOT


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, film=None, audio=None):
        self.film = film or Film()
        self.audio = audio or ROOT/'media/song.mp3'
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'TonkatsuPreview/0.1'

    def log_message(self, *_):
        pass

    def send_common_headers(self, code: int, content_type: str, length: int, extra=None):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def reply(self, code, data, content_type='application/json; charset=utf-8', head=False):
        payload = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_common_headers(code, content_type, len(payload))
        if not head:
            self.wfile.write(payload)

    def do_HEAD(self):
        self.dispatch(head=True)

    def do_GET(self):
        self.dispatch()

    def dispatch(self, head=False):
        try:
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers_get('Host') not in allowed:
                return self.reply(403, {'error':'Only loopback hosts are accepted.'}, head=head)
            url = urlsplit(self.path)
            if url.path == '/api/info':
                info = self.server.film.timeline.metadata()
                info['audio_available'] = self.server.audio.is_file()
                info['art'] = self.server.film.art.status
                return self.reply(200, info, head=head)
            if url.path == '/api/frame':
                query = parse_qs(url.query, max_num_fields=16)
                def number(key, default, low, high):
                    value = float(query.get(key, [default])[0])
                    if not math.isfinite(value) or not low <= value <= high:
                        raise ValueError(f'{key} is out of range')
                    return value
                t = number('t', 0, 0, self.server.film.timeline.duration+60)
                w = int(number('w', 120, 64, 240))
                h = int(number('h', 42, 24, 85))
                offset = number('offset', 0, -60, 60)
                pulse = number('pulse', 0, 0, 1)
                reduced = query.get('reduced', ['0'])[0] == '1'
                paused = query.get('paused', ['0'])[0] == '1'
                frame = self.server.film.render(t,w,h,reduced,pulse,paused,offset)
                cue = self.server.film.timeline.at(t+offset)
                return self.reply(200, {'rows': frame.runs(), 'scene': cue.title,
                                        't': max(0, min(self.server.film.timeline.duration,t+offset))}, head=head)
            files = {'/':('index.html','text/html; charset=utf-8'),
                     '/app.js':('app.js','text/javascript; charset=utf-8'),
                     '/style.css':('style.css','text/css; charset=utf-8')}
            if url.path in files:
                name, content_type = files[url.path]
                return self.reply(200, (ROOT/'web'/name).read_bytes(), content_type, head)
            if url.path == '/audio':
                return self.audio_file(head)
            return self.reply(404, {'error':'Not found'}, head=head)
        except (ValueError, TypeError, OverflowError) as error:
            self.reply(400, {'error':str(error)}, head=head)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def headers_get(self, key):
        # BaseHTTPRequestHandler stores the parsed request headers on self.headers.
        return self.headers.get(key, '')

    def audio_file(self, head=False):
        path = self.server.audio
        if not path.is_file():
            return self.reply(404, {'error':'No local audio file configured.'}, head=head)
        size = path.stat().st_size
        start, end, status = 0, max(0,size-1), 200
        extra = {'Accept-Ranges':'bytes'}
        requested = self.headers_get('Range')
        if requested:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
            if not match or not any(match.groups()) or size == 0:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length','0')
                self.end_headers()
                return
            left, right = match.groups()
            if left:
                start = int(left)
                end = min(size-1, int(right)) if right else size-1
            else:
                start, end = max(0, size-int(right)), size-1
            if start >= size or start > end:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length','0')
                self.end_headers()
                return
            status = 206
            extra['Content-Range'] = f'bytes {start}-{end}/{size}'
        length = max(0, end-start+1) if size else 0
        mime = {'.wav':'audio/wav','.ogg':'audio/ogg','.m4a':'audio/mp4','.flac':'audio/flac'}.get(path.suffix.lower(),'audio/mpeg')
        self.send_common_headers(status, mime, length, extra)
        if not head:
            with path.open('rb') as file:
                file.seek(start)
                remaining = length
                while remaining:
                    data = file.read(min(65536, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)


def main():
    parser = argparse.ArgumentParser(description='Tonkatsu.(me) 本地浏览器预览')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--audio', type=Path, default=ROOT/'media/song.mp3')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('--port 必须在 0..65535 内。')
    try:
        with PreviewServer(('127.0.0.1', args.port), audio=args.audio) as server:
            url = f'http://127.0.0.1:{server.server_port}/'
            print(f'Tonkatsu.(me) 本地预览：{url}\n按 Ctrl+C 停止。音频不上传、不联网。', flush=True)
            if not args.no_open:
                webbrowser.open(url)
            server.serve_forever()
    except KeyboardInterrupt:
        return
    except OSError as error:
        parser.exit(1, f'无法启动预览服务：{error}\n可用 --port 8766 换一个端口。\n')


if __name__ == '__main__':
    main()
