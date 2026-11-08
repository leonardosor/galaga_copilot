"""Desktop launcher — the game lives in game/main.py (shared with the web build)."""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "game", "main.py"),
               run_name="__main__")
