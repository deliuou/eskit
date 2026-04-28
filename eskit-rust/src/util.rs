use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

pub fn is_wsl() -> bool {
    if env::var("WSL_DISTRO_NAME").is_ok() || env::var("WSL_INTEROP").is_ok() {
        return true;
    }
    std::fs::read_to_string("/proc/version")
        .map(|s| s.to_ascii_lowercase().contains("microsoft"))
        .unwrap_or(false)
}

pub fn is_windows() -> bool {
    cfg!(windows)
}

pub fn split_drive_alias(input: &str) -> Option<(char, String)> {
    let mut raw = input.trim().trim_matches('"').trim_matches('\'').replace('\\', "/");
    if raw.is_empty() {
        return None;
    }
    if raw.starts_with("/mnt/") && raw.len() >= 6 {
        let chars: Vec<char> = raw.chars().collect();
        let drive = chars.get(5).copied()?;
        if drive.is_ascii_alphabetic() {
            let rest: String = chars.iter().skip(6).collect();
            return Some((drive.to_ascii_uppercase(), rest.trim_start_matches('/').to_string()));
        }
    }
    if raw.starts_with('/') && raw.len() >= 2 {
        let chars: Vec<char> = raw.chars().collect();
        let drive = chars.get(1).copied()?;
        if drive.is_ascii_alphabetic() && (chars.len() == 2 || chars.get(2) == Some(&'/')) {
            let rest: String = chars.iter().skip(3).collect();
            return Some((drive.to_ascii_uppercase(), rest.trim_start_matches('/').to_string()));
        }
    }
    if raw.len() == 1 && raw.chars().next().unwrap().is_ascii_alphabetic() {
        return Some((raw.chars().next().unwrap().to_ascii_uppercase(), String::new()));
    }
    if raw.len() >= 2 {
        let mut chars = raw.chars();
        let first = chars.next().unwrap();
        let second = chars.next().unwrap();
        if first.is_ascii_alphabetic() && second == ':' {
            let rest: String = chars.collect();
            return Some((first.to_ascii_uppercase(), rest.trim_start_matches('/').to_string()));
        }
    }
    if raw.len() >= 3 {
        let chars: Vec<char> = raw.chars().collect();
        if chars[0].is_ascii_alphabetic() && chars[1] == '/' {
            let rest: String = chars.iter().skip(2).collect();
            return Some((chars[0].to_ascii_uppercase(), rest.trim_start_matches('/').to_string()));
        }
    }
    None
}

pub fn to_windows_path(input: &str) -> Option<String> {
    let (drive, rest) = split_drive_alias(input)?;
    if rest.is_empty() {
        return Some(format!("{}:\\", drive));
    }
    Some(format!("{}:\\{}", drive, rest.replace('/', "\\")))
}

pub fn to_local_path(input: &str) -> String {
    if is_wsl() {
        if let Some((drive, rest)) = split_drive_alias(input) {
            let d = drive.to_ascii_lowercase();
            if rest.is_empty() {
                return format!("/mnt/{d}");
            }
            return format!("/mnt/{d}/{}", rest.replace('\\', "/"));
        }
    }
    input.to_string()
}

pub fn to_everything_path(input: &str) -> String {
    to_windows_path(input).unwrap_or_else(|| input.to_string())
}

pub fn basename(path: &str) -> String {
    let clean = path.trim_end_matches(['\\', '/']);
    clean.rsplit(['\\', '/']).next().unwrap_or(clean).to_string()
}

pub fn extension(path: &str) -> Option<String> {
    let name = basename(path);
    let idx = name.rfind('.')?;
    if idx + 1 >= name.len() {
        return None;
    }
    Some(name[idx + 1..].to_string())
}

pub fn parent_dir(path: &str) -> String {
    let clean = path.trim_end_matches(['\\', '/']);
    match clean.rfind(['\\', '/']) {
        Some(i) => clean[..i].to_string(),
        None => clean.to_string(),
    }
}

pub fn find_executable(name: &str) -> Option<String> {
    if let Ok(value) = env::var("ESKIT_ES_PATH") {
        if !value.trim().is_empty() {
            return Some(value);
        }
    }
    let candidates = if cfg!(windows) && !name.to_ascii_lowercase().ends_with(".exe") {
        vec![name.to_string(), format!("{name}.exe")]
    } else {
        vec![name.to_string()]
    };
    if let Ok(path_env) = env::var("PATH") {
        for dir in env::split_paths(&path_env) {
            for cand in &candidates {
                let p = dir.join(cand);
                if p.exists() {
                    return Some(p.to_string_lossy().to_string());
                }
            }
        }
    }
    None
}

pub fn windows_process_running(process_name: &str) -> bool {
    let ps = format!(
        "Get-Process -Name '{}' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty ProcessName",
        process_name.replace('\'', "''")
    );
    let exe = if is_wsl() { "powershell.exe" } else { "powershell" };
    Command::new(exe)
        .args(["-NoProfile", "-Command", ps.as_str()])
        .output()
        .map(|out| !String::from_utf8_lossy(&out.stdout).trim().is_empty())
        .unwrap_or(false)
}

pub fn which_es_default_hint() -> String {
    if is_wsl() {
        "export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe".to_string()
    } else {
        "setx ESKIT_ES_PATH C:\\Path\\To\\Everything\\es.exe".to_string()
    }
}

pub fn ensure_parent(path: &Path) -> std::io::Result<()> {
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)?;
        }
    }
    Ok(())
}

pub fn normalize_export_path(path: &str) -> PathBuf {
    PathBuf::from(to_local_path(path))
}
