import json, sys, wave
import numpy as np
ev = json.load(open(sys.argv[1])); D = float(sys.argv[2]); out = sys.argv[3]; mode = sys.argv[4]
SR = 48000; N = int(round(D * SR)); mix = np.zeros(N + SR * 4); rng = np.random.default_rng(len(mode))
seamless = mode in ('pendulum', 'poly')
WAVE = mode in ('pwave', 'spiral', 'bounce', 'helix')
def add(t, sig, g=1.0):
    i = int(round(t * SR)); j = min(len(mix), i + len(sig));
    if i < len(mix): mix[i:j] += sig[:j - i] * g
def T(x): return np.arange(int(x * SR)) / SR
def lp(x, k):
    y = np.empty_like(x); a = 0.0
    for i in range(len(x)): a += (x[i] - a) * k; y[i] = a
    return y
NZ = rng.uniform(-1, 1, SR * 5)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
PENT = [0, 3, 5, 7, 10]; MAJP = [0, 2, 4, 7, 9]
ROOT = {'pwave': 62, 'spiral': 60, 'bounce': 64, 'helix': 57, 'gates': 62, 'split': 60, 'morph': 64, 'shrink': 59, 'wall': 62, 'orbit': 57, 'galton': 64, 'corner': 60, 'chain': 65, 'paint': 62, 'pendulum': 55, 'poly': 57}[mode]
def scale(i, sc): return sc[i % 5] + 12 * (i // 5)
def pluck(m, dur=0.3, v=0.2):
    t = T(dur); f = mtof(m)
    s = np.sin(2*np.pi*f*t) + 0.45*np.sin(4*np.pi*f*t)*np.exp(-t/0.05) + 0.18*np.sign(np.sin(2*np.pi*f*t))*np.exp(-t/0.025)
    return s * np.exp(-t/(dur*0.4)) * np.minimum(1, t/0.002) * v
def bell(m, v=0.16):
    t = T(1.2); f = mtof(m)
    s = np.sin(2*np.pi*f*t)*np.exp(-t/0.6) + 0.4*np.sin(2*np.pi*2.0*f*t)*np.exp(-t/0.3) + 0.2*np.sin(2*np.pi*3.01*f*t)*np.exp(-t/0.12)
    return s * np.minimum(1, t/0.002) * v
def ting():
    t = T(0.9); s = sum(a*np.sin(2*np.pi*f*t)*np.exp(-t/d) for f, a, d in [(2637, .5, .5), (3951, .3, .35), (5274, .2, .2)])
    return s * 0.3 + lp(NZ[:len(t)], 0.3) * np.exp(-((t - 0.05) / 0.08) ** 2) * 0.5
def impact(x, big=False):
    L = 2.6 if big else 0.9; t = T(L)
    kick = np.sin(2*np.pi*np.cumsum(32 + (160 if big else 110)*np.exp(-t/0.06))/SR) * np.exp(-t/(0.9 if big else 0.3))
    glass = (NZ[:len(t)] - lp(NZ[:len(t)], 0.6)) * np.exp(-t/(0.5 if big else 0.15)) * (0.5 if big else 0.3)
    stab = sum(lp(2 * ((mtof(m + int(x * 7)) * t) % 1) - 1, 0.15) * np.exp(-t/(1.0 if big else 0.22)) * 0.1 for m in ([45, 57, 64, 69, 76] if big else [57, 64, 69]))
    noise = lp(NZ[:len(t)] * np.exp(-t/(1.2 if big else 0.25)), 0.05) * (3 if big else 0.8)
    return kick * (1.3 if big else 0.8) + glass + stab + noise
evs = sorted(ev, key=lambda e: e[1]); lastp = -1
for e in evs:
    k, t = e[0], e[1]
    if k == 'p':
        if t - lastp < 0.03: continue
        lastp = t; add(t, pluck(ROOT + scale(int(e[2]) % 15, PENT) + 12 * int(e[3] > 2)))
    elif k == 'n':
        sc = MAJP if not WAVE else PENT; i = int(e[2]); i = i % 13 if WAVE else i
        if WAVE:
            if t - lastp < 0.028: continue
            lastp = t; add(t, pluck(ROOT + scale(i, PENT), 0.35, 0.16))
        else: add(t, bell(ROOT + scale(i, sc), 0.12 if mode == 'pendulum' else 0.14))
    elif k == 'a': add(t, impact(float(e[2])), 0.5 + 0.5 * float(e[2]))
    elif k == 't': add(t, ting())
    elif k == 'k': add(t, impact(float(e[2])), 0.8)
    elif k == 'F': add(t, impact(1.0, True), 1.0)
fin = next((e[1] for e in evs if e[0] == 'F'), D)
if WAVE:
    beats = 36; bl = D / beats; BASS = [ROOT - 29, ROOT - 26, ROOT - 31]
    for tgt in (D / 2, D):
        L = 2.2; t = T(L); y = np.zeros(len(t)); a = 0.0
        for i in range(len(t)): a += (NZ[i] - a) * (0.01 + 0.4 * (t[i] / L) ** 2); y[i] = a
        add(tgt - L, (y * 0.22 + np.sin(2*np.pi*np.cumsum(110 * 2 ** (3 * t / L))/SR) * 0.05) * (t / L) ** 2)
    for i in range(beats):
        tb = i * bl; inten = 0.6 + 0.4 * abs(np.sin(np.pi * tb / D * 2))
        tt = T(0.25); add(tb, np.sin(2*np.pi*np.cumsum(46 + 130*np.exp(-tt/0.03))/SR) * np.exp(-tt/0.12), 0.55)
        if i % 2: add(tb, lp(NZ[:int(.16*SR)], .45) * np.exp(-T(.16)/.05), 0.2)
        for h in range(4):
            th = T(0.035); x = NZ[:len(th)]; add(tb + h * bl / 4, (x - lp(x, .5)) * np.exp(-th/.007), 0.06 + 0.04 * (h % 2 == 0))
        m = BASS[(i // 4) % 3]
        for h in range(2):
            tt = T(bl * 0.48); f0 = mtof(m + 12); add(tb + h * bl / 2, lp(2 * ((f0 * tt) % 1) - 1, 0.06 + 0.08 * inten) * np.exp(-tt/0.15), 0.26)
elif not seamless:
    L = 2.0; t = T(L); y = np.zeros(len(t)); a = 0.0
    for i in range(len(t)): a += (NZ[i] - a) * (0.01 + 0.4 * (t[i] / L) ** 2); y[i] = a
    add(max(0, fin - L), (y * 0.25 + np.sin(2*np.pi*np.cumsum(110 * 2 ** (3 * t / L))/SR) * 0.06) * (t / L) ** 2)
    beats = max(8, round(D * 128 / 60 / 4) * 4); bl = D / beats; BASS = [ROOT - 29, ROOT - 29, ROOT - 26, ROOT - 31]
    for i in range(beats):
        tb = i * bl; inten = min(1, tb / max(1, fin))
        tt = T(0.25); add(tb, np.sin(2*np.pi*np.cumsum(46 + 130*np.exp(-tt/0.03))/SR) * np.exp(-tt/0.12), 0.5)
        if i % 2: add(tb, lp(NZ[:int(.16*SR)], .45) * np.exp(-T(.16)/.05), 0.12 + 0.12 * inten)
        hs = 2 if inten < 0.5 else 4
        for h in range(hs):
            th = T(0.035); x = NZ[:len(th)]; add(tb + h * bl / hs, (x - lp(x, .5)) * np.exp(-th/.007), 0.06 + 0.05 * inten)
        m = BASS[(i // 4) % 4]
        for h in range(2):
            tt = T(bl * 0.48); f0 = mtof(m + 12); add(tb + h * bl / 2, lp(2 * ((f0 * tt) % 1) - 1, 0.04 + 0.1 * inten) * np.exp(-tt/0.15), 0.26)
else:
    bars = max(2, round(D * 90 / 60 / 4)); bl = D / bars
    CH = [[0, 4, 7], [-3, 0, 4], [5, 9, 12], [7, 11, 14]]
    for i in range(bars):
        tb = i * bl; t = T(bl + 0.6); ch = CH[i % 4]
        pad = sum(np.sin(2*np.pi*mtof(ROOT - 12 + c)*t) + 0.3*np.sin(2*np.pi*mtof(ROOT + c)*t*1.003) for c in ch)
        env = np.minimum(1, t / 0.4) * np.clip((bl + 0.6 - t) / 0.6, 0, 1)
        add(tb, pad * env * 0.035)
        tt = T(0.5); add(tb, np.sin(2*np.pi*np.cumsum(45 + 60*np.exp(-tt/0.05))/SR) * np.exp(-tt/0.3), 0.25)
tail = mix[N:].copy(); mix = mix[:N]; mix[:len(tail)] += tail[:N]
mix /= np.abs(mix).max() / 0.9
w = wave.open(out, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close(); print('ok', mode)
