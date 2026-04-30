# Bean

A 6-reel Megaways-style slot machine in Python (pygame).

- 6 reels × 4–7 rows per spin (up to 117,649 ways)
- Left-to-right "ways" wins, wild substitutions, scatter free-spin trigger
- Free spins with climbing multiplier (Bonanza-style)
- ~95.8% RTP (verified via 2M-spin Monte Carlo)
- Custom PNG icons in `icons/` (auto-fallback to colored tiles if missing)

## Run

```powershell
pip install pygame pillow
python slot_megaways.py
```

Press **SPACE** to spin, **Q/Esc** to quit.

## RTP simulation

```powershell
python simulate_rtp.py 1000000
```

## Tweak

Edit the `SYMBOLS`, `WILD_WEIGHT`, `SCATTER_WEIGHT`, and `FS_*` constants near the top of `slot_megaways.py`. Re-run `simulate_rtp.py` to confirm RTP.
