import math
import random
from collections import defaultdict

from OpenGL.GL import *

import gfx
import models
from config import *
from env import Environment, billboards
from mesh import Mesh, beam, disc, quad_out

FAC_U = 12.8
MARBLE = (0.95, 0.95, 0.93, 1)
RED = (0.82, 0.07, 0.06, 1)
STONE = (0.70, 0.68, 0.64, 1)
BRONZE = (0.42, 0.30, 0.18, 1)
TREE_UV = {"rain": (0.0, 0.2, 0.0, 1.0), "flame": (0.2, 0.4, 0.0, 1.0), "palm": (0.4, 0.6, 0.0, 1.0),
           "banana": (0.6, 0.8, 0.0, 1.0), "shrub": (0.8, 1.0, 0.0, 0.25)}
TREE_SIZE = {"rain": (14.0, 13.0), "flame": (11.0, 10.0), "palm": (8.0, 12.0), "banana": (4.2, 4.6), "shrub": (2.4, 1.3)}
MATERIALS = [("grass", "grass.jpg"), ("crops", "crops.jpg"), ("turf", "turf.jpg"), ("dirt", "dirt.jpg"), ("road", "campus_road.jpg"),
             ("foot", "sidewalk.jpg"), ("plaza", "plaza.jpg"), ("plain", None),
             ("facade_cream", "facade_cream.jpg"), ("facade_pink", "facade_pink.jpg"), ("facade_blue", "facade_blue.jpg"),
             ("facade_grime", "facade_grime.jpg"), ("facade_brick", "facade_brick.jpg"), ("facade_glass_blue", "facade_glass_blue.jpg"),
             ("roof", "roof.jpg"), ("brick", "redbrick.jpg"), ("shops", "shops_a.jpg"), ("tarp", "tarp.jpg"), ("posters", "posters.jpg")]
LIT = [("facade_cream", "facade_cream_lit.jpg"), ("facade_pink", "facade_pink_lit.jpg"), ("facade_blue", "facade_blue_lit.jpg"),
       ("facade_grime", "facade_grime_lit.jpg"), ("facade_brick", "facade_brick_lit.jpg"), ("facade_glass_blue", "facade_glass_blue_lit.jpg"),
       ("shops", "shops_a_lit.jpg")]
ROADS = [((-320, 0), (870, 0), 6.5), ((420, 0), (420, 331), 5.0), ((110, -320), (110, 331), 5.0), ((110, 331), (870, 331), 5.0),
         ((870, -320), (870, 331), 5.0), ((110, -320), (870, -320), 5.0), ((520, -320), (520, 0), 4.6)]
BUILDINGS = [
    dict(key="auditorium", r=(124, 20, 200, 82), floors=3, fac="facade_brick", board="w", board2="s", style="hall"),
    dict(key=None, r=(215, 22, 300, 70), floors=4, fac="facade_cream", board=None),
    dict(key="tsc", r=(124, 145, 186, 205), floors=3, fac="facade_cream", board="w"),
    dict(key="mosque", r=(206, 150, 250, 192), floors=1, fac="facade_cream", board="s", style="mosque"),
    dict(key="agri", r=(200, 262, 330, 316), floors=4, fac="facade_brick", board="n"),
    dict(key="csm", r=(352, 232, 406, 292), floors=3, fac="facade_blue", board="e"),
    dict(key="faculty_ah", r=(250, 95, 340, 138), floors=3, fac="facade_cream", board="s"),
    dict(key="library", r=(434, 58, 522, 120), floors=2, fac="facade_glass_blue", board="w", style="modern"),
    dict(key="ag_engg", r=(434, 162, 545, 232), floors=4, fac="facade_brick", board="w"),
    dict(key="museum", r=(578, 16, 650, 60), floors=2, fac="facade_cream", board="s"),
    dict(key="fish_museum", r=(690, 16, 748, 56), floors=2, fac="facade_blue", board="s"),
    dict(key="vet", r=(600, 262, 722, 316), floors=4, fac="facade_brick", board="n"),
    dict(key="faculty_econ", r=(760, 150, 856, 216), floors=4, fac="facade_cream", board="e"),
    dict(key=None, r=(560, 98, 660, 150), floors=3, fac="facade_grime", board=None),
    dict(key=None, r=(560, 180, 700, 236), floors=4, fac="facade_cream", board=None),
    dict(key=None, r=(124, 232, 186, 316), floors=3, fac="facade_pink", board=None),
    dict(key="hall_shahjalal", r=(124, -132, 192, -38), floors=5, fac="facade_pink", board="w"),
    dict(key="hall_ashraful", r=(124, -252, 192, -160), floors=5, fac="facade_cream", board="w"),
    dict(key="hall_fazlul", r=(205, -306, 300, -252), floors=5, fac="facade_blue", board="s"),
    dict(key="hall_isha", r=(318, -306, 412, -252), floors=5, fac="facade_grime", board="s"),
    dict(key="hall_rokeya", r=(430, -132, 506, -40), floors=5, fac="facade_pink", board="e"),
    dict(key="hall_razia", r=(430, -240, 506, -150), floors=5, fac="facade_pink", board="e"),
    dict(key="hall_bangabandhu", r=(570, -132, 662, -40), floors=6, fac="facade_cream", board="n"),
    dict(key="hall_nazmul", r=(578, -262, 662, -170), floors=5, fac="facade_blue", board="n"),
    dict(key="kr_market", r=(534, -302, 556, -196), floors=1, fac="facade_grime", board="w", style="market"),
]
CAMPUS_CENTER = (450 - 450, 0)


def wr(mx0, mz0, mx1, mz1):
    return (ORIGIN_MX - max(mx0, mx1), min(mz0, mz1), ORIGIN_MX - min(mx0, mx1), max(mz0, mz1))


def wp(mx, mz):
    return ORIGIN_MX - mx, mz




class World:
    def __init__(self, track, env):
        self.track = track
        self.env = env
        self.rng = random.Random(1961)
        self.meshes = defaultdict(Mesh)
        self.lines = []
        self.lists = {}
        self.boards = []
        self.lamps = []
        self.people = []
        self.walkers = []
        self.parked = []
        self.boats = []
        self.t = 0.0
        self.track_grid = defaultdict(list)
        for i in range(0, track.n, 2):
            x, z = track.pos[i, 0], track.pos[i, 2]
            self.track_grid[(int(x // 20), int(z // 20))].append((x, z))
        self.build()
        gfx.reset_hooks.append(self.reset_gl)

    @property
    def sun_dir(self):
        return self.env.sun_dir

    def reset_gl(self):
        self.lists = {}

    def release(self):
        if self.reset_gl in gfx.reset_hooks:
            gfx.reset_hooks.remove(self.reset_gl)
        for m in self.parked:
            if hasattr(m[0], "release"):
                m[0].release()

    def near_track(self, x, z, r):
        cx, cz = int(x // 20), int(z // 20)
        n = int(r // 20) + 1
        r2 = r * r
        for i in range(cx - n, cx + n + 1):
            for j in range(cz - n, cz + n + 1):
                for px, pz in self.track_grid.get((i, j), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 < r2:
                        return True
        return False

    def m(self, mat):
        return self.meshes[mat]

    def build(self):
        self.build_ground()
        self.build_roads()
        for b in BUILDINGS:
            self.building(b)
        self.build_gate()
        self.build_shaheed_minar()
        self.build_bijoy()
        self.build_botanical()
        self.build_ghat()
        self.build_field()
        self.build_farm()
        self.build_outskirts()
        self.build_trees()
        self.build_lamps()
        self.build_people()
        self.build_parked()

    def build_ground(self):
        x0, z0, x1, z1 = wr(-700, -900, 905, 1100)
        self.chunked_floor("grass", (x0, z0, x1, z1), -0.03, 12.0, 50.0)
        for rect in ((x1, -2500, x1 + 2500, 2500), (x0 - 2500, -2500, x1, z0), (x0 - 2500, z1, x1, 2500)):
            self.chunked_floor("grass", rect, -0.03, 8.0, 250.0)
        bx0, _, bx1, _ = wr(905, 0, 935, 0)
        bank = (0.36, 0.42, 0.26, 1)
        for k in range(30):
            za, zb = -1500 + k * 100, -1500 + (k + 1) * 100
            quad_out(self.m("dirt"), [(bx1, -0.03, za), (bx1, -0.03, zb), (bx0, -1.3, zb), (bx0, -1.3, za)], (0.3, 1, 0), bank)
        fx0, _, fx1, _ = wr(1240, 0, 1400, 0)
        self.chunked_floor("dirt", (fx0 - 1500, -1500, fx1, 1500), -0.2, 9.0, 100.0)
        for k in range(30):
            za, zb = -1500 + k * 100, -1500 + (k + 1) * 100
            quad_out(self.m("dirt"), [(fx1, -0.2, za), (fx1, -0.2, zb), (fx1 + 20, -1.3, zb), (fx1 + 20, -1.3, za)], (-0.3, 1, 0))
        for mx0, mz0, mx1, mz1 in ((140, 352, 400, 560), (440, 440, 860, 600), (140, 580, 860, 760), (-300, -330 - 260, 860, -345)):
            self.chunked_floor("crops", wr(mx0, mz0, mx1, mz1), -0.01, 12.0)
        rx0, _, rx1, _ = wr(1240, 0, 905, 0)
        self.water = (rx0 + 20, -1500, rx1 - 4, 1500)

    def build_roads(self):
        for (ax, az), (bx, bz), h in ROADS:
            x0, z0, x1, z1 = wr(ax, az, bx, bz)
            if abs(ax - bx) > abs(az - bz):
                z0, z1 = az - h, az + h
                rect = (x0, z0, x1, z1)
                self.chunked_floor("road", rect, 0.0, 10.0)
                for side in (-1, 1):
                    zz0, zz1 = (az + side * 10.0, az + side * 12.2)
                    self.footpath_strip(rect[0], min(zz0, zz1), rect[2], max(zz0, zz1), "x")
            else:
                xx = ORIGIN_MX - ax
                rect = (xx - h, z0, xx + h, z1)
                self.chunked_floor("road", rect, 0.0, 10.0)
                for side in (-1, 1):
                    a0, a1 = xx + side * 10.0, xx + side * 12.2
                    self.footpath_strip(min(a0, a1), z0, max(a0, a1), z1, "z")

    def footpath_strip(self, x0, z0, x1, z1, axis):
        cuts = []
        for (ax, az), (bx, bz), h in ROADS:
            if abs(ax - bx) > abs(az - bz):
                cuts.append(("z", az))
            else:
                cuts.append(("x", ORIGIN_MX - ax))
        segs = [(x0, x1) if axis == "x" else (z0, z1)]
        for kind, v in cuts:
            if kind != axis:
                continue
            nxt = []
            for a, b in segs:
                lo, hi = v - 22, v + 22
                if hi <= a or lo >= b:
                    nxt.append((a, b))
                    continue
                if lo > a:
                    nxt.append((a, lo))
                if hi < b:
                    nxt.append((hi, b))
            segs = nxt
        for a, b in segs:
            if b - a < 2:
                continue
            if axis == "x":
                self.chunked_floor("foot", (a, z0, b, z1), 0.03, 4.8)
            else:
                self.chunked_floor("foot", (x0, a, x1, b), 0.03, 4.8)

    def chunked_floor(self, mat, rect, y, scale, step=40.0):
        x0, z0, x1, z1 = rect
        mesh = self.m(mat)
        gx = x0
        while gx < x1 - 0.01:
            ex = min(x1, gx + step)
            gz = z0
            while gz < z1 - 0.01:
                ez = min(z1, gz + step)
                mesh.floor_rect(gx, gz, ex, ez, y, scale)
                gz = ez
            gx = ex

    def box_walls(self, mesh, x0, z0, x1, z1, y0, y1, u_scale=FAC_U, col=(1, 1, 1, 1), u_off=0.0):
        mesh.wall(x1, z0, x0, z0, y0, y1, u_off, u_off + (x1 - x0) / u_scale, 0, (y1 - y0) / u_scale, col)
        mesh.wall(x0, z1, x1, z1, y0, y1, u_off, u_off + (x1 - x0) / u_scale, 0, (y1 - y0) / u_scale, col)
        mesh.wall(x0, z0, x0, z1, y0, y1, u_off, u_off + (z1 - z0) / u_scale, 0, (y1 - y0) / u_scale, col)
        mesh.wall(x1, z1, x1, z0, y0, y1, u_off, u_off + (z1 - z0) / u_scale, 0, (y1 - y0) / u_scale, col)

    def building(self, b):
        x0, z0, x1, z1 = wr(*b["r"])
        style = b.get("style")
        floors = b["floors"]
        rng = self.rng
        if style == "modern":
            self.modern_library(x0, z0, x1, z1)
        elif style == "mosque":
            self.mosque(x0, z0, x1, z1)
        elif style == "market":
            self.market(x0, z0, x1, z1)
        else:
            base = 0.9
            top = base + floors * 3.2
            if style == "hall":
                top = 13.0
            mm = self.m(b["fac"])
            self.box_walls(mm, x0, z0, x1, z1, base, top, u_off=rng.randint(0, 3) * 0.25)
            pc = (0.55, 0.52, 0.48, 1)
            self.box_walls(self.m("plain"), x0, z0, x1, z1, -0.05, base, 100.0, pc)
            self.m("roof").floor_rect(x0, z0, x1, z1, top, 6.0)
            pm = self.m("plain")
            cap = (0.82, 0.78, 0.70, 1) if b["fac"] != "facade_brick" else (0.86, 0.84, 0.80, 1)
            pm.box(x0 - 0.2, top, z0 - 0.2, x1 + 0.2, top + 0.8, z0 + 0.2, cap)
            pm.box(x0 - 0.2, top, z1 - 0.2, x1 + 0.2, top + 0.8, z1 + 0.2, cap)
            pm.box(x0 - 0.2, top, z0, x0 + 0.2, top + 0.8, z1, cap)
            pm.box(x1 - 0.2, top, z0, x1 + 0.2, top + 0.8, z1, cap)
            for k in range(rng.randint(1, 3)):
                tx, tz = rng.uniform(x0 + 2, x1 - 2), rng.uniform(z0 + 2, z1 - 2)
                pm.cylinder(tx, top, tz, 0.65, 1.4, 10, (0.08, 0.08, 0.09, 1))
            if style == "hall":
                fx = (x0 + x1) / 2
                for side_z, nz in ((z0, -1), (z1, 1)):
                    pm.box(fx - 9, base, side_z + nz * 0.0 - (4 if nz < 0 else 0), fx + 9, top + 2.5, side_z + (4 if nz > 0 else 0), cap)
                gx = x1
                for k in range(5):
                    cz = z0 + 6 + k * (z1 - z0 - 12) / 4
                    pm.cylinder(gx + 3.0, 0.0, cz, 0.45, 9.0, 10, MARBLE)
                pm.box(gx, 9.0, z0 + 3, gx + 4.2, 10.0, z1 - 3, cap)
                pm.box(gx, 0.0, z0 + 3, gx + 4.2, 0.6, z1 - 3, STONE)
        if b.get("key") and b.get("board"):
            for side in (b["board"], b.get("board2")):
                if side:
                    self.add_board(b["key"], x0, z0, x1, z1, side, 3.6 if style != "market" else 3.3)

    def add_board(self, key, x0, z0, x1, z1, side, y):
        w, h = 7.0, 2.0
        if side == "s":
            cx = (x0 + x1) / 2
            a, b2 = (cx + w / 2, z0 - 0.08), (cx - w / 2, z0 - 0.08)
        elif side == "n":
            cx = (x0 + x1) / 2
            a, b2 = (cx - w / 2, z1 + 0.08), (cx + w / 2, z1 + 0.08)
        elif side == "e":
            cz = (z0 + z1) / 2
            a, b2 = (x0 - 0.08, cz - w / 2), (x0 - 0.08, cz + w / 2)
        else:
            cz = (z0 + z1) / 2
            a, b2 = (x1 + 0.08, cz + w / 2), (x1 + 0.08, cz - w / 2)
        self.boards.append(dict(a=(a[0], y, a[1]), b=(b2[0], y, b2[1]), h=h, tex="board_%s.jpg" % key))

    def modern_library(self, x0, z0, x1, z1):
        pm = self.m("plain")
        glass = self.m("facade_glass_blue")
        white = (0.94, 0.94, 0.92, 1)
        self.box_walls(glass, x0 + 1.5, z0 + 1.5, x1 - 1.5, z1 - 1.5, 0.0, 9.0)
        for y in (0.0, 4.2, 8.6):
            pm.box(x0, y, z0, x1, y + 0.7, z1, white)
        pm.box(x0 - 2.5, 9.3, z0 - 2.5, x1 + 2.5, 10.1, z1 + 2.5, white)
        for k in range(int((z1 - z0) / 5) + 1):
            zz = z0 + k * (z1 - z0) / max(1, int((z1 - z0) / 5))
            pm.box(x1 + 1.6, 0.0, zz - 0.15, x1 + 1.9, 9.3, zz + 0.15, white)
        for k in range(6):
            pm.box(x1, 0.0 - 0.0, (z0 + z1) / 2 - 6 + k * 2.4 - 0.1, x1 + 3.5 - k * 0.5, 0.18 + k * 0.0, (z0 + z1) / 2 - 6 + k * 2.4 + 2.3, STONE)
        self.m("roof").floor_rect(x0 - 2.5, z0 - 2.5, x1 + 2.5, z1 + 2.5, 10.11, 6.0)

    def mosque(self, x0, z0, x1, z1):
        pm = self.m("plain")
        white = (0.95, 0.94, 0.90, 1)
        self.box_walls(self.m("facade_cream"), x0, z0, x1, z1, 0.0, 7.0)
        self.m("roof").floor_rect(x0, z0, x1, z1, 7.0, 6.0)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        pm.cylinder(cx, 7.0, cz, 6.0, 1.5, 18, white)
        pm.dome(cx, 8.5, cz, 6.0, 18, 7, white, 1.1)
        pm.cylinder(cx, 8.5 + 6.6, cz, 0.15, 1.6, 6, (0.85, 0.7, 0.3, 1))
        mx, mz = x0 - 4, z0 + 3
        pm.cylinder(mx, 0.0, mz, 1.1, 22.0, 10, white, r_top=0.85)
        pm.cylinder(mx, 22.0, mz, 1.4, 0.6, 10, white)
        pm.dome(mx, 22.6, mz, 1.0, 10, 4, white, 1.6)

    def market(self, x0, z0, x1, z1):
        pm = self.m("plain")
        shops = self.m("shops")
        L = z1 - z0
        shops.wall(x1, z1, x1, z0, 0.0, 3.6, 0, L / 32.0, 0, 1)
        self.box_walls(self.m("facade_grime"), x0, z0, x1 - 0.02, z1, 3.6, 4.0, 40.0)
        tin = (0.55, 0.57, 0.60, 1)
        quad_out(pm, [(x0 - 0.5, 4.4, z0 - 0.5), (x1 + 2.6, 3.6, z0 - 0.5), (x1 + 2.6, 3.6, z1 + 0.5), (x0 - 0.5, 4.4, z1 + 0.5)], (0.3, 1, 0), tin)
        quad_out(pm, [(x0 - 0.5, 4.4, z0 - 0.5), (x1 + 2.6, 3.6, z0 - 0.5), (x1 + 2.6, 3.6, z1 + 0.5), (x0 - 0.5, 4.4, z1 + 0.5)], (-0.3, -1, 0), tin)
        self.m("roof").floor_rect(x0, z0, x1, z1, 3.62, 6.0)
        rng = self.rng
        for k in range(int(L / 9)):
            z = z0 + 4 + k * 9
            sx = x1 + 4.0
            pm.box(sx - 0.8, 0.0, z - 0.5, sx + 0.8, 0.9, z + 0.5, (0.45, 0.30, 0.18, 1))
            pm.cylinder(sx, 0.9, z, 0.14, 0.3, 8, (0.7, 0.7, 0.72, 1))
            for q in range(rng.randint(2, 4)):
                self.people.append(dict(x=sx + rng.uniform(1.0, 2.6), y=0.03, z=z + rng.uniform(-1.4, 1.4), h=rng.uniform(0, 6.28),
                                        look=models.random_look(rng, rng.choice(["shirt", "lungi", "panjabi", "salwar"]))))

    def build_gate(self):
        x, z = wp(22, 0)
        pm = self.m("brick")
        for side in (-1, 1):
            zz = side * 9.5
            pm.box(x - 1.4, 0.0, zz - 1.4, x + 1.4, 7.5, zz + 1.4, uv_scale=3.0)
            self.m("plain").box(x - 1.7, 7.5, zz - 1.7, x + 1.7, 8.1, zz + 1.7, (0.9, 0.88, 0.82, 1))
            self.m("plain").dome(x, 8.1, zz, 1.4, 12, 4, (0.9, 0.88, 0.82, 1), 1.0)
        self.m("plain").box(x - 0.6, 6.3, -8.2, x + 0.6, 8.2, 8.2, (0.12, 0.35, 0.24, 1))
        self.boards.append(dict(a=(x - 0.62, 6.4, 7.6), b=(x - 0.62, 6.4, -7.6), h=1.7, tex="board_main_gate.jpg"))
        self.boards.append(dict(a=(x + 0.62, 6.4, -7.6), b=(x + 0.62, 6.4, 7.6), h=1.7, tex="board_main_gate.jpg"))
        rng = self.rng
        for k in range(10):
            mx = -60 - k * 24
            for side in (-1, 1):
                if rng.random() < 0.8:
                    bx0, bz0, bx1, bz1 = wr(mx - 10, side * 14, mx + 10, side * (14 + rng.uniform(10, 18)))
                    h = rng.uniform(5, 12)
                    fac = rng.choice(["facade_grime", "facade_cream", "facade_pink"])
                    self.box_walls(self.m(fac), bx0, bz0, bx1, bz1, 0.0, h)
                    self.m("roof").floor_rect(bx0, bz0, bx1, bz1, h, 6.0)

    def frame(self, mm, cx, cz, y0, width, height, rot, lean=0.0, bend_at=None, bars=3):
        fx, fz = math.sin(rot), math.cos(rot)
        rx, rz = -fz, fx

        def P(s, h, f=0.0):
            return (cx + rx * s + fx * f, y0 + h, cz + rz * s + fz * f)
        hw = width / 2
        t = 0.4
        if bend_at is None:
            for s in (-hw, hw):
                beam(mm, P(s, 0), P(s, height), t, MARBLE)
            beam(mm, P(-hw - t / 2, height), P(hw + t / 2, height), t, MARBLE)
            for k in range(1, bars + 1):
                s = -hw + width * k / (bars + 1)
                beam(mm, P(s, 0), P(s, height), 0.13, MARBLE)
        else:
            bh = bend_at
            hy = bh + (height - bh) * math.cos(lean)
            hf = (height - bh) * math.sin(lean)
            for s in (-hw, hw):
                beam(mm, P(s, 0), P(s, bh), t, MARBLE)
                beam(mm, P(s, bh), P(s, hy, hf), t, MARBLE)
            beam(mm, P(-hw - t / 2, hy, hf), P(hw + t / 2, hy, hf), t, MARBLE)
            for k in range(1, bars + 1):
                s = -hw + width * k / (bars + 1)
                beam(mm, P(s, 0), P(s, bh), 0.13, MARBLE)
                beam(mm, P(s, bh), P(s, hy, hf), 0.13, MARBLE)

    def build_shaheed_minar(self):
        x0, z0, x1, z1 = wr(796, 16, 856, 72)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        pm = self.m("plain")
        for k in range(3):
            w, d = 40 - k * 4, 30 - k * 3
            y0 = k * 0.35
            self.m("plaza").floor_rect(cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2, y0 + 0.35, 5.0)
            self.box_walls(pm, cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2, y0, y0 + 0.35, 100.0, STONE)
        top = 1.05
        zc = cz + 5
        self.frame(pm, cx, zc, top, 3.6, 12.5, math.pi, lean=0.6, bend_at=8.5, bars=4)
        for s, rot, w, h in ((-4.4, 0.25, 2.3, 9.0), (4.4, -0.25, 2.3, 9.0), (-8.0, 0.5, 2.0, 7.2), (8.0, -0.5, 2.0, 7.2)):
            self.frame(pm, cx - s, zc + abs(s) * 0.3, top, w, h, math.pi + rot, bars=3)
        disc(pm, cx, top + 6.8, zc + 2.4, 3.8, (0, 0, -1), RED, 32)
        disc(pm, cx, top + 6.8, zc + 2.45, 3.8, (0, 0, 1), RED, 32)
        self.add_board("shaheed_minar", cx - 14, cz - 16, cx + 14, cz - 15.9, "s", 0.6)
        rng = self.rng
        for k in range(10):
            self.people.append(dict(x=cx + rng.uniform(-16, 16), y=1.08, z=cz + rng.uniform(-12, -2), h=rng.uniform(0, 6.28),
                                    look=models.random_look(rng)))

    def build_bijoy(self):
        x0, z0, x1, z1 = wr(796, -72, 856, -16)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        pm = self.m("plain")
        self.m("plaza").floor_rect(x0 + 6, z0 + 6, x1 - 6, z1 - 6, 0.05, 5.0)
        for k in range(3):
            w = 9 - k * 2
            pm.box(cx - w / 2, k * 0.9, cz - w / 2, cx + w / 2, (k + 1) * 0.9, cz + w / 2, (0.62, 0.60, 0.58, 1))
        base = 2.7
        for k, (ox, h, lean) in enumerate(((-1.6, 5.2, 0.08), (0.0, 6.2, 0.0), (1.6, 5.0, -0.08))):
            bx = cx + ox
            pm.box(bx - 0.45, base, cz - 0.35, bx + 0.45, base + h * 0.48, cz + 0.35, BRONZE)
            pm.box(bx - 0.55, base + h * 0.48, cz - 0.4, bx + 0.55, base + h * 0.85, cz + 0.4, BRONZE)
            pm.dome(bx, base + h * 0.85, cz, 0.42, 10, 4, BRONZE, 1.3)
            pm.dome(bx, base + h * 0.85, cz, 0.42, 10, 4, BRONZE, -0.4)
            beam(pm, (bx + 0.5, base + h * 0.8, cz), (bx + 0.9 + lean * 4, base + h * 1.05, cz - 0.2), 0.22, BRONZE)
        pole_top = base + 9.0
        beam(pm, (cx + 0.9, base + 4.8, cz - 0.2), (cx + 1.3, pole_top, cz - 0.3), 0.12, (0.3, 0.25, 0.2, 1))
        green = (0.0, 0.42, 0.31, 1)
        fz = cz - 0.3
        quad_out(pm, [(cx + 1.3, pole_top - 2.0, fz), (cx + 1.3, pole_top, fz), (cx + 4.6, pole_top, fz), (cx + 4.6, pole_top - 2.0, fz)], (0, 0, -1), green)
        quad_out(pm, [(cx + 1.3, pole_top - 2.0, fz), (cx + 1.3, pole_top, fz), (cx + 4.6, pole_top, fz), (cx + 4.6, pole_top - 2.0, fz)], (0, 0, 1), green)
        disc(pm, cx + 2.8, pole_top - 1.0, fz - 0.02, 0.6, (0, 0, -1), RED, 18)
        disc(pm, cx + 2.8, pole_top - 1.0, fz + 0.02, 0.6, (0, 0, 1), RED, 18)
        self.add_board("bijoy71", cx - 10, cz + 13, cx + 10, cz + 13.1, "n", 0.6)

    def build_botanical(self):
        x0, z0, x1, z1 = wr(680, -306, 856, -40)
        rng = self.rng
        col = (0.12, 0.25, 0.16, 1)
        for (ax, az, bx, bz) in ((x0, z0, x1, z0), (x1, z0, x1, z1), (x1, z1, x0, z1), (x0, z1, x0, z0)):
            self.fence(ax, az, bx, bz, col)
        self.trees_extra = []
        for k in range(260):
            x, z = rng.uniform(x0 + 3, x1 - 3), rng.uniform(z0 + 3, z1 - 3)
            self.trees_extra.append((x, z, rng.choice(["rain", "rain", "flame", "palm", "banana", "shrub"]), rng.uniform(0.7, 1.25)))
        gz = (z0 + z1) / 2
        self.add_board("botanical", x0, gz - 4, x0 + 0.1, gz + 4, "e", 2.4)

    def fence(self, ax, az, bx, bz, col, h=1.3):
        L = math.hypot(bx - ax, bz - az)
        fx, fz = (bx - ax) / L, (bz - az) / L
        pm = self.m("plain")
        cx, cz = (ax + bx) / 2, (az + bz) / 2
        pm.obox(cx, h - 0.08, cz, 0.05, 0.08, L / 2, fx, fz, col)
        pm.obox(cx, h * 0.45, cz, 0.04, 0.06, L / 2, fx, fz, col)
        p = 0.0
        while p <= L:
            pm.box(ax + fx * p - 0.05, 0.0, az + fz * p - 0.05, ax + fx * p + 0.05, h, az + fz * p + 0.05, col)
            p += 2.5

    def build_ghat(self):
        x0, z0, x1, z1 = wr(880, -228, 905, -182)
        pm = self.m("plain")
        n = 8
        for k in range(n):
            xa = x0 + (x1 - x0) * k / n
            y = -0.03 - k * 0.16
            pm.box(x0, -1.4, z0, xa + (x1 - x0) / n, y, z1, (0.66, 0.64, 0.60, 1))
        self.add_board("river_ghat", x1 - 2, z1 + 1, x1 - 1.9, z1 + 1.1, "n", 1.0)
        rng = self.rng
        for k in range(4):
            self.boats.append(dict(x=x0 - 6 - k * 5, z=(z0 + z1) / 2 + rng.uniform(-14, 14), ang=rng.uniform(0, 6.28), moving=False))
        for k in range(6):
            self.boats.append(dict(x=rng.uniform(x0 - 300, x0 - 40), z=rng.uniform(-700, 700), ang=rng.choice((0.0, math.pi)), moving=True,
                                   speed=rng.uniform(1.0, 2.0)))
        for k in range(12):
            self.people.append(dict(x=x1 - rng.uniform(1, 9), y=0.03, z=rng.uniform(z0 - 6, z1 + 6), h=rng.uniform(0, 6.28),
                                    look=models.random_look(rng)))
        for k in range(3):
            sx = x1 - 3 - k * 2.5
            sz = z1 + 4
            pm.box(sx - 0.7, 0.0, sz - 0.5, sx + 0.7, 1.0, sz + 0.5, (0.85, 0.75, 0.25, 1))
            pm.box(sx - 0.8, 1.9, sz - 0.6, sx + 0.8, 2.0, sz + 0.6, (0.85, 0.15, 0.15, 1))
            for q in (-0.7, 0.7):
                pm.box(sx + q - 0.04, 1.0, sz - 0.04, sx + q + 0.04, 1.9, sz + 0.04, (0.3, 0.3, 0.3, 1))

    def build_field(self):
        x0, z0, x1, z1 = wr(210, -232, 420, -66)
        self.chunked_floor("turf", (x0, z0, x1, z1), 0.0, 10.0)
        white = (0.95, 0.95, 0.95, 1)
        pm = self.m("plain")
        fx0, fz0, fx1, fz1 = x0 + 12, z0 + 10, x1 - 12, z1 - 10
        for a, b, c2, d in ((fx0, fz0, fx1, fz0 + 0.15), (fx0, fz1 - 0.15, fx1, fz1), (fx0, fz0, fx0 + 0.15, fz1), (fx1 - 0.15, fz0, fx1, fz1),
                            ((fx0 + fx1) / 2 - 0.07, fz0, (fx0 + fx1) / 2 + 0.07, fz1)):
            pm.floor_rect(a, b, c2, d, 0.02, None, white)
        cz = (fz0 + fz1) / 2
        for gx in (fx0, fx1):
            for s in (-3.6, 3.6):
                pm.box(gx - 0.06, 0.0, cz + s - 0.06, gx + 0.06, 2.4, cz + s + 0.06, white)
            pm.box(gx - 0.06, 2.34, cz - 3.6, gx + 0.06, 2.46, cz + 3.6, white)
        self.add_board("field", x0, z1 - 0.1, x0 + 20, z1, "n", 0.8)
        rng = self.rng
        for k in range(14):
            self.people.append(dict(x=rng.uniform(fx0 + 5, fx1 - 5), y=0.03, z=rng.uniform(fz0 + 5, fz1 - 5), h=rng.uniform(0, 6.28),
                                    look=models.random_look(rng, "shirt"), run=True))

    def build_farm(self):
        x0, z0, x1, z1 = wr(450, 360, 560, 420)
        pm = self.m("plain")
        self.box_walls(self.m("brick"), x0, z0, x1, z1, 0.0, 3.0, 4.0)
        quad_out(pm, [(x0 - 1, 3.0, z0 - 1), (x1 + 1, 3.0, z0 - 1), (x1 + 1, 5.0, (z0 + z1) / 2), (x0 - 1, 5.0, (z0 + z1) / 2)], (0, 1, -1), (0.62, 0.20, 0.15, 1))
        quad_out(pm, [(x0 - 1, 3.0, z1 + 1), (x1 + 1, 3.0, z1 + 1), (x1 + 1, 5.0, (z0 + z1) / 2), (x0 - 1, 5.0, (z0 + z1) / 2)], (0, 1, 1), (0.62, 0.20, 0.15, 1))
        rng = self.rng
        for k in range(9):
            x = rng.uniform(x0 - 30, x1 + 30)
            z = rng.uniform(z0 - 25, z0 - 8)
            a = rng.uniform(0, 6.28)
            self.cow(pm, x, z, a, rng.choice([(0.9, 0.9, 0.88, 1), (0.45, 0.30, 0.18, 1), (0.25, 0.2, 0.18, 1)]))

    def cow(self, pm, x, z, a, col):
        fx, fz = math.sin(a), math.cos(a)
        pm.obox(x, 0.75, z, 0.38, 0.7, 0.95, fx, fz, col)
        pm.obox(x + fx * 1.15, 1.05, z + fz * 1.15, 0.2, 0.42, 0.32, fx, fz, col)
        rx, rz = -fz, fx
        for s in (-0.25, 0.25):
            for f in (-0.7, 0.7):
                pm.obox(x + fx * f + rx * s, 0.0, z + fz * f + rz * s, 0.07, 0.75, 0.07, fx, fz, col)

    def build_outskirts(self):
        rng = self.rng
        for k in range(26):
            mx = 130 + k * 28
            if rng.random() < 0.6:
                x0, z0, x1, z1 = wr(mx, -345, mx + 20, -345 - rng.uniform(10, 20))
                h = rng.uniform(6, 14)
                fac = rng.choice(["facade_cream", "facade_pink", "facade_grime"])
                self.box_walls(self.m(fac), x0, z0, x1, z1, 0.0, h)
                self.m("roof").floor_rect(x0, z0, x1, z1, h, 6.0)
        fx0, _, fx1, _ = wr(1240, 0, 1400, 0)
        for k in range(120):
            self.trees_extra.append((rng.uniform(fx0 - 300, fx1 - 10), rng.uniform(-900, 900), rng.choice(["rain", "palm", "banana"]), rng.uniform(0.8, 1.3)))

    def build_trees(self):
        rng = self.rng
        trees = list(getattr(self, "trees_extra", []))
        for k in range(-320, 870, 13):
            for side in (-1, 1):
                x, z = wp(k, side * 10.6)
                trees.append((x, z, "palm", rng.uniform(0.9, 1.1)))
        for (ax, az), (bx, bz), h in ROADS[1:]:
            L = math.hypot(bx - ax, bz - az)
            n = int(L / 22)
            for k in range(n):
                t = (k + 0.5) / n
                mx, mz = ax + (bx - ax) * t, az + (bz - az) * t
                for side in (-1, 1):
                    if rng.random() < 0.7:
                        if abs(ax - bx) > abs(az - bz):
                            x, z = wp(mx + rng.uniform(-4, 4), mz + side * rng.uniform(13.5, 16))
                        else:
                            x, z = wp(mx + side * rng.uniform(13.5, 16), mz + rng.uniform(-4, 4))
                        trees.append((x, z, rng.choice(["rain", "rain", "flame", "flame"]), rng.uniform(0.85, 1.15)))
        for k in range(500):
            mx, mz = rng.uniform(-150, 890), rng.uniform(-330, 340)
            x, z = wp(mx, mz)
            trees.append((x, z, rng.choice(["rain", "flame", "palm", "banana", "shrub"]), rng.uniform(0.75, 1.2)))
        rects = [wr(*b["r"]) for b in BUILDINGS] + [wr(210, -232, 420, -66), wr(796, 16, 856, 72), wr(796, -72, 856, -16),
                                                     wr(450, 360, 560, 420), wr(880, -228, 905, -182)]
        tm = self.m("trees")
        sm = self.m("shadow")
        kept = 0
        for x, z, kind, s in trees:
            w, h = TREE_SIZE[kind]
            w *= s
            h *= s
            r = w * 0.3
            if self.near_track(x, z, WALL_DIST + 0.5 + (0 if kind == "shrub" else r * 0.3)):
                continue
            bad = False
            for x0, z0, x1, z1 in rects:
                if x0 - r < x < x1 + r and z0 - r < z < z1 + r:
                    bad = True
                    break
            if bad:
                continue
            on_road = False
            for (ax, az), (bx, bz), hw in ROADS:
                rx0, rz0, rx1, rz1 = wr(ax, az, bx, bz)
                if abs(ax - bx) > abs(az - bz):
                    if rx0 - 2 < x < rx1 + 2 and abs(z - az) < hw + 1.5:
                        on_road = True
                else:
                    if rz0 - 2 < z < rz1 + 2 and abs(x - (ORIGIN_MX - ax)) < hw + 1.5:
                        on_road = True
            if on_road or x < ORIGIN_MX - 902 and x > ORIGIN_MX - 1240:
                continue
            u0, u1, v0, v1 = TREE_UV[kind]
            for ang in (0.3, 0.3 + math.pi / 2):
                dx, dz = math.cos(ang) * w / 2, math.sin(ang) * w / 2
                tm.quad((x - dx, 0.0, z - dz), (x + dx, 0.0, z + dz), (x + dx, h, z + dz), (x - dx, h, z - dz), (0, 1, 0),
                        ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
            if kind in ("rain", "flame", "palm"):
                rr = w * (0.36 if kind != "palm" else 0.22)
                for k2 in range(10):
                    a0 = 2 * math.pi * k2 / 10
                    a1 = 2 * math.pi * (k2 + 1) / 10
                    sm.tri((x, 0.05, z), (x + math.cos(a1) * rr, 0.05, z + math.sin(a1) * rr), (x + math.cos(a0) * rr, 0.05, z + math.sin(a0) * rr), (0, 1, 0))
            kept += 1
        self.tree_count = kept

    def build_lamps(self):
        pole = (0.40, 0.41, 0.43, 1)
        pm = self.m("plain")
        for (ax, az), (bx, bz), h in ROADS:
            L = math.hypot(bx - ax, bz - az)
            n = int(L / 32)
            for k in range(n + 1):
                t = k / max(1, n)
                mx, mz = ax + (bx - ax) * t, az + (bz - az) * t
                side = 1 if k % 2 == 0 else -1
                horiz = abs(ax - bx) > abs(az - bz)
                if horiz:
                    x, z = wp(mx, mz + side * 9.9)
                    ex, ez = x, z - side * 2.0
                else:
                    x, z = wp(mx + side * 9.9, mz)
                    ex, ez = x + side * 2.0, z
                if self.near_track(x, z, WALL_DIST + 0.2):
                    continue
                pm.cylinder(x, 0.0, z, 0.09, 7.8, 8, pole, r_top=0.07)
                pm.box(min(x, ex) - 0.05, 7.7, min(z, ez) - 0.05, max(x, ex) + 0.05, 7.8, max(z, ez) + 0.05, pole)
                pm.box(ex - 0.25, 7.55, ez - 0.25, ex + 0.25, 7.72, ez + 0.25, (0.25, 0.25, 0.27, 1))
                self.lamps.append((ex, 7.5, ez))

    def build_people(self):
        rng = self.rng
        spots = [(124 - 4, 175, 8), (434 - 4, 90, 10), (124 - 4, 55, 6), (434 - 4, 200, 8), (352 + 58, 262, 6), (200, 331 - 16, 6)]
        for mx, mz, n in spots:
            for k in range(n):
                x, z = wp(mx + rng.uniform(-3, 3), mz + rng.uniform(-10, 10))
                if self.near_track(x, z, WALL_DIST + 0.6):
                    continue
                self.people.append(dict(x=x, y=0.03, z=z, h=rng.uniform(0, 6.28), look=models.random_look(rng)))
        for (ax, az), (bx, bz), h in ROADS:
            for side in (-1, 1):
                for k in range(int(math.hypot(bx - ax, bz - az) / 60)):
                    horiz = abs(ax - bx) > abs(az - bz)
                    t0 = rng.uniform(0, 1)
                    self.walkers.append(dict(a=(ax, az), b=(bx, bz), horiz=horiz, side=side * 11.1, t=t0, dir=rng.choice((-1, 1)),
                                             speed=rng.uniform(1.0, 1.5), L=math.hypot(bx - ax, bz - az), phase=rng.uniform(0, 6),
                                             look=models.random_look(rng)))

    def build_parked(self):
        rng = self.rng
        for mx, mz, a in ((112 - 14, 120, 0.0), (430, 140, math.pi)):
            x, z = wp(mx, mz)
            if not self.near_track(x, z, WALL_DIST + 2):
                self.parked.append((models.BusModel("bus_bau"), x, z, a))
        for k in range(6):
            x, z = wp(560 + 6 + rng.uniform(0, 2), -290 + k * 15)
            if not self.near_track(x, z, WALL_DIST + 1):
                self.parked.append((models.RickshawModel(k), x, z, rng.uniform(-0.4, 0.4)))
        for k in range(3):
            x, z = wp(-30 - k * 8, -12)
            self.parked.append((models.CNGModel((0.10, 0.48, 0.20)), x, z, math.pi / 2))

    def compile(self):
        if self.lists:
            return
        for mat, mesh in self.meshes.items():
            self.lists[mat] = mesh.compile(mat not in ("trees", "shadow"))

    def update(self, dt):
        self.t += dt
        for w in self.walkers:
            w["t"] += w["dir"] * w["speed"] * dt / max(1.0, w["L"])
            if w["t"] > 1 or w["t"] < 0:
                w["dir"] *= -1
                w["t"] = min(1.0, max(0.0, w["t"]))
            w["phase"] += dt * w["speed"] * 4.2
        for b in self.boats:
            if b.get("moving"):
                b["z"] += math.cos(b["ang"]) * b["speed"] * dt
                if abs(b["z"]) > 900:
                    b["ang"] += math.pi

    def draw(self, cam, dt):
        env = self.env
        self.compile()
        env.draw_sky(cam, CAMPUS_CENTER)
        env.setup_light()
        glEnable(GL_LIGHTING)
        glColor4f(1, 1, 1, 1)
        for mat, tex in MATERIALS:
            lid = self.lists.get(mat)
            if not lid:
                continue
            if tex:
                gfx.bind(tex)
            else:
                glDisable(GL_TEXTURE_2D)
            glCallList(lid)
        glDisable(GL_TEXTURE_2D)
        self.draw_water()
        self.draw_boards()
        self.draw_parked()
        self.draw_boats()
        self.track.draw()

    def draw_water(self):
        x0, z0, x1, z1 = self.water
        gfx.bind("water_river.jpg")
        sky = self.env.hor
        glColor4f(min(1, 0.75 + sky[0] * 0.35), min(1, 0.75 + sky[1] * 0.35), min(1, 0.75 + sky[2] * 0.35), 1)
        off = self.t * 0.02
        glNormal3f(0, 1, 0)
        glBegin(GL_QUADS)
        step = 60.0
        z = z0
        while z < z1:
            ze = min(z1, z + step)
            x = x0
            while x < x1:
                xe = min(x1, x + step)
                for px, pz in ((x, z), (x, ze), (xe, ze), (xe, z)):
                    glTexCoord2f(px / 40 + off * 0.3, pz / 40 + off)
                    glVertex3f(px, -1.0, pz)
                x = xe
            z = ze
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def draw_boards(self):
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        k = max(self.env.light_level, 0.75 * self.env.night)
        for bd in self.boards:
            gfx.bind(bd["tex"], repeat=False)
            glColor4f(k, k, k, 1)
            alpha = bd["tex"].endswith(".png")
            if alpha:
                glEnable(GL_ALPHA_TEST)
                glAlphaFunc(GL_GREATER, 0.4)
            ax, ay, az = bd["a"]
            bx, by, bz = bd["b"]
            h = bd["h"]
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex3f(ax, ay, az)
            glTexCoord2f(1, 0); glVertex3f(bx, by, bz)
            glTexCoord2f(1, 1); glVertex3f(bx, by + h, bz)
            glTexCoord2f(0, 1); glVertex3f(ax, ay + h, az)
            glEnd()
            if alpha:
                glDisable(GL_ALPHA_TEST)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)

    def draw_parked(self):
        glEnable(GL_LIGHTING)
        for model, x, z, a in self.parked:
            glPushMatrix()
            glTranslatef(x, 0.0, z)
            glRotatef(math.degrees(a), 0, 1, 0)
            model.draw(0.0, 0.0, False)
            glPopMatrix()

    def boat_list(self):
        if "boat" not in self.lists:
            m = Mesh()
            c4 = (0.42, 0.28, 0.16, 1)
            m.box(-0.9, -0.4, -4.0, 0.9, 0.5, 4.0, c4)
            beam(m, (0, 0.3, 4.0), (0, 1.2, 5.2), 0.35, c4)
            beam(m, (0, 0.3, -4.0), (0, 1.2, -5.2), 0.35, c4)
            for k in range(8):
                a0 = math.pi * k / 8
                a1 = math.pi * (k + 1) / 8
                p = [(math.cos(a0), 0.5 + math.sin(a0), -1.5), (math.cos(a0), 0.5 + math.sin(a0), 1.5),
                     (math.cos(a1), 0.5 + math.sin(a1), 1.5), (math.cos(a1), 0.5 + math.sin(a1), -1.5)]
                quad_out(m, p, (math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0), (0.55, 0.45, 0.25, 1))
                quad_out(m, p, (-math.cos((a0 + a1) / 2), -math.sin((a0 + a1) / 2), 0), (0.35, 0.28, 0.16, 1))
            self.lists["boat"] = m.compile()
        return self.lists["boat"]

    def draw_boats(self):
        lid = self.boat_list()
        for b in self.boats:
            glPushMatrix()
            glTranslatef(b["x"], -1.0 + 0.08 * math.sin(self.t * 1.3 + b["x"]), b["z"])
            glRotatef(math.degrees(b["ang"]), 0, 1, 0)
            glRotatef(2.0 * math.sin(self.t + b["z"]), 0, 0, 1)
            glCallList(lid)
            glPopMatrix()

    def draw_late(self, eye, fwd):
        env = self.env
        self.draw_people(eye, fwd)
        k = env.light_level
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glDepthMask(GL_FALSE)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-1.0, -4.0)
        glColor4f(0, 0, 0.02, 0.28 * env.shadow_alpha / 0.42)
        if self.lists.get("shadow"):
            glCallList(self.lists["shadow"])
        glDisable(GL_POLYGON_OFFSET_FILL)
        glDepthMask(GL_TRUE)
        gfx.bind("trees.png", repeat=False)
        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GREATER, 0.45)
        glDisable(GL_CULL_FACE)
        sc = env.sun_color
        glColor4f(min(1, k * (0.8 + 0.2 * sc[0])), min(1, k * (0.82 + 0.18 * sc[1])), min(1, k * (0.8 + 0.2 * sc[2])), 1)
        if self.lists.get("trees"):
            glCallList(self.lists["trees"])
        glEnable(GL_CULL_FACE)
        glDisable(GL_ALPHA_TEST)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        self.draw_night(eye)

    def draw_people(self, eye, fwd):
        glEnable(GL_LIGHTING)
        ex, ez = eye[0], eye[2]
        for p in self.people:
            dx, dz = p["x"] - ex, p["z"] - ez
            if dx * dx + dz * dz > 140 * 140 or (dx * fwd[0] + dz * fwd[1] < -5 and dx * dx + dz * dz > 100):
                continue
            glPushMatrix()
            glTranslatef(p["x"], p["y"], p["z"])
            glRotatef(math.degrees(p["h"]), 0, 1, 0)
            if p.get("run"):
                models.draw_person(p["look"], self.t * 7 + p["x"], 2.0)
            else:
                models.draw_person(p["look"], self.t * 0.5, 0.0, "idle")
            glPopMatrix()
        for w in self.walkers:
            (ax, az), (bx, bz) = w["a"], w["b"]
            mx, mz = ax + (bx - ax) * w["t"], az + (bz - az) * w["t"]
            if w["horiz"]:
                mz += w["side"]
                hd = math.atan2(-(bx - ax) * w["dir"], 0.0)
            else:
                mx += w["side"]
                hd = math.atan2(0.0, (bz - az) * w["dir"])
            x, z = wp(mx, mz)
            dx, dz = x - ex, z - ez
            if dx * dx + dz * dz > 130 * 130 or (dx * fwd[0] + dz * fwd[1] < -5 and dx * dx + dz * dz > 100):
                continue
            if self.near_track(x, z, WALL_DIST + 0.4):
                continue
            glPushMatrix()
            glTranslatef(x, 0.03, z)
            glRotatef(math.degrees(hd), 0, 1, 0)
            models.draw_person(w["look"], w["phase"], w["speed"])
            glPopMatrix()

    def draw_night(self, eye):
        env = self.env
        n = env.night
        if n < 0.02 and not env.lamps:
            return
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glEnable(GL_FOG)
        glFogfv(GL_FOG_COLOR, (0, 0, 0, 1))
        if n > 0.02:
            glBlendFunc(GL_CONSTANT_COLOR, GL_ONE)
            kk = n * 0.8
            glBlendColor(kk, kk, kk, 1)
            for mat, tex in LIT:
                lid = self.lists.get(mat)
                if lid:
                    gfx.bind(tex)
                    glCallList(lid)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_TEXTURE_2D)
        if env.lamps:
            lk = max(n, 0.5)
            ex, ez = eye[0], eye[2]
            near = [(x, y, z) for x, y, z in self.lamps if (x - ex) ** 2 + (z - ez) ** 2 < 320 ** 2]
            glEnable(GL_POLYGON_OFFSET_FILL)
            glPolygonOffset(-2.0, -8.0)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, gfx.texture("pool"))
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            r = 10.0
            glBegin(GL_QUADS)
            for x, y, z in near:
                glColor4f(1.0, 0.78, 0.45, 0.45 * lk)
                glTexCoord2f(0, 0); glVertex3f(x - r, 0.12, z - r)
                glTexCoord2f(0, 1); glVertex3f(x - r, 0.12, z + r)
                glTexCoord2f(1, 1); glVertex3f(x + r, 0.12, z + r)
                glTexCoord2f(1, 0); glVertex3f(x + r, 0.12, z - r)
            glEnd()
            glDisable(GL_POLYGON_OFFSET_FILL)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDisable(GL_TEXTURE_2D)
            items = []
            for x, y, z in near:
                items.append(((x, y, z), 2.4, (1.0, 0.8, 0.5), 0.85 * lk))
                items.append(((x, y, z), 8.0, (1.0, 0.75, 0.45), 0.15 * lk))
            billboards(items, "glow")
        glDepthMask(GL_TRUE)
        env.fog_on()
        glEnable(GL_LIGHTING)


def make_env(time_i, weather_i):
    name, hour = TIMES[time_i]
    w = WEATHERS[weather_i].lower()
    env = Environment(hour, False, w)
    env.update(0.01)
    return env
