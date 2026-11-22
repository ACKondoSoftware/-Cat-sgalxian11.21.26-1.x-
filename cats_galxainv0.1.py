#!/usr/bin/env python3
# ============================================================================
#  GALAXIAN — arcade-style recreation by A.C Holdings / Team Flames
#  single file · FILES=OFF · string sprites · 3x5 bitmap font · synth audio
#  1979-inspired arcade presentation, formation attacks and synthesized SFX
#  controls: <-/-> or A/D move · SPACE/Z fire · P pause · M mute · ESC quit
# ============================================================================
import math, random, sys, array
import pygame

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

W, H = 224, 288
FPS = 60
ROT = 32
TITLE = "cat's galxain"
TAU = math.tau

PAL = {
    'W': (255, 255, 255), 'R': (232, 40, 40), 'B': (60, 110, 255),
    'Y': (255, 224, 32), 'P': (190, 60, 230), 'C': (40, 220, 230),
    'G': (60, 230, 90), 'O': (255, 140, 20), 'K': (120, 120, 140),
}

# ---------------------------------------------------------------- sprites ---
# Hand-drawn original pixel sprites inspired by the 1979 arcade silhouettes.
PLAYER = [
    "......W......",
    "......W......",
    ".....WWW.....",
    ".....WRW.....",
    ".....WRW.....",
    "..W..WWW..W..",
    "..WWWWWWWWW..",
    ".WWWWWWWWWWW.",
    "WWWWWRRRWWWWW",
    "WWWW.....WWWW",
]
AL1 = [
    "B.........B",
    ".B...Y...B.",
    "..B.CCC.B..",
    "...BCCCB...",
    "..BBBBBBB..",
    ".BB.BBB.BB.",
    "B...B.B...B",
    "...........",
]
AL2 = [
    "...........",
    "B....Y....B",
    "BB..CCC..BB",
    ".BBBCCCBBB.",
    "..BBBBBBB..",
    "...BB.BB...",
    "..B.....B..",
    "...........",
]
FL1 = [
    "R...........R",
    ".R....Y....R.",
    "..R..YYY..R..",
    "...RRWWWRR...",
    "RRRRRWWWRRRRR",
    "R..RRWWWRR..R",
    "....R.R.R....",
    "...R.....R...",
    ".............",
]
FL2 = [
    ".............",
    "R.....Y.....R",
    "RR...YYY...RR",
    ".RRRRWWWRRRR.",
    "..RRRWWWRRR..",
    "R..RRWWWRR..R",
    "...RR.R.RR...",
    "....R...R....",
    ".............",
]
FLAGICON = ["WRRR.", "WRRRR", "WRRR.", "W....", "W....", "W...."]

KINDS = {
    'flag':   dict(wing=PAL['R'], body=PAL['W'], eye=PAL['Y'], pts=(60, 150), name="FLAGSHIP"),
    'red':    dict(wing=PAL['R'], body=PAL['W'], eye=PAL['Y'], pts=(50, 100), name="RED"),
    'purple': dict(wing=PAL['P'], body=PAL['W'], eye=PAL['Y'], pts=(40, 80),  name="PURPLE"),
    'drone':  dict(wing=PAL['B'], body=PAL['C'], eye=PAL['Y'], pts=(30, 60),  name="BLUE"),
}

GLYPHS = {
    '0': "111101101101111", '1': "010110010010111", '2': "111001111100111",
    '3': "111001111001111", '4': "101101111001001", '5': "111100111001111",
    '6': "111100111101111", '7': "111001001010010", '8': "111101111101111",
    '9': "111101111001111", 'A': "010101111101101", 'B': "110101110101110",
    'C': "011100100100011", 'D': "110101101101110", 'E': "111100110100111",
    'F': "111100110100100", 'G': "011100101101011", 'H': "101101111101101",
    'I': "111010010010111", 'J': "001001001101010", 'K': "101101110101101",
    'L': "100100100100111", 'M': "101111111101101", 'N': "110101101101101",
    'O': "010101101101010", 'P': "110101110100100", 'Q': "010101101110011",
    'R': "110101110101101", 'S': "011100010001110", 'T': "111010010010010",
    'U': "101101101101111", 'V': "101101101101010", 'W': "101101111111101",
    'X': "101101010101101", 'Y': "101101010010010", 'Z': "111001010100111",
    '-': "000000111000000", "'": "010010000000000", '.': "000000000000010",
    '!': "010010010000010", ':': "000010000010000", '/': "001001010100100",
    '<': "001010100010001", '>': "100010001010100",
    ' ': "000000000000000",
}


def make_sprite(rows, cmap=None):
    cmap = cmap or {}
    s = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != '.':
                s.set_at((x, y), cmap.get(ch, PAL.get(ch, (255, 0, 255))))
    return s


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


class Font:
    def __init__(self):
        self.cache = {}

    def glyph(self, ch, col, size):
        key = (ch, col, size)
        g = self.cache.get(key)
        if g is None:
            bits = GLYPHS.get(ch, GLYPHS[' '])
            g = pygame.Surface((3 * size, 5 * size), pygame.SRCALPHA)
            for i, b in enumerate(bits):
                if b == '1':
                    g.fill(col, ((i % 3) * size, (i // 3) * size, size, size))
            self.cache[key] = g
        return g

    def draw(self, dst, text, x, y, col, size=1, center=False):
        text = str(text).upper()
        adv = 4 * size
        if center:
            x = x - (len(text) * adv - size) // 2
        for ch in text:
            dst.blit(self.glyph(ch, col, size), (x, y))
            x += adv


# ------------------------------------------------------------ audio engine ---
class AudioEngine:
    """FILES=OFF synth: square/tri/saw/sine/noise voices, envelopes, sweeps,
    vibrato, sequencer, and phase-continuous loopable background hum."""

    def __init__(self):
        self.on = False
        self.muted = False
        self.sfx = {}
        self.hum = []
        self.hum_ix = -1
        try:
            init = pygame.mixer.get_init()
            if not init:
                pygame.mixer.init(22050, -16, 1, 512)
                init = pygame.mixer.get_init()
            self.sr, size, self.ch = init
            self.fmt = {-16: 'h', 16: 'H', -8: 'b', 8: 'B', 32: 'f'}.get(size, 'h')
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(2)
            self.hum_ch = pygame.mixer.Channel(0)
            self.dive_ch = pygame.mixer.Channel(1)
            self.hum_ch.set_volume(0.7)
            self._build()
            self.on = True
        except Exception as e:  # no device → silent but playable
            print("audio off:", e)

    # --- dsp primitives
    @staticmethod
    def osc(wave, ph, duty):
        p = ph % 1.0
        if wave == 'sq':
            return 1.0 if p < duty else -1.0
        if wave == 'tri':
            return 4.0 * abs(p - 0.5) - 1.0
        if wave == 'saw':
            return 2.0 * p - 1.0
        return math.sin(TAU * p)

    def voice(self, dur, f0, f1=None, wave='sq', vol=0.3, att=0.003, dec=1.0,
              duty=0.5, vib=0.0, vibf=6.0, curve=1.0):
        sr = self.sr
        n = max(1, int(dur * sr))
        f1 = f0 if f1 is None else f1
        out = [0.0] * n
        ph, nz, last = 0.0, 0.0, 0
        a = max(1.0, att * sr)
        osc = self.osc
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * (t ** curve)
            if vib:
                f *= 1.0 + vib * math.sin(TAU * vibf * i / sr)
            ph += f / sr
            if wave == 'noise':
                k = int(ph)
                if k != last:
                    last = k
                    nz = random.uniform(-1.0, 1.0)
                s = nz
            else:
                s = osc(wave, ph, duty)
            e = min(1.0, i / a) * (1.0 - t) ** dec
            out[i] = s * e * vol
        return out

    @staticmethod
    def mix(*bufs):
        n = max(len(b) for b in bufs)
        out = [0.0] * n
        for b in bufs:
            for i, v in enumerate(b):
                out[i] += v
        return out

    def seq(self, notes, dur, **kw):
        buf = []
        for n in notes:
            buf += self.voice(dur, midi(n), **kw) if n else [0.0] * int(dur * self.sr)
        return buf

    def hum_loop(self, f, lfo, vol, dep=0.035):
        # integer f & lfo over exactly 1 s → seamless loop (phase integral closes)
        sr = self.sr
        out = [0.0] * sr
        k = f * dep / (TAU * lfo)
        for i in range(sr):
            t = i / sr
            ph = f * t - k * math.cos(TAU * lfo * t)
            p = ph % 1.0
            tri = 4.0 * abs(p - 0.5) - 1.0
            s2 = math.sin(TAU * ph * 2.0)
            amp = 0.55 + 0.45 * math.sin(TAU * lfo * t)
            out[i] = (tri * 0.7 + s2 * 0.3) * amp * vol
        return out

    def pack(self, buf):
        c = [max(-1.0, min(1.0, s)) for s in buf]
        f = self.fmt
        if f == 'h':
            vals = [int(s * 32767) for s in c]
        elif f == 'H':
            vals = [int(s * 32767) + 32768 for s in c]
        elif f == 'b':
            vals = [int(s * 127) for s in c]
        elif f == 'B':
            vals = [int(s * 127) + 128 for s in c]
        else:
            vals = c
        if self.ch > 1:
            vals = [v for v in vals for _ in range(self.ch)]
        return pygame.mixer.Sound(buffer=array.array(f, vals).tobytes())

    # --- sound bank
    def _build(self):
        v, m = self.voice, self.mix
        hit = m(v(0.30, 2400, 200, 'noise', 0.45, dec=2.0),
                v(0.15, 600, 100, 'sq', 0.15, dec=2.0))
        bank = {
            'shoot': m(v(0.14, 1600, 300, 'sq', 0.22, duty=0.25, dec=1.5),
                       v(0.05, 5000, 2000, 'noise', 0.10)),
            'hit': hit,
            'flaghit': m(hit, self.seq([96, 91, 88, 84, 79], 0.05, wave='sq',
                                       vol=0.16, duty=0.25, dec=0.5)),
            'boom': m(v(1.10, 1800, 60, 'noise', 0.55, dec=1.6, curve=0.5),
                      v(0.90, 180, 40, 'tri', 0.40, dec=1.2)),
            'dive': v(0.75, 1900, 350, 'tri', 0.22, dec=0.6, vib=0.04, vibf=14, curve=0.7),
            'extra': self.seq([72, 76, 79, 84, 88, 91], 0.06, wave='sq', vol=0.18, duty=0.25, dec=0.4),
            'wave': self.seq([84, 88, 91, 96, 0, 96], 0.08, wave='sq', vol=0.18, duty=0.125, dec=0.5),
            'coin': v(0.07, 1000, 2000, 'sq', 0.18, duty=0.25),
            'over': self.seq([79, 75, 72, 67, 63, 60, 60], 0.2, wave='tri', vol=0.35, dec=0.5),
            'jingle': m(
                self.seq([72, 0, 76, 79, 84, 0, 79, 76, 77, 0, 81, 84, 83, 79, 74, 0,
                          76, 79, 84, 88, 86, 83, 79, 0, 84, 0, 84, 0, 84],
                         0.12, wave='sq', vol=0.17, duty=0.25, dec=0.6),
                self.seq([48, 48, 55, 55, 53, 53, 55, 55, 48, 48, 55, 55, 48, 0, 48],
                         0.24, wave='tri', vol=0.30, dec=0.3)),
        }
        self.sfx = {k: self.pack(b) for k, b in bank.items()}
        self.hum = [self.pack(self.hum_loop(f, l, vv))
                    for f, l, vv in ((98, 2, 0.10), (131, 3, 0.10), (175, 5, 0.11))]

    # --- api
    def play(self, name):
        if self.on and not self.muted:
            if name == 'dive':
                self.dive_ch.play(self.sfx[name])
            else:
                self.sfx[name].play()

    def hum_set(self, ix):
        if not self.on:
            return
        if self.muted:
            ix = -1
        if ix == self.hum_ix:
            return
        self.hum_ix = ix
        if ix < 0:
            self.hum_ch.fadeout(200)
        else:
            self.hum_ch.play(self.hum[ix], loops=-1, fade_ms=150)

    def toggle(self):
        self.muted = not self.muted
        if self.on and self.muted:
            pygame.mixer.stop()

    def pause(self, p):
        if self.on:
            (pygame.mixer.pause if p else pygame.mixer.unpause)()


# ------------------------------------------------------------------ actors ---
class Alien:
    def __init__(self, kind, col, row):
        self.kind, self.col, self.row = kind, col, row
        self.state = 'form'
        self.x = self.y = 0.0
        self.h = math.pi / 2
        self.alive = True
        self.dir = 1
        self.turned = 0.0
        self.t = 0
        self.shots = 0
        self.seed = random.uniform(0, TAU)
        self.leader = None
        self.off = (0, 0)
        self.esc_total = 0
        self.esc_killed = 0


class Boom:
    def __init__(self, x, y, cols, big=False):
        self.x, self.y, self.big = x, y, big
        self.t = 0
        self.life = 44 if big else 26
        n = 30 if big else 14
        k = 1.7 if big else 1.0
        self.p = [(random.uniform(0, TAU), random.uniform(0.4, 1.6) * k, random.choice(cols))
                  for _ in range(n)]

    def draw(self, dst):
        k, L = self.t, self.life
        r0 = k - k * k / (2 * L)
        fade = 1 - k / L
        sz = 2 if self.big else 1
        for ang, sp, c in self.p:
            r = sp * r0 * 0.9
            col = (int(c[0] * fade), int(c[1] * fade), int(c[2] * fade))
            dst.fill(col, (int(self.x + math.cos(ang) * r), int(self.y + math.sin(ang) * r), sz, sz))
        if k < 6:
            pygame.draw.circle(dst, (255, 255, 200), (int(self.x), int(self.y)), 6 - k)


# -------------------------------------------------------------------- game ---
class Game:
    def __init__(self):
        info = pygame.display.Info()
        sc = max(1, min(3, (info.current_h - 100) // H)) if info.current_h > 0 else 2
        self.win = pygame.display.set_mode((W * sc, H * sc))
        pygame.display.set_caption(TITLE)
        self.scr = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font = Font()
        self.audio = AudioEngine()
        self.build_sprites()
        cols = [PAL[c] for c in "WRBYPCGO"]
        self.stars = [[random.uniform(0, W), random.uniform(0, H), random.choice(cols),
                       random.uniform(0.3, 1.2), random.uniform(0, TAU), random.uniform(0.02, 0.08)]
                      for _ in range(70)]
        self.hi = 5000
        self.tick = 0
        self.state = 'title'
        self.paused = False
        self.score, self.lives, self.level = 0, 3, 1
        self.aliens, self.ebul, self.booms, self.popups = [], [], [], []
        self.missile = None
        self.px, self.py = W / 2, H - 30
        self.player_alive = False
        self.timer = 0
        self.form_t = 0
        self.dive_timer = 0
        self.extra_given = False

    def build_sprites(self):
        self.spr = {}
        for kind, t in KINDS.items():
            cmap = {'a': t['wing'], 'b': t['body'], 'c': t['eye']}
            frames = (FL1, FL2) if kind == 'flag' else (AL1, AL2)
            base = [make_sprite(f, cmap) for f in frames]
            self.spr[kind] = [[pygame.transform.rotate(b, -i * 360 / ROT) for i in range(ROT)]
                              for b in base]
        self.player_spr = make_sprite(PLAYER)
        self.flag_spr = make_sprite(FLAGICON)

    # --- setup
    def new_game(self):
        self.score, self.lives, self.level = 0, 3, 1
        self.extra_given = False
        self.new_wave()
        self.px = W / 2
        self.player_alive = True
        self.state, self.timer = 'ready', 150
        self.audio.play('coin')

    def new_wave(self):
        A = []
        for c in (3, 6):
            A.append(Alien('flag', c, 0))
        for c in range(2, 8):
            A.append(Alien('red', c, 1))
        for c in range(1, 9):
            A.append(Alien('purple', c, 2))
        for r in (3, 4, 5):
            for c in range(10):
                A.append(Alien('drone', c, r))
        self.aliens = A
        self.ebul, self.booms, self.popups = [], [], []
        self.missile = None
        self.dive_timer = 120
        for a in A:
            a.x, a.y = self.slot(a)

    def slot(self, a):
        fx = math.sin(self.form_t * 0.012) * 22
        return W / 2 + (a.col - 4.5) * 16 + fx, 36 + a.row * 12

    def add_score(self, p):
        self.score += p
        self.hi = max(self.hi, self.score)
        if not self.extra_given and self.score >= 7000:
            self.extra_given = True
            self.lives += 1
            self.audio.play('extra')

    # --- dive director
    def launch(self, a, d):
        a.state = 'loop'
        a.h = -math.pi / 2
        a.dir, a.turned, a.shots, a.t = d, 0.0, 0, 0
        self.audio.play('dive')

    def launch_some(self):
        form = [a for a in self.aliens if a.alive and a.state == 'form']
        if not form:
            return
        flags = [a for a in form if a.kind == 'flag']
        if flags and random.random() < 0.22:
            f = random.choice(flags)
            d = -1 if f.col < 5 else 1
            esc = sorted([a for a in form if a.kind == 'red' and abs(a.col - f.col) <= 1],
                         key=lambda e: e.col)[:2]
            self.launch(f, d)
            f.esc_total, f.esc_killed = len(esc), 0
            for i, e in enumerate(esc):
                side = (-1 if i == 0 else 1) if len(esc) == 2 else (-1 if e.col < f.col else 1)
                e.state, e.leader, e.off, e.shots = 'escort', f, (11 * side, -11), 0
            return
        side = random.choice((-1, 1))
        ec = min(a.col for a in form) if side < 0 else max(a.col for a in form)
        self.launch(random.choice([a for a in form if a.col == ec]), side)

    def alien_fire(self, a):
        if self.state != 'play' or not self.player_alive:
            return
        if a.shots >= (2 if self.level < 3 else 3):
            return
        if 70 < a.y < 200 and random.random() < 0.025 + 0.004 * self.level:
            a.shots += 1
            vy = 2.0 + 0.12 * min(self.level, 8)
            t = max(1.0, (self.py - a.y) / vy)
            self.ebul.append([a.x, a.y + 4, clamp((self.px - a.x) / t, -0.7, 0.7), vy])

    def update_alien(self, a):
        if a.state == 'form':
            a.x, a.y = self.slot(a)
            a.h = math.pi / 2
            return
        spd = 1.5 + 0.08 * min(self.level, 10)
        if a.state == 'loop':
            a.x += math.cos(a.h) * spd
            a.y += math.sin(a.h) * spd
            step = 0.065
            a.h += a.dir * step
            a.turned += step
            if a.turned >= math.pi:
                a.state, a.t, a.h = 'dive', 0, math.pi / 2
        elif a.state == 'escort':
            L = a.leader
            if L is None or not L.alive or L.state not in ('loop', 'dive'):
                a.state, a.t = 'dive', 0
            else:
                ang = L.h - math.pi / 2
                ox, oy = a.off
                ca, sa = math.cos(ang), math.sin(ang)
                a.x += (L.x + ox * ca - oy * sa - a.x) * 0.2
                a.y += (L.y + ox * sa + oy * ca - a.y) * 0.2
                a.h = L.h
                if L.state == 'dive':
                    self.alien_fire(a)
        elif a.state == 'dive':
            a.t += 1
            vy = spd * 1.05
            vx = clamp((self.px - a.x) * 0.03, -1.4, 1.4) + math.sin(a.t * 0.06 + a.seed) * 0.9
            if a.kind == 'flag':
                vx *= 0.8
            a.x = clamp(a.x + vx, 4, W - 4)
            a.y += vy
            a.h = math.atan2(vy, vx)
            self.alien_fire(a)
            if a.y > H + 10:
                a.y, a.state = -12, 'return'
        elif a.state == 'return':
            sx, sy = self.slot(a)
            dx, dy = sx - a.x, sy - a.y
            d = math.hypot(dx, dy)
            if d < 2:
                a.state = 'form'
            else:
                s = min(d, 1.8)
                a.x += dx / d * s
                a.y += dy / d * s
                a.h = math.atan2(dy, dx)

    # --- combat
    def kill_alien(self, a):
        a.alive = False
        fp, dp = KINDS[a.kind]['pts']
        if a.state == 'form':
            pts = fp
        elif a.kind == 'flag':
            if a.esc_total and a.esc_killed >= a.esc_total:
                pts = 800 if a.esc_total == 2 else 300
            elif a.esc_killed:
                pts = 200
            else:
                pts = 150
            self.popups.append([a.x, a.y, str(pts), 70])
        else:
            pts = dp
        if a.state == 'escort' and a.leader is not None and a.leader.alive:
            a.leader.esc_killed += 1
        self.add_score(pts)
        t = KINDS[a.kind]
        self.booms.append(Boom(a.x, a.y, [t['wing'], t['body'], PAL['Y'], PAL['W']], a.kind == 'flag'))
        self.audio.play('flaghit' if a.kind == 'flag' else 'hit')

    def kill_player(self):
        self.player_alive = False
        self.lives -= 1
        self.state, self.timer = 'dead', 200
        self.missile = None
        self.booms.append(Boom(self.px, self.py, [PAL['W'], PAL['R'], PAL['Y'], PAL['O']], True))
        self.audio.play('boom')

    # --- frame
    def update(self):
        self.tick += 1
        # Fixed arcade starfield: stars twinkle but do not scroll.
        if self.state == 'title':
            self.audio.hum_set(-1)
            return

        self.form_t += 1
        keys = pygame.key.get_pressed()
        for a in self.aliens:
            if a.alive:
                self.update_alien(a)

        if self.player_alive and self.state in ('ready', 'play'):
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            self.px = clamp(self.px + dx * 1.6, 8, W - 8)
            if self.state == 'play' and self.missile is None and \
                    (keys[pygame.K_SPACE] or keys[pygame.K_z] or keys[pygame.K_UP]):
                self.missile = [self.px, self.py - 9]
                self.audio.play('shoot')

        if self.state == 'play':
            divers = sum(1 for a in self.aliens if a.alive and a.state != 'form')
            self.dive_timer -= 1
            if self.dive_timer <= 0:
                frac = sum(a.alive for a in self.aliens) / 46
                base = max(45, 160 - self.level * 14)
                self.dive_timer = int(base * (0.35 + 0.65 * frac)) + random.randint(0, 40)
                if divers < min(2 + self.level, 7) + (3 if frac < 0.25 else 0):
                    self.launch_some()

        m = self.missile
        if m:
            m[1] -= 5
            if m[1] < 8:
                self.missile = None
            else:
                for a in self.aliens:
                    if a.alive and abs(a.x - m[0]) < (7 if a.kind == 'flag' else 6) and abs(a.y - m[1]) < 5:
                        self.kill_alien(a)
                        self.missile = None
                        break

        for b in self.ebul:
            b[0] += b[2]
            b[1] += b[3]
        self.ebul = [b for b in self.ebul if b[1] < H + 4]

        if self.player_alive and self.state == 'play':
            for b in self.ebul:
                if abs(b[0] - self.px) < 5 and self.py - 5 < b[1] < self.py + 5:
                    self.ebul.remove(b)
                    self.kill_player()
                    break
        if self.player_alive and self.state == 'play':
            for a in self.aliens:
                if a.alive and a.state != 'form' and abs(a.x - self.px) < 9 and abs(a.y - self.py) < 8:
                    self.kill_alien(a)
                    self.kill_player()
                    break

        for bm in self.booms:
            bm.t += 1
        self.booms = [bm for bm in self.booms if bm.t < bm.life]
        for p in self.popups:
            p[3] -= 1
            p[1] -= 0.2
        self.popups = [p for p in self.popups if p[3] > 0]

        st = self.state
        if st == 'ready':
            self.timer -= 1
            if self.timer <= 0:
                self.state = 'play'
        elif st == 'play':
            if not any(a.alive for a in self.aliens):
                self.state, self.timer = 'clear', 150
                self.audio.play('wave')
        elif st == 'dead':
            self.timer -= 1
            settled = all(a.state == 'form' for a in self.aliens if a.alive)
            if self.timer <= 0 and settled:
                if self.lives > 0:
                    self.player_alive = True
                    self.px = W / 2
                    self.ebul = []
                    self.state, self.timer = 'ready', 90
                else:
                    self.state, self.timer = 'over', 300
                    self.audio.play('over')
        elif st == 'clear':
            self.timer -= 1
            if self.timer <= 0:
                self.level += 1
                self.new_wave()
                self.state, self.timer = 'ready', 120
                self.audio.play('coin')
        elif st == 'over':
            self.timer -= 1
            if self.timer <= 0:
                self.state = 'title'

        if self.state == 'play' and self.player_alive:
            self.audio.hum_set(-1)
        else:
            self.audio.hum_set(-1)

    # --- render
    def draw_alien(self, a):
        if a.state == 'form':
            fr, idx = ((self.tick // 14) + a.col) % 2, 0
        else:
            fr = (self.tick // 6) % 2
            idx = round((a.h - math.pi / 2) / (TAU / ROT)) % ROT
        s = self.spr[a.kind][fr][idx]
        self.scr.blit(s, s.get_rect(center=(int(a.x), int(a.y))))

    def draw_hud(self):
        F, S = self.font, self.scr
        if self.state != 'title' and (self.tick // 20) % 2:
            F.draw(S, "1UP", 14, 2, PAL['R'])
        F.draw(S, "%d" % self.score, 14, 9, PAL['W'])
        F.draw(S, "HI-SCORE", W // 2, 2, PAL['R'], center=True)
        F.draw(S, "%d" % self.hi, W // 2, 9, PAL['W'], center=True)
        if self.state != 'title':
            reserve = self.lives - 1 if self.player_alive else self.lives
            for i in range(max(0, min(reserve, 6))):
                S.blit(self.player_spr, (4 + i * 15, H - 12))
            for i in range(min(self.level, 12)):
                S.blit(self.flag_spr, (W - 9 - i * 7, H - 9))

    def draw_title(self):
        F, S = self.font, self.scr
        F.draw(S, "CAT'S GALXAIN", W // 2, 40, PAL['Y'], 2, True)
        F.draw(S, "ARCADE RECREATION", W // 2, 65, PAL['C'], center=True)
        F.draw(S, "- SCORE ADVANCE TABLE -", W // 2, 92, PAL['W'], center=True)
        F.draw(S, "FORM  ATTACK", 153, 107, PAL['K'], center=True)
        for i, k in enumerate(('flag', 'red', 'purple', 'drone')):
            y = 120 + i * 22
            spr = self.spr[k][(self.tick // 18) % 2][0]
            S.blit(spr, spr.get_rect(center=(40, y + 4)))
            t = KINDS[k]
            F.draw(S, t['name'], 57, y, t['wing'])
            F.draw(S, str(t['pts'][0]), 129, y, PAL['W'])
            F.draw(S, "150-800" if k == 'flag' else str(t['pts'][1]), 153, y, PAL['W'])
        if (self.tick // 30) % 2 == 0:
            F.draw(S, "PRESS SPACE TO START", W // 2, 224, PAL['W'], center=True)
        F.draw(S, "ARROWS / A D : MOVE", W // 2, 243, PAL['C'], center=True)
        F.draw(S, "SPACE / Z : FIRE", W // 2, 253, PAL['C'], center=True)
        F.draw(S, "P PAUSE  M MUTE  ESC EXIT", W // 2, 264, PAL['K'], center=True)
        F.draw(S, "AC HOLDINGS 2026", W // 2, 280, PAL['R'], center=True)

    def draw(self):
        S, F = self.scr, self.font
        S.fill((0, 0, 0))
        for x, y, c, sp, ph, rt in self.stars:
            if math.sin(self.tick * rt + ph) > -0.2:
                S.set_at((int(x), int(y)), c)
        if self.state == 'title':
            self.draw_title()
        else:
            for a in self.aliens:
                if a.alive:
                    self.draw_alien(a)
            for b in self.ebul:
                S.fill(PAL['W'], (int(b[0]), int(b[1]), 1, 3))
                S.fill(PAL['R'], (int(b[0]), int(b[1]) + 3, 1, 1))
            if self.missile:
                S.fill(PAL['Y'], (int(self.missile[0]), int(self.missile[1]), 1, 4))
            elif self.player_alive:
                S.fill(PAL['Y'], (int(self.px), int(self.py) - 9, 1, 4))
            if self.player_alive:
                S.blit(self.player_spr, self.player_spr.get_rect(center=(int(self.px), int(self.py))))
            for bm in self.booms:
                bm.draw(S)
            for x, y, txt, t in self.popups:
                F.draw(S, txt, int(x), int(y), PAL['Y'], center=True)
            if self.state == 'ready':
                F.draw(S, "PLAYER ONE", W // 2, 150, PAL['C'], center=True)
                F.draw(S, "READY!", W // 2, 162, PAL['Y'], 2, True)
            elif self.state == 'clear':
                F.draw(S, "WAVE CLEAR!", W // 2, 150, PAL['G'], 2, True)
            elif self.state == 'over':
                F.draw(S, "GAME OVER", W // 2, 150, PAL['R'], 2, True)
            if self.paused:
                F.draw(S, "PAUSED", W // 2, 130, PAL['W'], 2, True)
        self.draw_hud()
        pygame.transform.scale(S, self.win.get_size(), self.win)
        pygame.display.flip()

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif e.key == pygame.K_m:
                        self.audio.toggle()
                    elif e.key == pygame.K_p and self.state != 'title':
                        self.paused = not self.paused
                        self.audio.pause(self.paused)
                    elif self.state == 'title' and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.new_game()
            if not self.paused:
                self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == '__main__':
    Game().run()
