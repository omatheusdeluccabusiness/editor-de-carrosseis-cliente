use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{AppHandle, Manager, RunEvent, WebviewWindow, WebviewWindowBuilder, WindowEvent};

#[cfg(all(test, unix))]
use std::process::Stdio;

const SIDECAR_NAME: &str = "editor-carrosseis-sidecar";
const HEALTH_ADDRESS: &str = "127.0.0.1:8777";
const HEALTH_PATH: &str = "/api/health";
const HEALTH_TIMEOUT: Duration = Duration::from_secs(10);
const CHILD_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(2);

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
    let listener = TcpListener::bind(HEALTH_ADDRESS).map_err(|_| {
        "A porta local 8777 já está em uso. Feche outro Editor de Carrosseis e tente novamente."
            .to_owned()
    })?;
    drop(listener);
    Ok(())
}

fn configure_sidecar_command(command: &mut Command) {
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
}

fn start_sidecar(app_data_dir: &Path) -> Result<Child, String> {
    ensure_loopback_port_is_available()?;
    std::fs::create_dir_all(app_data_dir).map_err(|error| error.to_string())?;

    let mut command = Command::new(sidecar_path()?);
    command.env("CARROSSEL_APP_DATA_DIR", app_data_dir);
    configure_sidecar_command(&mut command);
    command
        .spawn()
        .map_err(|error| format!("Não foi possível iniciar o servidor local: {error}"))
}

fn bounded_timeout(deadline: Instant) -> Option<Duration> {
    let remaining = deadline.saturating_duration_since(Instant::now());
    (!remaining.is_zero()).then_some(remaining.min(Duration::from_millis(250)))
}

fn health_check_before(deadline: Instant) -> bool {
    let address: SocketAddr = match HEALTH_ADDRESS.parse() {
        Ok(address) => address,
        Err(_) => return false,
    };
    let Some(connect_timeout) = bounded_timeout(deadline) else {
        return false;
    };
    let mut stream = match TcpStream::connect_timeout(&address, connect_timeout) {
        Ok(stream) => stream,
        Err(_) => return false,
    };
    let Some(io_timeout) = bounded_timeout(deadline) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(io_timeout));
    let _ = stream.set_write_timeout(Some(io_timeout));
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
    loop {
        if health_check_before(deadline) {
            return Ok(());
        }
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            break;
        }
        thread::sleep(remaining.min(Duration::from_millis(100)));
    }
    Err("O servidor local não respondeu em até 10 segundos.".to_owned())
}

fn wait_for_child_exit(child: &mut Child, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    loop {
        match child.try_wait() {
            Ok(Some(_)) => return true,
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(25)),
            Ok(None) | Err(_) => return false,
        }
    }
}

fn terminate_process_tree(child: &mut Child) {
    if !matches!(child.try_wait(), Ok(None)) {
        return;
    }

    #[cfg(unix)]
    {
        let process_group = -(child.id() as i32);
        unsafe {
            libc::kill(process_group, libc::SIGTERM);
        }
        if !wait_for_child_exit(child, CHILD_SHUTDOWN_TIMEOUT) {
            unsafe {
                libc::kill(process_group, libc::SIGKILL);
            }
            let _ = wait_for_child_exit(child, CHILD_SHUTDOWN_TIMEOUT);
        }
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let mut taskkill = Command::new("taskkill");
        taskkill
            .args(["/PID", &child.id().to_string(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW);
        let _ = taskkill.status();
        let _ = wait_for_child_exit(child, CHILD_SHUTDOWN_TIMEOUT);
    }

    #[cfg(not(any(unix, windows)))]
    {
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn wait_for_health_to_stop() {
    let deadline = Instant::now() + CHILD_SHUTDOWN_TIMEOUT;
    while Instant::now() < deadline {
        if !health_check_before(Instant::now() + Duration::from_millis(100)) {
            return;
        }
        thread::sleep(Duration::from_millis(25));
    }
}

fn stop_sidecar(app: &AppHandle) {
    let state = app.state::<SidecarState>();
    let child = state
        .0
        .lock()
        .expect("estado do sidecar indisponível")
        .take();
    if let Some(mut child) = child {
        terminate_process_tree(&mut child);
        wait_for_health_to_stop();
    }
}

fn is_allowed_navigation(url: &tauri::Url) -> bool {
    (url.scheme() == "tauri")
        || (url.scheme() == "https" && url.host_str() == Some("tauri.localhost"))
        || (url.scheme() == "http"
            && url.host_str() == Some("127.0.0.1")
            && url.port_or_known_default() == Some(8777))
}

fn navigate_to_hub(window: WebviewWindow) -> Result<(), String> {
    let url = tauri::Url::parse("http://127.0.0.1:8777/").map_err(|error| error.to_string())?;
    window.navigate(url).map_err(|error| error.to_string())
}

fn show_startup_error(window: &WebviewWindow, message: &str) {
    let display_message = format!("Não foi possível abrir o Editor de Carrosseis: {message}");
    let script = format!(
        "document.querySelector('[data-startup-message]').textContent = {};",
        format!("{display_message:?}")
    );
    let _ = window.eval(script);
}

fn exit_after_startup_error(app: AppHandle) {
    thread::spawn(move || {
        thread::sleep(Duration::from_secs(3));
        app.exit(1);
    });
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            app.manage(SidecarState(Mutex::new(None)));
            let window_config = app
                .config()
                .app
                .windows
                .iter()
                .find(|window| window.label == "main")
                .ok_or_else(|| std::io::Error::other("janela principal ausente"))?;
            let window = WebviewWindowBuilder::from_config(app.handle(), window_config)
                .map_err(std::io::Error::other)?
                .on_navigation(is_allowed_navigation)
                .build()
                .map_err(std::io::Error::other)?;

            let app_data_dir = app.path().app_data_dir().map_err(|error| {
                std::io::Error::other(format!("Diretório de dados indisponível: {error}"))
            })?;
            let child = match start_sidecar(&app_data_dir) {
                Ok(child) => child,
                Err(error) => {
                    show_startup_error(&window, &error);
                    exit_after_startup_error(app.handle().clone());
                    return Ok(());
                }
            };
            {
                let state = app.state::<SidecarState>();
                *state.0.lock().expect("estado do sidecar indisponível") = Some(child);
            }

            let app_handle = app.handle().clone();
            thread::spawn(move || match wait_for_health() {
                Ok(()) => {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        if let Err(error) = navigate_to_hub(window.clone()) {
                            show_startup_error(&window, &error);
                            stop_sidecar(&app_handle);
                            exit_after_startup_error(app_handle);
                        }
                    }
                }
                Err(error) => {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        show_startup_error(&window, &error);
                    }
                    stop_sidecar(&app_handle);
                    exit_after_startup_error(app_handle);
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_allows_embedded_splash_and_exact_loopback_origin() {
        for allowed in [
            "tauri://localhost/index.html",
            "https://tauri.localhost/index.html",
            "http://127.0.0.1:8777/",
        ] {
            assert!(is_allowed_navigation(&tauri::Url::parse(allowed).unwrap()));
        }
        for blocked in [
            "https://example.com/",
            "http://localhost:8777/",
            "http://127.0.0.1:9999/",
        ] {
            assert!(!is_allowed_navigation(&tauri::Url::parse(blocked).unwrap()));
        }
    }

    #[test]
    fn expired_deadline_never_starts_a_health_request() {
        assert!(!health_check_before(Instant::now()));
    }

    #[cfg(unix)]
    #[test]
    fn termination_stops_the_entire_process_group() {
        let pid_file = std::env::temp_dir().join(format!(
            "editor-carrosseis-descendant-{}.pid",
            std::process::id()
        ));
        let command_text = format!(
            "sleep 30 & child=$!; echo $child > {}; wait $child",
            pid_file.display()
        );
        let mut command = Command::new("sh");
        command.args(["-c", &command_text]);
        configure_sidecar_command(&mut command);
        let mut parent = command.spawn().unwrap();

        let deadline = Instant::now() + Duration::from_secs(1);
        while !pid_file.exists() && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(10));
        }
        let descendant = std::fs::read_to_string(&pid_file).unwrap();
        terminate_process_tree(&mut parent);

        let descendant_gone = (0..40).any(|_| {
            let gone = !Command::new("kill")
                .args(["-0", descendant.trim()])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()
                .unwrap()
                .success();
            if !gone {
                thread::sleep(Duration::from_millis(25));
            }
            gone
        });
        let _ = std::fs::remove_file(pid_file);
        assert!(descendant_gone, "o descendente do sidecar continuou vivo");
    }
}
