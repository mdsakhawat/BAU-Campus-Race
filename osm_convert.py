import glob
import heapq
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OSM_DIR = os.path.join(HERE, "osm")
OUT = os.path.join(HERE, "assets", "campus_osm.json")
ROAD_TYPES = {"primary", "secondary", "tertiary", "unclassified", "residential", "service", "living_street", "footway", "path",
              "track", "pedestrian", "road"}
ROUTES = {
    "grand": dict(name="Grand Loop", tour_only=False, start=(110, -6), via=[(-269, 21), (-309, -832), (434, -460), (276, -192), (164, -3)],
                  desc="BINA road, Aambagan Road, the coconut grove and the railway side"),
    "stadium": dict(name="Stadium Circuit", tour_only=False, start=(150, -60), via=[(163, -211), (276, -192), (164, -3), (141, -4)],
                    desc="BAU Stadium loop next to Jobbar Moor"),
    "aet": dict(name="AET - CSM Tour", tour_only=True, start=(232, 42),
                via=[(185, 128), (153, 182), ("turn", (312, 280)), (153, 182), (185, 128), ("turn", (254, 5))],
                desc="Jobbar Moor, railway station, CSM department and AET faculty"),
}


def load(files):
    nodes = {}
    ways = {}
    bounds = None
    for f in files:
        root = ET.parse(f).getroot()
        b = root.find("bounds")
        if b is not None:
            bb = [float(b.get(k)) for k in ("minlat", "minlon", "maxlat", "maxlon")]
            if bounds is None:
                bounds = bb
            else:
                bounds = [min(bounds[0], bb[0]), min(bounds[1], bb[1]), max(bounds[2], bb[2]), max(bounds[3], bb[3])]
        for n in root.findall("node"):
            tags = {t.get("k"): t.get("v") for t in n.findall("tag")}
            nodes[n.get("id")] = (float(n.get("lat")), float(n.get("lon")), tags)
        for w in root.findall("way"):
            tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
            ways[w.get("id")] = ([nd.get("ref") for nd in w.findall("nd")], tags)
    return nodes, ways, bounds


def main():
    files = sorted(glob.glob(os.path.join(OSM_DIR, "*.osm")))
    if not files:
        print("Put .osm files in", OSM_DIR)
        sys.exit(1)
    nodes, ways, bounds = load(files)
    lat0 = (bounds[0] + bounds[2]) / 2
    lon0 = (bounds[1] + bounds[3]) / 2
    kx = 111320 * math.cos(math.radians(lat0))
    ky = 110574

    def en(nid):
        lat, lon, _ = nodes[nid]
        return ((lon - lon0) * kx, (lat - lat0) * ky)

    out = dict(origin=[lat0, lon0], box=[(bounds[1] - lon0) * kx, (bounds[0] - lat0) * ky, (bounds[3] - lon0) * kx, (bounds[2] - lat0) * ky],
               roads=[], buildings=[], water=[], rail=[], areas=[], places=[], routes={})
    graph = {}
    for wid, (refs, tags) in ways.items():
        refs = [r for r in refs if r in nodes]
        if len(refs) < 2:
            continue
        pts = [en(r) for r in refs]
        hw = tags.get("highway")
        if hw in ROAD_TYPES:
            out["roads"].append(dict(type=hw, name=tags.get("name", ""), pts=[[round(x, 2), round(y, 2)] for x, y in pts]))
            if hw not in ("footway", "path", "pedestrian"):
                for a, b in zip(refs, refs[1:]):
                    d = math.dist(en(a), en(b))
                    graph.setdefault(a, []).append((b, d))
                    graph.setdefault(b, []).append((a, d))
        elif "building" in tags:
            levels = tags.get("building:levels")
            out["buildings"].append(dict(pts=[[round(x, 2), round(y, 2)] for x, y in pts[:-1]], levels=int(float(levels)) if levels else 0,
                                         name=tags.get("name", ""), kind=tags.get("building", "yes"), amenity=tags.get("amenity", "")))
        elif tags.get("natural") == "water" or "water" in tags or tags.get("landuse") in ("reservoir", "basin"):
            out["water"].append(dict(pts=[[round(x, 2), round(y, 2)] for x, y in pts], name=tags.get("name", "")))
        elif "railway" in tags:
            out["rail"].append(dict(type=tags["railway"], pts=[[round(x, 2), round(y, 2)] for x, y in pts]))
        elif "leisure" in tags or "landuse" in tags or "natural" in tags:
            out["areas"].append(dict(kind=tags.get("leisure") or tags.get("landuse") or tags.get("natural"), name=tags.get("name", ""),
                                     pts=[[round(x, 2), round(y, 2)] for x, y in pts]))
    for nid, (lat, lon, tags) in nodes.items():
        if "name" in tags:
            x, y = en(nid)
            out["places"].append(dict(name=tags["name"], x=round(x, 2), y=round(y, 2), kind=tags.get("amenity") or tags.get("railway") or tags.get("public_transport") or ""))
    keys = list(graph.keys())
    pos = {k: en(k) for k in keys}

    def nearest(p):
        return min(keys, key=lambda k: (pos[k][0] - p[0]) ** 2 + (pos[k][1] - p[1]) ** 2)

    def path(a, b):
        dist = {a: 0.0}
        prev = {}
        q = [(0.0, a)]
        while q:
            d, u = heapq.heappop(q)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, w in graph[u]:
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(q, (nd, v))
        p = [b]
        while p[-1] != a:
            p.append(prev[p[-1]])
        return [pos[k] for k in reversed(p)]

    for key, r in ROUTES.items():
        pts = []
        cur = nearest(r["start"])
        pts.append(pos[cur])
        for v in r["via"]:
            if isinstance(v, tuple) and v and v[0] == "turn":
                tgt = nearest(v[1])
                seg = path(cur, tgt)
                pts.extend(seg[1:])
                pts.extend(teardrop(pts, 21.0))
                cur = tgt
                continue
            tgt = nearest(v)
            seg = path(cur, tgt)
            pts.extend(seg[1:])
            cur = tgt
        start = nearest(r["start"])
        seg = path(cur, start)
        pts.extend(seg[1:-1])
        pts = smooth_route(pts)
        out["routes"][key] = dict(name=r["name"], tour_only=r["tour_only"], desc=r["desc"], pts=[[round(x, 2), round(y, 2)] for x, y in pts])
        L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:] + pts[:1]))
        print(key, "points", len(pts), "length", round(L))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print("wrote", OUT, "roads", len(out["roads"]), "buildings", len(out["buildings"]), "water", len(out["water"]))


def teardrop(pts, R):
    ex, ey = pts[-1]
    k = len(pts) - 2
    while k > 0 and math.dist(pts[k], pts[-1]) < 6:
        k -= 1
    dx, dy = ex - pts[k][0], ey - pts[k][1]
    d = math.hypot(dx, dy) or 1.0
    dx, dy = dx / d, dy / d
    lx, ly = -dy, dx
    cx, cy = ex + dx * R * 0.9, ey + dy * R * 0.9
    out = []
    a0 = math.radians(140)
    for i in range(1, 14):
        a = a0 - (2 * a0) * i / 14
        out.append((cx + R * (math.cos(a) * dx + math.sin(a) * lx), cy + R * (math.cos(a) * dy + math.sin(a) * ly)))
    out.append((ex, ey))
    return out


def smooth_route(pts):
    clean = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, clean[-1]) > 0.5:
            clean.append(p)
    if math.dist(clean[0], clean[-1]) < 0.5:
        clean.pop()
    dense = []
    n = len(clean)
    for i in range(n):
        a, b = clean[i], clean[(i + 1) % n]
        L = math.dist(a, b)
        steps = max(1, int(L / 2.0))
        for s in range(steps):
            t = s / steps
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    m = len(dense)
    for _ in range(4):
        w = 6
        nxt = []
        for i in range(m):
            sx = sy = 0.0
            for k in range(-w, w + 1):
                sx += dense[(i + k) % m][0]
                sy += dense[(i + k) % m][1]
            nxt.append((sx / (2 * w + 1), sy / (2 * w + 1)))
        dense = nxt
    out = [dense[0]]
    acc = 0.0
    for i in range(1, m):
        acc += math.dist(dense[i], dense[i - 1])
        if acc >= 9.0:
            out.append(dense[i])
            acc = 0.0
    return out


if __name__ == "__main__":
    main()
