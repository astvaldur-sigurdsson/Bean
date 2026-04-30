"""
Monte Carlo RTP simulator for slot_megaways.

Run: python simulate_rtp.py [num_spins]
"""

import random
import sys
import time

import slot_megaways as sm


def simulate(n_spins: int, seed: int = 0) -> dict:
    rng = random.Random(seed)
    bet = sm.BET
    total_bet = 0.0
    total_pay = 0.0
    hits = 0
    triggers = 0
    fs_total_paid = 0.0
    fs_total_count = 0
    big_wins = 0  # >= 50x bet

    in_fs = False
    fs_left = 0
    fs_mult = sm.FS_START_MULT

    spins_done = 0
    while spins_done < n_spins:
        if not in_fs:
            total_bet += bet
        grid = sm.spin_reels(rng)
        _, raw_pay = sm.evaluate_ways(grid, bet)
        scatters = sm.count_scatters(grid)

        if in_fs:
            pay = raw_pay * fs_mult
            fs_total_paid += pay
            fs_left -= 1
            if raw_pay > 0:
                fs_mult += sm.FS_MULT_INCREMENT_ON_WIN
        else:
            pay = raw_pay

        total_pay += pay
        if pay > 0:
            hits += 1
        if pay >= bet * 50:
            big_wins += 1

        if scatters >= 3:
            table = sm.FS_RETRIGGER_AWARDS if in_fs else sm.FS_TRIGGER_AWARDS
            tier = max(t for t in table if t <= scatters)
            awarded = table[tier]
            if not in_fs:
                in_fs = True
                fs_mult = sm.FS_START_MULT
                fs_left = awarded
                triggers += 1
                fs_total_count += awarded
            else:
                fs_left += awarded
                fs_total_count += awarded
        elif in_fs and fs_left <= 0:
            in_fs = False

        spins_done += 1

    return {
        "spins": spins_done,
        "total_bet": total_bet,
        "total_pay": total_pay,
        "rtp": total_pay / total_bet * 100 if total_bet else 0,
        "hit_rate": hits / spins_done * 100,
        "fs_trigger_rate": (1 / (spins_done / triggers)) * 100 if triggers else 0,
        "fs_one_in": spins_done / triggers if triggers else 0,
        "fs_avg_payout_per_trigger": fs_total_paid / triggers if triggers else 0,
        "fs_avg_spins_per_trigger": fs_total_count / triggers if triggers else 0,
        "big_win_rate_one_in": spins_done / big_wins if big_wins else 0,
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000
    print(f"Simulating {n:,} spins...")
    t0 = time.time()
    r = simulate(n)
    dt = time.time() - t0
    print(f"  ({dt:.1f}s, {n/dt:,.0f} spins/sec)\n")
    print(f"  RTP                       : {r['rtp']:.2f}%")
    print(f"  Hit rate                  : {r['hit_rate']:.2f}%")
    print(f"  Big-win rate (>=50x bet)  : 1 in {r['big_win_rate_one_in']:,.0f}")
    print(f"  Free-spin trigger rate    : 1 in {r['fs_one_in']:,.0f}"
          f"  ({r['fs_trigger_rate']:.3f}%)")
    print(f"  Avg free spins per trigger: {r['fs_avg_spins_per_trigger']:.1f}")
    print(f"  Avg payout per trigger    : ${r['fs_avg_payout_per_trigger']:,.2f}")
