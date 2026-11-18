"""Blender scene: seamless studio backdrop, camera, softbox lighting,
the concrete-and-gold machine and the soft pieces."""
import math

import bpy  # noqa: I001  (bpy must be imported before bmesh)
import bmesh
import numpy as np

from . import materials as M
from .meshgen import arc_tube, revolve_profile, torus


def hex_to_linear(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def mesh_object(name, verts, faces, mat=None, smooth=True, collection=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def bake(ob):
    """Apply all modifiers (no operator context needed)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


class Scene:
    def __init__(self, cfg, machine, hole_offset):
        self.cfg = cfg
        self.mc = machine
        self.hole_offset = hole_offset
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self._render_settings()
        self._world()
        self._backdrop()
        self._camera()
        self._lights()
        detail = cfg["effects"]["texture_detail"]
        m = cfg["machine"]
        self.mat_body = M.static_material("Body", m["body_material"], detail)
        self.mat_trim = M.static_material("Trim", m["trim_material"], detail)
        self._pedestal()
        self._gates()
        self._pieces()

    # ------------------------------------------------------------ settings
    def _render_settings(self):
        r = self.cfg["render"]
        s = self.scene
        s.render.engine = "CYCLES"
        s.cycles.device = "CPU"
        s.render.resolution_x, s.render.resolution_y = r["resolution"]
        s.render.resolution_percentage = max(1, int(round(100 * float(r.get("render_scale", 1.0)))))
        if int(r.get("threads", 0)) > 0:
            s.render.threads_mode = "FIXED"
            s.render.threads = int(r["threads"])
        s.render.fps = r["fps"]
        s.cycles.samples = int(r["samples"])
        s.cycles.use_adaptive_sampling = True
        s.cycles.adaptive_threshold = float(r["adaptive_threshold"])
        s.cycles.use_denoising = bool(r["denoise"])
        try:
            s.cycles.denoiser = "OPENIMAGEDENOISE"
            s.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        except (TypeError, AttributeError):
            pass
        s.cycles.max_bounces = 8
        s.cycles.diffuse_bounces = 2
        s.cycles.glossy_bounces = 4
        s.cycles.transmission_bounces = 8
        s.cycles.transparent_max_bounces = 8
        s.cycles.caustics_reflective = False
        s.cycles.caustics_refractive = False
        s.cycles.blur_glossy = 1.0
        s.cycles.sample_clamp_indirect = 8.0
        s.render.use_persistent_data = bool(r.get("persistent_data", False))
        s.render.film_transparent = False
        s.render.filter_size = 1.2
        s.render.image_settings.file_format = "PNG"
        s.render.image_settings.color_depth = "8"
        s.render.image_settings.color_mode = "RGB"
        s.view_settings.view_transform = r["view_transform"]
        try:
            s.view_settings.look = r["look"]
        except TypeError:
            pass
        s.view_settings.exposure = float(r["exposure"])
        s.render.use_motion_blur = False

    def _world(self):
        li = self.cfg["lighting"]
        w = bpy.data.worlds.new("World")
        self.scene.world = w
        w.use_nodes = True
        bg = w.node_tree.nodes["Background"]
        bg.inputs["Color"].default_value = (*hex_to_linear(li["background"]), 1.0)
        bg.inputs["Strength"].default_value = li["world_strength"]

    def _backdrop(self):
        """Infinite cyclorama: floor curving up into the back wall."""
        li = self.cfg["lighting"]
        prof = []
        y0, y1, R = -40.0, 7.0, 5.0
        for i in range(12):
            prof.append((y0 + (y1 - y0) * i / 11, 0.0))
        for i in range(1, 24):
            a = math.pi / 2 * i / 24
            prof.append((y1 + R * math.sin(a), R - R * math.cos(a)))
        for i in range(1, 8):
            prof.append((y1 + R, R + 30.0 * i / 7))
        verts, faces = [], []
        xs = (-40.0, 40.0)
        for (y, z) in prof:
            verts += [(xs[0], y, z), (xs[1], y, z)]
        for i in range(len(prof) - 1):
            a = 2 * i
            faces.append((a, a + 1, a + 3, a + 2))
        mat = bpy.data.materials.new("Backdrop")
        mat.use_nodes = True
        nt = mat.node_tree
        p = nt.nodes["Principled BSDF"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = -2.0
        mr.inputs["From Max"].default_value = 7.0
        mr.inputs["To Min"].default_value = 0.0
        mr.inputs["To Max"].default_value = 1.0
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        bgc = hex_to_linear(li["background"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*[c * 0.62 for c in bgc], 1.0)
        ramp.color_ramp.elements[1].color = (*bgc, 1.0)
        nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.9
        p.inputs["Specular IOR Level"].default_value = 0.25
        ob = mesh_object("Backdrop", verts, faces, mat)
        ob.data.shade_smooth()

    def _camera(self):
        c = self.cfg["camera"]
        cam = bpy.data.cameras.new("Camera")
        cam.lens = float(c["focal_length"])
        cam.sensor_fit = "HORIZONTAL"
        cam.sensor_width = 36.0
        cam.shift_x = float(c["shift_x"])
        cam.shift_y = float(c["shift_y"])
        cam.clip_end = 300
        ob = bpy.data.objects.new("Camera", cam)
        self.scene.collection.objects.link(ob)
        ob.location = c["location"]
        d = np.array(c["target"]) - np.array(c["location"])
        import mathutils
        ob.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()
        self.scene.camera = ob

    def _area(self, name, loc, target, size, energy, color=(1, 1, 1), size_y=None):
        import mathutils
        L = bpy.data.lights.new(name, "AREA")
        L.shape = "RECTANGLE"
        L.size = size
        L.size_y = size_y or size
        L.energy = energy
        L.color = color
        ob = bpy.data.objects.new(name, L)
        self.scene.collection.objects.link(ob)
        ob.location = loc
        d = mathutils.Vector(target) - mathutils.Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return ob

    def _lights(self):
        li = self.cfg["lighting"]
        k = float(li["intensity"])
        a = math.radians(li["key_angle"])
        tgt = (0, 0, 2.4)
        # large key softbox front-left, high
        self._area("Key", (-7.5 * math.sin(a) - 2.0, -7.5 * math.cos(a), 8.5), tgt,
                   5.0, 2400 * k, (1.0, 0.97, 0.93), 3.5)
        # soft fill front-right
        self._area("Fill", (7.0, -5.0, 5.0), tgt, 5.0, 380 * k, (0.95, 0.96, 1.0))
        # top light for the bright highlight band on metal / pedestal top
        self._area("Top", (0.5, -1.0, 11.0), (0, 0, 2.0), 4.0, 900 * k, (1.0, 0.98, 0.95))
        # rim from behind to separate objects from the backdrop
        self._area("Rim", (3.5, 6.0, 6.5), tgt, 3.0, 650 * k, (1.0, 0.95, 0.95))

    # ------------------------------------------------------------ machine
    def _pedestal(self):
        ped = self.cfg["machine"]["pedestal"]
        hw, H = ped["half_width"], ped["height"]
        col = self.scene.collection
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= 2 * hw
            v.co.y *= 2 * hw
            v.co.z = (v.co.z + 0.5) * H
        me = bpy.data.meshes.new("Pedestal")
        bm.to_mesh(me)
        bm.free()
        body = bpy.data.objects.new("Pedestal", me)
        col.objects.link(body)
        me.materials.append(self.mat_body)
        bev = body.modifiers.new("bevel", "BEVEL")
        bev.width = 0.02
        bev.segments = 3
        # cutter: hole + conical dish, revolved
        rh, rs, ds = ped["hole_radius"], ped["sink_radius"], ped["sink_depth"]
        k = (rs - rh) / ds
        prof = [(0.0, -0.5), (rh, -0.5), (rh, H - ds), (rs, H), (rs + k * 0.2, H + 0.2), (0.0, H + 0.2)]
        for i, (hx, hy) in enumerate(self.mc.holes_xy(self.hole_offset)):
            cv, cf = revolve_profile(prof, 128)
            cv[:, 0] += hx
            cv[:, 1] += hy
            cut = mesh_object(f"Cutter{i}", cv, cf, smooth=False)
            boo = body.modifiers.new(f"hole{i}", "BOOLEAN")
            boo.operation = "DIFFERENCE"
            boo.object = cut
            try:
                boo.solver = "EXACT"
            except TypeError:
                pass
        bake(body)
        for ob in [o for o in bpy.data.objects if o.name.startswith("Cutter")]:
            bpy.data.objects.remove(ob)
        body.data.shade_smooth()
        try:
            body.data.set_sharp_from_angle(angle=math.radians(35))
        except AttributeError:
            pass
        # gold edge frame
        t = ped["trim"]
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= 2 * hw + t * 0.4
            v.co.y *= 2 * hw + t * 0.4
            v.co.z = (v.co.z + 0.5) * H + (t * 0.2 if v.co.z > 0 else -t)
        me = bpy.data.meshes.new("Frame")
        bm.to_mesh(me)
        bm.free()
        fr = bpy.data.objects.new("Frame", me)
        col.objects.link(fr)
        wf = fr.modifiers.new("wire", "WIREFRAME")
        wf.thickness = t
        wf.use_even_offset = True
        wf.use_replace = True
        bv = fr.modifiers.new("bevel", "BEVEL")
        bv.width = t * 0.2
        bv.segments = 2
        me.materials.append(self.mat_trim)
        bake(fr)
        # square gold inlay on the top face
        o = hw * 0.85
        wdt = 0.1
        th = 0.006
        bm = bmesh.new()
        outer = [(-o, -o), (o, -o), (o, o), (-o, o)]
        inner = [(-o + wdt, -o + wdt), (o - wdt, -o + wdt), (o - wdt, o - wdt), (-o + wdt, o - wdt)]
        vs = []
        for z in (H - 0.002, H + th):
            vs.append([bm.verts.new((x, y, z)) for x, y in outer])
            vs.append([bm.verts.new((x, y, z)) for x, y in inner])
        (ob_, ib_, ot_, it_) = vs
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((ot_[i], ot_[j], it_[j], it_[i]))       # top
            bm.faces.new((ob_[i], ib_[i], ib_[j], ob_[j]))       # bottom
            bm.faces.new((ob_[i], ob_[j], ot_[j], ot_[i]))       # outer wall
            bm.faces.new((ib_[i], it_[i], it_[j], ib_[j]))       # inner wall
        me = bpy.data.meshes.new("Inlay")
        bm.to_mesh(me)
        bm.free()
        inl = bpy.data.objects.new("Inlay", me)
        col.objects.link(inl)
        me.materials.append(self.mat_trim)
        bv = inl.modifiers.new("bevel", "BEVEL")
        bv.width = 0.002
        bv.segments = 2

    def _gates(self):
        m = self.cfg["machine"]
        rb = m["piece_size"]
        self.sleeves = []  # (object, gate index, base angle)
        _, rg, gdepth = self.mc.groove()
        for gi, g in enumerate(m["gates"]):
            R, z = g["radius"], g["height"]
            tv, tf = torus(R + self.mc.wire_offset(g), g["wire"], 220, 20)
            tv[:, 2] += z - self.mc.wire_drop(g)
            mesh_object(f"Wire{gi}", tv, tf, self.mat_trim)
            hs = math.radians(g["span"]) / 2
            sv, sf = arc_tube(R, g["sleeve"], hs, 56, 40)
            # carve the cradle groove on top (same as the collider)
            zc = g["sleeve"] + rg - gdepth
            rxy = np.hypot(sv[:, 0], sv[:, 1])
            dx = rxy - R
            dz = sv[:, 2] - zc
            dist = np.hypot(dx, dz)
            inside = dist < rg
            if inside.any():
                s = rg / np.maximum(dist[inside], 1e-9)
                nr = R + dx[inside] * s
                sv[inside, 2] = zc + dz[inside] * s
                sv[inside, 0] *= nr / rxy[inside]
                sv[inside, 1] *= nr / rxy[inside]
            # thin gold band along the outer side of each sleeve
            bv_, bf_ = arc_tube(R + g["sleeve"] * 0.99, g["sleeve"] * 0.13, hs * 0.995, 56, 12, 0.9)
            for pi, a in enumerate(self.mc.piece_angles):
                ob = mesh_object(f"Sleeve{gi}_{pi}", sv, sf, self.mat_body)
                ob.location = (0, 0, z)
                band = mesh_object(f"Band{gi}_{pi}", bv_, bf_, self.mat_trim)
                band.parent = ob
                sub = ob.modifiers.new("sub", "SUBSURF")
                sub.levels = 1
                sub.render_levels = 1
                self.sleeves.append((ob, gi, a))

    def _pieces(self):
        m = self.cfg["machine"]
        from .meshgen import make_piece
        verts, tris = make_piece(m["piece_shape"], m["piece_size"], m["piece_detail"])
        self.morph = M.MorphLibrary(m["piece_size"], self.cfg["effects"]["texture_detail"])
        # build every material the video needs up front
        steps = self.cfg["progression"]["steps"]
        mode = self.cfg["progression"]["morph"].get("mode", "spread")
        for i, st in enumerate(steps):
            prev = steps[i - 1]["material"] if i else st["material"]
            self.morph.get(prev, st["material"], "fade" if mode == "cut" else mode)
            self.morph.get(st["material"], st["material"])
        first = self.morph.get(steps[0]["material"], steps[0]["material"])
        self.pieces = []
        rest = (verts - verts.mean(0)).astype(np.float32)
        for i in range(self.mc.n):
            ob = mesh_object(f"Piece{i}", verts, tris, first)
            ob["bb_morph"] = 0.0
            ob["bb_time"] = 0.0
            attr = ob.data.attributes.new("rest", "FLOAT_VECTOR", "POINT")
            attr.data.foreach_set("vector", rest.ravel())
            lv = int(self.cfg["render"]["piece_subdivision"])
            if lv > 0:
                sub = ob.modifiers.new("sub", "SUBSURF")
                sub.levels = 0
                sub.render_levels = lv
            self.pieces.append(ob)

    # ------------------------------------------------------------ per frame
    def set_frame(self, f, positions, material_state, time_s):
        si, lf, t = self.mc.step_of_frame(f)
        t_sim = t * self.mc.speed
        for ob, gi, a in self.sleeves:
            ob.rotation_euler = (0, 0, a + self.mc.gate_angle(gi, t_sim))
        for ob, x in zip(self.pieces, positions):
            if x is None:
                # gone through the hole: park it below the floor instead of
                # toggling visibility (avoids Cycles persistent-data glitches)
                ob.location = (0.0, 0.0, -100.0)
                continue
            ob.location = (0.0, 0.0, 0.0)
            ob.data.vertices.foreach_set("co", x.ravel())
            ob.data.update()
        a, b, prog, mode = material_state
        mat = self.morph.get(a, b, mode)
        for ob in self.pieces:
            if ob.data.materials[0] != mat:
                ob.data.materials[0] = mat
            ob["bb_morph"] = float(prog)
            ob["bb_time"] = float(time_s)
        self.scene.frame_current = f
