"""
The functions under test are pure and need no Flask app context, but importing
hlasys2_app.util pulls in hlasys2_app.config, which must exist.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
