import math

import numpy as np
from OpenGL.GL import *

import gfx

STYLES = {
    "coupe": dict(L=4.45, W=0.96, bottom=0.22, nose=0.62, hood=0.80, deck=0.92, tail=0.86,
                  cab0=-1.25, cab1=0.55, roof=1.28, roof_w=0.70, wheel_z=(1.42, -1.38), wheel_r=0.34, spoiler=False,
                  lip=0.10),
    "muscle": dict(L=4.75, W=1.0, bottom=0.25, nose=0.76, hood=0.92, deck=0.98, tail=0.96,
                   cab0=-1.20, cab1=0.35, roof=1.36, roof_w=0.76, wheel_z=(1.55, -1.45), wheel_r=0.36, spoiler=True,
                   lip=0.05, stripes=True),
    "hyper": dict(L=4.55, W=1.02, bottom=0.17, nose=0.48, hood=0.66, deck=0.84, tail=0.80,
                  cab0=-0.95, cab1=0.75, roof=1.12, roof_w=0.62, wheel_z=(1.46, -1.42), wheel_r=0.34, spoiler=True,
                  lip=0.14, wing_high=True),
    "sedan": dict(L=4.45, W=0.87, bottom=0.21, nose=0.64, hood=0.86, deck=0.94, tail=0.92,
                  cab0=-1.32, cab1=0.62, roof=1.44, roof_w=0.72, wheel_z=(1.36, -1.30), wheel_r=0.31, spoiler=False,
                  lip=0.03),
    "van": dict(L=4.70, W=0.87, bottom=0.25, nose=0.78, hood=0.98, deck=1.02, tail=1.00,
                cab0=-2.28, cab1=1.30, roof=1.95, roof_w=0.80, wheel_z=(1.52, -1.55), wheel_r=0.32, spoiler=False,
                lip=0.02),
    "suv": dict(L=4.60, W=0.93, bottom=0.34, nose=0.88, hood=1.06, deck=1.10, tail=1.08,
                cab0=-1.95, cab1=0.52, roof=1.80, roof_w=0.80, wheel_z=(1.42, -1.38), wheel_r=0.38, spoiler=False,
                lip=0.02),
}


def smooth(a, b, t):
    t = max(0.0, min(1.0, t))
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def profile(st, z):
    L = st["L"] / 2
    u = z / L
    if u > 0:
        sh = smooth(st["hood"], st["nose"], (u - 0.35) / 0.65)
    elif u > -0.12:
        sh = smooth(st["hood"], st["deck"], -u / 0.12)
    else:
        sh = smooth(st["deck"], st["tail"], (-u - 0.70) / 0.30)
    plan = max(0.0, 1 - abs(u) ** 7) ** 0.22
    w = st["W"] * plan
    b = st["bottom"] + max(0.0, abs(u) - 0.88) / 0.12 * 0.10
    r = st["wheel_r"]
    ra = r + 0.07
    for wz in st["wheel_z"]:
        dz = z - wz
        if abs(dz) < ra:
            arch = r + math.sqrt(ra * ra - dz * dz) * 0.92
            b = max(b, min(arch, sh - 0.14))
    return w, sh, b


def section(st, z):
    w, sh, b = profile(st, z)
    base = st["bottom"]
    pts = [(0.0, base), (w * 0.80, base), (w * 0.80, b) if b > base + 0.01 else (w * 0.80, base + 0.001),
           (w * 0.985, b + 0.03), (w, b + (sh - b) * 0.45), (w * 0.985, sh - 0.05),
           (w * 0.93, sh), (w * 0.62, sh + 0.025), (0.0, sh + 0.035)]
    return pts


def cabin_section(st, z):
    w, sh, b = profile(st, z)
    c0, c1 = st["cab0"], st["cab1"]
    span = c1 - c0
    t = (z - c0) / span
    lift = math.sin(math.pi * max(0.0, min(1.0, t))) ** 0.55
    front_rake = smooth(1.0, 0.0, (t - 0.55) / 0.45)
    rear_rake = smooth(0.0, 1.0, t / 0.35)
    h = sh + (st["roof"] - sh) * lift * min(front_rake, rear_rake) ** 0.5
    rw = st["roof_w"] * (0.75 + 0.25 * lift)
    base_w = w * 0.84
    return [(base_w, sh), (base_w * 0.96 + rw * 0.04, sh + (h - sh) * 0.25), (rw, h - 0.05), (rw * 0.75, h), (0.0, h + 0.01)]


def loft(sections_fn, st, z_list):
    rings = []
    for z in z_list:
        half = sections_fn(st, z)
        full = [(-x, y) for x, y in half] + [(x, y) for x, y in list(reversed(half))[1:]]
        rings.append([(x, y, z) for x, y in full])
    return np.array(rings)


def normals_for(grid):
    R, C, _ = grid.shape
    n = np.zeros_like(grid)
    for i in range(R - 1):
        for j in range(C - 1):
            a, b, d = grid[i, j], grid[i + 1, j], grid[i, j + 1]
            fn = np.cross(b - a, d - a)
            ln = np.linalg.norm(fn)
            if ln > 1e-9:
                fn /= ln
                for (ii, jj) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                    n[ii, jj] += fn
    ln = np.linalg.norm(n, axis=2)
    ln[ln < 1e-9] = 1
    return n / ln[..., None]


def draw_grid(grid, nrm, colors=None, flip=False):
    R, C, _ = grid.shape
    for j in range(C - 1):
        glBegin(GL_TRIANGLE_STRIP)
        for i in range(R):
            i0, i1 = max(0, i - 1), min(R - 1, i + 1)
            tz = grid[i1, j] - grid[i0, j] + grid[i1, j + 1] - grid[i0, j + 1]
            tb = grid[i, j + 1] - grid[i, j]
            n = np.cross(tz, tb)
            ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-9 else nrm[i, j]
            n = 0.75 * n + 0.25 * (nrm[i, j] + nrm[i, j + 1]) / 2
            for jj in (j + 1, j):
                if colors is not None:
                    glColor4f(*colors(i, jj, grid[i, jj]))
                glNormal3f(n[0], n[1], n[2])
                p = grid[i, jj]
                glVertex3f(p[0], p[1], p[2])
        glEnd()


def surface_z(st, x, front=True):
    L = st["L"] / 2
    q = min(0.999, abs(x) / st["W"])
    u = (1 - q ** (1 / 0.22)) ** (1 / 7)
    return (u if front else -u) * L


class CarModel:
    def __init__(self, style, color):
        self.style = style
        self.st = STYLES[style]
        self.color = color
        self.lists = {}
        st = self.st
        L = st["L"] / 2
        zs = sorted(set([L * math.sin(t * math.pi / 2) for t in np.linspace(-1, 1, 30)] + [wz + d for wz in st["wheel_z"] for d in np.linspace(-st["wheel_r"] - 0.08, st["wheel_r"] + 0.08, 9)]))
        self.body = loft(section, st, zs)
        self.body_n = normals_for(self.body)
        cz = np.linspace(st["cab0"], st["cab1"], 14)
        self.cab = loft(cabin_section, st, cz)
        self.cab_n = normals_for(self.cab)
        wz = st["wheel_z"]
        wx = st["W"] * 0.86
        self.wheels = [(wx, st["wheel_r"], wz[0], True), (-wx, st["wheel_r"], wz[0], True),
                       (wx, st["wheel_r"], wz[1], False), (-wx, st["wheel_r"], wz[1], False)]
        w, sh, b = profile(st, L * 0.93)
        self.head = [(s * w * 0.6, b + (sh - b) * 0.75, L + 0.02) for s in (-1, 1)]
        w, sh, b = profile(st, -L * 0.95)
        self.tail = [(s * w * 0.6, sh - 0.13, -L - 0.03) for s in (-1, 1)]
        self.length = st["L"]
        self.width = st["W"] * 2
        self.height = st["roof"]
        gfx.reset_hooks.append(self.reset_gl)

    def reset_gl(self):
        self.lists.clear()

    def release(self):
        if self.reset_gl in gfx.reset_hooks:
            gfx.reset_hooks.remove(self.reset_gl)

    def paint_color(self, i, j, p):
        c = self.color
        k = 0.88 + 0.12 * min(1.0, p[1] / 0.9)
        if self.st.get("stripes") and abs(p[0]) < 0.16 and p[1] > 0.6:
            return (0.95, 0.95, 0.95, 1)
        if p[1] < self.st["bottom"] + 0.03 or (abs(p[0]) < self.st["W"] * 0.81 and p[1] < self.st["bottom"] + 0.6 and abs(p[0]) > 0.01 and p[1] < 0.9 and False):
            return (0.06, 0.06, 0.07, 1)
        return (c[0] * k, c[1] * k, c[2] * k, 1)

    def cab_color(self, i, j, p):
        R = self.cab.shape[1]
        mid = (R - 1) / 2
        span = self.st["cab1"] - self.st["cab0"]
        t = (p[2] - self.st["cab0"]) / span
        top = abs(j - mid) <= 1.6 and 0.30 < t < 0.72
        if top:
            c = self.color
            if self.st.get("stripes") and abs(p[0]) < 0.16:
                return (0.95, 0.95, 0.95, 1)
            return (c[0], c[1], c[2], 1)
        return (0.05, 0.07, 0.09, 1)

    def build_body(self):
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.9, 0.9, 0.9, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 70)
        draw_grid(self.body, self.body_n, self.paint_color)
        draw_grid(self.cab, self.cab_n, self.cab_color)
        self.build_caps()
        self.build_extras()
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0, 0, 0, 1))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 10)

    def build_caps(self):
        for idx, nz in ((0, -1), (-1, 1)):
            ring = self.body[idx]
            glNormal3f(0, 0, nz)
            glColor4f(*self.paint_color(0, 0, (0, 0.7, 0)))
            glBegin(GL_TRIANGLE_FAN)
            cx = ring[:, 0].mean()
            cy = ring[:, 1].mean()
            glVertex3f(cx, cy, ring[0, 2])
            pts = ring[::-1] if nz > 0 else ring
            for p in pts:
                glVertex3f(*p)
            glEnd()
        for idx, nz in ((0, -1), (-1, 1)):
            ring = self.cab[idx]
            glNormal3f(0, 0, nz)
            glColor4f(0.05, 0.07, 0.09, 1)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0, ring[:, 1].mean(), ring[0, 2])
            pts = ring[::-1] if nz > 0 else ring
            for p in pts:
                glVertex3f(*p)
            glEnd()

    def build_extras(self):
        st = self.st
        L = st["L"] / 2
        w, sh, b = profile(st, L * 0.93)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        for side in (-1, 1):
            x0, x1 = side * w * 0.40, side * w * 0.80
            y0, y1 = b + (sh - b) * 0.50, sh - 0.05
            glColor4f(0.95, 0.96, 1.0, 1)
            glBegin(GL_QUADS)
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                glVertex3f(x, y, surface_z(st, x) + 0.012)
            glEnd()
        glColor4f(0.04, 0.04, 0.05, 1)
        glBegin(GL_QUADS)
        for x, y in ((-w * 0.36, b + 0.06), (w * 0.36, b + 0.06), (w * 0.36, b + (sh - b) * 0.42), (-w * 0.36, b + (sh - b) * 0.42)):
            glVertex3f(x, y, surface_z(st, x) + 0.01)
        glEnd()
        w, sh, b = profile(st, -L * 0.95)
        zr = surface_z(st, 0.25, False)
        for side in (-1, 1):
            x0, x1 = side * w * 0.30, side * w * 0.90
            y0, y1 = sh - 0.20, sh - 0.06
            glColor4f(0.65, 0.04, 0.04, 1)
            glBegin(GL_QUADS)
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                glVertex3f(x, y, surface_z(st, x, False) - 0.012)
            glEnd()
        glColor4f(0.15, 0.15, 0.16, 1)
        for side in (-0.25, 0.25):
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(side, b + 0.12, zr - 0.06)
            for k in range(13):
                a = 2 * math.pi * k / 12
                glVertex3f(side + math.cos(a) * 0.05, b + 0.12 + math.sin(a) * 0.05, zr - 0.06)
            glEnd()
        glEnable(GL_LIGHTING)
        if st["spoiler"]:
            hgt = 0.30 if st.get("wing_high") else 0.12
            ys = st["deck"] + hgt
            zs0, zs1 = -L * 0.80, -L * 0.98
            wing = st["W"] * 0.9
            c = self.color
            glColor4f(0.08, 0.08, 0.09, 1) if st.get("wing_high") else glColor4f(c[0], c[1], c[2], 1)
            glNormal3f(0, 1, 0)
            glBegin(GL_QUADS)
            for x, z in ((-wing, zs0), (wing, zs0), (wing, zs1), (-wing, zs1)):
                glVertex3f(x, ys + (0.03 if z == zs0 else 0.0), z)
            glEnd()
            glColor4f(0.08, 0.08, 0.09, 1)
            for x in (-wing * 0.6, wing * 0.6):
                glBegin(GL_QUADS)
                glNormal3f(1, 0, 0)
                for y, z in ((st["deck"] - 0.02, zs0), (st["deck"] - 0.02, zs1), (ys, zs1), (ys, zs0)):
                    glVertex3f(x, y, z)
                glEnd()
        glColor4f(0.06, 0.06, 0.07, 1)
        glNormal3f(0, 1, 0)
        glBegin(GL_QUADS)
        lip = st["lip"]
        for x, z in ((-st["W"] * 0.9, L * 0.92), (st["W"] * 0.9, L * 0.92), (st["W"] * 0.9, L + lip * 0.3), (-st["W"] * 0.9, L + lip * 0.3)):
            glVertex3f(x, st["bottom"] + 0.02, z)
        glEnd()
        glColor4f(0.03, 0.03, 0.035, 1)
        r = st["wheel_r"] + 0.07
        for wz in st["wheel_z"]:
            for side in (-1, 1):
                x = side * st["W"] * 0.62
                glNormal3f(side, 0, 0)
                glBegin(GL_TRIANGLE_FAN)
                glVertex3f(x, st["wheel_r"], wz)
                for k in range(17):
                    a = math.pi * k / 16
                    glVertex3f(x, st["wheel_r"] + math.sin(a) * r, wz + math.cos(a) * r)
                glEnd()
        for side in (-1, 1):
            z = st["cab1"] - 0.12
            w, sh, b = profile(st, z)
            x = side * (w * 0.86)
            c = self.color
            glColor4f(c[0] * 0.9, c[1] * 0.9, c[2] * 0.9, 1)
            glNormal3f(side, 0.3, 0)
            glBegin(GL_QUADS)
            for dx, dy, dz in ((0, 0.06, 0), (0.16, 0.06, -0.02), (0.16, 0.16, -0.06), (0, 0.16, -0.06)):
                glVertex3f(x + side * dx, sh + dy, z + dz)
            glEnd()
        glEnable(GL_CULL_FACE)

    def build_wheel(self):
        r = self.st["wheel_r"]
        w = 0.26
        seg = 20
        glDisable(GL_CULL_FACE)
        glColor4f(0.07, 0.07, 0.08, 1)
        glBegin(GL_QUAD_STRIP)
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            c, s = math.cos(a), math.sin(a)
            glNormal3f(0, c, s)
            glVertex3f(-w / 2, c * r, s * r)
            glVertex3f(w / 2, c * r, s * r)
        glEnd()
        for side in (-1, 1):
            x = side * w / 2
            glNormal3f(side, 0, 0)
            glColor4f(0.08, 0.08, 0.09, 1)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(x, 0, 0)
            for k in range(seg + 1):
                a = 2 * math.pi * k / seg * side
                glVertex3f(x, math.cos(a) * r, math.sin(a) * r)
            glEnd()
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (1, 1, 1, 1))
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 90)
            glColor4f(0.72, 0.74, 0.78, 1)
            rr = r * 0.66
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(x + side * 0.012, 0, 0)
            for k in range(seg + 1):
                a = 2 * math.pi * k / seg * side
                glVertex3f(x + side * 0.012, math.cos(a) * rr, math.sin(a) * rr)
            glEnd()
            glColor4f(0.25, 0.26, 0.28, 1)
            glBegin(GL_TRIANGLES)
            for k in range(5):
                a = 2 * math.pi * (k + 0.5) / 5
                b1, b2 = a - 0.32, a + 0.32
                glVertex3f(x + side * 0.016, 0, 0)
                glVertex3f(x + side * 0.016, math.cos(b1) * rr * 0.92, math.sin(b1) * rr * 0.92)
                glVertex3f(x + side * 0.016, math.cos(b2) * rr * 0.92, math.sin(b2) * rr * 0.92)
            glEnd()
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0, 0, 0, 1))
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 10)
        glEnable(GL_CULL_FACE)

    def build_silhouette(self):
        draw_grid(self.body, self.body_n)
        draw_grid(self.cab, self.cab_n)

    def list(self, key, fn):
        if key not in self.lists:
            lid = glGenLists(1)
            glNewList(lid, GL_COMPILE)
            fn()
            glEndList()
            self.lists[key] = lid
        return self.lists[key]

    def draw(self, wheel_spin=0.0, steer=0.0, brake=False, reflect=True):
        glCallList(self.list("body", self.build_body))
        wl = self.list("wheel", self.build_wheel)
        for x, y, z, front in self.wheels:
            glPushMatrix()
            glTranslatef(x, y, z)
            if front:
                glRotatef(math.degrees(steer), 0, 1, 0)
            glRotatef(math.degrees(wheel_spin), 1, 0, 0)
            glCallList(wl)
            glPopMatrix()
        if reflect:
            self.draw_reflection()

    def draw_reflection(self):
        fog = glIsEnabled(GL_FOG)
        glDisable(GL_FOG)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, gfx.image("env.jpg", repeat=False))
        glEnable(GL_TEXTURE_GEN_S)
        glEnable(GL_TEXTURE_GEN_T)
        glTexGeni(GL_S, GL_TEXTURE_GEN_MODE, GL_SPHERE_MAP)
        glTexGeni(GL_T, GL_TEXTURE_GEN_MODE, GL_SPHERE_MAP)
        glBlendFunc(GL_ONE, GL_ONE)
        glDepthMask(GL_FALSE)
        k = 0.20
        glColor4f(k, k, k, 1)
        glCallList(self.list("sil", self.build_silhouette))
        glDepthMask(GL_TRUE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_TEXTURE_GEN_S)
        glDisable(GL_TEXTURE_GEN_T)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        if fog:
            glEnable(GL_FOG)

    def draw_shadow_shape(self):
        glCallList(self.list("sil", self.build_silhouette))
