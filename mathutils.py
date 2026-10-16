import math


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def approach(v, target, step):
    if v < target:
        return min(target, v + step)
    return max(target, v - step)


def quad_bezier(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def point_segment_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - ax, py - ay)
    t = clamp(((px - ax) * dx + (py - ay) * dy) / l2)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rgba(c, a=1.0):
    return (c[0], c[1], c[2], a)


def shade(c, k, a=1.0):
    return (c[0] * k, c[1] * k, c[2] * k, a)


def hash01(*vals):
    h = 0
    for v in vals:
        h = (h * 1103515245 + int(v) * 2654435761 + 12345) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5bd1e995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / 0xFFFFFF


def overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
