#!/usr/bin/env python3
"""Optional browser smoke test for the exported offline UI; not a live-HTTP E2E test.

Requires Playwright plus a local Chromium binary. Generates only a diagnostic
sine wave in a temporary directory, never downloads or embeds the song.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import struct
import tempfile
import wave
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--html',type=Path,default=ROOT/'dist/tonkatsu-preview.html')
    parser.add_argument('--browser',help='Optional installed Chromium executable path')
    parser.add_argument('--results',type=Path,default=ROOT/'test-results')
    args=parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.exit(1,'可选测试依赖未安装：python3 -m pip install playwright\n')
    if not args.html.is_file():
        parser.exit(1,'请先运行 python3 tools/export_preview.py\n')
    args.results.mkdir(parents=True,exist_ok=True)
    errors=[];requests=[];checks={}
    with tempfile.TemporaryDirectory() as td:
        tone=Path(td)/'diagnostic-tone.wav'
        with wave.open(str(tone),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000)
            second=b''.join(struct.pack('<h',int(300*math.sin(i/8000*math.tau*220))) for i in range(8000))
            for _ in range(212): audio.writeframesraw(second)
        with sync_playwright() as p:
            options={'headless':True}
            if args.browser: options['executable_path']=args.browser
            browser=p.chromium.launch(**options)
            try:
                page=browser.new_page(viewport={'width':1440,'height':1050})
                page.set_default_timeout(10000)
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda req:requests.append(req.url))
                # In-memory HTML rendering does not exercise live HTTP navigation.
                page.set_content(args.html.read_text(encoding='utf-8'),wait_until='load')
                page.wait_for_function('window.TonkatsuPreview && document.querySelectorAll("#chapters button").length===31')
                page.wait_for_function('document.querySelector("#screen").textContent.includes("Tonkatsu.(me)")')
                checks['31_scenes_and_initial_frame']=True
                page.locator('#play').click();page.wait_for_timeout(300)
                assert page.evaluate('TonkatsuPreview.position()')>.1
                page.locator('#play').click()
                paused=page.evaluate('TonkatsuPreview.position()');page.wait_for_timeout(150)
                assert abs(page.evaluate('TonkatsuPreview.position()')-paused)<.01
                checks['silent_transport']=True
                # Regression: a fractional cue boundary must not retain the old scene.
                page.locator('#chapters button').nth(13).click()
                page.wait_for_function('document.querySelector("#screen").textContent.includes("我开动了")')
                checks['exact_cue_boundary']=True
                page.screenshot(path=str(args.results/'desktop.png'),full_page=True)
                page.locator('#audioFile').set_input_files(str(tone))
                page.wait_for_function('document.querySelector("#audio").readyState>=1 && !document.querySelector("#play").disabled')
                assert page.evaluate('document.querySelector("#audio").src').startswith('blob:')
                page.locator('#play').click();page.wait_for_timeout(300)
                now=page.evaluate('document.querySelector("#audio").currentTime')
                assert now>66.601
                assert abs(page.evaluate('TonkatsuPreview.position()')-now)<.15
                page.locator('#play').click()
                paused=page.evaluate('document.querySelector("#audio").currentTime');page.wait_for_timeout(150)
                assert abs(page.evaluate('document.querySelector("#audio").currentTime')-paused)<.03
                checks['synthetic_audio_clock_and_pause']=True
                page.locator('#chapters button').nth(28).click()
                page.wait_for_function('document.querySelector("#screen").textContent.includes("LOVE IS NOT")')
                assert abs(page.evaluate('document.querySelector("#audio").currentTime')-177.246)<.05
                checks['synthetic_audio_seek']=True
                page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
                page.screenshot(path=str(args.results/'mobile.png'),full_page=True)
                checks['mobile_no_page_overflow']=True
                assert not errors,errors
                assert not [url for url in requests if not url.startswith('blob:')],requests
                checks['no_external_requests_or_javascript_errors']=True
                checks['scope']='Offline HTML in-memory test with a diagnostic tone, not the actual song and not a live-HTTP E2E test.'
            finally:
                browser.close()
    result=json.dumps(checks,ensure_ascii=False,indent=2)
    (args.results/'browser.json').write_text(result+'\n',encoding='utf-8')
    print(result)


if __name__=='__main__':
    main()
