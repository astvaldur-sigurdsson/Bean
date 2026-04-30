"""
5x5 Slot Machine — scatter-pays style.
Pure stdlib, no dependencies. Run: python slot_machine.py
"""

import os
import random
import sys
import time
from collections import Counter

# ---------------------------------------------------------------------------
# Config — tweak freely
# ---------------------------------------------------------------------------

ROWS, COLS = 5, 5
BET = 10
STARTING_BALANCE = 500

# (symbol, weight, payout_table)
# payout_table is keyed by count of that symbol on the grid (>= 3 pays)
SYMBOLS = [
    # symbol, weight, {count: multiplier_of_bet}
    ("🍒", 30, {3: 1,   4: 2,    5: 4,    6: 8,    7: 15,  8: 30}),
    ("🍋", 28, {3: 1,   4: 3,    5: 5,    6: 10,   7: 20,  8: 40}),
    ("🍊", 24, {3: 2,   4: 4,    5: 8,    6: 15,   7: 30,  8: 60}),
    ("🍇", 18, {3: 3,   4: 6,    5: 12,   6: 25,   7: 50,  8: 100}),
    ("🔔", 12, {3: 5,   4: 10,   5: 20,   6: 40,   7: 80,  8: 160}),
    ("⭐", 8,  {3: 10,  4: 25,   5: 50,   6: 100,  7: 200, 8: 400}),
    ("💎", 4,  {3: 25,  4: 75,   5: 150,  6: 300,  7: 600, 8: 1500}),
    ("7️⃣", 2,  {3: 50,  4: 150,  5: 500,  6: 1000, 7: 2500, 8: 5000}),
]

WILD = "🃏"
WILD_WEIGHT = 3  # wild substitutes for any symbol

# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------

if os.name == "nt":
    os.system("")  # enable ANSI on Windows

C_RESET = "\033[0m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_RED = "\033[91m"

# ---------------------------------------------------------------------------
# Reels
# ---------------------------------------------------------------------------

def build_reel():
    reel = []
    for sym, weight, _ in SYMBOLS:
        reel.extend([sym] * weight)
    reel.extend([WILD] * WILD_WEIGHT)
    random.shuffle(reel)
    return reel


def spin_grid():
    reel = build_reel()
    grid = [[random.choice(reel) for _ in range(COLS)] for _ in range(ROWS)]
    return grid


# ---------------------------------------------------------------------------
# Payouts
# ---------------------------------------------------------------------------

def evaluate(grid, bet):
    flat = [c for row in grid for c in row]
    counts = Counter(flat)
    wilds = counts.get(WILD, 0)

    wins = []  # (symbol, count_used, payout)
    total = 0
    for sym, _, table in SYMBOLS:
        n = counts.get(sym, 0) + wilds  # wilds boost every symbol
        if n >= 3:
            # find biggest tier <= n
            tier = max((k for k in table if k <= n), default=None)
            if tier is not None:
                payout = table[tier] * bet
                wins.append((sym, n, payout))
                total += payout
    return wins, total


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(grid, highlight=None, color=C_RESET):
    highlight = highlight or set()
    border = "┌" + "─────┬" * (COLS - 1) + "─────┐"
    sep    = "├" + "─────┼" * (COLS - 1) + "─────┤"
    bottom = "└" + "─────┴" * (COLS - 1) + "─────┘"

    print(border)
    for r, row in enumerate(grid):
        cells = []
        for c, sym in enumerate(row):
            cell = f" {sym}  "  # emoji rendering varies; pad for width
            if (r, c) in highlight:
                cells.append(f"{color}{C_BOLD}{cell}{C_RESET}")
            else:
                cells.append(cell)
        print("│" + "│".join(cells) + "│")
        if r < ROWS - 1:
            print(sep)
    print(bottom)


def animate_spin(final_grid, frames=8, delay=0.06):
    reel = build_reel()
    for i in range(frames):
        # progressively lock columns left-to-right
        locked_cols = int(COLS * (i + 1) / frames)
        grid = []
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                if c < locked_cols:
                    row.append(final_grid[r][c])
                else:
                    row.append(random.choice(reel))
            grid.append(row)
        clear_screen()
        print(f"{C_CYAN}{C_BOLD}  ★  5x5 SLOTS  ★{C_RESET}\n")
        render(grid)
        time.sleep(delay)


def clear_screen():
    print("\033[H\033[J", end="")


def print_paytable():
    print(f"\n{C_BOLD}Paytable{C_RESET} (multipliers × bet):")
    header = f"  {'Symbol':<8}" + "".join(f"{n:>6}x" for n in (3, 4, 5, 6, 7, 8))
    print(C_DIM + header + C_RESET)
    for sym, _, table in SYMBOLS:
        row = f"  {sym:<8}"
        for n in (3, 4, 5, 6, 7, 8):
            row += f"{table.get(n, '-'):>6} "
        print(row)
    print(f"  {WILD}  Wild — substitutes for any symbol\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    balance = STARTING_BALANCE
    spins = 0
    biggest_win = 0

    clear_screen()
    print(f"{C_CYAN}{C_BOLD}  ★  5x5 SLOTS  ★{C_RESET}")
    print(f"  Starting balance: ${balance}   Bet per spin: ${BET}")
    print_paytable()

    while True:
        if balance < BET:
            print(f"{C_RED}Out of money. You lasted {spins} spins. "
                  f"Biggest win: ${biggest_win}{C_RESET}")
            return

        prompt = (f"{C_DIM}Balance: ${balance}  |  Spins: {spins}  |  "
                  f"[Enter]=spin  q=quit  p=paytable{C_RESET}\n> ")
        try:
            cmd = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if cmd in ("q", "quit", "exit"):
            print(f"Walked away with ${balance}. Biggest win: ${biggest_win}.")
            return
        if cmd in ("p", "paytable"):
            print_paytable()
            continue

        balance -= BET
        spins += 1
        grid = spin_grid()
        animate_spin(grid)

        wins, payout = evaluate(grid, BET)

        # Highlight winning symbols on the final grid
        winning_syms = {sym for sym, _, _ in wins}
        highlight = set()
        if winning_syms:
            for r in range(ROWS):
                for c in range(COLS):
                    s = grid[r][c]
                    if s in winning_syms or (s == WILD and wins):
                        highlight.add((r, c))

        clear_screen()
        print(f"{C_CYAN}{C_BOLD}  ★  5x5 SLOTS  ★{C_RESET}\n")
        render(grid, highlight=highlight, color=C_YELLOW)

        if payout:
            balance += payout
            biggest_win = max(biggest_win, payout)
            print(f"\n{C_GREEN}{C_BOLD}WIN! +${payout}{C_RESET}")
            for sym, n, p in sorted(wins, key=lambda w: -w[2]):
                print(f"  {sym} × {n}  →  ${p}")
            if payout >= BET * 50:
                print(f"{C_MAGENTA}{C_BOLD}  ✦ BIG WIN ✦{C_RESET}")
        else:
            print(f"\n{C_DIM}No win. Try again.{C_RESET}")
        print()


if __name__ == "__main__":
    main()
