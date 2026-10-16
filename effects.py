import math
import random

from OpenGL.GL import *

import gfx


class Effects:
    def __init__(self):
        self.parts = []
        self.skids = []
        self.last_skid = {}

    def clear(self):
        self.parts.clear()
        self.skids.clear()
        self.last_skid.clear()

    def add(self, kind, x, y, z, vx, vy, vz, life, size, grow, color, alpha):
        if len(self.parts) < 700:
            self.parts.append([kind, x, y, z, vx, vy, vz, life, life, size, grow, color, alpha])

    def smoke(self, x, y, z, vx, vz, amount=1.0, color=(0.82, 0.82, 0.84)):
        self.add("smoke", x + random.uniform(-0.2, 0.2), y + 0.25, z + random.uniform(-0.2, 0.2),
                 vx * 0.25 + random.uniform(-0.8, 0.8), random.uniform(0.6, 1.6), vz * 0.25 + random.uniform(-0.8, 0.8),
                 random.uniform(1.0, 1.8), random.uniform(0.6, 1.0), 2.2, color, 0.45 * amount)

    def dust(self, x, y, z, vx, vz, color=(0.62, 0.52, 0.38)):
        self.add("smoke", x, y + 0.2, z, vx * 0.3 + random.uniform(-1, 1), random.uniform(0.5, 1.4), vz * 0.3 + random.uniform(-1, 1),
                 random.uniform(0.7, 1.2), random.uniform(0.5, 0.9), 2.2, color, 0.26)

    def sparks(self, x, y, z, n=10):
        for _ in range(n):
            self.add("spark", x, y + 0.4, z, random.uniform(-6, 6), random.uniform(1, 5), random.uniform(-6, 6),
                     random.uniform(0.2, 0.5), 0.18, 0.0, (1.0, 0.8, 0.35), 1.0)

    def flame(self, x, y, z, vx, vz):
        self.add("flame", x, y, z, vx * 0.8 + random.uniform(-0.5, 0.5), random.uniform(-0.2, 0.3), vz * 0.8 + random.uniform(-0.5, 0.5),
                 random.uniform(0.08, 0.16), random.uniform(0.35, 0.55), -1.5, (1.0, 0.55, 0.15), 1.0)

    def skid(self, key, x, y, z, active, width=0.24):
        last = self.last_skid.get(key)
        if not active:
            self.last_skid.pop(key, None)
            return
        if last is not None:
            lx, ly, lz = last
            if (x - lx) ** 2 + (z - lz) ** 2 < 0.25:
                return
            dx, dz = x - lx, z - lz
            ln = math.hypot(dx, dz) or 1
            nx, nz = -dz / ln * width, dx / ln * width
            self.skids.append((lx - nx, ly, lz - nz, lx + nx, lz + nz, x + nx, y, z + nz, x - nx, z - nz))
            if len(self.skids) > 1800:
                del self.skids[:300]
        self.last_skid[key] = (x, y + 0.03, z)

    def update(self, dt):
        keep = []
        for p in self.parts:
            p[7] -= dt
            if p[7] <= 0:
                continue
            if p[0] == "spark":
                p[5] -= 9.8 * dt
            else:
                p[4] *= 1 - 1.2 * dt
                p[6] *= 1 - 1.2 * dt
            p[1] += p[4] * dt
            p[2] += p[5] * dt
            p[3] += p[6] * dt
            p[9] += p[10] * dt
            keep.append(p)
        self.parts = keep

    def draw_skids(self):
        if not self.skids:
            return
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-2.0, -4.0)
        glColor4f(0.05, 0.05, 0.05, 0.32)
        glBegin(GL_QUADS)
        for ax, ay, az, bx, bz, cx, cy, cz, dx, dz in self.skids:
            glVertex3f(ax, ay, az)
            glVertex3f(bx, ay, bz)
            glVertex3f(cx, cy, cz)
            glVertex3f(dx, cy, dz)
        glEnd()
        glDisable(GL_POLYGON_OFFSET_FILL)
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)

    def draw(self):
        if not self.parts:
            return
        m = glGetFloatv(GL_MODELVIEW_MATRIX)
        rx, ry, rz = m[0][0], m[1][0], m[2][0]
        ux, uy, uz = m[0][1], m[1][1], m[2][1]
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glEnable(GL_TEXTURE_2D)
        glDisable(GL_CULL_FACE)
        for mode, tex, additive in (("smoke", "smoke", False), ("glow", "glow", True)):
            glBindTexture(GL_TEXTURE_2D, gfx.texture(tex))
            glBlendFunc(GL_SRC_ALPHA, GL_ONE if additive else GL_ONE_MINUS_SRC_ALPHA)
            glBegin(GL_QUADS)
            for kind, x, y, z, vx, vy, vz, life, mx, size, grow, col, alpha in self.parts:
                if (kind == "smoke") != (mode == "smoke"):
                    continue
                f = life / mx
                a = alpha * (f if kind != "smoke" else min(1.0, f * 1.5) * min(1.0, (1 - f) * 6 + 0.2))
                s = size
                glColor4f(col[0], col[1], col[2], a)
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
