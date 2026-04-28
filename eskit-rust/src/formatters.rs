use chrono::{Local, TimeZone};
use std::collections::BTreeMap;
use std::io::Write;
use std::path::Path;

use crate::models::{EsKitResponse, SearchResult};
use crate::util::{basename, extension, ensure_parent, normalize_export_path, split_drive_alias};

pub fn print_table(resp: &EsKitResponse, limit: Option<usize>) {
    let max = limit.unwrap_or(resp.results.len());
    println!("eskit search: {} result(s)", resp.count);
    println!("{:<5} {:<8} {:>12} {:<19} {}", "#", "Kind", "Size", "Modified", "Path");
    println!("{}", "-".repeat(100));
    for (idx, item) in resp.results.iter().take(max).enumerate() {
        println!(
            "{:<5} {:<8} {:>12} {:<19} {}",
            idx + 1,
            item.kind,
            format_size(item.size),
            format_time(item.modified_unix),
            item.path
        );
    }
}

pub fn print_json(resp: &EsKitResponse) -> Result<(), Box<dyn std::error::Error>> {
    println!("{}", serde_json::to_string_pretty(resp)?);
    Ok(())
}

pub fn print_ndjson(resp: &EsKitResponse) -> Result<(), Box<dyn std::error::Error>> {
    for item in &resp.results {
        println!("{}", serde_json::to_string(item)?);
    }
    Ok(())
}

pub fn write_export(resp: &EsKitResponse, path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let p = normalize_export_path(path);
    ensure_parent(&p)?;
    let ext = p.extension().and_then(|s| s.to_str()).unwrap_or("txt").to_ascii_lowercase();
    match ext.as_str() {
        "json" => std::fs::write(&p, serde_json::to_string_pretty(resp)?)?,
        "ndjson" | "jsonl" => {
            let mut f = std::fs::File::create(&p)?;
            for item in &resp.results {
                writeln!(f, "{}", serde_json::to_string(item)?)?;
            }
        }
        "csv" => write_csv(resp, &p)?,
        "md" | "markdown" => std::fs::write(&p, to_markdown(resp))?,
        _ => std::fs::write(&p, resp.results.iter().map(|r| r.path.clone()).collect::<Vec<_>>().join("\n"))?,
    }
    println!("exported: {}", p.display());
    Ok(())
}

fn write_csv(resp: &EsKitResponse, path: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let mut wtr = csv::Writer::from_path(path)?;
    wtr.write_record(["index", "kind", "size", "modified_unix", "path"])?;
    for (i, r) in resp.results.iter().enumerate() {
        wtr.write_record([
            (i + 1).to_string(),
            r.kind.clone(),
            r.size.map(|v| v.to_string()).unwrap_or_default(),
            r.modified_unix.map(|v| v.to_string()).unwrap_or_default(),
            r.path.clone(),
        ])?;
    }
    wtr.flush()?;
    Ok(())
}

fn to_markdown(resp: &EsKitResponse) -> String {
    let mut s = String::new();
    s.push_str(&format!("# eskit search report\n\n"));
    s.push_str(&format!("- Query: `{}`\n", resp.query));
    s.push_str(&format!("- Count: {}\n\n", resp.count));
    s.push_str("| # | Kind | Size | Modified | Path |\n|---:|---|---:|---|---|\n");
    for (i, r) in resp.results.iter().enumerate() {
        s.push_str(&format!("| {} | {} | {} | {} | `{}` |\n", i + 1, r.kind, format_size(r.size), format_time(r.modified_unix), r.path.replace('|', "\\|")));
    }
    s
}

pub fn print_stats(resp: &EsKitResponse) {
    let stats = response_stats(resp);
    println!("Count: {}", stats.count);
    println!("Total size: {}", format_size(Some(stats.total_size)));
    println!("Files: {}", stats.files);
    println!("Folders: {}", stats.folders);
    println!("Unknown: {}", stats.unknown);
    println!();
    print_map("Extensions", &stats.exts);
    print_map("Drives", &stats.drives);
}

fn print_map(title: &str, map: &BTreeMap<String, usize>) {
    println!("{title}:");
    if map.is_empty() {
        println!("  -");
    } else {
        for (k, v) in map {
            println!("  {:<10} {}", k, v);
        }
    }
}

#[derive(Debug)]
pub struct Stats {
    pub count: usize,
    pub total_size: u64,
    pub files: usize,
    pub folders: usize,
    pub unknown: usize,
    pub exts: BTreeMap<String, usize>,
    pub drives: BTreeMap<String, usize>,
}

pub fn response_stats(resp: &EsKitResponse) -> Stats {
    let mut s = Stats { count: resp.results.len(), total_size: 0, files: 0, folders: 0, unknown: 0, exts: BTreeMap::new(), drives: BTreeMap::new() };
    for r in &resp.results {
        if let Some(size) = r.size { s.total_size += size; }
        match r.kind.as_str() {
            "file" => s.files += 1,
            "folder" => s.folders += 1,
            _ => s.unknown += 1,
        }
        let ext = extension(&r.path).unwrap_or_else(|| "[no-ext]".to_string()).to_ascii_lowercase();
        *s.exts.entry(ext).or_insert(0) += 1;
        if let Some((drive, _)) = split_drive_alias(&r.path) {
            *s.drives.entry(format!("{}:", drive)).or_insert(0) += 1;
        }
    }
    s
}

pub fn format_size(size: Option<u64>) -> String {
    let Some(n) = size else { return "-".to_string(); };
    let units = ["B", "KB", "MB", "GB", "TB"];
    let mut value = n as f64;
    let mut unit = 0;
    while value >= 1024.0 && unit < units.len() - 1 {
        value /= 1024.0;
        unit += 1;
    }
    if unit == 0 { format!("{} {}", n, units[unit]) } else { format!("{:.1} {}", value, units[unit]) }
}

pub fn format_time(ts: Option<i64>) -> String {
    match ts.and_then(|v| Local.timestamp_opt(v, 0).single()) {
        Some(dt) => dt.format("%Y-%m-%d %H:%M").to_string(),
        None => "-".to_string(),
    }
}

pub fn print_count(resp: &EsKitResponse) { println!("{}", resp.count); }

pub fn enrich_for_stats_or_sort(results: &mut [SearchResult]) {
    for r in results {
        if r.kind == "unknown" || r.size.is_none() || r.modified_unix.is_none() {
            r.populate_metadata();
        }
    }
}
