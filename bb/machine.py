"""The 'ring gates' contraption from the reference: pieces drop onto
concrete sleeves riding on thin gold rings; the sleeves turn away, the
pieces fall to the next ring and finally onto a concrete pedestal with
countersunk holes. Rigid pieces get stuck in the holes; soft ones squeeze
through. Also the timeline (steps, gate angles) and the simulation driver."""
import math
import numpy as np

from . import colliders as C
from .meshgen import make_piece
from .softbody import SoftBody, step_all


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)  # smootherstep


class Machine:
    def __init__(self, cfg, hole_offset=None):
        self.cfg = cfg
        m = cfg["machine"]
        tm = cfg["timing"]
        self.n = int(m["pieces"])
        self.orient = math.radians(m.get("orientation", 0.0))
        self.piece_angles = [self.orient + 2 * math.pi * i / self.n for i in range(self.n)]
        self.turn = math.pi / self.n  # how far a gate turns to open
        self.speed = float(tm["speed"])
        self.fps = cfg["render"]["fps"]
        self.step_dur = float(tm["step_duration"])
        self.steps = cfg["progression"]["steps"]
        self.frames_per_step = int(round(self.step_dur * self.fps))
        self.total_frames = self.frames_per_step * len(self.steps)
        ped = m["pedestal"]
        self.ped = ped
        if hole_offset is None:
            hole_offset = ped["hole_offset"]
        self.hole_offset = None if hole_offset == "auto" else float(hole_offset)
        self.layout = m.get("layout", "rings")
        if self.layout == "rings":
            self.hole_offset = float(m["ring_offset"])  # a hole under every ring

    # ------------------------------------------------------------ timeline
    def gate_angle(self, gi, t):
        """Rotation of gate gi's sleeves at local step time t (seconds).
        0 = closed (sleeves under the pieces), self.turn = open."""
        tm = self.cfg["timing"]
        c0, cd = tm["gate_close"]
        opens = tm["gate_open"]
        o0 = opens[min(gi, len(opens) - 1)]
        d = tm["gate_turn"]
        closing = ease_in_out((t - c0) / max(cd, 1e-6))
        opening = ease_in_out((t - o0) / max(d, 1e-6))
        # alternate direction per gate for a nicer counter-rotation
        sgn = 1 if gi % 2 == 0 else -1
        return sgn * self.turn * ((1 - closing) + opening)

    def step_of_frame(self, f):
        si = min(f // self.frames_per_step, len(self.steps) - 1)
        lf = f - si * self.frames_per_step
        return si, lf, lf / self.fps

    # ------------------------------------------------------------ colliders
    def holes_xy(self, offset):
        if offset < 1e-6:
            return [(0.0, 0.0)]
        return [(offset * math.cos(a), offset * math.sin(a)) for a in self.piece_angles]

    # ------------------------------------------------------------ rings layout
    def ring_xy(self, i):
        a = self.piece_angles[i]
        d = self.cfg["machine"]["ring_offset"]
        return np.array([d * math.cos(a), d * math.sin(a)])

    def ring_z(self, row, i, t):
        """Floating height of ring `row` above piece i at machine time t."""
        rg = self.cfg["machine"]["rings"][row]
        ph = 1.7 * i + 0.9 * row
        return rg["height"] + rg.get("bob", 0.0) * math.sin(2 * math.pi * t / rg.get("period", 2.6) + ph)

    def ring_major(self, rg):
        return rg["inner"] + rg["tube"]

    def world(self, offset, with_holes=True, wires=True, rings=True):
        m = self.cfg["machine"]
        parts = [C.Floor(0.0)]
        ped = m["pedestal"]
        parts.append(C.Pedestal(ped["half_width"], ped["height"],
                                self.holes_xy(offset) if with_holes else [],
                                ped["hole_radius"], ped["sink_radius"], ped["sink_depth"]))
        if self.layout == "rings":
            if rings:
                for row, rg in enumerate(m["rings"]):
                    for i in range(self.n):
                        cx, cy = self.ring_xy(i)
                        parts.append(C.FloatingRing(cx, cy, self.ring_major(rg), rg["tube"],
                                                    (lambda t, row=row, i=i: self.ring_z(row, i, t)),
                                                    rg.get("bob", 0.0)))
            return C.SceneSDF(parts)
        for gi, g in enumerate(m["gates"]):
            if wires:
                parts.append(C.Ring(g["radius"] + self.wire_offset(g), g["wire"],
                                    g["height"] - self.wire_drop(g)))
            hs = math.radians(g["span"]) / 2
            for a in self.piece_angles:
                parts.append(C.Sleeve(g["radius"], g["sleeve"], g["height"], hs,
                                      (lambda t, a=a, gi=gi: a + self.gate_angle(gi, t)),
                                      groove=self.groove()))
        return C.SceneSDF(parts)

    def wire_offset(self, g=None):
        """The gold wire runs outside and below the sleeve centre line (still
        hidden inside the sleeve), so a released piece always falls first and
        then rolls off the wire towards the inside."""
        g = g or self.cfg["machine"]["gates"][0]
        return 0.72 * g["sleeve"]

    def wire_drop(self, g):
        return 0.36 * g["sleeve"]

    def groove(self):
        m = self.cfg["machine"]
        return (0.0, m["piece_size"] * 1.12, m.get("groove_depth", 0.045))

    # ------------------------------------------------------------ pieces
    def spawn(self, softness, intensity):
        m = self.cfg["machine"]
        tm = self.cfg["timing"]
        verts, tris = make_piece(m["piece_shape"], m["piece_size"], m["piece_detail"])
        r = m["gates"][0]["radius"] if (self.layout == "gates" and m.get("gates")) else m.get("ring_offset", 0.5)
        bodies = []
        for i, a in enumerate(self.piece_angles):
            # tiny deterministic stagger so the two pieces don't move like clones
            z = tm["spawn_height"] + 0.12 * i
            pos = (r * math.cos(a), r * math.sin(a), z)
            bodies.append(SoftBody(verts, tris, pos, softness, intensity))
        return bodies, tris

    # ------------------------------------------------------------ simulate
    def simulate(self, offset, steps=None, log=print, frames_limit=None):
        """Choreographed path + simulated soft skin.

        The centre path of every piece is built from real ballistic falls,
        analytic bounces and exact resting heights measured against the
        machine geometry (see build_paths). Rigid steps are that path
        exactly; softer steps simulate the soft body around the path with an
        elastic tether, real collisions and a 'drain' phase where the piece
        squeezes through the hole (deeper and faster the softer it is).
        Returns positions[frame] -> list of (n,3) arrays or None,
        impacts[frame] -> list of floats, tris."""
        tm = self.cfg["timing"]
        intensity = self.cfg["effects"]["deform_intensity"]
        sub = int(tm["substeps"])
        dt = self.speed / self.fps / sub
        # the choreographed path clears the thin gold wires; leaving them out
        # of the soft-skin collisions stops jelly from draping over them
        world = self.world(offset, wires=False)
        steps = range(len(self.steps)) if steps is None else steps
        nf = self.frames_per_step if frames_limit is None else frames_limit
        verts, tris = make_piece(self.cfg["machine"]["piece_shape"],
                                 self.cfg["machine"]["piece_size"],
                                 self.cfg["machine"]["piece_detail"])
        q = verts - verts.mean(0)
        rings = self.layout == "rings"
        if not rings:
            cen, rot, impacts = self.build_paths(world, q, nf * sub, dt)
        out_pos, out_imp = {}, {}

        for si in steps:
            st = self.steps[si]
            s_ = float(st["softness"]) * intensity
            if rings:
                cen, impacts = self.build_ring_paths(q, nf * sub, dt, s_)
                rot = [np.repeat(np.eye(3)[None], nf * sub, 0) for _ in range(self.n)]
            if s_ <= 0.02:
                for lf in range(nf):
                    k = lf * sub
                    f = si * self.frames_per_step + lf
                    out_pos[f] = [(q @ rot[i][k].T + cen[i][k]).astype(np.float32)
                                  for i in range(self.n)]
                    out_imp[f] = [impacts[i][lf * sub:(lf + 1) * sub].max() for i in range(self.n)]
            else:
                paths = cen if rings else self._drain_paths(np.stack(cen, 1), s_, offset, dt)
                bodies, _ = self.spawn(st["softness"], intensity)
                for i, b in enumerate(bodies):
                    b.x = q @ rot[i][0].T + paths[i][0]
                    b.tether = 0.09 - 0.05 * s_
                for lf in range(nf):
                    f = si * self.frames_per_step + lf
                    out_pos[f] = [b.x.astype(np.float32).copy() if b.alive else None for b in bodies]
                    fi = [0.0] * self.n
                    for k in range(sub):
                        kk = lf * sub + k
                        if rings:
                            for bi, b in enumerate(bodies):
                                fz, fk = self.funnels[bi][kk]
                                b.funnel = None if np.isnan(fz) else (*self.ring_xy(bi), fz, fk)
                        step_all(bodies, dt, world, kk * dt, targets=[p[kk] for p in paths])
                        for bi, b in enumerate(bodies):
                            fi[bi] = max(fi[bi], b.impact)
                    out_imp[f] = fi
            log(f"  step {si + 1}/{len(self.steps)} simulated (softness {st['softness']:.2f})")
        return {"positions": out_pos, "impacts": out_imp, "tris": tris}

    # ------------------------------------------------------------ ring choreography
    def build_ring_paths(self, q, n_sub, dt, s):
        """Each piece drops onto its floating ring. Depending on softness it
        rests on top (rigid), sinks into it, or squeezes through, falls onto
        the pedestal and then sinks / squeezes into the hole below.
        Thresholds make the progression readable:
          ring: passes from 45% soft;  hole: passes from 70% soft."""
        m = self.cfg["machine"]
        tm = self.cfg["timing"]
        g = 9.81
        rb = m["piece_size"]
        rows = m["rings"]
        T = np.arange(n_sub) * dt
        stages = []  # (kind, row) ring rows then the hole
        for row in range(len(rows)):
            th = 0.45 if len(rows) == 1 else 0.3 + 0.25 * row / (len(rows) - 1)
            stages.append(("ring", row, th))
        stages.append(("hole", None, 0.7))
        hole_world = self.world(self.hole_offset, rings=False)
        cens, imps, funs = [], [], []
        for i in range(self.n):
            xy = self.ring_xy(i)
            # rest offsets measured against the real geometry
            offs = []
            for row, rg in enumerate(rows):
                w = C.SceneSDF([C.FloatingRing(xy[0], xy[1], self.ring_major(rg), rg["tube"],
                                               lambda t, h=rg["height"]: h)])
                offs.append(self.rest_z(w, q, xy, 0.0, rg["height"] + 3 * rb) - rg["height"])
            z_ped = self.rest_z(hole_world, q, xy, 0.0, m["pedestal"]["height"] + 3 * rb)
            cen = np.zeros((n_sub, 3))
            cen[:, :2] = xy
            imp = np.zeros(n_sub)
            fun = np.full((n_sub, 2), np.nan)  # (plane z, strength) while squeezing
            z = tm["spawn_height"] + 0.15 * i
            v = 0.0
            mode = "fall"
            stage = 0
            t_mode = 0.0
            z_base = None
            v_imp = 0.0
            e = 0.3 * (1 - s) ** 2 + 0.04
            for k, t in enumerate(T):
                if mode == "fall":
                    v += g * dt
                    z -= v * dt
                    kind, row, th = stages[stage]
                    support = (self.ring_z(row, i, t) + offs[row]) if kind == "ring" else z_ped
                    if z <= support:
                        z = support
                        v_imp = v
                        imp[k] = v
                        v = 0.0
                        mode, t_mode = "rest", t
                elif mode == "rest":
                    kind, row, th = stages[stage]
                    base = (self.ring_z(row, i, t) + offs[row]) if kind == "ring" else z_ped
                    tau = t - t_mode
                    # decaying bounces
                    vb, b, tt = v_imp * e, 0.0, tau
                    while vb > 0.25:
                        d = 2 * vb / g
                        if tt < d:
                            b = vb * tt - 0.5 * g * tt * tt
                            break
                        tt -= d
                        vb *= e
                    z = base + b
                    wait = (0.32 if kind == "ring" else 0.22) + 0.08 * i
                    if s > 0.02 and tau > wait:
                        mode, t_mode, z_base = "squeeze", t, (kind, row, th)
                elif mode == "squeeze":
                    kind, row, th = z_base
                    base = (self.ring_z(row, i, t) + offs[row]) if kind == "ring" else z_ped
                    tau = t - t_mode
                    passes = s >= th
                    # a passing piece squeezes through slowly enough for the
                    # skin to stretch into a clean hourglass / sausage
                    acc = (2.2 + 3.0 * s) if passes else (1.2 + 10.0 * s)
                    depth = 0.5 * acc * tau * tau
                    if not passes:
                        dmax = (s / th) ** 1.3 * 0.85 * rb
                        # ease into the stuck depth (no hard stop)
                        depth = dmax * (1 - math.exp(-depth / max(dmax, 1e-6)))
                    z = base - depth
                    if passes:
                        plane = self.ring_z(row, i, t) if kind == "ring" else m["pedestal"]["height"]
                        fun[k] = (plane, 0.008 + 0.017 * s)
                    through = (offs[row] + rb * 1.05) if kind == "ring" else (z_ped - m["pedestal"]["height"] + 2.2 * rb)
                    if passes and depth >= through:
                        v = acc * tau
                        if stage + 1 < len(stages):
                            stage += 1
                            mode = "fall"
                        else:
                            mode = "gone"
                elif mode == "gone":
                    v += g * dt
                    z -= v * dt
                    fun[k] = (m["pedestal"]["height"], 0.008 + 0.017 * s)
                cen[k, 2] = z
            # keep the funnel on while the piece is still crossing the
            # opening it just squeezed through (a few tenths of a second)
            last = None
            for k in range(n_sub):
                if not np.isnan(fun[k, 0]):
                    last = (k, fun[k].copy())
                elif last is not None and k - last[0] < int(0.25 / dt):
                    fun[k] = last[1]
            cens.append(cen)
            imps.append(imp)
            funs.append(fun)
        self.funnels = funs
        return cens, imps

    # ------------------------------------------------------------ choreography
    def rest_z(self, world, q, xy, t, z_hi):
        """Lowest centre height at xy where the (upright) piece touches
        nothing, found by bisection against the real collider SDF."""
        sample = q[:: max(1, len(q) // 400)]

        def hit(z):
            return world.sdf(sample + np.array([xy[0], xy[1], z]), t).min() < 0.004

        hi = z_hi
        lo = hi - 0.02
        while lo > 0 and not hit(lo):  # march down to the first contact
            hi, lo = lo, lo - 0.02
        for _ in range(20):
            mid = (lo + hi) / 2
            if hit(mid):
                lo = mid
            else:
                hi = mid
        return hi

    def release_time(self, gi):
        hs = math.radians(self.cfg["machine"]["gates"][gi]["span"]) / 2
        o0 = self.cfg["timing"]["gate_open"][min(gi, len(self.cfg["timing"]["gate_open"]) - 1)]
        for k in range(2000):
            t = o0 + k * 0.002
            if abs(self.gate_angle(gi, t)) >= hs * 0.92:
                return t
        return o0

    def build_paths(self, world, q, n_sub, dt):
        m = self.cfg["machine"]
        tm = self.cfg["timing"]
        g = 9.81
        rb = m["piece_size"]
        gates = m["gates"]
        ped = m["pedestal"]
        top = ped["height"]
        holes = np.array(self.holes_xy(self.hole_offset or 0.0))
        T = np.arange(n_sub) * dt
        t_rest = tm["gate_open"][0] - 0.05  # gates are closed then
        cens, rots, imps = [], [], []
        for i, a in enumerate(self.piece_angles):
            u = np.array([math.cos(a), math.sin(a)])
            delay = 0.07 * i  # tiny stagger: pieces never move like clones
            # key points --------------------------------------------------
            pts = []  # (xy, z_rest, release_time)
            for gi, gt in enumerate(gates):
                xy = u * gt["radius"]
                t_eval = t_rest if gi == 0 else self.release_time(gi - 1) + tm["gate_turn"]
                pts.append((xy, self.rest_z(world, q, xy, t_eval, gt["height"] + 0.8),
                            self.release_time(gi)))
            hole = holes[np.argmin(np.linalg.norm(holes - u * 0.3, axis=1))]
            if i == 0 or len(holes) > 1:
                final = hole
            else:  # rests next to the piece that plugs the hole
                final = hole + u * (2 * rb + 0.012)
            land = hole + u * max(np.linalg.norm(final - hole) + 0.14, rb * 1.3)
            z_land = self.rest_z(world, q, land, 99.0, top + 2.0)
            line = [final + (land - final) * v for v in np.linspace(0, 1, 24)]
            z_line = [self.rest_z(world, q, xy, 99.0, top + 2.0) for xy in line]
            if i > 0 and len(holes) == 1:
                # the first piece plugs the hole: rest against it
                z_plug = self.rest_z(world, q, hole, 99.0, top + 2.0)
                c0 = np.array([*hole, z_plug])
                for j, xy in enumerate(line):
                    dz = (2 * rb + 0.004) ** 2 - np.sum((xy - hole) ** 2)
                    if dz > 0:
                        z_line[j] = max(z_line[j], c0[2] + math.sqrt(dz))
            spawn = np.array([*(u * gates[0]["radius"]), tm["spawn_height"] + 0.12 * i])
            cen = np.zeros((n_sub, 3))
            imp = np.zeros(n_sub)

            def bounce(tau, v_imp, e=0.32):
                """Height above rest of a decaying bounce sequence."""
                v = v_imp * e
                while v > 0.35:
                    d = 2 * v / g
                    if tau < d:
                        return v * tau - 0.5 * g * tau * tau
                    tau -= d
                    v *= e
                return 0.0

            # timeline -----------------------------------------------------
            segs = []
            z0 = spawn[2]
            t_land = math.sqrt(2 * (z0 - pts[0][1]) / g)
            segs.append(("fall", 0.0, t_land, spawn[:2], spawn[:2], z0, pts[0][1]))
            prev_xy, prev_z, prev_land = pts[0][0], pts[0][1], t_land
            targets = [(p[0], p[1]) for p in pts[1:]] + [(land, z_land)]
            for (xy_r, z_r, t_rel), (xy_n, z_n) in zip(pts, targets):
                segs.append(("rest", prev_land, t_rel, xy_r, xy_r, z_r, z_r,
                             math.sqrt(2 * g * max(segs[-1][5] - z_r, 0.0))))
                tf = math.sqrt(2 * max(z_r - z_n, 0.01) / g)
                segs.append(("fall", t_rel, t_rel + tf, xy_r, xy_n, z_r, z_n))
                prev_land = t_rel + tf
                prev_xy, prev_z = xy_n, z_n
            v_imp = math.sqrt(2 * g * max(segs[-1][5] - z_land, 0.0))
            for k, t in enumerate(T):
                c = None
                for sg in segs:
                    kind, t0, t1 = sg[0], sg[1], sg[2]
                    if t0 <= t < t1:
                        if kind == "fall":
                            tau, d = t - t0, t1 - t0
                            xy = sg[3] + (sg[4] - sg[3]) * (tau / d)
                            z = sg[5] - 0.5 * g * tau * tau
                            c = (*xy, z)
                        else:
                            c = (*sg[3], sg[5] + bounce(t - t0, sg[7]))
                        break
                if c is None and t >= prev_land:  # on the pedestal: bounce and roll home
                    tau = t - prev_land
                    w = min(tau / 0.65, 1.0)
                    w = 1 - (1 - w) ** 3
                    j = (1 - w) * (len(line) - 1)
                    j0 = int(min(j, len(line) - 2))
                    fr = j - j0
                    xy = line[j0] * (1 - fr) + line[j0 + 1] * fr
                    zr = z_line[j0] * (1 - fr) + z_line[j0 + 1] * fr
                    c = (*xy, zr + bounce(tau, v_imp, 0.3))
                if c is None:
                    c = tuple(spawn)
                cen[k] = c
            # impacts (for the optional SFX)
            for sg in segs:
                if sg[0] == "fall":
                    k = int(sg[2] / dt)
                    if k < n_sub:
                        imp[k] = math.sqrt(2 * g * max(sg[5] - sg[6], 0.0))
            # rolling rotation from horizontal motion
            rot = np.zeros((n_sub, 3, 3))
            R = np.eye(3)
            for k in range(n_sub):
                if k > 0:
                    v = (cen[k] - cen[k - 1])
                    hv = np.array([v[0], v[1], 0.0])
                    sp = np.linalg.norm(hv)
                    if sp > 1e-7:
                        axis = np.cross([0, 0, 1.0], hv / sp)
                        ang = sp / rb
                        K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
                        R = (np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K) @ R
                rot[k] = R
            if delay:
                sh = int(delay / dt)
                cen = np.concatenate([np.repeat(cen[:1], sh, 0), cen[:-sh]]) if sh else cen
            cens.append(cen)
            rots.append(rot)
            imps.append(imp)
        return cens, rots, imps

    def _drain_paths(self, cen, s, offset, dt):
        """Rigid centre paths, modified so pieces resting at the hole squeeze
        down through it. Low softness only sinks a little (gets stuck)."""
        m = self.cfg["machine"]
        rb = m["piece_size"]
        top = m["pedestal"]["height"]
        reach = m["pedestal"]["sink_radius"] + rb
        holes = np.array(self.holes_xy(offset))
        n_sub, n_b, _ = cen.shape
        land = []
        for i in range(n_b):
            c = cen[:, i]
            dh = np.min(np.linalg.norm(c[:, None, :2] - holes[None], axis=2), axis=1)
            ok = np.nonzero((c[:, 2] < top + rb + 0.06) & (dh < reach))[0]
            land.append(ok[0] if len(ok) else None)
        order = sorted([i for i in range(n_b) if land[i] is not None], key=lambda i: land[i])
        depth_max = 1e9 if s >= 0.55 else (s / 0.55) ** 1.5 * 1.1 * rb
        acc = 2.0 + 12.0 * s
        pass_t = np.sqrt(2 * (2.0 * rb) / acc) + 0.05
        paths = [cen[:, i].copy() for i in range(n_b)]
        t_prev = None
        for rank, i in enumerate(order):
            if rank > 0 and s < 0.55:
                break  # only the first piece sinks in when it's not soft enough
            t0 = land[i] * dt + 0.08
            if t_prev is not None:
                t0 = max(t0, t_prev + pass_t)
            t_prev = t0
            k0 = int(t0 / dt)
            if k0 >= n_sub:
                continue
            c0 = paths[i][k0].copy()
            hole = holes[np.argmin(np.linalg.norm(holes - c0[:2], axis=1))]
            for k in range(k0, n_sub):
                tau = (k - k0) * dt
                u = min(tau / 0.35, 1.0)
                u = u * u * (3 - 2 * u)
                xy = c0[:2] * (1 - u) + hole * u
                z = min(c0[2], top + rb * 0.55) - min(depth_max, 0.5 * acc * tau * tau)
                z = min(z, c0[2])
                paths[i][k] = (xy[0], xy[1], z)
        return paths

    def _rigid_track(self, world, z_cross):
        """Radius of the rigid piece centre when it first drops below z_cross."""
        sub = int(self.cfg["timing"]["substeps"])
        bodies, _ = self.spawn(0.0, 1.0)
        b = bodies[0]
        for lf in range(self.frames_per_step * 2):
            for k in range(sub):
                b.step(self.speed / self.fps / sub, world, (lf + k / sub) / self.fps * self.speed)
            c = b.x.mean(0)
            if c[2] < z_cross:
                return float(np.hypot(c[0], c[1]))
        return None

    def calibrate(self, log=print):
        if self.layout == "rings":
            return self.hole_offset
        """Design the machine around the real trajectory: each lower gate and
        the pedestal holes are placed exactly where a rigid piece falls."""
        m = self.cfg["machine"]
        rb = m["piece_size"]
        gates = m["gates"]
        off = self.groove()[0]
        for gi in range(1, len(gates)):
            if gates[gi].get("radius", "auto") != "auto":
                continue
            saved = gates[gi:]
            m["gates"] = gates[:gi]
            zc = saved[0]["height"] + saved[0]["sleeve"] + rb + 0.02
            r = self._rigid_track(self.world(0.0, with_holes=False), zc)
            m["gates"] = gates
            gates[gi]["radius"] = round(r if r else gates[gi - 1]["radius"] * 0.7, 4)
            log(f"  gate {gi + 1} radius calibrated: {gates[gi]['radius']:.3f}")
        if self.hole_offset is None:
            top = self.ped["height"]
            r = self._rigid_track(self.world(0.0, with_holes=False), top + rb + 0.02)
            lim = self.ped["half_width"] - self.ped["sink_radius"] - 0.12
            self.hole_offset = float(min(r if r else 0.5, lim))
            log(f"  holes calibrated at radius {self.hole_offset:.3f}")
        return self.hole_offset
