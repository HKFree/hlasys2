"""
Shared test setup.

hlasys2_app/config.py is gitignored, so a clean checkout (and CI) has none, and
importing hlasys2_app fails without it. Seed it from config.example.py when it
is missing so the suite runs anywhere.
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_config = ROOT / "hlasys2_app" / "config.py"
if not _config.exists():
    shutil.copyfile(ROOT / "hlasys2_app" / "config.example.py", _config)
