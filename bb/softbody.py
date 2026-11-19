"""Position-based soft-body solver (numpy).

Each piece is a closed triangle surface simulated as particles with:
  * edge-length constraints (inextensible skin -> folds/wrinkles when soft),
  * a global volume constraint (pressure, like a filled balloon),
  * shape matching (Mueller et al. 2005) whose strength is the rigidity:
    softness 0 -> perfectly rigid ball, softness 1 -> a heavy jelly/foil blob,
  * SDF collisions with friction and a little restitution.
Deterministic: the same config always produces the same motion."""
import numpy as np


def softness_params(s, intensity=1.0):
    s = float(np.clip(s * intensity, 0.0, 1.0))
    return dict(
        alpha=10 ** (-1.3 * s ** 1.15),       # shape-matching stiffness / substep
        beta=0.6 * s,                          # allowed linear (squash) deformation
        volume=1.0,                            # keeps the skin taut: smooth, no foil creases
        friction=0.25 + 0.45 * s,
        restitution=0.12 * (1 - s) ** 2,
        damping=0.002 + 0.03 * s,
        edge_k=0.6,
        softness=s,
    )


class SoftBody:
    def __init__(self, verts, tris, position, softness, intensity=1.0,
                 velocity=(0, 0, 0), thickness=0.006):
        self.tris = np.asarray(tris)
        rest = np.asarray(verts, float)
        self.q = rest - rest.mean(0)               # rest shape, centred
        self.x = self.q + np.asarray(position, float)
        self.v = np.tile(np.asarray(velocity, float), (len(rest), 1))
        self.n = len(rest)
        self.p = softness_params(softness, intensity)
        self.th = thickness
        e = np.concatenate([self.tris[:, [0, 1]], self.tris[:, [1, 2]], self.tris[:, [2, 0]]])
        e.sort(1)
        self.e = np.unique(e, axis=0)
        self.L0 = np.linalg.norm(rest[self.e[:, 1]] - rest[self.e[:, 0]], axis=1)
        self.deg = np.bincount(self.e.ravel(), minlength=self.n).astype(float)
        self.V0 = self.volume(self.x)
        Aqq = self.q.T @ self.q
        self.Aqq_inv = np.linalg.inv(Aqq)
        self.impact = 0.0
        self.alive = True
        self.target = None   # path centre the body is tethered to (or None)
        self.tether = 0.08   # tether strength per substep
        self.radius = float(np.linalg.norm(self.q, axis=1).max())
        self.max_stretch = 2.3
        self.funnel = None   # (axis_x, axis_y, plane_z, strength) while squeezing

    # ------------------------------------------------------------------
    def volume(self, x):
        a, b, c = x[self.tris[:, 0]], x[self.tris[:, 1]], x[self.tris[:, 2]]
        return np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0

    def _edges(self, x, k):
        e0, e1 = self.e[:, 0], self.e[:, 1]
        d = x[e1] - x[e0]
        L = np.linalg.norm(d, axis=1)
        corr = ((L - self.L0) / np.maximum(L, 1e-9))[:, None] * d * 0.5
        acc = np.zeros_like(x)
        for k_ in range(3):
            acc[:, k_] += np.bincount(e0, corr[:, k_], self.n)
            acc[:, k_] -= np.bincount(e1, corr[:, k_], self.n)
        x += k * 1.6 * acc / self.deg[:, None]

    def _volume(self, x):
        t = self.tris
        a, b, c = x[t[:, 0]], x[t[:, 1]], x[t[:, 2]]
        g = np.zeros_like(x)
        gb = np.cross(b, c)
        gc = np.cross(c, a)
        ga = np.cross(a, b)
        for k_ in range(3):
            g[:, k_] += np.bincount(t[:, 0], gb[:, k_], self.n)
            g[:, k_] += np.bincount(t[:, 1], gc[:, k_], self.n)
            g[:, k_] += np.bincount(t[:, 2], ga[:, k_], self.n)
        g /= 6.0
        C = self.volume(x) - self.V0 * self.p["volume"]
        lam = C / max((g * g).sum(), 1e-12)
        x -= lam * g

    def _shape_match(self, x, w=None):
        """Shape matching; contact particles get a large weight so the
        fitted (rigid) motion satisfies the collisions."""
        p = self.p
        if w is None:
            c = x.mean(0)
            q = self.q
        else:
            ws = w.sum()
            c = (w[:, None] * x).sum(0) / ws
            q = self.q - (w[:, None] * self.q).sum(0) / ws
        Apq = ((x - c) * (w[:, None] if w is not None else 1.0)).T @ q
        U, S, Vt = np.linalg.svd(Apq)
        R = U @ Vt
        if np.linalg.det(R) < 0:
            U[:, -1] *= -1
            R = U @ Vt
        M = R
        if p["beta"] > 0:
            A = Apq @ self.Aqq_inv
            det = np.linalg.det(A)
            if det > 1e-6:
                A = A / np.cbrt(det)
                M = p["beta"] * A + (1 - p["beta"]) * R
        goal = q @ M.T + c
        x += p["alpha"] * (goal - x)

    def _collide(self, x, xprev, world, t):
        d = world.sdf(x, t)
        m = d < self.th
        if not m.any():
            return None
        idx = np.nonzero(m)[0]
        dd, nn = world.sdf_grad(x[idx], t)
        x[idx] += (self.th - dd)[:, None] * nn
        # Coulomb-ish positional friction
        disp = x[idx] - xprev[idx]
        dn = (disp * nn).sum(1, keepdims=True)
        dt_ = disp - dn * nn
        fr = world.friction_of(x[idx], t, self.p["friction"]) if hasattr(world, "friction_of") else self.p["friction"]
        x[idx] -= np.asarray(fr).reshape(-1, 1) * dt_
        return idx, nn

    # ------------------------------------------------------------------
    # A substep is split in phases so several bodies can be solved together
    # (piece-vs-piece contacts are projected like any other constraint).
    def begin(self, dt, gravity=-9.81):
        p = self.p
        self.v_pre = self.v.copy()
        self.v[:, 2] += gravity * dt
        vm = self.v.mean(0)  # damp only internal (jiggle) motion, not the fall
        self.v = vm + (self.v - vm) * (1 - p["damping"])
        self.xprev = self.x.copy()
        self.xp = self.x + self.v * dt
        self.contact = None
        self.pair_idx = []
        self.pair_n = []

    def solve(self, world, t, last):
        p = self.p
        x = self.xp
        rigid = p["alpha"] > 0.5
        if not rigid:
            self._edges(x, p["edge_k"])
            self._volume(x)
        c = self._collide(x, self.xprev, world, t)
        if c is not None:
            self.contact = c
        if rigid or last:
            w = np.ones(self.n)
            if c is not None:
                w[c[0]] = 60.0
            for idx in self.pair_idx:
                w[idx] = 60.0
            self._shape_match(x, w)
        if last and self.target is not None:
            x += self.tether * (self.target - x.mean(0))
        if last and self.funnel is not None and not rigid:
            # material above an opening flows towards its axis (hourglass
            # squeeze) instead of spreading into a disc on the rim
            ax, ay, zf, k = self.funnel
            h = x[:, 2] - zf
            m = h > -0.02
            if m.any():
                w = np.exp(-np.maximum(h[m], 0.0) / (0.6 * self.radius))
                x[m, 0] -= k * w * (x[m, 0] - ax)
                x[m, 1] -= k * w * (x[m, 1] - ay)
        if not rigid:
            # long-range stretch limit: no part of the piece may drift further
            # than max_stretch radii from its centre (Jacobi edge constraints
            # alone are too weak for that)
            c = x.mean(0)
            r = x - c
            L = np.linalg.norm(r, axis=1)
            lim = self.max_stretch * self.radius
            over = L > lim
            if over.any():
                x[over] = c + r[over] * (lim / L[over])[:, None]
        if last and not rigid:
            c = self._collide(x, self.xprev, world, t)
            if c is not None:
                self.contact = c

    def finish(self, dt):
        p = self.p
        x = self.xp
        self.v = (x - self.xprev) / dt
        self.impact = 0.0
        groups = []
        if self.contact is not None:
            groups.append((self.contact[0], self.contact[1], True))
        for idx, nn in zip(self.pair_idx, self.pair_n):
            groups.append((idx, nn, False))
        for idx, nn, world_contact in groups:
            vn_pre = (self.v_pre[idx] * nn).sum(1)
            vn_new = (self.v[idx] * nn).sum(1)
            hit = vn_pre < -0.4
            if world_contact and hit.any():
                self.impact = float(-vn_pre[hit].mean()) * hit.mean() ** 0.25
            # PBD push-out creates fake separating velocity: clamp it to the
            # restitution target so impacts don't launch the piece
            target = np.where(hit, -p["restitution"] * vn_pre, 0.0) if world_contact else 0.0
            excess = np.maximum(vn_new - target, 0.0)
            self.v[idx] -= excess[:, None] * nn
            # same at body level: push-outs propagated by shape matching must
            # not turn into whole-body velocity away from the contact
            nbar = nn.mean(0)
            ln = np.linalg.norm(nbar)
            if ln > 0.3:
                nbar /= ln
                vb = self.v.mean(0) @ nbar
                vb_pre = self.v_pre.mean(0) @ nbar
                tb = max(0.0, -p["restitution"] * vb_pre) if world_contact else 0.0
                if vb > tb:
                    self.v -= (vb - tb) * nbar
        if p["alpha"] > 0.5 and groups:  # rigid: keep a coherent rigid-body velocity
            self.v[:] = (self.v.mean(0) + self._rigid_spin(x)) * 0.992  # rolling resistance
        # safety: nothing in this kind of video ever gets launched upwards
        vm = self.v.mean(0)
        if vm[2] > 1.2:
            self.v[:, 2] -= vm[2] - 1.2
        hs = np.hypot(vm[0], vm[1])
        if hs > 3.0:
            self.v[:, :2] -= vm[:2] * (1 - 3.0 / hs)
        sp = np.linalg.norm(self.v - vm, axis=1)
        fast = sp > 6.0
        if fast.any():
            self.v[fast] = vm + (self.v[fast] - vm) * (6.0 / sp[fast])[:, None]
        self.x = x
        if self.x[:, 2].max() < -0.5:
            self.alive = False

    def step(self, dt, world, t, gravity=-9.81, iters=3):
        step_all([self], dt, world, t, gravity, iters)

    def _rigid_spin(self, x):
        # keep angular motion of a rigid body after averaging linear velocity
        c = x.mean(0)
        r = x - c
        L = np.cross(r, self.v - self.v.mean(0)).sum(0)
        I = (r * r).sum() * np.eye(3) - r.T @ r
        try:
            w = np.linalg.solve(I + 1e-9 * np.eye(3), L)
        except np.linalg.LinAlgError:
            return 0.0
        return np.cross(w, r)


def vertex_normals(x, tris, n):
    a, b, c = x[tris[:, 0]], x[tris[:, 1]], x[tris[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.zeros((n, 3))
    for k in range(3):
        for j in range(3):
            vn[:, k] += np.bincount(tris[:, j], fn[:, k], n)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


_NT, _NP = 24, 48  # angular bins (theta, phi) of the star-shaped proxy


def _bins(d):
    th = np.arccos(np.clip(d[:, 2], -1, 1))
    ph = np.arctan2(d[:, 1], d[:, 0])
    it = np.minimum((th / np.pi * _NT).astype(int), _NT - 1)
    ip = np.minimum(((ph + np.pi) / (2 * np.pi) * _NP).astype(int), _NP - 1)
    return it * _NP + ip


def _star_proxy(Q):
    """Radius of body Q per direction from its centroid (pieces stay
    star-shaped), with the outermost vertex of each bin."""
    c = Q.xp.mean(0)
    r = Q.xp - c
    rad = np.linalg.norm(r, axis=1)
    b = _bins(r / np.maximum(rad, 1e-9)[:, None])
    R = np.zeros(_NT * _NP)
    np.maximum.at(R, b, rad)
    owner = np.full(_NT * _NP, -1)
    order = np.argsort(rad)
    owner[b[order]] = order  # last write = largest radius
    # fill empty bins from neighbours
    G = R.reshape(_NT, _NP)
    O = owner.reshape(_NT, _NP)
    for _ in range(4):
        empty = G == 0
        if not empty.any():
            break
        for sh in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            Gs = np.roll(G, sh, axis=(0, 1))
            Os = np.roll(O, sh, axis=(0, 1))
            m = empty & (Gs > G)
            G[m] = Gs[m]
            O[m] = Os[m]
    return c, G.ravel(), O.ravel()


def collide_pair(A, B, th=0.012):
    """Piece-vs-piece contact (O(N), robust to deep overlap): particles of
    each body found inside the other's star-shaped hull are pushed out
    radially; the other body's surface is pushed back equally."""
    lo = np.maximum(A.xp.min(0), B.xp.min(0)) - th
    hi = np.minimum(A.xp.max(0), B.xp.max(0)) + th
    if np.any(lo > hi):
        return
    for P, Q in ((A, B), (B, A)):
        ia = np.nonzero(np.all((P.xp >= lo) & (P.xp <= hi), axis=1))[0]
        if len(ia) == 0:
            continue
        c, R, O = _star_proxy(Q)
        r = P.xp[ia] - c
        rad = np.linalg.norm(r, axis=1)
        d = r / np.maximum(rad, 1e-9)[:, None]
        b = _bins(d)
        sd = rad - R[b]
        hit = (sd < th) & (O[b] >= 0)
        if not hit.any():
            continue
        corr = ((th - sd[hit]) * 0.5)[:, None] * d[hit]
        ih, jh = ia[hit], O[b[hit]]
        np.add.at(P.xp, ih, corr)
        np.add.at(Q.xp, jh, -corr)
        P.pair_idx.append(ih)
        P.pair_n.append(d[hit])
        Q.pair_idx.append(jh)
        Q.pair_n.append(-d[hit])


def step_all(bodies, dt, world, t, gravity=-9.81, iters=3, targets=None):
    if targets is not None:
        for b, tg in zip(bodies, targets):
            b.target = tg
    live = [b for b in bodies if b.alive]
    for b in live:
        b.begin(dt, gravity)
    for it in range(iters):
        last = it == iters - 1
        for i in range(len(live)):
            for j in range(i + 1, len(live)):
                collide_pair(live[i], live[j])
        for b in live:
            b.solve(world, t, last)
    for b in live:
        b.finish(dt)
