//! Desktop shell: starts the Python engine (`uv run factory serve`) next to the window and stops it on exit.
//! The React UI talks to the engine over http://127.0.0.1:8790.
//!
//! Two layouts. A release build carries the repository's code as resources (`content-factory/`: engine/, formats/,
//! render/) and keeps everything it writes in the user's app-data folder (CF_DATA), with Python and packages in
//! `<data>/venv`. A debug build runs the repository it was built from, with its data in `data/`, so development
//! works on the checkout itself.

use std::fs::File;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use serde::Serialize;
use tauri::{AppHandle, Manager, RunEvent, State};

const PORT: u16 = 8790;

struct Engine(Mutex<Option<Child>>);

#[derive(Clone, Serialize)]
struct Layout {
    /// The repository: engine/ (the Python project), formats/, render/.
    root: PathBuf,
    /// Where the engine writes; None in development, where it is the repository's data/.
    data: Option<PathBuf>,
}

impl Layout {
    fn data_dir(&self) -> PathBuf {
        self.data.clone().unwrap_or_else(|| self.root.join("data"))
    }
    fn log(&self) -> PathBuf {
        self.data_dir().join("engine.log")
    }
}

fn layout(app: &AppHandle) -> Layout {
    if let Some(root) = std::env::var_os("CF_ROOT") {
        return Layout { root: root.into(), data: std::env::var_os("CF_DATA").map(PathBuf::from) };
    }
    let bundled = app.path().resource_dir().ok().map(|d| d.join("content-factory")).filter(|d| d.join("engine/pyproject.toml").is_file());
    match bundled {
        Some(root) if !cfg!(debug_assertions) => Layout { root, data: app.path().app_data_dir().ok() },
        _ => Layout {
            root: Path::new(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap_or_default(),
            data: None,
        },
    }
}

/// GUI apps on macOS start without the shell PATH, so look where uv is usually installed too, and in the
/// app's own folder, where `install_uv` puts it.
fn find_uv(data: &Path) -> Option<PathBuf> {
    let exe = if cfg!(windows) { "uv.exe" } else { "uv" };
    let home = std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" }).map(PathBuf::from).unwrap_or_default();
    let mut dirs: Vec<PathBuf> = vec![data.join("bin")];
    dirs.extend(std::env::var_os("PATH").map(|p| std::env::split_paths(&p).collect::<Vec<_>>()).unwrap_or_default());
    dirs.extend([
        home.join(".local/bin"),
        home.join(".cargo/bin"),
        PathBuf::from("/opt/homebrew/bin"),
        PathBuf::from("/usr/local/bin"),
    ]);
    dirs.into_iter().map(|d| d.join(exe)).find(|p| p.is_file())
}

fn engine_up() -> bool {
    TcpStream::connect_timeout(&([127, 0, 0, 1], PORT).into(), Duration::from_millis(300)).is_ok()
}

fn start_engine(l: &Layout) -> Result<Option<Child>, String> {
    if engine_up() {
        log::info!("engine already running on {PORT}");
        return Ok(None);
    }
    let data = l.data_dir();
    std::fs::create_dir_all(&data).map_err(|e| e.to_string())?;
    let uv = find_uv(&data).ok_or("uv not found")?;
    let log = File::create(l.log()).map_err(|e| e.to_string())?;
    let mut cmd = Command::new(uv);
    cmd.arg("run").arg("--project").arg(l.root.join("engine"));
    if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        cmd.args(["--extra", "mac"]); // MLX voice and speech-to-text
    }
    if let Some(d) = &l.data {
        // the bundled code is read-only: the lock is used as is and the environment lives with the data
        cmd.arg("--frozen").env("UV_PROJECT_ENVIRONMENT", d.join("venv")).env("CF_DATA", d);
    }
    cmd.args(["factory", "serve", "--port", &PORT.to_string()])
        .env("CF_ROOT", &l.root)
        .current_dir(&data)
        .stdout(Stdio::from(log.try_clone().map_err(|e| e.to_string())?))
        .stderr(Stdio::from(log));
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW: no console window behind the app
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        cmd.process_group(0); // own group, so stopping it also stops the Python process uv started
    }
    cmd.spawn().map(Some).map_err(|e| e.to_string())
}

/// uv runs the engine as its own child: stop the whole tree, not only uv.
fn stop_engine(mut child: Child) {
    let pid = child.id().to_string();
    #[cfg(unix)]
    let _ = Command::new("kill").args(["-TERM", &format!("-{pid}")]).status();
    #[cfg(windows)]
    let _ = Command::new("taskkill").args(["/PID", &pid, "/T", "/F"]).status();
    let _ = child.kill();
    let _ = child.wait();
}

#[derive(Serialize)]
struct EngineInfo {
    uv: bool,
    running: bool,
    /// The process is alive but not answering yet: on first launch uv is fetching Python and packages.
    starting: bool,
    log: String,
}

/// What the "engine is not running" screen shows: is uv there, is the engine coming up, the end of its log.
#[tauri::command]
fn engine_info(app: AppHandle, engine: State<Engine>) -> EngineInfo {
    let l = layout(&app);
    let mut child = engine.0.lock().unwrap();
    let alive = child.as_mut().is_some_and(|c| matches!(c.try_wait(), Ok(None)));
    let text = std::fs::read_to_string(l.log()).unwrap_or_default();
    let tail: Vec<&str> = text.lines().rev().take(12).collect();
    EngineInfo {
        uv: find_uv(&l.data_dir()).is_some(),
        running: engine_up(),
        starting: alive && !engine_up(),
        log: tail.into_iter().rev().collect::<Vec<_>>().join("\n"),
    }
}

/// Start (or restart) the engine.
#[tauri::command]
fn restart_engine(app: AppHandle, engine: State<Engine>) -> Result<(), String> {
    let mut slot = engine.0.lock().unwrap();
    if let Some(child) = slot.take() {
        stop_engine(child);
    }
    *slot = start_engine(&layout(&app))?;
    Ok(())
}

/// Install uv with its official installer into the app's own folder, without touching the user's PATH or shell.
#[tauri::command]
async fn install_uv(app: AppHandle) -> Result<(), String> {
    let bin = layout(&app).data_dir().join("bin");
    std::fs::create_dir_all(&bin).map_err(|e| e.to_string())?;
    let mut cmd = if cfg!(windows) {
        let mut c = Command::new("powershell");
        c.args(["-NoProfile", "-ExecutionPolicy", "ByPass", "-Command", "irm https://astral.sh/uv/install.ps1 | iex"]);
        c
    } else {
        let mut c = Command::new("sh");
        c.args(["-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]);
        c
    };
    let out = cmd.env("UV_INSTALL_DIR", &bin).env("UV_NO_MODIFY_PATH", "1").output().map_err(|e| e.to_string())?;
    if !out.status.success() {
        return Err(String::from_utf8_lossy(&out.stderr).lines().last().unwrap_or("uv install failed").to_string());
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().level(log::LevelFilter::Info).build())
        .invoke_handler(tauri::generate_handler![engine_info, restart_engine, install_uv])
        .setup(|app| {
            let child = start_engine(&layout(app.handle())).unwrap_or_else(|e| {
                log::error!("engine not started: {e}");
                None
            });
            app.manage(Engine(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(child) = handle.state::<Engine>().0.lock().unwrap().take() {
                stop_engine(child);
            }
        }
    });
}
