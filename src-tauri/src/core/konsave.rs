use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

// ── Paths ──────────────────────────────────────────────────────────────────

fn home() -> String {
    std::env::var("HOME").unwrap_or_else(|_| "/root".to_string())
}

pub fn konsave_dir() -> PathBuf {
    PathBuf::from(format!("{}/.config/konsave", home()))
}

pub fn profiles_dir() -> PathBuf {
    konsave_dir().join("profiles")
}

pub fn config_file() -> PathBuf {
    konsave_dir().join("conf.yaml")
}

// ── Token expansion ────────────────────────────────────────────────────────

fn expand_location(location: &str) -> String {
    let home = home();
    let config_dir = format!("{}/.config", home);
    let share_dir = format!("{}/.local/share", home);
    let bin_dir = format!("{}/.local/bin", home);

    let mut s = location
        .replace("$HOME", &home)
        .replace("$CONFIG_DIR", &config_dir)
        .replace("$SHARE_DIR", &share_dir)
        .replace("$BIN_DIR", &bin_dir);

    // ${ENDS_WITH="text"} and ${BEGINS_WITH="text"}
    let re = Regex::new(r#"\$\{(ENDS_WITH|BEGINS_WITH)=["']([^"']+)["']\}"#).unwrap();
    loop {
        let s_clone = s.clone();
        let cap = match re.captures(&s_clone) {
            Some(c) => c,
            None => break,
        };
        let full = cap.get(0).unwrap().as_str();
        let func = cap.get(1).unwrap().as_str();
        let text = cap.get(2).unwrap().as_str();
        let match_start = s.find(full).unwrap();
        let parent = &s[..match_start];

        let replacement = fs::read_dir(parent)
            .ok()
            .and_then(|entries| {
                entries
                    .filter_map(|e| e.ok())
                    .map(|e| e.file_name().to_string_lossy().to_string())
                    .find(|name| match func {
                        "ENDS_WITH" => name.ends_with(text),
                        "BEGINS_WITH" => name.starts_with(text),
                        _ => false,
                    })
            })
            .unwrap_or_else(|| full.to_string());

        s = s.replace(full, &replacement);
        if !re.is_match(&s) {
            break;
        }
    }
    s
}

// ── Config parsing ─────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
struct Section {
    location: String,
    entries: Vec<String>,
}

struct KonsaveConfig {
    save: HashMap<String, Section>,
    export: HashMap<String, Section>,
}

fn parse_section(v: &serde_yaml::Value) -> Option<Section> {
    let location = v.get("location")?.as_str()?.to_string();
    let entries = v
        .get("entries")
        .and_then(|e| e.as_sequence())
        .map(|seq| {
            seq.iter()
                .filter_map(|s| s.as_str())
                .map(String::from)
                .collect()
        })
        .unwrap_or_default();
    Some(Section { location, entries })
}

fn parse_config(path: &Path) -> Result<KonsaveConfig, String> {
    let text = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let raw: serde_yaml::Value = serde_yaml::from_str(&text).map_err(|e| e.to_string())?;

    let mut save: HashMap<String, Section> = HashMap::new();
    let mut export: HashMap<String, Section> = HashMap::new();

    for (key, map) in [("save", &mut save), ("export", &mut export)] {
        if let Some(serde_yaml::Value::Mapping(m)) = raw.get(key) {
            for (k, v) in m {
                if let (Some(name), Some(sec)) =
                    (k.as_str(), parse_section(v))
                {
                    map.insert(name.to_string(), sec);
                }
            }
        }
    }

    for sec in save.values_mut().chain(export.values_mut()) {
        sec.location = expand_location(&sec.location);
    }

    Ok(KonsaveConfig { save, export })
}

// ── Profile info ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SectionInfo {
    pub name: String,
    pub location: String,
    pub entries: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileInfo {
    pub name: String,
    pub modified: String,
    pub sections_save: Vec<SectionInfo>,
    pub sections_export: Vec<SectionInfo>,
}

fn to_section_infos(map: HashMap<String, Section>) -> Vec<SectionInfo> {
    let mut v: Vec<SectionInfo> = map
        .into_iter()
        .map(|(name, s)| SectionInfo {
            name,
            location: s.location,
            entries: s.entries,
        })
        .collect();
    v.sort_by(|a, b| a.name.cmp(&b.name));
    v
}

fn format_mtime(path: &Path) -> String {
    use chrono::{DateTime, Local};
    path.metadata()
        .ok()
        .and_then(|m| m.modified().ok())
        .map(|t| {
            let dt: DateTime<Local> = t.into();
            dt.format("%B %d, %Y  %H:%M").to_string()
        })
        .unwrap_or_default()
}

pub fn list_profiles() -> Result<Vec<ProfileInfo>, String> {
    let dir = profiles_dir();
    if !dir.exists() {
        return Ok(vec![]);
    }
    let mut entries: Vec<_> = fs::read_dir(&dir)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok())
        .filter(|e| e.path().is_dir())
        .collect();
    entries.sort_by_key(|e| e.file_name());

    let mut profiles = Vec::new();
    for entry in entries {
        let name = entry.file_name().to_string_lossy().to_string();
        let profile_dir = entry.path();
        let modified = format_mtime(&profile_dir);

        let conf_path = profile_dir.join("conf.yaml");
        let (sections_save, sections_export) = if conf_path.exists() {
            match parse_config(&conf_path) {
                Ok(cfg) => (to_section_infos(cfg.save), to_section_infos(cfg.export)),
                Err(_) => (vec![], vec![]),
            }
        } else {
            (vec![], vec![])
        };

        profiles.push(ProfileInfo { name, modified, sections_save, sections_export });
    }
    Ok(profiles)
}

// ── Copy helper ────────────────────────────────────────────────────────────

fn copy_path(src: &Path, dst: &Path) -> Result<(), String> {
    if src.is_dir() {
        fs::create_dir_all(dst).map_err(|e| e.to_string())?;
        for e in WalkDir::new(src).min_depth(1) {
            let e = e.map_err(|e| e.to_string())?;
            let rel = e.path().strip_prefix(src).map_err(|e| e.to_string())?;
            let target = dst.join(rel);
            if e.path().is_dir() {
                fs::create_dir_all(&target).map_err(|e| e.to_string())?;
            } else {
                if let Some(p) = target.parent() {
                    fs::create_dir_all(p).map_err(|e| e.to_string())?;
                }
                fs::copy(e.path(), &target).map_err(|e| e.to_string())?;
            }
        }
    } else {
        if let Some(p) = dst.parent() {
            fs::create_dir_all(p).map_err(|e| e.to_string())?;
        }
        fs::copy(src, dst).map_err(|e| e.to_string())?;
    }
    Ok(())
}

// ── Save / Apply / Delete / Wipe ───────────────────────────────────────────

pub fn save_profile(name: &str, force: bool) -> Result<(), String> {
    let profile_dir = profiles_dir().join(name);
    if profile_dir.exists() && !force {
        return Err(format!("Profile '{}' already exists", name));
    }
    fs::create_dir_all(&profile_dir).map_err(|e| e.to_string())?;

    let cfg_path = config_file();
    let config = parse_config(&cfg_path)?;

    for (sec_name, sec) in &config.save {
        let dest_dir = profile_dir.join(sec_name);
        fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;
        for entry in &sec.entries {
            let src = Path::new(&sec.location).join(entry);
            if src.exists() {
                copy_path(&src, &dest_dir.join(entry))?;
            }
        }
    }

    fs::copy(&cfg_path, profile_dir.join("conf.yaml")).map_err(|e| e.to_string())?;
    Ok(())
}

pub fn apply_profile(name: &str) -> Result<(), String> {
    let profile_dir = profiles_dir().join(name);
    if !profile_dir.exists() {
        return Err(format!("Profile '{}' not found", name));
    }
    let config = parse_config(&profile_dir.join("conf.yaml"))?;
    for (sec_name, sec) in &config.save {
        let src_dir = profile_dir.join(sec_name);
        let dest = Path::new(&sec.location);
        for entry in &sec.entries {
            let src = src_dir.join(entry);
            if src.exists() {
                copy_path(&src, &dest.join(entry))?;
            }
        }
    }
    Ok(())
}

pub fn delete_profile(name: &str) -> Result<(), String> {
    let dir = profiles_dir().join(name);
    if !dir.exists() {
        return Err(format!("Profile '{}' not found", name));
    }
    fs::remove_dir_all(&dir).map_err(|e| e.to_string())
}

pub fn wipe_profiles() -> Result<(), String> {
    let dir = profiles_dir();
    if dir.exists() {
        fs::remove_dir_all(&dir).map_err(|e| e.to_string())?;
    }
    fs::create_dir_all(&dir).map_err(|e| e.to_string())
}

// ── Export .knsv ───────────────────────────────────────────────────────────

pub fn export_profile(name: &str, dest_dir: &str) -> Result<String, String> {
    let profile_dir = profiles_dir().join(name);
    if !profile_dir.exists() {
        return Err(format!("Profile '{}' not found", name));
    }

    let out_path = PathBuf::from(dest_dir).join(format!("{}.knsv", name));
    let file = fs::File::create(&out_path).map_err(|e| e.to_string())?;
    let mut zip = zip::ZipWriter::new(file);
    let opts = zip::write::SimpleFileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    // conf.yaml
    let conf_path = profile_dir.join("conf.yaml");
    zip.start_file("conf.yaml", opts).map_err(|e| e.to_string())?;
    zip.write_all(&fs::read(&conf_path).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;

    let config = parse_config(&conf_path)?;

    // save/ — from profile dir (already-snapshotted files)
    for sec_name in config.save.keys() {
        let sec_dir = profile_dir.join(sec_name);
        if !sec_dir.exists() {
            continue;
        }
        for e in WalkDir::new(&sec_dir) {
            let e = e.map_err(|e| e.to_string())?;
            let rel = e.path().strip_prefix(&profile_dir).map_err(|e| e.to_string())?;
            let zip_path = format!("save/{}", rel.to_string_lossy());
            if e.path().is_dir() {
                zip.add_directory(format!("{}/", zip_path), opts)
                    .map_err(|e| e.to_string())?;
            } else {
                zip.start_file(&zip_path, opts).map_err(|e| e.to_string())?;
                zip.write_all(&fs::read(e.path()).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
            }
        }
    }

    // export/ — from live system
    for (sec_name, sec) in &config.export {
        let location = Path::new(&sec.location);
        for entry in &sec.entries {
            let src = location.join(entry);
            if !src.exists() {
                continue;
            }
            if src.is_dir() {
                for e in WalkDir::new(&src) {
                    let e = e.map_err(|e| e.to_string())?;
                    let rel = e.path().strip_prefix(location).map_err(|e| e.to_string())?;
                    let zip_path = format!("export/{}/{}", sec_name, rel.to_string_lossy());
                    if e.path().is_dir() {
                        zip.add_directory(format!("{}/", zip_path), opts)
                            .map_err(|e| e.to_string())?;
                    } else {
                        zip.start_file(&zip_path, opts).map_err(|e| e.to_string())?;
                        zip.write_all(&fs::read(e.path()).map_err(|e| e.to_string())?)
                            .map_err(|e| e.to_string())?;
                    }
                }
            } else {
                let zip_path = format!("export/{}/{}", sec_name, entry);
                zip.start_file(&zip_path, opts).map_err(|e| e.to_string())?;
                zip.write_all(&fs::read(&src).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
            }
        }
    }

    zip.finish().map_err(|e| e.to_string())?;
    Ok(out_path.to_string_lossy().to_string())
}

// ── Import .knsv ───────────────────────────────────────────────────────────

pub fn import_profile(path: &str) -> Result<String, String> {
    if !path.ends_with(".knsv") {
        return Err("Not a valid .knsv file".to_string());
    }
    let path = Path::new(path);
    let name = path
        .file_stem()
        .and_then(|s| s.to_str())
        .ok_or("Invalid filename")?
        .to_string();

    let profile_dir = profiles_dir().join(&name);
    if profile_dir.exists() {
        return Err(format!("Profile '{}' already exists", name));
    }

    // First pass: extract conf.yaml and save/ into profile dir
    {
        let file = fs::File::open(path).map_err(|e| e.to_string())?;
        let mut zip = zip::ZipArchive::new(file).map_err(|e| e.to_string())?;
        for i in 0..zip.len() {
            let mut zf = zip.by_index(i).map_err(|e| e.to_string())?;
            let zname = zf.name().to_string();
            let dest = if zname == "conf.yaml" {
                profile_dir.join("conf.yaml")
            } else if let Some(rest) = zname.strip_prefix("save/") {
                if rest.is_empty() {
                    continue;
                }
                profile_dir.join(rest)
            } else {
                continue;
            };
            if zname.ends_with('/') {
                fs::create_dir_all(&dest).map_err(|e| e.to_string())?;
            } else {
                if let Some(p) = dest.parent() {
                    fs::create_dir_all(p).map_err(|e| e.to_string())?;
                }
                let mut buf = Vec::new();
                zf.read_to_end(&mut buf).map_err(|e| e.to_string())?;
                fs::write(&dest, buf).map_err(|e| e.to_string())?;
            }
        }
    }

    // Second pass: apply export/ sections to live system
    let conf_path = profile_dir.join("conf.yaml");
    if conf_path.exists() {
        let config = parse_config(&conf_path)?;
        let file = fs::File::open(path).map_err(|e| e.to_string())?;
        let mut zip = zip::ZipArchive::new(file).map_err(|e| e.to_string())?;

        for (sec_name, sec) in &config.export {
            let prefix = format!("export/{}/", sec_name);
            let location = Path::new(&sec.location);

            for i in 0..zip.len() {
                let mut zf = zip.by_index(i).map_err(|e| e.to_string())?;
                let zname = zf.name().to_string();
                if !zname.starts_with(&prefix) {
                    continue;
                }
                let rel = &zname[prefix.len()..];
                if rel.is_empty() {
                    continue;
                }
                let dest = location.join(rel);
                if zname.ends_with('/') {
                    fs::create_dir_all(&dest).map_err(|e| e.to_string())?;
                } else {
                    if let Some(p) = dest.parent() {
                        fs::create_dir_all(p).map_err(|e| e.to_string())?;
                    }
                    let mut buf = Vec::new();
                    zf.read_to_end(&mut buf).map_err(|e| e.to_string())?;
                    fs::write(&dest, buf).map_err(|e| e.to_string())?;
                }
            }
        }
    }

    Ok(name)
}

// ── Config file read/write ─────────────────────────────────────────────────

pub fn read_config_text() -> Result<String, String> {
    fs::read_to_string(config_file()).map_err(|e| e.to_string())
}

pub fn write_config_text(text: &str) -> Result<(), String> {
    serde_yaml::from_str::<serde_yaml::Value>(text)
        .map_err(|e| format!("Invalid YAML: {}", e))?;
    fs::write(config_file(), text).map_err(|e| e.to_string())
}

// ── Nextcloud sync ─────────────────────────────────────────────────────────

pub fn sync_push(nextcloud_path: &str) -> Result<u32, String> {
    let nc_dir = Path::new(nextcloud_path).join("konsave");
    fs::create_dir_all(&nc_dir).map_err(|e| e.to_string())?;
    let profiles = list_profiles()?;
    let mut count = 0u32;
    for p in &profiles {
        export_profile(&p.name, &nc_dir.to_string_lossy())?;
        count += 1;
    }
    Ok(count)
}

pub fn sync_pull(nextcloud_path: &str) -> Result<u32, String> {
    let nc_dir = Path::new(nextcloud_path).join("konsave");
    if !nc_dir.exists() {
        return Ok(0);
    }
    let existing: Vec<String> = list_profiles()?.into_iter().map(|p| p.name).collect();
    let mut count = 0u32;
    for e in fs::read_dir(&nc_dir).map_err(|e| e.to_string())? {
        let e = e.map_err(|e| e.to_string())?;
        let path = e.path();
        if path.extension().and_then(|x| x.to_str()) == Some("knsv") {
            let name = path
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("")
                .to_string();
            if !existing.contains(&name) {
                import_profile(&path.to_string_lossy())?;
                count += 1;
            }
        }
    }
    Ok(count)
}
