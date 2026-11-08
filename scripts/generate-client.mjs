import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let result = spawnSync(
	path.join(root, "backend/.venv/bin/python"),
	[path.join(root, "scripts/export_openapi.py")],
	{ cwd: root, stdio: "inherit" },
);
if (result.status !== 0) process.exit(result.status ?? 1);
result = spawnSync(
	process.execPath,
	[path.join(root, "node_modules/@hey-api/openapi-ts/bin/run.js")],
	{ cwd: path.join(root, "frontend"), stdio: "inherit" },
);
process.exit(result.status ?? 1);
