const { chromium } = require('playwright');
const { spawn } = require('child_process'); const fs = require('fs');
const [mode, seed, outDir] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto(`file:///home/user/G/loops12/index.html?mode=${mode}&seed=${seed}`);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', '60', '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', outDir + '/video_noaudio.mp4']);
  let n = 0;
  const first = await p.evaluate(() => { window.__draw(); return document.getElementById('c').toDataURL('image/jpeg', 0.95); });
  ff.stdin.write(Buffer.from(first.split(',')[1], 'base64')); n++;
  while (n < 60 * 60) {
    const r = await p.evaluate(() => { window.__tick(1 / 60); if (window.__sim().loopDone) return null; window.__draw(); return document.getElementById('c').toDataURL('image/jpeg', 0.95); });
    if (!r) break; ff.stdin.write(Buffer.from(r.split(',')[1], 'base64')); n++;
  }
  fs.writeFileSync(outDir + '/events.json', JSON.stringify(await p.evaluate(() => window.__ev())));
  ff.stdin.end(); await new Promise(res => ff.on('close', res)); console.log(mode, 'frames', n); fs.writeFileSync(outDir + '/frames.txt', String(n)); await b.close(); })();
