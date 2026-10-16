import math

from config import *
from mathutils import clamp, approach


class Controls:
    def __init__(self):
        self.throttle = 0.0
        self.brake = 0.0
        self.steer = 0.0
        self.handbrake = False
        self.nitro = False


def torque_curve(rpm):
    x = rpm / MAX_RPM
    return clamp(0.55 + 1.6 * x - 1.3 * x * x, 0.4, 1.0)


class Car:
    WHEELBASE = 2.65
    RADIUS = 1.05

    def __init__(self, spec, color, name, player=False, model=None):
        self.spec = spec
        self.color = color
        self.name = name
        self.player = player
        self.model = model
        self.mass = spec["mass"]
        self.torque = spec["torque"]
        self.grip = spec["grip"]
        self.top = spec["top"] / 3.6
        top_force = self.torque * torque_curve(6800) * GEARS[-1] * FINAL_DRIVE * 0.85 / WHEEL_R
        self.drag_k = top_force / (self.top ** 2) * 0.96
        self.power_scale = 1.0
        self.grip_scale = 1.0
        self.assist = False
        self.reset_state()

    def reset_state(self):
        self.x = self.y = self.z = 0.0
        self.heading = 0.0
        self.vx = self.vz = 0.0
        self.yaw_rate = 0.0
        self.steer = 0.0
        self.rpm = IDLE_RPM
        self.gear = 1
        self.shift_t = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.handbrake = False
        self.nitro = 1.0
        self.nitro_on = False
        self.spin = 0.0
        self.idx = 0
        self.lateral = 0.0
        self.along = 0.0
        self.total = 0.0
        self.last_s = None
        self.finished = False
        self.finish_time = None
        self.slip = 0.0
        self.offroad = False
        self.on_curb = False
        self.pitch = 0.0
        self.roll = 0.0
        self.accel_long = 0.0
        self.accel_lat = 0.0
        self.impact = 0.0
        self.wall_contact = False
        self.wrong_way_t = 0.0
        self.best_lap = None
        self.lap_start = 0.0
        self.lap_times = []
        self.gear_changed = False

    @property
    def speed(self):
        return math.hypot(self.vx, self.vz)

    @property
    def kmh(self):
        return self.forward_speed() * 3.6

    def forward(self):
        return math.sin(self.heading), math.cos(self.heading)

    def right(self):
        fx, fz = self.forward()
        return -fz, fx

    def forward_speed(self):
        fx, fz = self.forward()
        return self.vx * fx + self.vz * fz

    def place(self, track, idx, lateral, total):
        self.reset_state()
        idx = idx % track.n
        x, y, z = track.edge(idx, lateral)
        self.x, self.y, self.z = x, y, z
        self.heading = track.heading[idx]
        self.idx = idx
        self.total = total
        self.last_s = idx * track.step

    def lap(self, track, laps):
        return int(clamp(math.floor(self.total / track.length) + 1, 1, laps))

    def update(self, dt, ctl, track, race_time, racing=True):
        self.gear_changed = False
        if not racing:
            ctl = Controls() if self.finished else ctl
        fx, fz = self.forward()
        rx, rz = -fz, fx
        v_f = self.vx * fx + self.vz * fz
        v_r = self.vx * rx + self.vz * rz
        speed = abs(v_f)
        lat_edge = ROAD_HALF + CURB_W
        self.offroad = abs(self.lateral) > lat_edge + 0.3
        self.on_curb = ROAD_HALF < abs(self.lateral) <= lat_edge + 0.3
        surface = 0.82 if self.offroad else 1.0
        grip = self.grip * self.grip_scale * surface * (1 + min(speed, 80) ** 2 / 9000)

        steer_in = clamp(ctl.steer, -1, 1)
        max_steer = STEER_MAX / (1 + speed / STEER_FADE)
        target = steer_in * max_steer
        self.steer = approach(self.steer, target, 6.5 * dt)

        throttle = clamp(ctl.throttle, 0, 1)
        brake = clamp(ctl.brake, 0, 1)
        self.handbrake = ctl.handbrake
        if not racing:
            if self.finished:
                throttle, brake = 0.0, 0.35
            else:
                self.rpm = approach(self.rpm, IDLE_RPM + throttle * (MAX_RPM - IDLE_RPM) * 0.85, 9000 * dt)
                self.throttle = throttle
                self.vx *= max(0.0, 1 - 4 * dt)
                self.vz *= max(0.0, 1 - 4 * dt)
                return
        self.throttle = throttle
        self.brake = brake

        wheel_rpm = abs(v_f) / (2 * math.pi * WHEEL_R) * 60
        gear_ratio = GEARS[self.gear - 1] * FINAL_DRIVE
        self.rpm = clamp(wheel_rpm * gear_ratio, IDLE_RPM, MAX_RPM)
        if self.shift_t > 0:
            self.shift_t -= dt
        elif v_f > 1:
            if self.rpm > SHIFT_UP and self.gear < len(GEARS):
                self.gear += 1
                self.shift_t = 0.16
                self.gear_changed = True
            elif self.rpm < SHIFT_DOWN and self.gear > 1:
                self.gear -= 1
                self.shift_t = 0.08
                self.gear_changed = True
        if v_f < 1 and self.gear > 1:
            self.gear = 1

        self.nitro_on = ctl.nitro and self.nitro > 0.02 and throttle > 0.2 and racing
        if self.nitro_on:
            self.nitro = max(0.0, self.nitro - 0.22 * dt)
        else:
            self.nitro = min(1.0, self.nitro + (0.025 + min(1.0, self.slip / 6.0) * 0.10) * dt)

        drive = 0.0
        if self.shift_t <= 0:
            drive = self.torque * torque_curve(self.rpm) * gear_ratio * 0.85 / WHEEL_R * throttle * self.power_scale
        if self.nitro_on:
            drive += self.mass * 4.2
        traction = grip * self.mass * GRAVITY * 1.05
        if self.assist:
            drive = min(drive, traction * 0.95)
        elif drive > traction:
            self.slip = max(self.slip, (drive - traction) / self.mass * 0.6)
            drive = traction + (drive - traction) * 0.25
        reverse = False
        if brake > 0 and v_f < 0.8:
            reverse = True
            drive = -brake * self.mass * 3.5 if v_f > -9 else 0.0
            brake = 0.0
        top_bonus = 1.12 if self.nitro_on else 1.0
        drag = self.drag_k / top_bonus ** 2 * v_f * abs(v_f) + 14.0 * v_f
        if self.offroad:
            drag += 0.45 * self.mass * 0.25 * math.copysign(1, v_f) * min(1.0, speed / 5) + 0.25 * v_f * self.mass * 0.01
        brake_force = brake * grip * self.mass * GRAVITY * 1.05 * math.copysign(1, v_f) if speed > 0.3 else 0.0
        if ctl.handbrake and speed > 0.5:
            brake_force += 0.35 * self.mass * GRAVITY * math.copysign(1, v_f)
        slope_i = track.slope[self.idx]
        tf = track.fwd[self.idx]
        along_dot = fx * tf[0] + fz * tf[2]
        grav = -GRAVITY * slope_i * along_dot * self.mass
        a_long = (drive - drag - brake_force + grav) / self.mass
        if speed < 0.3 and drive == 0 and abs(grav) < self.mass * 2.0:
            a_long = -v_f / max(dt, 1e-3)
        v_f_new = v_f + a_long * dt
        if brake_force and v_f * v_f_new < 0 and not reverse:
            v_f_new = 0.0
        self.accel_long = (v_f_new - v_f) / dt

        yaw_target = -v_f * math.tan(self.steer) / self.WHEELBASE
        a_max = grip * GRAVITY * STEER_GRIP
        hb = ctl.handbrake and speed > 6
        if hb:
            a_max *= 1.55
        if abs(v_f) > 1:
            yaw_target = clamp(yaw_target, -a_max / abs(v_f), a_max / abs(v_f))
        rate = 13.0 if not hb else 4.0
        self.yaw_rate += (yaw_target - self.yaw_rate) * min(1.0, rate * dt)
        self.heading += self.yaw_rate * dt

        damp = grip * GRAVITY * (1.25 if not hb else 0.30)
        if self.assist:
            damp *= 1.25
        v_r_new = v_r - math.copysign(min(abs(v_r), damp * dt), v_r)
        self.slip = abs(v_r_new) * 0.8 + self.slip * 0.2 if speed > 3 else 0.0
        if brake > 0.6 and speed > 12 and not self.assist:
            self.slip = max(self.slip, 2.5 * brake)

        nfx, nfz = math.sin(self.heading), math.cos(self.heading)
        nrx, nrz = -nfz, nfx
        self.vx = nfx * v_f_new + nrx * v_r_new
        self.vz = nfz * v_f_new + nrz * v_r_new
        self.accel_lat = v_f * self.yaw_rate

        self.x += self.vx * dt
        self.z += self.vz * dt
        self.spin += v_f_new / WHEEL_R * dt
        self.locate(track, dt)
        self.update_progress(track, race_time)

    def locate(self, track, dt):
        idx, lat, along = track.nearest(self.x, self.z, self.idx)
        self.idx, self.lateral, self.along = idx, lat, along
        self.wall_contact = False
        limit = WALL_DIST - 1.0
        dist = math.hypot(lat, along) if abs(along) > track.step else abs(lat)
        if dist > limit:
            if abs(along) > track.step:
                p = track.pos[idx]
                r = ((self.x - p[0]) / dist, 0.0, (self.z - p[2]) / dist)
                sgn = 1
                lat = dist
            else:
                r = track.right[idx]
                sgn = 1 if lat > 0 else -1
            push = dist - limit
            self.x -= r[0] * push * sgn
            self.z -= r[2] * push * sgn
            vn = (self.vx * r[0] + self.vz * r[2]) * sgn
            if vn > 0:
                self.impact = max(self.impact, vn)
                self.vx -= r[0] * sgn * vn * 1.25
                self.vz -= r[2] * sgn * vn * 1.25
                k = max(0.8, 1 - vn * 0.015)
                self.vx *= k
                self.vz *= k
                if vn > 4:
                    self.yaw_rate *= 0.6
            sp = self.speed
            self.vx *= max(0.0, 1 - 0.35 * dt)
            self.vz *= max(0.0, 1 - 0.35 * dt)
            self.wall_contact = sp > 2
            lat = (1 if self.lateral >= 0 else -1) * limit
            self.lateral = lat
        fx, fz = self.forward()
        rx, rz = -fz, fx
        r = track.right[idx]
        worst = 0.0
        sg = 1
        for sa in (-2.2, 2.2):
            for sb in (-0.92, 0.92):
                ox, oz = fx * sa + rx * sb, fz * sa + rz * sb
                lc = self.lateral + ox * r[0] + oz * r[2]
                ex = abs(lc) - (WALL_DIST - 0.1)
                if ex > worst:
                    worst = ex
                    sg = 1 if lc > 0 else -1
        if worst > 0:
            self.x -= r[0] * worst * sg
            self.z -= r[2] * worst * sg
            self.lateral -= worst * sg
            lat = self.lateral
            vn = (self.vx * r[0] + self.vz * r[2]) * sg
            if vn > 0:
                self.impact = max(self.impact, vn)
                self.vx -= r[0] * sg * vn * 1.25
                self.vz -= r[2] * sg * vn * 1.25
                if vn > 4:
                    self.yaw_rate *= 0.7
            self.wall_contact = self.speed > 2
        ground_lat = clamp(lat, -(ROAD_HALF + CURB_W), ROAD_HALF + CURB_W)
        y = track.height(idx, ground_lat, along)
        if abs(lat) > ROAD_HALF + CURB_W:
            y -= min(0.12, (abs(lat) - ROAD_HALF - CURB_W) * 0.05)
        if self.on_curb:
            y += 0.03 * math.sin(self.total * 9)
        self.y += (y - self.y) * min(1.0, 18 * dt)
        tf = track.fwd[idx]
        fx, fz = self.forward()
        dot = fx * tf[0] + fz * tf[2]
        target_pitch = math.atan(track.slope[idx]) * dot - clamp(self.accel_long, -15, 15) * 0.004
        target_roll = track.bank[idx] * (1 if dot > 0 else -1) + clamp(self.accel_lat, -15, 15) * 0.006
        self.pitch += (target_pitch - self.pitch) * min(1.0, 8 * dt)
        self.roll += (target_roll - self.roll) * min(1.0, 8 * dt)
        if self.forward_speed() > 6 and dot < -0.3:
            self.wrong_way_t += dt
        else:
            self.wrong_way_t = 0.0

    def update_progress(self, track, race_time):
        s = self.idx * track.step + self.along
        if self.last_s is None:
            self.last_s = s
        d = s - self.last_s
        if d < -track.length / 2:
            d += track.length
        elif d > track.length / 2:
            d -= track.length
        self.last_s = s
        before = self.total
        self.total += d
        L = track.length
        if before < 0 <= self.total:
            self.lap_start = race_time
        elif math.floor(self.total / L) > math.floor(before / L) and before >= 0:
            lap_time = race_time - self.lap_start
            self.lap_times.append(lap_time)
            if self.best_lap is None or lap_time < self.best_lap:
                self.best_lap = lap_time
            self.lap_start = race_time

    def respawn(self, track):
        idx = self.idx
        total = self.total
        lap_start, best, times = self.lap_start, self.best_lap, self.lap_times
        nitro = self.nitro
        self.place(track, idx, clamp(self.lateral, -3, 3), total)
        self.lap_start, self.best_lap, self.lap_times = lap_start, best, times
        self.nitro = nitro

    def wheel_world(self, track):
        fx, fz = self.forward()
        rx, rz = -fz, fx
        out = []
        for wx, wy, wz, front in self.model.wheels:
            px = self.x + fx * wz - rx * wx
            pz = self.z + fz * wz - rz * wx
            out.append((px, self.y + 0.02, pz, front))
        return out
