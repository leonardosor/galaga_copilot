# Galaga Copilot — MegaTech Robot Wars

A pygame-based arcade shooter with detailed robot graphics and weapon upgrades.

## Play Online

🎮 **[Play in Browser](https://leonardosor.github.io/galaga_copilot/)**

## Run Locally

### Desktop Version
```bash
python galaga_copilot.py
```

### Web Version (Local Testing)
```bash
cd game/build/web
python -m http.server 8000
# Open http://127.0.0.1:8000/
```

## Controls
- **Arrows / WASD**: Move (full 2D in lower half of screen)
- **Hold Space / Z**: Fire (autofire)
- **Mouse / touch drag**: Move + autofire
- **P / Esc**: Pause
- **M**: Mute
- **R / Space** on game over: Retry

## Features
- 5 weapons (Blaster, Double, Spread, Bomb, Laser) — grab the same token again to stack power to LV3
- Combo multiplier up to x8 for chaining kills
- 4 enemy types (grunts, dive-bombers, sine-weavers, armored tanks) plus squad formations
- Dreadnought boss every 5 levels with rotating bullet patterns and an enrage phase
- Screen shake, hit-stop, hit flashes, additive glow, shockwaves, warp-speed starfield
- Procedurally synthesized sound effects (no asset files)
- Persistent high score (localStorage on web, `~/.megatech_robot_wars_hiscore` on desktop)

## File Structure
- `game/main.py` — the game (single source for desktop and web)
- `galaga_copilot.py` — desktop launcher for `game/main.py`
- `game/build/web/` — deployed pygbag build
- `.github/workflows/deploy.yml` — auto-deployment to GitHub Pages

## Rebuilding the web bundle
```bash
PYTHONUTF8=1 python -m pygbag --build game
```

`game/build/web/index.html` is hand-patched so Space/arrow keys don't scroll the page
(`overflow: hidden` + a keydown `preventDefault` handler). If pygbag regenerates the
template, re-apply that patch or keep the committed `index.html`.
