use std::{env, fs, path::PathBuf, process::Command};

const SIDECAR_NAME: &str = "editor-carrosseis-sidecar";

fn main() {
    println!("cargo:rerun-if-changed=../../scripts/build_sidecar.py");
    println!("cargo:rerun-if-changed=../../scripts/desktop_sidecar.py");
    println!("cargo:rerun-if-changed=../../templates");
    println!("cargo:rerun-if-changed=../../assets");
    ensure_sidecar();
    tauri_build::build();
}

fn ensure_sidecar() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("manifesto ausente"));
    let project_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .expect("raiz do projeto ausente");
    let target = env::var("TARGET").expect("target Rust ausente");
    let extension = if target.contains("windows") {
        ".exe"
    } else {
        ""
    };
    let binaries_dir = manifest_dir.join("binaries");
    let staged = binaries_dir.join(format!("{SIDECAR_NAME}-{target}{extension}"));
    if staged.exists() {
        return;
    }

    if target.contains("windows") != cfg!(windows) {
        panic!("o sidecar PyInstaller precisa ser construído nativamente para {target}");
    }
    let venv_python = if cfg!(windows) {
        project_root.join(".venv/Scripts/python.exe")
    } else {
        project_root.join(".venv/bin/python")
    };
    let python = env::var_os("CARROSSEL_PYTHON")
        .map(PathBuf::from)
        .filter(|path| path.exists())
        .or_else(|| venv_python.exists().then_some(venv_python))
        .unwrap_or_else(|| PathBuf::from(if cfg!(windows) { "python" } else { "python3" }));

    fs::create_dir_all(&binaries_dir).expect("não foi possível criar binaries");
    let status = Command::new(python)
        .arg(project_root.join("scripts/build_sidecar.py"))
        .arg("--target-dir")
        .arg(&binaries_dir)
        .current_dir(project_root)
        .status()
        .expect("não foi possível executar o builder do sidecar");
    assert!(status.success(), "o builder do sidecar falhou");

    let raw = binaries_dir.join(format!("{SIDECAR_NAME}{extension}"));
    fs::rename(&raw, &staged).expect("não foi possível estagiar o sidecar para o target Rust");
}
