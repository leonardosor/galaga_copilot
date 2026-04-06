#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip
pip install pygbag
mkdir -p game && cp galaga_copilot.py game/main.py
python -m pygbag --build game/
echo "Build complete: game/build/web/ contains the web build"