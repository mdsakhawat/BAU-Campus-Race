import os
import time

import pygame

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
ENGINE_RPMS = [900, 1500, 2200, 3000, 3800, 4600, 5400, 6200, 7000, 7700]
EFFECTS = {"crash": 0.8, "bump": 0.6, "shift": 0.35, "beep_low": 0.55, "beep_high": 0.6, "final_lap": 0.6,
           "finish": 0.75, "menu_move": 0.35, "menu_select": 0.5, "pause": 0.45, "rev": 0.6,
           "discover": 0.6, "horn_car": 0.7}
LOOPS = {"tyre": 0.55, "wind": 0.45, "gravel": 0.5, "nitro": 0.5, "scrape": 0.5}
MUSIC = {"menu": "music_menu.ogg", "race": "music_race.ogg"}
MUSIC_VOLUME = 0.32


class SoundManager:
    def __init__(self, muted=False):
        self.muted = muted
        self.enabled = False
        self.effects = {}
        self.last = {}
        self.current = None
        self.engine = []
        self.loops = {}
        self.ai_channel = None
        self.running = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(40)
            reserved = len(ENGINE_RPMS) + len(LOOPS) + 1
            pygame.mixer.set_reserved(reserved)
            for name, vol in EFFECTS.items():
                snd = pygame.mixer.Sound(os.path.join(SOUND_DIR, name + ".ogg"))
                snd.set_volume(vol)
                self.effects[name] = snd
            ch = 0
            for i in range(len(ENGINE_RPMS)):
                snd = pygame.mixer.Sound(os.path.join(SOUND_DIR, "engine_%02d.ogg" % i))
                self.engine.append((snd, pygame.mixer.Channel(ch)))
                ch += 1
            for name in LOOPS:
                snd = pygame.mixer.Sound(os.path.join(SOUND_DIR, name + ".ogg"))
                self.loops[name] = (snd, pygame.mixer.Channel(ch))
                ch += 1
            self.ai_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "engine_05.ogg"))
            self.ai_channel = pygame.mixer.Channel(ch)
            self.enabled = True
        except (pygame.error, FileNotFoundError, OSError) as error:
            print("Sound disabled:", error)

    def play(self, name, throttle=0.0):
        if not self.enabled or self.muted or name not in self.effects:
            return
        now = time.perf_counter()
        if throttle and now - self.last.get(name, 0) < throttle:
            return
        self.last[name] = now
        self.effects[name].play()

    def start_engine(self):
        if not self.enabled or self.running:
            return
        self.running = True
        for snd, ch in self.engine:
            ch.play(snd, loops=-1)
            ch.set_volume(0)
        for name, (snd, ch) in self.loops.items():
            ch.play(snd, loops=-1)
            ch.set_volume(0)
        self.ai_channel.play(self.ai_sound, loops=-1)
        self.ai_channel.set_volume(0)

    def stop_engine(self):
        if not self.enabled or not self.running:
            return
        self.running = False
        for snd, ch in self.engine:
            ch.fadeout(300)
        for name, (snd, ch) in self.loops.items():
            ch.fadeout(300)
        self.ai_channel.fadeout(300)

    def update_engine(self, rpm, throttle, speed, slip, offroad, nitro, scrape, ai_dist):
        if not self.enabled or not self.running:
            return
        master = 0.0 if self.muted else 1.0
        r = max(ENGINE_RPMS[0], min(ENGINE_RPMS[-1], rpm))
        i = 0
        while i < len(ENGINE_RPMS) - 2 and ENGINE_RPMS[i + 1] < r:
            i += 1
        t = (r - ENGINE_RPMS[i]) / (ENGINE_RPMS[i + 1] - ENGINE_RPMS[i])
        loud = (0.35 + 0.65 * throttle) * master * 0.75
        for k, (snd, ch) in enumerate(self.engine):
            if k == i:
                v = (1 - t) * loud
            elif k == i + 1:
                v = t * loud
            else:
                v = 0.0
            ch.set_volume(v)
        vals = {"tyre": min(1.0, max(0.0, (slip - 3) / 5)) if speed > 4 else 0.0,
                "wind": min(1.0, speed / 75) ** 2 * 0.8,
                "gravel": min(1.0, speed / 25) if offroad else 0.0,
                "nitro": 1.0 if nitro else 0.0,
                "scrape": 1.0 if scrape else 0.0}
        for name, (snd, ch) in self.loops.items():
            ch.set_volume(vals[name] * LOOPS[name] * master)
        self.ai_channel.set_volume(max(0.0, 1 - ai_dist / 45) * 0.35 * master)

    def play_music(self, name, loop=True, fade=1200):
        if not self.enabled or name == self.current:
            return
        self.current = name
        try:
            pygame.mixer.music.fadeout(300)
            pygame.mixer.music.load(os.path.join(SOUND_DIR, MUSIC[name]))
            pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade)
            pygame.mixer.music.set_volume(0 if self.muted else MUSIC_VOLUME)
        except pygame.error as error:
            print("Music error:", error)

    def stop_music(self, fade=800):
        if self.enabled:
            pygame.mixer.music.fadeout(fade)
            self.current = None

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled:
            pygame.mixer.music.set_volume(0 if self.muted else MUSIC_VOLUME)
            if self.muted:
                for snd, ch in self.engine:
                    ch.set_volume(0)
        return self.muted
