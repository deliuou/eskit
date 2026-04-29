from __future__ import annotations

import sys
from pathlib import PureWindowsPath
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .actions import copy_file_to, copy_text_to_clipboard, open_path, reveal_in_file_manager
from .es import EsClient
from .es import duplicates_by_name as es_duplicates_by_name
from .es import empty as es_empty
from .es import find as es_find
from .es import large as es_large
from .es import recent as es_recent
from .es import smart_find as es_smart_find
from .exporters import project_report, save_project_report
from .formatters import print_response, print_stats, response_stats, write_export
from .grammar import SearchSpec, parse_search_tokens
from .listary import listary_results
from .models import EsKitResponse, SearchResult
from .safety import is_dangerous_root, remove_empty_folders
from .util import display_path_equivalence, is_wsl, json_dumps, platform_info, windows_process_running

app = typer.Typer(
    name="eskit",
    help=(
        "Everything/es.exe friendly CLI. Main grammar: "
        "eskit [drive/path ...] [file-type ...] [filename ...] [action options]."
    ),
    no_args_is_help=False,
)
console = Console()


# ----------------------------- common helpers -----------------------------

def _client(es_path: Optional[str] = None, timeout: int = 30, instance: Optional[str] = None) -> EsClient:
    return EsClient(es_path=es_path, timeout=timeout, instance=instance)


def _handle_error(exc: Exception, json_out: bool = False) -> None:
    if json_out:
        console.print(json_dumps({"ok": False, "error": str(exc), "type": exc.__class__.__name__}))
    else:
        console.print(f"[red]ERROR:[/] {exc}")
    raise typer.Exit(code=2)


def _print_debug(payload: dict) -> None:
    if payload:
        console.print(Panel(json_dumps(payload), title="Debug", border_style="cyan"))


def _basename(path: str) -> str:
    text = path.rstrip('\\/')
    # Windows paths can arrive while running in WSL/Linux.
    if ':\\' in text or '\\' in text:
        return PureWindowsPath(text).name
    return text.replace('\\', '/').rsplit('/', 1)[-1]


def _combine_responses(responses: list[EsKitResponse], *, spec: SearchSpec, limit: int, verify: bool) -> EsKitResponse:
    if not responses:
        return EsKitResponse(
            ok=True,
            action="search",
            query=spec.query,
            count=0,
            results=[],
            warnings=[],
            meta={"grammar": spec.__dict__},
        )

    seen: set[str] = set()
    results: list[SearchResult] = []
    warnings: list[str] = []
    attempts: list[dict] = []
    queries: list[str] = []
    for resp in responses:
        queries.append(resp.query or "")
        warnings.extend(resp.warnings)
        attempts.extend(resp.meta.get("attempts", []))
        if "raw_command" in resp.meta:
            attempts.append(
                {
                    "mode": resp.action,
                    "query": resp.query,
                    "count": resp.count,
                    "raw_command": resp.meta.get("raw_command"),
                    "elapsed_ms": resp.meta.get("elapsed_ms"),
                }
            )
        for item in resp.results:
            key = item.path.casefold()
            if key in seen:
                continue
            seen.add(key)
            results.append(item if verify else SearchResult.from_path(item.path, verify=False))

    return EsKitResponse(
        ok=True,
        action="search",
        query=" | ".join(q for q in queries if q),
        count=len(results),
        results=results,
        warnings=warnings,
        meta={
            "grammar": {
                "roots": spec.roots,
                "file_types": spec.exts,
                "kinds": spec.kinds,
                "filename_tokens": spec.name_tokens,
                "raw_tokens": spec.raw_tokens,
            },
            "attempts": attempts,
        },
    )


def _set_kind_hint(response: EsKitResponse, kind: str | None) -> EsKitResponse:
    """Fill result kind without filesystem stat when the search query already guarantees it."""
    if kind:
        for item in response.results:
            if not item.kind or item.kind == "unknown":
                item.kind = kind
    return response


def _run_search_spec(
    spec: SearchSpec,
    *,
    limit: int,
    candidate_limit: int,
    verify: bool,
    files_only: bool,
    folders_only: bool,
    fuzzy: str | bool,
    es_path: Optional[str],
    instance: Optional[str] = None,
    es_sort: Optional[str] = None,
) -> EsKitResponse:
    client = _client(es_path, instance=instance)
    # smart_find expects extension tokens in the token stream and extra extensions separately.
    search_tokens = spec.name_tokens or ["*"]
    roots = spec.roots or [None]

    if files_only and folders_only:
        raise RuntimeError("--files-only and --folders-only cannot be used together.")

    # Kind grammar:
    #   folder / dir / 目录 / 文件夹 -> folders only
    #   file / 文件                 -> files only
    #   .pdf .pptx                  -> files of those types
    #   folder .pdf ODL             -> folders named ODL plus PDF files named ODL
    if files_only:
        include_files, include_folders = True, False
    elif folders_only:
        include_files, include_folders = False, True
    elif spec.kinds:
        include_files = "file" in spec.kinds
        include_folders = "folder" in spec.kinds
    else:
        include_files, include_folders = True, True

    # Query each extension separately when several file types are supplied.
    # This makes `eskit d f .pdf .pptx ODL` robust even on Everything/es.exe
    # setups where `ext:pdf;pptx` does not return all extensions consistently.
    if len(spec.exts) > 1:
        ext_groups: list[list[str]] = [[ext] for ext in spec.exts]
    else:
        ext_groups = [spec.exts]

    responses: list[EsKitResponse] = []
    for root in roots:
        # File branch: extension filters apply to files.
        if include_files:
            for ext_group in ext_groups:
                resp = es_smart_find(
                    client,
                    search_tokens,
                    root,
                    ext_group,
                    limit,
                    verify,
                    True if (ext_group or not include_folders or "file" in spec.kinds) else False,
                    False,
                    listary=fuzzy,
                    candidate_limit=candidate_limit,
                    es_sort=es_sort,
                )
                responses.append(_set_kind_hint(resp, "file" if ext_group or not include_folders or "file" in spec.kinds else None))

        # Folder branch: extension filters do not apply to folders, so we run a
        # separate folder-only search with no ext filters whenever the grammar
        # explicitly asks for folders.
        if include_folders and ("folder" in spec.kinds or folders_only) and not files_only:
            resp = es_smart_find(
                client,
                search_tokens,
                root,
                [],
                limit,
                verify,
                False,
                True,
                listary=fuzzy,
                candidate_limit=candidate_limit,
                es_sort=es_sort,
            )
            responses.append(_set_kind_hint(resp, "folder"))

    combined = _combine_responses(responses, spec=spec, limit=limit, verify=verify)
    combined.meta["kind_filter"] = {"include_files": include_files, "include_folders": include_folders}
    return combined



def _selected_result(response: EsKitResponse, index: int) -> SearchResult:
    if not response.results:
        raise RuntimeError("No results to process.")
    if index < 1 or index > len(response.results):
        raise RuntimeError(f"--index {index} is out of range. Valid range: 1..{len(response.results)}")
    return response.results[index - 1]


def _apply_result_action(
    response: EsKitResponse,
    *,
    index: int,
    open_result: bool,
    reveal_result: bool,
    copy_path_result: bool,
    copy_name_result: bool,
    copy_to: Optional[str],
    json_out: bool,
) -> bool:
    actions = [open_result, reveal_result, copy_path_result, copy_name_result, bool(copy_to)]
    if sum(bool(x) for x in actions) == 0:
        return False
    if sum(bool(x) for x in actions) > 1:
        raise RuntimeError("Choose only one result action: --open, --reveal, --copy-path, --copy-name, or --copy-to.")

    item = _selected_result(response, index)
    payload: dict = {"ok": True, "index": index, "path": item.path}
    if open_result:
        open_path(item.path)
        payload["action"] = "open"
    elif reveal_result:
        reveal_in_file_manager(item.path)
        payload["action"] = "reveal"
    elif copy_path_result:
        copy_text_to_clipboard(item.path)
        payload["action"] = "copy-path"
        payload["copied"] = item.path
    elif copy_name_result:
        name = _basename(item.path)
        copy_text_to_clipboard(name)
        payload["action"] = "copy-name"
        payload["copied"] = name
    elif copy_to:
        final = copy_file_to(item.path, copy_to)
        payload["action"] = "copy-to"
        payload["destination"] = final

    if json_out:
        console.print(json_dumps({"ok": True, "result_action": payload, "search": response.to_dict()}))
    else:
        console.print(f"[green]Done:[/] {payload['action']} -> {item.path}")
    return True


def _print_or_export(response: EsKitResponse, *, export: Optional[str], json_out: bool, ndjson: bool) -> None:
    if export:
        out = write_export(response, export)
        if not json_out and not ndjson:
            console.print(f"[green]Saved:[/] {out}")
    print_response(console, response, as_json=json_out, ndjson=ndjson)




_SORT_ALIASES = {
    "name": "name",
    "filename": "name",
    "file": "name",
    "path": "path",
    "fullpath": "path",
    "ext": "ext",
    "extension": "ext",
    "type": "ext",
    "size": "size",
    "modified": "modified",
    "mtime": "modified",
    "time": "modified",
    "date": "modified",
}


def _es_sort_hint(sort_alias: Optional[str], descending: bool) -> Optional[str]:
    """Map eskit sort names to Everything/es.exe sort names when safe.

    This is only a hint for Everything. eskit still applies its own final sort
    after merging multi-drive results.
    """
    if not sort_alias:
        return None
    direction = "descending" if descending else "ascending"
    mapping = {
        "size": "size",
        "modified": "date-modified",
        "name": "name",
        "path": "path",
        "ext": "extension",
    }
    base = mapping.get(sort_alias)
    if not base:
        return None
    return f"{base}-{direction}"


def _ext_of(path: str) -> str:
    name = _basename(path)
    if "." not in name or (name.startswith(".") and name.count(".") == 1):
        return ""
    return name.rsplit(".", 1)[-1].lower()


def _ensure_metadata(response: EsKitResponse) -> None:
    enriched = [SearchResult.from_path(item.path, verify=True) for item in response.results]
    # Preserve original path order but replace metadata when available.
    response.results = enriched


def _sort_response(response: EsKitResponse, sort_key: str, descending: bool) -> None:
    key = _SORT_ALIASES.get(sort_key.lower().strip())
    if not key:
        valid = ", ".join(sorted(set(_SORT_ALIASES.values())))
        raise RuntimeError(f"Unknown --sort value: {sort_key!r}. Valid values: {valid}")

    if key in {"size", "modified"}:
        _ensure_metadata(response)

    if key == "name":
        response.results.sort(key=lambda r: _basename(r.path).casefold(), reverse=descending)
    elif key == "path":
        response.results.sort(key=lambda r: r.path.casefold(), reverse=descending)
    elif key == "ext":
        response.results.sort(key=lambda r: (_ext_of(r.path), _basename(r.path).casefold()), reverse=descending)
    elif key == "size":
        def size_value(r: SearchResult) -> int:
            if r.size_bytes is None:
                return -1 if descending else 10**30
            return r.size_bytes
        response.results.sort(key=size_value, reverse=descending)
    elif key == "modified":
        def modified_value(r: SearchResult) -> str:
            if r.modified:
                return r.modified
            return "" if descending else "9999-99-99T99:99:99"
        response.results.sort(key=modified_value, reverse=descending)
    response.meta["sort"] = {"key": key, "descending": descending}


def _trim_response(response: EsKitResponse, top: Optional[int]) -> None:
    if top is None:
        return
    if top < 0:
        raise RuntimeError("--top must be >= 0")
    response.results = response.results[:top]
    response.count = len(response.results)
    response.meta["top"] = top


def _print_count(response: EsKitResponse, *, json_out: bool = False) -> None:
    if json_out:
        console.print(json_dumps({"ok": True, "count": response.count, "query": response.query}))
    else:
        console.print(str(response.count))


# ----------------------------- direct grammar -----------------------------

def _run_direct_search(argv: list[str]) -> int:
    positional: list[str] = []
    limit = 80
    candidate_limit = 5000
    verify = False
    files_only = False
    folders_only = False
    fuzzy_mode = "auto"
    json_out = False
    ndjson = False
    debug = False
    export: Optional[str] = None
    sort_key: Optional[str] = None
    sort_desc: Optional[bool] = None
    stats = False
    count_only = False
    top: Optional[int] = None
    # The old standalone tui/interactive/agent commands are removed,
    # but a normal human search should still open a Listary-like selector.
    select_mode = True
    table_mode = False
    es_path: Optional[str] = None
    instance: Optional[str] = None
    index = 1
    open_result = False
    reveal_result = False
    copy_path_result = False
    copy_name_result = False
    copy_to: Optional[str] = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in {"--limit", "-n"}:
            i += 1
            if i >= len(argv):
                raise RuntimeError("--limit requires a value")
            limit = int(argv[i])
        elif arg == "--candidate-limit":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--candidate-limit requires a value")
            candidate_limit = int(argv[i])
        elif arg == "--verify":
            verify = True
        elif arg == "--no-verify":
            verify = False
        elif arg in {"--files-only", "--files"}:
            files_only = True
        elif arg in {"--folders-only", "--folders", "--dirs", "--directories"}:
            folders_only = True
        elif arg == "--no-fuzzy":
            fuzzy_mode = "off"
        elif arg == "--fuzzy":
            fuzzy_mode = "on"
        elif arg == "--json":
            json_out = True
        elif arg == "--ndjson":
            ndjson = True
        elif arg == "--debug":
            debug = True
        elif arg == "--sort":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--sort requires a value")
            value = argv[i]
            if ":" in value:
                value, order = value.split(":", 1)
                if order.lower() in {"desc", "descending", "-"}:
                    sort_desc = True
                elif order.lower() in {"asc", "ascending", "+"}:
                    sort_desc = False
                else:
                    raise RuntimeError("--sort order must be asc or desc")
            if value.startswith("-"):
                value = value[1:]
                sort_desc = True
            sort_key = value
        elif arg == "--asc":
            sort_desc = False
        elif arg == "--desc":
            sort_desc = True
        elif arg in {"--stats", "--stat", "--summary"}:
            stats = True
        elif arg in {"--count", "--count-only"}:
            count_only = True
        elif arg == "--top":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--top requires a value")
            top = int(argv[i])
        elif arg in {"--file"}:
            files_only = True
        elif arg in {"--folder"}:
            folders_only = True
        elif arg in {"--export", "-o"}:
            i += 1
            if i >= len(argv):
                raise RuntimeError("--export requires a value")
            export = argv[i]
        elif arg in {"--table", "--no-select"}:
            table_mode = True
            select_mode = False
        elif arg == "--select":
            select_mode = True
            table_mode = False
        elif arg == "--es-path":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--es-path requires a value")
            es_path = argv[i]
        elif arg == "--instance":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--instance requires a value")
            instance = argv[i]
        elif arg == "--index":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--index requires a value")
            index = int(argv[i])
        elif arg == "--open":
            open_result = True
        elif arg == "--reveal":
            reveal_result = True
        elif arg == "--copy-path":
            copy_path_result = True
        elif arg == "--copy-name":
            copy_name_result = True
        elif arg == "--copy-to":
            i += 1
            if i >= len(argv):
                raise RuntimeError("--copy-to requires a destination")
            copy_to = argv[i]
        elif arg in {"--help", "-h"}:
            console.print(DIRECT_HELP)
            return 0
        elif arg in {"--help-full", "--long-help"}:
            console.print(DIRECT_HELP_FULL)
            return 0
        else:
            positional.append(arg)
        i += 1

    spec = parse_search_tokens(positional)
    sort_alias = None
    if sort_key:
        sort_alias = _SORT_ALIASES.get(sort_key.lower().lstrip("-").split(":", 1)[0])
    effective_verify = verify or stats or count_only or (sort_alias in {"size", "modified"})
    default_desc = sort_alias in {"size", "modified"}
    effective_desc = sort_desc if sort_desc is not None else default_desc
    es_sort_hint = _es_sort_hint(sort_alias, effective_desc) if sort_alias else None
    response = _run_search_spec(
        spec,
        limit=limit,
        candidate_limit=candidate_limit,
        verify=effective_verify,
        files_only=files_only,
        folders_only=folders_only,
        fuzzy=fuzzy_mode,
        es_path=es_path,
        instance=instance,
        es_sort=es_sort_hint,
    )
    if sort_key:
        _sort_response(response, sort_key, effective_desc)
    _trim_response(response, top)
    if stats or json_out:
        response.meta["stats"] = response_stats(response)

    if debug and not json_out and not ndjson:
        _print_debug(response.meta)
    action_applied = _apply_result_action(
        response,
        index=index,
        open_result=open_result,
        reveal_result=reveal_result,
        copy_path_result=copy_path_result,
        copy_name_result=copy_name_result,
        copy_to=copy_to,
        json_out=json_out,
    )
    if action_applied:
        return 0

    if count_only:
        _print_count(response, json_out=json_out)
        return 0

    if stats and not json_out and not ndjson:
        if table_mode:
            print_response(console, response)
        print_stats(console, response)
        return 0

    # Default behavior for a human terminal:
    #   search -> keyboard selector -> action -> exit.
    # Script/output modes remain plain and machine-friendly.
    machine_mode = json_out or ndjson or bool(export) or stats or count_only or bool(sort_key) or top is not None
    if select_mode and not table_mode and not machine_mode and sys.stdin.isatty() and sys.stdout.isatty():
        listary_results(response, initial_query=" ".join(positional))
        return 0

    _print_or_export(response, export=export, json_out=json_out, ndjson=ndjson)
    return 0


KNOWN_COMMANDS = {
    "doctor",
    "path",
    "--version",
}

DIRECT_HELP = r"""
[bold cyan]eskit[/] — Everything/es.exe 的 Listary 风格搜索器

[bold]语法[/]
  eskit [盘符/路径 ...] [文件类型 ...] [文件名 ...] [处理参数]

[bold]例子[/]
  eskit .pdf ODL
  eskit d f ODL --sort size --top 10
  eskit d e .jpg .png screenshot --stats
  eskit d folder ODL
  eskit d folder .pdf ODL
  eskit d/Projects .pdf 开题 --copy-path --index 2

[bold]盘符/路径[/]  d -> D:\    d f -> D:\ + F:\    d/Projects -> D:\Projects
[bold]文件类型[/]  .pdf .jpg .png 可多个；folder/dir/目录/文件夹 表示只搜文件夹
[bold]处理参数[/]
  --sort name|path|ext|size|modified   --asc / --desc   --top N
  --count   --stats   --table   --json   --export out.md
  --open / --reveal / --copy-path / --copy-name / --copy-to DIR  [--index N]

[bold]帮助[/]
  eskit --version     查看版本号
  eskit --help-full   查看完整说明
  eskit doctor        检查 es.exe / Everything
  eskit path d/ABC    查看路径规范化
"""

DIRECT_HELP_FULL = r"""
[bold cyan]eskit：Everything / es.exe 的 Listary 风格命令行搜索器[/]

[bold]核心语法[/]

  eskit [盘符/路径 ...] [文件类型 ...] [文件名 ...] [对结果的处理]

[bold]最常用例子[/]

  eskit .pdf ODL
  eskit d .pdf ODL
  eskit d e .jpg .png ODL
  eskit d/Projects .pdf 开题
  eskit /mnt/d/Projects .pdf ODL

[bold]盘符 / 路径[/]

  d                  等价于 D:\
  d e                同时搜索 D:\ 和 E:\
  d/Projects         等价于 D:\Projects
  /mnt/d/Projects    等价于 D:\Projects
  D:/Projects        等价于 D:\Projects

[bold]文件类型[/]

  .pdf               只搜 PDF
  .jpg .png          同时搜 JPG / PNG
  .docx .pptx .pdf   同时搜多种文档
  folder / dir        只搜文件夹
  文件夹 / 目录        只搜文件夹
  file / 文件          只搜文件
  folder .pdf ODL     同时搜名含 ODL 的文件夹和 PDF 文件
  不写文件类型        搜全部类型

[bold]文件名关键词[/]

  ODL                普通关键词
  开题               中文关键词
  ODL 开题           多关键词
  默认启用 Listary 风格模糊匹配 / 拼音首字母匹配

[bold]搜索后选择[/]

  eskit .pdf ODL     默认进入键盘选择界面
                     ↑/↓ 选择，→ 更多操作，Enter 执行，Esc 退出

  eskit .pdf ODL --table       只输出表格，不进入选择界面
  eskit .pdf ODL --no-select   同上

[bold]对结果的处理[/]

  --open             打开第 1 个结果
  --open --index 3   打开第 3 个结果
  --reveal           打开结果所在位置
  --copy-path        复制完整路径
  --copy-name        复制文件名
  --copy-to d/Temp   复制文件到目标目录

[bold]排序[/]

  --sort name        按文件名排序
  --sort path        按完整路径排序
  --sort ext         按扩展名排序
  --sort size        按大小排序，默认从大到小
  --sort modified    按修改时间排序，默认从新到旧
  --asc / --desc     指定升序 / 降序
  --top 20           只保留前 20 条

[bold]统计 / 输出[/]

  --count            只输出结果数量
  --stats            统计类型、扩展名、盘符和总大小
  --json             JSON 输出
  --ndjson           每行一个 JSON
  --export out.md    导出 md/csv/json/txt
  --debug            显示实际调用 es.exe 的查询

[bold]维护命令[/]

  eskit doctor       检查 es.exe / Everything / WSL
  eskit path d/ABC   查看路径如何被规范化

[bold]示例组合[/]

  eskit d e .pdf .docx ODL --sort modified --top 30
  eskit d folder ODL --sort modified --top 20
  eskit d folder .pdf ODL --stats
  eskit d .jpg .png screenshot --sort size --desc --table
  eskit d .pdf 开题 --stats
  eskit d .pdf ODL --copy-path --index 2

"""



def entrypoint() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in {"--help", "-h", "help"}:
        console.print(DIRECT_HELP)
        raise SystemExit(0)
    if argv[0] in {"--version", "-V"}:
        console.print(__version__)
        raise SystemExit(0)
    if argv[0] in {"--help-full", "--long-help"}:
        console.print(DIRECT_HELP_FULL)
        raise SystemExit(0)
    if argv[0] not in KNOWN_COMMANDS and argv[0] not in {"--version", "--install-completion", "--show-completion"}:
        try:
            raise SystemExit(_run_direct_search(argv))
        except Exception as exc:  # noqa: BLE001
            _handle_error(exc, json_out="--json" in argv)
    app()


@app.callback()
def main(version: bool = typer.Option(False, "--version", help="Show version and exit.")) -> None:
    if version:
        console.print(__version__)
        raise typer.Exit()


@app.command("search", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def search_cmd(ctx: typer.Context) -> None:
    """Run the direct grammar explicitly: eskit search d .pdf ODL --json."""
    try:
        raise typer.Exit(_run_direct_search(list(ctx.args)))
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out="--json" in ctx.args)


@app.command()
def doctor(
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe. Also supports ESKIT_ES_PATH."),
    instance: Optional[str] = typer.Option(None, "--instance", help="Everything instance name, e.g. 1.5a."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Check es.exe, Everything availability, WSL interop, and runtime environment."""
    client = _client(es_path, instance=instance)
    checks: list[dict] = []
    checks.append({"name": "python", "ok": True, "details": platform_info()})
    checks.append({"name": "es.exe found", "ok": client.available, "details": {"path": client.es_path}})

    if is_wsl():
        proc = windows_process_running("Everything.exe")
        checks.append(
            {
                "name": "WSL detected",
                "ok": True,
                "details": {"wsl": True, "hint": "Windows Everything GUI/search client must be running."},
            }
        )
        if proc is not None:
            checks.append({"name": "Everything.exe process", "ok": proc, "details": {"running": proc}})

    raw_dict = None
    if client.available:
        try:
            raw = client.run_raw(["-n", "1", "*"])
            raw_dict = raw.to_dict()
            checks.append({"name": "es.exe query", "ok": raw.ok, "details": raw_dict})
        except Exception as exc:  # noqa: BLE001
            checks.append({"name": "es.exe query", "ok": False, "details": {"error": str(exc)}})

    ok = all(c["ok"] for c in checks)
    advice: list[str] = []
    if not client.available:
        advice.append("Cannot find es.exe. Set ESKIT_ES_PATH to the full es.exe path.")
    if raw_dict and raw_dict.get("returncode") == 8:
        advice.append("Error 8 means Everything IPC window was not found: start the Windows Everything GUI/search client.")
        advice.append("If you use Everything 1.5 alpha, try: eskit doctor --instance 1.5a")
    if is_wsl():
        advice.append("Path aliases: d == D:\\, d/Projects == D:\\Projects, /mnt/d/Projects == D:\\Projects.")

    payload = {"ok": ok, "checks": checks, "advice": advice}
    if json_out:
        console.print(json_dumps(payload))
        raise typer.Exit(code=0 if ok else 1)
    table = Table(title="eskit doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for c in checks:
        table.add_row(c["name"], "[green]OK[/]" if c["ok"] else "[red]FAIL[/]", str(c.get("details", "")))
    console.print(table)
    if advice:
        console.print(Panel("\n".join(f"• {item}" for item in advice), title="How to fix", border_style="yellow"))
    if not ok:
        raise typer.Exit(code=1)


@app.command("path")
def path_cmd(
    path: str = typer.Argument(..., help="Path to normalize, e.g. d, d/Projects, or /mnt/d/Projects."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
) -> None:
    """Show how eskit normalizes a path."""
    payload = display_path_equivalence(path)
    if len(path) in {1, 2} and path[0].isalpha():
        payload["everything"] = f"{path[0].upper()}:\\"
        payload["local"] = f"/mnt/{path[0].lower()}" if is_wsl() else f"{path[0].upper()}:\\"
    if json_out:
        console.print(json_dumps({"ok": True, "path": payload}))
        return
    table = Table(title="eskit path")
    table.add_column("Form")
    table.add_column("Path")
    for key, value in payload.items():
        table.add_row(key, value or "")
    console.print(table)


@app.command("find")
def find_cmd(
    query: str = typer.Argument(..., help="Everything search text, e.g. *.pdf, fig2, ext:f90."),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Restrict search to a root path."),
    ext: Optional[list[str]] = typer.Option(None, "--ext", "-e", help="Extension filter; can be repeated."),
    limit: int = typer.Option(200, "--limit", "-n", min=1, help="Maximum number of results."),
    verify: bool = typer.Option(False, "--verify", help="Verify results with Python stat."),
    files_only: bool = typer.Option(False, "--files-only", help="Return files only."),
    folders_only: bool = typer.Option(False, "--folders-only", help="Return folders only."),
    export: Optional[str] = typer.Option(None, "--export", "-o", help="Export to .md/.csv/.json/.txt."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ndjson: bool = typer.Option(False, "--ndjson", help="One JSON object per result."),
    debug: bool = typer.Option(False, "--debug", help="Show generated es.exe command."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Low-level Everything wrapper. Prefer direct grammar for daily use."""
    try:
        resp = es_find(_client(es_path), query, path, ext or [], limit, verify, files_only, folders_only)
        if debug and not json_out and not ndjson:
            _print_debug(resp.meta)
        _print_or_export(resp, export=export, json_out=json_out, ndjson=ndjson)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=json_out)


@app.command()
def empty(
    path: str = typer.Argument(..., help="Root path."),
    limit: int = typer.Option(500, "--limit", "-n", min=1, help="Maximum number of candidates."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify with Python that folders are truly empty."),
    export: Optional[str] = typer.Option(None, "--export", "-o", help="Export to .md/.csv/.json/.txt."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ndjson: bool = typer.Option(False, "--ndjson", help="One JSON object per result."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Find empty folders under a path."""
    try:
        resp = es_empty(_client(es_path), path, limit, verify)
        _print_or_export(resp, export=export, json_out=json_out, ndjson=ndjson)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=json_out)


@app.command()
def large(
    path: str = typer.Argument(..., help="Root path."),
    min_size: str = typer.Option("1GB", "--min", help="Minimum size, e.g. 500MB, 1GB."),
    limit: int = typer.Option(100, "--limit", "-n", min=1, help="Maximum number of results."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify with Python stat."),
    export: Optional[str] = typer.Option(None, "--export", "-o", help="Export to .md/.csv/.json/.txt."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ndjson: bool = typer.Option(False, "--ndjson", help="One JSON object per result."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Find large files."""
    try:
        resp = es_large(_client(es_path), path, min_size, limit, verify)
        _print_or_export(resp, export=export, json_out=json_out, ndjson=ndjson)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=json_out)


@app.command()
def recent(
    path: str = typer.Argument(..., help="Root path."),
    days: Optional[int] = typer.Option(7, "--days", min=0, help="Modified in the last N days."),
    hours: Optional[int] = typer.Option(None, "--hours", min=0, help="Modified in the last N hours."),
    limit: int = typer.Option(100, "--limit", "-n", min=1, help="Maximum number of results."),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify with Python stat."),
    export: Optional[str] = typer.Option(None, "--export", "-o", help="Export to .md/.csv/.json/.txt."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ndjson: bool = typer.Option(False, "--ndjson", help="One JSON object per result."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Find recently modified files/folders."""
    try:
        resp = es_recent(_client(es_path), path, days, hours, limit, verify)
        _print_or_export(resp, export=export, json_out=json_out, ndjson=ndjson)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=json_out)


@app.command("dup-name")
def dup_name(
    path: str = typer.Argument(..., help="Root path."),
    limit: int = typer.Option(5000, "--limit", "-n", min=1, help="Maximum files to inspect."),
    verify: bool = typer.Option(False, "--verify", help="Verify with Python stat."),
    export: Optional[str] = typer.Option(None, "--export", "-o", help="Export to .md/.csv/.json/.txt."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
    ndjson: bool = typer.Option(False, "--ndjson", help="One JSON object per result."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Find files with duplicate names under a path."""
    try:
        resp = es_duplicates_by_name(_client(es_path), path, limit, verify)
        _print_or_export(resp, export=export, json_out=json_out, ndjson=ndjson)
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=json_out)


@app.command("clean-empty")
def clean_empty(
    path: str = typer.Argument(..., help="Root path."),
    limit: int = typer.Option(1000, "--limit", "-n", min=1, help="Maximum candidates."),
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview by default; use --apply to delete."),
    trash: bool = typer.Option(True, "--trash/--permanent", help="Move to recycle bin by default."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Required confirmation for --apply."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Safely clean empty folders. Defaults to dry-run; no interactive prompts."""
    try:
        if is_dangerous_root(path):
            raise RuntimeError(f"Refusing to clean dangerous root: {path}")
        resp = es_empty(_client(es_path), path, limit, verify=True)
        if dry_run and not json_out:
            print_response(console, resp)
            console.print("[yellow]Dry-run only.[/] Use --apply --yes to delete.")
        result = remove_empty_folders(
            [r.path for r in resp.results],
            dry_run=dry_run,
            trash=trash,
            interactive=False,
            yes=yes,
            console=console,
        )
        if json_out:
            console.print(json_dumps({"ok": result.get("ok", False), "search": resp.to_dict(), "cleanup": result}))
        elif not dry_run:
            console.print(json_dumps(result))
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=json_out)


@app.command()
def report(
    path: str = typer.Argument(..., help="Root path."),
    out: str = typer.Option("eskit-report.md", "--out", "-o", help="Markdown report path."),
    large_min: str = typer.Option("1GB", "--large-min", help="Large file threshold."),
    recent_days: int = typer.Option(7, "--recent-days", help="Recent file window."),
    limit: int = typer.Option(200, "--limit", help="Limit for each section."),
    es_path: Optional[str] = typer.Option(None, "--es-path", help="Path to es.exe."),
) -> None:
    """Generate a Markdown file health report for a project/folder."""
    try:
        client = _client(es_path)
        sections = [
            es_empty(client, path, limit, verify=True),
            es_large(client, path, large_min, limit, verify=True),
            es_recent(client, path, recent_days, None, limit, verify=True),
            es_duplicates_by_name(client, path, limit * 5, verify=False),
        ]
        p = save_project_report(out, project_report(path, sections))
        console.print(f"[green]Saved report:[/] {p}")
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, json_out=False)


if __name__ == "__main__":
    entrypoint()
