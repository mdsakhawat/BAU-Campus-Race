
import numpy as np
from OpenGL.GL import *

import gfx
from config import *


def catmull_rom(points, per_segment):
    P = np.array(points, dtype=np.float64)
    n = len(P)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for t in np.linspace(0, 1, per_segment, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


class Track:
    def __init__(self, info):
        self.info = info
        raw = catmull_rom([(x, h, z) for x, z, h in info["points"]], 80)
        seg = np.linalg.norm(np.diff(np.vstack([raw, raw[:1]]), axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)])
        self.length = cum[-1]
        n = int(self.length // SAMPLE_STEP)
        self.n = n
        self.step = self.length / n
        s = np.arange(n) * self.step
        closed = np.vstack([raw, raw[:1]])
        pos = np.stack([np.interp(s, cum, closed[:, k]) for k in range(3)], axis=1)
        y = pos[:, 1].copy()
        for _ in range(6):
            y = (np.roll(y, 1) + 2 * y + np.roll(y, -1)) / 4
        pos[:, 1] = y
        self.pos = pos
        fwd = np.roll(pos, -1, axis=0) - np.roll(pos, 1, axis=0)
        flat = fwd.copy()
        flat[:, 1] = 0
        flat /= np.linalg.norm(flat, axis=1)[:, None]
        self.fwd = flat
        self.right = np.stack([-flat[:, 2], np.zeros(n), flat[:, 0]], axis=1)
        heading = np.arctan2(flat[:, 0], flat[:, 2])
        dh = np.angle(np.exp(1j * (np.roll(heading, -1) - np.roll(heading, 1))))
        curv = dh / (2 * self.step)
        for _ in range(4):
            curv = (np.roll(curv, 1) + 2 * curv + np.roll(curv, -1)) / 4
        self.curv = curv
        self.heading = heading
        self.slope = (np.roll(pos[:, 1], -1) - np.roll(pos[:, 1], 1)) / (2 * self.step)
        self.bank = np.clip(-curv * 6.0, -0.07, 0.07)
        self.dist = s
        self.curb = np.abs(curv) > 1 / 260.0
        grow = self.curb.copy()
        for k in range(1, 6):
            grow |= np.roll(self.curb, k) | np.roll(self.curb, -k)
        self.curb = grow
        self.lists = {}
        gfx.reset_hooks.append(self.reset_gl)

    def reset_gl(self):
        self.lists.clear()

    def release(self):
        if self.reset_gl in gfx.reset_hooks:
            gfx.reset_hooks.remove(self.reset_gl)

    def wrap(self, i):
        return i % self.n

    def edge(self, i, off, lift=0.0):
        p = self.pos[i]
        r = self.right[i]
        return (p[0] + r[0] * off, p[1] + off * self.bank[i] + lift, p[2] + r[2] * off)

    def nearest(self, x, z, hint=None, window=40):
        if hint is None:
            d = (self.pos[:, 0] - x) ** 2 + (self.pos[:, 2] - z) ** 2
            i = int(np.argmin(d))
        else:
            idx = (np.arange(hint - window, hint + window + 1)) % self.n
            d = (self.pos[idx, 0] - x) ** 2 + (self.pos[idx, 2] - z) ** 2
            i = int(idx[int(np.argmin(d))])
        px, py, pz = self.pos[i]
        fx, fz = self.fwd[i, 0], self.fwd[i, 2]
        rx, rz = self.right[i, 0], self.right[i, 2]
        dx, dz = x - px, z - pz
        along = dx * fx + dz * fz
        lateral = dx * rx + dz * rz
        return i, lateral, along

    def height(self, i, lateral, along=0.0):
        j = (i + (1 if along >= 0 else -1)) % self.n
        t = min(1.0, abs(along) / self.step)
        y0 = self.pos[i, 1] + lateral * self.bank[i]
        y1 = self.pos[j, 1] + lateral * self.bank[j]
        return y0 + (y1 - y0) * t

    def progress(self, i, along):
        return i * self.step + along

    def build_road(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, gfx.image("road.jpg"))
        glColor4f(1, 1, 1, 1)
        glNormal3f(0, 1, 0)
        glBegin(GL_QUADS)
        tex_len = 28.0
        for i in range(self.n):
            j = (i + 1) % self.n
            v0 = self.dist[i] / tex_len
            v1 = (self.dist[i] + self.step) / tex_len
            for (a0, a1, u0, u1) in ((-ROAD_HALF, 0.0, 0.0, 0.5), (0.0, ROAD_HALF, 0.5, 1.0)):
                glNormal3f(self.right[i, 0] * -self.bank[i], 1, self.right[i, 2] * -self.bank[i])
                glTexCoord2f(u0, v0)
                glVertex3f(*self.edge(i, a0))
                glTexCoord2f(u1, v0)
                glVertex3f(*self.edge(i, a1))
                glTexCoord2f(u1, v1)
                glVertex3f(*self.edge(j, a1))
                glTexCoord2f(u0, v1)
                glVertex3f(*self.edge(j, a0))
        glEnd()
        glBindTexture(GL_TEXTURE_2D, gfx.image("curb.jpg"))
        glBegin(GL_QUADS)
        for i in range(self.n):
            if not self.curb[i]:
                continue
            j = (i + 1) % self.n
            v0 = self.dist[i] / 4.0
            v1 = (self.dist[i] + self.step) / 4.0
            for side in (-1, 1):
                a0 = side * ROAD_HALF
                a1 = side * (ROAD_HALF + CURB_W)
                pts = [(a0, 0.02, 0.0), (a1, 0.07, 1.0)]
                if side < 0:
                    pts = pts[::-1]
                (b0, l0, u0), (b1, l1, u1) = pts
                glNormal3f(0, 1, 0)
                glTexCoord2f(u0, v0)
                glVertex3f(*self.edge(i, b0, l0))
                glTexCoord2f(u1, v0)
                glVertex3f(*self.edge(i, b1, l1))
                glTexCoord2f(u1, v1)
                glVertex3f(*self.edge(j, b1, l1))
                glTexCoord2f(u0, v1)
                glVertex3f(*self.edge(j, b0, l0))
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        i0 = 0
        for k in range(2):
            for c in range(14):
                white = (c + k) % 2 == 0
                glColor4f(*((0.95, 0.95, 0.95, 1) if white else (0.08, 0.08, 0.08, 1)))
                a0 = -ROAD_HALF + c * (2 * ROAD_HALF / 14)
                a1 = a0 + 2 * ROAD_HALF / 14
                fx, fz = self.fwd[i0, 0], self.fwd[i0, 2]
                base0 = self.edge(i0, a0, 0.03)
                base1 = self.edge(i0, a1, 0.03)
                d0 = k * 1.0 - 1.0
                d1 = d0 + 1.0
                glVertex3f(base0[0] + fx * d0, base0[1], base0[2] + fz * d0)
                glVertex3f(base1[0] + fx * d0, base1[1], base1[2] + fz * d0)
                glVertex3f(base1[0] + fx * d1, base1[1], base1[2] + fz * d1)
                glVertex3f(base0[0] + fx * d1, base0[1], base0[2] + fz * d1)
        glEnd()
        glColor4f(1, 1, 1, 1)

    def build_walls(self):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, gfx.image("kerb.jpg"))
        glColor4f(1, 1, 1, 1)
        h = 0.32
        glBegin(GL_QUADS)
        for i in range(self.n):
            j = (i + 1) % self.n
            u0 = self.dist[i] / 4.0
            u1 = (self.dist[i] + self.step) / 4.0
            for side in (-1, 1):
                off = side * WALL_DIST
                bi = self.edge(i, off, -0.05)
                bj = self.edge(j, off, -0.05)
                ti = (bi[0], bi[1] + h + 0.05, bi[2])
                tj = (bj[0], bj[1] + h + 0.05, bj[2])
                nx, nz = -self.right[i, 0] * side, -self.right[i, 2] * side
                glNormal3f(nx, 0.15, nz)
                quad = [(u0, 0.0, bi), (u1, 0.0, bj), (u1, 1.0, tj), (u0, 1.0, ti)]
                if side > 0:
                    quad = [(-u0, 0.0, bi), (-u0, 1.0, ti), (-u1, 1.0, tj), (-u1, 0.0, bj)]
                for u, v, p in quad:
                    glTexCoord2f(u, v)
                    glVertex3f(*p)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        glColor4f(0.62, 0.62, 0.64, 1)
        glNormal3f(0, 1, 0)
        for i in range(self.n):
            j = (i + 1) % self.n
            for side in (-1, 1):
                off = side * WALL_DIST
                a = self.edge(i, off, h)
                b = self.edge(j, off, h)
                c = self.edge(j, off + side * 0.3, h)
                d = self.edge(i, off + side * 0.3, h)
                quad = [a, b, c, d] if side < 0 else [d, c, b, a]
                for p in quad:
                    glVertex3f(*p)
        glEnd()
        glColor4f(1, 1, 1, 1)

    def draw(self):
        if "road" not in self.lists:
            for key, fn in (("road", self.build_road), ("walls", self.build_walls)):
                lid = glGenLists(1)
                glNewList(lid, GL_COMPILE)
                fn()
                glEndList()
                self.lists[key] = lid
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-1.0, -2.0)
        glCallList(self.lists["road"])
        glDisable(GL_POLYGON_OFFSET_FILL)
        glCallList(self.lists["walls"])

    def minimap_points(self, count=220):
        idx = np.linspace(0, self.n, count, endpoint=False).astype(int)
        return [(self.pos[i, 0], self.pos[i, 2]) for i in idx]
