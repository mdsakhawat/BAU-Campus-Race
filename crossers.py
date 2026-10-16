import math
import random

from OpenGL.GL import *

import models
from config import *

CAR_HALF_W = 0.95
CAR_HALF_L = 2.25
PED_R = 0.32


class Crossers:
    def __init__(self, track, seed=7):
        self.track = track
        rng = random.Random(seed)
        self.rng = rng
        self.spots = []
        self.peds = []
        gap = 230.0
        s = 140.0
        while s < track.length - 90:
            i = int(s / track.step) % track.n
            if abs(track.curv[i]) < 1 / 120.0:
                self.spots.append(i)
                for k in range(rng.randint(1, 3)):
                    side = rng.choice((-1, 1))
                    self.peds.append(dict(i=i, side=side, lat=side * (WALL_DIST + 0.9 + rng.uniform(0, 0.8)), along=rng.uniform(-1.6, 1.6),
                                          state="wait", t=rng.uniform(1, 12), speed=rng.uniform(1.1, 1.5), phase=rng.uniform(0, 6),
                                          look=models.random_look(rng), fall=0.0, spin=0.0, vx=0.0, vz=0.0, ox=0.0, oz=0.0, heading=0.0))
            s += gap * rng.uniform(0.8, 1.25)
        self.horn_t = 0.0
        self.hits = 0

    def pos(self, p):
        tr = self.track
        i = p["i"]
        q = tr.pos[i]
        r = tr.right[i]
        f = tr.fwd[i]
        x = q[0] + r[0] * p["lat"] + f[0] * p["along"] + p["ox"]
        z = q[2] + r[2] * p["lat"] + f[2] * p["along"] + p["oz"]
        return x, z

    def car_near(self, i, cars, dist=70.0):
        tr = self.track
        s_ped = i * tr.step
        for c in cars:
            ds = s_ped - (c.idx * tr.step + c.along)
            if ds < -tr.length / 2:
                ds += tr.length
            elif ds > tr.length / 2:
                ds -= tr.length
            if -8 < ds < max(dist, c.speed * 4.0):
                return True
        return False

    def horn(self):
        self.horn_t = 2.5

    def update(self, dt, cars):
        self.horn_t = max(0.0, self.horn_t - dt)
        tr = self.track
        for p in self.peds:
            st = p["state"]
            if st == "wait":
                p["t"] -= dt
                if p["t"] <= 0:
                    if self.horn_t > 0 or self.car_near(p["i"], cars):
                        p["t"] = self.rng.uniform(0.8, 2.0)
                    else:
                        p["state"] = "cross"
                        p["target"] = -p["side"] * (WALL_DIST + 0.9 + self.rng.uniform(0, 0.8))
                        p["run"] = False
            elif st == "cross":
                danger = self.car_near(p["i"], cars, 25.0) or self.horn_t > 0
                if danger and not p["run"]:
                    p["run"] = True
                    if abs(p["lat"]) < ROAD_HALF * 0.5:
                        p["target"] = math.copysign(WALL_DIST + 1.0, p["lat"])
                v = (3.6 if p["run"] else p["speed"])
                d = p["target"] - p["lat"]
                step = math.copysign(min(abs(d), v * dt), d)
                p["lat"] += step
                p["phase"] += dt * v * 4.2
                p["heading_dir"] = 1 if d > 0 else -1
                if abs(d) < 0.05:
                    p["state"] = "wait"
                    p["side"] = 1 if p["lat"] > 0 else -1
                    p["t"] = self.rng.uniform(8, 25)
            elif st == "fall":
                p["fall"] += dt
                k = max(0.0, 1 - p["fall"] / 0.9)
                p["ox"] += p["vx"] * dt * k
                p["oz"] += p["vz"] * dt * k
                if p["fall"] > 3.6:
                    p["state"] = "getup"
                    p["fall"] = 0.0
            elif st == "getup":
                p["fall"] += dt
                if p["fall"] > 0.8:
                    x, z = self.pos(p)
                    i, lat, along = tr.nearest(x, z, p["i"], 10)
                    p["i"], p["lat"], p["along"], p["ox"], p["oz"] = i, lat, along, 0.0, 0.0
                    p["state"] = "cross"
                    p["run"] = True
                    p["target"] = math.copysign(WALL_DIST + 1.0, lat if abs(lat) > 0.1 else 1.0)

    def collide(self, cars):
        hits = []
        for p in self.peds:
            if p["state"] in ("fall", "getup"):
                continue
            if abs(p["lat"]) > WALL_DIST + 0.2:
                continue
            x, z = self.pos(p)
            for c in cars:
                dx, dz = x - c.x, z - c.z
                if dx * dx + dz * dz > 16:
                    continue
                fx, fz = c.forward()
                a = dx * fx + dz * fz
                b = dx * -fz + dz * fx
                if abs(a) < CAR_HALF_L + PED_R and abs(b) < CAR_HALF_W + PED_R:
                    sp = c.speed
                    if sp < 1.5:
                        pen = CAR_HALF_L + PED_R - abs(a)
                        c.x -= fx * pen * math.copysign(1, a)
                        c.z -= fz * pen * math.copysign(1, a)
                        c.vx *= 0.3
                        c.vz *= 0.3
                        continue
                    p["state"] = "fall"
                    p["fall"] = 0.0
                    k = min(1.0, sp / 20.0)
                    p["vx"] = c.vx * 0.55 + (-fz if b > 0 else fz) * 2.0 * k
                    p["vz"] = c.vz * 0.55 + (fx if b > 0 else -fx) * 2.0 * k
                    p["heading"] = math.atan2(p["vx"], p["vz"])
                    slow = max(0.35, 1 - 0.035 * sp)
                    c.vx *= slow
                    c.vz *= slow
                    hits.append((c, sp))
                    break
        return hits

    def blocking(self, car, look=38.0):
        tr = self.track
        s_car = car.idx * tr.step + car.along
        for p in self.peds:
            if p["state"] == "wait" or abs(p["lat"]) > ROAD_HALF + 1.5:
                continue
            ds = p["i"] * tr.step - s_car
            if ds < -tr.length / 2:
                ds += tr.length
            if 0 < ds < look + car.speed * 1.2 and abs(p["lat"] - car.lateral) < 3.2:
                return True
        return False

    def zebra_quads(self):
        out = []
        tr = self.track
        for i in self.spots:
            q = tr.pos[i]
            r = tr.right[i]
            f = tr.fwd[i]
            lat = -ROAD_HALF + 0.3
            while lat < ROAD_HALF - 0.3:
                l0, l1 = lat, lat + 0.5
                pts = []
                for la, al in ((l0, -1.6), (l1, -1.6), (l1, 1.6), (l0, 1.6)):
                    pts.append((q[0] + r[0] * la + f[0] * al, q[1] + 0.025, q[2] + r[2] * la + f[2] * al))
                out.append(pts)
                lat += 1.0
        return out

    def draw_zebra(self):
        if not hasattr(self, "_zebra"):
            self._zebra = self.zebra_quads()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-2.0, -6.0)
        glNormal3f(0, 1, 0)
        glColor4f(0.88, 0.88, 0.86, 1)
        glBegin(GL_QUADS)
        for pts in self._zebra:
            for p in (pts[0], pts[3], pts[2], pts[1]):
                glVertex3f(*p)
        glEnd()
        glDisable(GL_POLYGON_OFFSET_FILL)
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)
        glColor4f(1, 1, 1, 1)

    def draw(self, eye):
        tr = self.track
        glEnable(GL_LIGHTING)
        ex, ez = eye[0], eye[2]
        for p in self.peds:
            x, z = self.pos(p)
            if (x - ex) ** 2 + (z - ez) ** 2 > 160 ** 2:
                continue
            i = p["i"]
            r = tr.right[i]
            st = p["state"]
            lift = 0.32 if abs(abs(p["lat"]) - WALL_DIST) < 0.35 else 0.0
            glPushMatrix()
            glTranslatef(x, tr.pos[i][1] + 0.03 + lift, z)
            if st == "cross":
                hd = math.atan2(r[0] * p.get("heading_dir", 1), r[2] * p.get("heading_dir", 1))
                glRotatef(math.degrees(hd), 0, 1, 0)
                models.draw_person(p["look"], p["phase"], 3.0 if p["run"] else p["speed"])
            elif st == "wait":
                hd = math.atan2(-r[0] * p["side"], -r[2] * p["side"])
                glRotatef(math.degrees(hd), 0, 1, 0)
                models.draw_person(p["look"], p["phase"] * 0.1, 0.0, "idle")
            else:
                glRotatef(math.degrees(p["heading"]), 0, 1, 0)
                if st == "fall":
                    a = min(90.0, p["fall"] / 0.45 * 90.0)
                else:
                    a = 90.0 * max(0.0, 1 - p["fall"] / 0.8)
                glTranslatef(0, 0.12 * math.sin(math.radians(a)), 0)
                glRotatef(a, 1, 0, 0)
                models.draw_person(p["look"], 0.0, 0.0, "idle")
            glPopMatrix()
