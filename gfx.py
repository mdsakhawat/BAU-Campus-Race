import math
import os
from collections import OrderedDict

import pygame
from pygame.locals import OPENGL, DOUBLEBUF, FULLSCREEN, RESIZABLE
from OpenGL.GL import *
import numpy as np

from config import VW, VH, TITLE
from mathutils import lerp_color

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ANISO = 0x84FE
display = None
_image_data = {}
_textures = {}
_text_cache = OrderedDict()
_fonts = {}
_circles = {}
reset_hooks = []


def circle_table(seg):
    if seg not in _circles:
        _circles[seg] = [(math.cos(2 * math.pi * i / seg), math.sin(2 * math.pi * i / seg)) for i in range(seg + 1)]
    return _circles[seg]


class Display:
    def __init__(self, fullscreen=False):
        global display
        display = self
        self.fullscreen = fullscreen
        self.window_size = (VW, VH)
        self.w, self.h = VW, VH
        self.scale, self.ox, self.oy = 1.0, 0, 0
        self.apply()

    def apply(self):
        flags = OPENGL | DOUBLEBUF
        if self.fullscreen:
            try:
                size = pygame.display.get_desktop_sizes()[0]
            except (AttributeError, IndexError, pygame.error):
                size = (0, 0)
            flags |= FULLSCREEN
        else:
            size = self.window_size
            flags |= RESIZABLE
        surface = None
        for samples in (4, 0):
            try:
                pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
                pygame.display.gl_set_attribute(pygame.GL_STENCIL_SIZE, 8)
                pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1 if samples else 0)
                pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, samples)
                surface = pygame.display.set_mode(size, flags)
                break
            except pygame.error:
                if samples == 0:
                    raise
                pygame.display.quit()
                pygame.display.init()
        pygame.display.set_caption(TITLE)
        if self.fullscreen:
            try:
                self.w, self.h = pygame.display.get_window_size()
            except (AttributeError, pygame.error):
                self.w, self.h = surface.get_size()
        else:
            self.w, self.h = self.window_size
        self.stencil = glGetIntegerv(GL_STENCIL_BITS) > 0
        reset_resources()
        self.setup()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.apply()

    def resize(self, w, h):
        if self.fullscreen:
            return
        self.window_size = (max(320, w), max(180, h))
        self.w, self.h = self.window_size
        self.setup()

    def setup(self):
        self.scale = min(self.w / VW, self.h / VH)
        vw, vh = int(VW * self.scale), int(VH * self.scale)
        self.ox, self.oy = (self.w - vw) // 2, (self.h - vh) // 2
        self.vw, self.vh = vw, vh
        glViewport(self.ox, self.oy, vw, vh)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        try:
            glEnable(GL_MULTISAMPLE)
        except Exception:
            pass

    @property
    def text_scale(self):
        return max(1.0, round(self.scale * 4) / 4)

    def to_virtual(self, px, py):
        x = (px - self.ox) / self.scale
        y = VH - (py - self.oy) / self.scale
        return x, y

    def begin_frame(self, color=(0, 0, 0)):
        glViewport(0, 0, self.w, self.h)
        glClearColor(0, 0, 0, 1)
        glClearStencil(0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
        glViewport(self.ox, self.oy, self.vw, self.vh)


def perspective(fov, aspect, near, far):
    f = near * math.tan(math.radians(fov) / 2)
    glFrustum(-f * aspect, f * aspect, -f, f, near, far)


def look_at(eye, center, up=(0, 1, 0)):
    e = np.array(eye, dtype=np.float64)
    fwd = np.array(center, dtype=np.float64) - e
    fwd /= np.linalg.norm(fwd)
    side = np.cross(fwd, np.array(up, dtype=np.float64))
    side /= np.linalg.norm(side)
    u = np.cross(side, fwd)
    m = np.identity(4)
    m[0, :3] = side
    m[1, :3] = u
    m[2, :3] = -fwd
    glMultMatrixd(m.T.flatten())
    glTranslated(-e[0], -e[1], -e[2])


def begin_3d(fov, near=0.3, far=3000.0):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    perspective(fov, VW / VH, near, far)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glDepthMask(GL_TRUE)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glShadeModel(GL_SMOOTH)


def begin_2d():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, VW, 0, VH, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)
    glDisable(GL_LIGHTING)
    glDisable(GL_FOG)
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_ALPHA_TEST)
    glDisable(GL_STENCIL_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDepthMask(GL_TRUE)


def reset_resources():
    _textures.clear()
    _text_cache.clear()
    for fn in reset_hooks:
        fn()


def make_texture(width, height, data, smooth=True, repeat=False):
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    mode = GL_LINEAR if smooth else GL_NEAREST
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, mode)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, mode)
    wrap = GL_REPEAT if repeat else GL_CLAMP_TO_EDGE
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tex


def texture(name):
    if name not in _textures:
        size = 64
        buf = bytearray(size * size * 4)
        for j in range(size):
            for i in range(size):
                dx = (i + 0.5) / size * 2 - 1
                dy = (j + 0.5) / size * 2 - 1
                d = math.sqrt(dx * dx + dy * dy)
                if name == "vignette":
                    a = min(1.0, max(0.0, (d - 0.55) / 0.85)) ** 1.6
                elif name == "glow":
                    a = max(0.0, 1 - d) ** 2
                elif name == "soft":
                    a = max(0.0, 1 - d) ** 0.8
                elif name == "smoke":
                    a = max(0.0, 1 - d) ** 1.4 * (0.75 + 0.25 * math.sin(i * 0.7) * math.cos(j * 0.6))
                elif name == "beam":
                    u = (i + 0.5) / size
                    v = (j + 0.5) / size
                    spread = 0.10 + 0.40 * v
                    side = max(0.0, 1 - abs(u - 0.5) / spread)
                    a = side ** 1.2 * (1 - v) ** 0.8 * min(1.0, v * 5)
                elif name == "pool":
                    a = max(0.0, 1 - d) ** 1.6
                elif name == "streak":
                    u = (i + 0.5) / size
                    a = max(0.0, 1 - abs(u - 0.5) * 2) ** 2 * max(0.0, 1 - abs((j + 0.5) / size - 0.5) * 2) ** 0.5
                else:
                    a = max(0.0, min(1.0, (1 - d) * 6)) * max(0.0, min(1.0, (d - 0.72) * 8))
                k = (j * size + i) * 4
                buf[k:k + 4] = bytes((255, 255, 255, int(max(0.0, a) * 255)))
        _textures[name] = make_texture(size, size, bytes(buf))
    return _textures[name]


def load_image_data(path):
    if path not in _image_data:
        surf = pygame.image.load(os.path.join(ASSET_DIR, path))
        _image_data[path] = (surf.get_width(), surf.get_height(), pygame.image.tobytes(surf, "RGBA", True))
    return _image_data[path]


def image(path, repeat=True, mipmap=True):
    key = "img:" + path
    if key not in _textures:
        w, h, data = load_image_data(path)
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        wrap = GL_REPEAT if repeat else GL_CLAMP_TO_EDGE
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        if mipmap:
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            level = 0
            arr = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 4).astype(np.float32)
            while True:
                lh, lw = arr.shape[:2]
                glTexImage2D(GL_TEXTURE_2D, level, GL_RGBA, lw, lh, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                             np.ascontiguousarray(arr.astype(np.uint8)).tobytes())
                if lw == 1 and lh == 1:
                    break
                if lh > 1:
                    arr = arr[:lh - lh % 2]
                    arr = (arr[0::2] + arr[1::2]) / 2
                if lw > 1:
                    arr = arr[:, :lw - lw % 2]
                    arr = (arr[:, 0::2] + arr[:, 1::2]) / 2
                level += 1
            try:
                glTexParameterf(GL_TEXTURE_2D, ANISO, 8.0)
            except Exception:
                pass
        else:
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        _textures[key] = tex
    return _textures[key]


def bind(path, repeat=True, mipmap=True):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, image(path, repeat, mipmap))


def image_quad(path, x, y, w, h, alpha=1.0, color=(1, 1, 1)):
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, image(path, repeat=False, mipmap=True))
    glColor4f(color[0], color[1], color[2], alpha)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y)
    glTexCoord2f(1, 0); glVertex2f(x + w, y)
    glTexCoord2f(1, 1); glVertex2f(x + w, y + h)
    glTexCoord2f(0, 1); glVertex2f(x, y + h)
    glEnd()
    glDisable(GL_TEXTURE_2D)


def image_size(path):
    w, h, _ = load_image_data(path)
    return w, h


def label(path, x, y, height, alpha=1.0, align="left", shadow=True, color=(1, 1, 1)):
    w, h = image_size(path)
    ww = height * w / h
    if align == "center":
        x -= ww / 2
    elif align == "right":
        x -= ww
    if shadow:
        image_quad(path, x + height * 0.04, y - height * 0.04, ww, height, alpha * 0.6, (0, 0, 0))
    image_quad(path, x, y, ww, height, alpha, color)
    return ww


def sprites(items, tex="glow", additive=True):
    if not items:
        return
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture(tex))
    if additive:
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glBegin(GL_QUADS)
    for x, y, w, h, ang, r, g, b, a in items:
        glColor4f(r, g, b, a)
        hw, hh = w / 2, h / 2
        if ang:
            c, s = math.cos(ang), math.sin(ang)
            ux, uy, vx, vy = c * hw, s * hw, -s * hh, c * hh
            glTexCoord2f(0, 0); glVertex2f(x - ux - vx, y - uy - vy)
            glTexCoord2f(1, 0); glVertex2f(x + ux - vx, y + uy - vy)
            glTexCoord2f(1, 1); glVertex2f(x + ux + vx, y + uy + vy)
            glTexCoord2f(0, 1); glVertex2f(x - ux + vx, y - uy + vy)
        else:
            glTexCoord2f(0, 0); glVertex2f(x - hw, y - hh)
            glTexCoord2f(1, 0); glVertex2f(x + hw, y - hh)
            glTexCoord2f(1, 1); glVertex2f(x + hw, y + hh)
            glTexCoord2f(0, 1); glVertex2f(x - hw, y + hh)
    glEnd()
    if additive:
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_TEXTURE_2D)


def glow(x, y, size, color, alpha=1.0, stretch=1.0, angle=0.0):
    return (x, y, size * stretch, size, angle, color[0], color[1], color[2], alpha)


FONTS = {
    "regular": ("segoeui,helveticaneue,arial,dejavusans", False),
    "bold": ("segoeuisemibold,segoeui,arial,dejavusans", True),
    "light": ("segoeuilight,segoeui,helveticaneue,arial,dejavusans", False),
}


def get_font(px, style="regular"):
    key = (px, style)
    if key not in _fonts:
        names, bold = FONTS[style]
        _fonts[key] = pygame.font.SysFont(names, px, bold=bold)
    return _fonts[key]


def text_texture(s, size, color, style="regular"):
    px = max(8, int(round(size * (display.text_scale if display else 1.0))))
    key = (s, px, color, style)
    if key in _text_cache:
        _text_cache.move_to_end(key)
        return _text_cache[key]
    surf = get_font(px, style).render(s, True, color)
    w, h = surf.get_size()
    tex = make_texture(w, h, pygame.image.tobytes(surf, "RGBA", True))
    entry = (tex, w * size / px, h * size / px)
    _text_cache[key] = entry
    if len(_text_cache) > 500:
        _, old = _text_cache.popitem(last=False)
        try:
            glDeleteTextures([old[0]])
        except Exception:
            pass
    return entry


def text_width(s, size, style="regular"):
    return text_texture(s, size, (255, 255, 255), style)[1]


def text(s, x, y, size=24, color=(255, 255, 255), align="left", alpha=1.0, shadow=False, style="regular"):
    if not s:
        return 0
    tex, w, h = text_texture(s, size, color, style)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex)
    passes = []
    if shadow:
        off = max(1.0, size / 16)
        passes.append((off, -off, (0, 0, 0, 0.55 * alpha)))
    passes.append((0, 0, (1, 1, 1, alpha)))
    for dx, dy, col in passes:
        glColor4f(*col)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x + dx, y + dy)
        glTexCoord2f(1, 0); glVertex2f(x + w + dx, y + dy)
        glTexCoord2f(1, 1); glVertex2f(x + w + dx, y + h + dy)
        glTexCoord2f(0, 1); glVertex2f(x + dx, y + h + dy)
        glEnd()
    glDisable(GL_TEXTURE_2D)
    return w


def disc(cx, cy, r, color, rim=None, seg=20):
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(*color)
    glVertex2f(cx, cy)
    glColor4f(*(rim or color))
    for c, s in circle_table(seg):
        glVertex2f(cx + r * c, cy + r * s)
    glEnd()


def ring(cx, cy, r, color, width=2.0, seg=32):
    glLineWidth(width)
    glColor4f(*color)
    glBegin(GL_LINE_LOOP)
    for c, s in circle_table(seg)[:-1]:
        glVertex2f(cx + r * c, cy + r * s)
    glEnd()
    glLineWidth(1)


def thick_ring(cx, cy, r, w, color, seg=40, outer=None):
    glBegin(GL_TRIANGLE_STRIP)
    for c, s in circle_table(seg):
        glColor4f(*color)
        glVertex2f(cx + (r - w / 2) * c, cy + (r - w / 2) * s)
        glColor4f(*(outer or color))
        glVertex2f(cx + (r + w / 2) * c, cy + (r + w / 2) * s)
    glEnd()


def ellipse(rx, ry, color, inner=None, seg=18):
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(*(inner or color))
    glVertex2f(0, 0)
    glColor4f(*color)
    for c, s in circle_table(seg):
        glVertex2f(rx * c, ry * s)
    glEnd()


def ellipse_at(x, y, rx, ry, angle, color, inner=None, seg=18):
    glPushMatrix()
    glTranslatef(x, y, 0)
    if angle:
        glRotatef(angle, 0, 0, 1)
    ellipse(rx, ry, color, inner, seg)
    glPopMatrix()


def rect(x, y, w, h, c_bottom, c_top=None):
    glBegin(GL_QUADS)
    glColor4f(*c_bottom)
    glVertex2f(x, y)
    glVertex2f(x + w, y)
    glColor4f(*(c_top or c_bottom))
    glVertex2f(x + w, y + h)
    glVertex2f(x, y + h)
    glEnd()


def rect_h(x, y, w, h, c_left, c_right):
    glBegin(GL_QUADS)
    glColor4f(*c_left)
    glVertex2f(x, y)
    glColor4f(*c_right)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glColor4f(*c_left)
    glVertex2f(x, y + h)
    glEnd()


CORNERS = [(math.cos(math.radians(a0 + i * 15)), math.sin(math.radians(a0 + i * 15)), sx, sy)
           for sx, sy, a0 in ((1, 0, -90), (1, 1, 0), (0, 1, 90), (0, 0, 180)) for i in range(7)]


def rounded_rect(x, y, w, h, r, color, color_top=None, outline=False, width=2):
    r = max(0.0, min(r, w / 2, h / 2))
    if outline:
        glLineWidth(width)
        glBegin(GL_LINE_LOOP)
    else:
        glBegin(GL_POLYGON)
    if color_top and h:
        c0, c1 = color, color_top
        dr, dg, db, da = c1[0] - c0[0], c1[1] - c0[1], c1[2] - c0[2], c1[3] - c0[3]
        for cx, cy, sx, sy in CORNERS:
            py = (y + h - r if sy else y + r) + r * cy
            k = (py - y) / h
            glColor4f(c0[0] + dr * k, c0[1] + dg * k, c0[2] + db * k, c0[3] + da * k)
            glVertex2f((x + w - r if sx else x + r) + r * cx, py)
    else:
        glColor4f(*color)
        for cx, cy, sx, sy in CORNERS:
            glVertex2f((x + w - r if sx else x + r) + r * cx, (y + h - r if sy else y + r) + r * cy)
    glEnd()
    glLineWidth(1)


def polygon(points, color, center_color=None):
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(*(center_color or color))
    glVertex2f(cx, cy)
    glColor4f(*color)
    for x, y in points:
        glVertex2f(x, y)
    glVertex2f(*points[0])
    glEnd()


def poly_gradient(points, colors):
    glBegin(GL_POLYGON)
    for (x, y), c in zip(points, colors):
        glColor4f(*c)
        glVertex2f(x, y)
    glEnd()


def outline(points, color, width=1.5, closed=True):
    glLineWidth(width)
    glColor4f(*color)
    glBegin(GL_LINE_LOOP if closed else GL_LINE_STRIP)
    for x, y in points:
        glVertex2f(x, y)
    glEnd()
    glLineWidth(1)


def thick_line(points, width, color, color_end=None):
    n = len(points)
    if n < 2:
        return
    glBegin(GL_TRIANGLE_STRIP)
    for i, (x, y) in enumerate(points):
        nx, ny = points[min(i + 1, n - 1)]
        px, py = points[max(i - 1, 0)]
        dx, dy = nx - px, ny - py
        length = math.hypot(dx, dy) or 1
        ox, oy = -dy / length * width / 2, dx / length * width / 2
        glColor4f(*(lerp_color(color, color_end, i / (n - 1)) if color_end else color))
        glVertex2f(x + ox, y + oy)
        glVertex2f(x - ox, y - oy)
    glEnd()


def star_shape(x, y, r, color, rim=None, points=5, inner=0.45):
    pts = []
    for i in range(points * 2):
        a = math.pi / 2 + i * math.pi / points
        rr = r if i % 2 == 0 else r * inner
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(*color)
    glVertex2f(x, y)
    glColor4f(*(rim or color))
    for px, py in pts + [pts[0]]:
        glVertex2f(px, py)
    glEnd()


def heart_shape(x, y, size, color):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(size, size, 1)
    glBegin(GL_TRIANGLE_FAN)
    glColor4f(*color)
    glVertex2f(0, 0)
    for i in range(33):
        t = 2 * math.pi * i / 32
        glVertex2f(math.sin(t) ** 3, (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) / 16)
    glEnd()
    glPopMatrix()


def capsule(x0, y0, x1, y1, r0, r1, color, color_end=None, seg=10):
    dx, dy = x1 - x0, y1 - y0
    ang = math.atan2(dy, dx)
    pts = []
    for i in range(seg + 1):
        a = ang + math.pi / 2 + math.pi * i / seg
        pts.append((x0 + math.cos(a) * r0, y0 + math.sin(a) * r0))
    for i in range(seg + 1):
        a = ang - math.pi / 2 + math.pi * i / seg
        pts.append((x1 + math.cos(a) * r1, y1 + math.sin(a) * r1))
    glBegin(GL_POLYGON)
    for k, (px, py) in enumerate(pts):
        glColor4f(*(color if color_end is None or k <= seg else color_end))
        glVertex2f(px, py)
    glEnd()


LEAF_PROFILE = [(i / 8, math.sin(math.pi * i / 8) ** 0.8) for i in range(9)]
LEAF_PROFILE = LEAF_PROFILE + [(t, -k) for t, k in reversed(LEAF_PROFILE)]


def leaf(x, y, angle, length, width, color, vein=None):
    c, s = math.cos(angle), math.sin(angle)
    glBegin(GL_POLYGON)
    glColor4f(*color)
    for t, k in LEAF_PROFILE:
        px, py = t * length, k * width
        glVertex2f(x + px * c - py * s, y + px * s + py * c)
    glEnd()
    if vein:
        glColor4f(*vein)
        glBegin(GL_LINES)
        glVertex2f(x, y)
        glVertex2f(x + c * length * 0.9, y + s * length * 0.9)
        glEnd()
