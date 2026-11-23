const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
 const q = process.argv[2], n = +(process.argv[3] || 8), s0 = +(process.argv[4] || 1);
 for (let seed = s0; seed < s0 + n; seed++) {
  await p.goto(`file:///home/user/G/hero_sim/index.html?${q}&seed=${seed}`);
  const r = await p.evaluate(() => { const fl = [], ev = []; let hits = 0, bh = 0, boss = -1;
    onFloor = (n) => fl.push(+window.__sim().vt.toFixed(1)); onEvolve = (t) => ev.push(+window.__sim().vt.toFixed(1));
    onHit = () => hits++; onBossHit = () => bh++; onBoss = () => boss = +window.__sim().vt.toFixed(1);
    let f = 0; while (f < 60 * 120 && !window.__sim().done) { window.__tick(1 / 60); f++; }
    let mg = fl[0]; for (let k = 1; k < fl.length; k++) mg = Math.max(mg, fl[k] - fl[k - 1]);
    return { dur: +(f / 60).toFixed(1), floors: fl.length, mg: +mg.toFixed(1), ev, hits, bh, boss, power: window.__sim().power }; });
  console.log(seed, JSON.stringify(r));
 } await b.close(); })();
