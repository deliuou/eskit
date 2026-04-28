from __future__ import annotations

from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.table import Table

from .models import EsKitResponse, SearchResult
from .util import human_size, json_dumps


def result_table(results: Iterable[SearchResult], title: str = "Results") -> Table:
    table = Table(title=title, show_lines=False)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Kind", width=8)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Modified", width=20)
    table.add_column("Path", overflow="fold")
    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r.kind or "",
            human_size(r.size_bytes),
            r.modified or "",
            r.path,
        )
    return table


def print_response(console: Console, response: EsKitResponse, *, as_json: bool = False, ndjson: bool = False) -> None:
    if as_json:
        console.print(json_dumps(response.to_dict()))
        return
    if ndjson:
        for r in response.results:
            console.print(json_dumps(r.to_dict()))
        return
    console.print(result_table(response.results, title=f"eskit {response.action}: {response.count} result(s)"))
    for w in response.warnings:
        console.print(f"[yellow]WARN:[/] {w}")


def markdown_report(response: EsKitResponse, title: str | None = None) -> str:
    title = title or f"eskit {response.action} report"
    lines = [f"# {title}", "", f"- Action: `{response.action}`", f"- Query: `{response.query or ''}`", f"- Count: `{response.count}`", ""]
    if response.warnings:
        lines += ["## Warnings", ""]
        for w in response.warnings:
            lines.append(f"- {w}")
        lines.append("")
    lines += ["## Results", "", "| # | Kind | Size | Modified | Path |", "|---:|---|---:|---|---|"]
    for i, r in enumerate(response.results, 1):
        path = r.path.replace("|", "\\|")
        lines.append(f"| {i} | {r.kind or ''} | {human_size(r.size_bytes)} | {r.modified or ''} | `{path}` |")
    lines.append("")
    return "\n".join(lines)


def csv_text(response: EsKitResponse) -> str:
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["path", "kind", "size_bytes", "modified", "exists", "is_empty"])
    writer.writeheader()
    for r in response.results:
        writer.writerow(r.to_dict())
    return buf.getvalue()


def txt_text(response: EsKitResponse) -> str:
    return "\n".join(r.path for r in response.results) + ("\n" if response.results else "")



def _ext_name(path: str) -> str:
    text = path.rstrip('\\/')
    name = text.replace('\\', '/').rsplit('/', 1)[-1]
    if '.' not in name or (name.startswith('.') and name.count('.') == 1):
        return ''
    return name.rsplit('.', 1)[-1].lower()


def _drive_name(path: str) -> str:
    text = path.strip()
    if len(text) >= 2 and text[1] == ':':
        return text[0].upper() + ':'
    if text.startswith('/mnt/') and len(text) >= 6:
        return text[5].upper() + ':'
    return ''


def response_stats(response: EsKitResponse) -> dict:
    by_ext: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_drive: dict[str, int] = {}
    total_size = 0
    known_size_count = 0
    for r in response.results:
        kind = r.kind or 'unknown'
        by_kind[kind] = by_kind.get(kind, 0) + 1
        ext = _ext_name(r.path) or '(no ext)'
        by_ext[ext] = by_ext.get(ext, 0) + 1
        drive = _drive_name(r.path) or '(unknown)'
        by_drive[drive] = by_drive.get(drive, 0) + 1
        if r.size_bytes is not None:
            total_size += r.size_bytes
            known_size_count += 1
    return {
        'count': len(response.results),
        'query': response.query or '',
        'total_size_bytes': total_size,
        'total_size_human': human_size(total_size),
        'known_size_count': known_size_count,
        'by_kind': dict(sorted(by_kind.items(), key=lambda x: (-x[1], x[0]))),
        'by_extension': dict(sorted(by_ext.items(), key=lambda x: (-x[1], x[0]))),
        'by_drive': dict(sorted(by_drive.items(), key=lambda x: (-x[1], x[0]))),
    }


def print_stats(console: Console, response: EsKitResponse) -> None:
    stats = response_stats(response)
    summary = Table(title='eskit statistics', show_lines=False)
    summary.add_column('Item')
    summary.add_column('Value', justify='right')
    summary.add_row('Results', str(stats['count']))
    summary.add_row('Known total size', stats['total_size_human'])
    summary.add_row('Known-size files', str(stats['known_size_count']))
    console.print(summary)

    def small_table(title: str, data: dict[str, int]) -> Table:
        t = Table(title=title, show_lines=False)
        t.add_column('Group')
        t.add_column('Count', justify='right')
        for k, v in list(data.items())[:20]:
            t.add_row(str(k), str(v))
        return t

    console.print(small_table('By kind', stats['by_kind']))
    console.print(small_table('By extension', stats['by_extension']))
    console.print(small_table('By drive', stats['by_drive']))

def write_export(response: EsKitResponse, out: str) -> Path:
    path = Path(out)
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "json":
        text = json_dumps(response.to_dict()) + "\n"
    elif suffix == "csv":
        text = csv_text(response)
    elif suffix in {"md", "markdown"}:
        text = markdown_report(response)
    else:
        text = txt_text(response)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
