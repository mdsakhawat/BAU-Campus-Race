import math
import random

from config import *
from car import Controls
from mathutils import clamp


class AIDriver:
    def __init__(self, car, track, skill, diff):
        self.car = car
        self.track = track
        self.skill = skill
        self.diff = diff
        self.offset = random.uniform(-2.5, 2.5)
        self.offset_target = self.offset
        self.retarget = random.uniform(2, 5)
        self.stuck_t = 0.0
        self.nitro_t = random.uniform(4, 10)
        self.speed_cap = self.build_speed_profile()

    def build_speed_profile(self):
        tr = self.track
        a_lat = GRAVITY * self.car.grip * self.diff["ai_grip"] * self.skill * 0.92
        n = tr.n
        caps = []
        for i in range(n):
            k = abs(tr.curv[i])
            v = math.sqrt(a_lat / k) if k > 1e-5 else 120.0
            caps.append(min(v, 120.0))
        decel = GRAVITY * self.car.grip * 0.95
        for _ in range(2):
            for i in range(n - 1, -1, -1):
                j = (i + 1) % n
                caps[i] = min(caps[i], math.sqrt(caps[j] ** 2 + 2 * decel * tr.step))
        return caps

    def control(self, dt, cars, leader_total, player_total):
        car = self.car
        tr = self.track
        ctl = Controls()
        speed = car.forward_speed()
        self.retarget -= dt
        if self.retarget <= 0:
            self.retarget = random.uniform(3, 7)
            k = tr.curv[(car.idx + 30) % tr.n]
            inside = -math.copysign(3.0, k) if abs(k) > 1 / 300 else random.uniform(-2.5, 2.5)
            self.offset_target = clamp(inside * self.diff["ai_line"] + random.uniform(-1, 1), -(ROAD_HALF - 1.6), ROAD_HALF - 1.6)
        for other in cars:
            if other is car:
                continue
            dx, dz = other.x - car.x, other.z - car.z
            fx, fz = car.forward()
            ahead = dx * fx + dz * fz
            side = dx * -fz + dz * fx
            if 0 < ahead < 14 and abs(side) < 2.6 and other.forward_speed() < speed + 2:
                self.offset_target = clamp(other.lateral + (3.2 if other.lateral < 0 else -3.2), -5, 5)
        self.offset += (self.offset_target - self.offset) * min(1.0, dt * 0.8)
        look = int(6 + max(0.0, speed) * 0.45 / tr.step * 2)
        j = (car.idx + look) % tr.n
        tx, _, tz = tr.edge(j, self.offset)
        dx, dz = tx - car.x, tz - car.z
        fx, fz = car.forward()
        rx, rz = -fz, fx
        fwd = dx * fx + dz * fz
        side = dx * rx + dz * rz
        ang = math.atan2(side, max(fwd, 0.1))
        ctl.steer = clamp(ang * 2.4, -1, 1)
        cap = min(self.speed_cap[(car.idx + k) % tr.n] for k in range(0, 10))
        cap *= self.skill
        rubber = self.diff["rubber"]
        gap = player_total - car.total
        if rubber:
            cap *= 1 + clamp(gap / 300.0, -1, 1) * rubber
        if speed < cap - 1:
            ctl.throttle = 1.0
        elif speed > cap + 1.5:
            ctl.brake = clamp((speed - cap) / 6, 0.2, 1.0)
        else:
            ctl.throttle = 0.4
        if abs(car.lateral) > ROAD_HALF + 2:
            ctl.throttle = min(ctl.throttle, 0.7)
        self.nitro_t -= dt
        if self.nitro_t < 0 and abs(tr.curv[j]) < 1 / 500 and speed > 30:
            ctl.nitro = True
            if self.nitro_t < -2.5:
                self.nitro_t = random.uniform(8, 16)
        if speed < 2 and car.throttle > 0.5:
            self.stuck_t += dt
        else:
            self.stuck_t = 0.0
        if self.stuck_t > 2.5:
            car.respawn(tr)
            self.stuck_t = 0.0
        return ctl
