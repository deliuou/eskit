use std::fs;
use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};

use crate::util::{basename, is_wsl, is_windows, parent_dir, to_local_path, to_windows_path};

fn ps_quote(s: &str) -> String { format!("'{}'", s.replace('\'', "''")) }

pub fn open_path(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let win = to_windows_path(path).unwrap_or_else(|| path.to_string());
    if is_wsl() || is_windows() {
        let script = format!("Start-Process -LiteralPath {}", ps_quote(&win));
        Command::new(if is_wsl() { "powershell.exe" } else { "powershell" })
            .args(["-NoProfile", "-Command", script.as_str()])
            .status()?;
    } else {
        Command::new("xdg-open").arg(to_local_path(path)).status()?;
    }
    Ok(())
}

pub fn reveal_in_file_manager(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let win = to_windows_path(path).unwrap_or_else(|| path.to_string());
    if is_wsl() || is_windows() {
        Command::new("explorer.exe").arg(format!("/select,{}", win)).status()?;
    } else {
        Command::new("xdg-open").arg(parent_dir(&to_local_path(path))).status()?;
    }
    Ok(())
}

pub fn copy_text_to_clipboard(text: &str) -> Result<(), Box<dyn std::error::Error>> {
    if is_wsl() {
        let mut child = Command::new("clip.exe").stdin(Stdio::piped()).spawn()?;
        child.stdin.as_mut().unwrap().write_all(text.as_bytes())?;
        child.wait()?;
    } else if is_windows() {
        let mut child = Command::new("clip").stdin(Stdio::piped()).spawn()?;
        child.stdin.as_mut().unwrap().write_all(text.as_bytes())?;
        child.wait()?;
    } else {
        let mut child = Command::new("xclip").args(["-selection", "clipboard"]).stdin(Stdio::piped()).spawn()?;
        child.stdin.as_mut().unwrap().write_all(text.as_bytes())?;
        child.wait()?;
    }
    Ok(())
}

pub fn copy_file_to(src: &str, dest_dir: &str) -> Result<String, Box<dyn std::error::Error>> {
    let src_local = to_local_path(src);
    let dest_local = to_local_path(dest_dir);
    fs::create_dir_all(&dest_local)?;
    let target = Path::new(&dest_local).join(basename(src));
    fs::copy(&src_local, &target)?;
    Ok(target.to_string_lossy().to_string())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActionKind { Open, Reveal, CopyPath, CopyName, CopyTo }

pub fn run_action(kind: ActionKind, path: &str, copy_to: Option<&str>) -> Result<(), Box<dyn std::error::Error>> {
    match kind {
        ActionKind::Open => open_path(path)?,
        ActionKind::Reveal => reveal_in_file_manager(path)?,
        ActionKind::CopyPath => { copy_text_to_clipboard(path)?; println!("copied path: {path}"); },
        ActionKind::CopyName => { let name = basename(path); copy_text_to_clipboard(&name)?; println!("copied name: {name}"); },
        ActionKind::CopyTo => {
            let dest = copy_to.ok_or("--copy-to requires a destination")?;
            let target = copy_file_to(path, dest)?;
            println!("copied to: {target}");
        }
    }
    Ok(())
}
