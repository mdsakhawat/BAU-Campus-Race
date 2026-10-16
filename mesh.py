import math

import numpy as np
from OpenGL.GL import *

WHITE = (1.0, 1.0, 1.0, 1.0)


class Mesh:
    def __init__(self):
        self.v = []
        self.n = []
        self.t = []
        self.c = []

    def __len__(self):
        return len(self.v)

    def tri(self, a, b, c, n, ta=(0, 0), tb=(0, 0), tc=(0, 0), col=WHITE):
        self.v.extend((a, b, c))
        self.n.extend((n, n, n))
        self.t.extend((ta, tb, tc))
        self.c.extend((col, col, col))

    def quad(self, a, b, c, d, n=None, uv=((0, 0), (1, 0), (1, 1), (0, 1)), col=WHITE):
        if n is None:
            n = face_normal(a, b, c)
        self.v.extend((a, b, c, a, c, d))
        self.n.extend((n,) * 6)
        self.t.extend((uv[0], uv[1], uv[2], uv[0], uv[2], uv[3]))
        self.c.extend((col,) * 6)

    def quad_cols(self, a, b, c, d, cols, n=None, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
        if n is None:
            n = face_normal(a, b, c)
        self.v.extend((a, b, c, a, c, d))
        self.n.extend((n,) * 6)
        self.t.extend((uv[0], uv[1], uv[2], uv[0], uv[2], uv[3]))
        self.c.extend((cols[0], cols[1], cols[2], cols[0], cols[2], cols[3]))

    def floor_rect(self, x0, z0, x1, z1, y, scale=None, col=WHITE, uv_off=(0, 0)):
        if scale:
            uv = ((x0 / scale + uv_off[0], z0 / scale + uv_off[1]), (x1 / scale + uv_off[0], z0 / scale + uv_off[1]),
                  (x1 / scale + uv_off[0], z1 / scale + uv_off[1]), (x0 / scale + uv_off[0], z1 / scale + uv_off[1]))
        else:
            uv = ((0, 0), (1, 0), (1, 1), (0, 1))
        self.quad((x0, y, z0), (x0, y, z1), (x1, y, z1), (x1, y, z0), (0, 1, 0), (uv[0], uv[3], uv[2], uv[1]), col)

    def wall(self, x0, z0, x1, z1, y0, y1, u0=0.0, u1=1.0, v0=0.0, v1=1.0, col=WHITE, cols=None):
        dx, dz = x1 - x0, z1 - z0
        ln = math.hypot(dx, dz) or 1.0
        n = (-dz / ln, 0.0, dx / ln)
        a, b, c, d = (x0, y0, z0), (x1, y0, z1), (x1, y1, z1), (x0, y1, z0)
        uv = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        if cols:
            self.quad_cols(a, b, c, d, cols, n, uv)
        else:
            self.quad(a, b, c, d, n, uv, col)

    def box(self, x0, y0, z0, x1, y1, z1, col=WHITE, top=True, bottom=False, uv_scale=None):
        def uvw(a, b, h0, h1):
            if uv_scale:
                return a / uv_scale, b / uv_scale, h0 / uv_scale, h1 / uv_scale
            return 0.0, 1.0, 0.0, 1.0
        u0, u1, v0, v1 = uvw(x0, x1, y0, y1)
        self.wall(x1, z0, x0, z0, y0, y1, u0, u1, v0, v1, col)
        self.wall(x0, z1, x1, z1, y0, y1, u0, u1, v0, v1, col)
        u0, u1, v0, v1 = uvw(z0, z1, y0, y1)
        self.wall(x0, z0, x0, z1, y0, y1, u0, u1, v0, v1, col)
        self.wall(x1, z1, x1, z0, y0, y1, u0, u1, v0, v1, col)
        if top:
            self.floor_rect(x0, z0, x1, z1, y1, uv_scale, col)
        if bottom:
            self.quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0), col=col)

    def obox(self, cx, cy, cz, hw, h, hd, fx, fz, col=WHITE, top=True):
        rx, rz = -fz, fx

        def P(a, b, c):
            return (cx + rx * a + fx * c, cy + b, cz + rz * a + fz * c)
        pts = [P(-hw, 0, -hd), P(hw, 0, -hd), P(hw, 0, hd), P(-hw, 0, hd)]
        top_pts = [P(-hw, h, -hd), P(hw, h, -hd), P(hw, h, hd), P(-hw, h, hd)]
        for k in range(4):
            a, b = pts[k], pts[(k + 1) % 4]
            ta, tb = top_pts[k], top_pts[(k + 1) % 4]
            self.quad(a, b, tb, ta, col=col)
        if top:
            self.quad(top_pts[0], top_pts[1], top_pts[2], top_pts[3], (0, 1, 0), col=col)

    def cylinder(self, cx, y0, cz, r, h, seg=12, col=WHITE, top=True, r_top=None):
        rt = r if r_top is None else r_top
        for k in range(seg):
            a0 = 2 * math.pi * k / seg
            a1 = 2 * math.pi * (k + 1) / seg
            c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
            n = (math.cos((a0 + a1) / 2), 0, math.sin((a0 + a1) / 2))
            self.quad((cx + c0 * r, y0, cz + s0 * r), (cx + c0 * rt, y0 + h, cz + s0 * rt), (cx + c1 * rt, y0 + h, cz + s1 * rt),
                      (cx + c1 * r, y0, cz + s1 * r), n, col=col)
            if top and rt > 0:
                self.tri((cx, y0 + h, cz), (cx + c1 * rt, y0 + h, cz + s1 * rt), (cx + c0 * rt, y0 + h, cz + s0 * rt), (0, 1, 0), col=col)

    def dome(self, cx, y0, cz, r, seg=14, rings=6, col=WHITE, squash=1.0):
        for i in range(rings):
            p0 = math.pi / 2 * i / rings
            p1 = math.pi / 2 * (i + 1) / rings
            for k in range(seg):
                a0 = 2 * math.pi * k / seg
                a1 = 2 * math.pi * (k + 1) / seg
                pts = []
                for p, a in ((p0, a0), (p1, a0), (p1, a1), (p0, a1)):
                    pts.append((cx + math.cos(a) * math.cos(p) * r, y0 + math.sin(p) * r * squash, cz + math.sin(a) * math.cos(p) * r))
                n = (math.cos((a0 + a1) / 2) * math.cos(p0), math.sin(p0), math.sin((a0 + a1) / 2) * math.cos(p0))
                self.quad(pts[0], pts[1], pts[2], pts[3], n, col=col)

    def merge(self, other):
        self.v.extend(other.v)
        self.n.extend(other.n)
        self.t.extend(other.t)
        self.c.extend(other.c)

    def compile(self, colors=True):
        if not self.v:
            return None
        v = np.ascontiguousarray(np.array(self.v, dtype=np.float32))
        n = np.ascontiguousarray(np.array(self.n, dtype=np.float32))
        t = np.ascontiguousarray(np.array(self.t, dtype=np.float32))
        lid = glGenLists(1)
        glNewList(lid, GL_COMPILE)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, v)
        glNormalPointer(GL_FLOAT, 0, n)
        glTexCoordPointer(2, GL_FLOAT, 0, t)
        if colors:
            c = np.ascontiguousarray(np.array(self.c, dtype=np.float32))
            glEnableClientState(GL_COLOR_ARRAY)
            glColorPointer(4, GL_FLOAT, 0, c)
        glDrawArrays(GL_TRIANGLES, 0, len(v))
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        if colors:
            glDisableClientState(GL_COLOR_ARRAY)
        glEndList()
        return lid


class Lines:
    def __init__(self):
        self.v = []
        self.c = []

    def __len__(self):
        return len(self.v)

    def seg(self, a, b, col):
        self.v.extend((a, b))
        self.c.extend((col, col))

    def compile(self, width=1.0):
        if not self.v:
            return None
        v = np.ascontiguousarray(np.array(self.v, dtype=np.float32))
        c = np.ascontiguousarray(np.array(self.c, dtype=np.float32))
        lid = glGenLists(1)
        glNewList(lid, GL_COMPILE)
        glLineWidth(width)
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, v)
        glColorPointer(4, GL_FLOAT, 0, c)
        glDrawArrays(GL_LINES, 0, len(v))
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glLineWidth(1.0)
        glEndList()
        return lid


def face_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / ln, ny / ln, nz / ln)


def quad_out(m, pts, normal, col=WHITE, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    fn = face_normal(pts[0], pts[1], pts[2])
    if fn[0] * normal[0] + fn[1] * normal[1] + fn[2] * normal[2] < 0:
        pts = [pts[0], pts[3], pts[2], pts[1]]
        uv = (uv[0], uv[3], uv[2], uv[1])
    m.quad(pts[0], pts[1], pts[2], pts[3], None, uv, col)


def beam(m, a, b, w, col=WHITE, d=None):
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    dx, dy, dz = dx / L, dy / L, dz / L
    up = (0.0, 1.0, 0.0) if abs(dy) < 0.9 else (1.0, 0.0, 0.0)
    ux, uy, uz = dy * up[2] - dz * up[1], dz * up[0] - dx * up[2], dx * up[1] - dy * up[0]
    ul = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
    ux, uy, uz = ux / ul, uy / ul, uz / ul
    vx, vy, vz = uy * dz - uz * dy, uz * dx - ux * dz, ux * dy - uy * dx
    w2 = w / 2
    d2 = (d if d is not None else w) / 2

    def P(p, su, sv):
        return (p[0] + ux * su * w2 + vx * sv * d2, p[1] + uy * su * w2 + vy * sv * d2, p[2] + uz * su * w2 + vz * sv * d2)
    for su, sv, n in ((1, 0, (ux, uy, uz)), (-1, 0, (-ux, -uy, -uz)), (0, 1, (vx, vy, vz)), (0, -1, (-vx, -vy, -vz))):
        if su:
            pts = [P(a, su, -1), P(b, su, -1), P(b, su, 1), P(a, su, 1)]
        else:
            pts = [P(a, -1, sv), P(b, -1, sv), P(b, 1, sv), P(a, 1, sv)]
        quad_out(m, pts, n, col)
    quad_out(m, [P(b, -1, -1), P(b, 1, -1), P(b, 1, 1), P(b, -1, 1)], (dx, dy, dz), col)
    quad_out(m, [P(a, -1, -1), P(a, 1, -1), P(a, 1, 1), P(a, -1, 1)], (-dx, -dy, -dz), col)


def disc(m, cx, cy, cz, r, normal, col=WHITE, seg=24, axis="z"):
    pts = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        if axis == "z":
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, cz))
        elif axis == "x":
            pts.append((cx, cy + math.sin(a) * r, cz + math.cos(a) * r))
        else:
            pts.append((cx + math.cos(a) * r, cy, cz + math.sin(a) * r))
    for k in range(seg):
        a, b = pts[k], pts[(k + 1) % seg]
        fn = face_normal((cx, cy, cz), a, b)
        if fn[0] * normal[0] + fn[1] * normal[1] + fn[2] * normal[2] < 0:
            a, b = b, a
        m.tri((cx, cy, cz), a, b, normal, col=col)
