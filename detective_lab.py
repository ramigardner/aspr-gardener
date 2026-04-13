"""
KidsLab — DETECTIVE LAB 🔍  (demo standalone)
Descubrí qué celda de A + qué celda de B = la celda C que titila
Dashboard de botones — teclado en pantalla, sin escribir
Estética Commodore 64 · Sonido 8-bit · ASPR Oracle Node v2.0
Distribuible por email / SD / WhatsApp — 100% offline
"""

import pygame
import sys
import math
import random
import time
import numpy as np

# ══════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════
W, H  = 1024, 640
FPS   = 60
TOTAL = 6          # desafíos por ronda
VMIN, VMAX = 1, 9  # rango de valores en las matrices

PET_TYPES = [
    {"name": "Saltarina", "emoji": "🐸", "poder": "Salta bugs"},
    {"name": "Tortu",     "emoji": "🐢", "poder": "Escudo"},
    {"name": "Misifú",    "emoji": "🐱", "poder": "Vida extra"},
    {"name": "Pulgi",     "emoji": "🐶", "poder": "Olfato"},
    {"name": "Pinguino",  "emoji": "🐧", "poder": "Congela"},
]

C64 = {
    "bg":      (16,  16,  64),
    "grid":    (28,  28,  88),
    "border":  (100, 100, 255),
    "white":   (255, 255, 240),
    "cyan":    ( 84, 255, 255),
    "yellow":  (240, 240,  80),
    "green":   (112, 255, 112),
    "red":     (255,  80,  80),
    "grey":    (128, 128, 192),
    "dim":     ( 50,  50, 110),
    "black":   (  0,   0,   0),
    "orange":  (255, 160,  40),
    "magenta": (220,  80, 220),
}


# ══════════════════════════════════════════════════════════════════
# SONIDO  — síntesis 8-bit, sin archivos externos
# ══════════════════════════════════════════════════════════════════
class SFX:
    def __init__(self): self.ready = False

    def init(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.ready = True
        except Exception as e:
            print(f"[SFX] {e}")

    def _emit(self, arr):
        if not self.ready: return
        try:
            stereo = np.column_stack([arr, arr])
            pygame.sndarray.make_sound(stereo).play()
        except Exception: pass

    def _sq(self, freq, ms, vol=0.16):
        sr = 44100
        n  = int(sr * ms / 1000)
        t  = np.linspace(0, ms/1000, n, endpoint=False)
        w  = np.where((t * freq) % 1.0 < 0.5, 1.0, -1.0)
        env = np.linspace(1, 0, n) ** 0.4
        return (w * env * vol * 32767).astype(np.int16)

    def tap(self):    self._emit(self._sq(660,  30, 0.10))
    def ok(self):
        # dos notas encadenadas sin delay — evita cuelgue en hilo principal
        sr = 44100
        n1 = int(sr * 0.06)
        n2 = int(sr * 0.09)
        gap = int(sr * 0.07)
        t1 = np.linspace(0, 0.06, n1, endpoint=False)
        t2 = np.linspace(0, 0.09, n2, endpoint=False)
        w1 = np.where((t1 * 880)  % 1.0 < 0.5, 1.0, -1.0) * np.linspace(1,0,n1)**0.4
        w2 = np.where((t2 * 1318) % 1.0 < 0.5, 1.0, -1.0) * np.linspace(1,0,n2)**0.4
        silence = np.zeros(gap, dtype=np.float64)
        wave = np.concatenate([w1, silence, w2])
        self._emit((wave * 0.18 * 32767).astype(np.int16))
    def err(self):    self._emit(self._sq(180, 160, 0.20))
    def select(self): self._emit(self._sq(440,  40, 0.12))
    def win(self):
        # fanfarria sin delays
        sr  = 44100
        parts = []
        for f, ms in [(523,90),(659,90),(784,90),(1046,130)]:
            n   = int(sr * ms / 1000)
            gap = int(sr * 0.01)
            t   = np.linspace(0, ms/1000, n, endpoint=False)
            w   = np.where((t*f)%1.0 < 0.5, 1.0, -1.0) * np.linspace(1,0,n)**0.3
            parts.append(w)
            parts.append(np.zeros(gap))
        wave = np.concatenate(parts)
        self._emit((wave * 0.20 * 32767).astype(np.int16))

    def modem(self, ms=1600):
        """Módems 56k sintetizado — entre desafíos."""
        if not self.ready: return
        try:
            sr   = 44100
            n    = int(sr * ms / 1000)
            t    = np.linspace(0, ms/1000, n, endpoint=False)
            segs = [1200, 2400, 600, 1800, 900, 2100, 1500, 800]
            wave = np.zeros(n)
            seg  = n // len(segs)
            for i, f in enumerate(segs):
                s, e = i*seg, min((i+1)*seg, n)
                sub  = t[s:e]
                carrier = np.sin(2*np.pi*f*sub)
                mod     = np.sin(2*np.pi*(f*0.28)*sub)
                wave[s:e] = carrier * (0.55 + 0.45*mod)
            fn = min(int(sr*0.07), n//4)
            wave[:fn]  *= np.linspace(0, 1, fn)
            wave[-fn:] *= np.linspace(1, 0, fn)
            self._emit((wave * 0.20 * 32767).astype(np.int16))
        except Exception: pass

sfx = SFX()


# ══════════════════════════════════════════════════════════════════
# FUENTES
# ══════════════════════════════════════════════════════════════════
def load_fonts():
    mono = pygame.font.match_font(
        "px437ibmvga8x16,couriernew,lucidaconsole,monospace,courier")
    try:
        return {
            "title": pygame.font.Font(mono, 22),
            "lg":    pygame.font.Font(mono, 18),
            "md":    pygame.font.Font(mono, 14),
            "sm":    pygame.font.Font(mono, 12),
            "xs":    pygame.font.Font(mono, 10),
            "emoji": pygame.font.SysFont("segoeuiemoji,noto emoji", 24),
        }
    except Exception:
        return {k: pygame.font.SysFont("monospace", s)
                for k, s in [("title",22),("lg",18),("md",14),
                               ("sm",12),("xs",10),("emoji",22)]}


# ══════════════════════════════════════════════════════════════════
# UTILIDADES DE DIBUJO
# ══════════════════════════════════════════════════════════════════
def px(surf, text, x, y, font, color=None, center=False, right=False):
    color = color or C64["white"]
    sh = font.render(str(text), False, (0, 0, 0))
    rx = x - sh.get_width()//2 if center else (x - sh.get_width() if right else x)
    surf.blit(sh, (rx+1, y+1))
    r = font.render(str(text), False, color)
    rx2 = x - r.get_width()//2 if center else (x - r.get_width() if right else x)
    surf.blit(r, (rx2, y))
    return r.get_width()

def box(surf, rect, color=None, fill=None, thick=2):
    color = color or C64["border"]
    if fill:
        pygame.draw.rect(surf, fill, rect)
    pygame.draw.rect(surf, color, rect, thick)
    x, y, w, h = rect
    for cx, cy in [(x,y),(x+w-2,y),(x,y+h-2),(x+w-2,y+h-2)]:
        pygame.draw.rect(surf, C64["white"], (cx, cy, 2, 2))

def draw_grid_bg(surf):
    surf.fill(C64["bg"])
    for gx in range(0, W, 32):
        pygame.draw.line(surf, C64["grid"], (gx, 0), (gx, H))
    for gy in range(0, H, 32):
        pygame.draw.line(surf, C64["grid"], (0, gy), (W, gy))

def scanlines(surf):
    sl = pygame.Surface((W, H), pygame.SRCALPHA)
    for gy in range(0, H, 4):
        pygame.draw.line(sl, (0, 0, 0, 18), (0, gy), (W, gy))
    surf.blit(sl, (0, 0))

def demo_banner(surf, fonts, t):
    bw, bh = 110, 26
    bx, by = W - bw - 8, 8
    s = pygame.Surface((bw, bh), pygame.SRCALPHA)
    s.fill((20, 180, 80, int(150 + 40*math.sin(t*2))))
    surf.blit(s, (bx, by))
    pygame.draw.rect(surf, (50, 255, 120), (bx, by, bw, bh), 2)
    txt = fonts["sm"].render("★ DEMO ★", False, C64["white"])
    surf.blit(txt, (bx + bw//2 - txt.get_width()//2,
                    by + bh//2 - txt.get_height()//2))


# ══════════════════════════════════════════════════════════════════
# GENERADOR DE DESAFÍOS
# ══════════════════════════════════════════════════════════════════
def make_matrices():
    """Genera matrices A y B (3x3) con valores aleatorios."""
    A = [[random.randint(VMIN, VMAX) for _ in range(3)] for _ in range(3)]
    B = [[random.randint(VMIN, VMAX) for _ in range(3)] for _ in range(3)]
    C = [[A[r][c] + B[r][c] for c in range(3)] for r in range(3)]
    return A, B, C

def cell_name(mat, r, c):
    """Devuelve 'A5', 'B3', 'C7', etc."""
    return f"{mat}{r*3+c+1}"

def make_challenge(A, B, C):
    """
    Elige una celda objetivo de C al azar.
    Las celdas de A y B que la componen pueden estar MEZCLADAS
    (la suma igual sigue siendo correcta si los valores coinciden).
    Devuelve:
      target_name, target_val,
      a_row, a_col, b_row, b_col,
      (posibles respuestas correctas como set de tuplas)
    """
    tr = random.randint(0, 2)
    tc = random.randint(0, 2)
    target_val = C[tr][tc]
    target_name = cell_name("C", tr, tc)

    # Respuesta canónica
    ar, ac = tr, tc
    br, bc = tr, tc

    # Posibles alternativas correctas — otras celdas cuya suma = target_val
    alternativas = set()
    for r1 in range(3):
        for c1 in range(3):
            for r2 in range(3):
                for c2 in range(3):
                    if A[r1][c1] + B[r2][c2] == target_val:
                        alternativas.add((r1, c1, r2, c2))

    return target_name, target_val, alternativas


# ══════════════════════════════════════════════════════════════════
# BOTÓN DE CELDA
# ══════════════════════════════════════════════════════════════════
class CellButton:
    def __init__(self, rect, label, value, mat_id, row, col, font):
        self.rect   = pygame.Rect(rect)
        self.label  = label   # "A5"
        self.value  = value   # número
        self.mat_id = mat_id  # "A" o "B"
        self.row    = row
        self.col    = col
        self.font   = font
        self.selected  = False
        self.correct   = False
        self.wrong     = False
        self.press_t   = 0

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def update(self):
        if self.press_t > 0:
            self.press_t -= 1

    def draw(self, surf, t):
        r = self.rect

        # Color de fondo según estado
        if self.correct:
            fill = (20, 100, 20)
            border = C64["green"]
        elif self.wrong:
            fill = (100, 10, 10)
            border = C64["red"]
        elif self.selected:
            fill = (40, 40, 120)
            border = C64["cyan"]
        else:
            fill = (10, 10, 45)
            border = C64["border"] if self.mat_id == "A" else C64["magenta"]

        # Presión visual
        draw_r = r.inflate(-2, -2) if self.press_t > 0 else r

        pygame.draw.rect(surf, fill, draw_r, border_radius=5)
        pygame.draw.rect(surf, border, draw_r, 2, border_radius=5)

        # Esquinas pixel
        for cx, cy in [(r.x, r.y), (r.right-2, r.y),
                       (r.x, r.bottom-2), (r.right-2, r.bottom-2)]:
            pygame.draw.rect(surf, C64["white"], (cx, cy, 2, 2))

        # Etiqueta arriba
        lbl = self.font.render(self.label, False, border)
        surf.blit(lbl, (r.centerx - lbl.get_width()//2, r.y + 2))

        # Valor grande en el centro
        val_col = C64["white"] if not self.selected else C64["cyan"]
        if self.correct: val_col = C64["green"]
        if self.wrong:   val_col = C64["red"]
        big = pygame.font.Font(
            pygame.font.match_font("couriernew,monospace"), 18)
        vs = big.render(str(self.value), False, val_col)
        surf.blit(vs, (r.centerx - vs.get_width()//2,
                       r.centery - vs.get_height()//2 + 4))


# ══════════════════════════════════════════════════════════════════
# PANTALLA DE JUEGO PRINCIPAL
# ══════════════════════════════════════════════════════════════════
class DetectiveGame:
    # Layout
    MAT_CELL_W  = 72
    MAT_CELL_H  = 54
    MAT_GAP     = 6

    def __init__(self, fonts):
        self.fonts      = fonts
        self.t          = 0.0
        self.demo_t     = 0.0
        self.score      = 0
        self.errors     = 0
        self.challenge_n = 0
        self.done       = False

        # Estado del desafío actual
        self.A, self.B, self.C = make_matrices()
        self._new_challenge()

        # Modem state
        self.modem_active = False
        self.modem_until  = 0.0
        self.modem_lines  = []
        self.modem_line_t = 0.0

        # Feedback
        self.feedback_msg  = ""
        self.feedback_col  = C64["white"]
        self.feedback_t    = 0.0

        # Mascota y stats
        self.pet        = random.choice(PET_TYPES).copy()
        self.karma      = 0
        self.power      = 50
        self.pet_anim_t = 0.0

        # Restart
        self.restart_requested = False

        # Resultado flash
        self.flash_col   = None
        self.flash_alpha = 0

    # ── Desafío nuevo ───────────────────────────────────────────
    def _new_challenge(self):
        self.sel_a = None   # (row, col) seleccionado de A
        self.sel_b = None   # (row, col) seleccionado de B
        self.confirmed   = False
        self.result_shown = False

        self.target_name, self.target_val, self.valid_combos = \
            make_challenge(self.A, self.B, self.C)

        self._build_buttons()

    def _build_buttons(self):
        """Construye los 9+9 botones de celda."""
        # Matrices A y B lado a lado, centradas verticalmente
        mw = 3 * self.MAT_CELL_W + 2 * self.MAT_GAP
        mh = 3 * self.MAT_CELL_H + 2 * self.MAT_GAP

        # Panel izquierdo: A  (x=30)
        # Panel derecho:   B  (x=30 + mw + 60)
        ax0 = 32
        bx0 = ax0 + mw + 58
        y0  = 140

        self.buttons_a = []
        self.buttons_b = []

        for r in range(3):
            for c in range(3):
                x = ax0 + c * (self.MAT_CELL_W + self.MAT_GAP)
                y = y0  + r * (self.MAT_CELL_H + self.MAT_GAP)
                self.buttons_a.append(CellButton(
                    (x, y, self.MAT_CELL_W, self.MAT_CELL_H),
                    cell_name("A", r, c),
                    self.A[r][c], "A", r, c, self.fonts["xs"]
                ))

        for r in range(3):
            for c in range(3):
                x = bx0 + c * (self.MAT_CELL_W + self.MAT_GAP)
                y = y0  + r * (self.MAT_CELL_H + self.MAT_GAP)
                self.buttons_b.append(CellButton(
                    (x, y, self.MAT_CELL_W, self.MAT_CELL_H),
                    cell_name("B", r, c),
                    self.B[r][c], "B", r, c, self.fonts["xs"]
                ))

    # ── Eventos ─────────────────────────────────────────────────
    def handle_event(self, ev):
        # Restart siempre disponible
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if ev.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.restart_requested = True
                return

        if self.modem_active or self.confirmed:
            return

        # ── Teclado físico dashboard ─────────────────────────────
        # A1-A9: teclas 1-9 eligen celda de A
        # B1-B9: Q W E / A S D / Z X C eligen celda de B
        # ENTER / SPACE confirman
        KEY_A = {
            pygame.K_1:(0,0), pygame.K_2:(0,1), pygame.K_3:(0,2),
            pygame.K_4:(1,0), pygame.K_5:(1,1), pygame.K_6:(1,2),
            pygame.K_7:(2,0), pygame.K_8:(2,1), pygame.K_9:(2,2),
        }
        KEY_B = {
            pygame.K_q:(0,0), pygame.K_w:(0,1), pygame.K_e:(0,2),
            pygame.K_a:(1,0), pygame.K_s:(1,1), pygame.K_d:(1,2),
            pygame.K_z:(2,0), pygame.K_x:(2,1), pygame.K_c:(2,2),
        }
        if ev.type == pygame.KEYDOWN:
            if ev.key in KEY_A:
                r, c = KEY_A[ev.key]
                for b in self.buttons_a: b.selected = False
                for b in self.buttons_a:
                    if (b.row, b.col) == (r, c):
                        b.selected = True
                self.sel_a = (r, c)
                sfx.select()
                return
            if ev.key in KEY_B:
                r, c = KEY_B[ev.key]
                for b in self.buttons_b: b.selected = False
                for b in self.buttons_b:
                    if (b.row, b.col) == (r, c):
                        b.selected = True
                self.sel_b = (r, c)
                sfx.select()
                return
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.sel_a is not None and self.sel_b is not None:
                    self._confirm()
                return

        pos = None
        if ev.type == pygame.MOUSEBUTTONDOWN:
            pos = ev.pos
        elif ev.type == pygame.FINGERDOWN:
            pos = (int(ev.x * W), int(ev.y * H))

        if pos is None:
            return

        # Botón CONFIRMAR
        if hasattr(self, "btn_confirm") and self.btn_confirm.collidepoint(pos):
            if self.sel_a is not None and self.sel_b is not None:
                sfx.tap()
                self._confirm()
            return

        for btn in self.buttons_a:
            if btn.hit(pos):
                sfx.select()
                btn.press_t = 6
                # deseleccionar anterior de A
                for b in self.buttons_a:
                    b.selected = False
                btn.selected = True
                self.sel_a = (btn.row, btn.col)
                return

        for btn in self.buttons_b:
            if btn.hit(pos):
                sfx.select()
                btn.press_t = 6
                for b in self.buttons_b:
                    b.selected = False
                btn.selected = True
                self.sel_b = (btn.row, btn.col)
                return

    # ── Confirmar respuesta ──────────────────────────────────────
    def _confirm(self):
        self.confirmed = True
        ar, ac = self.sel_a
        br, bc = self.sel_b
        combo = (ar, ac, br, bc)

        if combo in self.valid_combos:
            # ✓ Correcto
            self.score += 1
            self.karma += 20
            self.power  = min(100, self.power + 10)
            sfx.ok()
            self.flash_col   = C64["green"]
            self.flash_alpha = 120
            an = cell_name("A", ar, ac)
            bn = cell_name("B", br, bc)
            self.feedback_msg = f"✓  {self.target_name} = {an}({self.A[ar][ac]}) + {bn}({self.B[br][bc]}) = {self.target_val}"
            self.feedback_col = C64["green"]
            for btn in self.buttons_a:
                if (btn.row, btn.col) == self.sel_a:
                    btn.correct = True
            for btn in self.buttons_b:
                if (btn.row, btn.col) == self.sel_b:
                    btn.correct = True
        else:
            # ✗ Error
            self.errors += 1
            self.karma  = max(0, self.karma - 5)
            self.power  = max(0, self.power - 8)
            sfx.err()
            self.flash_col   = C64["red"]
            self.flash_alpha = 120
            # Mostrar la respuesta correcta canónica
            cr, cc, dr, dc = next(iter(self.valid_combos))
            an = cell_name("A", cr, cc)
            bn = cell_name("B", dr, dc)
            self.feedback_msg = f"✗  Era: {an}({self.A[cr][cc]}) + {bn}({self.B[dr][dc]}) = {self.target_val}"
            self.feedback_col = C64["red"]
            for btn in self.buttons_a:
                btn.wrong = btn.selected
            for btn in self.buttons_b:
                btn.wrong = btn.selected

        self.feedback_t = 2.2
        # Lanzar módem y pasar al siguiente desafío
        self.challenge_n += 1
        pygame.time.set_timer(pygame.USEREVENT + 10, 2400)   # delay antes del modem

    # ── Siguiente desafío / fin ──────────────────────────────────
    def _next(self):
        if self.challenge_n >= TOTAL:
            self.done = True
            return
        # Cada 2 desafíos regenerar matrices
        if self.challenge_n % 2 == 0:
            self.A, self.B, self.C = make_matrices()
        self._new_challenge()
        # Sonido de modem entre desafíos
        self.modem_active = True
        self.modem_until  = time.time() + 1.7
        self.modem_lines  = self._gen_modem_lines()
        self.modem_line_t = time.time()
        sfx.modem(1600)

    def _gen_modem_lines(self):
        msgs = [
            "CONECTANDO AL SERVIDOR...",
            "HANDSHAKE V.90 → 56000 bps",
            "BUSCANDO SIGUIENTE DESAFIO...",
            f"DESAFIO {self.challenge_n + 1} DE {TOTAL} CARGANDO...",
            "MATRICES REGENERADAS",
            "LISTO.",
        ]
        return msgs[:4 + self.challenge_n % 3]

    # ── Update ──────────────────────────────────────────────────
    def update(self, dt, events):
        self.t      += dt
        self.demo_t += dt

        for ev in events:
            if ev.type == pygame.USEREVENT + 10:
                pygame.time.set_timer(pygame.USEREVENT + 10, 0)
                self._next()

        if self.modem_active and time.time() >= self.modem_until:
            self.modem_active = False

        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 4)

        if self.feedback_t > 0:
            self.feedback_t -= dt

        for btn in self.buttons_a + self.buttons_b:
            btn.update()

        self.pet_anim_t += dt

        # Botón confirmar — posición fija
        self.btn_confirm = pygame.Rect(W//2 - 90, H - 62, 180, 44)

    # ── Draw ────────────────────────────────────────────────────
    def draw(self, surf):
        draw_grid_bg(surf)

        # ── Header ──────────────────────────────────────────────
        px(surf, "🔍 DETECTIVE LAB", W//2, 10,
           self.fonts["title"], C64["yellow"], center=True)
        px(surf, f"DESAFIO {self.challenge_n + 1} DE {TOTAL}   "
                 f"✓ {self.score}   ✗ {self.errors}",
           W//2, 38, self.fonts["sm"], C64["grey"], center=True)

        # ── Instrucción ─────────────────────────────────────────
        px(surf, "Elegí una celda de A y una de B cuya suma sea:",
           W//2, 62, self.fonts["xs"], C64["grey"], center=True)

        # ── Celda objetivo titilante ─────────────────────────────
        self._draw_target(surf)

        # ── Matrices + ecuación ──────────────────────────────────
        if self.modem_active:
            self._draw_modem(surf)
        else:
            self._draw_matrices(surf)
            self._draw_equation(surf)
            self._draw_confirm_btn(surf)

        # ── Feedback ────────────────────────────────────────────
        if self.feedback_t > 0:
            alpha = min(255, int(self.feedback_t * 160))
            s = self.fonts["sm"].render(self.feedback_msg, False, self.feedback_col)
            s.set_alpha(alpha)
            surf.blit(s, (W//2 - s.get_width()//2, H - 110))

        # ── Flash ───────────────────────────────────────────────
        if self.flash_alpha > 0 and self.flash_col:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((*self.flash_col, self.flash_alpha))
            surf.blit(fl, (0, 0))

        # ── Panel stats + bichito ────────────────────────────────
        self._draw_stats(surf)

        # ── Keyboard dashboard hint ───────────────────────────────
        if not self.modem_active:
            self._draw_kbd_hint(surf)

        # ── Banner KidsLab pixel C64 ─────────────────────────────
        self._draw_kidslab_banner(surf)

        # ── Botón RESTART visible ─────────────────────────────────
        self._draw_restart_btn(surf)

        scanlines(surf)
        demo_banner(surf, self.fonts, self.demo_t)

    def _draw_kidslab_banner(self, surf):
        """Banner pixel-art estilo Commodore 64 — monitor con KidsLab."""
        bx, by = 8, 8
        # Monitor pixel-art dibujado con rectángulos
        # Cuerpo del monitor
        pygame.draw.rect(surf, (26, 26, 70),  (bx, by, 110, 72), border_radius=4)
        pygame.draw.rect(surf, C64["border"],  (bx, by, 110, 72), 2, border_radius=4)
        # Pantalla interior
        pygame.draw.rect(surf, (4, 4, 20),    (bx+6, by+6, 98, 50))
        pygame.draw.rect(surf, C64["cyan"],    (bx+6, by+6, 98, 50), 1)
        # Scanlines sobre la pantalla
        for sy in range(by+8, by+54, 4):
            pygame.draw.line(surf, (0,0,0), (bx+7, sy), (bx+102, sy))
        # Pie del monitor
        pygame.draw.rect(surf, (20, 20, 60),  (bx+44, by+72, 22, 6))
        pygame.draw.rect(surf, (26, 26, 70),  (bx+30, by+78, 50, 5), border_radius=2)
        pygame.draw.rect(surf, C64["border"], (bx+30, by+78, 50, 5), 1, border_radius=2)
        # LED verde parpadeante
        led_col = C64["green"] if int(self.t * 2) % 2 == 0 else (30, 80, 30)
        pygame.draw.circle(surf, led_col, (bx+95, by+66), 3)

        # Texto en la pantalla del monitor
        blink_cur = "_" if int(self.t * 3) % 2 == 0 else " "
        px(surf, "KIDS", bx+10, by+12, self.fonts["xs"], C64["cyan"])
        px(surf, "LAB" + blink_cur, bx+10, by+26, self.fonts["xs"], C64["green"])
        px(surf, "🔍 DETECTIVE", bx+10, by+40, self.fonts["xs"], C64["yellow"])

        # Título grande a la derecha del monitor
        px(surf, "DETECTIVE LAB", bx+124, by+10,
           self.fonts["md"], C64["yellow"])
        px(surf, "ORACLE KIDS · KIDSLAB.IO", bx+124, by+30,
           self.fonts["xs"], C64["grey"])
        px(surf, f"DESAFIO {self.challenge_n+1}/{TOTAL}  ✓{self.score}  ✗{self.errors}",
           bx+124, by+46, self.fonts["xs"], C64["cyan"])

    def _draw_restart_btn(self, surf):
        """Botón RESTART visible, esquina inferior izquierda."""
        bx, by, bw, bh = 8, H - 42, 130, 32
        blink = int(self.t * 1.5) % 2 == 0
        col  = C64["yellow"] if blink else C64["orange"]
        fill = (30, 20, 0)
        pygame.draw.rect(surf, fill, (bx, by, bw, bh), border_radius=6)
        pygame.draw.rect(surf, col,  (bx, by, bw, bh), 2, border_radius=6)
        # esquinas pixel
        for cx, cy in [(bx,by),(bx+bw-2,by),(bx,by+bh-2),(bx+bw-2,by+bh-2)]:
            pygame.draw.rect(surf, C64["white"], (cx, cy, 2, 2))
        px(surf, "[ R ] RESTART", bx + bw//2, by + 8,
           self.fonts["xs"], col, center=True)

    def _draw_stats(self, surf):
        """Panel derecho: mascota animada + karma + power."""
        px_x = W - 185
        py   = 140
        pw   = 175

        box(surf, (px_x - 8, py - 8, pw, 230),
            C64["border"], fill=(8, 8, 30))

        # Mascota
        bounce = int(math.sin(self.pet_anim_t * 3) * 4)
        emoji_surf = self.fonts["emoji"].render(
            self.pet["emoji"], True, C64["white"])
        surf.blit(emoji_surf,
                  (px_x + pw//2 - 30 - emoji_surf.get_width()//2,
                   py + 8 + bounce))

        px(surf, self.pet["name"],
           px_x + pw//2 - 30, py + 46,
           self.fonts["sm"], C64["yellow"], center=True)
        px(surf, self.pet["poder"],
           px_x + pw//2 - 30, py + 62,
           self.fonts["xs"], C64["grey"], center=True)

        # Karma
        py2 = py + 88
        px(surf, "KARMA", px_x, py2, self.fonts["xs"], C64["cyan"])
        bar_w = pw - 50
        pygame.draw.rect(surf, C64["dim"], (px_x, py2+14, bar_w, 8))
        kfill = int(bar_w * min(self.karma, 120) / 120)
        if kfill > 0:
            pygame.draw.rect(surf, C64["cyan"], (px_x, py2+14, kfill, 8))
        px(surf, str(self.karma), px_x + bar_w + 4,
           py2 + 12, self.fonts["xs"], C64["cyan"])

        # Power
        py3 = py2 + 34
        px(surf, "POWER", px_x, py3, self.fonts["xs"], C64["green"])
        pygame.draw.rect(surf, C64["dim"], (px_x, py3+14, bar_w, 8))
        pfill = int(bar_w * self.power / 100)
        if pfill > 0:
            col_p = C64["green"] if self.power > 40 else C64["orange"]
            pygame.draw.rect(surf, col_p, (px_x, py3+14, pfill, 8))
        px(surf, f"{self.power}%", px_x + bar_w + 4,
           py3 + 12, self.fonts["xs"], C64["green"])

        # Score rápido
        py4 = py3 + 38
        pygame.draw.line(surf, C64["dim"],
                         (px_x, py4), (px_x + bar_w, py4), 1)
        px(surf, f"✓ {self.score}  ✗ {self.errors}",
           px_x + bar_w//2, py4 + 8,
           self.fonts["sm"], C64["white"], center=True)

        # Hint restart
        px(surf, "[ R ] RESTART",
           px_x + bar_w//2, py4 + 30,
           self.fonts["xs"], C64["dim"], center=True)

    def _draw_kbd_hint(self, surf):
        """Dashboard visual del teclado — A: 1-9 · B: QWEASDZXC."""
        hx = W - 185
        hy = 385
        hw = 175
        hh = 210

        box(surf, (hx - 8, hy - 8, hw, hh),
            C64["dim"], fill=(6, 6, 22))

        px(surf, "TECLADO", hx + hw//2 - 30, hy,
           self.fonts["xs"], C64["grey"], center=True)

        # Teclas A — 1..9
        px(surf, "MATRIZ A", hx, hy + 16, self.fonts["xs"], C64["border"])
        keys_a = ["1","2","3","4","5","6","7","8","9"]
        for i, k in enumerate(keys_a):
            r, c = i//3, i%3
            kx = hx + c*26
            ky = hy + 28 + r*22
            sel = self.sel_a == (r, c)
            col = C64["cyan"] if sel else C64["border"]
            fill = (20, 20, 80) if sel else (8, 8, 30)
            pygame.draw.rect(surf, fill, (kx, ky, 22, 18), border_radius=3)
            pygame.draw.rect(surf, col,  (kx, ky, 22, 18), 1, border_radius=3)
            px(surf, k, kx+11, ky+3, self.fonts["xs"], col, center=True)

        # Teclas B — Q W E / A S D / Z X C
        px(surf, "MATRIZ B", hx + 88, hy + 16, self.fonts["xs"], C64["magenta"])
        keys_b = ["Q","W","E","A","S","D","Z","X","C"]
        for i, k in enumerate(keys_b):
            r, c = i//3, i%3
            kx = hx + 88 + c*26
            ky = hy + 28 + r*22
            sel = self.sel_b == (r, c)
            col = C64["cyan"] if sel else C64["magenta"]
            fill = (60, 10, 60) if sel else (20, 4, 20)
            pygame.draw.rect(surf, fill, (kx, ky, 22, 18), border_radius=3)
            pygame.draw.rect(surf, col,  (kx, ky, 22, 18), 1, border_radius=3)
            px(surf, k, kx+11, ky+3, self.fonts["xs"], col, center=True)

        # ENTER = confirmar
        pygame.draw.line(surf, C64["dim"],
                         (hx, hy+100), (hx+hw-20, hy+100), 1)
        px(surf, "ENTER / SPACE = confirmar",
           hx + hw//2 - 30, hy + 108,
           self.fonts["xs"], C64["dim"], center=True)

        # Valores seleccionados
        if self.sel_a or self.sel_b:
            av = str(self.A[self.sel_a[0]][self.sel_a[1]]) if self.sel_a else "?"
            bv = str(self.B[self.sel_b[0]][self.sel_b[1]]) if self.sel_b else "?"
            an = cell_name("A",*self.sel_a) if self.sel_a else "___"
            bn = cell_name("B",*self.sel_b) if self.sel_b else "___"
            total = (self.A[self.sel_a[0]][self.sel_a[1]] if self.sel_a else 0) +                     (self.B[self.sel_b[0]][self.sel_b[1]] if self.sel_b else 0)
            col_eq = C64["green"] if (self.sel_a and self.sel_b and total == self.target_val)                      else C64["orange"]
            px(surf, f"{an}+{bn}={total if self.sel_a and self.sel_b else '?'}",
               hx + hw//2 - 30, hy + 128,
               self.fonts["sm"], col_eq, center=True)

    def _draw_target(self, surf):
        """Casillero C que titila con el valor objetivo."""
        blink = int(self.t * 3) % 2 == 0
        col   = C64["cyan"] if blink else C64["yellow"]

        tx, ty, tw, th = W - 240, 80, 220, 46
        box(surf, (tx, ty, tw, th), col, fill=(8, 8, 35))

        # Nombre de celda
        px(surf, self.target_name, tx + 10, ty + 4,
           self.fonts["xs"], C64["grey"])

        # Valor grande
        big = pygame.font.Font(
            pygame.font.match_font("couriernew,monospace"), 26)
        vs = big.render(str(self.target_val), False, col)
        surf.blit(vs, (tx + tw//2 - vs.get_width()//2,
                       ty + th//2 - vs.get_height()//2 + 2))

        # Fórmula parcial debajo
        sel_a_txt = "___" if self.sel_a is None else \
            cell_name("A", *self.sel_a)
        sel_b_txt = "___" if self.sel_b is None else \
            cell_name("B", *self.sel_b)
        formula = f"{self.target_name} = {sel_a_txt} + {sel_b_txt}"
        px(surf, formula, tx + tw//2, ty + th + 8,
           self.fonts["sm"], C64["white"], center=True)

    def _draw_matrices(self, surf):
        for btn in self.buttons_a + self.buttons_b:
            btn.draw(surf, self.t)

        # Etiquetas de matriz
        ax0 = 32
        mw  = 3 * self.MAT_CELL_W + 2 * self.MAT_GAP
        bx0 = ax0 + mw + 58
        y0  = 140

        px(surf, "MATRIZ A", ax0 + mw//2, y0 - 28,
           self.fonts["md"], C64["border"], center=True)
        px(surf, "MATRIZ B", bx0 + mw//2, y0 - 28,
           self.fonts["md"], C64["magenta"], center=True)

        # Signo + entre matrices
        sign_x = ax0 + mw + 14
        sign_y = y0 + (3 * self.MAT_CELL_H + 2 * self.MAT_GAP) // 2 - 12
        big = pygame.font.Font(
            pygame.font.match_font("couriernew,monospace"), 32)
        ps = big.render("+", False, C64["yellow"])
        surf.blit(ps, (sign_x, sign_y))

        # Matriz C resultado (solo visual, derecha)
        cx0 = bx0 + mw + 48
        px(surf, "MATRIZ C", cx0 + mw//2, y0 - 28,
           self.fonts["md"], C64["green"], center=True)
        for r in range(3):
            for c in range(3):
                x = cx0 + c * (self.MAT_CELL_W + self.MAT_GAP)
                y = y0  + r * (self.MAT_CELL_H + self.MAT_GAP)
                name = cell_name("C", r, c)
                is_target = (name == self.target_name)
                blink = int(self.t * 3) % 2 == 0
                fill  = (8, 35, 8) if not is_target else \
                        ((20, 80, 20) if blink else (8, 8, 35))
                border = C64["green"] if not is_target else \
                         (C64["cyan"] if blink else C64["yellow"])
                pygame.draw.rect(surf, fill,
                                 (x, y, self.MAT_CELL_W, self.MAT_CELL_H),
                                 border_radius=5)
                pygame.draw.rect(surf, border,
                                 (x, y, self.MAT_CELL_W, self.MAT_CELL_H),
                                 2, border_radius=5)
                px(surf, name, x + 4, y + 2, self.fonts["xs"], C64["dim"])
                if is_target:
                    # signo de interrogación
                    qs = pygame.font.Font(
                        pygame.font.match_font("couriernew,monospace"), 22)
                    q = qs.render("?", False,
                                  C64["cyan"] if blink else C64["yellow"])
                    surf.blit(q, (x + self.MAT_CELL_W//2 - q.get_width()//2,
                                  y + self.MAT_CELL_H//2 - q.get_height()//2 + 4))
                else:
                    big2 = pygame.font.Font(
                        pygame.font.match_font("couriernew,monospace"), 16)
                    vs = big2.render(str(self.C[r][c]), False, C64["green"])
                    surf.blit(vs, (x + self.MAT_CELL_W//2 - vs.get_width()//2,
                                   y + self.MAT_CELL_H//2 - vs.get_height()//2 + 4))

    def _draw_equation(self, surf):
        """Ecuación parcial en la zona inferior."""
        if self.sel_a and self.sel_b:
            ar, ac = self.sel_a
            br, bc = self.sel_b
            av, bv = self.A[ar][ac], self.B[br][bc]
            an = cell_name("A", ar, ac)
            bn = cell_name("B", br, bc)
            eq = f"{self.target_name} = {an}({av}) + {bn}({bv}) = {av+bv}"
            col = C64["cyan"] if av + bv == self.target_val else C64["orange"]
            px(surf, eq, W//2, H - 80, self.fonts["md"], col, center=True)

    def _draw_confirm_btn(self, surf):
        ready = self.sel_a is not None and self.sel_b is not None
        col   = C64["green"] if ready else C64["dim"]
        fill  = (10, 50, 10) if ready else (10, 10, 30)
        r     = self.btn_confirm
        pygame.draw.rect(surf, fill, r, border_radius=8)
        pygame.draw.rect(surf, col, r, 2, border_radius=8)
        label = "[ CONFIRMAR ]" if ready else "[ elegí A y B ]"
        px(surf, label, r.centerx, r.centery - 8,
           self.fonts["sm"], col, center=True)

    def _draw_modem(self, surf):
        """Pantalla de carga estilo módem entre desafíos."""
        bx, by, bw, bh = 80, 130, W - 160, 360
        box(surf, (bx, by, bw, bh), C64["cyan"], fill=(4, 4, 20))

        px(surf, "// CALCULANDO SIGUIENTE DESAFIO...",
           bx + bw//2, by + 20, self.fonts["md"], C64["cyan"], center=True)
        pygame.draw.line(surf, C64["dim"],
                         (bx+20, by+44), (bx+bw-20, by+44), 1)

        elapsed = time.time() - (self.modem_until - 1.7)
        for i, line in enumerate(self.modem_lines):
            appear = i * 0.28
            if elapsed >= appear:
                alpha_t = min(1.0, (elapsed - appear) / 0.15)
                col = [C64["cyan"], C64["yellow"],
                       C64["green"], C64["grey"]][i % 4]
                cursor = ("_" if int(self.t * 4) % 2 == 0 else " ") \
                    if i == len(self.modem_lines) - 1 else ""
                px(surf, f"> {line}{cursor}",
                   bx + 30, by + 70 + i * 34,
                   self.fonts["sm"], col)

        # Barra de progreso
        prog = min(1.0, elapsed / 1.7)
        bary = by + bh - 50
        pygame.draw.rect(surf, C64["dim"], (bx+20, bary, bw-40, 14))
        fw = int((bw-44) * prog)
        if fw > 0:
            pygame.draw.rect(surf, C64["cyan"], (bx+22, bary+2, fw, 10))
        px(surf, f"{int(prog*100)}%", bx + bw//2, bary + 18,
           self.fonts["xs"], C64["grey"], center=True)


# ══════════════════════════════════════════════════════════════════
# PANTALLA FINAL
# ══════════════════════════════════════════════════════════════════
class EndScreen:
    def __init__(self, fonts, score, errors):
        self.fonts   = fonts
        self.score   = score
        self.errors  = errors
        self.t       = 0.0
        self.demo_t  = 0.0
        self.restart = False
        sfx.win()

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (
                pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
            self.restart = True
        if ev.type == pygame.MOUSEBUTTONDOWN:
            btn = pygame.Rect(W//2 - 120, H//2 + 120, 240, 50)
            if btn.collidepoint(ev.pos):
                sfx.tap()
                self.restart = True

    def update(self, dt):
        self.t      += dt
        self.demo_t += dt

    def draw(self, surf):
        draw_grid_bg(surf)

        pct = int(self.score / TOTAL * 100)
        col = C64["green"] if pct >= 60 else C64["orange"]

        px(surf, "🔍 DETECTIVE LAB — RESULTADO",
           W//2, 80, self.fonts["title"], C64["yellow"], center=True)

        px(surf, f"✓ CORRECTAS : {self.score} / {TOTAL}",
           W//2, 160, self.fonts["lg"], C64["green"], center=True)
        px(surf, f"✗ ERRORES   : {self.errors}",
           W//2, 195, self.fonts["lg"], C64["red"], center=True)
        px(surf, f"PUNTUACION  : {pct}%",
           W//2, 230, self.fonts["lg"], col, center=True)

        msg = ("★ DETECTIVE EXPERTO ★" if pct == 100 else
               "¡MUY BIEN, DETECTIVE!" if pct >= 60 else
               "SEGUÍ ENTRENANDO...")
        b = int(math.sin(self.t * 3) * 6)
        px(surf, msg, W//2, 290 + b, self.fonts["title"], col, center=True)

        # Botón reiniciar
        btn = pygame.Rect(W//2 - 120, H//2 + 120, 240, 50)
        bc  = C64["cyan"] if int(self.t*2)%2==0 else C64["yellow"]
        box(surf, tuple(btn), bc, fill=(8,8,35))
        px(surf, "[ R ]  JUGAR DE NUEVO",
           btn.centerx, btn.centery - 8,
           self.fonts["sm"], bc, center=True)

        px(surf, "ASPR ORACLE NODE v2.0  ·  KIDSLAB.IO",
           W//2, H - 28, self.fonts["xs"], C64["dim"], center=True)

        scanlines(surf)
        demo_banner(surf, self.fonts, self.demo_t)


# ══════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════
class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("🔍 KidsLab — Detective Lab")
        self.clock  = pygame.time.Clock()
        self.fonts  = load_fonts()
        sfx.init()
        self._new_game()

    def _new_game(self):
        pygame.time.set_timer(pygame.USEREVENT + 10, 0)  # cancelar timer pendiente
        self.state = "game"
        self.game  = DetectiveGame(self.fonts)

    def run(self):
        while True:
            dt     = self.clock.tick(FPS) / 1000.0
            events = pygame.event.get()

            for ev in events:
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                if self.state == "game":
                    self.game.handle_event(ev)
                elif self.state == "end":
                    self.end.handle_event(ev)
                # Restart global desde cualquier estado
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    self._new_game()

            if self.state == "game":
                self.game.update(dt, events)
                self.game.draw(self.screen)
                if self.game.restart_requested:
                    self._new_game()
                elif self.game.done:
                    self.state = "end"
                    self.end   = EndScreen(
                        self.fonts, self.game.score, self.game.errors)

            elif self.state == "end":
                self.end.update(dt)
                self.end.draw(self.screen)
                if self.end.restart:
                    self._new_game()

            pygame.display.flip()


if __name__ == "__main__":
    App().run()
