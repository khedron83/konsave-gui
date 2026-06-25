mod core;

use tauri::Manager;
use core::konsave::{self, ProfileInfo};
use core::settings::{self, Settings};


fn settings_path(app: &tauri::AppHandle) -> std::path::PathBuf {
    let dir = app.path().app_config_dir().unwrap_or_default();
    settings::settings_file(&dir)
}

// ── Settings ───────────────────────────────────────────────────────────────

#[tauri::command]
async fn get_settings(app: tauri::AppHandle) -> Result<Settings, String> {
    Ok(settings::load(&settings_path(&app)))
}

#[tauri::command]
async fn save_settings(app: tauri::AppHandle, s: Settings) -> Result<(), String> {
    settings::save(&settings_path(&app), &s)
}

// ── Profiles ───────────────────────────────────────────────────────────────

#[tauri::command]
async fn list_profiles() -> Result<Vec<ProfileInfo>, String> {
    konsave::list_profiles()
}

#[tauri::command]
async fn save_profile(name: String, force: bool) -> Result<(), String> {
    konsave::save_profile(&name, force)
}

#[tauri::command]
async fn apply_profile(name: String) -> Result<(), String> {
    konsave::apply_profile(&name)
}

#[tauri::command]
async fn delete_profile(name: String) -> Result<(), String> {
    konsave::delete_profile(&name)
}

#[tauri::command]
async fn wipe_profiles() -> Result<(), String> {
    konsave::wipe_profiles()
}

// ── Export / Import ────────────────────────────────────────────────────────

#[tauri::command]
async fn export_profile(name: String, dest_dir: String) -> Result<String, String> {
    konsave::export_profile(&name, &dest_dir)
}

#[tauri::command]
async fn import_profile(path: String) -> Result<String, String> {
    konsave::import_profile(&path)
}

// ── Config file ────────────────────────────────────────────────────────────

#[tauri::command]
async fn read_config() -> Result<String, String> {
    konsave::read_config_text()
}

#[tauri::command]
async fn write_config(text: String) -> Result<(), String> {
    konsave::write_config_text(&text)
}

// ── Nextcloud sync ─────────────────────────────────────────────────────────

#[tauri::command]
async fn sync_push(url: String, username: String, password: String) -> Result<u32, String> {
    konsave::sync_push(&url, &username, &password).await
}

#[tauri::command]
async fn sync_pull(url: String, username: String, password: String) -> Result<u32, String> {
    konsave::sync_pull(&url, &username, &password).await
}

// ── App run ────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|_app| Ok(()))
        .invoke_handler(tauri::generate_handler![
            get_settings,
            save_settings,
            list_profiles,
            save_profile,
            apply_profile,
            delete_profile,
            wipe_profiles,
            export_profile,
            import_profile,
            read_config,
            write_config,
            sync_push,
            sync_pull,
        ])
        .run(tauri::generate_context!())
        .expect("error running konsave-gui")
}
