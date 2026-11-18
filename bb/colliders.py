"""Signed distance fields of the machine parts. The soft-body solver only
needs `scene.sdf(P, t)`; normals come from a numerical gradient so any
composition of parts works. Every part here has a matching visual mesh
built in scene.py from the same parameters."""
import numpy as np


class Floor:
    def __init__(self, z=0.0):
        self.z = z

    def sdf(self, P, t):
        return P[:, 2] - self.z


class Pedestal:
    """Concrete block with countersunk holes going all the way down."""

    def __init__(self, half_width, height, holes, hole_radius,
                 sink_radius, sink_depth, bevel=0.02):
        self.hw = half_width
        self.h = height
        self.holes = np.array(holes, float).reshape(-1, 2)
        self.rh = hole_radius
        self.rs = sink_radius
        self.ds = sink_depth
        self.bevel = bevel

    def sdf(self, P, t):
        c = np.array([0.0, 0.0, self.h / 2])
        b = np.array([self.hw, self.hw, self.h / 2]) - self.bevel
        q = np.abs(P - c) - b
        d_box = (np.linalg.norm(np.maximum(q, 0), axis=1)
                 + np.minimum(q.max(1), 0) - self.bevel)
        if len(self.holes) == 0:
            return d_box
        k = (self.rs - self.rh) / max(self.ds, 1e-6)
        z0 = self.h - self.ds
        cut = np.full(len(P), 1e9)
        for hx, hy in self.holes:
            r = np.hypot(P[:, 0] - hx, P[:, 1] - hy)
            c_i = (r - self.rh - k * np.maximum(0.0, P[:, 2] - z0)) / np.sqrt(1 + k * k)
            cut = np.minimum(cut, c_i)
        return np.maximum(d_box, -cut)


class Ring:
    """Thin gold torus lying flat (axis Z)."""

    def __init__(self, R, r, z):
        self.R, self.r, self.z = R, r, z
        self.slab = (z, r)

    def sdf(self, P, t):
        q0 = np.hypot(P[:, 0], P[:, 1]) - self.R
        return np.hypot(q0, P[:, 2] - self.z) - self.r


class FloatingRing:
    """Gold torus floating horizontally at (cx, cy); its height is a
    function of time (gentle bob)."""

    def __init__(self, cx, cy, R, r, z_fn, amp=0.0):
        self.cx, self.cy, self.R, self.r = cx, cy, R, r
        self.z_fn = z_fn
        self.slab = (z_fn(0.0), r + amp + 1e-3)

    def sdf(self, P, t):
        q0 = np.hypot(P[:, 0] - self.cx, P[:, 1] - self.cy) - self.R
        return np.hypot(q0, P[:, 2] - self.z_fn(t)) - self.r


class Sleeve:
    """Arc of a thick torus (a concrete sleeve sliding along a ring). Its
    centre angle is a function of time so the gate can open and close."""

    def __init__(self, R, r, z, half_span, angle_fn, groove=None):
        self.R, self.r, self.z = R, r, z
        self.hs = half_span
        self.angle_fn = angle_fn
        # groove = (radius offset, groove tube radius, depth): a shallow
        # channel on top of the sleeve that cradles the piece
        self.groove = groove
        self.slab = (z, r)
        self.friction = 0.02  # polished sleeve: slides under the piece

    def sdf(self, P, t):
        q0 = np.hypot(P[:, 0], P[:, 1]) - self.R
        d_t = np.hypot(q0, P[:, 2] - self.z) - self.r
        a = np.arctan2(P[:, 1], P[:, 0]) - self.angle_fn(t)
        a = (a + np.pi) % (2 * np.pi) - np.pi
        rxy = np.hypot(P[:, 0], P[:, 1])
        d = d_t
        if self.groove:
            off, rg, depth = self.groove
            zc = self.z + self.r + rg - depth
            d_g = np.hypot(rxy - (self.R - off), P[:, 2] - zc) - rg
            d = np.maximum(d, -d_g)
        # outside the arc the sleeve does not exist. No end-cap normals: the
        # sleeve only ever pushes out of its tube, so a piece slides off its
        # end instead of being shoved sideways by the moving end face.
        return np.where(np.abs(a) <= self.hs, d, 1e3)


class SceneSDF:
    def __init__(self, parts):
        self.parts = parts

    def sdf(self, P, t):
        d = self.parts[0].sdf(P, t)
        for p in self.parts[1:]:
            slab = getattr(p, "slab", None)
            if slab is None:
                d = np.minimum(d, p.sdf(P, t))
                continue
            # cheap lower bound outside a horizontal slab around the part
            zc, half = slab
            lb = np.abs(P[:, 2] - zc) - half
            near = lb < 0.05
            if near.any():
                dn = p.sdf(P[near], t)
                d[near] = np.minimum(d[near], dn)
            far = ~near
            d[far] = np.minimum(d[far], lb[far])
        return d

    def friction_of(self, P, t, default):
        """Friction of the closest part for each point (None = body default)."""
        best = np.full(len(P), np.inf)
        fr = np.full(len(P), float(default))
        for p in self.parts:
            d = p.sdf(P, t)
            m = d < best
            best[m] = d[m]
            f = getattr(p, "friction", None)
            fr[m] = default if f is None else f
        return fr

    def sdf_grad(self, P, t, eps=1e-3):
        d = self.sdf(P, t)
        g = np.empty_like(P)
        for k in range(3):
            o = np.zeros(3)
            o[k] = eps
            fp = self.sdf(P + o, t)
            fm = self.sdf(P - o, t)
            gk = (fp - fm) * 0.5
            # one-sided differences across discontinuities (e.g. the open end
            # of a sleeve) so the normal never points along a jump
            jp = np.abs(fp - d) > 0.05
            jm = np.abs(fm - d) > 0.05
            gk = np.where(jp & ~jm, d - fm, gk)
            gk = np.where(jm & ~jp, fp - d, gk)
            gk = np.where(jm & jp, 0.0, gk)
            g[:, k] = gk
        n = np.linalg.norm(g, axis=1, keepdims=True)
        return d, g / np.maximum(n, 1e-9)
