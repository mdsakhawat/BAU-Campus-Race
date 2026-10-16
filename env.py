import math
import random

import numpy as np
from OpenGL.GL import *

import gfx
from mathutils import clamp, lerp, lerp_color

KEYS = [
    (0.0, dict(top=(0.015, 0.02, 0.06), hor=(0.09, 0.09, 0.13), sun=(0.16, 0.18, 0.28), amb=(0.11, 0.12, 0.18))),
    (4.8, dict(top=(0.02, 0.03, 0.08), hor=(0.12, 0.11, 0.15), sun=(0.16, 0.18, 0.28), amb=(0.12, 0.12, 0.18))),
    (5.6, dict(top=(0.10, 0.13, 0.26), hor=(0.42, 0.30, 0.32), sun=(0.30, 0.25, 0.30), amb=(0.20, 0.19, 0.24))),
    (6.3, dict(top=(0.28, 0.40, 0.64), hor=(0.95, 0.64, 0.44), sun=(1.00, 0.62, 0.38), amb=(0.34, 0.30, 0.32))),
    (8.0, dict(top=(0.36, 0.56, 0.84), hor=(0.84, 0.84, 0.80), sun=(1.00, 0.90, 0.76), amb=(0.42, 0.42, 0.44))),
    (12.0, dict(top=(0.34, 0.55, 0.86), hor=(0.84, 0.86, 0.86), sun=(1.00, 0.97, 0.90), amb=(0.46, 0.46, 0.48))),
    (16.0, dict(top=(0.36, 0.54, 0.82), hor=(0.88, 0.84, 0.76), sun=(1.00, 0.92, 0.78), amb=(0.44, 0.42, 0.42))),
    (17.4, dict(top=(0.34, 0.46, 0.72), hor=(0.98, 0.74, 0.48), sun=(1.00, 0.72, 0.42), amb=(0.40, 0.35, 0.33))),
    (18.2, dict(top=(0.20, 0.22, 0.44), hor=(0.94, 0.48, 0.32), sun=(0.92, 0.44, 0.26), amb=(0.28, 0.22, 0.26))),
    (19.0, dict(top=(0.05, 0.07, 0.17), hor=(0.30, 0.20, 0.28), sun=(0.24, 0.20, 0.30), amb=(0.16, 0.15, 0.20))),
    (19.8, dict(top=(0.02, 0.03, 0.08), hor=(0.11, 0.10, 0.14), sun=(0.16, 0.18, 0.28), amb=(0.12, 0.12, 0.18))),
    (24.0, dict(top=(0.015, 0.02, 0.06), hor=(0.09, 0.09, 0.13), sun=(0.16, 0.18, 0.28), amb=(0.11, 0.12, 0.18))),
]
HAZE = (0.74, 0.70, 0.62)
CITY_GLOW = (0.32, 0.22, 0.14)


def sample(hour):
    hour %= 24.0
    for k in range(len(KEYS) - 1):
        h0, a = KEYS[k]
        h1, b = KEYS[k + 1]
        if h0 <= hour <= h1:
            t = (hour - h0) / (h1 - h0)
            t = t * t * (3 - 2 * t)
            return {key: lerp_color(a[key], b[key], t) for key in a}
    return dict(KEYS[0][1])


class Environment:
    def __init__(self, hour=8.0, live=False, weather="clear"):
        self.hour = hour
        self.live = live
        self.weather = weather
        self.rain = 1.0 if weather == "rain" else 0.0
        self.haze = 1.0 if weather == "hazy" else 0.25
        self.t = 0.0
        self.flash = 0.0
        self.next_bolt = random.uniform(6, 14)
        self.events = []
        self.drops = None
        self.stars = [(random.uniform(0, 2 * math.pi), random.uniform(0.15, 1.45), random.uniform(0.4, 1.0)) for _ in range(380)]
        self.random_weather_t = random.uniform(120, 240)
        self.random_mode = False
        self.compute()

    def set_weather(self, w):
        self.weather = w

    def update(self, dt, cam=None):
        self.t += dt
        if self.live:
            self.hour = (self.hour + dt / 60.0) % 24.0
        if self.random_mode:
            self.random_weather_t -= dt
            if self.random_weather_t <= 0:
                self.weather = random.choice(["clear", "clear", "hazy", "rain"])
                self.random_weather_t = random.uniform(150, 300)
        target_rain = 1.0 if self.weather == "rain" else 0.0
        target_haze = 1.0 if self.weather == "hazy" else (0.5 if self.weather == "rain" else 0.25)
        self.rain += (target_rain - self.rain) * min(1.0, dt * 0.25)
        self.haze += (target_haze - self.haze) * min(1.0, dt * 0.3)
        self.flash = max(0.0, self.flash - dt * 3.5)
        if self.rain > 0.6:
            self.next_bolt -= dt
            if self.next_bolt <= 0:
                self.flash = 1.0
                self.next_bolt = random.uniform(7, 22)
                self.events.append(("thunder", random.uniform(0.4, 2.5)))
        pending = []
        for name, delay in self.events:
            pending.append((name, delay - dt))
        self.events = pending
        self.compute()

    def pop_events(self):
        out = [n for n, d in self.events if d <= 0]
        self.events = [(n, d) for n, d in self.events if d > 0]
        return out

    def compute(self):
        h = self.hour
        s = sample(h)
        day = clamp((math.sin(math.pi * (h - 6.0) / 12.0) + 0.18) / 0.5)
        self.daylight = day
        self.night = clamp(1 - (math.sin(math.pi * (h - 6.0) / 12.0) + 0.10) / 0.22)
        rain = self.rain
        haze = self.haze
        top, hor, sun, amb = s["top"], s["hor"], s["sun"], s["amb"]
        hz = haze * 0.55 * day
        hor = lerp_color(hor, lerp_color(HAZE, hor, 0.35), hz)
        top = lerp_color(top, lerp_color(top, hor, 0.5), hz * 0.6)
        if rain > 0:
            grey = 0.30 + 0.32 * day
            over_top = (grey * 0.62, grey * 0.66, grey * 0.72)
            over_hor = (grey * 0.86, grey * 0.88, grey * 0.90)
            top = lerp_color(top, over_top, rain * 0.9)
            hor = lerp_color(hor, over_hor, rain * 0.9)
            sun = lerp_color(sun, (sun[0] * 0.30, sun[1] * 0.32, sun[2] * 0.36), rain)
            amb = lerp_color(amb, (amb[0] * 1.05, amb[1] * 1.08, amb[2] * 1.14), rain)
        night_glow = self.night * (1 - rain * 0.4)
        hor = tuple(hor[i] + CITY_GLOW[i] * night_glow * 0.55 for i in range(3))
        if self.flash > 0:
            f = self.flash * (0.6 + 0.4 * math.sin(self.t * 90))
            top = tuple(min(1.0, c + f * 0.55) for c in top)
            hor = tuple(min(1.0, c + f * 0.45) for c in hor)
            amb = tuple(min(1.0, c + f * 0.5) for c in amb)
        self.top, self.hor, self.sun_color, self.ambient = top, hor, sun, amb
        self.fog_color = hor
        near = lerp(140.0, 60.0, haze * 0.6 + rain * 0.4)
        far = lerp(640.0, 330.0, haze * 0.55 + rain * 0.45)
        if self.night > 0:
            far = lerp(far, far * 0.82, self.night)
        self.fog_range = (near, far)
        a = math.pi * (h - 6.0) / 12.0
        if 5.0 < h < 19.0:
            sx = -math.cos(a)
            sy = max(0.18, math.sin(a))
            sz = -0.42
        else:
            sx, sy, sz = 0.35, 0.85, 0.30
        ln = math.sqrt(sx * sx + sy * sy + sz * sz)
        self.sun_dir = (sx / ln, sy / ln, sz / ln)
        self.sun_vis = clamp(math.sin(a) * 4) if 5.0 < h < 19.0 else 0.0
        self.shadow_alpha = 0.42 * clamp(day * 1.4) * (1 - rain * 0.65) + 0.10 * self.night
        self.light_level = clamp(0.28 + 0.72 * day) * (1 - 0.30 * rain) + self.flash * 0.3
        self.lamps = self.night > 0.25 or (rain > 0.7 and day < 0.8)
        self.wet = rain

    def clock(self):
        h = int(self.hour)
        m = int((self.hour - h) * 60)
        suffix = "AM" if h < 12 else "PM"
        hh = h % 12 or 12
        return "%d:%02d %s" % (hh, m, suffix)

    def setup_light(self):
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_NORMALIZE)
        sx, sy, sz = self.sun_dir
        glLightfv(GL_LIGHT0, GL_POSITION, (sx, sy, sz, 0.0))
        s = self.sun_color
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (s[0] * 0.85, s[1] * 0.85, s[2] * 0.85, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (s[0] * 0.6, s[1] * 0.6, s[2] * 0.6, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0, 0, 0, 1))
        a = self.ambient
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (a[0], a[1], a[2], 1))
        glLightModeli(GL_LIGHT_MODEL_LOCAL_VIEWER, GL_FALSE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0, 0, 0, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 10)
        self.fog_on()

    def fog_on(self, color=None, scale=1.0):
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        c = color if color is not None else self.fog_color
        glFogfv(GL_FOG_COLOR, (c[0], c[1], c[2], 1))
        glFogf(GL_FOG_START, self.fog_range[0] * scale)
        glFogf(GL_FOG_END, self.fog_range[1] * scale)

    def draw_sky(self, cam, center):
        glDisable(GL_LIGHTING)
        glDisable(GL_FOG)
        glDisable(GL_TEXTURE_2D)
        glDepthMask(GL_FALSE)
        glDisable(GL_CULL_FACE)
        glPushMatrix()
        glTranslatef(cam[0], cam[1], cam[2])
        R = 1400.0
        top, hor = self.top, self.hor
        sx, sy, sz = self.sun_dir
        sun = self.sun_color
        rings = 10
        seg = 32
        glow_k = self.sun_vis * (1 - self.rain * 0.8)
        for i in range(rings):
            e0 = (math.pi / 2) * (i / rings) ** 1.6
            e1 = (math.pi / 2) * ((i + 1) / rings) ** 1.6
            glBegin(GL_QUAD_STRIP)
            for k in range(seg + 1):
                a = 2 * math.pi * k / seg
                for e in (e0, e1):
                    dx, dy, dz = math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)
                    t = (e / (math.pi / 2)) ** 0.55
                    c = lerp_color(hor, top, t)
                    d = max(0.0, dx * sx + dy * sy + dz * sz)
                    g = (d ** 8) * 0.55 * glow_k + (d ** 2) * 0.12 * glow_k * (1 - t)
                    glColor4f(min(1, c[0] + sun[0] * g), min(1, c[1] + sun[1] * g), min(1, c[2] + sun[2] * g), 1)
                    glVertex3f(dx * R, dy * R, dz * R)
            glEnd()
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(hor[0], hor[1], hor[2], 1)
        glVertex3f(0, -R, 0)
        for k in range(seg + 1):
            a = -2 * math.pi * k / seg
            glVertex3f(math.sin(a) * R, 0, math.cos(a) * R)
        glEnd()
        if self.night > 0.05 and self.rain < 0.9:
            k = self.night * (1 - self.rain) * (1 - self.haze * 0.5)
            glPointSize(2.0)
            glBegin(GL_POINTS)
            for a, e, b in self.stars:
                tw = 0.75 + 0.25 * math.sin(self.t * 3 + a * 50)
                glColor4f(1, 1, 1, k * b * tw)
                glVertex3f(math.cos(e) * math.sin(a) * R * 0.9, math.sin(e) * R * 0.9, math.cos(e) * math.cos(a) * R * 0.9)
            glEnd()
            glPointSize(1.0)
        items = []
        if self.sun_vis > 0 and self.rain < 0.95:
            p = (sx * 1100, sy * 1100, sz * 1100)
            a = self.sun_vis * (1 - self.rain)
            items.append((p, 260, (sun[0], sun[1] * 0.95, sun[2] * 0.8), 0.55 * a))
            items.append((p, 70, (1.0, 0.98, 0.9), 0.95 * a))
        if self.night > 0.3 and self.rain < 0.9:
            mp = (-0.45 * 1100, 0.62 * 1100, 0.64 * 1100)
            a = self.night * (1 - self.rain)
            items.append((mp, 140, (0.6, 0.7, 0.9), 0.35 * a))
            items.append((mp, 36, (0.95, 0.95, 0.88), 0.95 * a))
        billboards(items, "glow")
        glPopMatrix()
        self.draw_clouds(cam)
        self.draw_skyline(cam, center)
        glDepthMask(GL_TRUE)
        glEnable(GL_CULL_FACE)

    def draw_clouds(self, cam):
        alpha = 0.55 * (1 - self.haze * 0.3) + 0.45 * self.rain
        if alpha <= 0.01:
            return
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        c = self.hor
        glFogfv(GL_FOG_COLOR, (c[0], c[1], c[2], 1))
        glFogf(GL_FOG_START, 500)
        glFogf(GL_FOG_END, 2200)
        gfx.bind("clouds.png", repeat=True, mipmap=True)
        lit = lerp_color(self.top, (1, 1, 1), 0.55 * self.daylight)
        if self.rain > 0:
            lit = lerp_color(lit, (lit[0] * 0.55, lit[1] * 0.57, lit[2] * 0.6), self.rain)
        if self.night > 0:
            lit = lerp_color(lit, (0.10, 0.10, 0.14), self.night * 0.7)
        ext = 2600.0
        y = 380.0 if self.rain < 0.5 else 300.0
        off = self.t * 0.004
        scale = 1 / 900.0
        cx, cz = cam[0], cam[2]
        glColor4f(lit[0], lit[1], lit[2], min(1.0, alpha))
        glBegin(GL_QUADS)
        for x, z in ((cx - ext, cz - ext), (cx + ext, cz - ext), (cx + ext, cz + ext), (cx - ext, cz + ext)):
            glTexCoord2f(x * scale + off, z * scale + off * 0.4)
            glVertex3f(x, y, z)
        glEnd()
        if self.rain > 0.3:
            glColor4f(lit[0] * 0.8, lit[1] * 0.8, lit[2] * 0.85, (self.rain - 0.3))
            glBegin(GL_QUADS)
            for x, z in ((cx - ext, cz - ext), (cx + ext, cz - ext), (cx + ext, cz + ext), (cx - ext, cz + ext)):
                glTexCoord2f(x * scale * 1.7 + off * 2, z * scale * 1.7)
                glVertex3f(x, y - 40, z)
            glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_FOG)

    def draw_skyline(self, cam, center):
        R = 1050.0
        H = getattr(self, "skyline_h", 150.0)
        tex = getattr(self, "skyline_tex", "skyline.png")
        cx, cz = center
        seg = 48
        fc = self.fog_color
        base = lerp_color(fc, (fc[0] * 0.72, fc[1] * 0.72, fc[2] * 0.76), 0.55 - 0.35 * self.haze)
        gfx.bind(tex, repeat=True, mipmap=True)
        glColor4f(base[0], base[1], base[2], 1)
        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GREATER, 0.4)
        glBegin(GL_QUAD_STRIP)
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            x, z = cx + math.sin(a) * R, cz + math.cos(a) * R
            glTexCoord2f(k / seg * 4, 0)
            glVertex3f(x, -6, z)
            glTexCoord2f(k / seg * 4, 1)
            glVertex3f(x, H, z)
        glEnd()
        glDisable(GL_ALPHA_TEST)
        if self.night > 0.2 and tex == "skyline.png":
            gfx.bind("skyline_lit.jpg", repeat=True, mipmap=True)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            k = self.night * 0.55 * (1 - self.haze * 0.4)
            glColor4f(k, k, k, 1)
            glBegin(GL_QUAD_STRIP)
            for k2 in range(seg + 1):
                a = 2 * math.pi * k2 / seg
                x, z = cx + math.sin(a) * R, cz + math.cos(a) * R
                glTexCoord2f(k2 / seg * 4, 0)
                glVertex3f(x, -6, z)
                glTexCoord2f(k2 / seg * 4, 1)
                glVertex3f(x, H, z)
            glEnd()
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_TEXTURE_2D)

    def draw_rain(self, cam, dt, ground_fn=None):
        if self.rain < 0.05:
            return
        n = int(1400 * self.rain)
        if self.drops is None or len(self.drops) < 1400:
            d = np.zeros((1400, 3), np.float32)
            d[:, 0] = np.random.uniform(-28, 28, 1400)
            d[:, 1] = np.random.uniform(0, 26, 1400)
            d[:, 2] = np.random.uniform(-28, 28, 1400)
            self.drops = d
        d = self.drops
        d[:, 1] -= 22 * dt
        low = d[:, 1] < -2
        cnt = int(low.sum())
        if cnt:
            d[low, 0] = np.random.uniform(-28, 28, cnt)
            d[low, 1] = np.random.uniform(20, 26, cnt)
            d[low, 2] = np.random.uniform(-28, 28, cnt)
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glDepthMask(GL_FALSE)
        bright = 0.55 + 0.35 * self.light_level
        glLineWidth(1.2)
        pts = d[:n]
        bx = cam[0] + (pts[:, 0] - cam[0] + 28) % 56 - 28
        bz = cam[2] + (pts[:, 2] - cam[2] + 28) % 56 - 28
        by = pts[:, 1] + cam[1] - 6
        glBegin(GL_LINES)
        for i in range(n):
            glColor4f(bright * 0.8, bright * 0.85, bright * 0.95, 0.0)
            glVertex3f(bx[i] + 0.15, by[i] + 1.2, bz[i] + 0.06)
            glColor4f(bright * 0.8, bright * 0.85, bright * 0.95, 0.6 * self.rain)
            glVertex3f(bx[i], by[i], bz[i])
        glEnd()
        glLineWidth(1.0)
        glDepthMask(GL_TRUE)


def billboards(items, tex="glow", additive=True):
    if not items:
        return
    m = glGetFloatv(GL_MODELVIEW_MATRIX)
    rx, ry, rz = m[0][0], m[1][0], m[2][0]
    ux, uy, uz = m[0][1], m[1][1], m[2][1]
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, gfx.texture(tex))
    if additive:
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glBegin(GL_QUADS)
    for (x, y, z), s, c, a in items:
        glColor4f(c[0], c[1], c[2], a)
        h = s / 2
        glTexCoord2f(0, 0); glVertex3f(x - rx * h - ux * h, y - ry * h - uy * h, z - rz * h - uz * h)
        glTexCoord2f(1, 0); glVertex3f(x + rx * h - ux * h, y + ry * h - uy * h, z + rz * h - uz * h)
        glTexCoord2f(1, 1); glVertex3f(x + rx * h + ux * h, y + ry * h + uy * h, z + rz * h + uz * h)
        glTexCoord2f(0, 1); glVertex3f(x - rx * h + ux * h, y - ry * h + uy * h, z - rz * h + uz * h)
    glEnd()
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_TEXTURE_2D)
