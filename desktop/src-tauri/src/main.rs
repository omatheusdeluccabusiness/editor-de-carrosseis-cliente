use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{AppHandle, Manager, RunEvent, WebviewWindow, WindowEvent};

const SIDECAR_NAME: &str = "editor-carrosseis-sidecar";
const HEALTH_ADDRESS: &str = "127.0.0.1:8777";
const HEALTH_PATH: &str = "/api/health";
const HEALTH_TIMEOUT: Duration = Duration::from_secs(10);

struct SidecarState(Mutex<Option<Child>>);

fn sidecar_path() -> Result<PathBuf, String> {
    let filename = if cfg!(target_os = "windows") {
        format!("{SIDECAR_NAME}.exe")
    } else {
        SIDECAR_NAME.to_owned()
    };
    let executable = std::env::current_exe().map_err(|error| error.to_string())?;
    let executable_dir = executable
        .parent()
        .ok_or_else(|| "Não foi possível localizar o diretório do aplicativo.".to_owned())?;

    Ok(executable_dir.join(filename))
}

fn ensure_loopback_port_is_available() -> Result<(), String> {
    TcpListener::bind(HEALTH_ADDRESS).map_err(|_| {
        "A porta local 8777 já está em uso. Feche outro Editor de Carrosseis e tente novamente."
            .to_owned()
    })?;
    Ok(())
}

fn start_sidecar(app_data_dir: &Path) -> Result<Child, String> {
    ensure_loopback_port_is_available()?;
    std::fs::create_dir_all(app_data_dir).map_err(|error| error.to_string())?;

    Command::new(sidecar_path()?)
        .env("CARROSSEL_APP_DATA_DIR", app_data_dir)
        .spawn()
        .map_err(|error| format!("Não foi possível iniciar o servidor local: {error}"))
}

fn health_check() -> bool {
    let address: SocketAddr = match HEALTH_ADDRESS.parse() {
        Ok(address) => address,
        Err(_) => return false,
    };
    let mut stream = match TcpStream::connect_timeout(&address, Duration::from_millis(250)) {
        Ok(stream) => stream,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(250)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(250)));
    let request =
        format!("GET {HEALTH_PATH} HTTP/1.1\r\nHost: 127.0.0.1:8777\r\nConnection: close\r\n\r\n");
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }

    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok()
        && response.starts_with("HTTP/1.1 200")
        && response.contains("\"ok\": true")
        && response.contains("\"service\": \"editor-carrosseis\"")
}

fn wait_for_health() -> Result<(), String> {
    let deadline = Instant::now() + HEALTH_TIMEOUT;
    while Instant::now() < deadline {
        if health_check() {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err("O servidor local não respondeu em até 10 segundos.".to_owned())
}

fn stop_sidecar(app: &AppHandle) {
    let state = app.state::<SidecarState>();
    let mut child = state.0.lock().expect("estado do sidecar indisponível");
    if let Some(child) = child.as_mut() {
        if matches!(child.try_wait(), Ok(None)) {
            let _ = child.kill();
            let _ = child.wait();
        }
    }
    *child = None;
}

fn navigate_to_hub(window: WebviewWindow) -> Result<(), String> {
    let url = tauri::Url::parse("http://127.0.0.1:8777/").map_err(|error| error.to_string())?;
    window.navigate(url).map_err(|error| error.to_string())
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            app.manage(SidecarState(Mutex::new(None)));

            let app_data_dir = app.path().app_data_dir().map_err(|error| {
                std::io::Error::other(format!("Diretório de dados indisponível: {error}"))
            })?;
            let child = start_sidecar(&app_data_dir).map_err(std::io::Error::other)?;
            {
                let state = app.state::<SidecarState>();
                *state.0.lock().expect("estado do sidecar indisponível") = Some(child);
            }

            let app_handle = app.handle().clone();
            thread::spawn(move || match wait_for_health() {
                Ok(()) => {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        if let Err(error) = navigate_to_hub(window) {
                            eprintln!("[desktop] não foi possível abrir o editor: {error}");
                        }
                    }
                }
                Err(error) => {
                    eprintln!("[desktop] {error}");
                    stop_sidecar(&app_handle);
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::CloseRequested { .. }) {
                stop_sidecar(window.app_handle());
            }
        })
        .build(tauri::generate_context!())
        .expect("erro ao preparar o Editor de Carrosseis");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. }) {
            stop_sidecar(app_handle);
        }
    });
}
