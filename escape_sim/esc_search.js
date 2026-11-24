const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
 p.on('pageerror', e => console.log('ERR', e.message));
 const q = process.argv[2] || '', n = +(process.argv[3] || 10), s0 = +(process.argv[4] || 1);
 for (let seed = s0; seed < s0 + n; seed++) {
  await p.goto(`file:///home/user/G/escape_sim/index.html?${q}&seed=${seed}`);
  const r = await p.evaluate(() => { let f = 0; while (f < 60 * 60 && !window.__sim().loopDone) { window.__tick(1 / 60); f++; }
    const S = window.__sim(); return { dur: +(f / 60).toFixed(2), lv: S.levelT, nears: S.nears, b: S.bounces }; });
  console.log(seed, JSON.stringify(r));
 } await b.close(); })();
