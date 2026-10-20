#!/usr/bin/env python3
"""Convert the artist's PNG into a registered ASCII slot (optional Pillow)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SLOTS = ('temari_calm','temari_tempted','temari_bite','temari_happy','tonkatsu_hero','tonkatsu_slice')


def convert(source: Path, columns: int, mode: str = 'luma', invert: bool = False) -> str:
    try:
        from PIL import Image, ImageFilter, ImageOps
    except ImportError as exc:
        raise RuntimeError('图片转换需要 Pillow：python3 -m pip install -r requirements-art.txt') from exc
    if not 8 <= columns <= 100:
        raise ValueError('--columns 应在 8..100 之间。')
    with Image.open(source) as opened:
        if opened.width < 1 or opened.height < 1:
            raise ValueError('图片尺寸无效。')
        rows = max(1, min(60, round(opened.height/opened.width*columns*.5)))
        rgba = opened.convert('RGBA').resize((columns, rows), Image.Resampling.LANCZOS)
    alpha = rgba.getchannel('A')
    gray = ImageOps.grayscale(rgba)
    if mode == 'edges':
        gray = ImageOps.autocontrast(gray.filter(ImageFilter.FIND_EDGES))
    values, mask = gray.tobytes(), alpha.tobytes()
    ramp = ' .:-=+*#%@'
    result=[]
    for y in range(rows):
        line=[]
        for x in range(columns):
            index=y*columns+x
            if mask[index] < 48:
                line.append(' ')
            elif mode == 'silhouette':
                line.append('#')
            else:
                brightness = values[index]/255
                if invert:
                    brightness=1-brightness
                brightness=brightness**.65
                line.append(ramp[round(brightness*(len(ramp)-1))])
        result.append(''.join(line).rstrip())
    return '\n'.join(result)+'\n'


def main() -> int:
    parser=argparse.ArgumentParser(description='将透明 PNG 导入 Tonkatsu.(me) 素材槽')
    parser.add_argument('source', type=Path)
    parser.add_argument('--slot', choices=SLOTS, required=True)
    parser.add_argument('--columns', type=int)
    parser.add_argument('--mode', choices=('luma','edges','silhouette'), default='luma')
    parser.add_argument('--invert', action='store_true')
    parser.add_argument('--output', type=Path, help='仅导出文本到此处，不修改素材槽或 manifest')
    args=parser.parse_args()
    try:
        manifest_path=ROOT/'assets/manifest.json'
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        columns=args.columns or manifest[args.slot]['columns']
        text=convert(args.source,columns,args.mode,args.invert)
        output=args.output or ROOT/'assets/ascii'/f'{args.slot}.txt'
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(text,encoding='ascii')
        if args.output is None:
            manifest[args.slot]['status']='ready'
            manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'已生成 {output}\n重启 preview.py 后可看到替换效果。')
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print(f'转换失败：{exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
