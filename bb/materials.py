"""Procedural PBR material library (no image textures needed) and the
morphing material used by the pieces.

Every library material is a shader node group with one input (Vector:
texture coordinates) and one output (Shader). A morph material mixes two
of them with an animated mask, so a transition really changes roughness,
metalness, bump, transmission, coat... not just the colour."""
import bpy

LIBRARY = {}


def material(name):
    def deco(fn):
        LIBRARY[name] = fn
        return fn
    return deco


# ---------------------------------------------------------------- helpers
class G:
    def __init__(self, tree):
        self.t = tree
        self.nodes = tree.nodes
        self.links = tree.links
        self.x = 0

    def n(self, kind, **props):
        node = self.nodes.new(kind)
        node.location = (self.x, 0)
        self.x += 200
        for k, v in props.items():
            if k in ("inputs",):
                continue
            setattr(node, k, v)
        for k, v in props.get("inputs", {}).items():
            sock = node.inputs[k]
            sock.default_value = v
        return node

    def link(self, a, b):
        self.links.new(a, b)

    def noise(self, vec, scale, detail=4.0, rough=0.5, dist=0.0, w=None):
        nd = self.n("ShaderNodeTexNoise", inputs={"Scale": scale, "Detail": detail,
                                                  "Roughness": rough, "Distortion": dist})
        if w is not None:
            nd.noise_dimensions = "4D"
            if isinstance(w, (int, float)):
                nd.inputs["W"].default_value = w
            else:
                self.link(w, nd.inputs["W"])
        self.link(vec, nd.inputs["Vector"])
        return nd

    def ramp(self, fac, stops):
        r = self.n("ShaderNodeValToRGB")
        els = r.color_ramp.elements
        while len(els) > len(stops):
            els.remove(els[-1])
        while len(els) < len(stops):
            els.new(0.5)
        for el, (pos, col) in zip(els, stops):
            el.position = pos
            el.color = (*col, 1.0) if len(col) == 3 else col
        self.link(fac, r.inputs["Fac"])
        return r

    def bump(self, height, strength, distance=0.02, normal=None):
        b = self.n("ShaderNodeBump", inputs={"Strength": strength, "Distance": distance})
        self.link(height, b.inputs["Height"])
        if normal is not None:
            self.link(normal, b.inputs["Normal"])
        return b

    def math(self, op, *args, clamp=False):
        m = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate(args):
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def mix_rgb(self, fac, a, b):
        m = self.n("ShaderNodeMix", data_type="RGBA")
        ins = {s.identifier: s for s in m.inputs}
        for key, v in (("Factor_Float", fac), ("A_Color", a), ("B_Color", b)):
            if isinstance(v, (tuple, list)):
                ins[key].default_value = (*v, 1.0) if len(v) == 3 else v
            elif isinstance(v, (int, float)):
                ins[key].default_value = v
            else:
                self.link(v, ins[key])
        return [s for s in m.outputs if s.identifier == "Result_Color"][0]

    def bsdf(self, **vals):
        p = self.n("ShaderNodeBsdfPrincipled")
        for k, v in vals.items():
            if hasattr(v, "is_output"):
                self.link(v, p.inputs[k])
            else:
                if isinstance(v, tuple) and len(v) == 3 and p.inputs[k].type == "RGBA":
                    v = (*v, 1.0)
                p.inputs[k].default_value = v
        return p


TIME_NODES = []  # value nodes that receive the current time each frame


def _group(name, builder, detail):
    ng = bpy.data.node_groups.new(f"BB_{name}", "ShaderNodeTree")
    ng.interface.new_socket("Vector", in_out="INPUT", socket_type="NodeSocketVector")
    ng.interface.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    g = G(ng)
    gin = g.n("NodeGroupInput")
    gout = g.n("NodeGroupOutput")
    shader = builder(g, gin.outputs["Vector"], detail)
    g.link(shader, gout.inputs["Shader"])
    return ng


def get_group(name, detail=1.0, owner=""):
    """Node group for a library material. Each owner (material) gets its own
    copy: Cycles' persistent data can lose shared groups when one of the
    materials using them is edited between frames."""
    key = f"BB_{name}" + (f"@{owner}" if owner else "")
    if key in bpy.data.node_groups:
        return bpy.data.node_groups[key]
    if name not in LIBRARY:
        raise KeyError(f"unknown material '{name}'. Available: {', '.join(sorted(LIBRARY))}")
    ng = _group(name, LIBRARY[name], detail)
    ng.name = key
    return ng


def _time(g):
    v = g.n("ShaderNodeValue")
    v.outputs[0].default_value = 0.0
    TIME_NODES.append(v)
    return v.outputs[0]


def set_time(t):
    for v in TIME_NODES:
        try:
            v.outputs[0].default_value = t
        except ReferenceError:
            pass


# ---------------------------------------------------------------- metals
def _metal(g, vec, d, color, rough, var=0.04, bump=0.015):
    n = g.noise(vec, 6.0, 6.0, 0.6)
    r = g.math("MULTIPLY_ADD", n.outputs["Fac"], var * 2, rough - var)
    micro = g.noise(vec, 160.0, 2.0, 0.5)
    b = g.bump(micro.outputs["Fac"], bump * d, 0.01)
    return g.bsdf(**{"Base Color": color, "Metallic": 1.0, "Roughness": r,
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("gold")
def m_gold(g, vec, d):
    return _metal(g, vec, d, (1.0, 0.66, 0.16), 0.13)


@material("silver")
def m_silver(g, vec, d):
    return _metal(g, vec, d, (0.95, 0.94, 0.92), 0.1)


@material("chrome")
def m_chrome(g, vec, d):
    return _metal(g, vec, d, (0.92, 0.93, 0.95), 0.03, var=0.01, bump=0.004)


@material("copper")
def m_copper(g, vec, d):
    return _metal(g, vec, d, (0.95, 0.47, 0.28), 0.18)


@material("rose_gold")
def m_rose_gold(g, vec, d):
    return _metal(g, vec, d, (0.98, 0.6, 0.48), 0.14)


@material("brushed_steel")
def m_brushed(g, vec, d):
    sc = g.n("ShaderNodeMapping", inputs={"Scale": (1.0, 1.0, 90.0)})
    g.link(vec, sc.inputs["Vector"])
    n = g.noise(sc.outputs["Vector"], 18.0, 8.0, 0.7)
    b = g.bump(n.outputs["Fac"], 0.25 * d, 0.01)
    r = g.math("MULTIPLY_ADD", n.outputs["Fac"], 0.12, 0.22)
    return g.bsdf(**{"Base Color": (0.78, 0.78, 0.8), "Metallic": 1.0, "Roughness": r,
                     "Anisotropic": 0.7, "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("liquid_metal")
def m_mercury(g, vec, d):
    t = _time(g)
    n = g.noise(vec, 2.2, 3.0, 0.5, w=t)
    b = g.bump(n.outputs["Fac"], 0.35 * d, 0.05)
    return g.bsdf(**{"Base Color": (0.86, 0.87, 0.9), "Metallic": 1.0, "Roughness": 0.02,
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


# ---------------------------------------------------------------- stones
@material("concrete")
def m_concrete(g, vec, d):
    n1 = g.noise(vec, 2.5, 8.0, 0.62)
    col = g.ramp(n1.outputs["Fac"], [(0.3, (0.045, 0.045, 0.043)), (0.72, (0.09, 0.088, 0.084))])
    # pitted surface: small craters (voronoi) + fine grain + large waviness
    vor = g.n("ShaderNodeTexVoronoi", inputs={"Scale": 24.0, "Randomness": 1.0})
    g.link(vec, vor.inputs["Vector"])
    pits = g.ramp(vor.outputs["Distance"], [(0.0, (0, 0, 0)), (0.3, (1, 1, 1))])
    vor2 = g.n("ShaderNodeTexVoronoi", inputs={"Scale": 110.0, "Randomness": 1.0})
    g.link(vec, vor2.inputs["Vector"])
    pits2 = g.ramp(vor2.outputs["Distance"], [(0.0, (0, 0, 0)), (0.25, (1, 1, 1))])
    fine = g.noise(vec, 160.0, 6.0, 0.75)
    h = g.math("MULTIPLY_ADD", fine.outputs["Fac"], 0.5, pits.outputs["Color"])
    h = g.math("MULTIPLY_ADD", pits2.outputs["Color"], 0.6, h)
    b = g.bump(h, 0.45 * d, 0.012)
    lumps = g.noise(vec, 14.0, 5.0, 0.6)
    b1 = g.bump(lumps.outputs["Fac"], 0.6 * d, 0.03, normal=b.outputs["Normal"])
    b2 = g.bump(n1.outputs["Fac"], 0.2 * d, 0.06, normal=b1.outputs["Normal"])
    # crater bottoms are a bit darker (dirt / occlusion)
    occ = g.mix_rgb(pits.outputs["Color"], (0.8, 0.8, 0.8), (1.0, 1.0, 1.0))
    col2 = g.mix_rgb(1.0, col.outputs["Color"], occ)
    col2.node.blend_type = "MULTIPLY"
    r = g.math("MULTIPLY_ADD", n1.outputs["Fac"], 0.12, 0.78)
    return g.bsdf(**{"Base Color": col2, "Roughness": r,
                     "Normal": b2.outputs["Normal"]}).outputs["BSDF"]


@material("stone")
def m_stone(g, vec, d):
    vor = g.n("ShaderNodeTexVoronoi", inputs={"Scale": 9.0, "Randomness": 1.0})
    g.link(vec, vor.inputs["Vector"])
    n = g.noise(vec, 12.0, 10.0, 0.7, dist=0.3)
    mix = g.math("MULTIPLY_ADD", n.outputs["Fac"], 0.6, vor.outputs["Distance"])
    col = g.ramp(mix, [(0.2, (0.08, 0.075, 0.07)), (0.55, (0.26, 0.24, 0.21)),
                       (0.8, (0.42, 0.4, 0.36))])
    b = g.bump(mix, 0.6 * d, 0.05)
    return g.bsdf(**{"Base Color": col.outputs["Color"], "Roughness": 0.72,
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("granite")
def m_granite(g, vec, d):
    vor = g.n("ShaderNodeTexVoronoi", inputs={"Scale": 60.0, "Randomness": 1.0})
    g.link(vec, vor.inputs["Vector"])
    col = g.ramp(vor.outputs["Color"],
                 [(0.0, (0.02, 0.02, 0.02)), (0.45, (0.3, 0.28, 0.27)), (0.8, (0.75, 0.72, 0.7))])
    fine = g.noise(vec, 200.0, 2.0, 0.5)
    b = g.bump(fine.outputs["Fac"], 0.08 * d, 0.01)
    return g.bsdf(**{"Base Color": col.outputs["Color"], "Roughness": 0.18,
                     "Coat Weight": 0.3, "Normal": b.outputs["Normal"]}).outputs["BSDF"]


def _marble(g, vec, d, base, vein, vein_metal=False):
    n = g.noise(vec, 1.6, 8.0, 0.65)
    w = g.n("ShaderNodeTexWave", wave_type="BANDS", inputs={"Scale": 1.8, "Distortion": 9.0,
                                                           "Detail": 6.0, "Detail Scale": 1.5})
    g.link(n.outputs["Color"], w.inputs["Vector"])
    v = g.ramp(w.outputs["Fac"], [(0.0, (1, 1, 1)), (0.06, (0, 0, 0)), (0.94, (0, 0, 0)), (1.0, (1, 1, 1))])
    fac = v.outputs["Color"]
    col = g.mix_rgb(fac, base, vein)
    kw = {"Base Color": col, "Roughness": 0.1, "Coat Weight": 0.5, "Coat Roughness": 0.04,
          "Subsurface Weight": 0.12, "Subsurface Radius": (0.4, 0.3, 0.25), "Subsurface Scale": 0.02}
    if vein_metal:
        kw["Metallic"] = g.math("MULTIPLY", fac, 1.0)
    return g.bsdf(**kw).outputs["BSDF"]


@material("marble")
def m_marble(g, vec, d):
    return _marble(g, vec, d, (0.82, 0.8, 0.77), (0.22, 0.22, 0.24))


@material("black_marble")
def m_black_marble(g, vec, d):
    return _marble(g, vec, d, (0.012, 0.012, 0.014), (0.95, 0.68, 0.25), vein_metal=True)


@material("sand")
def m_sand(g, vec, d):
    vor = g.n("ShaderNodeTexVoronoi", inputs={"Scale": 420.0, "Randomness": 1.0})
    g.link(vec, vor.inputs["Vector"])
    n = g.noise(vec, 9.0, 6.0, 0.6)
    col = g.ramp(n.outputs["Fac"], [(0.3, (0.46, 0.32, 0.17)), (0.7, (0.62, 0.46, 0.27))])
    grain = g.ramp(vor.outputs["Color"], [(0.0, (0.75, 0.75, 0.75)), (1.0, (1.1, 1.1, 1.1))])
    c2 = g.mix_rgb(1.0, col.outputs["Color"], grain.outputs["Color"])
    c2.node.blend_type = "MULTIPLY"
    h = g.math("ADD", vor.outputs["Distance"], g.math("MULTIPLY", n.outputs["Fac"], 0.4))
    b = g.bump(h, 0.55 * d, 0.01)
    return g.bsdf(**{"Base Color": c2, "Roughness": 0.97, "Normal": b.outputs["Normal"],
                     "Sheen Weight": 0.3}).outputs["BSDF"]


# ---------------------------------------------------------------- organics
@material("wood")
def m_wood(g, vec, d):
    mp = g.n("ShaderNodeMapping", inputs={"Scale": (1.0, 1.0, 0.25)})
    g.link(vec, mp.inputs["Vector"])
    n = g.noise(mp.outputs["Vector"], 2.0, 4.0, 0.5)
    w = g.n("ShaderNodeTexWave", wave_type="RINGS", inputs={"Scale": 4.0, "Distortion": 3.0,
                                                           "Detail": 3.0})
    g.link(n.outputs["Color"], w.inputs["Vector"])
    grain = g.noise(mp.outputs["Vector"], 120.0, 2.0, 0.5)
    h = g.math("MULTIPLY_ADD", grain.outputs["Fac"], 0.25, w.outputs["Fac"])
    col = g.ramp(h, [(0.1, (0.11, 0.045, 0.015)), (0.55, (0.32, 0.15, 0.06)), (0.9, (0.48, 0.25, 0.1))])
    b = g.bump(h, 0.12 * d, 0.02)
    return g.bsdf(**{"Base Color": col.outputs["Color"], "Roughness": 0.45, "Coat Weight": 0.6,
                     "Coat Roughness": 0.08, "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("clay")
def m_clay(g, vec, d):
    n = g.noise(vec, 30.0, 6.0, 0.6)
    b = g.bump(n.outputs["Fac"], 0.15 * d, 0.02)
    return g.bsdf(**{"Base Color": (0.55, 0.24, 0.13), "Roughness": 0.92,
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("velvet")
def m_velvet(g, vec, d):
    n = g.noise(vec, 300.0, 2.0, 0.5)
    b = g.bump(n.outputs["Fac"], 0.1 * d, 0.005)
    return g.bsdf(**{"Base Color": (0.28, 0.015, 0.05), "Roughness": 0.9, "Sheen Weight": 1.0,
                     "Sheen Roughness": 0.35, "Sheen Tint": (1.0, 0.55, 0.6),
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("rubber")
def m_rubber(g, vec, d):
    n = g.noise(vec, 220.0, 2.0, 0.5)
    b = g.bump(n.outputs["Fac"], 0.08 * d, 0.005)
    return g.bsdf(**{"Base Color": (0.018, 0.018, 0.02), "Roughness": 0.55,
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


# ---------------------------------------------------------------- dielectrics
@material("glass")
def m_glass(g, vec, d):
    return g.bsdf(**{"Base Color": (0.96, 0.98, 1.0), "Roughness": 0.0, "IOR": 1.5,
                     "Transmission Weight": 1.0}).outputs["BSDF"]


@material("frosted_glass")
def m_frosted(g, vec, d):
    return g.bsdf(**{"Base Color": (0.95, 0.97, 1.0), "Roughness": 0.28, "IOR": 1.5,
                     "Transmission Weight": 1.0}).outputs["BSDF"]


@material("water")
def m_water(g, vec, d):
    t = _time(g)
    n = g.noise(vec, 3.5, 3.0, 0.5, w=t)
    b = g.bump(n.outputs["Fac"], 0.3 * d, 0.04)
    return g.bsdf(**{"Base Color": (0.8, 0.93, 1.0), "Roughness": 0.0, "IOR": 1.33,
                     "Transmission Weight": 1.0, "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("jelly")
def m_jelly(g, vec, d):
    return g.bsdf(**{"Base Color": (0.95, 0.18, 0.35), "Roughness": 0.04, "IOR": 1.35,
                     "Transmission Weight": 0.85, "Subsurface Weight": 0.3,
                     "Subsurface Radius": (1.0, 0.25, 0.3), "Subsurface Scale": 0.1}).outputs["BSDF"]


@material("ceramic")
def m_ceramic(g, vec, d):
    n = g.noise(vec, 40.0, 3.0, 0.5)
    b = g.bump(n.outputs["Fac"], 0.015 * d, 0.01)
    return g.bsdf(**{"Base Color": (0.86, 0.85, 0.82), "Roughness": 0.4, "Coat Weight": 1.0,
                     "Coat Roughness": 0.02, "Subsurface Weight": 0.1, "Subsurface Scale": 0.01,
                     "Normal": b.outputs["Normal"]}).outputs["BSDF"]


@material("pearl")
def m_pearl(g, vec, d):
    n = g.noise(vec, 3.0, 4.0, 0.5)
    th = g.math("MULTIPLY_ADD", n.outputs["Fac"], 300.0, 380.0)
    return g.bsdf(**{"Base Color": (0.88, 0.86, 0.84), "Metallic": 0.25, "Roughness": 0.16,
                     "Thin Film Thickness": th, "Thin Film IOR": 1.6,
                     "Coat Weight": 0.6}).outputs["BSDF"]


@material("plastic")
def m_plastic(g, vec, d):
    return g.bsdf(**{"Base Color": (0.02, 0.25, 0.9), "Roughness": 0.25,
                     "Coat Weight": 0.4}).outputs["BSDF"]


@material("backdrop")
def m_backdrop(g, vec, d):
    # replaced at scene build with the configured colour
    return g.bsdf(**{"Base Color": (0.5, 0.4, 0.42), "Roughness": 0.85}).outputs["BSDF"]


# ---------------------------------------------------------------- materials
def static_material(name, lib_name, detail=1.0, coord="Object"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    g = G(nt)
    tc = g.n("ShaderNodeTexCoord")
    grp = g.n("ShaderNodeGroup")
    grp.node_tree = get_group(lib_name, detail, owner=name)
    out = g.n("ShaderNodeOutputMaterial")
    g.link(tc.outputs[coord], grp.inputs["Vector"])
    g.link(grp.outputs["Shader"], out.inputs["Surface"])
    return mat


class MorphMaterial:
    """Material A -> B transition driven by an animated mask on the piece's
    rest-pose coordinates (so the pattern sticks to the deforming surface)."""

    def __init__(self, name, size, detail=1.0):
        self.size = size
        self.detail = detail
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        g = G(nt)
        attr = g.n("ShaderNodeAttribute", attribute_name="rest")
        self.ga = g.n("ShaderNodeGroup")
        self.gb = g.n("ShaderNodeGroup")
        self.ga.node_tree = get_group("gold", detail, owner="morphA")
        self.gb.node_tree = get_group("gold", detail, owner="morphB")
        g.link(attr.outputs["Vector"], self.ga.inputs["Vector"])
        g.link(attr.outputs["Vector"], self.gb.inputs["Vector"])
        # mask: height in the piece + organic noise edge
        sep = g.n("ShaderNodeSeparateXYZ")
        g.link(attr.outputs["Vector"], sep.inputs["Vector"])
        h = g.math("MULTIPLY_ADD", sep.outputs["Z"], 0.5 / size, 0.5)
        nz = g.noise(attr.outputs["Vector"], 2.2 / size, 3.0, 0.55)
        hm = g.math("MULTIPLY_ADD", nz.outputs["Fac"], 0.45, h)
        self.mr = g.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        g.link(hm, self.mr.inputs["Value"])
        self.mix = g.n("ShaderNodeMixShader")
        g.link(self.mr.outputs["Result"], self.mix.inputs["Fac"])
        g.link(self.ga.outputs["Shader"], self.mix.inputs[1])
        g.link(self.gb.outputs["Shader"], self.mix.inputs[2])
        out = g.n("ShaderNodeOutputMaterial")
        g.link(self.mix.outputs["Shader"], out.inputs["Surface"])
        self.mat = mat
        self.state = None

    def set(self, mat_a, mat_b, progress, mode="spread"):
        """progress 0 -> all A, 1 -> all B."""
        if self.state != (mat_a, mat_b):
            self.ga.node_tree = get_group(mat_a, self.detail, owner="morphA")
            self.gb.node_tree = get_group(mat_b, self.detail, owner="morphB")
            self.state = (mat_a, mat_b)
        vals = self._values(progress, mode, mat_a == mat_b)
        if vals == getattr(self, "_last", None):
            return  # nothing changed: don't trigger a shader update
        self._last = vals
        mr = self.mr.inputs
        for k, v in zip(("From Min", "From Max", "To Min", "To Max"), vals):
            mr[k].default_value = v

    def _values(self, progress, mode, same):
        if mode == "fade" or same:
            # constant factor everywhere
            return (-10.0, -9.0, round(progress, 4), round(progress, 4))
        w = 0.06
        edge = -0.35 + progress * 1.95  # sweeps bottom -> top, past the noise range
        return (round(edge + w, 4), round(edge - w, 4), 0.0, 1.0)
