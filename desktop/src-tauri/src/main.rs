use std::{
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{AppHandle, Manager, RunEvent, WebviewWindow, WebviewWindowBuilder, WindowEvent};

#[cfg(all(test, windows))]
use std::io::BufRead;

const SIDECAR_NAME: &str = "editor-carrosseis-sidecar";
const LOOPBACK_HOST: &str = "127.0.0.1";
const HEALTH_PATH: &str = "/api/health";
const HEALTH_TIMEOUT: Duration = Duration::from_secs(10);
const CHILD_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(2);

struct SidecarState(Mutex<Option<Child>>);

#[derive(Clone, Copy)]
struct LoopbackEndpoint {
    port: u16,
}

impl LoopbackEndpoint {
    fn address(self) -> String {
        format!("{LOOPBACK_HOST}:{}", self.port)
    }

    fn origin(self) -> String {
        format!("http://{}", self.address())
    }
}

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

fn choose_loopback_endpoint() -> Result<LoopbackEndpoint, String> {
    let listener = TcpListener::bind((LOOPBACK_HOST, 0))
        .map_err(|error| format!("Não foi possível reservar uma porta local: {error}"))?;
    let port = listener
        .local_addr()
        .map_err(|error| format!("Não foi possível ler a porta local: {error}"))?
        .port();
    drop(listener);
    Ok(LoopbackEndpoint { port })
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

fn start_sidecar(app_data_dir: &Path, endpoint: LoopbackEndpoint) -> Result<Child, String> {
    std::fs::create_dir_all(app_data_dir).map_err(|error| error.to_string())?;
    let logs_dir = app_data_dir.join("logs");
    std::fs::create_dir_all(&logs_dir).map_err(|error| error.to_string())?;
    let log_file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(logs_dir.join("sidecar.log"))
        .map_err(|error| format!("Não foi possível criar o log do servidor local: {error}"))?;
    let stdout_log = log_file
        .try_clone()
        .map_err(|error| format!("Não foi possível preparar o log do servidor local: {error}"))?;

    let mut command = Command::new(sidecar_path()?);
    command
        .env("CARROSSEL_APP_DATA_DIR", app_data_dir)
        .env("CARROSSEL_EDITOR_PORT", endpoint.port.to_string())
        .stdout(Stdio::from(stdout_log))
        .stderr(Stdio::from(log_file));
    configure_sidecar_command(&mut command);
    command
        .spawn()
        .map_err(|error| format!("Não foi possível iniciar o servidor local: {error}"))
}

fn bounded_timeout(deadline: Instant) -> Option<Duration> {
    let remaining = deadline.saturating_duration_since(Instant::now());
    (!remaining.is_zero()).then_some(remaining.min(Duration::from_millis(250)))
}

fn health_check_before(endpoint: LoopbackEndpoint, deadline: Instant) -> bool {
    let address: SocketAddr = match endpoint.address().parse() {
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
    let request = format!(
        "GET {HEALTH_PATH} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n",
        endpoint.address()
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }

    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok()
        && response.starts_with("HTTP/1.1 200")
        && response.contains("\"ok\": true")
        && response.contains("\"service\": \"editor-carrosseis\"")
}

fn wait_for_health(endpoint: LoopbackEndpoint) -> Result<(), String> {
    let deadline = Instant::now() + HEALTH_TIMEOUT;
    loop {
        if health_check_before(endpoint, deadline) {
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

fn wait_for_health_to_stop(endpoint: LoopbackEndpoint) {
    let deadline = Instant::now() + CHILD_SHUTDOWN_TIMEOUT;
    while Instant::now() < deadline {
        if !health_check_before(endpoint, Instant::now() + Duration::from_millis(100)) {
            return;
        }
        thread::sleep(Duration::from_millis(25));
    }
}

fn stop_sidecar(app: &AppHandle, endpoint: LoopbackEndpoint) {
    let state = app.state::<SidecarState>();
    let child = state
        .0
        .lock()
        .expect("estado do sidecar indisponível")
        .take();
    if let Some(mut child) = child {
        terminate_process_tree(&mut child);
        wait_for_health_to_stop(endpoint);
    }
}

fn is_allowed_navigation(url: &tauri::Url, endpoint: LoopbackEndpoint) -> bool {
    (url.scheme() == "tauri")
        || (url.scheme() == "https" && url.host_str() == Some("tauri.localhost"))
        || (url.scheme() == "http"
            && url.host_str() == Some(LOOPBACK_HOST)
            && url.port_or_known_default() == Some(endpoint.port))
}

fn open_hub_in_default_browser(endpoint: LoopbackEndpoint) -> Result<(), String> {
    let url = format!("{}/", endpoint.origin());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        Command::new("rundll32.exe")
            .args(["url.dll,FileProtocolHandler", &url])
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .map_err(|error| format!("Não foi possível abrir o navegador: {error}"))?;
        return Ok(());
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&url)
            .spawn()
            .map_err(|error| format!("Não foi possível abrir o navegador: {error}"))?;
        return Ok(());
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        Command::new("xdg-open")
            .arg(&url)
            .spawn()
            .map_err(|error| format!("Não foi possível abrir o navegador: {error}"))?;
        return Ok(());
    }
    #[allow(unreachable_code)]
    Err("Não há navegador compatível neste sistema.".to_owned())
}

fn show_startup_error(window: &WebviewWindow, message: &str) {
    let display_message = format!("Não foi possível abrir o Editor de Carrosseis: {message}");
    let script = format!(
        "document.documentElement.dataset.startupState = 'error'; document.querySelector('[data-startup-message]').textContent = {};",
        format!("{display_message:?}")
    );
    let _ = window.eval(script);
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
            let endpoint = choose_loopback_endpoint().map_err(std::io::Error::other)?;
            let window = WebviewWindowBuilder::from_config(app.handle(), window_config)
                .map_err(std::io::Error::other)?
                .on_navigation(move |url| is_allowed_navigation(url, endpoint))
                .build()
                .map_err(std::io::Error::other)?;

            let app_data_dir = app.path().app_data_dir().map_err(|error| {
                std::io::Error::other(format!("Diretório de dados indisponível: {error}"))
            })?;
            let child = match start_sidecar(&app_data_dir, endpoint) {
                Ok(child) => child,
                Err(error) => {
                    show_startup_error(&window, &error);
                    return Ok(());
                }
            };
            {
                let state = app.state::<SidecarState>();
                *state.0.lock().expect("estado do sidecar indisponível") = Some(child);
            }

            let app_handle = app.handle().clone();
            thread::spawn(move || match wait_for_health(endpoint) {
                Ok(()) => {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        if let Err(error) = open_hub_in_default_browser(endpoint) {
                            show_startup_error(&window, &error);
                            stop_sidecar(&app_handle, endpoint);
                        } else {
                            let _ = window.hide();
                        }
                    }
                }
                Err(error) => {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        show_startup_error(&window, &error);
                    }
                    stop_sidecar(&app_handle, endpoint);
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, WindowEvent::CloseRequested { .. }) {
                // The endpoint is random for each launch. Closing the child is
                // sufficient here; the operating system releases its loopback port.
                let state = window.app_handle().state::<SidecarState>();
                let child = state
                    .0
                    .lock()
                    .expect("estado do sidecar indisponível")
                    .take();
                if let Some(mut child) = child {
                    terminate_process_tree(&mut child);
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("erro ao preparar o Editor de Carrosseis");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. }) {
            let state = app_handle.state::<SidecarState>();
            let child = state
                .0
                .lock()
                .expect("estado do sidecar indisponível")
                .take();
            if let Some(mut child) = child {
                terminate_process_tree(&mut child);
            }
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
            assert!(is_allowed_navigation(
                &tauri::Url::parse(allowed).unwrap(),
                LoopbackEndpoint { port: 8777 },
            ));
        }
        for blocked in [
            "https://example.com/",
            "http://localhost:8777/",
            "http://127.0.0.1:9999/",
        ] {
            assert!(!is_allowed_navigation(
                &tauri::Url::parse(blocked).unwrap(),
                LoopbackEndpoint { port: 8777 },
            ));
        }
    }

    #[test]
    fn expired_deadline_never_starts_a_health_request() {
        assert!(!health_check_before(LoopbackEndpoint { port: 8777 }, Instant::now()));
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

    #[cfg(windows)]
    #[test]
    fn termination_stops_windows_tree_without_touching_external_sentinel() {
        let mut sentinel_command = Command::new("powershell.exe");
        sentinel_command
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Start-Sleep -Seconds 30",
            ])
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        let mut sentinel = sentinel_command.spawn().unwrap();

        let mut parent_command = Command::new("powershell.exe");
        parent_command
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$child = Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile -NonInteractive -Command Start-Sleep -Seconds 30' -PassThru; [Console]::Out.WriteLine($child.Id); Wait-Process -Id $child.Id",
            ])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        configure_sidecar_command(&mut parent_command);
        let mut parent = parent_command.spawn().unwrap();
        let child_id = {
            let stdout = parent.stdout.take().unwrap();
            let mut line = String::new();
            std::io::BufReader::new(stdout)
                .read_line(&mut line)
                .unwrap();
            line.trim().parse::<u32>().unwrap()
        };

        terminate_process_tree(&mut parent);

        let check_child_command =
            format!("if (Get-Process -Id {child_id} -ErrorAction SilentlyContinue) {{ exit 1 }}");
        let child_gone = Command::new("powershell.exe")
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                &check_child_command,
            ])
            .status()
            .unwrap()
            .success();
        assert!(child_gone, "o descendente Windows continuou vivo");
        assert!(matches!(sentinel.try_wait(), Ok(None)));

        terminate_process_tree(&mut sentinel);
    }
}
