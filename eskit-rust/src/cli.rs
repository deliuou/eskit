use serde_json::json;
use std::cmp::Ordering;
use std::collections::HashSet;
use std::io::IsTerminal;

use crate::actions::{run_action, ActionKind};
use crate::es::{smart_find, EsClient, FuzzyMode};
use crate::formatters::{enrich_for_stats_or_sort, print_count, print_json, print_ndjson, print_stats, print_table, write_export};
use crate::grammar::{parse_search_tokens, SearchSpec};
use crate::models::{EsKitResponse, SearchResult};
use crate::selector::select_and_act;
use crate::util::{basename, extension, is_wsl, split_drive_alias, to_local_path, to_windows_path, windows_process_running, which_es_default_hint, VERSION};

#[derive(Debug, Clone)]
struct Options {
    tokens: Vec<String>,
    limit: usize,
    candidate_limit: usize,
    top: Option<usize>,
    sort: Option<String>,
    order: Option<String>,
    json: bool,
    ndjson: bool,
    table: bool,
    no_select: bool,
    count: bool,
    stats: bool,
    debug: bool,
    verify: bool,
    files: bool,
    folders: bool,
    fuzzy: FuzzyMode,
    export: Option<String>,
    index: usize,
    action: Option<ActionKind>,
    copy_to: Option<String>,
    es_path: Option<String>,
    instance: Option<String>,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            tokens: Vec::new(),
            limit: 80,
            candidate_limit: 5000,
            top: None,
            sort: None,
            order: None,
            json: false,
            ndjson: false,
            table: false,
            no_select: false,
            count: false,
            stats: false,
            debug: false,
            verify: false,
            files: false,
            folders: false,
            fuzzy: FuzzyMode::Auto,
            export: None,
            index: 1,
            action: None,
            copy_to: None,
            es_path: None,
            instance: None,
        }
    }
}

pub fn run() -> Result<u8, Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        print_short_help();
        return Ok(0);
    }
    match args[0].as_str() {
        "--help" | "-h" => { print_short_help(); Ok(0) }
        "--help-full" | "help-full" => { print_full_help(); Ok(0) }
        "--version" | "-V" | "version" => { println!("eskit {VERSION}"); Ok(0) }
        "doctor" => { doctor(&args[1..])?; Ok(0) }
        "path" => { path_cmd(&args[1..])?; Ok(0) }
        _ => { search(args)?; Ok(0) }
    }
}

fn parse_options(args: Vec<String>) -> Result<Options, Box<dyn std::error::Error>> {
    let mut opts = Options::default();
    let mut i = 0usize;
    while i < args.len() {
        let arg = &args[i];
        if !arg.starts_with('-') || arg == "-" || is_negative_number(arg) {
            opts.tokens.push(arg.clone());
            i += 1;
            continue;
        }
        match arg.as_str() {
            "--limit" | "-n" => { i += 1; opts.limit = need_value(&args, i, arg)?.parse()?; }
            "--candidate-limit" => { i += 1; opts.candidate_limit = need_value(&args, i, arg)?.parse()?; }
            "--top" => { i += 1; opts.top = Some(need_value(&args, i, arg)?.parse()?); }
            "--sort" => { i += 1; opts.sort = Some(need_value(&args, i, arg)?.to_string()); }
            "--asc" => opts.order = Some("asc".to_string()),
            "--desc" => opts.order = Some("desc".to_string()),
            "--json" => opts.json = true,
            "--ndjson" => opts.ndjson = true,
            "--table" => opts.table = true,
            "--no-select" => opts.no_select = true,
            "--count" => opts.count = true,
            "--stats" => opts.stats = true,
            "--debug" => opts.debug = true,
            "--verify" => opts.verify = true,
            "--files" | "--file" => opts.files = true,
            "--folders" | "--dirs" | "--folder" | "--dir" => opts.folders = true,
            "--fuzzy" => opts.fuzzy = FuzzyMode::On,
            "--no-fuzzy" => opts.fuzzy = FuzzyMode::Off,
            "--export" => { i += 1; opts.export = Some(need_value(&args, i, arg)?.to_string()); }
            "--index" => { i += 1; opts.index = need_value(&args, i, arg)?.parse()?; }
            "--open" => opts.action = Some(ActionKind::Open),
            "--reveal" => opts.action = Some(ActionKind::Reveal),
            "--copy-path" => opts.action = Some(ActionKind::CopyPath),
            "--copy-name" => opts.action = Some(ActionKind::CopyName),
            "--copy-to" => { i += 1; opts.action = Some(ActionKind::CopyTo); opts.copy_to = Some(need_value(&args, i, arg)?.to_string()); }
            "--path" => { i += 1; opts.tokens.insert(0, need_value(&args, i, arg)?.to_string()); }
            "--ext" => { i += 1; opts.tokens.push(format!(".{}", need_value(&args, i, arg)?.trim_start_matches('.'))); }
            "--es-path" => { i += 1; opts.es_path = Some(need_value(&args, i, arg)?.to_string()); }
            "--instance" => { i += 1; opts.instance = Some(need_value(&args, i, arg)?.to_string()); }
            _ => return Err(format!("unknown option: {arg}").into()),
        }
        i += 1;
    }
    Ok(opts)
}

fn is_negative_number(s: &str) -> bool { s.starts_with('-') && s[1..].chars().all(|c| c.is_ascii_digit()) }
fn need_value<'a>(args: &'a [String], i: usize, flag: &str) -> Result<&'a str, Box<dyn std::error::Error>> {
    args.get(i).map(|s| s.as_str()).ok_or_else(|| format!("{flag} requires a value").into())
}

fn search(args: Vec<String>) -> Result<(), Box<dyn std::error::Error>> {
    let opts = parse_options(args)?;
    let spec = parse_search_tokens(&opts.tokens);
    let mut resp = run_search_spec(&spec, &opts)?;

    let needs_meta = opts.verify || opts.stats || matches!(opts.sort.as_deref(), Some("size") | Some("modified"));
    if needs_meta { enrich_for_stats_or_sort(&mut resp.results); }

    apply_sort_and_top(&mut resp, &opts);

    if opts.debug { println!("{}", serde_json::to_string_pretty(&resp.meta)?); }
    if opts.count { print_count(&resp); return Ok(()); }
    if opts.stats { print_stats(&resp); return Ok(()); }
    if opts.json { print_json(&resp)?; return Ok(()); }
    if opts.ndjson { print_ndjson(&resp)?; return Ok(()); }
    if let Some(path) = &opts.export { write_export(&resp, path)?; return Ok(()); }

    if let Some(action) = opts.action {
        let idx = opts.index.saturating_sub(1);
        let item = resp.results.get(idx).ok_or_else(|| format!("--index {} out of range; result count = {}", opts.index, resp.results.len()))?;
        run_action(action, &item.path, opts.copy_to.as_deref())?;
        return Ok(());
    }

    if opts.table || opts.no_select || !std::io::stdout().is_terminal() {
        print_table(&resp, None);
    } else {
        select_and_act(&resp.results)?;
    }
    Ok(())
}

fn run_search_spec(spec: &SearchSpec, opts: &Options) -> Result<EsKitResponse, Box<dyn std::error::Error>> {
    let client = EsClient::new(opts.es_path.clone(), 30, opts.instance.clone());
    let search_tokens = if spec.name_tokens.is_empty() { vec!["*".to_string()] } else { spec.name_tokens.clone() };
    let roots: Vec<Option<String>> = if spec.roots.is_empty() { vec![None] } else { spec.roots.iter().cloned().map(Some).collect() };

    let (include_files, include_folders) = if opts.files {
        (true, false)
    } else if opts.folders {
        (false, true)
    } else if !spec.kinds.is_empty() {
        (spec.kinds.iter().any(|k| k == "file"), spec.kinds.iter().any(|k| k == "folder"))
    } else {
        (true, true)
    };

    let ext_groups: Vec<Vec<String>> = if spec.exts.len() > 1 {
        spec.exts.iter().map(|e| vec![e.clone()]).collect()
    } else {
        vec![spec.exts.clone()]
    };

    let es_sort = es_sort_hint(opts.sort.as_deref());
    let mut responses = Vec::new();
    for root in roots {
        if include_files {
            for ext_group in &ext_groups {
                let files_only = !ext_group.is_empty() || !include_folders || spec.kinds.iter().any(|k| k == "file");
                let mut r = smart_find(
                    &client,
                    &search_tokens,
                    root.as_deref(),
                    ext_group,
                    opts.limit.max(opts.top.unwrap_or(0)),
                    opts.verify,
                    files_only,
                    false,
                    opts.fuzzy,
                    opts.candidate_limit,
                    es_sort,
                )?;
                if files_only { set_kind_hint(&mut r, "file"); }
                responses.push(r);
            }
        }
        if include_folders && (spec.kinds.iter().any(|k| k == "folder") || opts.folders) && !opts.files {
            let mut r = smart_find(
                &client,
                &search_tokens,
                root.as_deref(),
                &[],
                opts.limit.max(opts.top.unwrap_or(0)),
                opts.verify,
                false,
                true,
                opts.fuzzy,
                opts.candidate_limit,
                es_sort,
            )?;
            set_kind_hint(&mut r, "folder");
            responses.push(r);
        }
    }
    Ok(combine_responses(responses, spec, opts))
}

fn set_kind_hint(resp: &mut EsKitResponse, kind: &str) {
    for item in &mut resp.results {
        if item.kind == "unknown" { item.kind = kind.to_string(); }
    }
}

fn combine_responses(responses: Vec<EsKitResponse>, spec: &SearchSpec, opts: &Options) -> EsKitResponse {
    let mut seen = HashSet::new();
    let mut results = Vec::new();
    let mut warnings = Vec::new();
    let mut attempts = Vec::new();
    let mut queries = Vec::new();
    for resp in responses {
        queries.push(resp.query.clone());
        warnings.extend(resp.warnings);
        attempts.push(resp.meta);
        for item in resp.results {
            let key = item.path.to_ascii_lowercase();
            if seen.insert(key) { results.push(item); }
        }
    }
    EsKitResponse {
        ok: true,
        action: "search".to_string(),
        query: queries.into_iter().filter(|q| !q.is_empty()).collect::<Vec<_>>().join(" | "),
        count: results.len(),
        results,
        warnings,
        meta: json!({
            "grammar": {
                "roots": spec.roots,
                "file_types": spec.exts,
                "kinds": spec.kinds,
                "filename_tokens": spec.name_tokens,
                "raw_tokens": spec.raw_tokens,
            },
            "attempts": attempts,
            "options": {
                "limit": opts.limit,
                "top": opts.top,
                "sort": opts.sort,
                "fuzzy": format!("{:?}", opts.fuzzy),
            }
        }),
    }
}

fn es_sort_hint(sort: Option<&str>) -> Option<&'static str> {
    match sort {
        Some("size") => Some("size-descending"),
        Some("modified") | Some("date") | Some("dm") => Some("date-modified-descending"),
        Some("name") => Some("name-ascending"),
        Some("path") => Some("path-ascending"),
        _ => None,
    }
}

fn apply_sort_and_top(resp: &mut EsKitResponse, opts: &Options) {
    if let Some(sort) = opts.sort.as_deref() {
        let desc = match opts.order.as_deref() {
            Some("asc") => false,
            Some("desc") => true,
            _ => matches!(sort, "size" | "modified" | "date" | "dm"),
        };
        resp.results.sort_by(|a, b| compare_results(a, b, sort));
        if desc { resp.results.reverse(); }
    }
    if let Some(top) = opts.top {
        resp.results.truncate(top);
    }
    resp.count = resp.results.len();
}

fn compare_results(a: &SearchResult, b: &SearchResult, sort: &str) -> Ordering {
    match sort {
        "name" => basename(&a.path).to_ascii_lowercase().cmp(&basename(&b.path).to_ascii_lowercase()),
        "path" => a.path.to_ascii_lowercase().cmp(&b.path.to_ascii_lowercase()),
        "ext" => extension(&a.path).unwrap_or_default().to_ascii_lowercase().cmp(&extension(&b.path).unwrap_or_default().to_ascii_lowercase()),
        "size" => a.size.unwrap_or(0).cmp(&b.size.unwrap_or(0)),
        "modified" | "date" | "dm" => a.modified_unix.unwrap_or(0).cmp(&b.modified_unix.unwrap_or(0)),
        _ => a.path.to_ascii_lowercase().cmp(&b.path.to_ascii_lowercase()),
    }
}

fn doctor(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let mut es_path = None;
    let mut instance = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--es-path" => { i += 1; es_path = Some(need_value(args, i, "--es-path")?.to_string()); }
            "--instance" => { i += 1; instance = Some(need_value(args, i, "--instance")?.to_string()); }
            "--help" | "-h" => { println!("Usage: eskit doctor [--es-path PATH] [--instance 1.5a]"); return Ok(()); }
            other => return Err(format!("unknown doctor option: {other}").into()),
        }
        i += 1;
    }
    let client = EsClient::new(es_path, 30, instance);
    println!("eskit doctor");
    println!("- version: {VERSION}");
    println!("- os: {}", std::env::consts::OS);
    println!("- wsl: {}", is_wsl());
    println!("- es.exe: {}", client.es_path.clone().unwrap_or_else(|| "NOT FOUND".to_string()));
    println!("- Everything process: {}", windows_process_running("Everything"));
    if client.es_path.is_none() {
        println!("\nSet es.exe path, for example:\n  {}", which_es_default_hint());
        return Ok(());
    }
    let args = vec!["-n".to_string(), "1".to_string(), "*".to_string()];
    match client.run_raw(&args) {
        Ok(raw) if raw.ok => println!("- es.exe query: OK ({} ms)", raw.elapsed_ms),
        Ok(raw) => {
            println!("- es.exe query: FAIL");
            println!("  returncode: {}", raw.returncode);
            if !raw.stderr.trim().is_empty() { println!("  stderr: {}", raw.stderr.trim()); }
            if raw.returncode == 8 {
                println!("\nError 8 usually means Everything GUI/search client is not running on Windows.");
            }
        }
        Err(err) => println!("- es.exe query: ERROR: {err}"),
    }
    Ok(())
}

fn path_cmd(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    if args.is_empty() || args[0] == "--help" || args[0] == "-h" {
        println!("Usage: eskit path <d|d/Projects|/mnt/d/Projects|D:\\Projects>");
        return Ok(());
    }
    let input = &args[0];
    println!("input:   {input}");
    println!("windows: {}", to_windows_path(input).unwrap_or_else(|| input.to_string()));
    println!("local:   {}", to_local_path(input));
    if let Some((drive, rest)) = split_drive_alias(input) {
        println!("drive:   {}:", drive);
        println!("rest:    {}", rest);
    }
    Ok(())
}

fn print_short_help() {
    println!(r#"eskit {}

用法:
  eskit [盘符/路径 ...] [文件类型 ...] [文件名 ...] [处理参数]

例子:
  eskit .pdf ODL
  eskit d f .pdf .pptx ODL
  eskit d folder ODL
  eskit d .jpg screenshot --sort modified --top 20
  eskit d .pdf ODL --copy-path --index 2

筛选:
  d f                 搜索 D: 和 F:
  d/Projects          搜索 D:\Projects
  /mnt/d/Projects     等价于 D:\Projects
  .pdf .pptx          多文件类型
  folder / dir / 目录  搜索文件夹
  --files / --folders 文件/文件夹筛选

处理:
  --sort name|path|ext|size|modified   --asc / --desc   --top N
  --count   --stats   --json   --ndjson   --export out.md|csv|json
  --open   --reveal   --copy-path   --copy-name   --copy-to DIR   --index N
  --table  --no-select  --debug  --verify

其他:
  eskit doctor
  eskit path d/Projects
  eskit --help-full
"#, VERSION);
}

fn print_full_help() {
    println!(r#"eskit-rust: WSL 中搜索 Windows 文件的 Everything/es.exe 友好包装器

核心语法:
  eskit [盘符/路径 ...] [文件类型 ...] [文件名关键词 ...] [对结果的处理]

路径写法:
  d                 -> D:\
  f                 -> F:\
  d/Projects        -> D:\Projects
  /mnt/d/Projects   -> D:\Projects
  D:/Projects       -> D:\Projects

搜索例子:
  eskit .pdf ODL
  eskit d .pdf ODL
  eskit d f .pdf .pptx ODL
  eskit d folder ODL
  eskit d folder .pdf ODL
  eskit d .jpg .png screenshot --sort modified --top 20

搜索后的键盘选择:
  普通搜索在真实终端中会进入轻量选择器。
  ↑/↓ 选择，→ 更多操作，Enter 执行，Esc 退出。
  只想表格输出时使用 --table 或 --no-select。

动作:
  --open             打开第 N 个结果，默认 N=1
  --reveal           在资源管理器中定位
  --copy-path        复制完整路径
  --copy-name        复制文件名
  --copy-to DIR      复制文件到目录
  --index N          指定第 N 个结果

排序/统计:
  --sort name|path|ext|size|modified
  --asc / --desc
  --top N
  --count
  --stats

脚本输出:
  --json
  --ndjson
  --export result.md|result.csv|result.json|result.txt

模糊匹配:
  默认在有文件类型或具体路径时启用 Listary 风格候选扫描。
  --fuzzy      强制启用
  --no-fuzzy   禁用

Everything 相关:
  Windows 端必须安装并运行 Everything，且 es.exe 可用。
  WSL 中可以设置:
    export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe

官方地址:
  Everything: https://www.voidtools.com/
  Downloads:  https://www.voidtools.com/downloads/
  ES docs:    https://www.voidtools.com/support/everything/command_line_interface/
  ES GitHub:  https://github.com/voidtools/ES
"#);
}
