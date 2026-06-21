"""Pytest configuration."""

# Human: Ensure pytest can import `app.*` from the backend package root when tests run from any cwd.
# Agent: READS conftest path; WRITES sys.path with backend ROOT; failure: import errors if path wrong.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
