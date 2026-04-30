"""
Megaways slot — 6 reels × 2-7 rows, left-to-right ways wins, free spins bonus.

Run:    python slot_megaways.py
Icons:  drop PNGs into the icons/ folder (see icons/README.txt for names).
        Missing icons fall back to colored circles.
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import pygame

# ---------------------------------------------------------------------------
# Game config — tweak freely
# ---------------------------------------------------------------------------

REELS = 6
MIN_ROWS, MAX_ROWS = 4, 7
BET = 1.0
STARTING_BALANCE = 1000.0

# (key, weight, payouts {3:mult, 4:mult, 5:mult, 6:mult})  multiplier of bet
# Tuned via simulate_rtp.py to hit ~95% RTP.
SYMBOLS = [
    ("low_a", 22, {3: 0.0009, 4: 0.0030, 5: 0.0080, 6: 0.022}),
    ("low_b", 20, {3: 0.0011, 4: 0.0040, 5: 0.0100, 6: 0.029}),
    ("low_c", 18, {3: 0.0016, 4: 0.0050, 5: 0.0125, 6: 0.040}),
    ("low_d", 16, {3: 0.0023, 4: 0.0062, 5: 0.0155, 6: 0.049}),
    ("high_e", 11, {3: 0.0040, 4: 0.0093, 5: 0.0245, 6: 0.078}),
    ("high_f", 8,  {3: 0.0062, 4: 0.0155, 5: 0.0445, 6: 0.122}),
    ("high_g", 5,  {3: 0.0100, 4: 0.0300, 5: 0.0890, 6: 0.245}),
    ("high_h", 3,  {3: 0.0245, 4: 0.0850, 5: 0.2550, 6: 0.846}),
]
WILD = "wild"
WILD_WEIGHT = 3            # substitutes for paying symbols (not scatter)
SCATTER = "scatter"
SCATTER_WEIGHT = 2          # triggers free spins

# Free spins
FS_TRIGGER_AWARDS = {3: 10, 4: 15, 5: 20, 6: 25}  # scatters_count -> spins
FS_RETRIGGER_AWARDS = {3: 5, 4: 10, 5: 15, 6: 20}
FS_START_MULT = 1
FS_MULT_INCREMENT_ON_WIN = 1   # +1 multiplier for each winning free spin

# ---------------------------------------------------------------------------
# Symbol display config — colors used as PNG fallback
# ---------------------------------------------------------------------------

SYMBOL_DISPLAY = {
    "low_a":   ("A", (220, 220, 100)),
    "low_b":   ("K", (240, 150, 80)),
    "low_c":   ("Q", (200, 100, 200)),
    "low_d":   ("J", (100, 200, 220)),
    "high_e":  ("🐺", (180, 180, 200)),
    "high_f":  ("🦅", (200, 130, 60)),
    "high_g":  ("🐻", (140, 90, 50)),
    "high_h":  ("🦁", (240, 200, 80)),
    "wild":    ("W", (255, 80, 200)),
    "scatter": ("★", (255, 220, 80)),
}

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1280, 800
REEL_AREA = pygame.Rect(60, 100, 1160, 560)
CELL = 80                  # cell size in px
CELL_PAD = 6

BG = (18, 22, 32)
PANEL = (32, 38, 56)
PANEL_HI = (52, 62, 92)
GOLD = (255, 210, 80)
WHITE = (240, 240, 245)
DIM = (120, 130, 150)
GREEN = (90, 220, 130)
RED = (230, 90, 90)


# ---------------------------------------------------------------------------
# Reel logic
# ---------------------------------------------------------------------------

def build_pool() -> list[str]:
    pool: list[str] = []
    for key, w, _ in SYMBOLS:
        pool += [key] * w
    pool += [WILD] * WILD_WEIGHT
    pool += [SCATTER] * SCATTER_WEIGHT
    return pool


POOL = build_pool()


def spin_reels(rng: random.Random) -> list[list[str]]:
    """Return list of 6 reels. Each reel is a list of 2-7 symbols (top→bottom)."""
    grid = []
    for _ in range(REELS):
        rows = rng.randint(MIN_ROWS, MAX_ROWS)
        grid.append([rng.choice(POOL) for _ in range(rows)])
    return grid


# ---------------------------------------------------------------------------
# Win evaluation — left-to-right "ways"
# ---------------------------------------------------------------------------

@dataclass
class Win:
    symbol: str
    matches: int            # number of consecutive reels (3..6)
    ways: int               # multiplicity
    multiplier: float       # paytable multiplier
    pay: float              # multiplier * ways * bet


def evaluate_ways(grid: list[list[str]], bet: float) -> tuple[list[Win], float]:
    wins: list[Win] = []
    total = 0.0
    for sym, _, table in SYMBOLS:
        # count occurrences (sym or wild) per reel, left to right
        counts = []
        for reel in grid:
            c = sum(1 for s in reel if s == sym or s == WILD)
            if c == 0:
                break
            counts.append(c)
        k = len(counts)
        if k < 3:
            continue
        # cap k to highest tier in paytable
        max_tier = max(table)
        k = min(k, max_tier)
        ways = 1
        for c in counts[:k]:
            ways *= c
        mult = table[k]
        pay = mult * ways * bet
        wins.append(Win(sym, k, ways, mult, pay))
        total += pay
    return wins, total


def count_scatters(grid: list[list[str]]) -> int:
    return sum(1 for reel in grid for s in reel if s == SCATTER)


# ---------------------------------------------------------------------------
# Asset loading
# ---------------------------------------------------------------------------

class Assets:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.icons: dict[str, pygame.Surface] = {}
        # Try SysFont (works on desktop); fallback to default font (works in browser)
        def _font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                if f is not None:
                    return f
            except Exception:
                pass
            return pygame.font.Font(None, size)
        self.font_lg = _font("segoeui", 36, bold=True)
        self.font_md = _font("segoeui", 26, bold=True)
        self.font_sm = _font("segoeui", 18)
        self.font_sym = _font("segoeuiemoji", 36, bold=True)

    def load_icons(self):
        icons_dir = os.path.join(self.base_dir, "icons")
        os.makedirs(icons_dir, exist_ok=True)
        size = CELL - CELL_PAD * 2
        for key in list(SYMBOL_DISPLAY):
            path = os.path.join(icons_dir, f"{key}.png")
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (size, size))
                    self.icons[key] = img
                    continue
                except pygame.error:
                    pass
            # fallback: colored circle with letter/glyph
            self.icons[key] = self._make_fallback_icon(key, size)

    def _make_fallback_icon(self, key: str, size: int) -> pygame.Surface:
        glyph, color = SYMBOL_DISPLAY[key]
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        # rounded square background
        bg = pygame.Rect(0, 0, size, size)
        pygame.draw.rect(surf, color, bg, border_radius=12)
        pygame.draw.rect(surf, (0, 0, 0, 80), bg, width=2, border_radius=12)
        # glyph
        text = self.font_sym.render(glyph, True, (30, 30, 40))
        rect = text.get_rect(center=(size // 2, size // 2))
        surf.blit(text, rect)
        return surf


# ---------------------------------------------------------------------------
# Visual game
# ---------------------------------------------------------------------------

class SlotGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Megaways Slot")
        self.clock = pygame.time.Clock()
        self.assets = Assets(os.path.dirname(os.path.abspath(__file__)))
        self.assets.load_icons()
        self.rng = random.Random()

        self.balance = STARTING_BALANCE
        self.last_grid: list[list[str]] = [[] for _ in range(REELS)]
        self.last_wins: list[Win] = []
        self.last_pay = 0.0
        self.message = "Press SPACE to spin"
        self.spin_anim: Optional[SpinAnimation] = None

        # free spins state
        self.fs_remaining = 0
        self.fs_multiplier = FS_START_MULT
        self.fs_total_won = 0.0
        self.in_free_spins = False

        self.spins = 0
        self.biggest_win = 0.0

    # ----- input -----
    async def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.try_spin()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.try_spin()
            self.update(dt)
            self.draw()
            pygame.display.flip()
            await asyncio.sleep(0)
        pygame.quit()

    # ----- spin flow -----
    def try_spin(self):
        if self.spin_anim is not None:
            return
        if self.in_free_spins:
            self.do_spin(free=True)
        else:
            if self.balance < BET:
                self.message = "Out of balance"
                return
            self.balance -= BET
            self.do_spin(free=False)

    def do_spin(self, free: bool):
        self.spins += 1
        grid = spin_reels(self.rng)
        self.spin_anim = SpinAnimation(grid, self.assets)
        self._pending_free = free

    def resolve_spin(self, grid: list[list[str]]):
        wins, pay = evaluate_ways(grid, BET)
        scatters = count_scatters(grid)

        free = self._pending_free
        if free:
            pay *= self.fs_multiplier
            self.fs_total_won += pay

        self.balance += pay
        self.last_grid = grid
        self.last_wins = wins
        self.last_pay = pay
        if pay > self.biggest_win:
            self.biggest_win = pay

        # free spin trigger / retrigger
        if scatters >= 3:
            table = FS_RETRIGGER_AWARDS if self.in_free_spins else FS_TRIGGER_AWARDS
            tier = max(t for t in table if t <= scatters)
            awarded = table[tier]
            if not self.in_free_spins:
                self.in_free_spins = True
                self.fs_multiplier = FS_START_MULT
                self.fs_total_won = 0.0
                self.fs_remaining = awarded
                self.message = f"FREE SPINS! +{awarded} spins"
            else:
                self.fs_remaining += awarded
                self.message = f"Retrigger! +{awarded} free spins"
        elif free:
            self.fs_remaining -= 1
            if pay > 0:
                self.fs_multiplier += FS_MULT_INCREMENT_ON_WIN
            if self.fs_remaining <= 0:
                self.in_free_spins = False
                self.message = (f"Free spins ended. Total won: "
                                f"${self.fs_total_won:,.2f}")
            else:
                self.message = (f"Free spin won ${pay:,.2f}  "
                                f"(x{self.fs_multiplier} mult, "
                                f"{self.fs_remaining} left)")
        else:
            if pay > 0:
                self.message = f"WIN  ${pay:,.2f}"
            else:
                self.message = "No win"

    # ----- update / draw -----
    def update(self, dt: float):
        if self.spin_anim is not None:
            done = self.spin_anim.update(dt)
            if done:
                grid = self.spin_anim.grid
                self.spin_anim = None
                self.resolve_spin(grid)

    def draw(self):
        self.screen.fill(BG)
        self.draw_header()
        self.draw_reels()
        self.draw_footer()

    def draw_header(self):
        title = self.assets.font_lg.render("MEGAWAYS  6×(2-7)", True, GOLD)
        self.screen.blit(title, (60, 30))

        bal = f"Balance: ${self.balance:,.2f}"
        bet = f"Bet: ${BET:.2f}"
        ways = product([len(r) if r else MAX_ROWS for r in self.last_grid])
        ways_t = f"Ways: {ways:,}"
        for i, t in enumerate([bal, bet, ways_t]):
            surf = self.assets.font_md.render(t, True, WHITE)
            self.screen.blit(surf, (520 + i * 220, 42))

        if self.in_free_spins:
            fs = (f"FREE SPINS  ×{self.fs_multiplier}  "
                  f"({self.fs_remaining} left)  total ${self.fs_total_won:,.2f}")
            surf = self.assets.font_md.render(fs, True, GOLD)
            self.screen.blit(surf, (60, 70))

    def draw_reels(self):
        # If animating, draw the animation; else draw last_grid
        if self.spin_anim is not None:
            grid = self.spin_anim.current_display()
            highlight_cells: set[tuple[int, int]] = set()
        else:
            grid = self.last_grid
            highlight_cells = self._winning_cells(grid)

        # draw reel backgrounds first
        reel_w = REEL_AREA.width // REELS
        for r in range(REELS):
            x = REEL_AREA.x + r * reel_w
            rect = pygame.Rect(x + 6, REEL_AREA.y, reel_w - 12, REEL_AREA.height)
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)

        # draw symbols centered vertically per reel
        for r, reel in enumerate(grid):
            if not reel:
                continue
            x = REEL_AREA.x + r * reel_w + reel_w // 2
            total_h = len(reel) * CELL
            y0 = REEL_AREA.y + (REEL_AREA.height - total_h) // 2
            for i, sym in enumerate(reel):
                cx = x
                cy = y0 + i * CELL + CELL // 2
                self._draw_symbol(sym, cx, cy, highlight=(r, i) in highlight_cells)

    def _draw_symbol(self, sym: str, cx: int, cy: int, highlight: bool):
        size = CELL - CELL_PAD * 2
        if highlight:
            glow = pygame.Rect(0, 0, size + 12, size + 12)
            glow.center = (cx, cy)
            pygame.draw.rect(self.screen, GOLD, glow, border_radius=14)
        icon = self.assets.icons.get(sym)
        if icon is not None:
            rect = icon.get_rect(center=(cx, cy))
            self.screen.blit(icon, rect)

    def _winning_cells(self, grid: list[list[str]]) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for w in self.last_wins:
            for r in range(w.matches):
                if r >= len(grid):
                    continue
                for i, s in enumerate(grid[r]):
                    if s == w.symbol or s == WILD:
                        cells.add((r, i))
        # also light up scatters if 3+
        if count_scatters(grid) >= 3:
            for r, reel in enumerate(grid):
                for i, s in enumerate(reel):
                    if s == SCATTER:
                        cells.add((r, i))
        return cells

    def draw_footer(self):
        msg_color = GOLD if self.last_pay > 0 or self.in_free_spins else WHITE
        msg = self.assets.font_md.render(self.message, True, msg_color)
        self.screen.blit(msg, (60, REEL_AREA.bottom + 20))

        # win breakdown
        if self.last_wins and self.spin_anim is None:
            lines = []
            for w in sorted(self.last_wins, key=lambda x: -x.pay)[:5]:
                lines.append(
                    f"{w.symbol:7s} × {w.matches}  ways={w.ways:5d}  "
                    f"x{w.multiplier:.2f}  =  ${w.pay:,.2f}"
                )
            for i, line in enumerate(lines):
                surf = self.assets.font_sm.render(line, True, DIM)
                self.screen.blit(surf, (60, REEL_AREA.bottom + 60 + i * 22))

        hint = "SPACE = spin    Q/Esc = quit"
        surf = self.assets.font_sm.render(hint, True, DIM)
        self.screen.blit(surf, (WIDTH - surf.get_width() - 60,
                                HEIGHT - surf.get_height() - 20))


# ---------------------------------------------------------------------------
# Spin animation
# ---------------------------------------------------------------------------

class SpinAnimation:
    """Each reel scrolls fake symbols then settles to its final list."""

    REEL_DURATIONS = [0.45, 0.60, 0.75, 0.90, 1.05, 1.20]

    def __init__(self, final_grid: list[list[str]], assets: Assets):
        self.grid = final_grid
        self.assets = assets
        self.elapsed = 0.0
        self.fake_pool = [k for k, _, _ in SYMBOLS] + [WILD, SCATTER]

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        return self.elapsed >= max(self.REEL_DURATIONS) + 0.05

    def current_display(self) -> list[list[str]]:
        out = []
        for r, final_reel in enumerate(self.grid):
            if self.elapsed >= self.REEL_DURATIONS[r]:
                out.append(final_reel)
            else:
                rows = len(final_reel)
                # rapidly cycling fake symbols
                fake = [random.choice(self.fake_pool) for _ in range(rows)]
                out.append(fake)
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def product(xs):
    p = 1
    for x in xs:
        p *= x if x else 1
    return p


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

async def main():
    await SlotGame().run()


if __name__ == "__main__":
    asyncio.run(main())
