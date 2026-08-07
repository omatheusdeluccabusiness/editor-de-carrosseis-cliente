import { existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktopDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = resolve(desktopDir, "..");
const venvPython = process.platform === "win32"
  ? join(projectRoot, ".venv", "Scripts", "python.exe")
  : join(projectRoot, ".venv", "bin", "python");
const python = existsSync(venvPython) ? venvPython : (process.env.PYTHON ?? "python");

execFileSync(
  python,
  ["-m", "unittest", "tests.test_desktop_sidecar_integration", "-v"],
  { cwd: projectRoot, stdio: "inherit" },
);
