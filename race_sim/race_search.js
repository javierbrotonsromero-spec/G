const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
 const q = process.argv[2], n = +(process.argv[3] || 10), s0 = +(process.argv[4] || 1);
 for (let seed = s0; seed < s0 + n; seed++) {
  await p.goto(`file:///home/user/G/race_sim/index.html?${q}&seed=${seed}`);
  const r = await p.evaluate(() => { const kills = []; let bump = 0;
    onKill = (id, left) => kills.push(+window.__sim().vt.toFixed(1)); onBumper = () => bump++;
    let f = 0; while (f < 60 * 120 && !window.__sim().done) { window.__tick(1 / 60); f++; }
    const S = window.__sim(); let mg = kills[0]; for (let k = 1; k < kills.length; k++) mg = Math.max(mg, kills[k] - kills[k - 1]);
    const spread = S.balls.length; return { dur: +(f / 60).toFixed(1), kills, mg: +mg.toFixed(1), bump, win: S.winner }; });
  console.log(seed, JSON.stringify(r));
 } await b.close(); })();
