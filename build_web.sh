#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip
pip install pygbag
python -m pygbag --build --output out ./game
echo "Build complete: out/ contains the web build"