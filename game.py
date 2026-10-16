import math

import pygame
from pygame.locals import (KEYDOWN, MOUSEMOTION, MOUSEBUTTONDOWN, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_w, K_s, K_a, K_d,
                           K_RETURN, K_KP_ENTER, K_SPACE, K_ESCAPE, K_p, K_m, K_c, K_r, K_h, K_F1)
from OpenGL.GL import *

import gfx
import hud
import save as savefile
import ui
from car import Controls
from carmodel import CarModel
from config import *
from mathutils import clamp, approach
from race import Race
from sound import SoundManager
from track import Track

CONFIRM = (K_RETURN, K_KP_ENTER)


class Game:
    def __init__(self, display, data):
        self.display = display
        self.data = data
        self.sound = SoundManager(data.get("muted", False))
        self.quit_requested = False
        self.state_t = 0.0
        self.race = None
        self.steer = 0.0
        self.showroom = None
        self.showroom_key = None
        self.previews = []
        self.lengths = []
        for info in TRACKS:
            tr = Track(info)
            self.previews.append(tr.minimap_points(160))
            self.lengths.append(tr.length)
            tr.release()
        self.pending = None
        self.frame_dt = 1 / 60
        self.data["track"] = self.next_track(self.data.get("track", 0), 0)
        self.go_menu()

    def menu_items(self):
        d = self.data
        items = [("race", "Start Race" if MODES[d["mode"]][0] == "race" else "Start Campus Tour"),
                 ("mode", "Mode:  ‹ %s ›" % MODES[d["mode"]][1]),
                 ("track", "Route:  ‹ %s ›" % TRACKS[d["track"]]["name"]),
                 ("car", "Car:  ‹ %s ›" % CARS[d["car"]]["name"]),
                 ("color", "Color:  ‹ %s ›" % COLORS[d["color"]][0])]
        if MODES[d["mode"]][0] == "race":
            items.append(("laps", "Laps:  ‹ %d ›" % d["laps"]))
            items.append(("difficulty", "Difficulty:  ‹ %s ›" % DIFFICULTY[d["difficulty"]]["label"]))
        items += [("time", "Time:  ‹ %s ›" % TIMES[d["time"]][0]), ("weather", "Weather:  ‹ %s ›" % WEATHERS[d["weather"]]),
                  ("quit", "Quit")]
        return items

    def go_menu(self):
        if self.race:
            self.race.release()
            self.race = None
        self.sound.stop_engine()
        self.state = "menu"
        self.state_t = 0.0
        index = self.menu.index if getattr(self, "menu", None) and self.menu.items[0][0] == "race" else 0
        self.menu = ui.Menu(self.menu_items())
        self.menu.index = index
        self.sound.play_music("menu")

    def refresh_menu(self):
        index = self.menu.index
        self.menu = ui.Menu(self.menu_items())
        self.menu.index = index

    def track_allowed(self, i):
        return MODES[self.data["mode"]][0] == "tour" or not TRACKS[i].get("tour_only")

    def next_track(self, i, d):
        i %= len(TRACKS)
        if d == 0 and self.track_allowed(i):
            return i
        step = d or 1
        for k in range(len(TRACKS)):
            i = (i + step) % len(TRACKS)
            if self.track_allowed(i):
                return i
        return 0

    def adjust(self, key, d):
        data = self.data
        if key == "car":
            data["car"] = (data["car"] + d) % len(CARS)
            self.sound.play("rev", 0.3)
        elif key == "color":
            data["color"] = (data["color"] + d) % len(COLORS)
        elif key == "track":
            data["track"] = self.next_track(data["track"], d)
        elif key == "laps":
            data["laps"] = int(clamp(data["laps"] + d, 1, 5))
        elif key == "difficulty":
            i = DIFF_ORDER.index(data["difficulty"])
            data["difficulty"] = DIFF_ORDER[(i + d) % len(DIFF_ORDER)]
        elif key == "mode":
            data["mode"] = (data["mode"] + d) % len(MODES)
            data["track"] = self.next_track(data["track"], 0)
        elif key == "time":
            data["time"] = (data["time"] + d) % len(TIMES)
        elif key == "weather":
            data["weather"] = (data["weather"] + d) % len(WEATHERS)
        else:
            return False
        self.sound.play("menu_move")
        self.refresh_menu()
        self.persist()
        return True

    def start_race(self):
        self.state = "loading"
        self.state_t = 0.0
        self.pending = 2
        self.sound.play("menu_select")
        self.sound.stop_music(600)

    def build_race(self):
        if self.race:
            self.race.release()
        d = self.data
        self.race = Race(self, d["track"], d["car"], d["color"], d["difficulty"], d["laps"], MODES[d["mode"]][0], d["time"], d["weather"])
        self.state = "race"
        self.state_t = 0.0
        self.steer = 0.0
        self.sound.start_engine()
        self.sound.play_music("race")

    def visit(self, key):
        if key not in self.data["visited"]:
            self.data["visited"].append(key)

    def toggle_fullscreen(self):
        self.display.toggle_fullscreen()
        self.data["fullscreen"] = self.display.fullscreen
        self.persist()

    def persist(self):
        self.data["muted"] = self.sound.muted
        savefile.store(self.data)

    def pause(self):
        self.state = "pause"
        self.state_t = 0.0
        self.menu = ui.Menu([("resume", "Resume"), ("restart", "Restart Race"), ("menu", "Quit to Menu")])
        self.sound.play("pause")
        self.sound.stop_engine()
        if self.sound.enabled:
            pygame.mixer.music.pause()

    def resume(self):
        self.state = "race"
        self.sound.start_engine()
        if self.sound.enabled:
            pygame.mixer.music.unpause()

    def handle_event(self, event):
        if event.type == KEYDOWN and event.key == K_m:
            self.sound.toggle_mute()
            self.persist()
            return
        if self.state == "race":
            if event.type == KEYDOWN:
                if event.key in (K_ESCAPE, K_p):
                    self.pause()
                elif event.key == K_c:
                    self.race.camera.cycle()
                elif event.key == K_r and self.race.state == "racing":
                    self.race.player.respawn(self.race.track)
                elif event.key in CONFIRM and self.race.showcase:
                    self.race.end_showcase()
                elif event.key == K_F1:
                    self.race.show_help = not getattr(self.race, "show_help", False)
                elif event.key == K_h:
                    self.sound.play("horn_car", 0.3)
                    if self.race:
                        self.race.crossers.horn()
            return
        if self.state == "results":
            if event.type == KEYDOWN and self.state_t > 1.0:
                if event.key in CONFIRM + (K_SPACE,):
                    self.start_race()
                elif event.key == K_ESCAPE:
                    self.sound.play("menu_select")
                    self.go_menu()
            return
        if self.state not in ("menu", "pause"):
            return
        if event.type == KEYDOWN:
            if event.key in (K_UP, K_w):
                self.menu.move(-1)
                self.sound.play("menu_move")
            elif event.key in (K_DOWN, K_s):
                self.menu.move(1)
                self.sound.play("menu_move")
            elif event.key in (K_LEFT, K_a, K_RIGHT, K_d) and self.state == "menu":
                self.adjust(self.menu.choice, -1 if event.key in (K_LEFT, K_a) else 1)
            elif event.key in CONFIRM + (K_SPACE,):
                self.choose(self.menu.choice)
            elif event.key in (K_ESCAPE, K_p) and self.state == "pause":
                self.resume()
        elif event.type == MOUSEMOTION:
            if self.menu.hover(*self.display.to_virtual(*event.pos)):
                self.sound.play("menu_move")
        elif event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.menu.hit(*self.display.to_virtual(*event.pos)):
                self.choose(self.menu.choice)

    def choose(self, key):
        if key == "race":
            self.start_race()
        elif key == "quit":
            self.quit_requested = True
        elif key == "resume":
            self.sound.play("menu_select")
            self.resume()
        elif key == "restart":
            if self.sound.enabled:
                pygame.mixer.music.unpause()
            self.start_race()
        elif key == "menu":
            if self.sound.enabled:
                pygame.mixer.music.unpause()
            self.sound.play("menu_select")
            self.go_menu()
        elif self.state == "menu":
            self.adjust(key, 1)

    def player_controls(self, dt, keys):
        ctl = Controls()
        ctl.throttle = 1.0 if keys["up"] else 0.0
        ctl.brake = 1.0 if keys["down"] else 0.0
        target = (1.0 if keys["right"] else 0.0) - (1.0 if keys["left"] else 0.0)
        speed = abs(self.race.player.forward_speed()) if self.race else 0
        same = target != 0 and (self.steer == 0 or math.copysign(1, target) == math.copysign(1, self.steer))
        rate = STEER_RATE if same else STEER_RETURN
        rate *= 1.0 / (1 + speed / 120)
        self.steer = approach(self.steer, target, rate * dt)
        ctl.steer = self.steer
        ctl.handbrake = keys["handbrake"]
        ctl.nitro = keys["nitro"]
        return ctl

    def update(self, dt, keys):
        self.frame_dt = dt
        self.state_t += dt
        if self.state == "loading":
            self.pending -= 1
            if self.pending <= 0:
                self.build_race()
            return
        if self.state in ("race", "results"):
            race = self.race
            ctl = self.player_controls(dt, keys) if self.state == "race" else Controls()
            race.update(dt, ctl)
            p = race.player
            near = min((math.hypot(c.x - p.x, c.z - p.z) for c in race.cars if c is not p), default=999)
            racing = race.state in ("racing", "finished")
            self.sound.update_engine(p.rpm, p.throttle if not p.finished else 0.1, p.speed, p.slip, p.offroad and racing,
                                     p.nitro_on, p.wall_contact, near)
            if self.state == "race" and race.results is not None:
                self.on_results()

    def on_results(self):
        race = self.race
        p = race.player
        key = race.info["key"]
        if race.mode == "tour":
            t = p.finish_time or race.time
            best = self.data["best_tours"].get(key)
            race.new_best = best is None or t < best
            if race.new_best:
                self.data["best_tours"][key] = round(t, 3)
            self.persist()
            self.state = "results"
            self.state_t = 0.0
            return
        if p.best_lap is not None:
            best = self.data["best_laps"].get(key)
            if best is None or p.best_lap < best:
                self.data["best_laps"][key] = round(p.best_lap, 3)
        place = next(r[0] for r in race.results if r[4])
        if place == 1:
            self.data["wins"] += 1
        self.persist()
        self.state = "results"
        self.state_t = 0.0

    def draw_showroom(self, t):
        d = self.data
        key = (CARS[d["car"]]["style"], d["color"])
        if key != self.showroom_key:
            if self.showroom:
                self.showroom.release()
            self.showroom = CarModel(key[0], COLORS[d["color"]][1])
            self.showroom_key = key
        gfx.begin_2d()
        gfx.rect(0, 0, VW, VH, (0.02, 0.025, 0.035, 1), (0.10, 0.12, 0.17, 1))
        gfx.sprites([gfx.glow(VW * 0.62, VH * 0.55, 1300, (0.35, 0.45, 0.65), 0.35)])
        gfx.begin_3d(30, 0.5, 200)
        ang = t * 0.35
        eye = (math.sin(ang) * 11.5, 2.8, math.cos(ang) * 11.5)
        fwd = (-eye[0], 0, -eye[2])
        ln = math.hypot(fwd[0], fwd[2])
        rx, rz = -fwd[2] / ln, fwd[0] / ln
        target = (-rx * 0.5, 0.6, -rz * 0.5)
        gfx.look_at(eye, target)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_NORMALIZE)
        glLightfv(GL_LIGHT0, GL_POSITION, (0.4, 0.9, 0.6, 0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1, 1, 1, 1))
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.38, 0.40, 0.46, 1))
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glDisable(GL_FOG)
        glPushMatrix()
        glScalef(1, -1, 1)
        glFrontFace(GL_CW)
        self.showroom.draw(t * 2, 0.0, False, reflect=False)
        glFrontFace(GL_CCW)
        glPopMatrix()
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glDepthMask(GL_FALSE)
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(0.10, 0.12, 0.16, 0.80)
        glVertex3f(0, 0, 0)
        for k in range(65):
            a = 2 * math.pi * k / 64
            glColor4f(0.04, 0.05, 0.07, 0.96)
            glVertex3f(math.cos(a) * 3.9, 0, math.sin(a) * 3.9)
        glEnd()
        glColor4f(0.3, 0.9, 0.5, 0.7)
        glBegin(GL_LINE_LOOP)
        for k in range(64):
            a = 2 * math.pi * k / 64
            glVertex3f(math.cos(a) * 3.9, 0.005, math.sin(a) * 3.9)
        glEnd()
        glDepthMask(GL_TRUE)
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)
        self.showroom.draw(t * 2, 0.0, False)
        glDisable(GL_LIGHTING)

    def draw(self):
        self.display.begin_frame()
        t = self.state_t
        if self.state == "menu":
            self.draw_showroom(t)
            gfx.begin_2d()
            ui.draw_menu(self, t)
            return
        if self.state == "loading":
            gfx.begin_2d()
            ui.draw_loading(TRACKS[self.data["track"]]["name"], t)
            return
        race = self.race
        dt = 0.0 if self.state == "pause" else self.frame_dt
        race.draw(dt)
        hud.draw(race, t)
        gfx.sprites([(VW / 2, VH / 2, VW * 1.2, VH * 1.3, 0, 0, 0, 0, 0.35)], "vignette", additive=False)
        if self.state == "pause":
            ui.draw_pause(self, t)
        elif self.state == "results":
            ui.draw_results(self, t)
