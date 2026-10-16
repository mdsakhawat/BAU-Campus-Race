import json
import os

VW, VH = 1280, 720
FPS = 60
TITLE = "BAU Campus Race"

GRAVITY = 9.81
ROAD_HALF = 5.6
CURB_W = 0.8
WALL_DIST = 9.5
SAMPLE_STEP = 2.0
NUM_CARS = 6
DEFAULT_LAPS = 3

CARS = [
    dict(key="gt", name="Falcon GT", style="coupe", mass=1250, torque=430, grip=1.18, top=285, drag=0.36,
         stats=(0.82, 0.78, 0.86), desc="Balanced sports coupe"),
    dict(key="muscle", name="Bulldog V8", style="muscle", mass=1500, torque=560, grip=1.05, top=275, drag=0.40,
         stats=(0.78, 0.92, 0.66), desc="Brutal power, slides easily"),
    dict(key="hyper", name="Vortex R", style="hyper", mass=1150, torque=470, grip=1.30, top=310, drag=0.33,
         stats=(0.95, 0.86, 0.95), desc="Low hypercar, sharp handling"),
    dict(key="sedan", name="Campus Sedan", style="sedan", mass=1250, torque=260, grip=1.08, top=200, drag=0.36,
         stats=(0.55, 0.50, 0.78), desc="Everyday sedan - easy to drive"),
]

COLORS = [
    ("Racing Red", (0.78, 0.06, 0.06)),
    ("Electric Blue", (0.06, 0.28, 0.80)),
    ("Sunset Orange", (0.95, 0.42, 0.05)),
    ("Pearl White", (0.88, 0.88, 0.86)),
    ("Lime Green", (0.35, 0.72, 0.10)),
    ("Midnight Black", (0.06, 0.06, 0.07)),
    ("Canary Yellow", (0.95, 0.78, 0.08)),
    ("Royal Purple", (0.40, 0.12, 0.62)),
]

AI_NAMES = ["Rafi", "Tanvir", "Nusrat", "Sakib", "Mim", "Arif", "Jannat", "Shuvo"]

STEER_RATE = 6.0
STEER_RETURN = 9.0
STEER_MAX = 0.62
STEER_FADE = 28.0
STEER_GRIP = 1.15

GEARS = [3.30, 2.20, 1.62, 1.28, 1.04, 0.86]
FINAL_DRIVE = 3.55
WHEEL_R = 0.33
IDLE_RPM = 900
MAX_RPM = 7600
SHIFT_UP = 7000
SHIFT_DOWN = 3600

ORIGIN_MX = 450.0


def W(mx, mz, h=0.0):
    return (ORIGIN_MX - mx, mz, h)


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "campus_osm.json"), encoding="utf-8") as _f:
    OSM = json.load(_f)

OSM_SPOTS = {"jobbar_moor": (254, 5), "bina": (-110, 29), "stadium": (60, -162), "rail_station": (110, 140), "aambagan": (-300, -380),
             "coconut": (-80, -700), "bina_pond": (-238, 149), "jame_mosjid": (334, -37), "railway": (330, -250), "csm": (244, 144),
             "ag_engg": (284, 142)}

OSM_TRACKS = [
    dict(key="osm_grand", route="grand", name="Grand Loop", map="osm",
         checkpoints=[("bina", (-110, 2)), ("aambagan", (-300, -380)), ("coconut", (-80, -845)), ("railway", (330, -300))],
         desc="Real map - BINA, Aambagan Road, coconut grove, railway"),
    dict(key="osm_stadium", route="stadium", name="Stadium Circuit", map="osm",
         checkpoints=[("stadium", (164, -150)), ("railway", (250, -150))],
         desc="Real map - a short, fast loop around BAU Stadium"),
    dict(key="osm_aet", route="aet", name="AET - CSM Tour", map="osm", tour_only=True,
         checkpoints=[("rail_station", (180, 135)), ("csm", (185, 128)), ("ag_engg", (312, 280)), ("jobbar_moor", (256, -5))],
         desc="Real map - Jobbar Moor, the station, CSM and AET faculty"),
]
for _t in OSM_TRACKS:
    _t["points"] = [(-e, n, 0.0) for e, n in OSM["routes"][_t["route"]]["pts"]]
    _t["signs"] = [k for k, _p in _t["checkpoints"]]


SHOWCASE = {
    "csm": ((258.0, 121.5, 1.8), (264.0, 140.0, 6.5), (6.0, 0.0, 0.4)),
    "ag_engg": ((276.0, 100.0, 2.0), (288.0, 128.0, 8.0), (-5.0, 2.0, 0.6)),
    "jobbar_moor": "track",
}
SHOWCASE_SECONDS = 5.0


def track_xz(info, a, b):
    if info.get("map") == "osm":
        return -a, b
    return ORIGIN_MX - a, b


CLASSIC_TRACKS = [
    dict(key="grand", name="Grand Campus Tour (classic)",
         route=[(200, -320), (420, -322), (640, -322), (800, -320), (858, -292), (870, -230), (870, -120), (868, -50),
                (848, -6), (800, 0), (650, 0), (500, 0), (446, 8), (424, 46), (420, 120), (420, 230), (418, 300),
                (398, 328), (320, 331), (180, 331), (130, 322), (112, 290), (110, 190), (110, 60), (110, -60),
                (110, -200), (116, -284), (140, -314)],
         checkpoints=[("kr_market", (520, -320)), ("river_ghat", (870, -205)), ("botanical", (870, -120)),
                      ("shaheed_minar", (835, 0)), ("bijoy71", (790, 0)), ("museum", (615, 0)), ("library", (420, 90)),
                      ("ag_engg", (420, 200)), ("csm", (420, 262)), ("agri", (260, 331)), ("tsc", (110, 175)),
                      ("auditorium", (110, 55)), ("hall_shahjalal", (110, -150))],
         desc="Whole campus - halls, river, Shaheed Minar, AET & CSM"),
    dict(key="academic", name="Academic Circuit (classic)",
         route=[(170, 0), (300, 0), (392, 0), (416, 18), (420, 80), (420, 200), (419, 292), (402, 326), (330, 331),
                (200, 331), (130, 322), (112, 292), (110, 180), (110, 60), (118, 16), (140, 1)],
         checkpoints=[("auditorium", (300, 0)), ("library", (420, 90)), ("ag_engg", (420, 200)), ("csm", (420, 262)),
                      ("agri", (260, 331)), ("tsc", (110, 175))],
         desc="AET faculty, CSM department, Library and TSC"),
    dict(key="riverside", name="Riverside Run (classic)",
         route=[(580, 0), (700, 0), (800, 0), (838, -6), (860, -26), (869, -70), (870, -180), (866, -285), (838, -318),
                (740, -322), (600, -322), (545, -314), (524, -290), (520, -180), (520, -90), (523, -45), (535, -18), (553, -4)],
         checkpoints=[("bijoy71", (790, 0)), ("shaheed_minar", (835, 0)), ("botanical", (870, -120)),
                      ("river_ghat", (870, -205)), ("hall_rokeya", (660, -322)), ("kr_market", (520, -250))],
         desc="Shaheed Minar, Bijoy '71, Botanical Garden and KR Market"),
]
for _t in CLASSIC_TRACKS:
    _t["points"] = [W(mx, mz) for mx, mz in _t["route"]]
    _t["map"] = "classic"
TRACKS = OSM_TRACKS + CLASSIC_TRACKS

PLACES = {
    "main_gate": ("Bangladesh Agricultural University", "Founded in 1961 on the bank of the Old Brahmaputra"),
    "ag_engg": ("Faculty of Agricultural Engineering & Technology", "Added in 1964 - home of five departments"),
    "csm": ("Dept. of Computer Science & Mathematics", "A department of the AET faculty"),
    "library": ("Central Library", "Modernist design by architect Richard Neutra, opened 1969"),
    "auditorium": ("Shilpacharya Zainul Abedin Auditorium", "Seats nearly 2,000 people"),
    "tsc": ("Teacher-Student Centre", "Dining, reading rooms and student clubs"),
    "shaheed_minar": ("Shaheed Minar", "Honours the martyrs of the 1952 Language Movement"),
    "bijoy71": ("Bijoy '71", "Sculpture by Shyamal Chowdhury, unveiled in 2000"),
    "botanical": ("Botanical Garden", "25 acres on the riverbank, about 1,500 plant species"),
    "river_ghat": ("River Ghat", "Boat landing on the Old Brahmaputra"),
    "kr_market": ("KR Market", "Tea, snacks and everything a student needs"),
    "museum": ("Agriculture Museum", "Opened in 2007 with about 500 farm implements"),
    "fish_museum": ("Fish Museum & Biodiversity Centre", "Set up in 2009 with the University of Stirling"),
    "agri": ("Faculty of Agriculture", "The largest faculty - 17 departments"),
    "vet": ("Faculty of Veterinary Science", "Eight departments of animal health"),
    "faculty_ah": ("Faculty of Animal Husbandry", "Livestock and poultry science"),
    "faculty_econ": ("Faculty of Agricultural Economics", "Economics and rural sociology"),
    "hall_shahjalal": ("Shahjalal Hall", "One of 14 residential halls on campus"),
    "hall_rokeya": ("Begum Rokeya Hall", "One of 14 residential halls on campus"),
    "field": ("Central Playground", "Football, cricket and campus festivals"),
    "jobbar_moor": ("Jobbar Moor", "The busiest crossroads on campus - tea stalls, shops and autos"),
    "bina": ("Bangladesh Institute of Nuclear Agriculture", "National crop research institute, headquartered on BAU campus"),
    "bina_pond": ("BINA Pond", "A quiet pond inside the BINA compound"),
    "stadium": ("BAU Stadium", "Football, cricket and inter-hall tournaments"),
    "rail_station": ("Agricultural University Railway Station", "A small railway station right on campus"),
    "railway": ("Railway Line", "Trains run straight through the campus"),
    "aambagan": ("Aambagan Road", "'Aambagan' means mango orchard"),
    "coconut": ("Coconut Grove", "Long rows of coconut palms on the university farm"),
    "jame_mosjid": ("BAU Jame Mosjid", "A short walk from Jobbar Moor"),
}

CONTROLS = [
    ("W / ↑", "Accelerate"),
    ("S / ↓", "Brake / Reverse"),
    ("A D / ← →", "Steer"),
    ("Space", "Handbrake"),
    ("Shift / N", "Nitro"),
    ("H", "Horn"),
    ("C", "Change camera"),
    ("R", "Reset car to road"),
    ("P / Esc", "Pause"),
    ("F1", "Show / hide this help"),
]
HELP_SECONDS = 6.0

TIMES = [("Morning", 7.8), ("Noon", 12.5), ("Evening", 17.9), ("Night", 21.0)]
WEATHERS = ["Clear", "Hazy", "Rain"]
MODES = [("race", "Race"), ("tour", "Campus Tour")]

DIFFICULTY = {
    "easy": dict(label="Easy", ai_grip=0.80, ai_power=0.82, ai_line=0.80, assist=True, rubber=0.10, info="Slower rivals  ·  steering and traction assist"),
    "medium": dict(label="Medium", ai_grip=0.93, ai_power=0.94, ai_line=0.90, assist=False, rubber=0.05, info="Fair rivals  ·  realistic handling"),
    "hard": dict(label="Hard", ai_grip=1.04, ai_power=1.03, ai_line=1.0, assist=False, rubber=0.0, info="Fast, aggressive rivals  ·  no assists"),
}
DIFF_ORDER = ["easy", "medium", "hard"]

SAVE_FILE = "bau_race_save.json"
DEFAULT_SAVE = {"best_laps": {}, "best_tours": {}, "wins": 0, "fullscreen": False, "muted": False, "difficulty": "easy",
                "car": 3, "color": 3, "track": 0, "laps": 2, "mode": 0, "time": 0, "weather": 0, "visited": []}

LANDMARK_KEYS = sorted({k for _t in TRACKS for k, _p in _t["checkpoints"]})
