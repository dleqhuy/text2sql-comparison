"""Export the app schema without starting services or reading credentials to stdout."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import app

(ROOT / "frontend/openapi.json").write_text(json.dumps(app.openapi(), indent=2))
print("Exported frontend/openapi.json")
