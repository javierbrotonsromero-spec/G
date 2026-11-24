const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
 p.on('pageerror', e => console.log('ERR', e.message));
 const mode = process.argv[2], n = +(process.argv[3] || 6), s0 = +(process.argv[4] || 1);
 const out = [];
 for (let seed = s0; seed < s0 + n; seed++) {
  await p.goto(`file:///home/user/G/loops12/index.html?mode=${mode}&seed=${seed}`);
  const r = await p.evaluate(() => { let f = 0; while (f < 60 * 45 && !window.__sim().loopDone) { window.__tick(1 / 60); f++; }
    const E = window.__ev(); const c = {}; for (const e of E) c[e[0]] = (c[e[0]] || 0) + 1;
    const ks = E.filter(e => e[0] === 'k' || e[0] === 'F').map(e => e[1]); return { dur: +(f / 60).toFixed(2), c, ks: ks.map(x => +x.toFixed(1)).join(',') }; });
  console.log(mode, seed, JSON.stringify(r));
 } await b.close(); })();
