import math

from OpenGL.GL import *

import gfx
from config import *
from mathutils import clamp

WHITE = (255, 255, 255)
SOFT = (222, 228, 236)
MUTED = (160, 170, 185)
GOLD = (255, 205, 80)
ACCENT = (255, 120, 60)


def panel(x, y, w, h, alpha=1.0, r=18):
    gfx.rounded_rect(x, y, w, h, r, (0.02, 0.03, 0.05, 0.64 * alpha), (0.06, 0.08, 0.12, 0.52 * alpha))
    gfx.rounded_rect(x + 1, y + h * 0.55, w - 2, h * 0.45 - 1, r - 1, (1, 1, 1, 0.0), (1, 1, 1, 0.05 * alpha))
    gfx.rounded_rect(x, y, w, h, r, (1, 1, 1, 0.15 * alpha), outline=True, width=1.2)


def pill(x, y, w, h, alpha=1.0):
    gfx.rounded_rect(x, y, w, h, h / 2, (0.05, 0.55, 0.32, 0.30 * alpha), (0.10, 0.70, 0.42, 0.38 * alpha))
    gfx.rounded_rect(x, y, w, h, h / 2, (0.40, 0.95, 0.65, 0.60 * alpha), outline=True, width=1.2)


def dim(alpha):
    gfx.rect(0, 0, VW, VH, (0, 0, 0, alpha), (0, 0, 0, alpha * 0.7))


class Menu:
    def __init__(self, items):
        self.items = items
        self.index = 0
        self.rects = []

    def move(self, d):
        self.index = (self.index + d) % len(self.items)

    def hover(self, x, y):
        for i, (rx, ry, rw, rh) in enumerate(self.rects):
            if rx <= x <= rx + rw and ry <= y <= ry + rh and i != self.index:
                self.index = i
                return True
        return False

    def hit(self, x, y):
        for i, (rx, ry, rw, rh) in enumerate(self.rects):
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self.index = i
                return True
        return False

    @property
    def choice(self):
        return self.items[self.index][0]

    def draw(self, x, y, t, alpha=1.0, gap=48, width=380, align="center"):
        self.rects = []
        for i, (key, label) in enumerate(self.items):
            yy = y - i * gap
            sel = i == self.index
            if sel:
                pill(x, yy - 17, width, 34, alpha * (0.85 + 0.15 * math.sin(t * 4)))
            tx = x + width / 2 if align == "center" else x + 22
            gfx.text(label, tx, yy - 10, 19, WHITE if sel else SOFT, align, alpha * (1 if sel else 0.78),
                     style="bold" if sel else "regular")
            self.rects.append((x, yy - 17, width, 34))


def stat_bar(label, value, x, y, w, alpha):
    gfx.text(label, x, y + 4, 15, MUTED, "left", alpha)
    bx = x + 120
    gfx.rounded_rect(bx, y + 5, w - 120, 9, 4.5, (1, 1, 1, 0.12 * alpha))
    gfx.rounded_rect(bx, y + 5, (w - 120) * value, 9, 4.5, (0.10, 0.70, 0.42, alpha), (0.40, 0.90, 0.60, alpha))


def track_preview(pts, x, y, size, alpha):
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    sc = (size - 20) / max(maxx - minx, maxz - minz)
    poly = [(x + size / 2 - (px - (minx + maxx) / 2) * sc, y + size / 2 + (pz - (minz + maxz) / 2) * sc) for px, pz in pts]
    poly.append(poly[0])
    gfx.thick_line(poly, 8, (1, 0.6, 0.25, 0.25 * alpha))
    gfx.thick_line(poly, 3, (1, 1, 1, 0.9 * alpha))
    gfx.disc(poly[0][0], poly[0][1], 5, (1.0, 0.8, 0.2, alpha), seg=12)


def draw_menu(game, t):
    a = clamp(t * 2)
    gfx.rect(60, VH - 92, 44, 26, (0.0, 0.42, 0.31, a))
    gfx.disc(80, VH - 79, 8, (0.86, 0.10, 0.18, a), seg=24)
    gfx.text("BAU", 116, VH - 100, 56, (255, 255, 255), "left", a, shadow=True, style="bold")
    gfx.text("CAMPUS RACE", 116 + gfx.text_width("BAU ", 56, "bold"), VH - 100, 56, (120, 220, 140), "left", a, shadow=True, style="bold")
    gfx.label("labels/title.png", 120, VH - 150, 40, a)
    gfx.text("Bangladesh Agricultural University, Mymensingh", 64, VH - 176, 16, SOFT, "left", a * 0.85, style="light")
    gap = 40
    n = len(game.menu.items)
    top = VH - 214
    h = 20 + gap * n
    panel(44, top - h, 420, h, a)
    game.menu.draw(64, top - 30, t, a, gap, 380)
    d = game.data
    if MODES[d["mode"]][0] == "race":
        gfx.text(DIFFICULTY[d["difficulty"]]["info"], 64, top - h - 26, 14, SOFT, "left", a * 0.85)
    else:
        gfx.text("Solo time trial  ·  pass every landmark gate", 64, top - h - 26, 14, SOFT, "left", a * 0.85)
    spec = CARS[d["car"]]
    tinfo = TRACKS[d["track"]]
    panel(VW - 400, 360, 360, 186, a)
    gfx.text(spec["name"], VW - 380, 508, 24, WHITE, "left", a, style="bold")
    gfx.text(spec["desc"], VW - 380, 484, 14, MUTED, "left", a)
    for i, (lab, v) in enumerate(zip(("Top speed", "Acceleration", "Handling"), spec["stats"])):
        stat_bar(lab, v, VW - 380, 444 - i * 28, 320, a)
    gfx.text("%d km/h  ·  %d Nm" % (spec["top"], spec["torque"]), VW - 380, 368, 14, SOFT, "left", a)
    panel(VW - 400, 64, 360, 280, a)
    gfx.text(tinfo["name"], VW - 380, 312, 21, WHITE, "left", a, style="bold")
    gfx.text(tinfo["desc"], VW - 380, 290, 13, MUTED, "left", a)
    track_preview(game.previews[d["track"]], VW - 380, 84, 180, a)
    length = game.lengths[d["track"]]
    tour = MODES[d["mode"]][0] == "tour"
    best = d["best_tours" if tour else "best_laps"].get(tinfo["key"])
    gfx.text("Length", VW - 186, 250, 13, MUTED, "left", a)
    gfx.text("%.2f km" % (length / 1000), VW - 186, 228, 18, WHITE, "left", a, style="bold")
    gfx.text("Best tour" if tour else "Best lap", VW - 186, 196, 13, MUTED, "left", a)
    gfx.text(fmt(best), VW - 186, 174, 18, GOLD, "left", a, style="bold")
    gfx.text("Landmarks", VW - 186, 142, 13, MUTED, "left", a)
    gfx.text("%d / %d" % (len([k for k in d["visited"] if k in LANDMARK_KEYS]), len(LANDMARK_KEYS)), VW - 186, 120, 18, WHITE, "left", a, style="bold")
    if tinfo.get("map") == "osm":
        gfx.text("Map data © OpenStreetMap contributors", VW - 380, 70, 11, MUTED, "left", a * 0.8)
    gfx.text("Wins", VW - 186, 92, 13, MUTED, "left", a)
    gfx.text(str(d["wins"]), VW - 120, 92, 15, WHITE, "left", a, style="bold")
    gfx.text("Up/Down select  ·  Left/Right change  ·  Enter start  ·  F11 fullscreen  ·  M sound %s" % ("off" if game.sound.muted else "on"),
             VW / 2, 16, 14, MUTED, "center", a * 0.7, style="light")


def fmt(t):
    if t is None:
        return "--:--.---"
    m = int(t // 60)
    return "%d:%06.3f" % (m, t - m * 60)


def draw_loading(name, t):
    gfx.rect(0, 0, VW, VH, (0.03, 0.04, 0.06, 1), (0.08, 0.10, 0.14, 1))
    gfx.text("Loading", VW / 2, VH / 2 + 20, 32, WHITE, "center", style="bold")
    gfx.text(name, VW / 2, VH / 2 - 16, 18, SOFT, "center")


def draw_pause(game, t):
    dim(0.5)
    w, h = 380, 230
    panel(VW / 2 - w / 2, VH / 2 - 100, w, h)
    gfx.text("Paused", VW / 2, VH / 2 + 84, 30, WHITE, "center", style="bold")
    game.menu.draw(VW / 2 - 170, VH / 2 + 40, t, 1.0, 48, 340)


def draw_tour_results(game, t):
    race = game.race
    dim(0.45)
    a = clamp(t * 2)
    w, h = 720, 470
    x0, y0 = VW / 2 - w / 2, VH / 2 - h / 2
    panel(x0, y0, w, h, a)
    gfx.text("Tour Complete!", VW / 2, y0 + h - 70, 44, GOLD, "center", a, style="bold")
    total = race.player.finish_time or race.time
    gfx.text("%s  ·  %s" % (race.info["name"], fmt(total)), VW / 2, y0 + h - 104, 20, WHITE, "center", a, style="bold")
    if getattr(race, "new_best", False):
        gfx.text("NEW BEST TIME", VW / 2, y0 + h - 130, 15, (140, 230, 160), "center", 0.6 + 0.4 * math.sin(t * 5), style="bold")
    y = y0 + h - 170
    cps = race.checkpoints
    cols = 2 if len(cps) > 7 else 1
    per = (len(cps) + cols - 1) // cols
    for k, cp in enumerate(cps):
        c, r = divmod(k, per)
        x = x0 + 50 + c * 330
        yy = y - r * 30
        ra = clamp(t * 3 - 0.3 - k * 0.08)
        gfx.text(PLACES[cp["key"]][0][:46], x, yy, 13, SOFT, "left", ra)
        gfx.text(fmt(cp["split"]), x + 300, yy, 14, GOLD, "right", ra)
    if t > 1.2:
        gfx.text("Enter: drive again   ·   Esc: main menu", VW / 2, y0 + 26, 16, SOFT, "center", 0.6 + 0.4 * math.sin(t * 4))


def draw_results(game, t):
    race = game.race
    if race.mode == "tour":
        draw_tour_results(game, t)
        return
    dim(0.45)
    a = clamp(t * 2)
    w, h = 720, 470
    x0, y0 = VW / 2 - w / 2, VH / 2 - h / 2
    panel(x0, y0, w, h, a)
    place = next((r[0] for r in race.results if r[4]), 6)
    title = {1: "VICTORY!", 2: "2nd Place", 3: "3rd Place"}.get(place, "%dth Place" % place)
    gfx.text(title, VW / 2, y0 + h - 70, 44, GOLD if place == 1 else WHITE, "center", a, style="bold")
    gfx.text("%s  ·  %d laps  ·  %s" % (race.info["name"], race.laps, race.diff["label"]), VW / 2, y0 + h - 100, 17, SOFT, "center", a)
    cols = (x0 + 50, x0 + 110, x0 + 300, x0 + 520, x0 + 660)
    y = y0 + h - 150
    for lab, cx, al in (("POS", cols[0], "left"), ("DRIVER", cols[1], "left"), ("CAR", cols[2], "left"), ("TIME", cols[3], "right"), ("BEST LAP", cols[4], "right")):
        gfx.text(lab, cx, y, 13, MUTED, al, a, style="bold")
    y -= 36
    for i, (pos, name, tm, best, player, carname) in enumerate(race.results):
        ra = clamp(t * 3 - 0.4 - i * 0.12)
        if player:
            gfx.rounded_rect(x0 + 30, y - 9, w - 60, 32, 8, (1.0, 0.6, 0.2, 0.22 * ra))
        col = GOLD if player else WHITE
        gfx.text(str(pos), cols[0], y, 18, col, "left", ra, style="bold")
        gfx.text(name, cols[1], y, 18, col, "left", ra, style="bold" if player else "regular")
        gfx.text(carname, cols[2], y, 16, SOFT, "left", ra)
        gfx.text(fmt(tm), cols[3], y, 18, col, "right", ra)
        gfx.text(fmt(best), cols[4], y, 16, SOFT, "right", ra)
        y -= 40
    if t > 1.2:
        gfx.text("Enter: race again   ·   Esc: main menu", VW / 2, y0 + 26, 16, SOFT, "center", 0.6 + 0.4 * math.sin(t * 4))
