"""Fill missing local app settings without replacing existing LLM credentials."""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / ".env"
if not path.exists():
    path.write_text((ROOT / ".env.example").read_text())
lines = path.read_text().splitlines()
values = {
    line.split("=", 1)[0]: line.split("=", 1)[1]
    for line in lines
    if "=" in line and not line.startswith("#")
}
new = {
    "PROJECT_NAME": "SQL / Lab",
    "FASTAPI_ENV": "development",
    "FRONTEND_HOST": "http://127.0.0.1:5173",
    "DATABASE_URL": "postgresql://postgres:"
    + secrets.token_urlsafe(24)
    + "@127.0.0.1:55432/app",
}
updated = []
for key, value in new.items():
    if values.get(key):
        continue
    lines = [line for line in lines if not line.startswith(key + "=")]
    lines.append(key + "=" + value)
    updated.append(key)
path.write_text("\n".join(lines) + "\n")
os.chmod(path, 0o600)
print(
    "Updated local settings: "
    + (", ".join(updated) or "none; existing values preserved")
)
