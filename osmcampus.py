import math
import random

from OpenGL.GL import *

import campus
import gfx
import models
from config import *
from env import billboards
from mesh import Mesh, beam, disc, quad_out

for _m in (("bau_red", "facade_bau_red.jpg"), ("bau_white", "facade_bau_white.jpg"), ("bwall", "bwall.jpg")):
    if _m not in campus.MATERIALS:
        campus.MATERIALS.append(_m)
for _m in (("bau_red", "facade_bau_red_lit.jpg"), ("bau_white", "facade_bau_white_lit.jpg"), ("csm_wall", "csm_facade_lit.jpg")):
    if _m not in campus.LIT:
        campus.LIT.append(_m)

FAC_U = campus.FAC_U
TREE_UV = campus.TREE_UV
TREE_SIZE = campus.TREE_SIZE
FLAT = [("crops", "crops.jpg", -0.03, (-0.2, -1.0)), ("turf", "turf.jpg", -0.03, (-0.2, -1.0)),
        ("rim", "dirt.jpg", -0.02, (-0.3, -1.4)), ("foot", "sidewalk.jpg", -0.015, (-0.4, -1.5)),
        ("road", "campus_road.jpg", -0.01, (-0.5, -1.6))]
SOLID = [("grass", "grass.jpg"), ("plain", None), ("roof", "roof.jpg"), ("brick", "redbrick.jpg"), ("facade_cream", "facade_cream.jpg"),
         ("facade_pink", "facade_pink.jpg"), ("facade_grime", "facade_grime.jpg"), ("facade_brick", "facade_brick.jpg"),
         ("bau_red", "facade_bau_red.jpg"), ("bau_white", "facade_bau_white.jpg"), ("bwall", "bwall.jpg"), ("shops", "shops_a.jpg"),
         ("plaza", "plaza.jpg"), ("ballast", "ballast.jpg"), ("csm_wall", "csm_facade.jpg"), ("aet_wall", "aet_brick.jpg"),
         ("tin", "tin_green.jpg")]
ROAD_HALF_OSM = {"primary": 4.5, "secondary": 4.2, "tertiary": 4.0, "unclassified": 3.6, "residential": 3.2, "road": 3.2,
                 "service": 2.6, "living_street": 2.4, "track": 2.0, "footway": 1.0, "path": 0.9, "pedestrian": 1.6}
WORLD = 1500.0
UMBRELLA_COLS = [(0.85, 0.15, 0.15, 1), (0.95, 0.80, 0.10, 1), (0.10, 0.45, 0.80, 1), (0.10, 0.60, 0.25, 1), (0.95, 0.95, 0.92, 1),
                 (0.90, 0.40, 0.70, 1), (0.95, 0.50, 0.10, 1)]


def P(e, n):
    return (-e, n)


def signed_area(pts):
    s = 0.0
    for i in range(len(pts)):
        x0, z0 = pts[i]
        x1, z1 = pts[(i + 1) % len(pts)]
        s += x0 * z1 - x1 * z0
    return s / 2


def clean_poly(pts):
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 0.05:
            out.append(tuple(p))
    if len(out) > 2 and math.dist(out[0], out[-1]) < 0.05:
        out.pop()
    return out


def point_in_poly(x, z, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, zi = pts[i]
        xj, zj = pts[j]
        if (zi > z) != (zj > z) and x < (xj - xi) * (z - zi) / ((zj - zi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def triangulate(pts):
    n = len(pts)
    if n < 3:
        return []
    idx = list(range(n))
    if signed_area(pts) < 0:
        idx.reverse()
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 5000:
        guard += 1
        found = False
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-9:
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = pts[j]
                d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
                d2 = (c[0] - b[0]) * (p[1] - b[1]) - (c[1] - b[1]) * (p[0] - b[0])
                d3 = (a[0] - c[0]) * (p[1] - c[1]) - (a[1] - c[1]) * (p[0] - c[0])
                if d1 >= 0 and d2 >= 0 and d3 >= 0:
                    ok = False
                    break
            if ok:
                tris.append((i0, i1, i2))
                idx.pop(k)
                found = True
                break
        if not found:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    elif len(idx) > 3:
        for k in range(1, len(idx) - 1):
            tris.append((idx[0], idx[k], idx[k + 1]))
    return tris


def up_tri(mesh, a, b, c, y, scale=None, col=(1, 1, 1, 1)):
    if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0:
        b, c = c, b

    def uv(p):
        return (p[0] / scale, p[1] / scale) if scale else (0, 0)
    mesh.tri((a[0], y, a[1]), (b[0], y, b[1]), (c[0], y, c[1]), (0, 1, 0), uv(a), uv(b), uv(c), col)


def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + dx * t), pz - (az + dz * t))


class Grid:
    def __init__(self, cell=25.0):
        self.cell = cell
        self.g = {}

    def add_seg(self, ax, az, bx, bz, item, pad=0.0):
        c = self.cell
        x0, x1 = min(ax, bx) - pad, max(ax, bx) + pad
        z0, z1 = min(az, bz) - pad, max(az, bz) + pad
        for i in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for j in range(int(math.floor(z0 / c)), int(math.floor(z1 / c)) + 1):
                self.g.setdefault((i, j), []).append(item)

    def add_box(self, x0, z0, x1, z1, item):
        self.add_seg(x0, z0, x1, z1, item)

    def near(self, x, z, r=0.0):
        c = self.cell
        out = []
        seen = set()
        for i in range(int(math.floor((x - r) / c)), int(math.floor((x + r) / c)) + 1):
            for j in range(int(math.floor((z - r) / c)), int(math.floor((z + r) / c)) + 1):
                for it in self.g.get((i, j), ()):
                    if id(it) not in seen:
                        seen.add(id(it))
                        out.append(it)
        return out


class World(campus.World):
    def __init__(self, track, env):
        self.data = OSM
        self.sign_keys = track.info.get("signs", [])
        self.train = None
        self.ponds = []
        env.skyline_tex = "treeline.png"
        env.skyline_h = 60.0
        super().__init__(track, env)

    def build(self):
        self.trees = []
        self.whitewash = []
        self.trees_extra = []
        self.walk_track = []
        self.road_grid = Grid(25.0)
        self.bld_grid = Grid(30.0)
        self.water_grid = Grid(40.0)
        self.rail_grid = Grid(25.0)
        self.kept_buildings = []
        self.decals = []
        self.prepare()
        self.build_ground()
        self.build_roads()
        self.build_water()
        self.build_aquaculture()
        self.build_buildings()
        self.build_rail()
        self.build_stadium()
        self.build_market()
        self.build_mosque()
        self.build_signs()
        self.build_bwalls()
        self.build_gazebos()
        self.build_cows()
        self.build_trees()
        self.build_lamps()
        self.build_people()
        self.build_parked()

    def prepare(self):
        d = self.data
        self.roads = []
        for r in d["roads"]:
            pts = [P(e, n) for e, n in r["pts"]]
            half = ROAD_HALF_OSM.get(r["type"], 3.0)
            self.roads.append((pts, half, r["type"]))
            for a, b in zip(pts, pts[1:]):
                if max(abs(a[0]), abs(b[0]), abs(a[1]), abs(b[1])) > WORLD + 400:
                    continue
                self.road_grid.add_seg(a[0], a[1], b[0], b[1], (a[0], a[1], b[0], b[1], half), half + 2)
        self.waters = []
        for w in d["water"]:
            pts = clean_poly([P(e, n) for e, n in w["pts"]])
            if len(pts) >= 3:
                self.add_water(self.carve(pts, WALL_DIST + 2.5), w["name"])
        self.rails = []
        for r in d["rail"]:
            pts = [P(e, n) for e, n in r["pts"]]
            if r["type"] == "rail":
                clipped = [p for p in pts if abs(p[0]) < WORLD and abs(p[1]) < WORLD]
                if len(clipped) >= 2:
                    self.rails.append(clipped)
                    for a, b in zip(clipped, clipped[1:]):
                        self.rail_grid.add_seg(a[0], a[1], b[0], b[1], (a[0], a[1], b[0], b[1]), 4)
            elif r["type"] == "platform":
                self.platform = clean_poly(pts)
        self.areas = [(a["kind"], clean_poly([P(e, n) for e, n in a["pts"]])) for a in d["areas"]]

    def carve(self, pts, clear):
        dense = []
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L = math.dist(a, b)
            steps = max(1, int(L / 3.0))
            for s in range(steps):
                t = s / steps
                dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        if not any(self.near_track(x, z, clear) for x, z in dense):
            return pts
        out = []
        for x, z in dense:
            if self.near_track(x, z, clear):
                i, lat, along = self.track.nearest(x, z)
                p = self.track.pos[i]
                r = self.track.right[i]
                sgn = 1 if lat >= 0 else -1
                x, z = p[0] + r[0] * sgn * clear, p[2] + r[2] * sgn * clear
            if not out or math.dist(out[-1], (x, z)) > 0.6:
                out.append((x, z))
        return out if len(out) >= 3 and abs(signed_area(out)) > 20 else pts

    def add_water(self, pts, name=""):
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        item = dict(pts=pts, box=(min(xs), min(zs), max(xs), max(zs)), name=name)
        self.waters.append(item)
        self.water_grid.add_box(item["box"][0] - 3, item["box"][1] - 3, item["box"][2] + 3, item["box"][3] + 3, item)

    def road_dist(self, x, z):
        best = 1e9
        for ax, az, bx, bz, half in self.road_grid.near(x, z, 6):
            d = seg_dist(x, z, ax, az, bx, bz) - half
            if d < best:
                best = d
        return best

    def rail_dist(self, x, z):
        best = 1e9
        for ax, az, bx, bz in self.rail_grid.near(x, z, 6):
            best = min(best, seg_dist(x, z, ax, az, bx, bz))
        return best

    def in_water(self, x, z, pad=0.0):
        for w in self.water_grid.near(x, z, pad):
            x0, z0, x1, z1 = w["box"]
            if x0 - pad <= x <= x1 + pad and z0 - pad <= z <= z1 + pad:
                if point_in_poly(x, z, w["pts"]):
                    return True
                if pad > 0 and any(seg_dist(x, z, *w["pts"][k], *w["pts"][(k + 1) % len(w["pts"])]) < pad for k in range(len(w["pts"]))):
                    return True
        return False

    def in_building(self, x, z, pad=0.0):
        for b in self.bld_grid.near(x, z, pad):
            x0, z0, x1, z1 = b["box"]
            if x0 - pad <= x <= x1 + pad and z0 - pad <= z <= z1 + pad:
                if pad > 0 or point_in_poly(x, z, b["pts"]):
                    return True
        return False

    def free(self, x, z, track=WALL_DIST + 1.0, road=1.0, bld=1.0, water=1.0, rail=4.0):
        if abs(x) > WORLD or abs(z) > WORLD:
            return False
        if track and self.near_track(x, z, track):
            return False
        if road is not None and self.road_dist(x, z) < road:
            return False
        if bld is not None and self.in_building(x, z, bld):
            return False
        if water is not None and self.in_water(x, z, water):
            return False
        if rail and self.rail_dist(x, z) < rail:
            return False
        return True

    def find_spot(self, cx, cz, r0, r1, rng, tries=60, **kw):
        for _ in range(tries):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(r0, r1)
            x, z = cx + math.cos(a) * r, cz + math.sin(a) * r
            if self.free(x, z, **kw):
                return x, z
        return None

    def track_side_point(self, x, z):
        i, lat, along = self.track.nearest(x, z)
        p = self.track.pos[i]
        r = self.track.right[i]
        f = self.track.fwd[i]
        side = 1.0 if lat >= 0 else -1.0
        return i, p, r, f, side, abs(lat)

    def build_ground(self):
        self.chunked_floor("grass", (-WORLD, -WORLD, WORLD, WORLD), -0.05, 12.0, 50.0)
        for rect in ((-4000, -4000, 4000, -WORLD), (-4000, WORLD, 4000, 4000), (-4000, -WORLD, -WORLD, WORLD), (WORLD, -WORLD, 4000, WORLD)):
            self.chunked_floor("grass", rect, -0.05, 8.0, 250.0)
        for e0, n0, e1, n1 in ((-900, -1300, 900, -900), (520, -900, 1200, -150), (-1200, -1300, -760, 600), (360, 330, 1100, 900)):
            x0, z0 = P(e1, n0)
            x1, z1 = P(e0, n1)
            self.chunked_floor("crops", (x0, z0, x1, z1), FLAT[0][2], 12.0)

    def build_roads(self):
        rm = self.m("road")
        fm = self.m("foot")
        for pts, half, kind in self.roads:
            mesh = fm if kind in ("footway", "path", "pedestrian") else rm
            y = -0.015 if mesh is fm else -0.01
            scale = 6.0 if mesh is fm else 9.0
            for a, b in zip(pts, pts[1:]):
                if max(abs(a[0]), abs(a[1])) > WORLD and max(abs(b[0]), abs(b[1])) > WORLD:
                    continue
                dx, dz = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dz)
                if L < 0.01:
                    continue
                rx, rz = -dz / L * half, dx / L * half
                quad = [(a[0] + rx, a[1] + rz), (b[0] + rx, b[1] + rz), (b[0] - rx, b[1] - rz), (a[0] - rx, a[1] - rz)]
                up_tri(mesh, quad[0], quad[1], quad[2], y, scale)
                up_tri(mesh, quad[0], quad[2], quad[3], y, scale)
            for p in pts:
                if abs(p[0]) > WORLD or abs(p[1]) > WORLD:
                    continue
                seg = 12
                for k in range(seg):
                    a0 = 2 * math.pi * k / seg
                    a1 = 2 * math.pi * (k + 1) / seg
                    up_tri(mesh, p, (p[0] + math.cos(a0) * half, p[1] + math.sin(a0) * half), (p[0] + math.cos(a1) * half, p[1] + math.sin(a1) * half), y, scale)

    def build_water(self):
        pm = self.meshes["pond"]
        rim = self.m("rim")
        for w in self.waters:
            pts = w["pts"]
            for i0, i1, i2 in triangulate(pts):
                up_tri(pm, pts[i0], pts[i1], pts[i2], 0.0, 30.0)
            cx = sum(p[0] for p in pts) / len(pts)
            cz = sum(p[1] for p in pts) / len(pts)
            n = len(pts)
            for k in range(n):
                a, b = pts[k], pts[(k + 1) % n]
                out = []
                for p in (a, b):
                    dx, dz = p[0] - cx, p[1] - cz
                    L = math.hypot(dx, dz) or 1.0
                    out.append((p[0] + dx / L * 2.2, p[1] + dz / L * 2.2))
                up_tri(rim, a, b, out[1], FLAT[2][2], 5.0)
                up_tri(rim, a, out[1], out[0], FLAT[2][2], 5.0)

    def build_aquaculture(self):
        for kind, pts in self.areas:
            if kind != "aquaculture" or len(pts) < 3:
                continue
            xs = [p[0] for p in pts]
            zs = [p[1] for p in pts]
            cw, ch = 34.0, 22.0
            z = min(zs) + 2
            while z + ch < max(zs):
                x = min(xs) + 2
                while x + cw < max(xs):
                    corners = [(x, z), (x + cw, z), (x + cw, z + ch), (x, z + ch)]
                    if all(point_in_poly(px, pz, pts) for px, pz in corners) and not any(
                            self.near_track(px, pz, WALL_DIST + 3) for px, pz in corners + [(x + cw / 2, z + ch / 2)]):
                        if all(self.road_dist(px, pz) > 2 for px, pz in corners):
                            inner = [(x + 2.5, z + 2.5), (x + 2.5, z + ch - 2.5), (x + cw - 2.5, z + ch - 2.5), (x + cw - 2.5, z + 2.5)]
                            self.add_water(inner, "fish")
                            pm = self.meshes["pond"]
                            up_tri(pm, inner[0], inner[1], inner[2], 0.0, 30.0)
                            up_tri(pm, inner[0], inner[2], inner[3], 0.0, 30.0)
                            self.m("rim").floor_rect(x + 1.2, z + 1.2, x + cw - 1.2, z + ch - 1.2, FLAT[2][2], 5.0)
                    x += cw
                z += ch

    def building_ok(self, pts):
        for x, z in pts:
            if self.near_track(x, z, WALL_DIST + 2.0):
                return False
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L = math.dist(a, b)
            steps = int(L / 3) + 1
            for s in range(steps):
                t = s / steps
                if self.near_track(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, WALL_DIST + 2.0):
                    return False
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        for gx in range(int(min(xs)), int(max(xs)) + 1, 4):
            for gz in range(int(min(zs)), int(max(zs)) + 1, 4):
                if point_in_poly(gx, gz, pts) and self.near_track(gx, gz, ROAD_HALF + 1):
                    return False
        return True

    def build_buildings(self):
        rng = random.Random(77)
        jm = P(254, 5)
        bina = P(-110, 60)
        for b in self.data["buildings"]:
            pts = clean_poly([P(e, n) for e, n in b["pts"]])
            if len(pts) < 3 or abs(signed_area(pts)) < 8:
                continue
            if not self.building_ok(pts):
                continue
            if signed_area(pts) > 0:
                pts = pts[::-1]
            area = abs(signed_area(pts))
            cx = sum(p[0] for p in pts) / len(pts)
            cz = sum(p[1] for p in pts) / len(pts)
            levels = b["levels"]
            kind = b["kind"]
            name = b["name"].lower()
            if kind == "university" and not name and math.dist((cx, cz), P(257, 129)) < 8:
                continue
            special = "computer science" in name or "faculty of agricultural engineering" in name
            near_jm = math.dist((cx, cz), jm) < 75
            if kind in ("shed", "roof", "garage") or b["amenity"] == "toilets":
                levels = 1
            elif not levels:
                if kind == "university":
                    levels = 3
                elif near_jm:
                    levels = 1 if area < 120 else 2
                else:
                    levels = 1 if area < 70 else (2 if area < 400 else 3)
            levels = min(levels, 6)
            if "faculty" in name or "depertment" in name or "department" in name:
                fac = "bau_red" if "faculty" in name else "bau_white"
            elif "lab" in name:
                fac = "bau_white"
            elif kind == "university":
                fac = rng.choice(["bau_red", "bau_red", "bau_white"])
            elif math.dist((cx, cz), bina) < 140:
                fac = rng.choice(["facade_brick", "bau_red", "bau_white"])
            elif near_jm:
                fac = rng.choice(["facade_grime", "facade_cream", "facade_pink"])
            elif kind in ("shed", "roof"):
                fac = "facade_grime"
            else:
                fac = rng.choice(["facade_cream", "facade_pink", "facade_grime", "bau_red"])
            item = dict(pts=pts, box=(min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)),
                        c=(cx, cz), name=b["name"])
            self.kept_buildings.append(item)
            self.bld_grid.add_box(item["box"][0], item["box"][1], item["box"][2], item["box"][3], item)
            if "computer science" in name:
                self.csm_building(pts)
            elif "faculty of agricultural engineering" in name:
                self.aet_building(pts)
            else:
                self.extrude(pts, levels, fac, shops=near_jm and levels <= 2, rng=rng, shed=kind in ("shed", "roof"))
        self.aet_grounds()

    def extrude(self, pts, levels, fac, shops=False, rng=None, shed=False):
        base = 0.6
        top = base + levels * 3.2 if not shed else 4.2
        pm = self.m("plain")
        n = len(pts)
        per = 0.0
        u0 = (rng.randint(0, 3) * 0.25) if rng else 0.0
        cap = (0.86, 0.80, 0.68, 1) if fac == "bau_red" else (0.84, 0.83, 0.80, 1)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L = math.dist(a, b)
            ua = u0 + per / FAC_U
            ub = u0 + (per + L) / FAC_U
            pm.wall(a[0], a[1], b[0], b[1], -0.05, base, 0, 1, 0, 1, (0.55, 0.52, 0.48, 1))
            if shed:
                pm.wall(a[0], a[1], b[0], b[1], base, top, 0, 1, 0, 1, (0.62, 0.58, 0.52, 1))
            elif shops:
                self.m("shops").wall(a[0], a[1], b[0], b[1], base, base + 3.4, per / 32.0, (per + L) / 32.0, 0, 1)
                if top > base + 3.4:
                    self.m(fac).wall(a[0], a[1], b[0], b[1], base + 3.4, top, ua, ub, 0.25, 0.25 + (top - base - 3.4) / FAC_U)
            else:
                self.m(fac).wall(a[0], a[1], b[0], b[1], base, top, ua, ub, 0, (top - base) / FAC_U)
            per += L
            dx, dz = b[0] - a[0], b[1] - a[1]
            if L > 0.01 and not shed:
                nx, nz = -dz / L, dx / L
                pa = (a[0] + nx * 0.25, a[1] + nz * 0.25)
                pb = (b[0] + nx * 0.25, b[1] + nz * 0.25)
                pm.wall(pa[0], pa[1], pb[0], pb[1], top, top + 0.7, 0, 1, 0, 1, cap)
                pm.wall(b[0] - nx * 0.15, b[1] - nz * 0.15, a[0] - nx * 0.15, a[1] - nz * 0.15, top + 0.1, top + 0.7, 0, 1, 0, 1, cap)
                quad_out(pm, [(pa[0], top + 0.7, pa[1]), (pb[0], top + 0.7, pb[1]), (b[0] - nx * 0.15, top + 0.7, b[1] - nz * 0.15),
                              (a[0] - nx * 0.15, top + 0.7, a[1] - nz * 0.15)], (0, 1, 0), cap)
                if shops:
                    sh = (0.45, 0.47, 0.50, 1)
                    quad_out(pm, [(a[0], base + 3.4, a[1]), (b[0], base + 3.4, b[1]), (b[0] + nx * 1.6, base + 3.0, b[1] + nz * 1.6),
                                  (a[0] + nx * 1.6, base + 3.0, a[1] + nz * 1.6)], (0, 1, 0), sh)
                    quad_out(pm, [(a[0], base + 3.4, a[1]), (b[0], base + 3.4, b[1]), (b[0] + nx * 1.6, base + 3.0, b[1] + nz * 1.6),
                                  (a[0] + nx * 1.6, base + 3.0, a[1] + nz * 1.6)], (0, -1, 0), sh)
        roof = self.m("roof") if not shed else pm
        rc = (1, 1, 1, 1) if not shed else (0.50, 0.52, 0.55, 1)
        for i0, i1, i2 in triangulate(pts):
            up_tri(roof, pts[i0], pts[i1], pts[i2], top + (0.02 if not shed else 0.0), 6.0 if not shed else None, rc)
        if not shed and levels >= 2 and rng:
            for k in range(rng.randint(0, 2)):
                tx = sum(p[0] for p in pts) / n + rng.uniform(-2, 2)
                tz = sum(p[1] for p in pts) / n + rng.uniform(-2, 2)
                pm.cylinder(tx, top, tz, 0.6, 1.3, 10, (0.08, 0.08, 0.09, 1))

    def edge_board(self, pts, key, y):
        best = None
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L = math.dist(a, b)
            if L < 8:
                continue
            mx, mz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            i, lat, along = self.track.nearest(mx, mz)
            d = abs(lat) + abs(along) * 0.3
            dr = self.road_dist(mx, mz) + 6
            d = min(d, dr)
            if best is None or d < best[0]:
                best = (d, a, b, L)
        if not best:
            return
        _, a, b, L = best
        dx, dz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx, nz = -dz, dx
        cx, cz = (a[0] + b[0]) / 2 + nx * 0.1, (a[1] + b[1]) / 2 + nz * 0.1
        self.board_at(cx, cz, nx, nz, y, key, 7.0, 2.0)

    def board_at(self, cx, cz, nx, nz, y, key, w, h, tex=None):
        rx, rz = nz, -nx
        a = (cx - rx * w / 2, y, cz - rz * w / 2)
        b = (cx + rx * w / 2, y, cz + rz * w / 2)
        self.boards.append(dict(a=a, b=b, h=h, tex=tex or "board_%s.jpg" % key))

    def edge_frame(self, a, b):
        L = math.dist(a, b) or 1.0
        fx, fz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        return L, fx, fz, -fz, fx

    def wall_art(self, a, b, t, w, h, y, tex, off=0.06):
        L, fx, fz, nx, nz = self.edge_frame(a, b)
        cx, cz = a[0] + fx * L * t + nx * off, a[1] + fz * L * t + nz * off
        self.board_at(cx, cz, nx, nz, y, None, w, h, tex)

    def walls_tex(self, mat, pts, y0, y1, us, vs):
        per = 0.0
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L = math.dist(a, b)
            self.m(mat).wall(a[0], a[1], b[0], b[1], y0, y1, per / us, (per + L) / us, 0, (y1 - y0) / vs)
            per += L

    def parapet(self, pts, top, cap, h=0.7, t=0.25):
        pm = self.m("plain")
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L, fx, fz, nx, nz = self.edge_frame(a, b)
            if L < 0.01:
                continue
            pa = (a[0] + nx * 0.05, a[1] + nz * 0.05)
            pb = (b[0] + nx * 0.05, b[1] + nz * 0.05)
            ia = (a[0] - nx * t, a[1] - nz * t)
            ib = (b[0] - nx * t, b[1] - nz * t)
            pm.wall(pa[0], pa[1], pb[0], pb[1], top - 0.3, top + h, 0, 1, 0, 1, cap)
            pm.wall(ib[0], ib[1], ia[0], ia[1], top, top + h, 0, 1, 0, 1, cap)
            quad_out(pm, [(pa[0], top + h, pa[1]), (pb[0], top + h, pb[1]), (ib[0], top + h, ib[1]), (ia[0], top + h, ia[1])], (0, 1, 0), cap)

    def flat_poly(self, mesh, pts, y, scale=None, col=(1, 1, 1, 1)):
        for i0, i1, i2 in triangulate(pts):
            up_tri(mesh, pts[i0], pts[i1], pts[i2], y, scale, col)

    def ebox(self, mesh, e0, n0, e1, n1, y0, y1, col):
        x0, z0 = P(max(e0, e1), min(n0, n1))
        x1, z1 = P(min(e0, e1), max(n0, n1))
        mesh.box(x0, y0, z0, x1, y1, z1, col)

    def csm_building(self, pts):
        base, top = 0.5, 0.5 + 4 * 3.4
        pm = self.m("plain")
        stone = (0.70, 0.71, 0.70, 1)
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            pm.wall(a[0], a[1], b[0], b[1], -0.05, base, 0, 1, 0, 1, stone)
        self.walls_tex("csm_wall", pts, base, top, 12.8, 13.6)
        self.flat_poly(self.m("roof"), pts, top + 0.02, 6.0)
        self.parapet(pts, top, (0.86, 0.87, 0.86, 1))
        grey = (0.84, 0.85, 0.84, 1)
        self.ebox(pm, 260.6, 133.9, 265.6, 136.6, 0.0, top + 0.9, grey)
        for k in range(5):
            y = base + 3.4 * k + 3.1
            self.ebox(pm, 260.4, 133.7, 265.8, 134.0, y, y + 0.25, (0.74, 0.75, 0.74, 1))
        fx, fz = P(263.1, 133.85)
        self.board_at(fx, fz, 0.0, -1.0, top - 2.0, None, 5.0, 1.25, "board_csm_wall.jpg")
        self.board_at(fx, fz, 0.0, -1.0, 0.9, None, 3.4, 2.55, "mural_bioinfo.jpg")
        self.board_at(fx, fz, 0.0, -1.0, 5.6, None, 3.0, 1.2, "board_ict.jpg")
        self.ebox(pm, 265.6, 135.0, 272.0, 138.0, 3.0, 3.25, (0.80, 0.80, 0.78, 1))
        dx, dz = P(268.8, 134.95)
        self.board_at(dx, dz, 0.0, -1.0, 2.3, None, 3.2, 0.8, "board_dean.jpg")
        for k in range(3):
            e = 262 + k * 4
            x, z = P(e, 132.6)
            self.people.append(dict(x=x, y=0.03, z=z, h=math.pi, look=models.random_look(random.Random(k + 40))))
        self.csm_pts = pts

    def aet_building(self, pts):
        base, top = 0.4, 11.0
        pm = self.m("plain")
        red_dark = (0.66, 0.24, 0.21, 1)
        n = len(pts)
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            pm.wall(a[0], a[1], b[0], b[1], -0.05, base, 0, 1, 0, 1, (0.55, 0.30, 0.27, 1))
        self.walls_tex("aet_wall", pts, base, top, 12.8, 12.8)
        self.flat_poly(self.m("roof"), pts, top + 0.02, 6.0)
        self.parapet(pts, top, (0.74, 0.30, 0.26, 1), 0.9, 0.35)
        tower = [P(287, 117), P(287, 131), P(299, 131), P(299, 117)]
        if signed_area(tower) > 0:
            tower = tower[::-1]
        th = 18.0
        self.walls_tex("aet_wall", tower, top, th, 12.8, 12.8)
        self.flat_poly(self.m("roof"), tower, th + 0.02, 6.0)
        self.parapet(tower, th, (0.74, 0.30, 0.26, 1), 0.8, 0.3)
        for k in range(6):
            nn = 117.6 + k * 2.55
            self.ebox(pm, 286.4, nn - 0.3, 287.0, nn + 0.3, base, th + 0.6, red_dark)
        wx, wz = P(286.3, 124.0)
        self.board_at(wx, wz, 1.0, 0.0, 7.0, None, 7.0, 1.75, "board_aet_wall.jpg")
        lx, lz = P(287.2, 124.0)
        self.boards.append(dict(a=(lx, th + 0.9, lz + 6.5), b=(lx, th + 0.9, lz - 6.5), h=3.2, tex="roof_letters_aet.png"))
        for dz in (-4.5, 0.0, 4.5):
            beam(pm, (lx - 0.3, th + 0.8, lz + dz), (lx - 0.3, th + 3.2, lz + dz), 0.08, (0.3, 0.3, 0.3, 1))
        best = None
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            L, fx, fz, nx, nz = self.edge_frame(a, b)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if nx > 0.6 and L > 7 and mid[1] < P(0, 124)[1]:
                if best is None or L > best[0]:
                    best = (L, a, b)
        if best:
            L, a, b = best
            self.wall_art(a, b, 0.42, 5.2, 2.6, 0.6, "mural_code.jpg")
            self.wall_art(a, b, 0.85, 1.4, 2.8, 0.5, "mural_bie.jpg")

    def aet_grounds(self):
        pm = self.m("plain")
        court = [P(244, 121.5), P(244, 133.6), P(285, 133.6), P(285, 121.5)]
        self.flat_poly(self.m("foot"), court, FLAT[3][2], 5.0)
        xs = [p[0] for p in court]
        zs = [p[1] for p in court]
        item = dict(pts=court, box=(min(xs), min(zs), max(xs), max(zs)), c=(sum(xs) / 4, sum(zs) / 4), name="court")
        self.bld_grid.add_box(item["box"][0], item["box"][1], item["box"][2], item["box"][3], item)
        tin = self.m("tin")
        e0, e1, n0, n1 = 267.0, 285.5, 129.0, 133.4
        y0, y1 = 3.0, 3.35
        a = P(e0, n0)
        b = P(e1, n0)
        c = P(e1, n1)
        d = P(e0, n1)
        L = abs(e1 - e0)
        q = [(a[0], y0, a[1]), (b[0], y0, b[1]), (c[0], y1, c[1]), (d[0], y1, d[1])]
        uv = ((0, 0), (L / 2.5, 0), (L / 2.5, 1.6), (0, 1.6))
        quad_out(tin, q, (0, 1, 0), (1, 1, 1, 1), uv)
        quad_out(tin, q, (0, -1, 0), (0.7, 0.7, 0.7, 1), uv)
        e = e0 + 0.6
        while e < e1:
            for nn, hh in ((n0 + 0.3, y0), (n1 - 0.3, y1)):
                x, z = P(e, nn)
                pm.cylinder(x, 0.0, z, 0.1, hh, 8, (0.62, 0.64, 0.66, 1))
                pm.cylinder(x, 0.0, z, 0.115, 0.8, 8, (0.86, 0.42, 0.12, 1))
            e += 3.6
        cx, cz = P(277.0, 119.6)
        rx, rz = 5.0, 2.6
        ring = []
        for k in range(28):
            ang = 2 * math.pi * k / 28
            ring.append((cx + math.cos(ang) * rx, cz + math.sin(ang) * rz))
        if signed_area(ring) > 0:
            ring = ring[::-1]
        self.flat_poly(self.m("turf"), ring, 0.2, 4.0)
        curb = (0.80, 0.40, 0.38, 1)
        for k in range(len(ring)):
            p0, p1 = ring[k], ring[(k + 1) % len(ring)]
            pm.wall(p0[0], p0[1], p1[0], p1[1], -0.05, 0.22, 0, 1, 0, 1, curb)
        org = (0.98, 0.62, 0.10, 1)
        h = 1.7
        bz0, bz1 = cz - 0.15, cz + 0.15

        def bar(u0, v0, u1, v1, ox):
            x0, x1 = ox - u1, ox - u0
            pm.box(x0, 0.2 + v0, bz0, x1, 0.2 + v1, bz1, org)
        ox = cx + 2.2
        bar(0, 0, 0.35, h, ox)
        for v in (0, h / 2 - 0.15, h - 0.3):
            bar(0.35, v, 1.0, v + 0.3, ox)
        bar(1.0, 0.1, 1.3, h / 2 - 0.05, ox)
        bar(1.0, h / 2 + 0.05, 1.3, h - 0.1, ox)
        ox = cx + 0.4
        bar(0, 0, 0.35, 1.1, ox)
        bar(0, 1.3, 0.35, 1.65, ox)
        ox = cx - 0.5
        bar(0, 0, 0.35, h, ox)
        for v in (0, h / 2 - 0.15, h - 0.3):
            bar(0.35, v, 1.2, v + 0.3, ox)
        rng = random.Random(77)
        for k in range(6):
            x, z = cx + rng.uniform(-4, 4), cz - rng.uniform(3.2, 5.0)
            self.people.append(dict(x=x, y=0.03, z=z, h=rng.uniform(-0.6, 0.6), look=models.random_look(rng)))
        for e, n in ((250, 125), (283, 124)):
            x, z = P(e, n)
            self.add_tree(x, z, "banana", 0.55)
        ax, az = P(232.0, 130.4)
        self.decals.append((ax, az, 3.2, "alpana.png"))

    def build_rail(self):
        bm = self.m("ballast")
        pm = self.m("plain")
        steel = (0.55, 0.55, 0.58, 1)
        wood = (0.30, 0.22, 0.16, 1)
        self.crossings = []
        for pts in self.rails:
            for a, b in zip(pts, pts[1:]):
                L = math.dist(a, b)
                if L < 0.01:
                    continue
                fx, fz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                rx, rz = -fz, fx
                s = 0.0
                while s < L:
                    e = min(L, s + 3.0)
                    p0 = (a[0] + fx * s, a[1] + fz * s)
                    p1 = (a[0] + fx * e, a[1] + fz * e)
                    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
                    crossing = self.near_track(mid[0], mid[1], ROAD_HALF + 1.5) or self.road_dist(mid[0], mid[1]) < 0.5
                    if crossing:
                        if self.near_track(mid[0], mid[1], ROAD_HALF + 1.5):
                            self.crossings.append((mid, (fx, fz)))
                        s = e
                        continue
                    q = [(p0[0] + rx * 1.7, p0[1] + rz * 1.7), (p1[0] + rx * 1.7, p1[1] + rz * 1.7),
                         (p1[0] - rx * 1.7, p1[1] - rz * 1.7), (p0[0] - rx * 1.7, p0[1] - rz * 1.7)]
                    up_tri(bm, q[0], q[1], q[2], 0.12, 3.0)
                    up_tri(bm, q[0], q[2], q[3], 0.12, 3.0)
                    edge = (0.42, 0.40, 0.37, 1)
                    for ia, ib in ((0, 1), (2, 3)):
                        ax, az = q[ia]
                        bx, bz = q[ib]
                        if (-(bz - az)) * (ax - mid[0]) + (bx - ax) * (az - mid[1]) < 0:
                            ax, az, bx, bz = bx, bz, ax, az
                        pm.wall(ax, az, bx, bz, -0.05, 0.12, 0, 1, 0, 1, edge)
                    t = s + 0.35
                    while t < e:
                        cx, cz = a[0] + fx * t, a[1] + fz * t
                        pm.obox(cx, 0.12, cz, 1.25, 0.10, 0.12, rx, rz, wood)
                        t += 0.75
                    for g in (-0.72, 0.72):
                        cx, cz = (p0[0] + p1[0]) / 2 + rx * g, (p0[1] + p1[1]) / 2 + rz * g
                        pm.obox(cx, 0.22, cz, 0.04, 0.13, (e - s) / 2, fx, fz, steel)
                    s = e
        self.build_crossings()
        self.build_station()
        self.setup_train()

    def build_crossings(self):
        pm = self.m("plain")
        done = []
        for (mx, mz), (fx, fz) in self.crossings:
            if any(math.dist((mx, mz), d) < 25 for d in done):
                continue
            done.append((mx, mz))
            i, p, r, f, side, lat = self.track_side_point(mx, mz)
            for sd in (-1, 1):
                for along in (-6.0, 6.0):
                    bx = p[0] + r[0] * sd * (WALL_DIST + 1.2) + f[0] * along
                    bz = p[2] + r[2] * sd * (WALL_DIST + 1.2) + f[2] * along
                    pm.cylinder(bx, 0.0, bz, 0.12, 1.2, 8, (0.2, 0.2, 0.2, 1))
                    for k in range(6):
                        col = (0.9, 0.1, 0.1, 1) if k % 2 == 0 else (0.95, 0.95, 0.95, 1)
                        pm.box(bx - 0.07, 1.2 + k * 0.9, bz - 0.07, bx + 0.07, 1.2 + (k + 1) * 0.9, bz + 0.07, col)
                    disc(pm, bx, 1.0, bz, 0.25, (f[0] * -sd, 0, f[2] * -sd), (0.9, 0.05, 0.05, 1), 12,
                         axis="x" if abs(f[0]) > abs(f[2]) else "z")

    def build_station(self):
        plat = getattr(self, "platform", None)
        if not plat or len(plat) < 3:
            return
        if signed_area(plat) > 0:
            plat = plat[::-1]
        pm = self.m("plain")
        for k in range(len(plat)):
            a, b = plat[k], plat[(k + 1) % len(plat)]
            pm.wall(a[0], a[1], b[0], b[1], -0.05, 0.9, 0, 1, 0, 1, (0.62, 0.60, 0.57, 1))
        for i0, i1, i2 in triangulate(plat):
            up_tri(self.m("plaza"), plat[i0], plat[i1], plat[i2], 0.9, 4.0)
        xs = [p[0] for p in plat]
        zs = [p[1] for p in plat]
        cx, cz = sum(xs) / len(xs), sum(zs) / len(zs)
        longest = max(((math.dist(plat[k], plat[(k + 1) % len(plat)]), plat[k], plat[(k + 1) % len(plat)]) for k in range(len(plat))))
        L, a, b = longest
        fx, fz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        rx, rz = -fz, fx
        if self.rail_dist(cx + rx * 6, cz + rz * 6) < self.rail_dist(cx - rx * 6, cz - rz * 6):
            rx, rz = -rx, -rz
        for k in range(-5, 6):
            px, pz = cx + fx * k * 7, cz + fz * k * 7
            pm.cylinder(px + rx * 0.8, 0.9, pz + rz * 0.8, 0.1, 3.2, 8, (0.25, 0.35, 0.30, 1))
        sx0, sz0 = cx - fx * 40 + rx * 0.2, cz - fz * 40 + rz * 0.2
        sx1, sz1 = cx + fx * 40 + rx * 0.2, cz + fz * 40 + rz * 0.2
        roofc = (0.30, 0.45, 0.38, 1)
        quad_out(pm, [(sx0 - rx * 2.0, 4.0, sz0 - rz * 2.0), (sx1 - rx * 2.0, 4.0, sz1 - rz * 2.0), (sx1 + rx * 2.6, 4.4, sz1 + rz * 2.6),
                      (sx0 + rx * 2.6, 4.4, sz0 + rz * 2.6)], (0, 1, 0), roofc)
        quad_out(pm, [(sx0 - rx * 2.0, 4.0, sz0 - rz * 2.0), (sx1 - rx * 2.0, 4.0, sz1 - rz * 2.0), (sx1 + rx * 2.6, 4.4, sz1 + rz * 2.6),
                      (sx0 + rx * 2.6, 4.4, sz0 + rz * 2.6)], (0, -1, 0), (0.2, 0.25, 0.22, 1))
        bx, bz = cx + rx * 9.5, cz + rz * 9.5
        if self.free(bx, bz, track=WALL_DIST + 6, road=2, bld=1, water=1, rail=0):
            hw, hd = 4.5, 9.0
            poly = [(bx + fx * hd + rx * hw, bz + fz * hd + rz * hw), (bx - fx * hd + rx * hw, bz - fz * hd + rz * hw),
                    (bx - fx * hd - rx * hw, bz - fz * hd - rz * hw), (bx + fx * hd - rx * hw, bz + fz * hd - rz * hw)]
            if signed_area(poly) > 0:
                poly = poly[::-1]
            self.extrude(poly, 1, "bau_red")
            self.kept_buildings.append(dict(pts=poly, box=(min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly),
                                                           max(p[1] for p in poly)), c=(bx, bz), name="station"))
            self.bld_grid.add_box(min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly),
                                  self.kept_buildings[-1])
            self.board_at(cx + rx * 2.2 + fx * 0.0, cz + rz * 2.2, -rx, -rz, 2.4, "rail_station", 8.0, 2.2)
            self.board_at(bx + rx * (hw + 0.1), bz + rz * (hw + 0.1), rx, rz, 2.5, "rail_station", 7.0, 2.0)
        rng = random.Random(5)
        for k in range(16):
            t = rng.uniform(-60, 60)
            self.people.append(dict(x=cx + fx * t + rx * rng.uniform(-1.5, 1.8), y=0.93, z=cz + fz * t + rz * rng.uniform(-1.5, 1.8),
                                    h=rng.uniform(0, 6.28), look=models.random_look(rng)))

    def setup_train(self):
        if not self.rails:
            return
        pts = max(self.rails, key=lambda p: sum(math.dist(a, b) for a, b in zip(p, p[1:])))
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        self.train = dict(pts=pts, cum=cum, L=cum[-1], s=-300.0, dir=1, wait=8.0, speed=13.0, cars=8)

    def rail_at(self, s):
        tr = self.train
        pts, cum = tr["pts"], tr["cum"]
        s = max(0.0, min(tr["L"] - 0.01, s))
        lo, hi = 0, len(cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        a, b = pts[lo], pts[lo + 1]
        L = (cum[lo + 1] - cum[lo]) or 1.0
        t = (s - cum[lo]) / L
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, math.atan2(b[0] - a[0], b[1] - a[1])

    def build_stadium(self):
        for kind, pts in self.areas:
            if kind != "pitch" or len(pts) < 3:
                continue
            for i0, i1, i2 in triangulate(pts):
                up_tri(self.m("turf"), pts[i0], pts[i1], pts[i2], FLAT[1][2], 10.0)
            n = len(pts)
            best = max(((math.dist(pts[k], pts[(k + 1) % n]), pts[k], pts[(k + 1) % n]) for k in range(n)))
            L, a, b = best
            fx, fz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            rx, rz = -fz, fx
            cx = sum(p[0] for p in pts) / n
            cz = sum(p[1] for p in pts) / n
            white = (0.95, 0.95, 0.95, 1)
            pm = self.m("plain")
            hl, hw = 50.0, 32.0

            def F(u, v):
                return (cx + fx * u + rx * v, cz + fz * u + rz * v)

            def line(u0, v0, u1, v1):
                a2, b2 = F(u0, v0), F(u1, v1)
                dx, dz = b2[0] - a2[0], b2[1] - a2[1]
                LL = math.hypot(dx, dz) or 1
                ox, oz = -dz / LL * 0.07, dx / LL * 0.07
                up_tri(pm, (a2[0] + ox, a2[1] + oz), (b2[0] + ox, b2[1] + oz), (b2[0] - ox, b2[1] - oz), FLAT[1][2] + 0.012, None, white)
                up_tri(pm, (a2[0] + ox, a2[1] + oz), (b2[0] - ox, b2[1] - oz), (a2[0] - ox, a2[1] - oz), FLAT[1][2] + 0.012, None, white)
            for u0, v0, u1, v1 in ((-hl, -hw, hl, -hw), (-hl, hw, hl, hw), (-hl, -hw, -hl, hw), (hl, -hw, hl, hw), (0, -hw, 0, hw),
                                   (-hl, -20, -hl + 16, -20), (-hl + 16, -20, -hl + 16, 20), (-hl, 20, -hl + 16, 20),
                                   (hl, -20, hl - 16, -20), (hl - 16, -20, hl - 16, 20), (hl, 20, hl - 16, 20)):
                line(u0, v0, u1, v1)
            for k in range(24):
                a0, a1 = 2 * math.pi * k / 24, 2 * math.pi * (k + 1) / 24
                line(math.cos(a0) * 9.15, math.sin(a0) * 9.15, math.cos(a1) * 9.15, math.sin(a1) * 9.15)
            for gu in (-hl, hl):
                g0, g1 = F(gu, -3.66), F(gu, 3.66)
                for gx, gz in (g0, g1):
                    pm.cylinder(gx, 0.0, gz, 0.07, 2.44, 8, white)
                beam(pm, (g0[0], 2.44, g0[1]), (g1[0], 2.44, g1[1]), 0.12, white)
            dists = []
            for v in (-hw - 14, hw + 14):
                px, pz = F(0, v)
                i, lat, along = self.track.nearest(px, pz)
                dists.append((math.hypot(lat, along), v))
            sgn = 1 if max(dists)[1] > 0 else -1
            conc = (0.70, 0.69, 0.66, 1)
            for step in range(5):
                v0 = sgn * (hw + 8 + step * 1.6)
                v1 = sgn * (hw + 8 + (step + 1) * 1.6)
                y = 0.5 * (step + 1)
                c0, c1, c2, c3 = F(-40, v0), F(40, v0), F(40, v1), F(-40, v1)
                xs2 = [c[0] for c in (c0, c1, c2, c3)]
                zs2 = [c[1] for c in (c0, c1, c2, c3)]
                if self.near_track((min(xs2) + max(xs2)) / 2, (min(zs2) + max(zs2)) / 2, WALL_DIST + 6):
                    break
                pm.obox((c0[0] + c2[0]) / 2, 0.0, (c0[1] + c2[1]) / 2, 0.8, y, 40, fx, fz, conc)
            rng = random.Random(9)
            for k in range(18):
                u, v = rng.uniform(-hl + 4, hl - 4), rng.uniform(-hw + 4, hw - 4)
                x, z = F(u, v)
                self.people.append(dict(x=x, y=0.03, z=z, h=rng.uniform(0, 6.28), look=models.random_look(rng, "shirt"), run=True))
            for k in range(14):
                u = rng.uniform(-38, 38)
                st = rng.randint(0, 4)
                x, z = F(u, sgn * (hw + 8 + st * 1.6 + 0.8))
                if not self.near_track(x, z, WALL_DIST + 5):
                    self.people.append(dict(x=x, y=0.5 * (st + 1), z=z, h=math.atan2(-rx * sgn, -rz * sgn), look=models.random_look(rng)))

    def build_market(self):
        rng = random.Random(31)
        cx, cz = P(254, 5)
        pm = self.m("plain")
        placed = 0
        for k in range(400):
            if placed >= 26:
                break
            s = self.find_spot(cx, cz, 12, 70, rng, tries=1, track=WALL_DIST + 2.2, road=0.8, bld=1.0, water=1.0, rail=4.0)
            if not s:
                continue
            x, z = s
            if any(math.dist((x, z), (p[0], p[1])) < 4.5 for p in getattr(self, "_stalls", [])):
                continue
            self._stalls = getattr(self, "_stalls", []) + [(x, z)]
            placed += 1
            self.umbrella(pm, x, z, rng)
            pm.box(x - 0.8, 0.0, z - 0.5, x + 0.8, 0.85, z + 0.5, rng.choice([(0.45, 0.30, 0.18, 1), (0.75, 0.75, 0.78, 1), (0.3, 0.45, 0.6, 1)]))
            for q in range(rng.randint(2, 4)):
                a = rng.uniform(0, 2 * math.pi)
                px, pz = x + math.cos(a) * 1.5, z + math.sin(a) * 1.5
                cc = rng.choice([(0.85, 0.12, 0.12, 1), (0.10, 0.35, 0.75, 1), (0.95, 0.85, 0.2, 1), (0.15, 0.6, 0.3, 1)])
                pm.box(px - 0.22, 0.0, pz - 0.22, px + 0.22, 0.45, pz + 0.22, cc)
                if rng.random() < 0.7:
                    self.people.append(dict(x=px, y=0.03, z=pz, h=math.atan2(x - px, z - pz),
                                            look=models.random_look(rng, rng.choice(["shirt", "lungi", "panjabi", "salwar"]))))
            for q in range(rng.randint(0, 2)):
                self.people.append(dict(x=x + rng.uniform(-2.5, 2.5), y=0.03, z=z + rng.uniform(-2.5, 2.5), h=rng.uniform(0, 6.28),
                                        look=models.random_look(rng)))

    def umbrella(self, pm, x, z, rng, r=1.6, h=2.4):
        pm.cylinder(x, 0.0, z, 0.03, h + 0.4, 6, (0.8, 0.8, 0.8, 1))
        seg = 8
        cols = rng.sample(UMBRELLA_COLS, 2)
        for k in range(seg):
            a0 = 2 * math.pi * k / seg
            a1 = 2 * math.pi * (k + 1) / seg
            top = (x, h + 0.45, z)
            p0 = (x + math.cos(a0) * r, h, z + math.sin(a0) * r)
            p1 = (x + math.cos(a1) * r, h, z + math.sin(a1) * r)
            col = cols[k % 2]
            pm.tri(top, p1, p0, (math.cos((a0 + a1) / 2) * 0.3, 1, math.sin((a0 + a1) / 2) * 0.3), col=col)
            pm.tri(top, p0, p1, (0, -1, 0), col=tuple(c * 0.7 if i < 3 else c for i, c in enumerate(col)))

    def build_mosque(self):
        ex, en = 334, -37
        x, z = P(ex, en)
        for b in self.kept_buildings:
            if point_in_poly(x, z, b["pts"]):
                return self.board_near("jame_mosjid", x, z)
        rng = random.Random(3)
        spot = (x, z) if self.free(x, z, track=WALL_DIST + 16, road=10, bld=12, water=10, rail=14) else self.find_spot(
            x, z, 4, 40, rng, track=WALL_DIST + 16, road=10, bld=12, water=10, rail=14)
        if not spot:
            return
        x, z = spot
        self.mosque(x - 10, z - 9, x + 10, z + 9)
        item = dict(pts=[(x - 10, z - 9), (x + 10, z - 9), (x + 10, z + 9), (x - 10, z + 9)], box=(x - 14, z - 9, x + 10, z + 9), c=(x, z), name="mosque")
        self.kept_buildings.append(item)
        self.bld_grid.add_box(x - 14, z - 9, x + 10, z + 9, item)
        self.board_near("jame_mosjid", x, z)

    def board_near(self, key, x, z):
        i, p, r, f, side, lat = self.track_side_point(x, z)
        if lat > 120:
            return
        bx = p[0] + r[0] * side * (WALL_DIST + 3.0)
        bz = p[2] + r[2] * side * (WALL_DIST + 3.0)
        nx, nz = -r[0] * side * 0.75 - f[0] * 0.66, -r[2] * side * 0.75 - f[2] * 0.66
        L = math.hypot(nx, nz)
        self.post_sign(bx, bz, nx / L, nz / L, key)

    def post_sign(self, x, z, nx, nz, key, w=6.4, h=2.0, y=2.0):
        pm = self.m("plain")
        rx, rz = nz, -nx
        for s in (-1, 1):
            px, pz = x + rx * s * (w / 2 - 0.4), z + rz * s * (w / 2 - 0.4)
            pm.cylinder(px - nx * 0.12, 0.0, pz - nz * 0.12, 0.08, y + h, 8, (0.85, 0.85, 0.85, 1))
        pm.obox(x - nx * 0.06, y - 0.1, z - nz * 0.06, w / 2 + 0.1, h + 0.2, 0.05, rx, rz, (0.1, 0.3, 0.2, 1))
        self.board_at(x, z, nx, nz, y, key, w, h)
        self.board_at(x - nx * 0.13, z - nz * 0.13, -nx, -nz, y, key, w, h)

    def build_signs(self):
        for key in self.sign_keys:
            spot = OSM_SPOTS.get(key)
            if not spot:
                continue
            x, z = P(*spot)
            self.board_near(key, x, z)

    def build_bwalls(self):
        tr = self.track
        mm = self.m("bwall")
        pm = self.m("plain")
        cap = (0.90, 0.78, 0.45, 1)
        done = set()
        off = WALL_DIST + 3.2
        for side in (-1, 1):
            prev = None
            for i in range(0, tr.n, 2):
                p = tr.pos[i]
                r = tr.right[i]
                x, z = p[0] + r[0] * side * off, p[2] + r[2] * side * off
                key = (int(x // 2), int(z // 2))
                ok = key not in done and self.road_dist(x, z) > 2.5 and not self.near_track(x, z, off - 0.8) and not self.in_water(x, z, 1.0) \
                    and not self.in_building(x, z, 0.8) and self.rail_dist(x, z) > 5
                if ok:
                    ok = False
                    for b in self.bld_grid.near(x, z, 45):
                        bx, bz = b["c"]
                        if math.dist((bx, bz), (x, z)) < 50 and ((bx - x) * r[0] + (bz - z) * r[2]) * side > 2:
                            ok = True
                            break
                if ok:
                    done.add(key)
                    if prev is not None:
                        ax, az = prev
                        if math.dist((ax, az), (x, z)) < 6:
                            u = math.dist((ax, az), (x, z)) / 8.0
                            mm.wall(ax, az, x, z, 0.0, 2.1, 0, u, 0, 1)
                            mm.wall(x, z, ax, az, 0.0, 2.1, 0, u, 0, 1)
                            dx, dz = x - ax, z - az
                            L = math.hypot(dx, dz) or 1
                            pm.obox((ax + x) / 2, 2.1, (az + z) / 2, 0.16, 0.12, L / 2 + 0.05, dx / L, dz / L, cap)
                    prev = (x, z)
                else:
                    prev = None

    def build_gazebos(self):
        rng = random.Random(12)
        spots = []
        for w in self.waters:
            if w["name"] == "BINA pond":
                x0, z0, x1, z1 = w["box"]
                spots.append(((x0 + x1) / 2, (z0 + z1) / 2, 50))
        spots.append((*P(225, 171), 50))
        spots.append((*P(-60, 80), 60))
        for cx, cz, r in spots:
            for k in range(2):
                s = self.find_spot(cx, cz, 10, r, rng, track=WALL_DIST + 5, road=2, bld=3, water=2, rail=6)
                if s:
                    self.gazebo(*s)

    def gazebo(self, x, z):
        pm = self.m("plain")
        r = 2.6
        for k in range(6):
            a = 2 * math.pi * k / 6
            pm.cylinder(x + math.cos(a) * r * 0.85, 0.0, z + math.sin(a) * r * 0.85, 0.09, 2.5, 8, (0.45, 0.20, 0.12, 1))
        pm.cylinder(x, 0.0, z, r, 0.25, 12, (0.62, 0.30, 0.22, 1))
        red = (0.85, 0.15, 0.15, 1)
        for k in range(8):
            a0 = 2 * math.pi * k / 8
            a1 = 2 * math.pi * (k + 1) / 8
            p0 = (x + math.cos(a0) * (r + 0.6), 2.5, z + math.sin(a0) * (r + 0.6))
            p1 = (x + math.cos(a1) * (r + 0.6), 2.5, z + math.sin(a1) * (r + 0.6))
            top = (x, 3.9, z)
            pm.tri(top, p1, p0, (math.cos((a0 + a1) / 2) * 0.6, 1, math.sin((a0 + a1) / 2) * 0.6), col=red)
            pm.tri(top, p0, p1, (0, -1, 0), col=(0.5, 0.1, 0.1, 1))
        pm.cylinder(x, 3.9, z, 0.08, 0.5, 6, (0.9, 0.8, 0.3, 1))
        rng = random.Random(int(x * 7 + z))
        for k in range(rng.randint(0, 3)):
            a = rng.uniform(0, 6.28)
            self.people.append(dict(x=x + math.cos(a) * 1.4, y=0.28, z=z + math.sin(a) * 1.4, h=rng.uniform(0, 6.28), look=models.random_look(rng)))

    def build_cows(self):
        rng = random.Random(44)
        pm = self.m("plain")
        for cx, cz, n in ((*P(-60, -260), 6), (*P(330, -120), 4), (*P(-420, -300), 5)):
            for k in range(n):
                s = self.find_spot(cx, cz, 0, 45, rng, track=WALL_DIST + 4, road=2, bld=2, water=1, rail=6)
                if s:
                    self.cow(pm, s[0], s[1], rng.uniform(0, 6.28), rng.choice([(0.9, 0.9, 0.88, 1), (0.45, 0.30, 0.18, 1), (0.25, 0.2, 0.18, 1)]))

    def add_tree(self, x, z, kind, s, wash=False):
        self.trees.append((x, z, kind, s))
        if wash:
            self.whitewash.append((x, z))

    def build_trees(self):
        rng = random.Random(1961)
        tr = self.track
        for side in (-1, 1):
            i = rng.randint(0, 5)
            while i < tr.n:
                p = tr.pos[i]
                r = tr.right[i]
                lat = WALL_DIST + rng.uniform(1.1, 1.9)
                x, z = p[0] + r[0] * side * lat, p[2] + r[2] * side * lat
                if self.free(x, z, track=WALL_DIST + 0.9, road=0.8, bld=1.5, water=0.5, rail=4.5):
                    kind = rng.choice(["rain", "rain", "rain", "flame", "palm"])
                    self.add_tree(x, z, kind, rng.uniform(0.85, 1.15), kind != "palm")
                i += int(rng.uniform(5.5, 8.0))
        for pts, half, kind in self.roads:
            if kind in ("footway", "path"):
                continue
            for a, b in zip(pts, pts[1:]):
                L = math.dist(a, b)
                if L < 1:
                    continue
                fx, fz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                s = rng.uniform(0, 8)
                while s < L:
                    for sd in (-1, 1):
                        x = a[0] + fx * s - fz * sd * (half + 2.6)
                        z = a[1] + fz * s + fx * sd * (half + 2.6)
                        if rng.random() < 0.8 and self.free(x, z, track=WALL_DIST + 0.9, road=1.6, bld=1.5, water=0.5, rail=4.5):
                            kind2 = rng.choice(["rain", "rain", "flame", "palm"])
                            self.add_tree(x, z, kind2, rng.uniform(0.8, 1.15), kind2 != "palm")
                    s += rng.uniform(12, 17)
        for e0, n0, e1, n1, sp in ((-260, -820, 140, -330, 9.0), (-240, -320, -30, -230, 9.0), (260, -820, 420, -520, 10.0)):
            n = n0
            while n < n1:
                e = e0
                while e < e1:
                    x, z = P(e + rng.uniform(-2, 2), n + rng.uniform(-2, 2))
                    if self.free(x, z, track=WALL_DIST + 1.5, road=1.5, bld=2, water=1, rail=5):
                        self.add_tree(x, z, "palm", rng.uniform(0.9, 1.25))
                    e += sp
                n += sp
        for kind, pts in self.areas:
            if kind != "orchard":
                continue
            xs = [p[0] for p in pts]
            zs = [p[1] for p in pts]
            for k in range(220):
                x, z = rng.uniform(min(xs), max(xs)), rng.uniform(min(zs), max(zs))
                if point_in_poly(x, z, pts) and self.free(x, z, track=WALL_DIST + 1.2, road=1.2, bld=1.5, water=0.5, rail=4.5):
                    self.add_tree(x, z, rng.choice(["rain", "banana", "flame", "palm"]), rng.uniform(0.5, 0.8))
        for k in range(1400):
            e, n = rng.uniform(-760, -330), rng.uniform(-860, 300)
            x, z = P(e, n)
            if self.free(x, z, track=WALL_DIST + 1.5, road=1.5, bld=2, water=1, rail=5):
                self.add_tree(x, z, "rain", rng.uniform(0.5, 0.7))
        for pts in self.rails:
            for a, b in zip(pts, pts[1:]):
                L = math.dist(a, b)
                if L < 1:
                    continue
                fx, fz = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                s = 0.0
                while s < L:
                    for sd in (-1, 1):
                        if rng.random() < 0.75:
                            off = rng.uniform(6, 26)
                            x = a[0] + fx * s - fz * sd * off
                            z = a[1] + fz * s + fx * sd * off
                            if self.free(x, z, track=WALL_DIST + 1.2, road=1.5, bld=1.5, water=0.5, rail=5):
                                self.add_tree(x, z, rng.choice(["rain", "rain", "flame", "banana", "shrub"]), rng.uniform(0.7, 1.15))
                    s += rng.uniform(5, 9)
        for k in range(1500):
            e, n = rng.uniform(-340, 520), rng.uniform(-600, 330)
            x, z = P(e, n)
            if self.free(x, z, track=WALL_DIST + 1.5, road=1.5, bld=2, water=1, rail=5):
                self.add_tree(x, z, rng.choice(["rain", "rain", "flame", "palm", "palm", "banana", "shrub"]), rng.uniform(0.7, 1.2))
        for k in range(900):
            e, n = rng.uniform(-1300, 1300), rng.uniform(-1400, 1400)
            if -760 < e < 520 and -870 < n < 330:
                continue
            x, z = P(e, n)
            if self.free(x, z, track=WALL_DIST + 2, road=2, bld=2, water=1, rail=5):
                self.add_tree(x, z, rng.choice(["rain", "palm", "banana", "flame"]), rng.uniform(0.8, 1.3))
        tm = self.m("trees")
        sm = self.m("shadow")
        pm = self.m("plain")
        for x, z, kind, s in self.trees:
            w, h = TREE_SIZE[kind]
            w *= s
            h *= s
            u0, u1, v0, v1 = TREE_UV[kind]
            ang0 = (x * 0.37 + z * 0.11) % math.pi
            for ang in (ang0, ang0 + math.pi / 2):
                dx, dz = math.cos(ang) * w / 2, math.sin(ang) * w / 2
                tm.quad((x - dx, 0.0, z - dz), (x + dx, 0.0, z + dz), (x + dx, h, z + dz), (x - dx, h, z - dz), (0, 1, 0),
                        ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
            if kind in ("rain", "flame", "palm"):
                rr = w * (0.36 if kind != "palm" else 0.22)
                for k2 in range(10):
                    a0 = 2 * math.pi * k2 / 10
                    a1 = 2 * math.pi * (k2 + 1) / 10
                    sm.tri((x, 0.05, z), (x + math.cos(a1) * rr, 0.05, z + math.sin(a1) * rr), (x + math.cos(a0) * rr, 0.05, z + math.sin(a0) * rr), (0, 1, 0))
        for x, z in self.whitewash:
            pm.cylinder(x, 0.0, z, 0.32, 1.25, 8, (0.93, 0.93, 0.90, 1), top=False)
        self.tree_count = len(self.trees)

    def build_lamps(self):
        tr = self.track
        pole = (0.40, 0.41, 0.43, 1)
        pm = self.m("plain")
        k = 0
        for i in range(0, tr.n, 17):
            side = 1 if k % 2 == 0 else -1
            k += 1
            p = tr.pos[i]
            r = tr.right[i]
            off = WALL_DIST + 0.7
            x, z = p[0] + r[0] * side * off, p[2] + r[2] * side * off
            if not self.free(x, z, track=WALL_DIST + 0.5, road=0.3, bld=0.6, water=0.3, rail=3):
                continue
            if any((lx - x) ** 2 + (lz - z) ** 2 < 100 for lx, ly, lz in self.lamps):
                continue
            ex, ez = x - r[0] * side * 2.4, z - r[2] * side * 2.4
            pm.cylinder(x, 0.0, z, 0.09, 7.8, 8, pole, r_top=0.07)
            beam(pm, (x, 7.7, z), (ex, 7.75, ez), 0.1, pole)
            pm.box(ex - 0.25, 7.55, ez - 0.25, ex + 0.25, 7.72, ez + 0.25, (0.25, 0.25, 0.27, 1))
            self.lamps.append((ex, 7.5, ez))

    def build_people(self):
        rng = random.Random(8)
        for e, n, cnt in ((-110, 25, 6), (244, 130, 10), (284, 135, 8), (232, 60, 5), (180, 120, 6)):
            cx, cz = P(e, n)
            for k in range(cnt):
                s = self.find_spot(cx, cz, 0, 22, rng, tries=20, track=WALL_DIST + 1.2, road=0.2, bld=0.6, water=0.5, rail=3)
                if s:
                    self.people.append(dict(x=s[0], y=0.03, z=s[1], h=rng.uniform(0, 6.28), look=models.random_look(rng)))
        tr = self.track
        for k in range(int(tr.length / 45)):
            side = rng.choice((-1, 1))
            self.walk_track.append(dict(s=rng.uniform(0, tr.length), lat=side * (WALL_DIST + rng.uniform(1.0, 2.2)), dir=rng.choice((-1, 1)),
                                        speed=rng.uniform(1.0, 1.5), phase=rng.uniform(0, 6), look=models.random_look(rng)))

    def build_parked(self):
        rng = random.Random(21)
        cx, cz = P(254, 5)
        for k in range(7):
            s = self.find_spot(cx, cz, 12, 45, rng, track=WALL_DIST + 2.5, road=0.0, bld=2.2, water=1.5, rail=5)
            if s:
                col = rng.choice([(0.10, 0.48, 0.20), (0.10, 0.48, 0.20), (0.12, 0.30, 0.60)])
                self.parked.append((models.CNGModel(col), s[0], s[1], rng.uniform(0, 6.28)))
        for k in range(6):
            s = self.find_spot(cx, cz, 10, 50, rng, track=WALL_DIST + 2.0, road=-0.5, bld=1.5, water=1.0, rail=4)
            if s:
                self.parked.append((models.RickshawModel(k), s[0], s[1], rng.uniform(0, 6.28)))
        ax, az = P(250, 90)
        s = self.find_spot(ax, az, 0, 60, rng, track=WALL_DIST + 5, road=0.5, bld=4, water=2, rail=8)
        if s:
            self.parked.append((models.BusModel("bus_bau"), s[0], s[1], rng.uniform(0, 6.28)))

    def compile(self):
        if self.lists:
            return
        for mat, mesh in self.meshes.items():
            self.lists[mat] = mesh.compile(mat not in ("trees", "shadow", "pond"))

    def update(self, dt):
        self.t += dt
        tr = self.track
        for w in self.walk_track:
            w["s"] = (w["s"] + w["dir"] * w["speed"] * dt) % tr.length
            w["phase"] += dt * w["speed"] * 4.2
        t = self.train
        if t:
            if t["wait"] > 0:
                t["wait"] -= dt
            else:
                t["s"] += t["dir"] * t["speed"] * dt
                span = t["cars"] * 21 + 40
                if (t["dir"] > 0 and t["s"] > t["L"] + span) or (t["dir"] < 0 and t["s"] < -span):
                    t["dir"] *= -1
                    t["wait"] = 35.0

    def draw(self, cam, dt):
        env = self.env
        self.compile()
        env.draw_sky(cam, (0.0, 0.0))
        env.setup_light()
        glEnable(GL_LIGHTING)
        glColor4f(1, 1, 1, 1)
        for mat, tex in SOLID[:1]:
            self.call(mat, tex)
        glEnable(GL_POLYGON_OFFSET_FILL)
        for mat, tex, y, (f, u) in FLAT:
            glPolygonOffset(f, u)
            self.call(mat, tex)
        self.draw_ponds()
        self.draw_decals()
        glDisable(GL_POLYGON_OFFSET_FILL)
        glColor4f(1, 1, 1, 1)
        for mat, tex in SOLID[1:]:
            self.call(mat, tex)
        glDisable(GL_TEXTURE_2D)
        self.draw_boards()
        self.draw_parked()
        self.draw_train()
        self.track.draw()

    def call(self, mat, tex):
        lid = self.lists.get(mat)
        if not lid:
            return
        if tex:
            gfx.bind(tex)
        else:
            glDisable(GL_TEXTURE_2D)
        glCallList(lid)

    def draw_ponds(self):
        lid = self.lists.get("pond")
        if not lid:
            return
        glPolygonOffset(-0.45, -1.5)
        gfx.bind("water_lake.jpg")
        sky = self.env.hor
        k = self.env.light_level
        glColor4f(min(1, (0.55 + sky[0] * 0.3) * k + 0.05), min(1, (0.62 + sky[1] * 0.3) * k + 0.05), min(1, (0.62 + sky[2] * 0.3) * k + 0.06), 1)
        glMatrixMode(GL_TEXTURE)
        glPushMatrix()
        glTranslatef(self.t * 0.004, self.t * 0.01, 0)
        glCallList(lid)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glColor4f(1, 1, 1, 1)
        glDisable(GL_TEXTURE_2D)

    def draw_water(self):
        pass

    def draw_decals(self):
        if not self.decals:
            return
        glPolygonOffset(-0.8, -2.0)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        k = self.env.light_level
        glColor4f(k, k, k, 1)
        for x, z, r, tex in self.decals:
            gfx.bind(tex, repeat=False)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex3f(x - r, 0.0, z + r)
            glTexCoord2f(1, 0); glVertex3f(x + r, 0.0, z + r)
            glTexCoord2f(1, 1); glVertex3f(x + r, 0.0, z - r)
            glTexCoord2f(0, 1); glVertex3f(x - r, 0.0, z - r)
            glEnd()
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glColor4f(1, 1, 1, 1)

    def train_lists(self):
        if "train_side" in self.lists:
            return
        side = Mesh()
        body = Mesh()
        loco_side = Mesh()
        hw, hl = 1.5, 10.0
        y0, y1 = 0.9, 4.1
        for sgn in (-1, 1):
            x = hw * sgn
            if sgn > 0:
                side.wall(x, hl, x, -hl, y0, y1, 0, 1, 0, 1)
                loco_side.wall(x, hl, x, -hl, y0, y1, 0, 1, 0, 1)
            else:
                side.wall(x, -hl, x, hl, y0, y1, 1, 0, 0, 1)
                loco_side.wall(x, -hl, x, hl, y0, y1, 1, 0, 0, 1)
        grey = (0.55, 0.56, 0.56, 1)
        green = (0.10, 0.34, 0.28, 1)
        quad_out(body, [(-hw, y1, -hl), (hw, y1, -hl), (hw, y1 + 0.4, -hl + 0.3), (-hw, y1 + 0.4, -hl + 0.3)], (0, 1, 0), grey)
        body.box(-hw + 0.1, y1, -hl + 0.3, hw - 0.1, y1 + 0.45, hl - 0.3, grey)
        body.wall(-hw, hl, hw, hl, y0, y1, 0, 1, 0, 1, green)
        body.wall(hw, -hl, -hw, -hl, y0, y1, 0, 1, 0, 1, green)
        body.box(-hw + 0.3, 0.35, -hl + 1.0, hw - 0.3, y0, hl - 1.0, (0.12, 0.12, 0.12, 1))
        for zz in (-hl + 2.5, hl - 2.5):
            for xx in (-hw + 0.25, hw - 0.25):
                body.box(xx - 0.08, 0.0, zz - 1.2, xx + 0.08, 0.8, zz + 1.2, (0.18, 0.18, 0.18, 1))
        front = Mesh()
        front.wall(-hw, hl, hw, hl, y0, y1, 0, 1, 0, 1)
        self.lists["train_side"] = side.compile()
        self.lists["train_body"] = body.compile()
        self.lists["loco_side"] = loco_side.compile()
        self.lists["loco_front"] = front.compile()

    def train_poses(self):
        t = self.train
        if not t or t["wait"] > 0:
            return []
        out = []
        for k in range(t["cars"] + 1):
            s = t["s"] - t["dir"] * k * 21.0
            if s < 0 or s > t["L"]:
                continue
            x, z, h = self.rail_at(s)
            if t["dir"] < 0:
                h += math.pi
            out.append((k, x, z, h))
        return out

    def draw_train(self):
        poses = self.train_poses()
        if not poses:
            return
        self.train_lists()
        glEnable(GL_LIGHTING)
        for k, x, z, h in poses:
            glPushMatrix()
            glTranslatef(x, 0.12, z)
            glRotatef(math.degrees(h), 0, 1, 0)
            glDisable(GL_TEXTURE_2D)
            glCallList(self.lists["train_body"])
            if k == 0:
                gfx.bind("loco_side.jpg")
                glCallList(self.lists["loco_side"])
                gfx.bind("loco_front.jpg")
                glCallList(self.lists["loco_front"])
            else:
                gfx.bind("train_bd.jpg")
                glCallList(self.lists["train_side"])
            glDisable(GL_TEXTURE_2D)
            glPopMatrix()

    def draw_people(self, eye, fwd):
        super().draw_people(eye, fwd)
        ex, ez = eye[0], eye[2]
        tr = self.track
        for w in self.walk_track:
            i = int(w["s"] / tr.step) % tr.n
            p = tr.pos[i]
            r = tr.right[i]
            x, z = p[0] + r[0] * w["lat"], p[2] + r[2] * w["lat"]
            dx, dz = x - ex, z - ez
            if dx * dx + dz * dz > 130 * 130 or (dx * fwd[0] + dz * fwd[1] < -5 and dx * dx + dz * dz > 100):
                continue
            f = tr.fwd[i]
            hd = math.atan2(f[0] * w["dir"], f[2] * w["dir"])
            glPushMatrix()
            glTranslatef(x, 0.03, z)
            glRotatef(math.degrees(hd), 0, 1, 0)
            models.draw_person(w["look"], w["phase"], w["speed"])
            glPopMatrix()

    def draw_night(self, eye):
        super().draw_night(eye)
        n = self.env.night
        poses = self.train_poses()
        if n < 0.05 or not poses:
            return
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glBlendFunc(GL_CONSTANT_COLOR, GL_ONE)
        glBlendColor(n, n, n, 1)
        gfx.bind("train_bd_lit.jpg")
        for k, x, z, h in poses:
            if k == 0:
                continue
            glPushMatrix()
            glTranslatef(x, 0.12, z)
            glRotatef(math.degrees(h), 0, 1, 0)
            glCallList(self.lists["train_side"])
            glPopMatrix()
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_TEXTURE_2D)
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)
