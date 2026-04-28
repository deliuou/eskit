use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::es::token_to_exts;
use crate::util::{split_drive_alias, to_windows_path};

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SearchSpec {
    pub roots: Vec<String>,
    pub exts: Vec<String>,
    pub kinds: Vec<String>,
    pub name_tokens: Vec<String>,
    pub raw_tokens: Vec<String>,
}

impl SearchSpec {
    pub fn query(&self) -> String {
        let q = self.name_tokens.join(" ").trim().to_string();
        if q.is_empty() { "*".to_string() } else { q }
    }
}

pub fn token_to_kind(token: &str) -> Option<&'static str> {
    let mut raw = token.trim().trim_matches('"').trim_matches('\'').to_ascii_lowercase();
    if raw.starts_with("*.") {
        raw = raw[2..].to_string();
    } else if raw.starts_with('.') {
        raw = raw[1..].to_string();
    }
    match raw.as_str() {
        "file" | "files" | "文件" | "文件类型" => Some("file"),
        "folder" | "folders" | "dir" | "dirs" | "directory" | "directories" | "文件夹" | "目录" => Some("folder"),
        _ => None,
    }
}

fn looks_like_drive_letter(token: &str) -> bool {
    let raw = token.trim().trim_matches('"').trim_matches('\'');
    (raw.len() == 1 && raw.chars().next().unwrap().is_ascii_alphabetic())
        || (raw.len() == 2 && raw.as_bytes()[0].is_ascii_alphabetic() && raw.as_bytes()[1] == b':')
}

fn drive_root(token: &str) -> String {
    let drive = token.trim().trim_matches('"').trim_matches('\'').chars().next().unwrap().to_ascii_uppercase();
    format!("{}:\\", drive)
}

fn looks_like_path_root(token: &str) -> bool {
    let raw = token.trim().trim_matches('"').trim_matches('\'');
    if raw.is_empty() || raw.starts_with('.') {
        return false;
    }
    if raw.starts_with("/mnt/") {
        return true;
    }
    if let Some((_drive, rest)) = split_drive_alias(raw) {
        return !rest.is_empty() || raw.contains(':') || raw.contains('/') || raw.contains('\\');
    }
    false
}

fn normalize_root(token: &str) -> String {
    if looks_like_drive_letter(token) {
        drive_root(token)
    } else {
        to_windows_path(token).unwrap_or_else(|| token.to_string())
    }
}

fn dedupe_case(items: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for item in items {
        let key = item.to_ascii_lowercase();
        if seen.insert(key) {
            out.push(item);
        }
    }
    out
}

pub fn parse_search_tokens(tokens: &[String]) -> SearchSpec {
    let mut spec = SearchSpec { raw_tokens: tokens.to_vec(), ..Default::default() };
    let mut roots_allowed = true;

    for raw in tokens {
        let token = raw.trim();
        if token.is_empty() {
            continue;
        }
        if let Some(kind) = token_to_kind(token) {
            spec.kinds.push(kind.to_string());
            roots_allowed = false;
            continue;
        }
        let exts = token_to_exts(token);
        if !exts.is_empty() {
            spec.exts.extend(exts);
            spec.kinds.push("file".to_string());
            roots_allowed = false;
            continue;
        }
        if looks_like_path_root(token) {
            spec.roots.push(normalize_root(token));
            continue;
        }
        if roots_allowed && looks_like_drive_letter(token) {
            spec.roots.push(normalize_root(token));
            continue;
        }
        roots_allowed = false;
        spec.name_tokens.push(token.to_string());
    }

    spec.roots = dedupe_case(spec.roots);
    spec.exts = dedupe_case(
        spec.exts
            .into_iter()
            .map(|e| e.trim().trim_start_matches("*.").trim_start_matches('.').to_string())
            .filter(|e| !e.is_empty())
            .collect(),
    );
    spec.kinds = dedupe_case(spec.kinds.into_iter().filter(|k| k == "file" || k == "folder").collect());
    spec
}
