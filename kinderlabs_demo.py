"""
ASPR Oracle Lab — Kids Lab v3 (Standalone)
- Modo CPU con rival y temporizador
- Modo SOLO con camino guía
- Mascota única al ganar nivel (modo CPU): rana, tortuga, gato o perro
- Con mascota -> comandos con paréntesis: FD(50) en lugar de FD 50
- Reinicio con tecla R al final
"""

import pygame
import sys
import os
import time
import math
import random
import array

# ==================================================================
# 1. DEFINICIÓN DE CONSTANTES Y DATOS DE NIVELES (reemplaza a puzzle.py)
# ==================================================================
CELL = 32

C64 = {
    "white":    (255, 255, 255),
    "cyan":     (0,   255, 255),
    "yellow":   (255, 255, 0),
    "lt_green": (144, 238, 144),
    "red":      (255, 80,  80),
    "mid_grey": (128, 128, 128),
    "black":    (0,   0,   0),
    "lt_grey":  (192, 192, 192),
}

# Niveles didácticos (4 niveles)
LEVELS = [
    {
        "id": 1,
        "titulo": "Adelante",
        "emoji_titulo": "➡️",
        "concepto": "Usá FD para moverte hacia adelante",
        "color": (100, 200, 100),
        "comandos_validos": {"FD": None, "ADELANTE": None},
        "pasos": [
            {"cmd": "FD 4", "action": ("fd", 4), "desc": "Mover 4 casillas adelante"},
        ]
    },
    {
        "id": 2,
        "titulo": "Giros",
        "emoji_titulo": "🔄",
        "concepto": "Gira a la derecha o izquierda",
        "color": (100, 150, 255),
        "comandos_validos": {"FD": None, "RT": None, "LT": None, "DERECHA": None, "IZQUIERDA": None},
        "pasos": [
            {"cmd": "FD 2", "action": ("fd", 2), "desc": "Adelante 2"},
            {"cmd": "RT 90", "action": ("rt", 90), "desc": "Gira derecha 90°"},
            {"cmd": "FD 3", "action": ("fd", 3), "desc": "Adelante 3"},
        ]
    },
    {
        "id": 3,
        "titulo": "Cuadrado",
        "emoji_titulo": "⬛",
        "concepto": "Dibujá un cuadrado",
        "color": (255, 180, 100),
        "comandos_validos": {"FD": None, "RT": None, "LT": None},
        "pasos": [
            {"cmd": "FD 4", "action": ("fd", 4), "desc": "Adelante 4"},
            {"cmd": "RT 90", "action": ("rt", 90), "desc": "Derecha"},
            {"cmd": "FD 4", "action": ("fd", 4), "desc": "Adelante 4"},
            {"cmd": "RT 90", "action": ("rt", 90), "desc": "Derecha"},
            {"cmd": "FD 4", "action": ("fd", 4), "desc": "Adelante 4"},
            {"cmd": "RT 90", "action": ("rt", 90), "desc": "Derecha"},
            {"cmd": "FD 4", "action": ("fd", 4), "desc": "Adelante 4"},
        ]
    },
    {
        "id": 4,
        "titulo": "Camino Secreto",
        "emoji_titulo": "🌀",
        "concepto": "Combiná movimientos y giros",
        "color": (200, 100, 200),
        "comandos_validos": {"FD": None, "BK": None, "RT": None, "LT": None},
        "pasos": [
            {"cmd": "FD 5", "action": ("fd", 5), "desc": "Adelante 5"},
            {"cmd": "LT 90", "action": ("lt", 90), "desc": "Izquierda"},
            {"cmd": "FD 3", "action": ("fd", 3), "desc": "Adelante 3"},
            {"cmd": "RT 90", "action": ("rt", 90), "desc": "Derecha"},
            {"cmd": "FD 2", "action": ("fd", 2), "desc": "Adelante 2"},
        ]
    }
]

class Turtle:
    """Placeholder para compatibilidad (no se usa directamente)"""
    pass

def check_command_matches_step(user_input, step, valid_commands):
    """Verifica si el comando del usuario coincide con el paso esperado."""
    expected = step["cmd"].upper()
    # Normalizar ambos: eliminar espacios extra y mayúsculas
    if user_input.strip().upper() == expected:
        return True, "¡Correcto!"
    return False, f"Se esperaba: {expected}"


# ==================================================================
# 2. MÓDULO DE SONIDO (reemplaza a sound.py)
# ==================================================================
class SFX:
    def __init__(self):
        self.initialized = False

    def init(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.initialized = True
        except Exception as e:
            print(f"[Sonido] No se pudo inicializar: {e}")

    def play(self, name):
        if not self.initialized:
            return
        if name == "piece":
            self.beep(880, 50, "square", 0.12)
        elif name == "error":
            self.beep(440, 100, "square", 0.15)
        elif name == "win":
            self.beep(1046, 200, "square", 0.2)
        elif name == "pet":
            self.beep(1318, 80, "square", 0.12)
        elif name == "door":
            self.beep(392, 80, "square", 0.1)

    def beep(self, freq, duration_ms, wave_type="square", volume=0.3):
        if not self.initialized:
            return
        try:
            import numpy as np
            sample_rate = 44100
            n_samples = int(sample_rate * duration_ms / 1000)
            t = np.linspace(0, duration_ms/1000, n_samples, endpoint=False)
            if wave_type == "square":
                wave = np.where((t * freq) % 1.0 < 0.5, 1.0, -1.0)
            else:
                wave = np.sin(2 * np.pi * freq * t)
            # Fade out para evitar clicks
            fade = np.ones(n_samples)
            fade_len = min(int(n_samples * 0.1), 100)
            if fade_len > 0:
                fade[-fade_len:] = np.linspace(1, 0, fade_len)
            wave = (wave * fade * volume * 32767).astype(np.int16)
            # Stereo: duplicar canal
            stereo = np.column_stack([wave, wave])
            sound = pygame.sndarray.make_sound(stereo)
            sound.play()
        except Exception:
            pass

sfx = SFX()


# ==================================================================
# 3. CONFIGURACIÓN DE PANTALLA Y COLORES
# ==================================================================
W, H     = 1024, 640
FPS      = 60
ANIM_H   = int(H * 0.58)
PANEL_Y  = ANIM_H
PANEL_H  = H - ANIM_H
STATS_W  = int(W * 0.22)
CONSOLE_X= STATS_W
CONSOLE_W= W - STATS_W

BG_COLOR   = (16,  16,  64)
GRID_COLOR = (30,  30,  90)
BORDER_COL = (100, 100, 255)
HACKER_COL = (255, 80,  80)
NERD_COL   = (80,  200, 255)
OK_COL     = C64["lt_green"]
ERR_COL    = C64["red"]
DIM_COL    = C64["mid_grey"]
CURSOR_COL = C64["yellow"]
GUIDE_COL  = (80, 80, 150)

TRIVIA = [
    ("1947", "Grace Hopper encontró una polilla real\natrapada en un relay del Harvard Mark II.\nNació la palabra BUG — y el debugging."),
    ("1967", "Logo fue el primer lenguaje diseñado\npara enseñar programación a niños.\nUsaba una tortuga que dibujaba con comandos."),
    ("1982", "El Commodore 64 vendió 17 millones\nde unidades. Fue la PC más vendida\nde la historia. Este juego le rinde homenaje."),
    ("HOY",  "Vos escribiste código real.\nAprendiste a depurar como Grace Hopper.\nSos parte de esta historia. 🐸"),
]

PET_TYPES = [
    {"name": "Saltarina", "emoji": "🐸", "poder": "Salta más rápido"},
    {"name": "Tortu",     "emoji": "🐢", "poder": "Escudo de error"},
    {"name": "Misifú",    "emoji": "🐱", "poder": "Vida extra"},
    {"name": "Pulgi",     "emoji": "🐶", "poder": "Olfato de bugs"},
    {"name": "Pinguino",  "emoji": "🐧", "poder": "Congela la CPU"},
]

ROLES_PER_LEVEL = ["hacker", "nerd", "hacker", "nerd"]


# ==================================================================
# 4. FUNCIONES AUXILIARES DE DIBUJO
# ==================================================================
def load_fonts():
    mono = pygame.font.match_font("px437ibmvga8x16,couriernew,lucidaconsole,monospace,courier")
    try:
        return {
            "title": pygame.font.Font(mono, 22),
            "lg":    pygame.font.Font(mono, 18),
            "md":    pygame.font.Font(mono, 14),
            "sm":    pygame.font.Font(mono, 12),
            "xs":    pygame.font.Font(mono, 10),
            "emoji": pygame.font.SysFont("segoeuiemoji,noto emoji", 26),
        }
    except Exception:
        return {k: pygame.font.SysFont("monospace", s)
                for k, s in [("title",22),("lg",18),("md",14),("sm",12),("xs",10),("emoji",24)]}

def px(surf, text, x, y, font, color=None, center=False, right=False):
    color = color or C64["white"]
    sh = font.render(text, False, (0,0,0))
    rx = x - sh.get_width()//2 if center else (x - sh.get_width() if right else x)
    surf.blit(sh, (rx+1, y+1))
    r = font.render(text, False, color)
    rx2 = x - r.get_width()//2 if center else (x - r.get_width() if right else x)
    surf.blit(r, (rx2, y))
    return r.get_width()

def draw_border_box(surf, rect, color=BORDER_COL, fill=None, thickness=2):
    if fill:
        pygame.draw.rect(surf, fill, rect)
    pygame.draw.rect(surf, color, rect, thickness)
    x, y, w, h = rect
    for corner in [(x,y),(x+w-2,y),(x,y+h-2),(x+w-2,y+h-2)]:
        pygame.draw.rect(surf, C64["white"], (*corner, 2, 2))

def draw_grid(surf, rect, cell=32, color=GRID_COLOR):
    x, y, w, h = rect
    for gx in range(x, x+w, cell):
        pygame.draw.line(surf, color, (gx, y), (gx, y+h))
    for gy in range(y, y+h, cell):
        pygame.draw.line(surf, color, (x, gy), (x+w, gy))

def draw_bar(surf, x, y, w, h, val, maxv, color):
    pygame.draw.rect(surf, (10,10,40), (x, y, w, h))
    fill = int(w * val / max(maxv,1))
    for bx in range(0, fill, 4):
        bw = min(3, fill-bx)
        pygame.draw.rect(surf, color, (x+bx, y+1, bw, h-2))
    pygame.draw.rect(surf, C64["mid_grey"], (x, y, w, h), 1)

def scanlines(surf):
    sl = pygame.Surface((W, H), pygame.SRCALPHA)
    for gy in range(0, H, 4):
        pygame.draw.line(sl, (0,0,0,20), (0,gy), (W,gy))
    surf.blit(sl, (0,0))



def draw_demo_banner(surf, fonts, t):
    """Banner verde semitransparente DEMO en esquina superior derecha."""
    banner_w, banner_h = 110, 28
    bx = W - banner_w - 8
    by = 8
    # Fondo semitransparente verde
    s = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
    alpha = int(160 + 40 * math.sin(t * 2))
    s.fill((20, 180, 80, alpha))
    surf.blit(s, (bx, by))
    # Borde
    pygame.draw.rect(surf, (50, 255, 120), (bx, by, banner_w, banner_h), 2)
    # Esquinas pixeladas
    for cx, cy in [(bx,by),(bx+banner_w-2,by),(bx,by+banner_h-2),(bx+banner_w-2,by+banner_h-2)]:
        pygame.draw.rect(surf, (255,255,255), (cx, cy, 2, 2))
    # Texto
    txt = fonts["sm"].render("★ DEMO ★", False, (255, 255, 255))
    surf.blit(txt, (bx + banner_w//2 - txt.get_width()//2, by + banner_h//2 - txt.get_height()//2))

# ==================================================================
# 5. CLASE FROG (RANA ANIMADA)
# ==================================================================
class Frog:
    def __init__(self, role: str, ox: int, oy: int, color, total_steps: int):
        self.role = role
        self.color = color
        self.trail = []
        self.angle = 90.0
        self.cx = 5.0
        self.cy = 5.0
        self.anim_x = float(ox + self.cx * CELL)
        self.anim_y = float(oy + self.cy * CELL)
        self.target_px = self.anim_x
        self.target_py = self.anim_y
        self.ox = ox
        self.oy = oy
        self.step_index = 0
        self.total_steps = total_steps
        self.error_shake = 0.0
        self.jump_t = 0.0
        self.jumping = False
        self.t = 0.0
        self.particles = []

    def execute(self, action):
        cmd, val = action
        moved = False
        if cmd == "fd":
            rad = math.radians(self.angle)
            nx = self.cx + math.cos(rad) * val
            ny = self.cy - math.sin(rad) * val
            self.trail.append((self.cx, self.cy, nx, ny, self.color))
            self.cx, self.cy = nx, ny
            self.target_px = self.ox + nx * CELL
            self.target_py = self.oy + ny * CELL
            self.jumping = True
            self.jump_t = 0.0
            moved = True
        elif cmd == "bk":
            rad = math.radians(self.angle)
            nx = self.cx - math.cos(rad) * val
            ny = self.cy + math.sin(rad) * val
            self.trail.append((self.cx, self.cy, nx, ny, self.color))
            self.cx, self.cy = nx, ny
            self.target_px = self.ox + nx * CELL
            self.target_py = self.oy + ny * CELL
            self.jumping = True
            self.jump_t = 0.0
            moved = True
        elif cmd in ("rt", "lt"):
            self.angle += val if cmd == "lt" else -val
        self.step_index += 1
        if moved:
            self.particles.append({
                "x": self.anim_x, "y": self.anim_y,
                "vx": random.uniform(-2,2), "vy": random.uniform(-3,-1),
                "life": 1.0, "emoji": random.choice(["🐛","🦟","🪲","🐞"]),
            })

    def shake_error(self):
        self.error_shake = 1.0

    def update(self, dt):
        self.t += dt
        self.error_shake = max(0, self.error_shake - dt*4)
        if self.jumping:
            self.jump_t = min(1.0, self.jump_t + dt*4)
            self.anim_x += (self.target_px - self.anim_x) * min(1, dt*8)
            self.anim_y += (self.target_py - self.anim_y) * min(1, dt*8)
            if self.jump_t >= 1.0:
                self.jumping = False
                self.anim_x = self.target_px
                self.anim_y = self.target_py
        for p in self.particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]
            p["vy"] += 0.15; p["life"] -= dt*1.2
        self.particles = [p for p in self.particles if p["life"] > 0]

    def draw(self, surf, fonts):
        # Dibujar rastro
        for seg in self.trail:
            x0,y0,x1,y1,col = seg
            px0 = int(self.ox + x0*CELL)
            py0 = int(self.oy + y0*CELL)
            px1 = int(self.ox + x1*CELL)
            py1 = int(self.oy + y1*CELL)
            for th in [5,3,2]:
                dim = tuple(max(0,int(c*0.35)) for c in col)
                pygame.draw.line(surf, dim, (px0,py0),(px1,py1), th)
            pygame.draw.line(surf, col, (px0,py0),(px1,py1), 2)

        for p in self.particles:
            alpha = int(p["life"]*220)
            bug_surf = fonts["xs"].render(p["emoji"], True, C64["white"])
            bug_surf.set_alpha(alpha)
            surf.blit(bug_surf, (int(p["x"])-6, int(p["y"])-6))

        shake = int(self.error_shake*5*math.sin(self.error_shake*25))
        fx = int(self.anim_x) + shake
        fy = int(self.anim_y)

        if self.jumping:
            arc = math.sin(self.jump_t * math.pi) * 12
            fy -= int(arc)

        col      = self.color
        dk       = tuple(max(0,c-80) for c in col)
        lt       = tuple(min(255,c+60) for c in col)
        err      = self.error_shake > 0
        body_col = C64["red"] if err else col
        eye_col  = HACKER_COL if self.role=="hacker" else NERD_COL

        # Cuerpo de la rana (versión simplificada pero funcional)
        pygame.draw.ellipse(surf, (0,0,0), (fx-14, fy+20, 28, 8))
        pygame.draw.ellipse(surf, dk,   (fx-18, fy+8,  14, 10))
        pygame.draw.ellipse(surf, dk,   (fx+4,  fy+8,  14, 10))
        pygame.draw.ellipse(surf, body_col, (fx-16, fy+7, 10, 8))
        pygame.draw.ellipse(surf, body_col, (fx+6,  fy+7, 10, 8))
        pygame.draw.ellipse(surf, dk,   (fx-18, fy-2, 10, 7))
        pygame.draw.ellipse(surf, dk,   (fx+8,  fy-2, 10, 7))
        pygame.draw.ellipse(surf, body_col, (fx-16, fy-1, 8, 6))
        pygame.draw.ellipse(surf, body_col, (fx+8,  fy-1, 8, 6))
        pygame.draw.ellipse(surf, body_col, (fx-13, fy-8, 26, 22))
        pygame.draw.ellipse(surf, lt,   (fx-8,  fy-2, 16, 14))
        pygame.draw.ellipse(surf, body_col, (fx-11, fy-22, 22, 18))
        pygame.draw.circle(surf, body_col, (fx-8,  fy-22), 6)
        pygame.draw.circle(surf, body_col, (fx+8,  fy-22), 6)
        pygame.draw.circle(surf, eye_col,  (fx-8,  fy-22), 5)
        pygame.draw.circle(surf, eye_col,  (fx+8,  fy-22), 5)
        pygame.draw.circle(surf, C64["black"], (fx-7, fy-22), 2)
        pygame.draw.circle(surf, C64["black"], (fx+7, fy-22), 2)
        pygame.draw.circle(surf, C64["white"], (fx-6, fy-23), 1)
        pygame.draw.circle(surf, C64["white"], (fx+8, fy-23), 1)

        if err:
            pygame.draw.line(surf, C64["white"], (fx-5,fy-10),(fx+5,fy-10), 2)
        else:
            pygame.draw.arc(surf, C64["white"],
                           pygame.Rect(fx-5, fy-13, 10, 6),
                           math.pi, 2*math.pi, 2)
        pygame.draw.circle(surf, dk, (fx-3, fy-14), 2)
        pygame.draw.circle(surf, dk, (fx+3, fy-14), 2)

        rad = math.radians(self.angle)
        ax = int(fx + math.cos(rad)*16)
        ay = int(fy - math.sin(rad)*16)
        pygame.draw.line(surf, C64["white"], (fx,fy-5), (ax,ay), 2)

        if self.role == "hacker":
            pygame.draw.ellipse(surf, (20,10,50), (fx-12, fy-32, 24, 14))
            pygame.draw.ellipse(surf, HACKER_COL,  (fx-12, fy-32, 24, 14), 2)
            pygame.draw.rect(surf, HACKER_COL, (fx-14, fy-24, 4, 6))
            pygame.draw.rect(surf, HACKER_COL, (fx+10, fy-24, 4, 6))
        else:
            pygame.draw.rect(surf, C64["yellow"], (fx-10, fy-26, 8, 5), 2)
            pygame.draw.rect(surf, C64["yellow"], (fx+2,  fy-26, 8, 5), 2)
            pygame.draw.line(surf, C64["yellow"], (fx-2,fy-24),(fx+2,fy-24), 2)


# ==================================================================
# 6. CPU RIVAL
# ==================================================================
class CPUPlayer:
    # Delays por nivel: (min, max) en segundos — más rápido a medida que sube
    SPEED = [
        (6.0, 14.0),   # nivel 1 — lento, da tiempo al nene
        (4.0,  9.0),   # nivel 2 — medio
        (2.0,  5.0),   # nivel 3 — rápido
        (1.0,  3.0),   # nivel 4 — muy rápido
    ]

    def __init__(self, level_index=0):
        self.step_index = 0
        self.next_action_at = 0.0
        self.power = 50
        self.karma = 0
        self.has_pet = False
        self.pet = {}
        self.wins = 0
        self.finished_level = False
        self.error_rate = max(0.05, 0.20 - level_index * 0.04)  # menos errores a más nivel
        self.level_index = level_index
        self._schedule_next(delay=self.SPEED[min(level_index, 3)][1])  # arranca con delay largo

    def _schedule_next(self, delay=None):
        if delay is None:
            mn, mx = self.SPEED[min(self.level_index, 3)]
            delay = random.uniform(mn, mx)
        self.next_action_at = time.time() + delay

    def reset_level(self):
        self.step_index = 0
        self.finished_level = False
        mn, mx = self.SPEED[min(self.level_index, 3)]
        self._schedule_next(delay=random.uniform(mn * 0.6, mx * 0.6))

    def tick(self, pasos, frog, game) -> bool:
        if self.finished_level:
            return False
        if time.time() < self.next_action_at:
            return False
        if self.step_index >= len(pasos):
            return False

        step = pasos[self.step_index]

        if random.random() < self.error_rate:
            frog.shake_error()
            sfx.play("error")
            game.add_log("CPU: comando incorrecto", ERR_COL)
            self._schedule_next(delay=random.uniform(5, 10))
            return False

        frog.execute(step["action"])
        sfx.play("piece")
        self.step_index += 1
        self.karma += 5
        self.power = min(100, self.power + 3)
        game.add_log(f"CPU: {step['cmd']}", DIM_COL)

        if self.step_index >= len(pasos):
            self.finished_level = True
            self.wins += 1
            self.karma += 50
            if not self.has_pet:
                self.has_pet = True
                self.pet = random.choice(PET_TYPES).copy()
                self.pet["hunger"] = 100
            sfx.play("win")
            game.add_log("CPU completó el nivel!", ERR_COL)
            return True

        self._schedule_next()
        return False


# ==================================================================
# 7. NORMALIZACIÓN DE COMANDOS (soporta paréntesis)
# ==================================================================
def normalize_input(text: str) -> str:
    import re
    text = text.strip().upper()
    m = re.match(r'^([A-Z]+)\(([^)]+)\)$', text)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m2 = re.match(r'^([A-Z]+)(\d+(?:\.\d+)?)$', text)
    if m2:
        return f"{m2.group(1)} {m2.group(2)}"
    return text


# ==================================================================
# 8. PANTALLAS (LOGIN, REVEAL, TRIVIA, GAMEOVER, GAME)
# ==================================================================
class LoginSolo:
    def __init__(self, fonts):
        self.fonts = fonts
        self.name = ""
        self.t = 0.0
        self.done = False
        self.result = {}
        self.error = ""
        self.mode = "cpu"
        self.mode_selected = False

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                if not self.name.strip():
                    self.error = "INGRESA TU NOMBRE"
                    return
                if not self.mode_selected:
                    self.error = "PRIMERO SELECCIONA MODO (← →)"
                    return
                self.result = {"name": self.name.strip(), "mode": self.mode}
                self.done = True
            elif ev.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif ev.key == pygame.K_LEFT:
                self.mode = "cpu"
                self.mode_selected = True
                sfx.beep(660, 30, "square", 0.08)
            elif ev.key == pygame.K_RIGHT:
                self.mode = "solo"
                self.mode_selected = True
                sfx.beep(660, 30, "square", 0.08)
            else:
                ch = ev.unicode
                if ch and ch.isprintable() and len(self.name) < 10:
                    self.name += ch.upper()
                    sfx.beep(880, 20, "square", 0.05)

    def draw(self, surf):
        self.t += 0.016
        surf.fill(BG_COLOR)
        draw_grid(surf, (0,0,W,H), 32, GRID_COLOR)

        glow = abs(math.sin(self.t*1.5))
        title_col = tuple(int(80 + 175*glow) for _ in range(3))
        px(surf, "🧪 KIDSLAB — ORACLE KIDS",
           W//2, 20, self.fonts["title"], C64["cyan"], center=True)
        px(surf, "HACKERS  VS  NERDS  EDITION",
           W//2, 46, self.fonts["sm"], C64["yellow"], center=True)
        pygame.draw.line(surf, BORDER_COL, (80, 66), (W-80, 66), 1)

        # Panel instrucciones
        draw_border_box(surf, (30, 78, 290, 380), BORDER_COL, fill=(8,8,30))
        px(surf, "CÓMO JUGAR", 175, 88, self.fonts["sm"], C64["yellow"], center=True)
        pygame.draw.line(surf, BORDER_COL, (40, 104), (310, 104), 1)
        instrucciones = [
            ("ESCRIBÍ", "el comando y ENTER"),
            ("ADELANTE 4", "→ la rana avanza"),
            ("DERECHA 90", "→ gira a la derecha"),
            ("IZQUIERDA 90","→ gira izquierda"),
            ("",""),
            ("CTRL+F","→ alimentá la mascota"),
            ("GRACE","→ comando secreto"),
        ]
        iy = 110
        for cmd, desc in instrucciones:
            if cmd == "":
                iy += 6; continue
            px(surf, cmd,  42, iy, self.fonts["xs"], C64["cyan"])
            px(surf, desc, 42, iy+12, self.fonts["xs"], DIM_COL)
            iy += 28

        # Panel nombre y modo
        draw_border_box(surf, (340, 78, 380, 130), BORDER_COL, fill=(10,10,40))
        px(surf, "TU NOMBRE:", 352, 90, self.fonts["sm"], DIM_COL)
        bc = CURSOR_COL if int(self.t*2)%2==0 else C64["mid_grey"]
        draw_border_box(surf, (352, 108, 356, 30), bc, fill=(0,0,20), thickness=2)
        disp = (self.name + ("|" if int(self.t*2)%2==0 else "")) or " "
        px(surf, disp, 360, 114, self.fonts["md"], C64["white"])

        px(surf, "MODO  ←  →", 530, 224, self.fonts["sm"], C64["yellow"], center=True)
        cpu_col  = C64["lt_green"] if self.mode=="cpu"  else DIM_COL
        solo_col = C64["lt_green"] if self.mode=="solo" else DIM_COL
        cpu_fill  = (0,40,0)  if self.mode=="cpu"  else (15,15,30)
        solo_fill = (0,40,0)  if self.mode=="solo" else (15,15,30)
        draw_border_box(surf, (350, 240, 160, 50), cpu_col,  fill=cpu_fill,  thickness=3 if self.mode=="cpu" else 1)
        draw_border_box(surf, (520, 240, 160, 50), solo_col, fill=solo_fill, thickness=3 if self.mode=="solo" else 1)
        px(surf, "VS CPU 🤖",    430, 258, self.fonts["sm"], cpu_col,  center=True)
        px(surf, "SOLO 🐸",      600, 258, self.fonts["sm"], solo_col, center=True)

        desc = "Competís contra la máquina" if self.mode == "cpu" else "Sin rival — seguís la guía"
        px(surf, desc, 530, 302, self.fonts["xs"], DIM_COL, center=True)

        pulse = abs(math.sin(self.t*3))
        bc2 = tuple(int(60+pulse*195) for _ in range(3))
        draw_border_box(surf, (370, 326, 320, 42), bc2, fill=(5,20,5), thickness=2)
        px(surf, "[ ENTER ]  EMPEZAR", 530, 339, self.fonts["md"], C64["lt_green"], center=True)

        if self.error:
            px(surf, "⚠ " + self.error, 530, 382, self.fonts["sm"], ERR_COL, center=True)

        # Panel mascotas
        draw_border_box(surf, (734, 78, 260, 380), BORDER_COL, fill=(8,8,30))
        px(surf, "MASCOTAS", W-130, 88, self.fonts["sm"], C64["yellow"], center=True)
        pygame.draw.line(surf, BORDER_COL, (744, 104), (984, 104), 1)
        py_pet = 114
        for pet in PET_TYPES:
            emoji_surf = self.fonts["emoji"].render(pet["emoji"], True, C64["white"])
            surf.blit(emoji_surf, (750, py_pet))
            px(surf, pet["name"],   788, py_pet+2,  self.fonts["sm"], C64["cyan"])
            px(surf, pet["poder"],  788, py_pet+16, self.fonts["xs"], DIM_COL)
            py_pet += 40
        px(surf, "Ganá un nivel para", W-130, py_pet+8,  self.fonts["xs"], DIM_COL, center=True)
        px(surf, "desbloquear mascota", W-130, py_pet+22, self.fonts["xs"], DIM_COL, center=True)

        pygame.draw.line(surf, BORDER_COL, (0, H-50), (W, H-50), 1)
        px(surf, "ASPR ORACLE NODE v2.0  ·  KIDSLAB.IO  ·  🧪",
           W//2, H-36, self.fonts["xs"], DIM_COL, center=True)
        px(surf, "Aprender jugando, competir pensando",
           W//2, H-20, self.fonts["xs"], (60,60,100), center=True)


class RoleReveal:
    def __init__(self, fonts, role, level_num):
        self.fonts = fonts
        self.role = role
        self.level_num = level_num
        self.t = 0.0
        self.phase = 0
        self.count = 3
        self.count_t = 0.0
        self.done = False
        sfx.beep(440, 100, "square", 0.12)

    def update(self, dt):
        self.t += dt
        if self.phase == 0:
            self.count_t += dt
            if self.count_t >= 1.0:
                self.count_t = 0
                self.count -= 1
                if self.count > 0:
                    sfx.beep(440 + self.count*100, 80, "square", 0.12)
                else:
                    self.phase = 1
                    sfx.play("level_start")
        elif self.phase == 1:
            if self.t > 2.5:
                self.phase = 2
        elif self.phase == 2:
            if self.t > 3.5:
                self.done = True

    def draw(self, surf):
        surf.fill(BG_COLOR)
        draw_grid(surf, (0,0,W,H), 32, GRID_COLOR)
        role_col = HACKER_COL if self.role=="hacker" else NERD_COL
        role_icon = "☠" if self.role=="hacker" else "🛡"
        role_name = "HACKER" if self.role=="hacker" else "NERD"

        px(surf, f"NIVEL {self.level_num} DE 4",
           W//2, 120, self.fonts["md"], DIM_COL, center=True)

        if self.phase == 0:
            px(surf, str(self.count),
               W//2, H//2-40, self.fonts["title"], C64["yellow"], center=True)
            px(surf, "PREPARATE...",
               W//2, H//2+40, self.fonts["sm"], DIM_COL, center=True)
        elif self.phase >= 1:
            flash = abs(math.sin(self.t*4))
            col = tuple(int(c*flash + 50*(1-flash)) for c in role_col)
            px(surf, "TU ROL ES...",
               W//2, H//2-80, self.fonts["md"], DIM_COL, center=True)
            px(surf, f"{role_icon}  {role_name}  {role_icon}",
               W//2, H//2-20, self.fonts["title"], col, center=True)
            lv = LEVELS[self.level_num-1] if self.level_num <= len(LEVELS) else LEVELS[-1]
            px(surf, f"FIGURA: {lv['emoji_titulo']} {lv['titulo']}",
               W//2, H//2+50, self.fonts["sm"], C64["cyan"], center=True)
            px(surf, lv.get("concepto",""),
               W//2, H//2+74, self.fonts["xs"], DIM_COL, center=True)
            if self.phase == 2:
                if int(self.t*3)%2==0:
                    px(surf, "— COMENZANDO —",
                       W//2, H//2+110, self.fonts["sm"], C64["lt_green"], center=True)


class TriviaScreen:
    def __init__(self, fonts, level_completed, player_won):
        self.fonts = fonts
        self.t = 0.0
        self.done = False
        self.player_won = player_won
        idx = min(level_completed, len(TRIVIA)-1)
        self.year, self.text = TRIVIA[idx]
        sfx.play("door")

    def update(self, dt):
        self.t += dt
        if self.t > 6.0:
            self.done = True

    def draw(self, surf):
        surf.fill(BG_COLOR)
        draw_grid(surf, (0,0,W,H), 32, GRID_COLOR)

        if self.player_won:
            px(surf, "★ NIVEL COMPLETADO ★",
               W//2, 100, self.fonts["lg"], C64["lt_green"], center=True)
        else:
            px(surf, "CPU GANÓ ESTE NIVEL",
               W//2, 100, self.fonts["md"], ERR_COL, center=True)
            px(surf, "PERO SEGUÍS APRENDIENDO...",
               W//2, 124, self.fonts["xs"], DIM_COL, center=True)

        draw_border_box(surf, (240, 200, W-480, 300), BORDER_COL, fill=(8,8,30))
        px(surf, f"// {self.year}",
           W//2, 230, self.fonts["md"], C64["yellow"], center=True)
        pygame.draw.line(surf, BORDER_COL, (260,256),(W-260,256),1)

        lines = self.text.split("\n")
        for i, line in enumerate(lines):
            px(surf, line, W//2, 274 + i*28,
               self.fonts["sm"], C64["cyan"], center=True)

        progress = min(1.0, self.t / 6.0)
        draw_bar(surf, 240, 520, W-480, 8, int(progress*100), 100, BORDER_COL)
        px(surf, "SIGUIENTE NIVEL EN...",
           W//2, 534, self.fonts["xs"], DIM_COL, center=True)

        bounce = int(math.sin(self.t*4)*10)
        px(surf, "🐸", W//2-16, 420+bounce, self.fonts["emoji"])


class RetroLoader:
    """Pantalla de carga retro de 3 seg entre niveles — estética C64."""

    MESSAGES = [
        (0.0,  "cyan",   "ASPR ORACLE LAB v2.0"),
        (0.4,  "grey",   "INICIALIZANDO SIGUIENTE NIVEL..."),
        (0.9,  "yellow", "CARGANDO MAPA DE BUGS..."),
        (1.4,  "cyan",   "CALIBRANDO KARMA ENGINE..."),
        (1.9,  "green",  "VERIFICANDO MASCOTA..."),
        (2.4,  "yellow", "PREPARANDO RIVAL CPU..."),
        (2.75, "white",  "LISTO."),
    ]
    DURATION = 3.0

    def __init__(self, fonts, next_level, pet_data=None):
        self.fonts      = fonts
        self.next_level = next_level  # 0-indexed
        self.pet_data   = pet_data
        self.t          = 0.0
        self.done       = False
        self._beeped    = set()
        # sonido inicial
        sfx.beep(220, 80, "square", 0.08)

    def update(self, dt):
        self.t += dt
        # beeps en momentos clave
        for i, (trigger, *_) in enumerate(self.MESSAGES):
            if i not in self._beeped and self.t >= trigger:
                sfx.beep(400 + i * 80, 30, "square", 0.05)
                self._beeped.add(i)
        if self.t >= self.DURATION:
            self.done = True

    def draw(self, surf):
        surf.fill((0, 0, 0))
        draw_grid(surf, (0, 0, W, H), 32, (10, 10, 40))

        cx = W // 2

        # Título nivel
        lv_txt = f"— NIVEL {self.next_level + 1} DE 4 —"
        px(surf, lv_txt, cx, 80, self.fonts["title"], C64["yellow"], center=True)

        # Línea separadora
        pygame.draw.line(surf, C64["mid_grey"], (W//2 - 200, 110), (W//2 + 200, 110), 1)

        # Mensajes que van apareciendo
        col_map = {
            "cyan":   C64["cyan"],
            "yellow": C64["yellow"],
            "green":  C64["lt_green"],
            "grey":   C64["mid_grey"],
            "white":  C64["white"],
        }
        y = 150
        for trigger, col_key, msg in self.MESSAGES:
            if self.t >= trigger:
                alpha_t = min(1.0, (self.t - trigger) / 0.18)
                color = col_map.get(col_key, C64["white"])
                # cursor parpadeante solo en el último mensaje visible
                is_last = (trigger == max(tr for tr, *_ in self.MESSAGES if self.t >= tr))
                suffix = ("_" if int(self.t * 4) % 2 == 0 else " ") if is_last and not self.done else ""
                px(surf, "> " + msg + suffix, cx, y, self.fonts["sm"], color, center=True)
            y += 28

        # Mascota si la tiene
        if self.pet_data:
            pet_txt = f"{self.pet_data['emoji']}  {self.pet_data['name']}  ·  {self.pet_data['poder']}"
            px(surf, pet_txt, cx, H - 160, self.fonts["sm"], C64["yellow"], center=True)

        # Barra de carga
        progress = min(1.0, self.t / self.DURATION)
        bar_w = 400
        bar_x = cx - bar_w // 2
        bar_y = H - 110
        pygame.draw.rect(surf, C64["mid_grey"], (bar_x - 2, bar_y - 2, bar_w + 4, 18), 1)
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(surf, C64["cyan"], (bar_x, bar_y, fill_w, 14))
            # patrón de scanlines sobre la barra
            for bx in range(bar_x, bar_x + fill_w, 10):
                pygame.draw.rect(surf, (0, 0, 0, 60), (bx + 7, bar_y, 3, 14))
        pct = int(progress * 100)
        px(surf, f"{pct}%", cx, bar_y + 20, self.fonts["xs"], C64["mid_grey"], center=True)

        # Footer
        px(surf, "ASPR ORACLE NODE v2.0  ·  KIDSLAB.IO",
           cx, H - 40, self.fonts["xs"], (50, 50, 100), center=True)


class GameOverScreen:
    def __init__(self, fonts, player_wins, cpu_wins, name, mode):
        self.fonts = fonts
        self.t = 0.0
        self.player_wins = player_wins
        self.cpu_wins = cpu_wins
        self.name = name
        self.mode = mode
        self.restart_requested = False
        if mode == "solo":
            sfx.play("win")
        elif player_wins > cpu_wins:
            sfx.play("win")
        else:
            sfx.play("error")

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_r,
                          pygame.K_RETURN, pygame.K_SPACE):
                self.restart_requested = True

    def draw(self, surf):
        self.t += 0.016
        surf.fill(BG_COLOR)
        draw_grid(surf, (0,0,W,H), 32, GRID_COLOR)

        if self.mode == "solo":
            title = "★ COMPLETASTE EL JUEGO ★"
            col = C64["lt_green"]
            msg = "¡Aprendiste los comandos como una campeona o campeón!"
        else:
            won = self.player_wins > self.cpu_wins
            col = C64["lt_green"] if won else ERR_COL
            title = "★ GANASTE ★" if won else "PERDISTE"
            msg = f"{self.name}: {self.player_wins}  vs  CPU: {self.cpu_wins}"
        px(surf, title, W//2, H//2-100, self.fonts["title"], col, center=True)
        if self.mode != "solo":
            px(surf, msg, W//2, H//2-40, self.fonts["md"], C64["white"], center=True)
        else:
            px(surf, msg, W//2, H//2-40, self.fonts["sm"], C64["cyan"], center=True)

        px(surf, "ASPR ORACLE LAB · KIDSLAB.IO",
           W//2, H//2+40, self.fonts["xs"], DIM_COL, center=True)

        if int(self.t*2)%2==0:
            px(surf, "[ R ]  [ ENTER ]  [ ESPACIO ]  — REINICIAR",
               W//2, H//2+80, self.fonts["sm"], C64["yellow"], center=True)
        else:
            px(surf, "PRESIONA R PARA REINICIAR",
               W//2, H//2+80, self.fonts["sm"], C64["lt_green"], center=True)

        b = int(math.sin(self.t*3)*8)
        px(surf, "🐸", W//2-60, H//2+140+b, self.fonts["emoji"])
        px(surf, "🐸", W//2+30, H//2+140-b, self.fonts["emoji"])


class GameSolo:
    def __init__(self, fonts, name, level_index=0, mode="cpu"):
        self.fonts  = fonts
        self.name   = name
        self.mode   = mode
        self.t      = 0.0
        self.blink  = 0.0

        self.level_index  = level_index
        self.my_role      = ROLES_PER_LEVEL[level_index % len(ROLES_PER_LEVEL)]
        self.power        = 50
        self.karma        = 0
        self.wins         = 0
        self.step_index   = 0
        self.has_pet      = False
        self.pet_data     = None
        self.pet_hunger   = 100
        self.pet_anim_t   = 0.0
        self.level_done   = False

        self.input_text   = ""
        self.log          = []
        self.result_msg   = ""
        self.result_col   = C64["white"]
        self.result_t     = 0.0

        self.cpu = None
        if self.mode == "cpu":
            self.cpu = CPUPlayer(level_index=self.level_index)

        self._load_level()

        self.canvas_w = 192
        self.canvas_h = 192
        self.canvas_x = W//2 - self.canvas_w//2
        self.canvas_y = ANIM_H//2 - self.canvas_h//2 - 15

        frog_col = HACKER_COL if self.my_role=="hacker" else NERD_COL
        self.my_frog  = Frog(self.my_role,
                             self.canvas_x, self.canvas_y,
                             frog_col, len(self.pasos))

        if self.mode == "cpu":
            cpu_role  = "nerd" if self.my_role=="hacker" else "hacker"
            cpu_col   = NERD_COL if cpu_role=="nerd" else HACKER_COL
            self.cpu_frog = Frog(cpu_role,
                                 self.canvas_x + self.canvas_w + 40,
                                 self.canvas_y,
                                 cpu_col, len(self.pasos))
        else:
            self.cpu_frog = None

        self.time_remaining = 120.0 if self.mode == "cpu" else 0.0
        self.time_limit     = 120.0

        self.flash_alpha  = 0
        self.flash_color  = C64["white"]
        self.burst_parts  = []
        self.door_open    = 0.0
        self.door_opening = False

        self.guide_points = []
        self._compute_guide_path()

    def _load_level(self):
        lv = LEVELS[self.level_index]
        self.pasos       = lv["pasos"]
        self.level_color = lv["color"]
        self.step_index  = 0
        self.level_done  = False
        if self.mode == "cpu":
            self.time_remaining = 120.0
            self.time_limit     = 120.0
        else:
            self.time_remaining = 0.0
        self.my_role     = ROLES_PER_LEVEL[self.level_index % len(ROLES_PER_LEVEL)]
        self.door_open = 0.0
        self.door_opening = False

    def _compute_guide_path(self):
        if self.mode != "solo":
            return
        cx, cy = 5.0, 5.0
        angle = 90.0
        points = [(cx, cy)]
        for paso in self.pasos:
            accion = paso["action"]
            cmd, val = accion
            if cmd == "fd":
                rad = math.radians(angle)
                nx = cx + math.cos(rad) * val
                ny = cy - math.sin(rad) * val
                cx, cy = nx, ny
                points.append((cx, cy))
            elif cmd == "bk":
                rad = math.radians(angle)
                nx = cx - math.cos(rad) * val
                ny = cy + math.sin(rad) * val
                cx, cy = nx, ny
                points.append((cx, cy))
            elif cmd == "lt":
                angle += val
            elif cmd == "rt":
                angle -= val
        self.guide_points = points

    def add_log(self, msg, color=None):
        self.log.append({"msg": msg[:48], "color": color or C64["white"]})
        if len(self.log) > 8:
            self.log.pop(0)

    def flash(self, color, alpha=100):
        self.flash_color = color
        self.flash_alpha = alpha

    def burst(self, x, y, color, n=20):
        for _ in range(n):
            angle = random.uniform(0, math.pi*2)
            speed = random.uniform(2,8)
            self.burst_parts.append({
                "x":x,"y":y,
                "vx":math.cos(angle)*speed,
                "vy":math.sin(angle)*speed,
                "life":1.0,"color":color,"r":random.randint(2,5),
            })

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            pressed = pygame.key.get_pressed()
            ctrl_pressed = pressed[pygame.K_LCTRL] or pressed[pygame.K_RCTRL]
            if ev.key == pygame.K_f and ctrl_pressed:
                if self.has_pet:
                    self.pet_hunger = min(100, self.pet_hunger+20)
                    sfx.beep(880,60,"square",0.08)
                    self.add_log(f"🍖 ¡{self.pet_data['name']} alimentada/o!", C64["lt_green"])
            elif ev.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif ev.key == pygame.K_RETURN:
                self._submit()
            elif ev.key == pygame.K_ESCAPE:
                self.input_text = ""
            else:
                ch = ev.unicode
                if ch and ch.isprintable() and len(self.input_text) < 28:
                    self.input_text += ch
                    sfx.beep(880, 15, "square", 0.04)

    def _submit(self):
        inp_raw = self.input_text.strip()
        if not inp_raw:
            return
        self.input_text = ""

        if self.step_index >= len(self.pasos):
            return

        inp = normalize_input(inp_raw)

        lv   = LEVELS[self.level_index]
        step = self.pasos[self.step_index]

        ok, msg = check_command_matches_step(inp, step, lv["comandos_validos"])

        if ok:
            sfx.play("piece")
            self.my_frog.execute(step["action"])
            self.step_index += 1
            self.karma += 5
            self.power = min(100, self.power+3)
            self.add_log(f"✓ {msg}", OK_COL)
            self.result_msg = "CORRECTO!"
            self.result_col = OK_COL
            self.flash(OK_COL, 60)

            if self.step_index >= len(self.pasos):
                self.level_done = True
                self.wins += 1
                self.karma += 50
                self.power = min(100, self.power+15)

                if not self.has_pet:
                    self.has_pet = True
                    self.pet_data = random.choice(PET_TYPES).copy()
                    self.pet_hunger = 100
                    sfx.play("pet")
                    self.add_log(f"🎉 ¡Ganaste a {self.pet_data['name']} {self.pet_data['emoji']} como mascota!", C64["yellow"])
                    self.add_log("⚠️ Desde ahora los comandos llevan PARÉNTESIS: EJ: FD(50)", C64["yellow"])

                self.door_opening = True
                sfx.play("win")
                self.burst(W//2, ANIM_H//2, OK_COL, 35)
        else:
            sfx.play("error")
            self.my_frog.shake_error()
            self.power = max(0, self.power-5)
            self.add_log(f"✗ {msg}", ERR_COL)
            self.result_msg = "INCORRECTO"
            self.result_col = ERR_COL
        self.result_t = 2.5

    def update(self, dt) -> str:
        self.t      += dt
        self.blink  += dt
        self.result_t= max(0, self.result_t-dt)
        self.flash_alpha = max(0, self.flash_alpha-180*dt)
        self.pet_anim_t += dt

        if self.mode == "cpu" and not self.level_done and self.cpu and not self.cpu.finished_level:
            self.time_remaining = max(0, self.time_remaining - dt)

        self.my_frog.update(dt)
        if self.cpu_frog:
            self.cpu_frog.update(dt)

        if self.door_opening:
            self.door_open = min(1.0, self.door_open + dt*0.7)

        for p in self.burst_parts:
            p["x"]+=p["vx"]; p["y"]+=p["vy"]
            p["vy"]+=0.2;    p["life"]-=dt
        self.burst_parts = [p for p in self.burst_parts if p["life"]>0]

        if self.mode == "cpu" and self.cpu and not self.cpu.finished_level and not self.level_done:
            self.cpu.tick(self.pasos, self.cpu_frog, self)

        player_won = self.level_done
        cpu_won = False
        if self.mode == "cpu" and self.cpu:
            cpu_won = self.cpu.finished_level and not self.level_done
        timeout = (self.mode == "cpu") and (self.time_remaining <= 0) and not player_won and not cpu_won

        if player_won or cpu_won or timeout:
            if timeout and not player_won and not cpu_won:
                self.add_log("TIEMPO AGOTADO", ERR_COL)
                self.power = max(0, self.power-20)
            return "trivia"

        return ""

    def draw(self, surf):
        surf.fill(BG_COLOR)
        self._draw_anim(surf)
        self._draw_stats(surf)
        self._draw_console(surf)

        role_col = HACKER_COL if self.my_role=="hacker" else NERD_COL
        pygame.draw.line(surf, role_col, (0,ANIM_H),(W,ANIM_H), 2)
        pygame.draw.line(surf, BORDER_COL,(STATS_W,PANEL_Y),(STATS_W,H),1)

        if self.flash_alpha > 0:
            fl = pygame.Surface((W,H), pygame.SRCALPHA)
            fl.fill((*self.flash_color, int(self.flash_alpha)))
            surf.blit(fl, (0,0))

        for p in self.burst_parts:
            a = int(p["life"]*255)
            s = pygame.Surface((p["r"]*2,p["r"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"],a),(p["r"],p["r"]),p["r"])
            surf.blit(s,(int(p["x"])-p["r"],int(p["y"])-p["r"]))

        scanlines(surf)

    def _draw_guide(self, surf):
        if self.mode != "solo" or not self.guide_points:
            return
        ox, oy = self.canvas_x, self.canvas_y
        for i in range(len(self.guide_points)-1):
            x1, y1 = self.guide_points[i]
            x2, y2 = self.guide_points[i+1]
            px1 = ox + x1 * CELL
            py1 = oy + y1 * CELL
            px2 = ox + x2 * CELL
            py2 = oy + y2 * CELL
            dash_len = 8
            step = 4
            dist = math.hypot(px2-px1, py2-py1)
            if dist < 0.1:
                continue
            dx = (px2-px1)/dist
            dy = (py2-py1)/dist
            for t in range(0, int(dist), step):
                if (t // dash_len) % 2 == 0:
                    sx = px1 + dx*t
                    sy = py1 + dy*t
                    pygame.draw.circle(surf, GUIDE_COL, (int(sx), int(sy)), 3)
        if self.step_index < len(self.guide_points):
            cx, cy = self.guide_points[self.step_index]
            px = ox + cx * CELL
            py = oy + cy * CELL
            pygame.draw.circle(surf, C64["yellow"], (int(px), int(py)), 8, 2)
            pygame.draw.circle(surf, C64["white"], (int(px), int(py)), 4)

    def _draw_anim(self, surf):
        for dy in range(ANIM_H):
            ratio = dy/ANIM_H
            c = tuple(int(BG_COLOR[i]*(0.7+0.3*(1-ratio))) for i in range(3))
            pygame.draw.line(surf, c, (0,dy),(W,dy))
        draw_grid(surf, (0,0,W,ANIM_H), 32, GRID_COLOR)

        ground_y = ANIM_H-45
        for gx in range(0, W, 16):
            c = C64["mid_grey"] if (gx//16)%2==0 else (50,50,100)
            pygame.draw.rect(surf, c, (gx, ground_y, 16, 3))

        canvas_surf = pygame.Surface((self.canvas_w, self.canvas_h))
        canvas_surf.fill((8,8,30))
        for cx in range(0, self.canvas_w, CELL):
            pygame.draw.line(canvas_surf,(20,20,60),(cx,0),(cx,self.canvas_h))
        for cy in range(0, self.canvas_h, CELL):
            pygame.draw.line(canvas_surf,(20,20,60),(0,cy),(self.canvas_w,cy))
        surf.blit(canvas_surf,(self.canvas_x, self.canvas_y))
        draw_border_box(surf,(self.canvas_x,self.canvas_y,
                             self.canvas_w,self.canvas_h),
                       self.level_color, thickness=2)

        self._draw_guide(surf)
        self._draw_door(surf)

        prog = self.step_index / max(len(self.pasos),1)
        bar_y = self.canvas_y + self.canvas_h + 6
        draw_bar(surf, self.canvas_x, bar_y, self.canvas_w, 7,
                int(prog*100),100, self.level_color)
        px(surf, f"TU PROGRESO: {self.step_index}/{len(self.pasos)}",
           self.canvas_x, bar_y+10, self.fonts["xs"], self.level_color)

        self.my_frog.draw(surf, self.fonts)
        if self.cpu_frog:
            self.cpu_frog.draw(surf, self.fonts)

        role_col = HACKER_COL if self.my_role=="hacker" else NERD_COL
        px(surf, f"{self.name[:8]} ({self.my_role.upper()})",
           int(self.my_frog.anim_x), self.canvas_y+self.canvas_h+20,
           self.fonts["xs"], role_col, center=True)

        if self.mode == "cpu" and self.cpu_frog:
            cpu_role = "nerd" if self.my_role=="hacker" else "hacker"
            cpu_col  = NERD_COL if cpu_role=="nerd" else HACKER_COL
            px(surf, f"CPU ({cpu_role.upper()})",
               int(self.cpu_frog.anim_x), self.canvas_y+self.canvas_h+20,
               self.fonts["xs"], cpu_col, center=True)
            cpu_prog = self.cpu.step_index / max(len(self.pasos),1)
            draw_bar(surf,
                    int(self.cpu_frog.anim_x)-40,
                    self.canvas_y+self.canvas_h+32,
                    80, 5, int(cpu_prog*100), 100, cpu_col)
        else:
            px(surf, "★ SIGUE EL CAMINO ★",
               int(self.my_frog.anim_x), self.canvas_y+self.canvas_h+32,
               self.fonts["xs"], C64["yellow"], center=True)

        if self.has_pet and self.pet_data:
            pet_x = 80
            pet_y = ground_y - 55
            b = int(math.sin(self.pet_anim_t*3)*5)
            pet_surf = self.fonts["emoji"].render(self.pet_data["emoji"], True, C64["white"])
            surf.blit(pet_surf,(pet_x-pet_surf.get_width()//2, pet_y+b))
            px(surf, self.pet_data["name"],
               pet_x, pet_y+32, self.fonts["xs"],
               HACKER_COL if self.my_role=="hacker" else NERD_COL,
               center=True)
            draw_bar(surf, pet_x-25, pet_y+44, 50,4,
                    self.pet_hunger, 100, C64["lt_green"])

        lv = LEVELS[self.level_index]
        px(surf, f"{lv['emoji_titulo']} {lv['titulo']}",
           W//2, 10, self.fonts["sm"], self.level_color, center=True)

    def _draw_door(self, surf):
        dw, dh = 100, 120
        dx = self.canvas_x + self.canvas_w//2 - dw//2
        dy = self.canvas_y - dh - 10
        glow = abs(math.sin(self.t*2))
        bc = tuple(int(c*(0.5+0.5*glow)) for c in self.level_color)

        pygame.draw.rect(surf,(10,10,40),(dx,dy,dw,dh))
        draw_border_box(surf,(dx,dy,dw,dh), bc, thickness=2)

        half = int(dw/2*(1-self.door_open))
        if half > 0:
            pygame.draw.rect(surf,(30,30,100),(dx,dy+2,half,dh-4))
            pygame.draw.rect(surf,(30,30,100),(dx+dw-half,dy+2,half,dh-4))
            for ky in range(dy+8, dy+dh-8, 10):
                pygame.draw.rect(surf,bc,(dx+3,ky,half-6,1))
                pygame.draw.rect(surf,bc,(dx+dw-half+3,ky,half-6,1))

        if self.door_open > 0.1:
            lw = int((dw-4)*self.door_open*0.7)
            ls = pygame.Surface((lw, dh-8), pygame.SRCALPHA)
            ls.fill((*self.level_color, int(self.door_open*100)))
            surf.blit(ls,(dx+(dw-lw)//2, dy+4))

        label = "ABIERTO!" if self.door_open>0.9 else (
                "ABRIENDO..." if self.door_open>0.05 else "NIVEL BLOQUEADO")
        if int(self.t*3)%2==0:
            px(surf, label, dx+dw//2, dy+dh//2-6,
               self.fonts["xs"], bc, center=True)

    def _draw_stats(self, surf):
        rx,ry,rw,rh = 0,PANEL_Y,STATS_W,PANEL_H
        pygame.draw.rect(surf,(10,10,40),(rx,ry,rw,rh))
        draw_border_box(surf,(rx,ry,rw,rh),BORDER_COL)

        role_col = HACKER_COL if self.my_role=="hacker" else NERD_COL
        px(surf,self.name[:8].upper(), rx+8,ry+8,self.fonts["sm"],role_col)
        px(surf,self.my_role.upper(),  rx+8,ry+24,self.fonts["xs"],DIM_COL)

        stats=[("POWER",self.power,100,role_col),
               ("KARMA",min(self.karma,200),200,C64["yellow"]),
               ("HAMBRE",self.pet_hunger,100,C64["lt_green"])]
        for i,(lbl,val,maxv,col) in enumerate(stats):
            sy=ry+48+i*38
            px(surf,lbl,rx+8,sy,self.fonts["xs"],DIM_COL)
            draw_bar(surf,rx+8,sy+13,rw-16,8,val,maxv,col)
            px(surf,str(val),rx+rw-8,sy,self.fonts["xs"],col,right=True)

        if self.mode == "cpu":
            ty=ry+48+3*38+4
            tr=self.time_remaining
            t_col=OK_COL if tr>60 else (C64["yellow"] if tr>30 else ERR_COL)
            px(surf,f"TIEMPO: {int(tr)}s",rx+rw//2,ty,self.fonts["xs"],t_col,center=True)
            draw_bar(surf,rx+8,ty+14,rw-16,6,int(tr),120,t_col)
            py2=ty+28
        else:
            py2=ry+48+3*38+4
            px(surf,"★ MODO SOLO ★",rx+rw//2,py2,self.fonts["xs"],C64["lt_green"],center=True)
            py2+=20

        px(surf,f"NIVEL {self.level_index+1}/4",rx+8,py2,self.fonts["xs"],C64["white"])
        px(surf,f"WINS: {self.wins}",rx+8,py2+16,self.fonts["xs"],C64["yellow"])
        if self.has_pet and self.pet_data and "poder" in self.pet_data:
            px(surf, f"POD:{self.pet_data['poder'][:14]}",
               rx+8, ry+rh-32, self.fonts["xs"], C64["yellow"])
        px(surf,"CTRL+F=ALIMENTAR",rx+rw//2,ry+rh-16,self.fonts["xs"],DIM_COL,center=True)

    def _draw_console(self, surf):
        rx,ry,rw,rh = CONSOLE_X,PANEL_Y,CONSOLE_W,PANEL_H
        pygame.draw.rect(surf,(6,6,26),(rx,ry,rw,rh))
        draw_border_box(surf,(rx,ry,rw,rh),BORDER_COL)

        lv=LEVELS[self.level_index]
        role_col=HACKER_COL if self.my_role=="hacker" else NERD_COL
        cmds=list(lv["comandos_validos"].keys())

        px(surf,f"NIVEL {lv['id']}: {lv['titulo']}",
           rx+10,ry+8,self.fonts["md"],self.level_color)
        px(surf,"COMANDOS: "+"  ".join(cmds),
           rx+10,ry+28,self.fonts["sm"],C64["cyan"])
        pygame.draw.line(surf,BORDER_COL,(rx,ry+46),(rx+rw,ry+46),1)

        if self.step_index < len(self.pasos):
            paso_actual = self.pasos[self.step_index]
            if self.has_pet:
                cmd_parts = paso_actual["cmd"].split()
                if len(cmd_parts) == 2:
                    display_cmd = f"{cmd_parts[0]}({cmd_parts[1]})"
                else:
                    display_cmd = paso_actual["cmd"]
            else:
                display_cmd = paso_actual["cmd"]

            draw_border_box(surf,(rx+8,ry+52,rw-16,58),
                           self.level_color,fill=(8,20,40),thickness=2)
            px(surf,"ESCRIBI ESTE COMANDO:",
               rx+rw//2,ry+56,self.fonts["xs"],DIM_COL,center=True)
            flash_col = self.level_color if int(self.blink*2)%2==0 else C64["white"]
            px(surf, display_cmd,
               rx+rw//2, ry+70, self.fonts["lg"], flash_col, center=True)
            px(surf, paso_actual["desc"][:50],
               rx+rw//2, ry+96, self.fonts["xs"], DIM_COL, center=True)

        pygame.draw.line(surf,BORDER_COL,(rx,ry+118),(rx+rw,ry+118),1)

        paso_y=ry+124
        for i,paso in enumerate(self.pasos):
            if paso_y+15 > ry+rh-100:
                px(surf,f"  ...{len(self.pasos)-i} pasos mas",
                   rx+10,paso_y,self.fonts["xs"],DIM_COL)
                break
            if i < self.step_index:
                col=C64["mid_grey"]; prefix="✓"
            elif i==self.step_index:
                col=self.level_color; prefix="►"
            else:
                col=(50,50,90); prefix=" "
            if self.has_pet:
                cmd_parts = paso["cmd"].split()
                if len(cmd_parts) == 2:
                    show_cmd = f"{cmd_parts[0]}({cmd_parts[1]})"
                else:
                    show_cmd = paso["cmd"]
            else:
                show_cmd = paso["cmd"]
            px(surf,f" {prefix} {i+1}. {show_cmd}",
               rx+10,paso_y,self.fonts["xs"],col)
            paso_y+=16

        pygame.draw.line(surf,BORDER_COL,(rx,ry+rh-82),(rx+rw,ry+rh-82),1)

        log_y=ry+rh-80
        for entry in self.log[-3:]:
            px(surf,entry["msg"],rx+12,log_y,self.fonts["xs"],entry["color"])
            log_y+=18

        pygame.draw.line(surf,BORDER_COL,(rx,ry+rh-38),(rx+rw,ry+rh-38),1)
        draw_border_box(surf,(rx+6,ry+rh-36,rw-12,30),
                       role_col,fill=(0,0,20),thickness=2)
        cur="|" if int(self.blink*3)%2==0 else " "
        px(surf,f"► {self.input_text}{cur}",
           rx+16,ry+rh-30,self.fonts["md"],CURSOR_COL)

        if self.result_t > 0:
            alpha = min(1.0, self.result_t)
            col=tuple(int(c*alpha) for c in self.result_col)
            px(surf,self.result_msg,rx+rw//2,ry+rh-108,
               self.fonts["lg"],col,center=True)


# ==================================================================
# 9. APLICACIÓN PRINCIPAL
# ==================================================================
class App:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()          # <--- crucial para sonido
        pygame.display.set_caption("🧪 KidsLab — Oracle Kids: Hackers vs Nerds Edition")
        self.screen = pygame.display.set_mode((W, H))
        self.clock  = pygame.time.Clock()
        self.fonts  = load_fonts()
        sfx.init()                   # inicializar sonido (sin hilo extra)

        self.state   = "login"
        self.login   = LoginSolo(self.fonts)
        self.reveal  = None
        self.game    = None
        self.trivia  = None
        self.loader  = None
        self.gameover= None
        self.player_name = ""
        self.player_wins = 0
        self.cpu_wins    = 0
        self.game_mode   = "cpu"
        self._demo_t     = 0.0
        self._pending_level = 0
        self._saved_pet = None
        self._saved_hunger = 100

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                self._event(ev)
            self._update(dt)
            self._draw()
            pygame.display.flip()

    def _event(self, ev):
        if self.state == "gameover" and self.gameover:
            self.gameover.handle_event(ev)
            if self.gameover.restart_requested:
                self.state          = "login"
                self.login          = LoginSolo(self.fonts)
                self.player_wins    = 0
                self.cpu_wins       = 0
                self.game           = None
                self.gameover       = None
                self.trivia         = None
                self.reveal         = None
                self.loader         = None
                self._saved_pet     = None
                self._saved_hunger  = 100
                self._pending_level = 0
            return  # no procesar más eventos en gameover

        if self.state == "login":
            self.login.handle(ev)
            if self.login.done:
                self.player_name = self.login.result["name"]
                self.game_mode   = self.login.result["mode"]
                self._start_level(0)

        elif self.state == "game" and self.game:
            self.game.handle_event(ev)

    def _start_level(self, idx):
        role = ROLES_PER_LEVEL[idx % len(ROLES_PER_LEVEL)]
        self.reveal = RoleReveal(self.fonts, role, idx+1)
        self.state  = "reveal"
        self._pending_level = idx

    def _launch_game(self, idx):
        self.game = GameSolo(self.fonts, self.player_name, idx, mode=self.game_mode)
        if self._saved_pet:
            self.game.has_pet    = True
            self.game.pet_data   = self._saved_pet
            self.game.pet_hunger = self._saved_hunger
            pet = self._saved_pet
            self.game.add_log(f"{pet['emoji']} {pet['name']} te acompaña — nivel {idx+1}/4", C64["yellow"])
            self.game.add_log("⚠️ Recordá: comandos con PARÉNTESIS — EJ: FD(50)", C64["cyan"])
        self.game.wins = self.player_wins
        self.state = "game"

    def _update(self, dt):
        if self.state == "reveal" and self.reveal:
            self.reveal.update(dt)
            if self.reveal.done:
                self._launch_game(self._pending_level)

        elif self.state == "game" and self.game:
            result = self.game.update(dt)
            if result == "trivia":
                player_won = self.game.level_done
                if self.game_mode == "cpu":
                    if player_won:
                        self.player_wins += 1
                    else:
                        self.cpu_wins += 1
                else:
                    self.player_wins += 1
                self._saved_pet    = self.game.pet_data if self.game.has_pet else None
                self._saved_hunger = self.game.pet_hunger
                self.trivia = TriviaScreen(self.fonts, self.game.level_index, player_won)
                self.state  = "trivia"

        elif self.state == "trivia" and self.trivia:
            self.trivia.update(dt)
            if self.trivia.done:
                next_idx = (self.game.level_index + 1) if self.game else 1
                if next_idx >= len(LEVELS):
                    self.gameover = GameOverScreen(
                        self.fonts, self.player_wins, self.cpu_wins, self.player_name, self.game_mode)
                    self.state = "gameover"
                else:
                    # ── pantalla de carga retro antes del siguiente nivel ──
                    pet = self._saved_pet
                    self.loader = RetroLoader(self.fonts, next_idx, pet_data=pet)
                    self._pending_level = next_idx
                    self.state = "loading"

        elif self.state == "loading" and self.loader:
            self.loader.update(dt)
            if self.loader.done:
                self.loader = None
                self._start_level(self._pending_level)

    def _draw(self):
        if self.state == "login":
            self.login.draw(self.screen)
        elif self.state == "reveal" and self.reveal:
            self.reveal.draw(self.screen)
        elif self.state == "game" and self.game:
            self.game.draw(self.screen)
        elif self.state == "loading" and self.loader:
            self.loader.draw(self.screen)
        elif self.state == "trivia" and self.trivia:
            self.trivia.draw(self.screen)
        elif self.state == "gameover" and self.gameover:
            self.gameover.draw(self.screen)
        else:
            self.screen.fill(BG_COLOR)
        # Banner DEMO siempre visible
        draw_demo_banner(self.screen, self.fonts, self._demo_t)
        self._demo_t += 0.016


if __name__ == "__main__":
    App().run()