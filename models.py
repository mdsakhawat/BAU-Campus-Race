import math
import random

from OpenGL.GL import *

import gfx
from carmodel import CarModel
from mesh import Mesh, beam, disc, quad_out

BLACK = (0.06, 0.06, 0.07, 1)
GLASS = (0.10, 0.14, 0.18, 1)
TYRE = (0.07, 0.07, 0.08, 1)
CHROME = (0.72, 0.74, 0.78, 1)


def c4(c, a=1.0):
    return (c[0], c[1], c[2], a)


def wheel_mesh(r, w, rim=(0.62, 0.64, 0.68, 1), seg=14):
    m = Mesh()
    for k in range(seg):
        a0 = 2 * math.pi * k / seg
        a1 = 2 * math.pi * (k + 1) / seg
        p = [(-w / 2, math.cos(a0) * r, math.sin(a0) * r), (w / 2, math.cos(a0) * r, math.sin(a0) * r),
             (w / 2, math.cos(a1) * r, math.sin(a1) * r), (-w / 2, math.cos(a1) * r, math.sin(a1) * r)]
        quad_out(m, p, (0, math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2)), TYRE)
    for s in (-1, 1):
        disc(m, s * w / 2, 0, 0, r, (s, 0, 0), TYRE, seg, "x")
        disc(m, s * (w / 2 + 0.005), 0, 0, r * 0.62, (s, 0, 0), rim, seg, "x")
        for k in range(4):
            a = k * math.pi / 2
            beam(m, (s * (w / 2 + 0.01), 0, 0), (s * (w / 2 + 0.01), math.cos(a) * r * 0.6, math.sin(a) * r * 0.6), 0.03, (0.3, 0.3, 0.32, 1))
    return m


class SimpleModel:
    def __init__(self):
        self.lists = {}
        self.wheels = []
        self.head = []
        self.tail = []
        self.textured = []
        gfx.reset_hooks.append(self.reset_gl)

    def reset_gl(self):
        self.lists = {}

    def release(self):
        if self.reset_gl in gfx.reset_hooks:
            gfx.reset_hooks.remove(self.reset_gl)

    def compiled(self, key, fn, colors=True):
        if key not in self.lists:
            self.lists[key] = fn().compile(colors)
        return self.lists[key]

    def draw(self, wheel_spin=0.0, steer=0.0, brake=False, reflect=False):
        glCallList(self.compiled("body", self.build_body))
        for tex, fn, alpha in self.textured:
            gfx.bind(tex, repeat=False)
            if alpha:
                glEnable(GL_ALPHA_TEST)
                glAlphaFunc(GL_GREATER, 0.5)
                glDisable(GL_CULL_FACE)
            glCallList(self.compiled(tex, fn))
            if alpha:
                glDisable(GL_ALPHA_TEST)
                glEnable(GL_CULL_FACE)
            glDisable(GL_TEXTURE_2D)
        for x, y, z, front, key in self.wheels:
            glPushMatrix()
            glTranslatef(x, y, z)
            if front:
                glRotatef(math.degrees(steer), 0, 1, 0)
            glRotatef(math.degrees(wheel_spin), 1, 0, 0)
            glCallList(self.compiled(key, getattr(self, "build_" + key)))
            glPopMatrix()
        self.draw_extra(wheel_spin)

    def draw_extra(self, wheel_spin):
        pass

    def draw_shadow_shape(self):
        glCallList(self.compiled("shadow", self.build_body, False))


class CNGModel(SimpleModel):
    def __init__(self, color):
        super().__init__()
        self.color = color
        self.length, self.width, self.height = 2.7, 1.32, 1.78
        self.wheels = [(0.0, 0.24, 0.98, True, "wheel"), (0.62, 0.24, -0.82, False, "wheel"), (-0.62, 0.24, -0.82, False, "wheel")]
        self.head = [(0.0, 1.0, 1.33)]
        self.tail = [(0.5, 0.62, -1.36), (-0.5, 0.62, -1.36)]
        self.textured = [("cng_cage.png", self.build_cage, True)]
        self.driver = True

    def build_wheel(self):
        return wheel_mesh(0.24, 0.12, (0.55, 0.55, 0.58, 1))

    def build_body(self):
        m = Mesh()
        g = c4(self.color)
        dark = (self.color[0] * 0.6, self.color[1] * 0.6, self.color[2] * 0.6, 1)
        m.box(-0.64, 0.30, -1.32, 0.64, 0.78, 0.55, g)
        fr = [(-0.64, 0.30, 0.55), (0.64, 0.30, 0.55), (0.64, 1.18, 0.55), (-0.64, 1.18, 0.55)]
        to = [(-0.34, 0.38, 1.32), (0.34, 0.38, 1.32), (0.34, 0.98, 1.30), (-0.34, 0.98, 1.30)]
        quad_out(m, [fr[0], to[0], to[3], fr[3]], (1, 0, 0.3), g)
        quad_out(m, [fr[1], to[1], to[2], fr[2]], (-1, 0, 0.3), g)
        quad_out(m, [fr[3], fr[2], to[2], to[3]], (0, 1, 0.4), g)
        quad_out(m, [to[0], to[1], to[2], to[3]], (0, 0, 1), g)
        quad_out(m, [fr[0], fr[1], to[1], to[0]], (0, -1, 0), dark)
        ws = [(-0.58, 1.16, 0.56), (0.58, 1.16, 0.56), (0.52, 1.66, 0.36), (-0.52, 1.66, 0.36)]
        quad_out(m, ws, (0, 0.4, 1), GLASS)
        quad_out(m, ws, (0, -0.4, -1), GLASS)
        for s in (-1, 1):
            beam(m, (s * 0.60, 1.14, 0.56), (s * 0.55, 1.72, 0.34), 0.06, BLACK)
            beam(m, (s * 0.64, 0.78, -1.30), (s * 0.64, 1.74, -1.30), 0.07, dark)
            beam(m, (s * 0.64, 0.78, -0.40), (s * 0.64, 1.74, -0.40), 0.06, dark)
        for k in range(4):
            a0 = math.pi * k / 4
            a1 = math.pi * (k + 1) / 4
            p = [(math.cos(a0) * 0.68, 1.70 + math.sin(a0) * 0.12, -1.40), (math.cos(a0) * 0.68, 1.70 + math.sin(a0) * 0.12, 0.42),
                 (math.cos(a1) * 0.68, 1.70 + math.sin(a1) * 0.12, 0.42), (math.cos(a1) * 0.68, 1.70 + math.sin(a1) * 0.12, -1.40)]
            quad_out(m, p, (math.cos((a0 + a1) / 2), 1, 0), (0.08, 0.10, 0.08, 1))
            quad_out(m, p, (0, -1, 0), (0.15, 0.15, 0.15, 1))
        m.box(-0.66, 0.30, -1.40, 0.66, 1.70, -1.30, g)
        m.box(-0.3, 0.4, -1.42, 0.3, 0.62, -1.40, (0.95, 0.95, 0.95, 1))
        for s in (-1, 1):
            m.box(s * 0.5 - 0.08, 0.55, -1.43, s * 0.5 + 0.08, 0.68, -1.40, (0.6, 0.05, 0.05, 1))
        disc(m, 0.0, 1.0, 1.31, 0.09, (0, 0, 1), (0.95, 0.95, 0.85, 1), 12)
        m.box(-0.62, 0.78, -1.28, 0.62, 0.90, -0.42, (0.15, 0.12, 0.10, 1))
        m.box(-0.62, 0.90, -1.28, 0.62, 1.40, -1.18, (0.15, 0.12, 0.10, 1))
        beam(m, (-0.42, 1.18, 0.52), (0.42, 1.18, 0.52), 0.04, BLACK)
        beam(m, (0.0, 1.18, 0.52), (0.0, 0.9, 0.6), 0.05, BLACK)
        return m

    def build_cage(self):
        m = Mesh()
        for s in (-1, 1):
            x = s * 0.645
            pts = [(x, 0.78, -1.30), (x, 0.78, 0.48), (x, 1.70, 0.40), (x, 1.70, -1.30)]
            quad_out(m, pts, (s, 0, 0), (1, 1, 1, 1), ((0, 0), (1.6, 0), (1.6, 1), (0, 1)))
        return m

    def draw_extra(self, wheel_spin):
        if self.driver:
            draw_seated(0.0, 0.80, 0.02, DRIVER_LOOK, 0.0)


class BusModel(SimpleModel):
    def __init__(self, livery="bus_blue", double=False):
        super().__init__()
        self.livery = livery
        self.double = double
        self.length = 10.8
        self.width = 2.5
        self.height = 4.4 if double else 3.25
        L = self.length / 2
        self.wheels = [(1.12, 0.5, 3.4, True, "wheel"), (-1.12, 0.5, 3.4, True, "wheel"),
                       (1.12, 0.5, -2.9, False, "wheel"), (-1.12, 0.5, -2.9, False, "wheel")]
        self.head = [(0.95, 0.9, L + 0.02), (-0.95, 0.9, L + 0.02)]
        self.tail = [(1.05, 0.95, -L - 0.03), (-1.05, 0.95, -L - 0.03)]
        self.textured = [(livery + ".jpg", self.build_sides, False), (livery + "_front.jpg", self.build_front, False),
                         (livery + "_back.jpg", self.build_back, False)]

    def build_wheel(self):
        return wheel_mesh(0.5, 0.32, (0.7, 0.7, 0.72, 1), 16)

    def build_body(self):
        m = Mesh()
        L = self.length / 2
        W = self.width / 2
        H = self.height
        m.box(-W + 0.02, 0.35, -L + 0.02, W - 0.02, 0.62, L - 0.02, (0.12, 0.12, 0.13, 1))
        m.floor_rect(-W, -L, W, L, H, None, (0.78, 0.78, 0.76, 1))
        m.box(-W * 0.5, H, -L * 0.6, W * 0.5, H + 0.12, -L * 0.2, (0.6, 0.6, 0.6, 1))
        for z in (3.4, -2.9):
            for s in (-1, 1):
                pts = []
                r = 0.62
                for k in range(9):
                    a = math.pi * k / 8
                    pts.append((s * (W + 0.005), 0.5 + math.sin(a) * r, z + math.cos(a) * r))
                for k in range(8):
                    quad_out(m, [(s * (W + 0.005), 0.5, z), pts[k], pts[k + 1], pts[k + 1]], (s, 0, 0), (0.05, 0.05, 0.05, 1))
        for s in (-1, 1):
            beam(m, (s * (W + 0.05), 2.2, L - 0.2), (s * (W + 0.35), 2.0, L + 0.05), 0.05, BLACK)
            m.box(s * (W + 0.3) - 0.04, 1.75, L - 0.02, s * (W + 0.3) + 0.04, 2.05, L + 0.1, (0.2, 0.25, 0.3, 1))
        return m

    def build_sides(self):
        m = Mesh()
        L = self.length / 2
        W = self.width / 2
        H = self.height
        m.wall(W, L, W, -L, 0.45, H, 0, 1, 0, 1)
        m.wall(-W, -L, -W, L, 0.45, H, 0, 1, 0, 1)
        return m

    def build_front(self):
        m = Mesh()
        L = self.length / 2
        W = self.width / 2
        m.wall(-W, L, W, L, 0.45, self.height, 0, 1, 0, 1)
        return m

    def build_back(self):
        m = Mesh()
        L = self.length / 2
        W = self.width / 2
        m.wall(W, -L, -W, -L, 0.45, self.height, 0, 1, 0, 1)
        return m


class TruckModel(SimpleModel):
    def __init__(self, cab_color=(0.85, 0.45, 0.10)):
        super().__init__()
        self.cab_color = cab_color
        self.length, self.width, self.height = 7.4, 2.4, 3.0
        self.wheels = [(1.05, 0.48, 2.5, True, "wheel"), (-1.05, 0.48, 2.5, True, "wheel"),
                       (1.05, 0.48, -2.3, False, "wheel"), (-1.05, 0.48, -2.3, False, "wheel")]
        self.head = [(0.85, 0.95, 3.72), (-0.85, 0.95, 3.72)]
        self.tail = [(1.0, 0.8, -3.72), (-1.0, 0.8, -3.72)]
        self.textured = [("truck_side.jpg", self.build_sides, False), ("truck_back.jpg", self.build_back, False)]

    def build_wheel(self):
        return wheel_mesh(0.48, 0.3, (0.6, 0.6, 0.62, 1))

    def build_body(self):
        m = Mesh()
        c = c4(self.cab_color)
        m.box(-1.15, 0.55, 1.75, 1.15, 2.7, 3.7, c)
        ws = [(-1.05, 1.75, 3.71), (1.05, 1.75, 3.71), (1.0, 2.55, 3.71), (-1.0, 2.55, 3.71)]
        quad_out(m, ws, (0, 0, 1), GLASS)
        for s in (-1, 1):
            quad_out(m, [(s * 1.151, 1.8, 2.3), (s * 1.151, 1.8, 3.4), (s * 1.151, 2.5, 3.4), (s * 1.151, 2.5, 2.3)], (s, 0, 0), GLASS)
        m.box(-0.9, 0.8, 3.7, 0.9, 1.35, 3.74, (0.2, 0.2, 0.2, 1))
        m.box(-1.2, 0.45, 3.70, 1.2, 0.65, 3.85, (0.25, 0.25, 0.25, 1))
        m.box(-1.2, 0.5, -3.7, 1.2, 0.95, 1.7, (0.15, 0.12, 0.10, 1))
        m.floor_rect(-1.2, -3.7, 1.2, 1.7, 3.0, None, (0.5, 0.4, 0.3, 1))
        m.box(-1.2, 0.95, 1.55, 1.2, 3.0, 1.72, (0.85, 0.55, 0.15, 1))
        m.box(-0.6, 3.0, -3.0, 0.6, 3.25, 1.0, (0.2, 0.45, 0.2, 1))
        return m

    def build_sides(self):
        m = Mesh()
        m.wall(1.2, 1.7, 1.2, -3.7, 0.95, 3.0, 0, 1, 0, 1)
        m.wall(-1.2, -3.7, -1.2, 1.7, 0.95, 3.0, 0, 1, 0, 1)
        return m

    def build_back(self):
        m = Mesh()
        m.wall(1.2, -3.7, -1.2, -3.7, 0.5, 3.0, 0, 1, 0, 1)
        return m


class RickshawModel(SimpleModel):
    def __init__(self, seed=0):
        super().__init__()
        rng = random.Random(seed)
        self.seat = rng.choice([(0.85, 0.10, 0.25), (0.10, 0.45, 0.80), (0.95, 0.70, 0.10), (0.15, 0.55, 0.30)])
        self.length, self.width, self.height = 2.5, 1.15, 2.2
        self.wheels = [(0.0, 0.33, 0.98, True, "wheel"), (0.56, 0.33, -0.62, False, "wheel"), (-0.56, 0.33, -0.62, False, "wheel")]
        self.head = []
        self.tail = [(0.45, 0.6, -0.95), (-0.45, 0.6, -0.95)]
        self.textured = [("rickshaw_hood.jpg", self.build_hood, False), ("rickshaw_art.jpg", self.build_art, False)]
        self.passenger = rng.random() < 0.55
        self.look = random_look(rng)
        self.pass_look = random_look(rng)
        self.pedal = 0.0

    def build_wheel(self):
        m = Mesh()
        r = 0.33
        seg = 16
        for k in range(seg):
            a0 = 2 * math.pi * k / seg
            a1 = 2 * math.pi * (k + 1) / seg
            beam(m, (0, math.cos(a0) * r, math.sin(a0) * r), (0, math.cos(a1) * r, math.sin(a1) * r), 0.05, TYRE)
        for k in range(8):
            a = k * math.pi / 4
            beam(m, (0, 0, 0), (0, math.cos(a) * r, math.sin(a) * r), 0.012, CHROME)
        return m

    def build_body(self):
        m = Mesh()
        frame = (0.15, 0.30, 0.55, 1)
        beam(m, (0, 0.33, 0.98), (0, 0.95, 0.85), 0.05, CHROME)
        beam(m, (0, 0.95, 0.85), (0, 0.85, 0.30), 0.06, frame)
        beam(m, (0, 0.85, 0.30), (0, 0.42, -0.45), 0.06, frame)
        beam(m, (-0.3, 1.05, 0.88), (0.3, 1.05, 0.88), 0.03, CHROME)
        m.box(-0.12, 0.95, 0.22, 0.12, 1.02, 0.42, (0.1, 0.1, 0.1, 1))
        beam(m, (-0.6, 0.33, -0.62), (0.6, 0.33, -0.62), 0.05, frame)
        m.box(-0.55, 0.40, -0.95, 0.55, 0.62, -0.25, c4(self.seat))
        m.box(-0.55, 0.62, -0.80, 0.55, 0.78, -0.30, (0.95, 0.85, 0.20, 1))
        m.box(-0.55, 0.78, -0.95, 0.55, 1.25, -0.82, c4(self.seat))
        m.box(-0.58, 0.20, -0.20, 0.58, 0.26, 0.15, (0.4, 0.3, 0.2, 1))
        for s in (-1, 1):
            beam(m, (s * 0.56, 0.62, -0.25), (s * 0.56, 1.2, -0.25), 0.03, CHROME)
        return m

    def build_hood(self):
        m = Mesh()
        seg = 8
        r = 0.62
        for k in range(seg):
            a0 = math.pi * k / seg
            a1 = math.pi * (k + 1) / seg
            p = [(math.cos(a0) * r, 1.25 + math.sin(a0) * 0.85, -1.0), (math.cos(a0) * r * 0.95, 1.18 + math.sin(a0) * 0.75, -0.2),
                 (math.cos(a1) * r * 0.95, 1.18 + math.sin(a1) * 0.75, -0.2), (math.cos(a1) * r, 1.25 + math.sin(a1) * 0.85, -1.0)]
            uv = ((k / seg, 0), (k / seg, 1), ((k + 1) / seg, 1), ((k + 1) / seg, 0))
            quad_out(m, p, (math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0), (1, 1, 1, 1), uv)
            quad_out(m, p, (-math.cos((a0 + a1) / 2), -math.sin((a0 + a1) / 2), 0), (0.5, 0.5, 0.5, 1), uv)
        return m

    def build_art(self):
        m = Mesh()
        quad_out(m, [(-0.5, 0.25, -0.97), (0.5, 0.25, -0.97), (0.5, 0.78, -0.97), (-0.5, 0.78, -0.97)], (0, 0, -1))
        return m

    def draw_extra(self, wheel_spin):
        draw_seated(0.0, 0.98, 0.32, self.look, wheel_spin * 0.33, pedal=True)
        if self.passenger:
            draw_seated(0.0, 0.62, -0.55, self.pass_look, 0.0)


SKIN = [(0.55, 0.38, 0.26), (0.45, 0.30, 0.20), (0.62, 0.45, 0.32), (0.38, 0.25, 0.17), (0.68, 0.50, 0.38)]
SHIRTS = [(0.92, 0.92, 0.90), (0.20, 0.35, 0.65), (0.75, 0.15, 0.15), (0.30, 0.55, 0.35), (0.85, 0.75, 0.45), (0.45, 0.45, 0.48),
          (0.95, 0.60, 0.20), (0.55, 0.25, 0.55), (0.15, 0.15, 0.18), (0.70, 0.82, 0.92)]
PANTS = [(0.12, 0.14, 0.20), (0.30, 0.28, 0.25), (0.85, 0.80, 0.70), (0.18, 0.18, 0.18), (0.35, 0.40, 0.55)]
LUNGI = [(0.20, 0.35, 0.60), (0.55, 0.15, 0.20), (0.25, 0.45, 0.30), (0.75, 0.60, 0.30), (0.40, 0.40, 0.45)]
WOMEN = [(0.85, 0.15, 0.40), (0.95, 0.70, 0.15), (0.25, 0.55, 0.65), (0.60, 0.20, 0.55), (0.90, 0.45, 0.25), (0.35, 0.65, 0.35),
         (0.95, 0.85, 0.80), (0.70, 0.10, 0.10)]
DRIVER_LOOK = dict(kind="shirt", skin=SKIN[0], top=(0.85, 0.85, 0.80), bottom=(0.20, 0.22, 0.28), hair=(0.05, 0.05, 0.05), scarf=None, scale=1.0, cap=None)


def random_look(rng, kind=None):
    kind = kind or rng.choice(["shirt", "shirt", "panjabi", "lungi", "salwar", "salwar", "saree", "burqa", "shirt"])
    skin = rng.choice(SKIN)
    hair = (0.04, 0.04, 0.04) if rng.random() < 0.85 else (0.35, 0.33, 0.30)
    scale = rng.uniform(0.92, 1.06)
    if kind in ("salwar", "saree", "burqa"):
        scale *= 0.94
    if rng.random() < 0.08 and kind != "burqa":
        scale *= 0.72
    look = dict(kind=kind, skin=skin, hair=hair, scale=scale, scarf=None, cap=None)
    if kind == "shirt":
        look.update(top=rng.choice(SHIRTS), bottom=rng.choice(PANTS))
    elif kind == "panjabi":
        look.update(top=rng.choice([(0.95, 0.95, 0.92), (0.85, 0.80, 0.65), (0.40, 0.55, 0.75), (0.25, 0.25, 0.28)]), bottom=(0.95, 0.95, 0.92))
        if rng.random() < 0.5:
            look["cap"] = (0.97, 0.97, 0.97)
    elif kind == "lungi":
        look.update(top=rng.choice(SHIRTS), bottom=rng.choice(LUNGI))
        if rng.random() < 0.3:
            look["scarf"] = (0.85, 0.20, 0.20)
    elif kind == "salwar":
        c = rng.choice(WOMEN)
        look.update(top=c, bottom=rng.choice([c, (0.95, 0.95, 0.92), (0.15, 0.15, 0.2)]), scarf=rng.choice(WOMEN))
    elif kind == "saree":
        c = rng.choice(WOMEN)
        look.update(top=c, bottom=c, scarf=c)
    else:
        look.update(top=(0.06, 0.06, 0.07), bottom=(0.06, 0.06, 0.07), hair=(0.06, 0.06, 0.07), scarf=(0.06, 0.06, 0.07))
    return look


_cube = {}


def cube():
    if "c" not in _cube:
        m = Mesh()
        m.box(-0.5, 0.0, -0.5, 0.5, 1.0, 0.5, bottom=True)
        _cube["c"] = m.compile(colors=False)
        m = Mesh()
        m.cylinder(0, 0, 0, 0.5, 1.0, 10, r_top=0.42)
        _cube["t"] = m.compile(colors=False)
        m = Mesh()
        m.dome(0, 0, 0, 0.5, 8, 4)
        m.dome(0, 0, 0, 0.5, 8, 4, squash=-1.0)
        _cube["s"] = m.compile(colors=False)
        gfx.reset_hooks.append(_cube.clear)
    return _cube


def part(kind, x, y, z, sx, sy, sz, col, rx=0.0):
    glPushMatrix()
    glTranslatef(x, y, z)
    if rx:
        glRotatef(rx, 1, 0, 0)
    glScalef(sx, sy, sz)
    glColor4f(col[0], col[1], col[2], 1)
    glCallList(cube()[kind])
    glPopMatrix()


def limb(x, y, z, length, w, col, angle):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle + 180, 1, 0, 0)
    glScalef(w, length, w)
    glColor4f(col[0], col[1], col[2], 1)
    glCallList(cube()["c"])
    glPopMatrix()


def draw_person(look, phase=0.0, speed=0.0, pose="walk", arm=None):
    s = look["scale"]
    k = look["kind"]
    glPushMatrix()
    glScalef(s, s, s)
    swing = math.sin(phase) * min(1.0, speed / 1.2) * 32 if pose == "walk" else 0.0
    skin = look["skin"]
    top = look["top"]
    bottom = look["bottom"]
    dress = k in ("lungi", "saree", "burqa")
    if dress:
        part("t", 0, 0.05, 0, 0.42, 0.88, 0.32, bottom)
        for side in (-1, 1):
            part("c", side * 0.09, 0.0, 0.03 + math.sin(phase + (0 if side > 0 else math.pi)) * 0.06 * min(1, speed), 0.1, 0.06, 0.2, (0.15, 0.12, 0.1))
    else:
        for side in (-1, 1):
            a = swing * side
            limb(side * 0.1, 0.92, 0, 0.9, 0.14, bottom, a)
            glPushMatrix()
            glTranslatef(side * 0.1, 0.92, 0)
            glRotatef(a, 1, 0, 0)
            part("c", 0, -0.92, 0.04, 0.12, 0.07, 0.24, (0.12, 0.10, 0.08))
            glPopMatrix()
    tunic = k in ("panjabi", "salwar", "burqa")
    if tunic:
        part("t", 0, 0.48 if k != "burqa" else 0.4, 0, 0.44, 1.0 if k != "burqa" else 1.1, 0.27, top)
    else:
        part("c", 0, 0.88, 0, 0.42, 0.62, 0.24, top)
    for side in (-1, 1):
        if arm is not None and side == 1:
            a = arm
        else:
            a = -swing * side * 0.8
        limb(side * 0.27, 1.46, 0, 0.6, 0.11, top, a)
        glPushMatrix()
        glTranslatef(side * 0.27, 1.46, 0)
        glRotatef(a, 1, 0, 0)
        part("c", 0, -0.66, 0, 0.09, 0.1, 0.09, skin)
        glPopMatrix()
    part("c", 0, 1.48, 0, 0.12, 0.08, 0.12, skin)
    part("s", 0, 1.68, 0.01, 0.24, 0.28, 0.25, skin)
    if k == "burqa":
        part("s", 0, 1.70, -0.01, 0.27, 0.32, 0.27, (0.06, 0.06, 0.07))
        part("c", 0, 1.64, 0.115, 0.16, 0.06, 0.03, skin)
    elif k in ("salwar", "saree"):
        part("s", 0, 1.72, -0.03, 0.26, 0.28, 0.26, look["hair"])
        part("s", 0, 1.62, -0.12, 0.14, 0.14, 0.14, look["hair"])
        if look["scarf"]:
            part("c", 0, 1.28, 0.02, 0.48, 0.18, 0.28, look["scarf"])
    else:
        part("s", 0, 1.74, -0.02, 0.25, 0.2, 0.25, look["hair"])
        if look.get("cap"):
            part("s", 0, 1.78, 0, 0.24, 0.14, 0.24, look["cap"])
        if look.get("scarf"):
            part("c", 0, 1.38, 0.02, 0.46, 0.08, 0.27, look["scarf"])
    glPopMatrix()


def draw_seated(x, y, z, look, pedal_phase=0.0, pedal=False):
    glPushMatrix()
    glTranslatef(x, y, z)
    s = look.get("scale", 1.0)
    glScalef(s, s, s)
    top, bottom, skin = look["top"], look["bottom"], look["skin"]
    for side in (-1, 1):
        if pedal:
            a = math.sin(pedal_phase + (0 if side > 0 else math.pi)) * 22
            a1 = -70 - a
            limb(side * 0.1, 0.0, 0.05, 0.48, 0.13, bottom, a1)
            th = math.radians(a1 + 180)
            kx, ky, kz = side * 0.1, 0.48 * math.cos(th), 0.05 + 0.48 * math.sin(th)
            limb(kx, ky, kz, 0.5, 0.12, skin, 10 + a)
        else:
            limb(side * 0.1, 0.0, 0.0, 0.45, 0.14, bottom, -90)
            limb(side * 0.1, 0.0, 0.45, 0.45, 0.13, bottom, 0)
    part("c", 0, 0.0, 0.0, 0.40, 0.6, 0.24, top)
    for side in (-1, 1):
        limb(side * 0.25, 0.55, 0.0, 0.55, 0.1, top, -55)
    part("s", 0, 0.82, 0.02, 0.23, 0.27, 0.24, skin)
    part("s", 0, 0.88, -0.01, 0.24, 0.19, 0.24, look["hair"])
    glPopMatrix()


_car_models = {}


def car_model(style, color):
    key = (style, color)
    if key not in _car_models:
        _car_models[key] = CarModel(style, color)
    return _car_models[key]


_simple = {}


def shared(kind, key, factory):
    k = (kind, key)
    if k not in _simple:
        _simple[k] = factory()
    return _simple[k]
