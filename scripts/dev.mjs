import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import net from "node:net";
import EmbeddedPostgres from "embedded-postgres";
import { createServer } from "vite";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
process.loadEnvFile(path.join(root, ".env"));
const python = path.join(root, "backend/.venv/bin/python");
if (!existsSync(python))
	throw new Error("Install backend first: uv sync --project backend");
const env = { ...process.env, PYTHONUNBUFFERED: "1" };
let pg, vite, api;
let closing = false;
const children = new Set();
const waitExit = (child) =>
	new Promise((resolve) => {
		if (child.exitCode !== null || child.signalCode !== null) return resolve();
		child.once("exit", resolve);
	});
async function stop(code = 0) {
	if (closing) return;
	closing = true;
	try {
		for (const child of children) child.kill("SIGINT");
		await Promise.all(
			[...children].map(async (child) => {
				let timeout;
				await Promise.race([
					waitExit(child),
					new Promise((resolve) => {
						timeout = setTimeout(resolve, 12000);
					}),
				]);
				clearTimeout(timeout);
				if (child.exitCode === null && child.signalCode === null)
					child.kill("SIGKILL");
			}),
		);
		if (vite) await vite.close();
		if (pg) await pg.stop();
	} finally {
		process.exitCode = code;
	}
}
process.on("SIGINT", () => void stop());
process.on("SIGTERM", () => void stop());
function launch(args) {
	const child = spawn(python, args, {
		cwd: path.join(root, "backend"),
		env,
		stdio: "inherit",
		detached: true,
	});
	children.add(child);
	child.on("error", (error) => {
		console.error(error.message);
		void stop(1);
	});
	child.on("exit", () => children.delete(child));
	return child;
}
async function command(args) {
	const child = launch(args);
	await waitExit(child);
	if (child.exitCode !== 0)
		throw new Error(`Backend setup failed (${args[1]})`);
}
async function portOpen(host, port) {
	return new Promise((resolve) => {
		const socket = net.createConnection({ host, port });
		socket.setTimeout(1000);
		socket.on("connect", () => {
			socket.destroy();
			resolve(true);
		});
		const fail = () => {
			socket.destroy();
			resolve(false);
		};
		socket.on("error", fail);
		socket.on("timeout", fail);
	});
}
try {
	const url = new URL(process.env.DATABASE_URL);
	if (
		process.env.LOCAL_POSTGRES !== "0" &&
		["localhost", "127.0.0.1"].includes(url.hostname) &&
		!(await portOpen(url.hostname, Number(url.port || 5432)))
	) {
		const base = path.join(root, ".cache/postgres");
		mkdirSync(base, { recursive: true });
		pg = new EmbeddedPostgres({
			databaseDir: path.join(base, "data"),
			user: decodeURIComponent(url.username),
			password: decodeURIComponent(url.password),
			port: Number(url.port || 5432),
			persistent: true,
			createPostgresUser: false,
			autoRehydrateSymlinks: true,
			authMethod: "scram-sha-256",
			postgresFlags: ["-c", "listen_addresses=127.0.0.1", "-k", base],
			onLog: () => {},
			onError: (message) => console.error(String(message)),
		});
		if (!existsSync(path.join(base, "data/PG_VERSION"))) await pg.initialise();
		await pg.start();
		const name = url.pathname.slice(1);
		if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name))
			throw new Error("Invalid development database name");
		const client = pg.getPgClient("postgres", "127.0.0.1");
		await client.connect();
		try {
			const found = await client.query(
				"SELECT 1 FROM pg_database WHERE datname=$1",
				[name],
			);
			if (!found.rowCount) await pg.createDatabase(name);
		} finally {
			await client.end();
		}
		console.log(
			`PostgreSQL ready on 127.0.0.1:${url.port || 5432} (workspace data)`,
		);
	}
	await command(["-m", "alembic", "upgrade", "head"]);
	api = launch([
		"-m",
		"uvicorn",
		"app.main:app",
		"--host",
		"127.0.0.1",
		"--port",
		"8100",
		"--workers",
		"1",
	]);
	api.on("exit", (code) => {
		if (!closing) void stop(code ?? 1);
	});
	vite = await createServer({
		root: path.join(root, "frontend"),
		configFile: path.join(root, "frontend/vite.config.ts"),
	});
	await vite.listen();
	vite.printUrls();
	console.log(
		`SQL / Lab: http://127.0.0.1:5173 · API docs: http://127.0.0.1:8100/docs`,
	);
} catch (error) {
	console.error(error.message);
	await stop(1);
}
