use serde_json::json;
use std::collections::HashSet;
use std::process::Command;
use std::time::Instant;

use crate::fuzzy::sort_paths_listary;
use crate::models::{CommandResult, EsKitResponse, SearchResult};
use crate::util::{find_executable, to_everything_path};

#[derive(Debug, Clone)]
pub struct EsClient {
    pub es_path: Option<String>,
    pub timeout_secs: u64,
    pub instance: Option<String>,
}

#[derive(Debug)]
pub struct EsError {
    pub message: String,
    pub result: Option<CommandResult>,
}

impl std::fmt::Display for EsError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for EsError {}

impl EsClient {
    pub fn new(es_path: Option<String>, timeout_secs: u64, instance: Option<String>) -> Self {
        let es_path = es_path
            .or_else(|| std::env::var("ESKIT_ES_PATH").ok())
            .or_else(|| find_executable("es.exe"))
            .or_else(|| find_executable("es"));
        let instance = instance.or_else(|| std::env::var("ESKIT_ES_INSTANCE").ok());
        Self { es_path, timeout_secs, instance }
    }

    pub fn require(&self) -> Result<String, EsError> {
        self.es_path.clone().ok_or_else(|| EsError {
            message: "Cannot find es.exe. Install Everything CLI or set ESKIT_ES_PATH.".to_string(),
            result: None,
        })
    }

    pub fn run_raw(&self, args: &[String]) -> Result<CommandResult, EsError> {
        let exe = self.require()?;
        let mut cmd_vec = vec![exe.clone()];
        if let Some(instance) = &self.instance {
            cmd_vec.push("-instance".to_string());
            cmd_vec.push(instance.clone());
        }
        cmd_vec.extend(args.iter().cloned());
        let start = Instant::now();
        let output = Command::new(&exe)
            .args(&cmd_vec[1..])
            .output()
            .map_err(|err| EsError { message: format!("failed to run es.exe: {err}"), result: None })?;
        let elapsed_ms = start.elapsed().as_millis();
        let result = CommandResult {
            ok: output.status.success(),
            command: cmd_vec,
            returncode: output.status.code().unwrap_or(-1),
            stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
            elapsed_ms,
        };
        Ok(result)
    }

    pub fn search_paths(
        &self,
        terms: &[String],
        limit: usize,
        sort: Option<&str>,
        files_only: bool,
        folders_only: bool,
    ) -> Result<(Vec<String>, CommandResult), EsError> {
        let mut args = vec!["-full-path-and-name".to_string(), "-n".to_string(), limit.to_string()];
        if let Some(sort) = sort {
            args.push("-sort".to_string());
            args.push(sort.to_string());
        }
        if files_only {
            args.push("file:".to_string());
        }
        if folders_only {
            args.push("folder:".to_string());
        }
        args.extend(terms.iter().filter(|t| !t.trim().is_empty()).cloned());
        let raw = self.run_raw(&args)?;
        if !raw.ok {
            return Err(EsError { message: "es.exe returned a non-zero exit code".to_string(), result: Some(raw) });
        }
        let paths = unique_lines(raw.stdout.lines().map(|s| s.to_string()).collect());
        Ok((paths, raw))
    }
}

fn unique_lines(lines: Vec<String>) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for line in lines {
        let text = line.trim().to_string();
        if text.is_empty() { continue; }
        let key = text.to_ascii_lowercase();
        if seen.insert(key) { out.push(text); }
    }
    out
}

pub fn token_to_exts(token: &str) -> Vec<String> {
    let mut raw = token.trim().trim_matches('"').trim_matches('\'').to_string();
    if raw.is_empty() { return vec![]; }
    if raw.starts_with("*.") { raw = raw[1..].to_string(); }
    if !raw.starts_with('.') { return vec![]; }
    if raw.contains('/') || raw.contains('\\') { return vec![]; }
    raw.replace(',', ";")
        .split(';')
        .map(|s| s.trim().trim_start_matches("*.").trim_start_matches('.').to_ascii_lowercase())
        .filter(|s| !s.is_empty())
        .map(|s| if s == "jpeg" { "jpg".to_string() } else { s })
        .fold(Vec::new(), |mut acc, item| { if !acc.contains(&item) { acc.push(item); } acc })
}

fn split_query_terms(query: &str) -> Vec<String> {
    let q = query.trim();
    if q.is_empty() { return vec![]; }
    q.split_whitespace().map(|s| s.to_string()).collect()
}

pub fn build_find_terms(query: &str, path: Option<&str>, exts: &[String], ext_mode: &str) -> Vec<String> {
    let mut terms = Vec::new();
    if let Some(path) = path {
        terms.push(to_everything_path(path));
    }
    terms.extend(split_query_terms(query));
    if !exts.is_empty() {
        if ext_mode == "glob" && exts.len() == 1 {
            terms.push(format!("*.{}", exts[0]));
        } else {
            terms.push(format!("ext:{}", exts.join(";")));
        }
    }
    terms.into_iter().filter(|t| !t.trim().is_empty()).collect()
}

fn display_expr(terms: &[String]) -> String { terms.join(" ") }

fn result_response(action: &str, query: &str, paths: Vec<String>, verify: bool, meta: serde_json::Value) -> EsKitResponse {
    let results: Vec<SearchResult> = paths.into_iter().map(|p| SearchResult::from_path(p, verify)).collect();
    EsKitResponse {
        ok: true,
        action: action.to_string(),
        query: query.to_string(),
        count: results.len(),
        results,
        warnings: Vec::new(),
        meta,
    }
}

pub fn run_find_attempt(
    client: &EsClient,
    action: &str,
    query: &str,
    path: Option<&str>,
    exts: &[String],
    limit: usize,
    verify: bool,
    files_only: bool,
    folders_only: bool,
    ext_mode: &str,
    es_sort: Option<&str>,
) -> Result<EsKitResponse, EsError> {
    let terms = build_find_terms(query, path, exts, ext_mode);
    let expr = display_expr(&terms);
    let (paths, raw) = client.search_paths(&terms, limit, es_sort, files_only, folders_only)?;
    Ok(result_response(
        action,
        &expr,
        paths,
        verify,
        json!({"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "search_terms": terms}),
    ))
}

pub fn smart_find(
    client: &EsClient,
    tokens: &[String],
    path: Option<&str>,
    exts: &[String],
    limit: usize,
    verify: bool,
    files_only: bool,
    folders_only: bool,
    fuzzy: FuzzyMode,
    candidate_limit: usize,
    es_sort: Option<&str>,
) -> Result<EsKitResponse, EsError> {
    let query = if tokens.is_empty() { "*".to_string() } else { tokens.join(" ") };
    let mut attempts = Vec::new();

    let first = run_find_attempt(client, "search", &query, path, exts, limit, verify, files_only, folders_only, "ext", es_sort)?;
    attempts.push(first.meta.clone());
    if first.count > 0 {
        let mut resp = first;
        resp.meta = json!({"attempts": attempts});
        return Ok(resp);
    }

    let fallback = if exts.len() == 1 {
        let fb = run_find_attempt(client, "search", &query, path, exts, limit, verify, files_only, folders_only, "glob", es_sort)?;
        attempts.push(fb.meta.clone());
        fb
    } else {
        first
    };
    if fallback.count > 0 {
        let mut resp = fallback;
        resp.meta = json!({"attempts": attempts});
        return Ok(resp);
    }

    let should_fuzzy = match fuzzy {
        FuzzyMode::Off => false,
        FuzzyMode::On => true,
        FuzzyMode::Auto => query.trim() != "*" && (!exts.is_empty() || path.map(|p| p.len() > 3).unwrap_or(false)),
    };
    if !should_fuzzy {
        let mut resp = fallback;
        resp.meta = json!({"attempts": attempts, "fuzzy": "skipped"});
        return Ok(resp);
    }

    let candidate_terms = build_find_terms("*", path, exts, "ext");
    let (candidates, raw) = client.search_paths(&candidate_terms, candidate_limit, es_sort, files_only, folders_only)?;
    let filtered = sort_paths_listary(&query, candidates).into_iter().take(limit).collect::<Vec<_>>();
    let expr = format!("{} [listary-fuzzy over {}]", query, display_expr(&candidate_terms));
    let mut resp = result_response(
        "search",
        &expr,
        filtered,
        verify,
        json!({"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "search_terms": candidate_terms, "mode": "listary-fuzzy"}),
    );
    attempts.push(resp.meta.clone());
    resp.meta = json!({"attempts": attempts, "fuzzy": "listary"});
    Ok(resp)
}

#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum FuzzyMode { Auto, On, Off }
