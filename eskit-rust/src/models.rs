use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::util::{basename, extension, to_local_path};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandResult {
    pub ok: bool,
    pub command: Vec<String>,
    pub returncode: i32,
    pub stdout: String,
    pub stderr: String,
    pub elapsed_ms: u128,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub path: String,
    pub kind: String,
    pub size: Option<u64>,
    pub modified_unix: Option<i64>,
}

impl SearchResult {
    pub fn from_path(path: impl Into<String>, verify: bool) -> Self {
        let path = path.into();
        let mut item = SearchResult {
            path,
            kind: "unknown".to_string(),
            size: None,
            modified_unix: None,
        };
        if verify {
            item.populate_metadata();
        }
        item
    }

    pub fn populate_metadata(&mut self) {
        let local = to_local_path(&self.path);
        let p = Path::new(&local);
        if let Ok(meta) = fs::metadata(p) {
            self.kind = if meta.is_dir() { "folder".to_string() } else { "file".to_string() };
            self.size = if meta.is_file() { Some(meta.len()) } else { None };
            if let Ok(st) = meta.modified() {
                self.modified_unix = system_time_to_unix(st);
            }
        }
    }

    pub fn basename(&self) -> String {
        basename(&self.path)
    }

    pub fn ext(&self) -> String {
        extension(&self.path).unwrap_or_default().to_ascii_lowercase()
    }
}

fn system_time_to_unix(st: SystemTime) -> Option<i64> {
    st.duration_since(UNIX_EPOCH).ok().map(|d| d.as_secs() as i64)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EsKitResponse {
    pub ok: bool,
    pub action: String,
    pub query: String,
    pub count: usize,
    pub results: Vec<SearchResult>,
    pub warnings: Vec<String>,
    pub meta: serde_json::Value,
}

impl EsKitResponse {
    pub fn empty(action: &str, query: &str) -> Self {
        Self {
            ok: true,
            action: action.to_string(),
            query: query.to_string(),
            count: 0,
            results: Vec::new(),
            warnings: Vec::new(),
            meta: serde_json::json!({}),
        }
    }
}
