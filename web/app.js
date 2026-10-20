/* No external libraries, telemetry, remote fonts, or network audio. */
'use strict';
(async () => {
  const $ = id => document.getElementById(id);
  const audio = $('audio'), screen = $('screen'), wrap = $('screenWrap');
  const play = $('play'), seekBar = $('seek'), reduced = $('reduced'), offset = $('offset');
  const errorBox = $('error'), status = $('audioStatus');
  const offline = window.TONKATSU_OFFLINE || null;
  let meta, offlineFrames;
  let mode = 'demo', demoBase = 0, demoAnchor = performance.now(), demoPaused = true;
  let ready = true, fileURL = null, frameBusy = false, force = true, epoch = 0;
  let width = 120, height = 42, lastRequest = -Infinity, active = -1;
  let audioContext = null, analyser = null, wave = null;
  const palette = new Set(['dim','ink','blue','gold','white','pink','red','darkgold']);
  reduced.checked = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  audio.volume = .75;

  function error(message) { errorBox.textContent = message; errorBox.hidden = !message; }
  function fmt(t) { t = Math.max(0, Number(t) || 0); return `${String(Math.floor(t/60)).padStart(2,'0')}:${(t%60).toFixed(1).padStart(4,'0')}`; }
  function position() {
    if (!meta) return 0;
    return mode === 'audio' ? Math.min(meta.duration, audio.currentTime || 0) :
      Math.min(meta.duration, demoBase + (demoPaused ? 0 : (performance.now()-demoAnchor)/1000));
  }
  function paused() { return mode === 'audio' ? audio.paused : demoPaused; }
  function invalidate() { epoch++; force = true; }
  function stop() {
    if (mode === 'audio') audio.pause();
    else { demoBase = position(); demoPaused = true; }
    invalidate();
  }
  function seek(t) {
    if (!meta) return;
    t = Math.max(0, Math.min(meta.duration, Number(t)||0));
    if (mode === 'audio') audio.currentTime = Math.min(t, Number.isFinite(audio.duration) ? audio.duration : t);
    else { demoBase = t; demoAnchor = performance.now(); }
    invalidate();
  }
  async function initializeMeter() {
    try {
      if (!audioContext) {
        const Constructor = window.AudioContext || window.webkitAudioContext;
        if (!Constructor) return;
        audioContext = new Constructor();
        analyser = audioContext.createAnalyser(); analyser.fftSize = 256;
        const source = audioContext.createMediaElementSource(audio);
        source.connect(analyser); analyser.connect(audioContext.destination);
        wave = new Uint8Array(analyser.fftSize);
      }
      if (audioContext.state === 'suspended') await audioContext.resume();
    } catch (_) { /* The clock remains audio.currentTime even without visual metering. */ }
  }
  function energy() {
    if (!analyser || !wave || paused() || mode !== 'audio') return 0;
    analyser.getByteTimeDomainData(wave);
    let sum = 0;
    for (const n of wave) sum += ((n-128)/128)**2;
    return Math.min(1, Math.sqrt(sum/wave.length)*3);
  }
  async function toggle() {
    if (!ready) return;
    error('');
    try {
      if (!paused()) { stop(); return; }
      const end = mode === 'audio' && Number.isFinite(audio.duration) ? Math.min(meta.duration,audio.duration) : meta.duration;
      if (position() >= end-.05) seek(0);
      if (mode === 'audio') { await initializeMeter(); await audio.play(); }
      else { demoAnchor = performance.now(); demoPaused = false; }
      invalidate();
    } catch (err) { error('音频未能开始播放：' + err.message); }
  }
  function useAudio(url, label) {
    const previous = position();
    stop(); ready = false; mode = 'audio'; play.disabled = true;
    status.textContent = '正在读取本地音频…';
    audio.src = url; audio.load();
    audio.onloadedmetadata = () => {
      ready = true; play.disabled = false;
      seek(Math.min(previous, audio.duration));
      let message = `${label} · ${fmt(audio.duration)} · 由真实音频时钟驱动画面`;
      if (Math.abs(audio.duration - meta.duration) > 1.5) message += '。音源长度与分镜不同，请使用约 3:31.9 版本或调整时间轴。';
      status.textContent = message;
    };
  }
  $('audioFile').addEventListener('change', event => {
    const file = event.target.files[0]; if (!file) return;
    if (fileURL) URL.revokeObjectURL(fileURL);
    fileURL = URL.createObjectURL(file);
    useAudio(fileURL, file.name + '（仅在本机读取）');
  });
  audio.addEventListener('error', () => {
    ready = true; play.disabled = false; mode = 'demo'; demoPaused = true;
    error('无法读取此音频。请换用浏览器支持的 MP3 / WAV，或继续无声预览。');
    status.textContent = '无声分镜预览 / 音频载入失败。'; invalidate();
  });
  audio.addEventListener('pause', invalidate);
  audio.addEventListener('seeking', invalidate);
  audio.addEventListener('seeked', invalidate);
  audio.addEventListener('ended', () => { invalidate(); });
  play.addEventListener('click', toggle);
  $('restart').addEventListener('click', async () => { seek(0); if (paused()) await toggle(); });
  seekBar.addEventListener('input', () => seek(seekBar.value));
  $('volume').addEventListener('input', event => { audio.volume = Number(event.target.value); });
  reduced.addEventListener('change', () => { document.body.classList.toggle('reduced',reduced.checked); invalidate(); });
  offset.addEventListener('change', () => {
    offset.value = Math.min(60,Math.max(-60,Number(offset.value)||0)); invalidate();
  });
  $('fullscreen').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
      else error('当前浏览器未提供全屏接口。可使用浏览器菜单进入全屏。');
    } catch (err) { error('全屏失败：'+err.message); }
  });
  document.addEventListener('keydown', event => {
    if (event.target.closest('input,button,a,select,textarea,label')) return;
    if ([' ','ArrowLeft','ArrowRight','r','R','m','M'].includes(event.key)) event.preventDefault();
    if (event.key===' ') toggle();
    else if (event.key==='ArrowLeft') seek(position()-5);
    else if (event.key==='ArrowRight') seek(position()+5);
    else if (event.key.toLowerCase()==='r') seek(0);
    else if (event.key.toLowerCase()==='m' && !offline) { reduced.checked=!reduced.checked; reduced.dispatchEvent(new Event('change')); }
  });
  function resize() {
    const available = Math.max(240, wrap.clientWidth-28);
    if (offline) { width=offline.width; height=offline.height; }
    else { width=available>880 ? 120 : available>650 ? 100 : 80; height=width>=100?42:36; }
    screen.style.fontSize = Math.min(16, available/(width*.61)).toFixed(2)+'px';
    invalidate();
  }
  new ResizeObserver(resize).observe(wrap);
  function draw(frame) {
    const fragment=document.createDocumentFragment();
    frame.rows.forEach((row,index) => {
      for (const [style,text] of row) {
        const span=document.createElement('span');
        span.className='s-'+(palette.has(style)?style:'ink');
        span.textContent=text; fragment.appendChild(span);
      }
      if(index<frame.rows.length-1) fragment.appendChild(document.createTextNode('\n'));
    });
    screen.replaceChildren(fragment);
    screen.setAttribute('aria-label',frame.scene+'，字符动画，角色立绘为占位稿');
  }
  async function requestFrame() {
    const requestEpoch=epoch;
    const time=position(), shift=Number(offset.value)||0;
    frameBusy=true; force=false;
    try {
      let frame;
      if (offline) {
        const t=Math.max(0,Math.min(meta.duration,time+shift));
        // Include exact cue-boundary frames; fixed-rate floor indexing shows the
        // preceding scene forever when paused on a fractional cue start.
        let lo=0, hi=offlineFrames.length;
        while(lo<hi) { const mid=(lo+hi)>>1; if(offlineFrames[mid].t<=t) lo=mid+1; else hi=mid; }
        frame=offlineFrames[Math.max(0,lo-1)];
      } else {
        const query=new URLSearchParams({t:time.toFixed(4),w:width,h:height,reduced:reduced.checked?'1':'0',
          paused:paused()?'1':'0',offset:shift,pulse:energy().toFixed(3)});
        const response=await fetch('/api/frame?'+query,{cache:'no-store'});
        if(!response.ok) throw new Error('渲染服务返回 '+response.status);
        frame=await response.json();
      }
      if(requestEpoch===epoch) draw(frame);
      else force=true;
    } catch(err) { error('无法读取画面：'+err.message+'。请确认 preview.py 仍在运行。'); stop(); force=false; }
    finally { frameBusy=false; }
  }
  function tick(now) {
    const t=position();
    if(!paused() && t>=meta.duration) stop();
    $('timeLabel').textContent=fmt(t); seekBar.value=t;
    play.textContent=!paused()?'暂停':mode==='audio'?'播放原曲':'播放无声预览';
    play.setAttribute('aria-pressed',String(!paused()));
    const visualT=Math.max(0,Math.min(meta.duration,t+(Number(offset.value)||0)));
    let index=meta.cues.findIndex(c => visualT>=c.start && visualT<c.end);
    if(index<0) index=meta.cues.length-1;
    if(index!==active) {
      const old=$('chapters').children[active]; if(old) {old.classList.remove('active');old.removeAttribute('aria-current');}
      const current=$('chapters').children[index]; if(current) {current.classList.add('active');current.setAttribute('aria-current','true');}
      active=index;
    }
    if(!frameBusy && (force || !paused()) && now-lastRequest>=1000/(offline?offline.fps:24)) {
      lastRequest=now; requestFrame();
    }
    requestAnimationFrame(tick);
  }
  try {
    if(offline) {
      if(!window.DecompressionStream) throw new Error('此独立预览需要支持 DecompressionStream 的现代浏览器；也可从项目运行 preview.py。');
      const bytes=Uint8Array.from(atob(offline.payload), c=>c.charCodeAt(0));
      const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
      offlineFrames=JSON.parse(await new Response(stream).text());
      meta=offline.meta; reduced.checked=true; reduced.disabled=true;
      $('renderInfo').textContent=`OFFLINE STORYBOARD / ${offline.fps} FPS`;
    } else {
      const response=await fetch('/api/info',{cache:'no-store'});
      if(!response.ok) throw new Error('HTTP '+response.status);
      meta=await response.json();
      $('renderInfo').textContent='PYTHON RENDERER / TARGET 24 FPS';
    }
    seekBar.max=meta.duration; $('durationLabel').textContent=fmt(meta.duration);
    $('cueCount').textContent=meta.cues.length+' SCENES';
    meta.cues.forEach(cue=>{
      const button=document.createElement('button');
      const time=document.createElement('time'), label=document.createElement('span');
      time.textContent=fmt(cue.start).slice(0,5); label.textContent=cue.title.replace(/^\d+ \/ /,'');
      button.append(time,label); button.addEventListener('click',()=>seek(cue.start));
      $('chapters').appendChild(button);
    });
    document.body.classList.toggle('reduced',reduced.checked);
    play.disabled=false; resize();
    if(meta.audio_available) useAudio('/audio','media/song.mp3');
    window.TonkatsuPreview={seek,position,metadata:meta};
    requestAnimationFrame(tick);
  } catch(err) { error('初始化失败：'+err.message); }
})();
