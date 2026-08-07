import { existsSync, renameSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SIDECAR_NAME = "editor-carrosseis-sidecar";
const desktopDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = resolve(desktopDir, "..");
const binariesDir = join(desktopDir, "src-tauri", "binaries");

function hostTriple() {
  const details = execFileSync("rustc", ["-vV"], { encoding: "utf8" });
  const match = details.match(/^host:\s*(.+)$/m);
  if (!match) throw new Error("Não foi possível descobrir o target triple do Rust.");
  return match[1].trim();
}

function pythonExecutable() {
  const venv = process.platform === "win32"
    ? join(projectRoot, ".venv", "Scripts", "python.exe")
    : join(projectRoot, ".venv", "bin", "python");
  return existsSync(venv) ? venv : (process.env.PYTHON ?? "python3");
}

const triple = hostTriple();
const extension = process.platform === "win32" ? ".exe" : "";
const output = join(binariesDir, `${SIDECAR_NAME}${extension}`);
const destination = join(binariesDir, `${SIDECAR_NAME}-${triple}${extension}`);

execFileSync(
  pythonExecutable(),
  [join(projectRoot, "scripts", "build_sidecar.py"), "--target-dir", binariesDir],
  { cwd: projectRoot, stdio: "inherit" },
);

if (!existsSync(output)) throw new Error(`Sidecar não foi produzido: ${output}`);
rmSync(destination, { force: true });
renameSync(output, destination);
