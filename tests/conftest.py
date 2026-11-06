"""Pytest configuration for the patched SmartIR component tests."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
