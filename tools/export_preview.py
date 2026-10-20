#!/usr/bin/env python3
"""Export a self-contained, reduced-motion HTML storyboard with local audio.

This is a fixed-resolution, sampled preview, not the live 24-fps renderer.
It contains no music, external JavaScript, images, or font files.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tonkatsu.film import Film


def main():
    parser=argparse.ArgumentParser(description='导出无需 Python 的单文件 HTML 分镜预览')
    parser.add_argument('--output',type=Path,default=ROOT/'dist/tonkatsu-preview.html')
    parser.add_argument('--fps',type=int,default=6)
    parser.add_argument('--width',type=int,default=100)
    parser.add_argument('--height',type=int,default=36)
    args=parser.parse_args()
    if not 1<=args.fps<=12 or not 64<=args.width<=160 or not 24<=args.height<=60:
        parser.error('fps: 1..12；width: 64..160；height: 24..60')
    film=Film()
    frames=[]
    times={min(film.timeline.duration,i/args.fps) for i in range(int(film.timeline.duration*args.fps)+2)}
    times.update(c.start for c in film.timeline.cues)
    times.add(205.811)
    for t in sorted(times):
        frame=film.render(t,args.width,args.height,reduced=True)
        frames.append({'rows':frame.runs(),'scene':film.timeline.at(t).title,'t':t})
    data=json.dumps(frames,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    packed=base64.b64encode(gzip.compress(data,compresslevel=9,mtime=0)).decode('ascii')
    meta=film.timeline.metadata()
    meta['audio_available']=False
    bundle={'meta':meta,'width':args.width,'height':args.height,'fps':args.fps,'payload':packed}
    html=(ROOT/'web/index.html').read_text(encoding='utf-8')
    css=(ROOT/'web/style.css').read_text(encoding='utf-8')
    script=(ROOT/'web/app.js').read_text(encoding='utf-8')
    html=html.replace('<link rel="stylesheet" href="/style.css">','<style>'+css+'</style>')
    html=html.replace('<script src="/app.js"></script>',
        '<script>window.TONKATSU_OFFLINE='+json.dumps(bundle,ensure_ascii=True,separators=(',',':'))+';</script>\n<script>'+script+'</script>')
    html=html.replace('无声分镜预览。载入你本地的 world.execute(me); 音频后，画面跟随音频时钟。',
        f'离线抽样分镜 / {args.fps} FPS / 已减弱动态。可载入本地原曲试听；正式实时版请运行 preview.py。')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(html,encoding='utf-8')
    print(f'{args.output} ({args.output.stat().st_size:,} bytes; {len(frames)} frames)')


if __name__=='__main__':
    main()
