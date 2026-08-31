use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;
use std::path::PathBuf;

fn configured_data_dir() -> Option<PathBuf> {
  std::env::var_os("TTS_WORKBENCH_DATA_DIR")
    .filter(|value| !value.is_empty())
    .map(PathBuf::from)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      
      // Resolve app data directory
      let app_data = match configured_data_dir() {
        Some(path) => path,
        None => app.path().app_data_dir()?,
      };
      std::fs::create_dir_all(&app_data)?;
      let data_dir_str = app_data.to_string_lossy().to_string();
      
      println!("Launching backend sidecar.");
      
      // Spawn sidecar
      let sidecar = app.shell()
        .sidecar("backend_sidecar")?
        .args(["--host", "127.0.0.1", "--port", "8765", "--data-dir", &data_dir_str]);
        
      let (mut rx, _child) = sidecar.spawn()?;
      
      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            CommandEvent::Stdout(line) => {
              let message = String::from_utf8_lossy(&line);
              println!("Sidecar Out: {}", message.chars().take(1_000).collect::<String>().trim_end());
            }
            CommandEvent::Stderr(line) => {
              let message = String::from_utf8_lossy(&line);
              eprintln!("Sidecar Err: {}", message.chars().take(1_000).collect::<String>().trim_end());
            }
            CommandEvent::Terminated(status) => {
              println!("Sidecar Terminated with status: {:?}", status);
            }
            _ => {}
          }
        }
      });
      
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
