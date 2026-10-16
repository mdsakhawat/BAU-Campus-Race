import math

from OpenGL.GL import *

import gfx
from config import *
from mathutils import clamp
from ui import panel, WHITE, SOFT, MUTED, GOLD


def fmt_time(t):
    if t is None:
        return "--:--.---"
    m = int(t // 60)
    s = t - m * 60
    return "%d:%06.3f" % (m, s)


def speedometer(car, cx, cy, t):
    R = 104
    gfx.disc(cx, cy, R + 14, (0.02, 0.03, 0.05, 0.62), seg=64)
    gfx.ring(cx, cy, R + 14, (1, 1, 1, 0.16), 1.2, 64)
    a0, a1 = math.radians(225), math.radians(-45)
    kmh = abs(car.kmh)
    rpm_k = (car.rpm - IDLE_RPM) / (MAX_RPM - IDLE_RPM)
    glBegin(GL_TRIANGLE_STRIP)
    n = 60
    for i in range(n + 1):
        u = i / n
        a = a0 + (a1 - a0) * u
        on = u <= rpm_k
        red = u > 0.86
        if on:
            c = (1.0, 0.25, 0.2, 0.95) if red else (1.0, 0.75, 0.25, 0.95)
        else:
            c = (0.6, 0.15, 0.12, 0.35) if red else (1, 1, 1, 0.10)
        glColor4f(*c)
        glVertex2f(cx + math.cos(a) * (R + 3), cy + math.sin(a) * (R + 3))
        glVertex2f(cx + math.cos(a) * (R + 10), cy + math.sin(a) * (R + 10))
    glEnd()
    glBegin(GL_LINES)
    for v in range(0, 341, 10):
        u = v / 340
        a = a0 + (a1 - a0) * u
        big = v % 40 == 0
        r0 = R - (14 if big else 7)
        glColor4f(1, 1, 1, 0.9 if big else 0.45)
        glVertex2f(cx + math.cos(a) * r0, cy + math.sin(a) * r0)
        glVertex2f(cx + math.cos(a) * R, cy + math.sin(a) * R)
    glEnd()
    for v in range(0, 341, 40):
        u = v / 340
        a = a0 + (a1 - a0) * u
        gfx.text(str(v), cx + math.cos(a) * (R - 28), cy + math.sin(a) * (R - 28) - 7, 13, SOFT, "center", 0.85)
    u = clamp(kmh / 340, 0, 1)
    a = a0 + (a1 - a0) * u
    gfx.thick_line([(cx - math.cos(a) * 12, cy - math.sin(a) * 12), (cx + math.cos(a) * (R - 6), cy + math.sin(a) * (R - 6))], 3.2,
                   (1.0, 0.25, 0.2, 1), (1.0, 0.55, 0.3, 1))
    gfx.disc(cx, cy, 9, (0.12, 0.12, 0.14, 1), (0.4, 0.4, 0.45, 1), 20)
    gfx.text("%d" % kmh, cx, cy - 58, 34, WHITE, "center", style="bold")
    gfx.text("km/h", cx, cy - 74, 13, MUTED, "center", style="light")
    gear = "R" if car.forward_speed() < -0.5 else str(car.gear)
    gfx.rounded_rect(cx + 34, cy - 30, 30, 30, 6, (1, 1, 1, 0.08))
    gfx.text(gear, cx + 49, cy - 25, 20, GOLD, "center", style="bold")
    bw = 170
    bx, by = cx - bw / 2, cy - R - 38
    gfx.text("NITRO", bx, by + 12, 12, MUTED, style="bold")
    gfx.rounded_rect(bx + 50, by + 12, bw - 50, 10, 5, (1, 1, 1, 0.12))
    k = car.nitro
    col = (0.35, 0.75, 1.0, 1) if not car.nitro_on else (1.0, 0.55 + 0.3 * math.sin(t * 30), 0.2, 1)
    if k > 0.01:
        gfx.rounded_rect(bx + 50, by + 12, (bw - 50) * k, 10, 5, col)


def minimap(race, x, y, size):
    tr = race.track
    pts = race.minimap
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    minx, maxx, minz, maxz = min(xs), max(xs), min(zs), max(zs)
    sc = (size - 30) / max(maxx - minx, maxz - minz)

    def Q(px, pz):
        return x + size / 2 + (px - (minx + maxx) / 2) * -sc, y + size / 2 + (pz - (minz + maxz) / 2) * sc
    panel(x, y, size, size, 1.0, 14)
    poly = [Q(px, pz) for px, pz in pts]
    poly.append(poly[0])
    gfx.thick_line(poly, 7, (1, 1, 1, 0.18))
    gfx.thick_line(poly, 3, (1, 1, 1, 0.85))
    sx, sz = Q(tr.pos[0, 0], tr.pos[0, 2])
    gfx.disc(sx, sz, 4, (1, 1, 1, 1), seg=10)
    for car in race.cars:
        if car.player:
            continue
        cx, cz = Q(car.x, car.z)
        c = car.color
        gfx.disc(cx, cz, 5, (0, 0, 0, 0.8), seg=12)
        gfx.disc(cx, cz, 3.8, (c[0], c[1], c[2], 1), seg=12)
    p = race.player
    cx, cz = Q(p.x, p.z)
    fx, fz = p.forward()
    a = math.atan2(fz, -fx)
    tri = [(cx + math.cos(a) * 9, cz + math.sin(a) * 9), (cx + math.cos(a + 2.5) * 6, cz + math.sin(a + 2.5) * 6),
           (cx + math.cos(a - 2.5) * 6, cz + math.sin(a - 2.5) * 6)]
    gfx.polygon(tri, (1.0, 0.85, 0.2, 1))


def controls_panel(race, t):
    show_t = race.time if race.state in ("racing", "finished") else 0.0
    auto = race.state in ("intro", "countdown") or show_t < HELP_SECONDS
    if not (auto or getattr(race, "show_help", False)):
        return
    a = 1.0 if getattr(race, "show_help", False) or race.state != "racing" else clamp((HELP_SECONDS - show_t) * 1.5)
    rows = (len(CONTROLS) + 1) // 2
    w, h = 600, 56 + rows * 30
    x, y = VW / 2 - w / 2, 46
    panel(x, y, w, h, a * 0.95)
    gfx.text("CONTROLS", VW / 2, y + h - 34, 15, GOLD, "center", a, style="bold")
    for i, (key, action) in enumerate(CONTROLS):
        col, row = i % 2, i // 2
        cx = x + 30 + col * (w / 2)
        cy = y + h - 68 - row * 30
        kw = gfx.text_width(key, 15, "bold") + 18
        gfx.rounded_rect(cx, cy - 5, kw, 24, 6, (1.0, 1.0, 1.0, 0.16 * a))
        gfx.text(key, cx + 9, cy, 15, WHITE, "left", a, style="bold")
        gfx.text(action, cx + kw + 12, cy, 15, SOFT, "left", a)


def draw_card(race, t):
    if race.card is None or race.card_t <= 0:
        return
    c = race.card
    a = clamp(race.card_t * 2) * clamp((4.5 - race.card_t) * 4 + 0.3)
    w = max(gfx.text_width(c["name"], 22, "bold"), gfx.text_width(c["fact"], 16)) + 70
    w = max(w, 420)
    x0 = VW / 2 - w / 2
    y0 = VH - 290
    panel(x0, y0, w, 150, a, 16)
    gfx.rounded_rect(x0, y0, 6, 150, 3, (0.25, 0.85, 0.5, a))
    path = "labels/l_%s.png" % c["key"]
    try:
        gfx.label(path, VW / 2, y0 + 82, 50, a, "center")
    except Exception:
        pass
    gfx.text(c["name"], VW / 2, y0 + 50, 22, WHITE, "center", a, style="bold")
    gfx.text(c["fact"], VW / 2, y0 + 24, 15, SOFT, "center", a)
    if race.mode == "tour":
        gfx.text("Checkpoint %d / %d   ·   %s" % (c["n"], len(race.checkpoints), fmt_time(c["time"])), VW / 2, y0 + 4, 13, GOLD, "center", a)


def draw(race, t):
    p = race.player
    gfx.begin_2d()
    if race.mode == "tour":
        draw_tour(race, t)
        return
    pos = race.player_position()
    panel(18, VH - 128, 250, 110, 1.0, 14)
    gfx.text("POS", 36, VH - 50, 13, MUTED, style="bold")
    gfx.text("%d" % pos, 36, VH - 108, 52, WHITE, style="bold")
    gfx.text("/%d" % NUM_CARS, 36 + gfx.text_width("%d" % pos, 52, "bold") + 2, VH - 92, 22, SOFT, style="bold")
    lap = p.lap(race.track, race.laps)
    gfx.text("LAP", 140, VH - 50, 13, MUTED, style="bold")
    gfx.text("%d/%d" % (lap, race.laps), 140, VH - 84, 28, WHITE, style="bold")
    cur = race.time - p.lap_start if race.state in ("racing", "finished") and p.total >= 0 and not p.finished else 0.0
    gfx.text(fmt_time(cur), 140, VH - 108, 15, SOFT)
    panel(18, VH - 178, 250, 42, 1.0, 12)
    gfx.text("BEST", 34, VH - 164, 13, MUTED, style="bold")
    gfx.text(fmt_time(p.best_lap), 252, VH - 166, 16, GOLD, "right", style="bold")
    standings = race.standings()
    y = VH - 214
    panel(18, y - 28 * len(standings) + 14, 200, 28 * len(standings) + 8, 0.8, 12)
    for i, car in enumerate(standings):
        col = car.color
        a = 1.0 if car.player else 0.8
        if car.player:
            gfx.rounded_rect(18, y - 6, 200, 26, 8, (1.0, 0.85, 0.2, 0.22))
        gfx.text("%d" % (i + 1), 30, y, 15, WHITE, "left", a, style="bold")
        gfx.rect(50, y + 1, 4, 14, (col[0], col[1], col[2], 1))
        gfx.text(car.name, 62, y, 15, GOLD if car.player else SOFT, "left", a, style="bold" if car.player else "regular")
        y -= 28
    minimap(race, VW - 238, VH - 238, 220)
    speedometer(p, VW - 150, 150, t)
    gfx.text("F1 controls  ·  C camera  ·  R reset  ·  Space handbrake  ·  Shift nitro", 22, 18, 13, MUTED, "left", 0.7, style="light")
    controls_panel(race, t)
    draw_card(race, t)
    if race.state == "countdown":
        label = str(max(1, min(3, 3 - int((race.state_t - 2.0) / 0.8)))) if race.state_t > 2.0 else ""
        if label:
            k = ((race.state_t - 2.0) % 0.8) / 0.8
            gfx.text(label, VW / 2, VH / 2 + 40, int(120 - k * 30), (255, 255, 255), "center", 1 - k * 0.6, shadow=True, style="bold")
        else:
            gfx.text("GET READY", VW / 2, VH / 2 + 60, 40, WHITE, "center", 0.9, shadow=True, style="bold")
    if race.state == "intro":
        a = clamp(race.state_t * 2) * clamp((2.6 - race.state_t) * 2)
        panel(VW / 2 - 260, VH / 2 + 30, 520, 110, a)
        gfx.text(race.info["name"], VW / 2, VH / 2 + 90, 36, WHITE, "center", a, style="bold")
        gfx.text("%d laps  ·  %.2f km  ·  %s" % (race.laps, race.track.length / 1000, race.diff["label"]), VW / 2, VH / 2 + 54, 18, SOFT, "center", a)
    if race.message_t > 0:
        a = clamp(race.message_t * 2)
        size = 64 if race.message in ("GO!",) else 44
        gfx.text(race.message, VW / 2, VH / 2 + 110, size, (255, 230, 120), "center", a, shadow=True, style="bold")
    if p.wrong_way_t > 1.2 and not p.finished:
        if int(t * 3) % 2 == 0:
            gfx.text("WRONG WAY", VW / 2, VH / 2 + 110, 48, (255, 90, 80), "center", 1, shadow=True, style="bold")
    if p.nitro_on:
        gfx.sprites([(VW / 2, VH / 2, VW * 1.3, VH * 1.5, 0, 0.3, 0.6, 1.0, 0.18)], "vignette", additive=True)


def showcase_overlay(race):
    sc = race.showcase
    if not sc:
        return False
    st = sc["t"]
    fade = max(clamp(1 - st / 0.35), clamp((st - (SHOWCASE_SECONDS - 0.35)) / 0.35))
    gfx.rect(0, 0, VW, 46, (0, 0, 0, 0.55))
    gfx.rect(0, VH - 46, VW, 46, (0, 0, 0, 0.55))
    gfx.text(PLACES[sc["key"]][0], VW / 2, VH - 32, 20, WHITE, "center", 1, style="bold")
    gfx.text("Enter: continue driving", VW / 2, 14, 14, SOFT, "center", 0.9)
    if fade > 0:
        gfx.rect(0, 0, VW, VH, (0, 0, 0, fade))
    draw_card(race, 0)
    return True


def draw_tour(race, t):
    if showcase_overlay(race):
        return
    p = race.player
    done = sum(1 for c in race.checkpoints if c["done"])
    panel(18, VH - 128, 290, 110, 1.0, 14)
    gfx.text("LANDMARKS", 36, VH - 50, 13, MUTED, style="bold")
    gfx.text("%d" % done, 36, VH - 108, 52, WHITE, style="bold")
    gfx.text("/%d" % len(race.checkpoints), 36 + gfx.text_width("%d" % done, 52, "bold") + 2, VH - 92, 22, SOFT, style="bold")
    gfx.text("TIME", 170, VH - 50, 13, MUTED, style="bold")
    gfx.text(fmt_time(race.time), 170, VH - 82, 24, WHITE, style="bold")
    nxt = next((c for c in race.checkpoints if not c["done"]), None)
    if nxt:
        gfx.text("Next: " + PLACES[nxt["key"]][0][:30], 36, VH - 150, 15, GOLD, style="bold")
        d = (nxt["s"] - (p.total % race.track.length if p.total >= 0 else 0))
        if d >= 0:
            gfx.text("%d m" % d, 36, VH - 172, 14, SOFT)
    minimap(race, VW - 238, VH - 238, 220)
    speedometer(p, VW - 150, 150, t)
    gfx.text("F1 controls  ·  C camera  ·  R reset  ·  H horn  ·  Space handbrake  ·  Shift nitro", 22, 18, 13, MUTED, "left", 0.7, style="light")
    controls_panel(race, t)
    draw_card(race, t)
    if race.state == "countdown":
        label = str(max(1, min(3, 3 - int((race.state_t - 2.0) / 0.8)))) if race.state_t > 2.0 else ""
        if label:
            k = ((race.state_t - 2.0) % 0.8) / 0.8
            gfx.text(label, VW / 2, VH / 2 + 40, int(120 - k * 30), (255, 255, 255), "center", 1 - k * 0.6, shadow=True, style="bold")
        else:
            gfx.text("GET READY", VW / 2, VH / 2 + 60, 40, WHITE, "center", 0.9, shadow=True, style="bold")
    if race.state == "intro":
        a = clamp(race.state_t * 2) * clamp((2.6 - race.state_t) * 2)
        panel(VW / 2 - 280, VH / 2 + 30, 560, 110, a)
        gfx.text(race.info["name"], VW / 2, VH / 2 + 90, 34, WHITE, "center", a, style="bold")
        gfx.text("Campus Tour  ·  %d landmarks  ·  %.2f km" % (len(race.checkpoints), race.track.length / 1000), VW / 2, VH / 2 + 54, 18, SOFT, "center", a)
    if race.message_t > 0:
        a = clamp(race.message_t * 2)
        gfx.text(race.message, VW / 2, VH / 2 + 110, 56, (255, 230, 120), "center", a, shadow=True, style="bold")
