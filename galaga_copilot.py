import asyncio
import pygame
import random
import sys
import math

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

# Weapon IDs
W_NORMAL, W_DOUBLE, W_SPREAD, W_BOMB, W_LASER = 0, 1, 2, 3, 4
WEAPON_NAMES  = {0:"NORMAL", 1:"DOUBLE", 2:"SPREAD", 3:"BOMB", 4:"LASER"}
WEAPON_COLORS = {0:CYAN, 1:GREEN, 2:YELLOW, 3:ORANGE, 4:(0, 200, 255)}
WEAPON_TOKENS = [1, 2, 3, 4]
WEAPON_DURATION = 600   # ~10 s at 60 fps

# Player
PW, PH       = 52, 58
PLAYER_SPEED = 5
PLAYER_LIVES = 3
INV_DUR      = 120      # invincibility frames after being hit
LASER_CD     = 50       # frames between laser shots

# Enemy
EW, EH         = 40, 34
E_NORMAL       = 0
E_DIVER        = 1
BASE_ENEMY_SPD = 2
BASE_SPAWN_MS  = 800

# Events (USEREVENT is a plain integer constant, safe at module level)
EVT_SPAWN = pygame.USEREVENT + 1
EVT_TOKEN = pygame.USEREVENT + 2

# Display/font globals — initialised inside main() once pygame is ready
screen = None
clk    = None
font   = None
font_s = None
font_b = None
stars  = []

# ═══════════════════════════════════════════════════════════════════
#  RENDERING HELPERS
# ═══════════════════════════════════════════════════════════════════

def draw_glow(cx, cy, r, color, alpha):
    """Draw a soft radial glow circle."""
    gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(gs, (*color, alpha), (0, 0, r * 2, r * 2))
    screen.blit(gs, (cx - r, cy - r))


def draw_stars():
    for s in stars:
        s[1] += s[3]
        if s[1] > HEIGHT:
            s[1] = 0.0
            s[0] = random.randint(0, WIDTH)
        b = min(255, 100 + s[2] * 50)
        pygame.draw.circle(screen, (b, b, b),
                           (int(s[0]), int(s[1])), max(1, s[2] - 1))


def draw_player(x, y, inv_cnt):
    """Anime MegaTech robot fighter — top-down view."""
    cx = x + PW // 2
    t  = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(t * 0.01)

    # Engine exhaust glow (bottom)
    draw_glow(cx, y + PH - 6, 18, ORANGE, int(40 + 40 * pulse))
    draw_glow(cx, y + PH - 6, 10, (255, 220, 0), int(100 + 80 * pulse))

    # Wings / shoulder armor
    for side in (-1, 1):
        wx = cx + side * (PW // 2)
        pygame.draw.polygon(screen, METAL_DARK, [
            (wx,               y + 26),
            (cx + side * 10,   y + 16),
            (cx + side * 18,   y + 38),
            (cx + side * 4,    y + 48),
        ])
        pygame.draw.line(screen, ORANGE,
                         (wx, y + 26), (cx + side * 4, y + 48), 2)

    # Main body - angular robotic plating with panel lines
    body = [
        (cx,       y + 2),
        (cx + 16,  y + 14),
        (cx + 12,  y + 44),
        (cx,       y + 54),
        (cx - 12,  y + 44),
        (cx - 16,  y + 14),
    ]
    pygame.draw.polygon(screen, METAL_DARK, body)
    pygame.draw.polygon(screen, NEON_BLUE,  body, 2)

    # Panel seams to read more mechanical
    pygame.draw.line(screen, METAL, (cx - 8, y + 18), (cx + 8, y + 18), 3)
    pygame.draw.line(screen, METAL, (cx - 4, y + 30), (cx + 4, y + 30), 2)

    # Chest armor plate with metallic sheen
    chest = [
        (cx,       y + 10),
        (cx + 11,  y + 22),
        (cx + 9,   y + 36),
        (cx,       y + 42),
        (cx - 9,   y + 36),
        (cx - 11,  y + 22),
    ]
    pygame.draw.polygon(screen, METAL, chest)
    pygame.draw.polygon(screen, NEON_BLUE, chest, 2)

    # Pulsing energy core (now recessed with grill)
    core = int(60 + 140 * pulse)
    draw_glow(cx, y + 28, 8, (0, core, 255), 160)
    pygame.draw.circle(screen, WHITE, (cx, y + 28), 2)
    pygame.draw.line(screen, METAL_DARK, (cx - 4, y + 26), (cx + 4, y + 26), 2)

    # Head unit - more angular helmet with central sensor
    pygame.draw.polygon(screen, METAL_DARK, [(cx - 10, y + 2), (cx + 10, y + 2), (cx + 6, y + 12), (cx - 6, y + 12)])
    pygame.draw.line(screen, NEON_BLUE, (cx - 6, y + 6), (cx + 6, y + 6), 2)
    # Sensor eye
    v = int(180 + 75 * math.sin(t * 0.01))
    pygame.draw.circle(screen, (0, v, 255), (cx, y + 6), 3)

    # Antennae as articulated arms
    for ax in (cx - 12, cx + 9):
        pygame.draw.rect(screen, METAL, (ax, y + 6, 3, 8))
        pygame.draw.circle(screen, GOLD, (ax + 1, y + 6), 2)

    # Left shoulder cannon - bulkier and more mechanical
    pygame.draw.rect(screen, METAL,    (cx - 22, y + 18, 10, 18))
    pygame.draw.rect(screen, CYAN,     (cx - 22, y + 18, 10, 18), 1)
    pygame.draw.rect(screen, RED,      (cx - 18, y + 12, 6,  8))
    draw_glow(cx - 16, y + 12, 5, RED, 120)

    # Right shoulder cannon
    pygame.draw.rect(screen, METAL,    (cx + 12, y + 18, 10, 18))
    pygame.draw.rect(screen, CYAN,     (cx + 12, y + 18, 10, 18), 1)
    pygame.draw.rect(screen, RED,      (cx + 16, y + 12, 6,  8))
    draw_glow(cx + 16, y + 12, 5, RED, 120)

    # Thruster pods - sleeker
    for tx in (cx - 8, cx + 8):
        pygame.draw.rect(screen, METAL_DARK, (tx - 6, y + 44, 12, 12))
        pygame.draw.rect(screen, NEON_BLUE,  (tx - 6, y + 44, 12, 12), 1)
        pygame.draw.ellipse(screen, ORANGE,  (tx - 4, y + 52,  8,  5))
        pygame.draw.ellipse(screen, YELLOW,  (tx - 2, y + 53,  4,  3))

    # Chest tech-line details
    pygame.draw.line(screen, CYAN, (cx - 8, y + 24), (cx + 8, y + 24), 1)
    pygame.draw.line(screen, CYAN, (cx,     y + 24), (cx,     y + 38), 1)

    # Invincibility energy shield (flashing)
    if inv_cnt > 0 and (inv_cnt // 6) % 2 == 0:
        shield = pygame.Surface((PW + 16, PH + 16), pygame.SRCALPHA)
        pygame.draw.ellipse(shield, (0, 200, 255,  55), (0, 0, PW + 16, PH + 16))
        pygame.draw.ellipse(shield, (0, 200, 255, 160), (0, 0, PW + 16, PH + 16), 2)
        screen.blit(shield, (x - 8, y - 8))


def draw_enemy(e):
    r  = e['rect']
    ex, ey, ew, eh = r.x, r.y, r.width, r.height
    cx = ex + ew // 2

    if e['etype'] == E_NORMAL:
        # Alien crab silhouette
        pygame.draw.polygon(screen, (160, 0, 50), [
            (cx,          ey + eh),
            (ex,          ey + eh // 2),
            (ex + 4,      ey + 2),
            (ex + ew - 4, ey + 2),
            (ex + ew,     ey + eh // 2),
        ])
        pygame.draw.polygon(screen, (255, 60, 100), [
            (cx,          ey + eh - 6),
            (ex + 8,      ey + eh // 2 + 4),
            (ex + 8,      ey + 8),
            (ex + ew - 8, ey + 8),
            (ex + ew - 8, ey + eh // 2 + 4),
        ])
        pygame.draw.ellipse(screen, GOLD, (cx - 6, ey + 6,  12, 8))
        pygame.draw.ellipse(screen, RED,  (cx - 3, ey + 8,   6, 4))
        pygame.draw.rect(screen, (100, 0, 30), (ex + 2,      ey + 2, 4, 8))
        pygame.draw.rect(screen, (100, 0, 30), (ex + ew - 6, ey + 2, 4, 8))
    else:
        # Purple dive-bomber
        pygame.draw.polygon(screen, (80, 0, 150), [
            (cx,          ey + eh),
            (ex,          ey + 4),
            (cx - 4,      ey),
            (cx + 4,      ey),
            (ex + ew,     ey + 4),
        ])
        pygame.draw.polygon(screen, (180, 80, 255), [
            (cx,          ey + eh - 8),
            (ex + 8,      ey + 8),
            (ex + ew - 8, ey + 8),
        ])
        pygame.draw.ellipse(screen, YELLOW, (cx - 5, ey + 6, 10, 7))
        pygame.draw.rect(screen, PURPLE, (ex + 1,      ey + 1, 5, 8))
        pygame.draw.rect(screen, PURPLE, (ex + ew - 6, ey + 1, 5, 8))


def draw_bullets(bullets):
    TYPE_COLORS = {
        'normal': CYAN, 'double': GREEN,
        'spread': YELLOW, 'bomb': ORANGE, 'enemy': RED,
    }
    for b in bullets:
        r = b['rect']
        # Display different visuals per rocket type
        if b['type'] == 'bomb':
            # small glowing orb with a lit fuse
            pygame.draw.ellipse(screen, ORANGE, r)
            inner = r.inflate(-6, -6)
            if inner.width > 0 and inner.height > 0:
                pygame.draw.ellipse(screen, GOLD, inner)
            # fuse spark
            if b.get('fuse', 0) > 0:
                fx = r.centerx + int(r.width // 2)
                fy = r.y - 4
                pygame.draw.line(screen, YELLOW, (fx, fy), (fx + 6, fy - 6), 2)
                draw_glow(fx + 6, fy - 6, 6, YELLOW, 90)
        elif b['type'] == 'double':
            # dual-core projectile with trailing glows
            pygame.draw.rect(screen, GREEN, r)
            pygame.draw.rect(screen, WHITE, (r.x, r.y, r.width, 2))
            draw_glow(r.centerx - 4, r.centery, 6, GREEN, 80)
            draw_glow(r.centerx + 4, r.centery, 6, GREEN, 80)
        elif b['type'] == 'spread':
            # jagged tracer for spread shots
            pygame.draw.rect(screen, YELLOW, r)
            pygame.draw.line(screen, WHITE, (r.x, r.y + 2), (r.x + r.width, r.y + 2), 2)
            # slight spark
            draw_glow(r.centerx, r.y, 4, YELLOW, 70)
        elif b['type'] == 'enemy':
            pygame.draw.rect(screen, RED,  r)
            pygame.draw.rect(screen, PINK, (r.x, r.y, r.width, 3))
        else:
            col = TYPE_COLORS.get(b['type'], CYAN)
            pygame.draw.rect(screen, col,   r)
            pygame.draw.rect(screen, WHITE, (r.x, r.y, r.width, 3))


def draw_laser(cx, py):
    """Vertical laser beam from player centre to top of screen."""
    for w, a in ((14, 20), (8, 55), (4, 130), (2, 255)):
        ls = pygame.Surface((w, py), pygame.SRCALPHA)
        ls.fill((0, 200, 255, a))
        screen.blit(ls, (cx - w // 2, 0))
    pygame.draw.line(screen, WHITE, (cx, 0), (cx, py), 1)


def draw_blasts(blasts):
    for b in blasts:
        r   = int(b['radius'])
        pct = b['life'] / b['max_life']
        if r < 1:
            continue
        a  = int(200 * pct)
        bs = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(bs, (255, 140,   0, a // 4), (r + 3, r + 3), r)
        pygame.draw.circle(bs, (255, 220,   0, a),      (r + 3, r + 3), r, 3)
        pygame.draw.circle(bs, (255, 255, 255, a // 2), (r + 3, r + 3), r // 3 + 1)
        screen.blit(bs, (b['cx'] - r - 3, b['cy'] - r - 3))


def draw_particles(particles):
    for p in particles:
        pct   = p['life'] / p['max_life']
        alpha = int(255 * pct)
        size  = max(1, int(p['size'] * pct))
        ps    = pygame.Surface((size * 2 + 1, size * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*p['color'], alpha), (size, size), size)
        screen.blit(ps, (int(p['x']) - size, int(p['y']) - size))


def draw_tokens(tokens):
    t = pygame.time.get_ticks()
    for (tok, ttype) in tokens:
        cx, cy = tok.centerx, tok.centery
        col    = WEAPON_COLORS[ttype]
        angle  = (t * 0.1) % 360
        pts    = [(cx + 13 * math.cos(math.radians(60 * i + angle)),
                   cy + 13 * math.sin(math.radians(60 * i + angle)))
                  for i in range(6)]
        pygame.draw.polygon(screen, col,   pts)
        pygame.draw.polygon(screen, WHITE, pts, 2)
        lbl = font_s.render(WEAPON_NAMES[ttype][0], True, BLACK)
        screen.blit(lbl, (cx - lbl.get_width() // 2,
                          cy - lbl.get_height() // 2))


def draw_hud(score, level, lives, weapon, w_expire, hits, shots):
    screen.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))
    ls = font.render(f"Lv {level}", True, GOLD)
    screen.blit(ls, (WIDTH - ls.get_width() - 10, 10))

    wc = WEAPON_COLORS.get(weapon, WHITE)
    ws = font_s.render(f"WPN: {WEAPON_NAMES[weapon]}", True, wc)
    screen.blit(ws, (10, 44))
    if weapon != W_NORMAL:
        bw = int((w_expire / WEAPON_DURATION) * 100)
        pygame.draw.rect(screen, DARK_GRAY, (10, 62, 100, 7))
        pygame.draw.rect(screen, wc,        (10, 62, bw,  7))

    rate = (hits / shots * 100) if shots > 0 else 0
    screen.blit(font_s.render(f"Acc: {rate:.0f}%", True, (140, 140, 160)), (10, 72))

    # Mini ship icons for lives
    for i in range(lives):
        lx = WIDTH - 24 - i * 22
        pygame.draw.polygon(screen, CYAN, [
            (lx + 8, HEIGHT - 28),
            (lx,     HEIGHT - 12),
            (lx + 16, HEIGHT - 12),
        ])
        pygame.draw.rect(screen, NEON_BLUE, (lx + 5, HEIGHT - 14, 6, 6))


async def game_over_screen(score):
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 160))
    screen.blit(ov, (0, 0))
    go  = font_b.render("GAME  OVER", True, RED)
    sc  = font.render(f"Score: {score}", True, WHITE)
    tip = font_s.render("R = Restart        Q = Quit", True, CYAN)
    screen.blit(go,  (WIDTH // 2 - go.get_width()  // 2, HEIGHT // 2 - 80))
    screen.blit(sc,  (WIDTH // 2 - sc.get_width()  // 2, HEIGHT // 2))
    screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT // 2 + 50))
    pygame.display.flip()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_r:
                    return True
                if ev.key == pygame.K_q:
                    return False
        await asyncio.sleep(0)


# ═══════════════════════════════════════════════════════════════════
#  GAME HELPERS
# ═══════════════════════════════════════════════════════════════════

def spawn_particles(particles, cx, cy, color, count=18):
    for _ in range(count):
        a = random.uniform(0, 2 * math.pi)
        v = random.uniform(1.0, 5.0)
        l = random.randint(25, 45)
        particles.append({
            'x': cx, 'y': cy,
            'vx': math.cos(a) * v,
            'vy': math.sin(a) * v - 1.0,
            'size': random.randint(2, 5),
            'color': color,
            'life': l, 'max_life': l,
        })


def make_blast(cx, cy):
    return {
        'cx': cx, 'cy': cy,
        'radius': 0, 'max_radius': 65,
        'life': 32, 'max_life': 32,
        'hit_ids': set(),
    }


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

async def main():
    global screen, clk, font, font_s, font_b, stars

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Galaga Copilot  ·  MegaTech Robot Wars")
    clk    = pygame.time.Clock()
    font   = pygame.font.Font(None, 34)
    font_s = pygame.font.Font(None, 22)
    font_b = pygame.font.Font(None, 70)
    stars  = [[random.randint(0, WIDTH), random.randint(0, HEIGHT),
               random.randint(1, 3), random.uniform(0.3, 1.5)] for _ in range(110)]
    print("pygbag: init done, starting game loop")

    # Debug: flash green briefly so we can confirm init completed
    screen.fill((0, 200, 0))
    pygame.display.flip()
    await asyncio.sleep(0)

    while True:   # ← restart loop
        # ── Game State ──────────────────────────────────────────────
        px, py    = WIDTH // 2 - PW // 2, HEIGHT - PH - 10
        bullets   = []
        enemies   = []
        tokens    = []
        particles = []
        blasts    = []

        score     = 0
        level     = 1
        lives     = PLAYER_LIVES
        inv_cnt   = 0
        weapon    = W_NORMAL
        w_expire  = 0
        laser_cd  = 0
        laser_on  = 0     # frames the laser beam stays visible
        hits      = 0
        shots     = 0

        e_speed   = BASE_ENEMY_SPD
        e_spawn   = BASE_SPAWN_MS
        e_fire    = 180   # frames between enemy shots
        lvl_msg   = 0
        game_over = False

        pygame.time.set_timer(EVT_SPAWN, e_spawn)
        pygame.time.set_timer(EVT_TOKEN, 5000)

        # ── Inner Game Loop ──────────────────────────────────────────
        while not game_over:

            # ── Events ────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                if event.type == EVT_SPAWN:
                    etype = E_DIVER if random.random() < 0.28 else E_NORMAL
                    ex    = random.randint(0, WIDTH - EW)
                    enemies.append({
                        'rect':     pygame.Rect(ex, -EH, EW, EH),
                        'etype':    etype,
                        'speed':    e_speed + (1 if etype == E_DIVER else 0),
                        'diving':   False,
                        'dive_vx':  0.0,
                        'shoot_cd': random.randint(60, e_fire),
                    })

                if event.type == EVT_TOKEN:
                    ttype = random.choice(WEAPON_TOKENS)
                    tx    = random.randint(20, WIDTH - 40)
                    tokens.append((pygame.Rect(tx, 0, 28, 28), ttype))

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        cx_p = px + PW // 2
                        # Allow shooting even when invincible/hit — remove inv_cnt check
                        if weapon == W_NORMAL:
                            bullets.append({'type': 'normal',
                                'rect': pygame.Rect(cx_p - 3, py, 6, 14),
                                'vx': 0.0, 'vy': -10.0, 'age': 0, 'pattern': 'normal'})
                            shots += 1
                        elif weapon == W_DOUBLE:
                            for bx in (px + 8, px + PW - 14):
                                bullets.append({'type': 'double',
                                    'rect': pygame.Rect(bx, py, 6, 14),
                                    'vx': 0.0, 'vy': -10.0, 'age': 0, 'pattern': 'accel', 'accel': -0.15})
                            shots += 2
                        elif weapon == W_SPREAD:
                            bullets.append({'type': 'spread',
                                'rect': pygame.Rect(cx_p - 3, py, 6, 14),
                                'vx': 0.0, 'vy': -10.0, 'age': 0, 'pattern': 'wave', 'wave_amp': 1.8, 'wave_freq': 0.25})
                            bullets.append({'type': 'spread',
                                'rect': pygame.Rect(px + 4, py + 4, 6, 14),
                                'vx': -2.5, 'vy': -9.0, 'age': 0, 'pattern': 'wave', 'wave_amp': 2.2, 'wave_freq': 0.22})
                            bullets.append({'type': 'spread',
                                'rect': pygame.Rect(px + PW - 10, py + 4, 6, 14),
                                'vx':  2.5, 'vy': -9.0, 'age': 0, 'pattern': 'wave', 'wave_amp': 2.2, 'wave_freq': 0.22})
                            shots += 3
                        elif weapon == W_BOMB:
                            bullets.append({'type': 'bomb',
                                'rect': pygame.Rect(cx_p - 7, py, 14, 14),
                                'vx': 0.0, 'vy': -5.0, 'fuse': 90, 'age': 0, 'pattern': 'bomb'})
                            shots += 1
                        elif weapon == W_LASER:
                            if laser_cd <= 0:
                                laser_on = 18
                                laser_cd = LASER_CD
                                shots   += 1

            # ── Movement ──────────────────────────────────────────
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]  and px > 0:           px -= PLAYER_SPEED
            if keys[pygame.K_RIGHT] and px < WIDTH - PW:  px += PLAYER_SPEED

            # ── Cooldowns ─────────────────────────────────────────
            if laser_cd > 0:  laser_cd -= 1
            if laser_on > 0:  laser_on -= 1
            if inv_cnt  > 0:  inv_cnt  -= 1
            if w_expire > 0:
                w_expire -= 1
                if w_expire <= 0:
                    weapon = W_NORMAL

            # ── Move Bullets ──────────────────────────────────────
            dead = []
            for b in bullets:
                # Update movement patterns based on bullet 'pattern'
                b['rect'].x += int(b.get('vx', 0))
                b['rect'].y += int(b.get('vy', 0))
                b['age'] = b.get('age', 0) + 1
                pat = b.get('pattern')
                if pat == 'wave':
                    # horizontal sinusoidal offset applied to rect.x
                    amp = b.get('wave_amp', 2.0)
                    freq = b.get('wave_freq', 0.2)
                    b['rect'].x += int(amp * math.sin(b['age'] * freq))
                elif pat == 'accel':
                    # gradually change vy by accel
                    if 'accel' in b:
                        b['vy'] += b['accel']
                elif pat == 'normal':
                    pass

                if b['type'] == 'bomb':
                    b['fuse'] -= 1
                    if b['fuse'] <= 0:
                        blasts.append(make_blast(b['rect'].centerx, b['rect'].centery))
                        spawn_particles(particles, b['rect'].centerx,
                                        b['rect'].centery, ORANGE, 25)
                        dead.append(b)
                        continue
                r = b['rect']
                if r.y < -40 or r.y > HEIGHT + 40 or r.x < -40 or r.x > WIDTH + 40:
                    dead.append(b)
            for b in dead:
                if b in bullets:
                    bullets.remove(b)

            # ── Move Tokens ───────────────────────────────────────
            player_rect = pygame.Rect(px, py, PW, PH)
            for item in tokens[:]:
                tok, ttype = item
                tok.y += 2
                if tok.y > HEIGHT:
                    tokens.remove(item)
                elif tok.colliderect(player_rect):
                    weapon   = ttype
                    w_expire = WEAPON_DURATION
                    tokens.remove(item)

            # ── Move Enemies + Enemy Shooting ─────────────────────
            for e in enemies[:]:
                r = e['rect']
                # Divers may break formation and dive toward the player
                if e['etype'] == E_DIVER and not e['diving'] and r.y > 110:
                    if random.random() < 0.012:
                        e['diving']  = True
                        e['dive_vx'] = (px + PW // 2 - r.centerx) / 35.0
                if e['diving']:
                    r.x += int(e['dive_vx'])
                    r.y += int(e['speed'] * 1.7)
                else:
                    r.y += int(e['speed'])

                # Enemy fires downward
                e['shoot_cd'] -= 1
                if e['shoot_cd'] <= 0 and 0 < r.y < HEIGHT - 80:
                    bullets.append({'type': 'enemy',
                        'rect': pygame.Rect(r.centerx - 3, r.bottom, 6, 10),
                        'vx': 0.0, 'vy': 5.0})
                    e['shoot_cd'] = random.randint(60, e_fire)

                if r.y > HEIGHT:
                    enemies.remove(e)

            # ── Laser Damage (each active frame hits all in column) ──
            if laser_on > 0:
                laser_cx = px + PW // 2
                for e in enemies[:]:
                    if e['rect'].x <= laser_cx <= e['rect'].right:
                        spawn_particles(particles,
                                        e['rect'].centerx, e['rect'].centery,
                                        CYAN, 10)
                        if e in enemies:
                            enemies.remove(e)
                        score += 1
                        hits  += 1

            # ── Bomb Blast Expansion & Area Damage ────────────────
            for blast in blasts[:]:
                blast['life'] -= 1
                blast['radius'] = blast['max_radius'] * (
                    1 - blast['life'] / blast['max_life'])
                if blast['life'] <= 0:
                    blasts.remove(blast)
                    continue
                for e in enemies[:]:
                    eid = id(e)
                    if eid not in blast['hit_ids']:
                        dist = math.hypot(e['rect'].centerx - blast['cx'],
                                          e['rect'].centery - blast['cy'])
                        if dist < blast['radius'] + 18:
                            blast['hit_ids'].add(eid)
                            ecol = (255, 60, 100) if e['etype'] == E_NORMAL \
                                   else (170, 80, 255)
                            spawn_particles(particles,
                                            e['rect'].centerx, e['rect'].centery,
                                            ecol, 14)
                            if e in enemies:
                                enemies.remove(e)
                            score += 1
                            hits  += 1

            # ── Bullet vs Enemy Collision ──────────────────────────
            for e in enemies[:]:
                for b in bullets[:]:
                    if b['type'] == 'enemy':
                        continue
                    if e['rect'].colliderect(b['rect']):
                        ecol = (255, 60, 100) if e['etype'] == E_NORMAL \
                               else (170, 80, 255)
                        spawn_particles(particles,
                                        e['rect'].centerx, e['rect'].centery,
                                        ecol, 18)
                        if b['type'] == 'bomb':
                            blasts.append(make_blast(e['rect'].centerx,
                                                     e['rect'].centery))
                            spawn_particles(particles,
                                            e['rect'].centerx, e['rect'].centery,
                                            ORANGE, 25)
                        if b in bullets: bullets.remove(b)
                        if e in enemies: enemies.remove(e)
                        score += 1
                        hits  += 1
                        break

            # ── Enemy Bullet vs Player ─────────────────────────────
            if inv_cnt == 0:
                for b in bullets[:]:
                    if b['type'] == 'enemy' and b['rect'].colliderect(player_rect):
                        lives   -= 1
                        inv_cnt  = INV_DUR
                        spawn_particles(particles,
                                        player_rect.centerx, player_rect.centery,
                                        CYAN, 20)
                        if b in bullets:
                            bullets.remove(b)
                        if lives <= 0:
                            game_over = True
                        break

            # ── Enemy Body vs Player ───────────────────────────────
            if inv_cnt == 0 and not game_over:
                for e in enemies[:]:
                    if e['rect'].colliderect(player_rect):
                        lives   -= 1
                        inv_cnt  = INV_DUR
                        spawn_particles(particles,
                                        e['rect'].centerx, e['rect'].centery,
                                        RED, 22)
                        if e in enemies:
                            enemies.remove(e)
                        if lives <= 0:
                            game_over = True
                        break

            # ── Level Up ──────────────────────────────────────────
            if score >= level * 10:
                level   += 1
                e_speed += 1
                e_spawn  = max(250, e_spawn - 100)
                e_fire   = max(60,  e_fire  - 15)
                pygame.time.set_timer(EVT_SPAWN, e_spawn)
                lvl_msg  = 120

            # ── Update Particles ──────────────────────────────────
            for p in particles[:]:
                p['x']    += p['vx']
                p['y']    += p['vy']
                p['vy']   += 0.08   # gravity pull
                p['life'] -= 1
                if p['life'] <= 0:
                    particles.remove(p)

            # ── Draw ──────────────────────────────────────────────
            screen.fill(DARK_BG)
            draw_stars()
            draw_particles(particles)
            draw_blasts(blasts)
            for e in enemies:
                draw_enemy(e)
            draw_bullets(bullets)
            draw_tokens(tokens)
            draw_player(px, py, inv_cnt)
            if laser_on > 0:
                draw_laser(px + PW // 2, py)
            draw_hud(score, level, lives, weapon, w_expire, hits, shots)
            if lvl_msg > 0:
                lt = font_b.render(f"LEVEL  {level}", True, GOLD)
                lt.set_alpha(min(255, lvl_msg * 3))
                screen.blit(lt, (WIDTH // 2 - lt.get_width() // 2,
                                 HEIGHT // 2 - 40))
                lvl_msg -= 1
            pygame.display.flip()
            await asyncio.sleep(0)

        # ── Death animation before game-over screen ───────────────
        for _ in range(60):
            screen.fill(DARK_BG)
            draw_stars()
            for p in particles[:]:
                p['x'] += p['vx']; p['y'] += p['vy']
                p['vy'] += 0.08;   p['life'] -= 1
                if p['life'] <= 0:
                    particles.remove(p)
            draw_particles(particles)
            pygame.display.flip()
            await asyncio.sleep(0)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return

        restart = await game_over_screen(score)
        if not restart:
            return


asyncio.run(main())
