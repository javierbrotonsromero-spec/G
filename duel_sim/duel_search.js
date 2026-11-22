const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage();
 const q = process.argv[2], n = +(process.argv[3] || 30); const wins = [0, 0]; const rows = [];
 for (let seed = +(process.argv[4]||1); seed < +(process.argv[4]||1) + n; seed++) {
  await p.goto(`file:///home/user/G/duel_sim/index.html?${q}&seed=${seed}`);
  const r = await p.evaluate(() => { const hits = []; let parries = 0;
    onHit = (i, d, hp) => hits.push([window.__sim().vt, i, d]); onParry = () => parries++;
    let f = 0; while (f < 60 * 120 && !window.__sim().done) { window.__tick(1 / 60); f++; }
    const S = window.__sim(); let mg = hits.length ? hits[0][0] : 99; for (let k = 1; k < hits.length; k++) mg = Math.max(mg, hits[k][0] - hits[k - 1][0]);
    return { dur: +(f / 60).toFixed(1), win: S.winner, whp: S.winner >= 0 ? S.balls[S.winner].hp : -1, leads: S.lead.length, hits: hits.length, parries, mg: +mg.toFixed(1), first: hits.length ? +hits[0][0].toFixed(2) : -1 }; });
  if (r.win >= 0) wins[r.win]++; rows.push([seed, r]);
 }
 for (const [s, r] of rows) console.log(s, JSON.stringify(r));
 console.log(q, 'wins', wins); await b.close(); })();
