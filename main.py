import OpenGL
OpenGL.ERROR_CHECKING = False

import pygame
from pygame.locals import (QUIT, KEYDOWN, VIDEORESIZE, K_F11, K_RETURN, K_UP, K_DOWN, K_LEFT, K_RIGHT,
                           K_w, K_a, K_s, K_d, K_SPACE, K_LSHIFT, K_RSHIFT, K_n)

import gfx
import save as savefile
from config import FPS
from game import Game


def read_keys():
    k = pygame.key.get_pressed()
    return {"up": k[K_UP] or k[K_w], "down": k[K_DOWN] or k[K_s], "left": k[K_LEFT] or k[K_a],
            "right": k[K_RIGHT] or k[K_d], "handbrake": k[K_SPACE], "nitro": k[K_LSHIFT] or k[K_RSHIFT] or k[K_n]}


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    data = savefile.load()
    display = gfx.Display(data["fullscreen"])
    game = Game(display, data)
    clock = pygame.time.Clock()
    while not game.quit_requested:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 30)
        for event in pygame.event.get():
            if event.type == QUIT:
                game.quit_requested = True
            elif event.type == VIDEORESIZE:
                display.resize(event.w, event.h)
            elif event.type == KEYDOWN and (event.key == K_F11 or (event.key == K_RETURN and event.mod & pygame.KMOD_ALT)):
                game.toggle_fullscreen()
            else:
                game.handle_event(event)
        game.update(dt, read_keys())
        game.draw()
        pygame.display.flip()
    game.persist()
    pygame.quit()


if __name__ == "__main__":
    main()
