import math
import random

import numpy as np
from OpenGL.GL import *

import gfx
from ai import AIDriver
from camera import Camera
from car import Car, Controls
from carmodel import CarModel
from config import *
from effects import Effects
from track import Track
import campus
import osmcampus
from campus import make_env
from env import billboards
from crossers import Crossers

GRID_SLOT = {"easy": 2, "medium": 4, "hard": 5}


class Race:
    def __init__(self, game, track_i, car_i, color_i, diff_key, laps, mode="race", time_i=0, weather_i=0):
        self.game = game
        self.mode = mode
        if mode == "tour":
            laps = 1
        self.sound = game.sound
        self.info = TRACKS[track_i]
        self.track_i = track_i
        self.diff_key = diff_key
        self.diff = DIFFICULTY[diff_key]
        self.laps = laps
        self.track = Track(self.info)
        self.env = make_env(time_i, weather_i)
        self.world = (osmcampus.World if self.info.get("map") == "osm" else campus.World)(self.track, self.env)
        self.world.people = [p for p in self.world.people if not self.world.near_track(p["x"], p["z"], WALL_DIST + 0.8)]
        self.crossers = Crossers(self.track, track_i * 31 + 7)
        self.minimap = self.track.minimap_points(220)
        self.fx = Effects()
        self.camera = Camera()
        self.cars = []
        self.drivers = {}
        self.models = []
        rng = random.Random()
        palette = [i for i in range(len(COLORS)) if i != color_i]
        rng.shuffle(palette)
        names = AI_NAMES[:]
        rng.shuffle(names)
        player_slot = GRID_SLOT[diff_key] if mode == "race" else 0
        ai_specs = []
        for k in range(NUM_CARS - 1):
            ai_specs.append(CARS[rng.randrange(3)])
        slots = list(range(NUM_CARS)) if mode == "race" else [0]
        k_ai = 0
        for slot in slots:
            if slot == player_slot:
                spec = CARS[car_i]
                model = CarModel(spec["style"], COLORS[color_i][1])
                car = Car(spec, COLORS[color_i][1], "You", True, model)
                car.assist = self.diff["assist"]
                self.player = car
            else:
                spec = ai_specs[k_ai]
                col = COLORS[palette[k_ai % len(palette)]][1]
                model = CarModel(spec["style"], col)
                car = Car(spec, col, names[k_ai], False, model)
                car.power_scale = self.diff["ai_power"] * rng.uniform(0.97, 1.03)
                car.grip_scale = self.diff["ai_grip"]
                k_ai += 1
            self.models.append(model)
            row, col_i = slot // 2, slot % 2
            dist = 10 + row * 9 + col_i * 4.5
            lat = -3.3 if col_i == 0 else 3.3
            idx = -int(round(dist / self.track.step))
            car.place(self.track, idx, lat, -dist)
            car.slot = slot
            self.cars.append(car)
            if not car.player:
                skill = rng.uniform(0.95, 1.02) * (1.0 if slot < player_slot else 0.99)
                self.drivers[id(car)] = AIDriver(car, self.track, skill, self.diff)
        self.state = "intro"
        self.state_t = 0.0
        self.time = 0.0
        self.lights = 0
        self.finish_order = []
        self.results = None
        self.message = ""
        self.message_t = 0.0
        self.final_lap_shown = False
        self.engine_rpm = IDLE_RPM
        self.checkpoints = []
        for key, (mx, mz) in self.info["checkpoints"]:
            x, z = track_xz(self.info, mx, mz)
            i, lat, along = self.track.nearest(x, z)
            self.checkpoints.append(dict(key=key, s=i * self.track.step, idx=i, done=False, split=None))
        self.checkpoints.sort(key=lambda c: c["s"])
        self.card = None
        self.card_t = 0.0
        self.cp_next = 0
        self.showcase = None

    def release(self):
        self.track.release()
        self.world.release()
        for m in self.models:
            m.release()

    def show(self, text, t=2.0):
        self.message = text
        self.message_t = t

    def player_position(self):
        p = self.player
        order = self.standings()
        return order.index(p) + 1

    def standings(self):
        def key(c):
            if c.finished:
                return (0, c.finish_time)
            return (1, -c.total)
        return sorted(self.cars, key=key)

    def update(self, dt, ctl):
        if self.showcase:
            self.showcase["t"] += dt
            self.card_t = max(0.0, self.card_t - dt * 0.2)
            self.world.update(dt)
            self.env.update(dt)
            self.crossers.update(dt, [])
            if self.showcase["t"] >= SHOWCASE_SECONDS:
                self.end_showcase()
            return
        self.state_t += dt
        self.message_t = max(0.0, self.message_t - dt)
        racing = self.state in ("racing", "finished")
        if self.state == "intro":
            if self.state_t > 2.6:
                self.state = "countdown"
                self.state_t = 0.0
        elif self.state == "countdown":
            n = int(self.state_t / 0.8)
            if n > self.lights and n <= 5:
                self.lights = n
                self.sound.play("beep_low" if n < 5 else "beep_low")
            if self.state_t >= 4.4:
                self.state = "racing"
                self.state_t = 0.0
                self.lights = 0
                self.sound.play("beep_high")
                self.show("GO!", 1.2)
        if racing:
            self.time += dt
        player_total = self.player.total
        leader = max(c.total for c in self.cars)
        for car in self.cars:
            if car.player:
                c = ctl if not car.finished else Controls()
            else:
                c = self.drivers[id(car)].control(dt, self.cars, leader, player_total) if racing else Controls()
                if not racing:
                    c.throttle = 0.3 if self.state == "countdown" and self.state_t > 3.2 and random.random() < 0.5 else 0.0
                elif self.crossers.blocking(car):
                    c.throttle = 0.0
                    c.brake = 1.0
                    c.nitro = False
            if self.state == "countdown" and car.player:
                car.update(dt, ctl, self.track, self.time, False)
                continue
            car.update(dt, c, self.track, self.time, racing and not car.finished)
            if racing and not car.finished and car.total >= self.laps * self.track.length:
                car.finished = True
                car.finish_time = self.time + getattr(car, "penalty", 0.0)
                self.finish_order.append(car)
                if car.player:
                    self.on_player_finish()
        self.collide_cars()
        self.crossers.update(dt, self.cars)
        for car, sp in self.crossers.collide(self.cars):
            if car.player:
                if racing and not car.finished:
                    car.penalty = getattr(car, "penalty", 0.0) + 3.0
                    self.show("PEDESTRIAN HIT  +3 s", 2.2)
                else:
                    self.show("WATCH OUT!", 1.6)
                self.sound.play("bump", 0.5)
                self.camera.shake = min(1.0, 0.25 + sp / 40.0)
        self.world.update(dt)
        self.env.update(dt)
        for ev in self.env.pop_events():
            self.sound.play("crash", 0.5)
        if self.card_t > 0:
            self.card_t -= dt
        self.check_points()
        self.emit_effects(dt)
        self.fx.update(dt)
        p = self.player
        if p.impact > 3:
            self.camera.shake = min(1.0, p.impact / 15)
            self.sound.play("crash" if p.impact > 9 else "bump", 0.25)
            self.fx.sparks(p.x, p.y, p.z, int(min(20, p.impact * 1.5)))
        for car in self.cars:
            if car.impact > 3 and not car.player:
                self.fx.sparks(car.x, car.y, car.z, 6)
            car.impact = 0.0
        if p.gear_changed and p.throttle > 0.3:
            self.sound.play("shift", 0.15)
        if racing and not p.finished:
            lap = p.lap(self.track, self.laps)
            if lap == self.laps and self.laps > 1 and not self.final_lap_shown and p.total >= 0:
                self.final_lap_shown = True
                self.show("FINAL LAP", 2.5)
                self.sound.play("final_lap")
        self.camera.follow(p, dt, orbit=(self.state == "intro" or p.finished))
        if self.state == "finished" and self.state_t > 6 and self.results is None:
            self.build_results()

    def end_showcase(self):
        self.showcase = None
        self.card_t = min(self.card_t, 1.2)
        self.camera.first = True

    def showcase_view(self):
        sc = self.showcase
        if not sc:
            return None
        k = sc["t"] / SHOWCASE_SECONDS
        k = k * k * (3 - 2 * k)
        if SHOWCASE[sc["key"]] == "track":
            tr = self.track
            i0 = (sc["idx"] - 22) % tr.n
            i1 = (sc["idx"] + 4) % tr.n
            a, b = tr.pos[i0], tr.pos[i1]
            r = tr.right[i0]
            eye = (a[0] + r[0] * 2.0 + (b[0] - a[0]) * 0.25 * k, 6.5 - 2.0 * k, a[2] + r[2] * 2.0 + (b[2] - a[2]) * 0.25 * k)
            return eye, (b[0], 1.5, b[2]), 62.0
        (e0, n0, y0), (e1, n1, y1), (pe, pn, py) = SHOWCASE[sc["key"]]
        eye = (-(e0 + pe * k), y0 + py * k, n0 + pn * k)
        tgt = (-e1, y1, n1)
        return eye, tgt, 58.0

    def check_points(self):
        p = self.player
        if self.state not in ("racing", "finished") or p.finished:
            return
        lap_i = math.floor(p.total / self.track.length) if p.total >= 0 else -1
        if lap_i != getattr(self, "cp_lap", lap_i):
            for c in self.checkpoints:
                c["done"] = False
        self.cp_lap = lap_i
        lap_s = p.total - lap_i * self.track.length if p.total >= 0 else -1
        for k, cp in enumerate(self.checkpoints):
            if cp["done"] or p.total < 0:
                continue
            if lap_s >= cp["s"] and lap_s - cp["s"] < 60:
                cp["done"] = True
                cp["split"] = self.time
                self.cp_next = k + 1
                name, fact = PLACES[cp["key"]]
                self.card = dict(key=cp["key"], name=name, fact=fact, time=self.time, n=sum(1 for c in self.checkpoints if c["done"]))
                self.card_t = 4.5 if self.mode == "tour" else 2.5
                self.sound.play("discover" if self.mode == "tour" else "beep_low", 0.2)
                self.game.visit(cp["key"])
                if self.mode == "tour" and self.info.get("map") == "osm" and cp["key"] in SHOWCASE:
                    self.showcase = dict(key=cp["key"], t=0.0, idx=cp["idx"])
                    self.card_t = SHOWCASE_SECONDS

    def on_player_finish(self):
        self.state = "finished"
        self.state_t = 0.0
        pos = self.finish_order.index(self.player) + 1
        self.player_place = pos
        self.show("FINISHED  " + ordinal(pos) if self.mode == "race" else "TOUR COMPLETE", 4)
        self.sound.play("finish")

    def build_results(self):
        rows = []
        for car in self.cars:
            if car.finished:
                t = car.finish_time
            else:
                remaining = self.laps * self.track.length - car.total
                t = self.time + remaining / max(25.0, car.speed * 0.9)
            rows.append((t, car))
        rows.sort(key=lambda r: r[0])
        self.results = [(i + 1, car.name, t, car.best_lap, car.player, car.spec["name"]) for i, (t, car) in enumerate(rows)]
        if self.mode == "tour":
            self.results = [(1, "You", self.player.finish_time or self.time, self.player.best_lap, True, self.player.spec["name"])]

    def collide_cars(self):
        cars = self.cars
        R = Car.RADIUS
        for i in range(len(cars)):
            a = cars[i]
            for j in range(i + 1, len(cars)):
                b = cars[j]
                if abs(a.x - b.x) > 7 or abs(a.z - b.z) > 7:
                    continue
                afx, afz = a.forward()
                bfx, bfz = b.forward()
                for oa in (-1.15, 1.15):
                    for ob in (-1.15, 1.15):
                        ax, az = a.x + afx * oa, a.z + afz * oa
                        bx, bz = b.x + bfx * ob, b.z + bfz * ob
                        dx, dz = bx - ax, bz - az
                        d2 = dx * dx + dz * dz
                        if d2 < (2 * R) ** 2 and d2 > 1e-6:
                            d = math.sqrt(d2)
                            nx, nz = dx / d, dz / d
                            pen = 2 * R - d
                            a.x -= nx * pen * 0.5
                            a.z -= nz * pen * 0.5
                            b.x += nx * pen * 0.5
                            b.z += nz * pen * 0.5
                            rv = (b.vx - a.vx) * nx + (b.vz - a.vz) * nz
                            if rv < 0:
                                ma, mb = a.mass, b.mass
                                jimp = -(1.3) * rv / (1 / ma + 1 / mb)
                                a.vx -= jimp / ma * nx
                                a.vz -= jimp / ma * nz
                                b.vx += jimp / mb * nx
                                b.vz += jimp / mb * nz
                                hit = abs(rv)
                                a.impact = max(a.impact, hit * 0.6)
                                b.impact = max(b.impact, hit * 0.6)
                                a.yaw_rate += (random.random() - 0.5) * hit * 0.04
                                b.yaw_rate += (random.random() - 0.5) * hit * 0.04

    def emit_effects(self, dt):
        for car in self.cars:
            if car.model is None:
                continue
            wheels = car.wheel_world(self.track)
            speed = car.speed
            skid = car.slip > 3.2 and speed > 4 and not car.offroad
            for k, (wx, wy, wz, front) in enumerate(wheels):
                if front and not (car.brake > 0.7 and speed > 15):
                    self.fx.skid((id(car), k), wx, wy, wz, False)
                    continue
                self.fx.skid((id(car), k), wx, wy, wz, skid or (car.brake > 0.8 and speed > 18 and not car.assist))
                if skid and random.random() < dt * 30 * min(1.0, car.slip / 6):
                    self.fx.smoke(wx, wy, wz, car.vx, car.vz, min(1.0, car.slip / 7))
                if car.offroad and speed > 6 and random.random() < dt * 10:
                    self.fx.dust(wx, wy, wz, car.vx, car.vz, (0.45, 0.40, 0.30))
                if self.env.wet > 0.4 and speed > 8 and random.random() < dt * 12:
                    self.fx.smoke(wx, wy, wz, car.vx * 0.3, car.vz * 0.3, 0.22, (0.85, 0.88, 0.92))
            if car.nitro_on:
                fx, fz = car.forward()
                L = car.model.st["L"] / 2
                rx, rz = -fz, fx
                for side in (-0.25, 0.25):
                    px = car.x - fx * (L + 0.1) - rx * side
                    pz = car.z - fz * (L + 0.1) - rz * side
                    self.fx.flame(px, car.y + car.model.st["bottom"] + 0.12, pz, -fx * 6 + car.vx * 0.9, -fz * 6 + car.vz * 0.9)
            if car.wall_contact and random.random() < dt * 40:
                self.fx.sparks(car.x, car.y, car.z, 2)

    def draw_car(self, car, shadow_only=False):
        glPushMatrix()
        glTranslatef(car.x, car.y, car.z)
        glRotatef(math.degrees(car.heading), 0, 1, 0)
        glRotatef(-math.degrees(car.pitch), 1, 0, 0)
        glRotatef(math.degrees(car.roll), 0, 0, 1)
        if shadow_only:
            car.model.draw_shadow_shape()
        else:
            car.model.draw(car.spin, -car.steer, car.brake > 0.1)
        glPopMatrix()

    def draw_shadows(self, cams):
        sx, sy, sz = self.world.sun_dir
        if sy < 0.4:
            k = 0.4 / max(0.05, sy)
            sx, sz, sy = sx / k, sz / k, 0.4
        if self.env.shadow_alpha < 0.03:
            return
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        stencil = gfx.display.stencil
        if stencil:
            glClear(GL_STENCIL_BUFFER_BIT)
            glEnable(GL_STENCIL_TEST)
            glStencilFunc(GL_EQUAL, 0, 0xFF)
            glStencilOp(GL_KEEP, GL_KEEP, GL_INCR)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-3.0, -6.0)
        glDepthMask(GL_FALSE)
        glColor4f(0.0, 0.0, 0.02, self.env.shadow_alpha)
        glDisable(GL_CULL_FACE)
        for car in self.cars:
            if (car.x - cams[0]) ** 2 + (car.z - cams[2]) ** 2 > 260 ** 2:
                continue
            y0 = car.y + 0.03
            M = np.array([[sy, -sx, 0, sx * y0],
                          [0, 0, 0, sy * y0],
                          [0, -sz, sy, sz * y0],
                          [0, 0, 0, sy]], dtype=np.float64)
            glPushMatrix()
            glMultMatrixd(M.T.flatten())
            self.draw_car(car, True)
            glPopMatrix()
        glEnable(GL_CULL_FACE)
        glDepthMask(GL_TRUE)
        glDisable(GL_POLYGON_OFFSET_FILL)
        if stencil:
            glDisable(GL_STENCIL_TEST)
        glEnable(GL_LIGHTING)

    def draw_brake_lights(self):
        items = []
        for car in self.cars:
            if car.brake < 0.1 and not car.player:
                continue
            fx, fz = car.forward()
            rx, rz = -fz, fx
            st = car.model.st
            L = st["L"] / 2
            for side in (-0.62, 0.62):
                px = car.x - fx * (L + 0.05) - rx * side * st["W"]
                pz = car.z - fz * (L + 0.05) - rz * side * st["W"]
                py = car.y + st["tail"] - 0.12
                items.append((px, py, pz, 1.0 if car.brake > 0.1 else 0.25))
        if not items:
            return
        m = glGetFloatv(GL_MODELVIEW_MATRIX)
        rx, ry, rz = m[0][0], m[1][0], m[2][0]
        ux, uy, uz = m[0][1], m[1][1], m[2][1]
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, gfx.texture("glow"))
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDisable(GL_CULL_FACE)
        glBegin(GL_QUADS)
        for x, y, z, a in items:
            s = 0.55
            glColor4f(1.0, 0.12, 0.08, 0.9 * a)
            for u, v in ((0, 0), (1, 0), (1, 1), (0, 1)):
                ox, oy = (u - 0.5) * 2 * s, (v - 0.5) * 2 * s
                glTexCoord2f(u, v)
                glVertex3f(x + rx * ox + ux * oy, y + ry * ox + uy * oy, z + rz * ox + uz * oy)
        glEnd()
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_CULL_FACE)
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)

    def draw_start_lights(self):
        if self.state != "countdown":
            return
        tr = self.track
        p = tr.pos[0]
        f = tr.fwd[0]
        r = tr.right[0]
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        for k in range(5):
            off = (k - 2) * 1.6
            cx = p[0] + r[0] * off - f[0] * 0.75
            cz = p[2] + r[2] * off - f[2] * 0.75
            cy = p[1] + 7.0
            on = k < self.lights
            glColor4f(*((1.0, 0.08, 0.05, 1) if on else (0.18, 0.04, 0.04, 1)))
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(cx, cy, cz)
            for j in range(17):
                a = 2 * math.pi * j / 16
                glVertex3f(cx + r[0] * math.cos(a) * 0.45, cy + math.sin(a) * 0.45, cz + r[2] * math.cos(a) * 0.45)
            glEnd()
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)

    def draw_gates(self):
        tr = self.track
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        k = max(self.env.light_level, 0.8 * self.env.night)
        items = [(0, "banner_start.jpg")]
        if self.mode == "tour":
            items += [(cp["idx"], "banner_check.jpg") for cp in self.checkpoints if not cp["done"]]
        for idx, tex in items:
            p = tr.pos[idx]
            r = tr.right[idx]
            w = ROAD_HALF + 1.2
            for s in (-1, 1):
                bx, bz = p[0] + r[0] * w * s, p[2] + r[2] * w * s
                glColor4f(0.25 * k, 0.25 * k, 0.27 * k, 1)
                glLineWidth(6.0)
                glBegin(GL_LINES)
                glVertex3f(bx, p[1], bz)
                glVertex3f(bx, p[1] + 6.2, bz)
                glEnd()
                glLineWidth(1.0)
            gfx.bind(tex, repeat=False)
            glColor4f(k, k, k, 1)
            ax, az = p[0] - r[0] * w, p[2] - r[2] * w
            bx, bz = p[0] + r[0] * w, p[2] + r[2] * w
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex3f(ax, p[1] + 4.7, az)
            glTexCoord2f(1, 0); glVertex3f(bx, p[1] + 4.7, bz)
            glTexCoord2f(1, 1); glVertex3f(bx, p[1] + 6.2, bz)
            glTexCoord2f(0, 1); glVertex3f(ax, p[1] + 6.2, az)
            glEnd()
            glDisable(GL_TEXTURE_2D)
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)

    def draw_headlights(self):
        env = self.env
        if not (env.lamps or env.rain > 0.5):
            return
        items = []
        beams = []
        for car in self.cars:
            fx, fz = car.forward()
            rx, rz = -fz, fx
            for hx, hy, hz in car.model.head:
                px = car.x + fx * hz - rx * hx
                pz = car.z + fz * hz - rz * hx
                items.append(((px, car.y + hy, pz), 0.9, (1.0, 0.97, 0.85), 0.95))
            beams.append(car)
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        billboards(items, "glow")
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, gfx.texture("beam"))
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-2.0, -6.0)
        glFogfv(GL_FOG_COLOR, (0, 0, 0, 1))
        a = 0.5 * max(env.night, 0.45)
        glBegin(GL_QUADS)
        for car in beams:
            fx, fz = car.forward()
            rx, rz = -fz, fx
            L = car.model.st["L"] / 2
            bx, bz = car.x + fx * L, car.z + fz * L
            y = car.y + 0.05
            glColor4f(1.0, 0.95, 0.82, a if car.player else a * 0.6)
            glTexCoord2f(0.38, 0.02); glVertex3f(bx - rx * 1.2, y, bz - rz * 1.2)
            glTexCoord2f(0.62, 0.02); glVertex3f(bx + rx * 1.2, y, bz + rz * 1.2)
            glTexCoord2f(1.0, 1.0); glVertex3f(bx + fx * 30 + rx * 7, y, bz + fz * 30 + rz * 7)
            glTexCoord2f(0.0, 1.0); glVertex3f(bx + fx * 30 - rx * 7, y, bz + fz * 30 - rz * 7)
        glEnd()
        glDisable(GL_POLYGON_OFFSET_FILL)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_TEXTURE_2D)
        glDepthMask(GL_TRUE)
        env.fog_on()
        glEnable(GL_LIGHTING)

    def draw(self, dt):
        cam = self.camera
        view = self.showcase_view()
        if view:
            eye, target, fov = view
        else:
            eye, target, fov = cam.eye(), cam.target, cam.fov
        gfx.begin_3d(fov, 0.3, 2600)
        gfx.look_at(eye, target)
        self.world.draw(eye, dt)
        self.crossers.draw_zebra()
        self.fx.draw_skids()
        self.draw_shadows(eye)
        for car in self.cars:
            if (car.x - eye[0]) ** 2 + (car.z - eye[2]) ** 2 < 900 ** 2:
                if car.player and cam.name == "hood" and not (self.state == "intro" or car.finished or view):
                    continue
                self.draw_car(car)
        dx, dz = target[0] - eye[0], target[2] - eye[2]
        dl = math.hypot(dx, dz) or 1.0
        self.world.draw_late(eye, (dx / dl, dz / dl))
        self.crossers.draw(eye)
        self.draw_gates()
        self.draw_start_lights()
        self.draw_brake_lights()
        self.draw_headlights()
        self.fx.draw()
        self.env.draw_rain(eye, dt)
        glDisable(GL_LIGHTING)
        glDisable(GL_FOG)


def ordinal(n):
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))
