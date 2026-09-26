import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const rootDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = join(rootDir, "backend");
const frontendDir = join(rootDir, "frontend");

const virtualenvPython =
  process.platform === "win32"
    ? join(backendDir, ".venv", "Scripts", "python.exe")
    : join(backendDir, ".venv", "bin", "python");
const python = existsSync(virtualenvPython)
  ? virtualenvPython
  : process.platform === "win32"
    ? "python"
    : "python3";
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const spawnOptions = (cwd) => ({
  cwd,
  stdio: "inherit",
  // Give each service its own process group so reloaders and other child
  // processes can be stopped together with their parent.
  detached: process.platform !== "win32",
});

const services = [
  spawn(
    python,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--reload",
      "--host",
      "0.0.0.0",
      "--port",
      "8000",
    ],
    spawnOptions(backendDir),
  ),
  spawn(npm, ["run", "dev"], spawnOptions(frontendDir)),
];

let shuttingDown = false;
let exitCode = 0;
const runningServices = new Set(services);

function signalService(service, signal) {
  try {
    if (process.platform === "win32") {
      service.kill(signal);
    } else if (service.pid) {
      process.kill(-service.pid, signal);
    }
  } catch (error) {
    if (error.code !== "ESRCH") throw error;
  }
}

function stopServices(code) {
  if (shuttingDown) return;

  shuttingDown = true;
  exitCode = code;
  for (const service of services) {
    signalService(service, "SIGTERM");
  }

  setTimeout(() => {
    for (const service of services) {
      signalService(service, "SIGKILL");
    }
  }, 5_000).unref();
}

for (const service of services) {
  service.on("error", (error) => {
    console.error(`Unable to start a development service: ${error.message}`);
    stopServices(1);
  });

  service.on("exit", (code, signal) => {
    runningServices.delete(service);

    if (!shuttingDown) {
      const reason = signal ? `signal ${signal}` : `exit code ${code ?? 1}`;
      console.error(`A development service stopped (${reason}).`);
      stopServices(code ?? 1);
    }

    if (runningServices.size === 0) {
      process.exit(exitCode);
    }
  });
}

process.once("SIGINT", () => stopServices(130));
process.once("SIGTERM", () => stopServices(143));
