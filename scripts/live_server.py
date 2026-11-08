"""Compatibility entry point; live HTTP routes now live in backend/app/."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    python = ROOT / "backend/.venv/bin/python"
    os.execv(
        str(python),
        [
            str(python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            str(ROOT / "backend"),
            "--host",
            "127.0.0.1",
            "--port",
            "8100",
        ],
    )
else:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.services import pipeline

    sys.modules[__name__] = pipeline
