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
- **Arrow Keys**: Move ship
- **Spacebar**: Shoot
- **R**: Restart (after game over)  
- **Q**: Quit (after game over)

## Features
- 5 weapon types: Normal, Double, Spread, Bomb, Laser
- Power-up tokens with limited duration
- Particle effects and explosion blasts  
- Enemy AI with dive-bomber patterns
- Progressive difficulty and scoring

## File Structure
- `galaga_copilot.py` - Desktop version (full features)
- `game/main.py` - Web-compatible version  
- `game/build/web/` - Deployed web build
- `.github/workflows/deploy.yml` - Auto-deployment to GitHub Pages
