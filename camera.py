import math
import random

from mathutils import lerp

MODES = ["chase", "far", "hood"]


class Camera:
    def __init__(self):
        self.mode = 0
        self.pos = [0.0, 5.0, -10.0]
        self.target = [0.0, 0.0, 0.0]
        self.fov = 62.0
        self.shake = 0.0
        self.orbit = 0.0
        self.first = True

    def cycle(self):
        self.mode = (self.mode + 1) % len(MODES)
        self.first = True

    @property
    def name(self):
        return MODES[self.mode]

    def follow(self, car, dt, orbit=False):
        fx, fz = car.forward()
        speed = max(0.0, car.forward_speed())
        if orbit:
            self.orbit += dt * 0.35
            a = car.heading + math.pi + self.orbit
            want = [car.x + math.sin(a) * 9, car.y + 2.6, car.z + math.cos(a) * 9]
            tgt = [car.x, car.y + 0.8, car.z]
            k = 1.0 if self.first else min(1.0, dt * 3)
            fov = 55
        elif MODES[self.mode] == "hood":
            want = [car.x + fx * 0.6, car.y + 1.22, car.z + fz * 0.6]
            tgt = [car.x + fx * 20, car.y + 1.0, car.z + fz * 20]
            k = 1.0
            fov = 68 + min(speed, 80) * 0.12
        else:
            far = MODES[self.mode] == "far"
            dist = (9.0 if far else 6.2) + speed * 0.025
            h = (3.3 if far else 2.15) + speed * 0.004
            vfx, vfz = fx, fz
            if speed > 3:
                ang = math.atan2(car.vx, car.vz)
                diff = math.atan2(math.sin(ang - car.heading), math.cos(ang - car.heading))
                ang2 = car.heading + diff * 0.35
                vfx, vfz = math.sin(ang2), math.cos(ang2)
            want = [car.x - vfx * dist, car.y + h, car.z - vfz * dist]
            tgt = [car.x + fx * 3.5, car.y + 1.0, car.z + fz * 3.5]
            k = 1.0 if self.first else min(1.0, dt * 7.5)
            fov = 60 + min(speed, 85) * 0.14 + (7 if car.nitro_on else 0)
        self.first = False
        for i in range(3):
            self.pos[i] = lerp(self.pos[i], want[i], k)
            self.target[i] = lerp(self.target[i], tgt[i], min(1.0, k * 1.6))
        self.fov = lerp(self.fov, fov, min(1.0, dt * 3))
        self.shake = max(0.0, self.shake - dt * 2.5)

    def eye(self):
        if self.shake > 0:
            s = self.shake * 0.25
            return (self.pos[0] + random.uniform(-s, s), self.pos[1] + random.uniform(-s, s), self.pos[2] + random.uniform(-s, s))
        return tuple(self.pos)
