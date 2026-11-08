"""MegaTech Robot Wars — arcade shooter (desktop + pygbag web)."""
import array
import asyncio
import math
import os
import random
import sys

import pygame

IS_WEB = sys.platform == "emscripten"

# ═══════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════
WIDTH, HEIGHT = 480, 640
FPS = 60

BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
DARK_BG    = (5,   5,  20)
DARK_GRAY  = (30,  30,  50)
RED        = (255,  50,  50)
CYAN       = (0,  220, 255)
ORANGE     = (255, 140,   0)
YELLOW     = (255, 220,   0)
GREEN      = (0,  220, 100)
PURPLE     = (170,   0, 220)
NEON_BLUE  = (0,  120, 255)
METAL      = (60,  80, 110)
METAL_DARK = (30,  40,  60)
GOLD       = (255, 200,  40)
PINK       = (255,  80, 160)
MAGENTA    = (255,  40, 220)
LIME       = (150, 255,  60)

# Weapons
W_NORMAL, W_DOUBLE, W_SPREAD, W_BOMB, W_LASER = 0, 1, 2, 3, 4
WEAPON_NAMES  = {0: "BLASTER", 1: "DOUBLE", 2: "SPREAD", 3: "BOMB", 4: "LASER"}
WEAPON_COLORS = {0: CYAN, 1: GREEN, 2: YELLOW, 3: ORANGE, 4: (0, 200, 255)}
WEAPON_TOKENS = [W_DOUBLE, W_SPREAD, W_BOMB, W_LASER]
WEAPON_DURATION = 720        # frames (~12 s)
FIRE_CD = {W_NORMAL: 9, W_DOUBLE: 8, W_SPREAD: 12, W_BOMB: 26, W_LASER: 0}
MAX_POWER = 3
TOKEN_LIFE = "life"
MAX_PARTICLES = 350          # keeps frame time steady in the browser

# Player
PW, PH       = 52, 58
PLAYER_SPEED = 5.2
PLAYER_LIVES = 3
MAX_LIVES    = 6
INV_DUR      = 120

# Enemies: w, h, hp, points, speed mult
ENEMY_SPECS = {
    "grunt":  (40, 34, 1, 100, 1.00),
    "diver":  (40, 34, 1, 150, 1.25),
    "weaver": (36, 36, 1, 150, 0.85),
    "tank":   (56, 46, 5, 500, 0.55),
}
ENEMY_COLORS = {
    "grunt": (255, 60, 100), "diver": (170, 80, 255),
    "weaver": (60, 255, 180), "tank": (255, 150, 40),
}

HISCORE_KEY  = "megatech_robot_wars_hiscore"
HISCORE_FILE = os.path.join(os.path.expanduser("~"), ".megatech_robot_wars_hiscore")

# Display globals — set in main() once pygame is ready.
display = None   # the real window
screen  = None   # off-screen world canvas
clk     = None
font = font_s = font_b = font_xl = None
stars   = []

# ═══════════════════════════════════════════════════════════════════
#  AUDIO (procedurally synthesised — no asset files)
# ═══════════════════════════════════════════════════════════════════
SND = {}
sound_on = True


def _tone(sr, dur, f0, f1, wave="sq", vol=0.3, curve=1.0):
    n = int(sr * dur)
    out = [0.0] * n
    ph = 0.0
    for i in range(n):
        p = i / n
        ph += (f0 + (f1 - f0) * p) / sr
        x = ph % 1.0
        if wave == "sq":
            s = 1.0 if x < 0.5 else -1.0
        elif wave == "saw":
            s = 2.0 * x - 1.0
        elif wave == "tri":
            s = 4.0 * abs(x - 0.5) - 1.0
        else:
            s = math.sin(ph * 6.2831853)
        out[i] = s * vol * (1.0 - p) ** curve
    return out


def _noise(sr, dur, vol, a0, a1, curve=1.0):
    n = int(sr * dur)
    out = [0.0] * n
    y = 0.0
    for i in range(n):
        p = i / n
        y += (a0 + (a1 - a0) * p) * (random.uniform(-1, 1) - y)
        out[i] = y * vol * (1.0 - p) ** curve
    return out


def _mix(*layers):
    out = [0.0] * max(len(l) for l in layers)
    for l in layers:
        for i, v in enumerate(l):
            out[i] += v
    return out


def _seq(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def _to_sound(samples, channels):
    a = array.array("h")
    for v in samples:
        iv = int(max(-1.0, min(1.0, v)) * 32000)
        a.append(iv)
        if channels == 2:
            a.append(iv)
    return pygame.mixer.Sound(buffer=a.tobytes())


def init_audio():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(22050, -16, 2, 512)
        sr, size, ch = pygame.mixer.get_init()
        if size != -16:
            return
        pygame.mixer.set_num_channels(24)
        defs = {
            "shoot": _tone(sr, .07, 1100, 450, "sq", .10),
            "bombshot": _tone(sr, .14, 320, 90, "sq", .16),
            "tick": _tone(sr, .03, 1700, 1200, "sq", .07),
            "boom": _mix(_noise(sr, .45, .9, .55, .03, 1.5),
                         _tone(sr, .45, 130, 40, "sin", .5, 2)),
            "boom_big": _mix(_noise(sr, 1.2, 1.0, .45, .02, 1.2),
                             _tone(sr, 1.2, 90, 22, "sin", .7, 1.4)),
            "hurt": _mix(_tone(sr, .4, 600, 60, "sq", .22),
                         _noise(sr, .4, .4, .3, .05)),
            "power": _seq(*[_tone(sr, .06, f, f, "sq", .13, .3)
                            for f in (523, 659, 784, 1047)]),
            "oneup": _seq(*[_tone(sr, .07, f, f, "tri", .3, .3)
                            for f in (784, 988, 1175, 1568, 1175, 1568)]),
            "warn": _seq(*[_tone(sr, .18, f, f, "saw", .14, .2)
                           for f in (440, 330, 440, 330, 440, 330)]),
            "level": _seq(*[_tone(sr, .08, f, f, "tri", .3, .4)
                            for f in (392, 523, 659, 784)]),
        }
        # Seamless-ish laser hum for looping
        n = int(sr * .25)
        hum, ph = [], 0.0
        for i in range(n):
            ph += (520 + 90 * math.sin(i / n * 6.2831853 * 5)) / sr
            hum.append((2 * (ph % 1.0) - 1) * .07)
        defs["laser"] = hum
        for k, v in defs.items():
            SND[k] = _to_sound(v, ch)
    except Exception as exc:          # audio is optional
        print("audio disabled:", exc)
        SND.clear()


def play(name, loops=0):
    if sound_on and name in SND:
        SND[name].play(loops=loops)


def stop(name):
    if name in SND:
        SND[name].stop()


# ═══════════════════════════════════════════════════════════════════
#  PERSISTENCE
# ═══════════════════════════════════════════════════════════════════

def load_hiscore():
    try:
        if IS_WEB:
            import platform as _pf
            v = _pf.window.localStorage.getItem(HISCORE_KEY)
            return int(v) if v else 0
        with open(HISCORE_FILE) as fh:
            return int(fh.read().strip() or 0)
    except Exception:
        return 0


def save_hiscore(v):
    try:
        if IS_WEB:
            import platform as _pf
            _pf.window.localStorage.setItem(HISCORE_KEY, str(v))
        else:
            with open(HISCORE_FILE, "w") as fh:
                fh.write(str(v))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  RENDERING HELPERS
# ═══════════════════════════════════════════════════════════════════
_glow_cache = {}
_txt_cache = {}


_glow_base = {}
_neon_cache = {}
_flash_surf = None
GLOW_BUCKETS = (3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 128, 160)


def _glow_bucket(r):
    for b in GLOW_BUCKETS:
        if r <= b:
            return b
    return GLOW_BUCKETS[-1]


def _glow_base_surf(r):
    """Greyscale radial gradient for bucket radius r (built once, at load)."""
    s = _glow_base.get(r)
    if s is None:
        s = pygame.Surface((r * 2, r * 2))
        s.fill(BLACK)
        for i in range(r, 0, -1):
            v = int(255 * (1 - i / r) ** 1.8)
            pygame.draw.circle(s, (v, v, v), (r, r), i)
        _glow_base[r] = s
    return s


def prewarm_glows():
    for b in GLOW_BUCKETS:
        _glow_base_surf(b)


def glow_surf(r, color, k=1.0):
    r = _glow_bucket(max(2, int(r)))
    q = max(1, min(8, int(k * 8 + 0.5)))
    key = (r, color, q)
    s = _glow_cache.get(key)
    if s is None:
        if len(_glow_cache) > 2000:
            _glow_cache.clear()
        # Tinting a pre-built gradient is one C-level fill: no per-frame Python drawing loops.
        s = _glow_base_surf(r).copy()
        s.fill(tuple(int(c * q / 8) for c in color), special_flags=pygame.BLEND_MULT)
        _glow_cache[key] = s
    return s


def draw_glow(cx, cy, r, color, alpha=255, surf=None):
    """Additive radial glow (cached)."""
    s = glow_surf(r, color, alpha / 255)
    (surf or screen).blit(s, (int(cx) - s.get_width() // 2, int(cy) - s.get_height() // 2),
                          special_flags=pygame.BLEND_ADD)


def txt(s, f, col):
    key = (s, id(f), col)
    surf = _txt_cache.get(key)
    if surf is None:
        if len(_txt_cache) > 400:
            _txt_cache.clear()
        surf = f.render(s, True, col)
        _txt_cache[key] = surf
    return surf


def blit_center(target, surf, cx, cy):
    target.blit(surf, (int(cx - surf.get_width() / 2), int(cy - surf.get_height() / 2)))


def neon_text(target, s, f, col, cx, cy, alpha=255):
    """Text with a coloured halo (composited once, then cached)."""
    key = (s, id(f), col)
    surf = _neon_cache.get(key)
    if surf is None:
        if len(_neon_cache) > 200:
            _neon_cache.clear()
        core = f.render(s, True, WHITE)
        halo = f.render(s, True, col)
        surf = pygame.Surface((core.get_width() + 4, core.get_height() + 4), pygame.SRCALPHA)
        for dx, dy in ((0, 2), (4, 2), (2, 0), (2, 4)):
            surf.blit(halo, (dx, dy))
        surf.blit(core, (2, 2))
        _neon_cache[key] = surf
    surf.set_alpha(alpha if alpha < 255 else None)
    blit_center(target, surf, cx, cy)


def make_stars():
    return [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT), random.randint(0, 2)]
            for _ in range(130)]


STAR_SPD = (0.5, 1.2, 2.6)
STAR_COL = ((70, 70, 110), (140, 140, 190), (230, 230, 255))


def draw_stars(t):
    """Constant-speed parallax starfield, independent of gameplay."""
    for s in stars:
        s[1] += STAR_SPD[s[2]]
        if s[1] > HEIGHT:
            s[1] = -2.0
            s[0] = random.uniform(0, WIDTH)
        pygame.draw.circle(t, STAR_COL[s[2]], (int(s[0]), int(s[1])),
                           1 if s[2] < 2 else 2)


def draw_player(x, y, inv_cnt, target=None, thrust=1.0):
    """MegaTech robot fighter — top-down view. (x, y) = top-left."""
    global screen
    saved = screen
    if target is not None:
        screen = target
    cx = int(x + PW // 2)
    y = int(y)
    t = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(t * 0.01)

    if inv_cnt > 0 and (inv_cnt // 4) % 2 == 1:
        screen = saved
        return

    # Engine exhaust
    draw_glow(cx, y + PH - 2, int(22 * thrust), ORANGE, int(90 + 60 * pulse))
    draw_glow(cx, y + PH - 4, int(12 * thrust), YELLOW, int(150 + 90 * pulse))

    for side in (-1, 1):
        wx = cx + side * (PW // 2)
        pygame.draw.polygon(screen, METAL_DARK, [
            (wx, y + 26), (cx + side * 10, y + 16),
            (cx + side * 18, y + 38), (cx + side * 4, y + 48)])
        pygame.draw.line(screen, ORANGE, (wx, y + 26), (cx + side * 4, y + 48), 2)

    body = [(cx, y + 2), (cx + 16, y + 14), (cx + 12, y + 44),
            (cx, y + 54), (cx - 12, y + 44), (cx - 16, y + 14)]
    pygame.draw.polygon(screen, METAL_DARK, body)
    pygame.draw.polygon(screen, NEON_BLUE, body, 2)
    pygame.draw.line(screen, METAL, (cx - 8, y + 18), (cx + 8, y + 18), 3)
    pygame.draw.line(screen, METAL, (cx - 4, y + 30), (cx + 4, y + 30), 2)

    chest = [(cx, y + 10), (cx + 11, y + 22), (cx + 9, y + 36),
             (cx, y + 42), (cx - 9, y + 36), (cx - 11, y + 22)]
    pygame.draw.polygon(screen, METAL, chest)
    pygame.draw.polygon(screen, NEON_BLUE, chest, 2)

    core = int(60 + 140 * pulse)
    draw_glow(cx, y + 28, 12, (0, core, 255), 220)
    pygame.draw.circle(screen, WHITE, (cx, y + 28), 2)

    pygame.draw.polygon(screen, METAL_DARK,
                        [(cx - 10, y + 2), (cx + 10, y + 2), (cx + 6, y + 12), (cx - 6, y + 12)])
    pygame.draw.line(screen, NEON_BLUE, (cx - 6, y + 6), (cx + 6, y + 6), 2)
    v = int(180 + 75 * math.sin(t * 0.01))
    pygame.draw.circle(screen, (0, v, 255), (cx, y + 6), 3)

    for ax in (cx - 12, cx + 9):
        pygame.draw.rect(screen, METAL, (ax, y + 6, 3, 8))
        pygame.draw.circle(screen, GOLD, (ax + 1, y + 6), 2)

    for side in (-1, 1):
        bx = cx - 22 if side < 0 else cx + 12
        pygame.draw.rect(screen, METAL, (bx, y + 18, 10, 18))
        pygame.draw.rect(screen, CYAN, (bx, y + 18, 10, 18), 1)
        rx = cx - 18 if side < 0 else cx + 12
        pygame.draw.rect(screen, RED, (rx, y + 12, 6, 8))
        draw_glow(rx + 3, y + 12, 7, RED, 140)

    for tx in (cx - 8, cx + 8):
        pygame.draw.rect(screen, METAL_DARK, (tx - 6, y + 44, 12, 12))
        pygame.draw.rect(screen, NEON_BLUE, (tx - 6, y + 44, 12, 12), 1)
        pygame.draw.ellipse(screen, ORANGE, (tx - 4, y + 52, 8, 5))
        pygame.draw.ellipse(screen, YELLOW, (tx - 2, y + 53, 4, 3))

    pygame.draw.line(screen, CYAN, (cx - 8, y + 24), (cx + 8, y + 24), 1)
    pygame.draw.line(screen, CYAN, (cx, y + 24), (cx, y + 38), 1)

    if inv_cnt > 0:
        draw_glow(cx, y + PH // 2, 46, (0, 120, 200), 90)
        pygame.draw.ellipse(screen, (0, 200, 255), (x - 8, y - 8, PW + 16, PH + 16), 1)
    screen = saved


def draw_enemy(e):
    w, h = e["w"], e["h"]
    ex, ey = int(e["x"] - w / 2), int(e["y"] - h / 2)
    cx = int(e["x"])
    fl = e["flash"] > 0
    C = (lambda c: WHITE) if fl else (lambda c: c)
    kind = e["kind"]

    if kind == "grunt":
        pygame.draw.polygon(screen, C((160, 0, 50)), [
            (cx, ey + h), (ex, ey + h // 2), (ex + 4, ey + 2),
            (ex + w - 4, ey + 2), (ex + w, ey + h // 2)])
        pygame.draw.polygon(screen, C((255, 60, 100)), [
            (cx, ey + h - 6), (ex + 8, ey + h // 2 + 4), (ex + 8, ey + 8),
            (ex + w - 8, ey + 8), (ex + w - 8, ey + h // 2 + 4)])
        pygame.draw.ellipse(screen, C(GOLD), (cx - 6, ey + 6, 12, 8))
        pygame.draw.ellipse(screen, C(RED), (cx - 3, ey + 8, 6, 4))
        pygame.draw.rect(screen, C((100, 0, 30)), (ex + 2, ey + 2, 4, 8))
        pygame.draw.rect(screen, C((100, 0, 30)), (ex + w - 6, ey + 2, 4, 8))
    elif kind == "diver":
        if e["diving"]:
            draw_glow(cx, ey, 14, PURPLE, 160)
        pygame.draw.polygon(screen, C((80, 0, 150)), [
            (cx, ey + h), (ex, ey + 4), (cx - 4, ey), (cx + 4, ey), (ex + w, ey + 4)])
        pygame.draw.polygon(screen, C((180, 80, 255)), [
            (cx, ey + h - 8), (ex + 8, ey + 8), (ex + w - 8, ey + 8)])
        pygame.draw.ellipse(screen, C(YELLOW), (cx - 5, ey + 6, 10, 7))
        pygame.draw.rect(screen, C(PURPLE), (ex + 1, ey + 1, 5, 8))
        pygame.draw.rect(screen, C(PURPLE), (ex + w - 6, ey + 1, 5, 8))
    elif kind == "weaver":
        cy = int(e["y"])
        spin = e["t"] * 0.15
        pts = [(cx + 18 * math.cos(spin + i * 2.094), cy + 18 * math.sin(spin + i * 2.094))
               for i in range(3)]
        pygame.draw.polygon(screen, C((0, 120, 90)), pts)
        pygame.draw.polygon(screen, C((60, 255, 180)), pts, 2)
        pygame.draw.circle(screen, C((20, 60, 50)), (cx, cy), 10)
        pygame.draw.circle(screen, C((60, 255, 180)), (cx, cy), 10, 2)
        draw_glow(cx, cy, 10, (60, 255, 180), 200)
        pygame.draw.circle(screen, WHITE, (cx, cy), 3)
    else:  # tank
        pygame.draw.polygon(screen, C((90, 45, 10)), [
            (ex + 8, ey), (ex + w - 8, ey), (ex + w, ey + 14), (ex + w, ey + h - 12),
            (cx + 10, ey + h), (cx - 10, ey + h), (ex, ey + h - 12), (ex, ey + 14)])
        pygame.draw.polygon(screen, C((255, 150, 40)), [
            (ex + 8, ey), (ex + w - 8, ey), (ex + w, ey + 14), (ex + w, ey + h - 12),
            (cx + 10, ey + h), (cx - 10, ey + h), (ex, ey + h - 12), (ex, ey + 14)], 2)
        pygame.draw.rect(screen, C(METAL), (ex + 10, ey + 10, w - 20, h - 22))
        for gx in (ex + 4, ex + w - 12):
            pygame.draw.rect(screen, C(METAL_DARK), (gx, ey + h - 16, 8, 16))
            pygame.draw.rect(screen, C(ORANGE), (gx, ey + h - 16, 8, 16), 1)
        eye = (255, 40, 0) if (e["t"] // 8) % 2 else (255, 200, 0)
        pygame.draw.circle(screen, C(eye), (cx, ey + h // 2 - 2), 6)
        draw_glow(cx, ey + h // 2 - 2, 14, eye, 180)
        # HP pips
        if e["hp"] < e["maxhp"]:
            bw = int((w - 8) * e["hp"] / e["maxhp"])
            pygame.draw.rect(screen, DARK_GRAY, (ex + 4, ey - 7, w - 8, 3))
            pygame.draw.rect(screen, ORANGE, (ex + 4, ey - 7, bw, 3))


def draw_boss(b):
    x, y = int(b["x"]), int(b["y"])
    fl = b["flash"] > 0
    C = (lambda c: WHITE) if fl else (lambda c: c)
    t = b["t"]
    frac = b["hp"] / b["maxhp"]
    core_col = (int(255 * (1 - frac)), int(80 + 140 * frac), int(255 * frac))

    # Wings
    for s in (-1, 1):
        wing = [(x + s * 50, y - 22), (x + s * 92, y - 34), (x + s * 98, y + 6),
                (x + s * 80, y + 28), (x + s * 48, y + 22)]
        pygame.draw.polygon(screen, C((60, 0, 90)), wing)
        pygame.draw.polygon(screen, C(MAGENTA), wing, 2)
        pygame.draw.line(screen, C(PURPLE), (x + s * 60, y - 18), (x + s * 88, y + 2), 3)
        # Cannons
        gx = x + s * 62
        pygame.draw.rect(screen, C(METAL), (gx - 7, y + 14, 14, 26))
        pygame.draw.rect(screen, C(RED), (gx - 7, y + 14, 14, 26), 1)
        draw_glow(gx, y + 42, 12, RED, 120 + int(100 * math.sin(t * 0.2)))

    hull = [(x - 40, y - 44), (x + 40, y - 44), (x + 58, y - 12),
            (x + 36, y + 42), (x - 36, y + 42), (x - 58, y - 12)]
    pygame.draw.polygon(screen, C(METAL_DARK), hull)
    pygame.draw.polygon(screen, C(RED), hull, 3)
    inner = [(x - 26, y - 32), (x + 26, y - 32), (x + 38, y - 8),
             (x + 22, y + 28), (x - 22, y + 28), (x - 38, y - 8)]
    pygame.draw.polygon(screen, C(METAL), inner)
    pygame.draw.polygon(screen, C((120, 30, 60)), inner, 2)
    # Eye slits
    for s in (-1, 1):
        pygame.draw.polygon(screen, C(YELLOW), [(x + s * 10, y - 26), (x + s * 30, y - 22),
                                                (x + s * 26, y - 16), (x + s * 10, y - 20)])
    # Core
    pr = 15 + int(3 * math.sin(t * 0.15))
    draw_glow(x, y + 4, pr * 3, core_col, 230)
    pygame.draw.circle(screen, C(core_col), (x, y + 4), pr)
    pygame.draw.circle(screen, WHITE, (x, y + 4), pr // 3)


# ═══════════════════════════════════════════════════════════════════
#  GAME
# ═══════════════════════════════════════════════════════════════════

class Game:
    def __init__(self, hiscore):
        self.hiscore = hiscore
        self.px, self.py = WIDTH / 2, HEIGHT - 60
        self.bullets, self.ebullets, self.enemies = [], [], []
        self.tokens, self.particles, self.blasts = [], [], []
        self.rings, self.popups = [], []
        self.boss = None
        self.boss_warn = 0
        self.boss_count = 0

        self.score = 0
        self.level = 1
        self.kills_lvl = 0
        self.lives = PLAYER_LIVES
        self.inv = 90
        self.weapon, self.wpower, self.wtime = W_NORMAL, 1, 0
        self.fire_cd = 0
        self.laser_on = False
        self.laser_tick = 0
        self.hits = self.shots = self.kills = 0
        self.combo = self.combo_t = self.best_combo = 0

        self.hitstop = 0
        self.flash, self.flash_col = 0, WHITE
        self.banner, self.banner_text = 120, "LEVEL 1"
        self.spawn_t = 0
        self.token_t = 0
        self.frame = 0
        self.muzzle = 0
        self.paused = False
        self.dead = False
        self.death_t = 0
        self.new_record = False

    # ── helpers ────────────────────────────────────────────────────
    @property
    def mult(self):
        return min(8, 1 + self.combo // 4)

    def quota(self):
        return 10 + self.level * 3

    def hitbox(self):
        return pygame.Rect(int(self.px - 8), int(self.py - 6), 16, 20)

    def add_score(self, pts, x, y, col=WHITE):
        gained = pts * self.mult
        self.score += gained
        if self.score > self.hiscore and not self.new_record and self.hiscore > 0:
            self.new_record = True
            self.popup(WIDTH / 2, HEIGHT / 2 + 60, "NEW HIGH SCORE!", GOLD, big=True)
        self.popup(x, y, f"+{gained}", col)

    def popup(self, x, y, text, col=WHITE, big=False):
        self.popups.append({"x": x, "y": y, "text": text, "col": col,
                            "life": 70 if big else 45, "max": 70 if big else 45, "big": big})

    def burst(self, x, y, col, n=18, spd=5.0, size=(2, 5), life=(25, 45), glow=False):
        room = MAX_PARTICLES - len(self.particles)
        if room <= 0:
            return
        n = min(n, room)
        for i in range(n):
            a = random.uniform(0, 6.2832)
            v = random.uniform(0.6, spd)
            l = random.randint(*life)
            self.particles.append({
                "x": x, "y": y, "vx": math.cos(a) * v, "vy": math.sin(a) * v,
                "size": random.randint(*size), "col": col, "life": l, "max": l,
                "glow": glow and i % 3 == 0, "spark": False})

    def sparks(self, x, y, col, n=10, spd=7.0):
        n = min(n, MAX_PARTICLES - len(self.particles))
        for _ in range(n):
            a = random.uniform(0, 6.2832)
            v = random.uniform(2, spd)
            l = random.randint(10, 22)
            self.particles.append({
                "x": x, "y": y, "vx": math.cos(a) * v, "vy": math.sin(a) * v,
                "size": 1, "col": col, "life": l, "max": l, "glow": False, "spark": True})

    def ring(self, x, y, col, max_r=50, life=20, width=4):
        self.rings.append({"x": x, "y": y, "col": col, "max": max_r,
                           "life": life, "maxlife": life, "w": width})

    def explode(self, x, y, col, scale=1.0):
        self.burst(x, y, col, int(22 * scale), 5.5 * scale, glow=True)
        self.burst(x, y, WHITE, int(6 * scale), 3 * scale, size=(2, 3), life=(10, 18))
        self.sparks(x, y, YELLOW, int(10 * scale), 8 * scale)
        self.ring(x, y, col, 40 * scale, 18)
        self.blasts.append({"cx": x, "cy": y, "radius": 0, "max_radius": 30 * scale,
                            "life": 14, "max_life": 14, "hit_ids": None})

    def add_ebullet(self, x, y, angle, speed, r=4, col=RED):
        self.ebullets.append({"x": x, "y": y, "vx": math.cos(angle) * speed,
                              "vy": math.sin(angle) * speed, "r": r, "col": col})

    def aim(self, x, y):
        return math.atan2(self.py - y, self.px - x)

    # ── spawning ───────────────────────────────────────────────────
    def make_enemy(self, kind, x, y=-30.0):
        w, h, hp, pts, sm = ENEMY_SPECS[kind]
        hp += (self.level - 1) // 6
        spd = min(5.5, (1.7 + self.level * 0.2) * sm)
        e = {"kind": kind, "x": float(x), "y": float(y), "w": w, "h": h,
             "hp": hp, "maxhp": hp, "pts": pts, "spd": spd, "t": 0, "flash": 0,
             "diving": False, "dvx": 0.0, "base_x": float(x),
             "phase": random.uniform(0, 6.28), "stop_y": random.uniform(110, 220),
             "hold": random.randint(150, 260), "dead": False,
             "shoot_cd": random.randint(40, self.fire_range()[1])}
        self.enemies.append(e)
        return e

    def fire_range(self):
        return max(45, 170 - self.level * 8), max(90, 260 - self.level * 10)

    def pick_kind(self):
        lv = self.level
        table = [("grunt", 60), ("diver", 25)]
        if lv >= 2:
            table.append(("weaver", 22))
        if lv >= 3:
            table.append(("tank", 6 + lv))
        r = random.uniform(0, sum(w for _, w in table))
        for k, w in table:
            r -= w
            if r <= 0:
                return k
        return "grunt"

    def spawn_one(self):
        kind = self.pick_kind()
        w = ENEMY_SPECS[kind][0]
        margin = w / 2 + (70 if kind == "weaver" else 4)
        self.make_enemy(kind, random.uniform(margin, WIDTH - margin))

    def spawn_squad(self):
        form = random.choice(("v", "snake", "divers"))
        if form == "v":
            c = random.uniform(100, WIDTH - 100)
            for i, (dx, dy) in enumerate(((0, 0), (-38, -28), (38, -28), (-76, -56), (76, -56))):
                self.make_enemy("grunt", c + dx, -30 + dy)
        elif form == "snake":
            c = random.uniform(100, WIDTH - 100)
            ph = random.uniform(0, 6.28)
            for i in range(6):
                e = self.make_enemy("weaver", c, -30 - i * 34)
                e["phase"] = ph
        else:
            for x in (WIDTH * 0.2, WIDTH * 0.5, WIDTH * 0.8):
                self.make_enemy("diver", x, -30)

    def spawn_token(self, x, y):
        if self.lives < MAX_LIVES and random.random() < 0.07:
            kind = TOKEN_LIFE
        else:
            kind = random.choice(WEAPON_TOKENS)
        self.tokens.append({"x": float(x), "y": float(y), "kind": kind,
                            "t": random.randint(0, 100)})

    def spawn_boss(self):
        self.boss_count += 1
        n = self.boss_count
        hp = 90 + 60 * (n - 1)
        self.boss = {"x": WIDTH / 2, "y": -80.0, "w": 170, "h": 90, "hp": hp, "maxhp": hp,
                     "t": 0, "flash": 0, "n": n, "dying": 0}

    # ── weapons ────────────────────────────────────────────────────
    def add_bullet(self, x, y, vx, vy, kind, dmg, r=3):
        self.bullets.append({"x": x, "y": y, "vx": vx, "vy": vy, "kind": kind,
                             "dmg": dmg, "r": r, "fuse": 58, "dead": False})
        self.shots += 1

    def fire(self):
        x, y = self.px, self.py - PH / 2 + 8
        p = self.wpower
        w = self.weapon
        if w == W_NORMAL:
            self.add_bullet(x, y, 0, -13, "normal", 1)
            play("shoot")
        elif w == W_DOUBLE:
            for ox in (-12, 12):
                self.add_bullet(x + ox, y + 6, 0, -13, "double", 1)
            if p >= 2:
                for s in (-1, 1):
                    self.add_bullet(x + s * 18, y + 10, s * 1.6, -12, "double", 1)
            if p >= 3:
                for ox in (-4, 4):
                    self.add_bullet(x + ox, y, 0, -14, "double", 1)
            play("shoot")
        elif w == W_SPREAD:
            n = 3 + 2 * (p - 1)
            total = 0.55 + 0.18 * (p - 1)
            for i in range(n):
                a = -total / 2 + total * i / (n - 1)
                self.add_bullet(x, y, math.sin(a) * 11, -math.cos(a) * 11, "spread", 1)
            play("shoot")
        elif w == W_BOMB:
            for i in range(p):
                vx = (i - (p - 1) / 2) * 2.2
                self.add_bullet(x, y, vx, -6.5, "bomb", 2, r=7)
            play("bombshot")
        self.muzzle = 4

    def detonate(self, x, y):
        p = self.wpower
        self.blasts.append({"cx": x, "cy": y, "radius": 0, "max_radius": 62 + 14 * p,
                            "life": 26, "max_life": 26, "hit_ids": set()})
        self.burst(x, y, ORANGE, 26, 6, glow=True)
        self.sparks(x, y, YELLOW, 14, 9)
        self.ring(x, y, YELLOW, 80 + 14 * p, 22, 5)
        play("boom")

    # ── damage ─────────────────────────────────────────────────────
    def damage_enemy(self, e, dmg, hx, hy):
        if e["dead"]:
            return
        e["hp"] -= dmg
        e["flash"] = 4
        if e["hp"] <= 0:
            self.kill_enemy(e)
        else:
            self.sparks(hx, hy, WHITE, 5, 5)
            play("tick")

    def kill_enemy(self, e, scored=True):
        e["dead"] = True
        col = ENEMY_COLORS[e["kind"]]
        big = e["kind"] == "tank"
        self.explode(e["x"], e["y"], col, 1.8 if big else 1.0)
        if big:
            self.hitstop = max(self.hitstop, 3)
        play("boom")
        if scored:
            self.kills += 1
            self.kills_lvl += 1
            self.combo += 1
            self.combo_t = 130
            self.best_combo = max(self.best_combo, self.combo)
            if self.combo in (8, 16, 24, 32):
                self.popup(WIDTH / 2, HEIGHT / 2 - 20, f"COMBO x{self.mult}!", MAGENTA, big=True)
            self.add_score(e["pts"], e["x"], e["y"] - 10, col)
            if random.random() < (0.35 if big else 0.06):
                self.spawn_token(e["x"], e["y"])

    def damage_boss(self, dmg, hx, hy):
        b = self.boss
        if not b or b["dying"] or b["y"] < 20:
            return
        b["hp"] -= dmg
        b["flash"] = 3
        self.sparks(hx, hy, WHITE, 3, 5)
        if b["hp"] <= 0:
            b["hp"] = 0
            b["dying"] = 110
            self.ebullets.clear()
            stop("laser")
            play("boom_big")

    def player_hit(self):
        if self.inv > 0 or self.dead:
            return
        self.lives -= 1
        self.inv = INV_DUR
        self.hitstop = 10
        self.flash, self.flash_col = 14, RED
        self.combo = 0
        self.wpower = max(1, self.wpower - 1)
        for b in self.ebullets:
            self.burst(b["x"], b["y"], b["col"], 3, 2, size=(1, 3), life=(10, 20))
        self.ebullets.clear()
        self.explode(self.px, self.py, CYAN, 1.4)
        play("hurt")
        if self.lives <= 0:
            self.dead = True
            self.laser_on = False
            stop("laser")
            self.explode(self.px, self.py, CYAN, 3.0)
            self.explode(self.px, self.py, WHITE, 1.5)
            self.flash, self.flash_col = 30, WHITE
            play("boom_big")

    def level_up(self):
        self.level += 1
        self.kills_lvl = 0
        if self.level % 5 == 0:
            self.boss_warn = 170
            self.banner = 0
            play("warn")
        else:
            self.banner, self.banner_text = 130, f"LEVEL {self.level}"
            play("level")

    # ── update ─────────────────────────────────────────────────────
    def update(self, keys, mouse_down, mouse_pos):
        if self.flash > 0:
            self.flash -= 1
        if self.hitstop > 0:
            self.hitstop -= 1
            return
        self.frame += 1

        if self.dead:
            self.death_t += 1
        else:
            self.update_player(keys, mouse_down, mouse_pos)

        self.update_spawning()
        self.update_bullets()
        self.update_enemies()
        self.update_boss()
        self.update_tokens()
        self.update_fx()

        self.enemies = [e for e in self.enemies if not e["dead"]]
        self.bullets = [b for b in self.bullets if not b["dead"]]

        if (not self.dead and not self.boss and not self.boss_warn
                and self.level % 5 != 0 and self.kills_lvl >= self.quota()):
            self.level_up()

        if self.combo_t > 0:
            self.combo_t -= 1
            if self.combo_t == 0:
                self.combo = 0

    def update_player(self, keys, mouse_down, mouse_pos):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.px += dx * PLAYER_SPEED
        self.py += dy * PLAYER_SPEED
        if mouse_down:
            tx, ty = mouse_pos[0], mouse_pos[1] - 60
            ddx, ddy = tx - self.px, ty - self.py
            d = math.hypot(ddx, ddy)
            if d > 1:
                step = min(d, PLAYER_SPEED * 1.6)
                self.px += ddx / d * step
                self.py += ddy / d * step
        self.px = max(PW / 2, min(WIDTH - PW / 2, self.px))
        self.py = max(HEIGHT * 0.42, min(HEIGHT - PH / 2 - 6, self.py))

        if self.inv > 0:
            self.inv -= 1
        if self.muzzle > 0:
            self.muzzle -= 1
        if self.wtime > 0:
            self.wtime -= 1
            if self.wtime == 0:
                self.weapon = W_NORMAL
                self.popup(self.px, self.py - 40, "WEAPON EXPIRED", (150, 150, 170))

        # Thruster trail
        for tx in (-8, 8):
            self.particles.append({
                "x": self.px + tx + random.uniform(-2, 2), "y": self.py + PH / 2 - 2,
                "vx": random.uniform(-0.3, 0.3), "vy": random.uniform(2.5, 4.0),
                "size": random.randint(2, 3), "col": ORANGE, "life": 12, "max": 12,
                "glow": False, "spark": False})

        firing = keys[pygame.K_SPACE] or keys[pygame.K_z] or keys[pygame.K_j] or mouse_down
        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.weapon == W_LASER:
            if firing and not self.laser_on:
                play("laser", loops=-1)
            elif not firing and self.laser_on:
                stop("laser")
            self.laser_on = firing
            if firing:
                self.update_laser()
        else:
            if self.laser_on:
                stop("laser")
                self.laser_on = False
            if firing and self.fire_cd <= 0:
                self.fire()
                self.fire_cd = FIRE_CD[self.weapon]

    def laser_width(self):
        return 8 + 5 * self.wpower

    def update_laser(self):
        self.laser_tick += 1
        if self.laser_tick % 5:
            return
        half = self.laser_width() / 2
        top = self.py - PH / 2
        self.shots += 1
        hit = False
        for e in self.enemies:
            if not e["dead"] and abs(e["x"] - self.px) < e["w"] / 2 + half and e["y"] < top:
                self.damage_enemy(e, self.wpower, self.px, e["y"] + e["h"] / 2)
                hit = True
        b = self.boss
        if b and abs(b["x"] - self.px) < 60 + half and b["y"] < top:
            self.damage_boss(self.wpower, self.px, b["y"] + 40)
            hit = True
        if hit:
            self.hits += 1

    def update_spawning(self):
        if self.boss_warn > 0:
            self.boss_warn -= 1
            if self.boss_warn == 0:
                self.spawn_boss()
        if not self.boss and not self.boss_warn and self.level % 5 != 0:
            self.spawn_t += 1
            delay = max(16, 50 - self.level * 3)
            if self.spawn_t >= delay:
                self.spawn_t = 0
                if self.level >= 2 and random.random() < 0.16:
                    self.spawn_squad()
                else:
                    self.spawn_one()
        self.token_t += 1
        if self.token_t >= 480:
            self.token_t = 0
            self.spawn_token(random.uniform(30, WIDTH - 30), -20)

    def update_bullets(self):
        for b in self.bullets:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if b["kind"] == "bomb":
                b["fuse"] -= 1
                if random.random() < 0.3:
                    self.particles.append({
                        "x": b["x"], "y": b["y"] + 6, "vx": random.uniform(-.5, .5),
                        "vy": 1.5, "size": 2, "col": YELLOW, "life": 10, "max": 10,
                        "glow": False, "spark": False})
                if b["fuse"] <= 0:
                    b["dead"] = True
                    self.detonate(b["x"], b["y"])
                    continue
            if b["y"] < -30 or b["x"] < -30 or b["x"] > WIDTH + 30:
                b["dead"] = True
                continue
            # vs enemies
            for e in self.enemies:
                if e["dead"]:
                    continue
                if (abs(b["x"] - e["x"]) < e["w"] / 2 + b["r"]
                        and abs(b["y"] - e["y"]) < e["h"] / 2 + b["r"]):
                    b["dead"] = True
                    self.hits += 1
                    if b["kind"] == "bomb":
                        self.detonate(b["x"], b["y"])
                    else:
                        self.damage_enemy(e, b["dmg"], b["x"], b["y"])
                    break
            if b["dead"]:
                continue
            bo = self.boss
            if bo and not bo["dying"] and abs(b["x"] - bo["x"]) < 62 and abs(b["y"] - bo["y"]) < 44:
                b["dead"] = True
                self.hits += 1
                if b["kind"] == "bomb":
                    self.detonate(b["x"], b["y"])
                else:
                    self.damage_boss(b["dmg"], b["x"], b["y"])

        hb = self.hitbox()
        keep = []
        for b in self.ebullets:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            if -20 < b["x"] < WIDTH + 20 and -40 < b["y"] < HEIGHT + 20:
                if not self.dead and self.inv == 0 and hb.inflate(b["r"], b["r"]).collidepoint(b["x"], b["y"]):
                    self.player_hit()
                    break     # player_hit clears ebullets
                keep.append(b)
        else:
            self.ebullets = keep

        for bl in self.blasts:
            bl["life"] -= 1
            bl["radius"] = bl["max_radius"] * (1 - (bl["life"] / bl["max_life"]) ** 2)
            if bl["hit_ids"] is None:
                continue
            for e in self.enemies:
                if not e["dead"] and id(e) not in bl["hit_ids"]:
                    if math.hypot(e["x"] - bl["cx"], e["y"] - bl["cy"]) < bl["radius"] + e["w"] / 2:
                        bl["hit_ids"].add(id(e))
                        self.damage_enemy(e, 3, e["x"], e["y"])
            bo = self.boss
            if bo and "boss" not in bl["hit_ids"]:
                if math.hypot(bo["x"] - bl["cx"], bo["y"] - bl["cy"]) < bl["radius"] + 50:
                    bl["hit_ids"].add("boss")
                    self.damage_boss(4, bl["cx"], bl["cy"])
        self.blasts = [bl for bl in self.blasts if bl["life"] > 0]

    def update_enemies(self):
        lo, hi = self.fire_range()
        bspd = min(6.5, 3.2 + self.level * 0.18)
        hb = self.hitbox()
        for e in self.enemies:
            if e["dead"]:
                continue
            e["t"] += 1
            if e["flash"] > 0:
                e["flash"] -= 1
            k = e["kind"]
            if k == "grunt":
                e["y"] += e["spd"]
            elif k == "diver":
                if not e["diving"] and e["y"] > 100 and random.random() < 0.016:
                    e["diving"] = True
                    e["dvx"] = max(-4.5, min(4.5, (self.px - e["x"]) / 38))
                if e["diving"]:
                    e["x"] += e["dvx"]
                    e["y"] += e["spd"] * 1.9
                else:
                    e["y"] += e["spd"]
            elif k == "weaver":
                e["y"] += e["spd"]
                e["x"] = e["base_x"] + math.sin(e["t"] * 0.055 + e["phase"]) * 70
            else:  # tank
                if e["y"] < e["stop_y"]:
                    e["y"] += e["spd"] * 1.4
                elif e["hold"] > 0:
                    e["hold"] -= 1
                    e["x"] += math.sin(e["t"] * 0.03) * 0.9
                else:
                    e["y"] += e["spd"]

            e["shoot_cd"] -= 1
            if e["shoot_cd"] <= 0 and 10 < e["y"] < HEIGHT - 140 and not self.dead:
                e["shoot_cd"] = random.randint(lo, hi)
                bx, by = e["x"], e["y"] + e["h"] / 2
                if k == "tank":
                    base = self.aim(bx, by)
                    spread = (-0.5, -0.25, 0, 0.25, 0.5) if self.level >= 8 else (-0.28, 0, 0.28)
                    for s in spread:
                        self.add_ebullet(bx, by, base + s, bspd * 0.85, 5, ORANGE)
                    e["shoot_cd"] = random.randint(70, 110)
                elif k == "diver" or (self.level >= 5 and random.random() < 0.4):
                    self.add_ebullet(bx, by, self.aim(bx, by), bspd)
                else:
                    self.add_ebullet(bx, by, math.pi / 2, bspd)

            if e["y"] > HEIGHT + 40:
                e["dead"] = True
                continue
            if not self.dead and self.inv == 0:
                er = pygame.Rect(int(e["x"] - e["w"] / 2 + 4), int(e["y"] - e["h"] / 2 + 4),
                                 e["w"] - 8, e["h"] - 8)
                if er.colliderect(hb):
                    self.kill_enemy(e)
                    self.player_hit()

    def update_boss(self):
        b = self.boss
        if not b:
            return
        b["t"] += 1
        if b["flash"] > 0:
            b["flash"] -= 1
        t = b["t"]
        if b["dying"]:
            b["dying"] -= 1
            b["x"] += random.uniform(-2, 2)
            if b["dying"] % 6 == 0:
                ox, oy = random.uniform(-80, 80), random.uniform(-40, 40)
                self.explode(b["x"] + ox, b["y"] + oy,
                             random.choice((ORANGE, MAGENTA, YELLOW, RED)), 1.3)
                play("boom")
            if b["dying"] == 0:
                for _ in range(4):
                    self.explode(b["x"] + random.uniform(-40, 40), b["y"] + random.uniform(-30, 30),
                                 random.choice((MAGENTA, WHITE, YELLOW)), 3.0)
                self.ring(b["x"], b["y"], WHITE, 300, 40, 8)
                self.flash, self.flash_col = 24, WHITE
                self.hitstop = 18
                bonus = 5000 * b["n"]
                self.score += bonus
                self.popup(WIDTH / 2, HEIGHT / 2 - 20, f"BOSS DESTROYED  +{bonus}", GOLD, big=True)
                for i in range(3):
                    self.spawn_token(b["x"] + (i - 1) * 50, b["y"])
                self.boss = None
                play("boom_big")
                self.level_up()
            return

        if b["y"] < 90:
            b["y"] += 1.3
            return
        cx = WIDTH / 2
        b["x"] = cx + math.sin((t - 50) * 0.011) * (cx - 105)
        if self.dead:
            return
        enraged = b["hp"] < b["maxhp"] * 0.5
        n = b["n"]
        pattern = (t // 240) % 3
        local = t % 240
        bs = 3.0 + n * 0.3
        if pattern == 0:
            if local % (38 if enraged else 52) == 0:
                count = 13 if enraged else 11
                for i in range(count):
                    a = math.pi / 2 + (i - (count - 1) / 2) * 0.16
                    self.add_ebullet(b["x"], b["y"] + 36, a, bs, 5, MAGENTA)
        elif pattern == 1:
            if local % 60 < (28 if enraged else 20) and local % 5 == 0:
                for s in (-1, 1):
                    gx, gy = b["x"] + s * 62, b["y"] + 42
                    self.add_ebullet(gx, gy, self.aim(gx, gy), bs + 1.5, 4, RED)
        else:
            if local % (3 if enraged else 4) == 0:
                arms = 3 if enraged else 2
                base = t * 0.12
                for k in range(arms):
                    self.add_ebullet(b["x"], b["y"] + 4, base + k * 6.2832 / arms, bs * 0.85, 4, PINK)
        if t % 320 == 0:
            for x in (WIDTH * 0.15, WIDTH * 0.85):
                self.make_enemy("diver", x, -30)

        if not self.dead and self.inv == 0:
            if pygame.Rect(int(b["x"] - 60), int(b["y"] - 40), 120, 80).colliderect(self.hitbox()):
                self.player_hit()

    def update_tokens(self):
        keep = []
        for tk in self.tokens:
            tk["t"] += 1
            tk["y"] += 1.6
            tk["x"] += math.sin(tk["t"] * 0.06) * 0.8
            if not self.dead:
                dx, dy = self.px - tk["x"], self.py - tk["y"]
                d = math.hypot(dx, dy)
                if d < 100:
                    pull = 6.0 * (1 - d / 100) + 1
                    tk["x"] += dx / max(d, 1) * pull
                    tk["y"] += dy / max(d, 1) * pull
                if d < 30:
                    self.collect(tk)
                    continue
            if tk["y"] < HEIGHT + 30:
                keep.append(tk)
        self.tokens = keep

    def collect(self, tk):
        k = tk["kind"]
        self.ring(tk["x"], tk["y"], WHITE, 50, 16, 3)
        if k == TOKEN_LIFE:
            self.lives = min(MAX_LIVES, self.lives + 1)
            self.popup(self.px, self.py - 50, "1UP!", LIME, big=True)
            play("oneup")
            return
        col = WEAPON_COLORS[k]
        if k == self.weapon and self.wpower < MAX_POWER:
            self.wpower += 1
            self.popup(self.px, self.py - 50, f"{WEAPON_NAMES[k]} LV{self.wpower}", col, big=True)
        elif k == self.weapon:
            self.score += 1000
            self.popup(self.px, self.py - 50, "MAX POWER +1000", col, big=True)
        else:
            self.popup(self.px, self.py - 50, WEAPON_NAMES[k], col, big=True)
        self.weapon = k
        self.wtime = WEAPON_DURATION
        self.burst(tk["x"], tk["y"], col, 16, 4, glow=True)
        play("power")

    def update_fx(self):
        keep = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.95
            p["vy"] = p["vy"] * 0.95 + 0.05
            p["life"] -= 1
            if p["life"] > 0:
                keep.append(p)
        self.particles = keep
        for r in self.rings:
            r["life"] -= 1
        self.rings = [r for r in self.rings if r["life"] > 0]
        for p in self.popups:
            p["life"] -= 1
            p["y"] -= 0.4 if p["big"] else 0.9
        self.popups = [p for p in self.popups if p["life"] > 0]
        if self.banner > 0:
            self.banner -= 1

    # ── draw ───────────────────────────────────────────────────────
    def draw(self):
        screen.fill(DARK_BG)
        draw_stars(screen)
        self.draw_blasts()
        self.draw_rings()
        self.draw_particles()
        self.draw_tokens()
        for e in self.enemies:
            draw_enemy(e)
        if self.boss:
            draw_boss(self.boss)
        self.draw_pbullets()
        if not self.dead:
            if self.laser_on:
                self.draw_laser()
            draw_player(self.px - PW / 2, self.py - PH / 2, self.inv,
                        thrust=1.0 + 0.4 * ((pygame.key.get_pressed()[pygame.K_UP]) or 0))
            if self.muzzle > 0 and self.weapon != W_LASER:
                for ox in (-13, 13):
                    draw_glow(self.px + ox, self.py - PH / 2 + 10, 12, WEAPON_COLORS[self.weapon], 220)
        self.draw_ebullets()
        self.draw_popups()

        display.blit(screen, (0, 0))
        if self.flash > 0:
            global _flash_surf
            if _flash_surf is None:
                _flash_surf = pygame.Surface((WIDTH, HEIGHT))
            _flash_surf.fill(self.flash_col)
            _flash_surf.set_alpha(min(180, self.flash * 10))
            display.blit(_flash_surf, (0, 0))
        self.draw_hud()

    def draw_blasts(self):
        for b in self.blasts:
            r = int(b["radius"])
            if r < 2:
                continue
            pct = b["life"] / b["max_life"]
            draw_glow(b["cx"], b["cy"], r + 8, (255, 150, 40), int(240 * pct))

    def draw_rings(self):
        for r in self.rings:
            pct = r["life"] / r["maxlife"]
            rad = int(r["max"] * (1 - pct ** 2)) + 2
            col = tuple(int(c * pct) for c in r["col"])
            pygame.draw.circle(screen, col, (int(r["x"]), int(r["y"])), rad, max(1, int(r["w"] * pct)))

    def draw_particles(self):
        for p in self.particles:
            pct = p["life"] / p["max"]
            col = (int(p["col"][0] * pct), int(p["col"][1] * pct), int(p["col"][2] * pct))
            x, y = int(p["x"]), int(p["y"])
            if p["spark"]:
                pygame.draw.line(screen, col, (x, y), (int(x - p["vx"] * 2.5), int(y - p["vy"] * 2.5)), 2)
            else:
                size = max(1, int(p["size"] * (0.4 + 0.6 * pct)))
                if p["glow"]:
                    draw_glow(x, y, size * 4, p["col"], int(200 * pct))
                pygame.draw.circle(screen, col, (x, y), size)

    def draw_tokens(self):
        t = self.frame
        for tk in self.tokens:
            cx, cy = int(tk["x"]), int(tk["y"])
            if tk["kind"] == TOKEN_LIFE:
                col, label = LIME, "+"
            else:
                col, label = WEAPON_COLORS[tk["kind"]], WEAPON_NAMES[tk["kind"]][0]
            draw_glow(cx, cy, 26, col, 140 + int(60 * math.sin(t * 0.15)))
            ang = t * 0.05
            pts = [(cx + 14 * math.cos(ang + i * 1.0472), cy + 14 * math.sin(ang + i * 1.0472))
                   for i in range(6)]
            pygame.draw.polygon(screen, col, pts)
            pygame.draw.polygon(screen, WHITE, pts, 2)
            blit_center(screen, txt(label, font_s, BLACK), cx, cy + 1)

    def draw_pbullets(self):
        for b in self.bullets:
            x, y = b["x"], b["y"]
            k = b["kind"]
            if k == "bomb":
                draw_glow(x, y, 16, ORANGE, 200)
                pygame.draw.circle(screen, ORANGE, (int(x), int(y)), 7)
                pygame.draw.circle(screen, GOLD if (b["fuse"] // 4) % 2 else WHITE, (int(x), int(y)), 4)
                continue
            col = {"normal": CYAN, "double": GREEN, "spread": YELLOW}.get(k, CYAN)
            tail = (int(x - b["vx"] * 1.3), int(y - b["vy"] * 1.3))
            draw_glow(x, y, 9, col, 170)
            pygame.draw.line(screen, col, (int(x), int(y)), tail, 4)
            pygame.draw.line(screen, WHITE, (int(x), int(y)), tail, 2)

    def draw_ebullets(self):
        blink = (self.frame // 4) % 2
        for b in self.ebullets:
            x, y, r = int(b["x"]), int(b["y"]), b["r"]
            draw_glow(x, y, r * 3, b["col"], 200)
            pygame.draw.circle(screen, b["col"], (x, y), r)
            pygame.draw.circle(screen, WHITE if blink else (255, 220, 220), (x, y), max(1, r - 2))

    def draw_laser(self):
        cx = int(self.px)
        top = int(self.py - PH / 2 + 4)
        w = self.laser_width()
        flick = random.uniform(0.85, 1.15)
        for ww, col in ((int(w * 2.2 * flick), (0, 60, 120)), (int(w * flick), (0, 170, 255)),
                        (max(2, int(w * 0.45)), (200, 250, 255))):
            pygame.draw.rect(screen, col, (cx - ww // 2, 0, ww, top), 0)
        for yy in range(top, -1, -48):
            draw_glow(cx, yy - (self.frame * 9) % 48, w + 10, (0, 160, 255), 150)
        draw_glow(cx, top, w + 18, (120, 220, 255), 255)
        if self.frame % 3 == 0:
            self.sparks(cx + random.uniform(-w / 2, w / 2), top, CYAN, 1, 4)

    def draw_popups(self):
        for p in self.popups:
            a = int(255 * min(1.0, p["life"] / (p["max"] * 0.4)))
            if p["big"]:
                neon_text(screen, p["text"], font, p["col"], p["x"], p["y"], a)
            else:
                s = txt(p["text"], font_s, p["col"])
                s.set_alpha(a if a < 255 else None)
                blit_center(screen, s, p["x"], p["y"])
                s.set_alpha(None)

    def draw_hud(self):
        d = display
        d.blit(txt(f"{self.score:,}", font, WHITE), (10, 8))
        d.blit(txt(f"HI {max(self.hiscore, self.score):,}", font_s, (140, 140, 170)), (12, 34))

        # Level / progress
        lt = txt(f"LV {self.level}", font, GOLD)
        d.blit(lt, (WIDTH - lt.get_width() - 10, 8))
        if not self.boss and not self.boss_warn and self.level % 5 != 0:
            pct = min(1.0, self.kills_lvl / self.quota())
            pygame.draw.rect(d, DARK_GRAY, (WIDTH - 90, 36, 80, 5))
            pygame.draw.rect(d, GOLD, (WIDTH - 90, 36, int(80 * pct), 5))

        # Weapon
        wc = WEAPON_COLORS[self.weapon]
        d.blit(txt(WEAPON_NAMES[self.weapon], font_s, wc), (12, 52))
        if self.weapon != W_NORMAL:
            for i in range(MAX_POWER):
                px = 90 + i * 12
                pts = [(px, 58), (px + 5, 53), (px + 10, 58), (px + 5, 63)]
                if i < self.wpower:
                    pygame.draw.polygon(d, wc, pts)
                else:
                    pygame.draw.polygon(d, DARK_GRAY, pts, 1)
            pct = min(1.0, self.wtime / WEAPON_DURATION)
            pygame.draw.rect(d, DARK_GRAY, (12, 70, 100, 5))
            bar_col = wc if self.wtime > 150 or (self.frame // 6) % 2 else WHITE
            pygame.draw.rect(d, bar_col, (12, 70, int(100 * pct), 5))

        # Lives
        for i in range(self.lives):
            lx = 12 + i * 22
            pygame.draw.polygon(d, CYAN, [(lx + 8, HEIGHT - 28), (lx, HEIGHT - 12), (lx + 16, HEIGHT - 12)])
            pygame.draw.rect(d, NEON_BLUE, (lx + 5, HEIGHT - 14, 6, 6))

        # Combo
        if self.mult > 1:
            pulse = 1 + 0.08 * math.sin(self.frame * 0.3)
            s = txt(f"x{self.mult}", font_b, MAGENTA)
            if pulse != 1:
                s = pygame.transform.rotozoom(s, 0, pulse)
            d.blit(s, (WIDTH - s.get_width() - 10, HEIGHT - s.get_height() - 18))
            pygame.draw.rect(d, DARK_GRAY, (WIDTH - 90, HEIGHT - 14, 80, 4))
            pygame.draw.rect(d, MAGENTA, (WIDTH - 90, HEIGHT - 14, int(80 * self.combo_t / 130), 4))

        # Boss HP
        b = self.boss
        if b:
            bw = 200
            x0 = (WIDTH - bw) // 2
            by = 30
            pygame.draw.rect(d, (40, 0, 30), (x0, by, bw, 8))
            pygame.draw.rect(d, MAGENTA if (self.frame // 3) % 2 or b["hp"] > b["maxhp"] * 0.25 else WHITE,
                             (x0, by, int(bw * b["hp"] / b["maxhp"]), 8))
            pygame.draw.rect(d, WHITE, (x0, by, bw, 8), 1)
            blit_center(d, txt(f"DREADNOUGHT MK-{b['n']}", font_s, PINK), WIDTH / 2, by - 12)

        # Banners
        if self.banner > 0:
            a = int(255 * min(1.0, self.banner / 40))
            neon_text(d, self.banner_text, font_b, GOLD, WIDTH / 2, HEIGHT / 2 - 40, a)
        if self.boss_warn > 0:
            if (self.boss_warn // 12) % 2 == 0:
                band = pygame.Surface((WIDTH, 70), pygame.SRCALPHA)
                band.fill((255, 0, 40, 70))
                d.blit(band, (0, HEIGHT // 2 - 75))
                neon_text(d, "WARNING", font_xl, RED, WIDTH / 2, HEIGHT / 2 - 50)
            blit_center(d, txt("MASSIVE HOSTILE APPROACHING", font_s, PINK), WIDTH / 2, HEIGHT / 2)

        if self.paused:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 150))
            d.blit(ov, (0, 0))
            neon_text(d, "PAUSED", font_b, CYAN, WIDTH / 2, HEIGHT / 2 - 20)
            blit_center(d, txt("P / ESC to resume     M = mute", font_s, WHITE), WIDTH / 2, HEIGHT / 2 + 30)

    async def run(self):
        global sound_on
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    stop("laser")
                    return "quit"
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_p, pygame.K_ESCAPE):
                        self.paused = not self.paused
                        if self.paused:
                            stop("laser")
                            self.laser_on = False
                    elif ev.key == pygame.K_m:
                        sound_on = not sound_on
                        if not sound_on:
                            stop("laser")
                            self.laser_on = False
            if not self.paused:
                self.update(pygame.key.get_pressed(),
                            pygame.mouse.get_pressed()[0], pygame.mouse.get_pos())
            self.draw()
            pygame.display.flip()
            clk.tick(FPS)
            await asyncio.sleep(0)
            if self.dead and self.death_t > 140:
                return "over"


# ═══════════════════════════════════════════════════════════════════
#  SCREENS
# ═══════════════════════════════════════════════════════════════════

async def title_screen(hiscore):
    t = 0
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                return True
            if ev.type == pygame.MOUSEBUTTONDOWN:
                return True
        t += 1
        display.fill(DARK_BG)
        draw_stars(display)
        neon_text(display, "MEGATECH", font_xl, CYAN, WIDTH / 2, 130 + 4 * math.sin(t * 0.05))
        neon_text(display, "ROBOT WARS", font_b, MAGENTA, WIDTH / 2, 195)
        draw_player(WIDTH / 2 - PW / 2, 270 + 8 * math.sin(t * 0.04), 0, display, 1.3)
        if (t // 30) % 2 == 0:
            blit_center(display, txt("PRESS SPACE  /  TAP TO START", font, WHITE), WIDTH / 2, 400)
        lines = ["ARROWS / WASD  move", "HOLD SPACE / Z  fire", "P  pause     M  mute",
                 "Grab tokens to power up — same weapon stacks to LV3",
                 "Chain kills for score multiplier"]
        for i, l in enumerate(lines):
            blit_center(display, txt(l, font_s, (150, 160, 200)), WIDTH / 2, 450 + i * 22)
        if hiscore:
            blit_center(display, txt(f"HIGH SCORE  {hiscore:,}", font, GOLD), WIDTH / 2, 590)
        pygame.display.flip()
        clk.tick(FPS)
        await asyncio.sleep(0)


async def game_over_screen(g):
    """Returns 'retry', 'title' or 'quit'."""
    shown = 0
    t = 0
    acc = (g.hits / g.shots * 100) if g.shots else 0
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return "quit"
            if ev.type == pygame.KEYDOWN and t > 30:
                if ev.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                    return "retry"
                if ev.key in (pygame.K_t, pygame.K_ESCAPE):
                    return "title"
                if ev.key == pygame.K_q:
                    return "title" if IS_WEB else "quit"
            if ev.type == pygame.MOUSEBUTTONDOWN and t > 30:
                return "retry"
        t += 1
        shown += (g.score - shown) * 0.08 + 1
        shown = min(shown, g.score)
        display.fill(DARK_BG)
        draw_stars(display)
        neon_text(display, "GAME OVER", font_xl, RED, WIDTH / 2, 140)
        neon_text(display, f"{int(shown):,}", font_b, WHITE, WIDTH / 2, 225)
        if g.new_record or (g.score >= g.hiscore and g.score > 0):
            if (t // 15) % 2 == 0:
                neon_text(display, "NEW HIGH SCORE!", font, GOLD, WIDTH / 2, 275)
        else:
            blit_center(display, txt(f"HIGH SCORE  {g.hiscore:,}", font_s, GOLD), WIDTH / 2, 275)
        stats = [("LEVEL", f"{g.level}"), ("KILLS", f"{g.kills}"),
                 ("BEST COMBO", f"{g.best_combo}"), ("ACCURACY", f"{acc:.0f}%"),
                 ("BOSSES", f"{g.boss_count - (1 if g.boss else 0)}")]
        for i, (k, v) in enumerate(stats):
            y = 330 + i * 30
            display.blit(txt(k, font_s, (150, 160, 200)), (WIDTH / 2 - 110, y))
            vs = txt(v, font_s, WHITE)
            display.blit(vs, (WIDTH / 2 + 110 - vs.get_width(), y))
        if (t // 30) % 2 == 0:
            blit_center(display, txt("SPACE / R = RETRY      ESC = TITLE", font_s, CYAN), WIDTH / 2, 520)
        pygame.display.flip()
        clk.tick(FPS)
        await asyncio.sleep(0)


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

async def main():
    global display, screen, clk, font, font_s, font_b, font_xl, stars
    try:
        pygame.mixer.pre_init(22050, -16, 2, 512)
    except Exception:
        pass
    pygame.init()
    display = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MegaTech Robot Wars")
    screen = pygame.Surface((WIDTH, HEIGHT))
    clk = pygame.time.Clock()
    font    = pygame.font.Font(None, 34)
    font_s  = pygame.font.Font(None, 22)
    font_b  = pygame.font.Font(None, 64)
    font_xl = pygame.font.Font(None, 86)
    stars = make_stars()

    display.fill(DARK_BG)
    blit_center(display, font.render("LOADING...", True, CYAN), WIDTH / 2, HEIGHT / 2)
    pygame.display.flip()
    await asyncio.sleep(0)
    prewarm_glows()
    init_audio()

    hiscore = load_hiscore()
    while True:
        if not await title_screen(hiscore):
            return
        while True:
            g = Game(hiscore)
            if await g.run() == "quit":
                return
            if g.score > hiscore:
                hiscore = g.score
                save_hiscore(hiscore)
            choice = await game_over_screen(g)
            g.hiscore = hiscore
            if choice == "quit":
                return
            if choice == "title":
                break


if __name__ == "__main__":
    asyncio.run(main())
