"""Procedural mesh generators (pure numpy, no bpy) used both for the
soft-body simulation and for the Blender scene geometry."""
import numpy as np


# ---------------------------------------------------------------- icosphere
def icosphere(subdiv=4):
    t = (1.0 + 5 ** 0.5) / 2.0
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
         (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
         (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
         (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    verts = [np.array(p, float) / np.linalg.norm(p) for p in v]
    faces = f
    for _ in range(subdiv):
        cache = {}
        nf = []

        def mid(a, b):
            k = (a, b) if a < b else (b, a)
            if k not in cache:
                m = verts[a] + verts[b]
                verts.append(m / np.linalg.norm(m))
                cache[k] = len(verts) - 1
            return cache[k]

        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = nf
    return np.array(verts), np.array(faces, dtype=np.int64)


def revolve_profile(profile, segments=48):
    """profile: list of (r, z) from bottom pole (r=0) to top pole (r=0).
    Returns a closed triangle mesh revolved around Z."""
    profile = list(profile)
    rings = profile[1:-1]
    verts = [(0, 0, profile[0][1])]
    ang = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    for r, z in rings:
        for a in ang:
            verts.append((r * np.cos(a), r * np.sin(a), z))
    verts.append((0, 0, profile[-1][1]))
    faces = []
    n = segments
    for j in range(n):  # bottom fan
        faces.append((0, 1 + (j + 1) % n, 1 + j))
    for i in range(len(rings) - 1):
        b0 = 1 + i * n
        b1 = 1 + (i + 1) * n
        for j in range(n):
            j1 = (j + 1) % n
            faces.append((b0 + j, b0 + j1, b1 + j1))
            faces.append((b0 + j, b1 + j1, b1 + j))
    top = len(verts) - 1
    last = 1 + (len(rings) - 1) * n
    for j in range(n):
        faces.append((last + j, last + (j + 1) % n, top))
    return np.array(verts, float), np.array(faces, dtype=np.int64)


def make_piece(shape, size, detail=4):
    """Closed triangle mesh for a soft piece, centred on the origin.
    size = radius of the piece (half width)."""
    shape = shape.lower()
    if shape == "sphere":
        v, f = icosphere(detail)
        return v * size, f
    if shape in ("cube", "rounded_cube"):
        v, f = icosphere(detail)
        k = 7.0
        s = (np.abs(v) ** k).sum(1) ** (1.0 / k)
        return v / s[:, None] * size, f
    if shape in ("capsule", "pill"):
        r = size * 0.62
        h = size * 1.55  # half length of the straight part
        prof = []
        nh = 10
        for i in range(nh + 1):  # bottom hemisphere
            a = -np.pi / 2 + np.pi / 2 * i / nh
            prof.append((r * np.cos(a), -h + r * np.sin(a)))
        for i in range(1, 14):
            prof.append((r, -h + 2 * h * i / 14))
        for i in range(nh + 1):
            a = np.pi / 2 * i / nh
            prof.append((r * np.cos(a), h + r * np.sin(a)))
        prof[0] = (0, prof[0][1])
        prof[-1] = (0, prof[-1][1])
        return revolve_profile(prof, 40)
    if shape in ("coin", "disc"):
        r = size
        t = size * 0.35
        prof = [(0, -t)]
        for i in range(1, 9):
            prof.append((r * 0.82 * i / 8, -t))
        for i in range(1, 12):
            a = -np.pi / 2 + np.pi * i / 12
            prof.append((r * 0.82 + t * np.cos(a), t * np.sin(a)))
        for i in range(8, 0, -1):
            prof.append((r * 0.82 * i / 8, t))
        prof.append((0, t))
        return revolve_profile(prof, 56)
    raise ValueError(f"unknown piece shape '{shape}'")


# ---------------------------------------------------------------- tubes
def torus(R, r, seg_major=160, seg_minor=24):
    verts, faces = [], []
    for i in range(seg_major):
        a = 2 * np.pi * i / seg_major
        ca, sa = np.cos(a), np.sin(a)
        for j in range(seg_minor):
            b = 2 * np.pi * j / seg_minor
            rr = R + r * np.cos(b)
            verts.append((rr * ca, rr * sa, r * np.sin(b)))
    for i in range(seg_major):
        i1 = (i + 1) % seg_major
        for j in range(seg_minor):
            j1 = (j + 1) % seg_minor
            faces.append((i * seg_minor + j, i1 * seg_minor + j,
                          i1 * seg_minor + j1, i * seg_minor + j1))
    return np.array(verts), faces


def arc_tube(R, r, half_span, seg_arc=48, seg_minor=32, cap_round=0.35):
    """Tube following an arc of radius R centred on angle 0 (+-half_span),
    with softly rounded flat caps (like a concrete sleeve)."""
    # arc-length samples, with extra density near the ends for the rounding
    L = 2 * half_span * R
    cr = min(r * cap_round, L * 0.2)
    k = 6
    cap = []  # (arc length, tube radius) for the rounded start cap
    for i in range(k + 1):
        th = np.pi / 2 * i / k
        cap.append((cr * (1 - np.cos(th)), r - cr + cr * np.sin(th)))
    body = [(s, r) for s in np.linspace(cr, L - cr, seg_arc)[1:-1]]
    prof = cap + body + [(L - s, rr) for s, rr in reversed(cap)]
    verts, faces = [], []
    for s, rr in prof:
        a = -half_span + s / R
        ca, sa = np.cos(a), np.sin(a)
        for j in range(seg_minor):
            b = 2 * np.pi * j / seg_minor
            rad = R + rr * np.cos(b)
            verts.append((rad * ca, rad * sa, rr * np.sin(b)))
    n = len(prof)
    for i in range(n - 1):
        for j in range(seg_minor):
            j1 = (j + 1) % seg_minor
            faces.append((i * seg_minor + j, (i + 1) * seg_minor + j,
                          (i + 1) * seg_minor + j1, i * seg_minor + j1))
    # caps (flat n-gons at both ends)
    faces.append(tuple(range(seg_minor))[::-1])
    faces.append(tuple((n - 1) * seg_minor + j for j in range(seg_minor)))
    return np.array(verts), faces
