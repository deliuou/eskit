from __future__ import annotations

from pathlib import Path

from .formatters import markdown_report
from .models import EsKitResponse
from .util import human_size, now_stamp


def project_report(path: str, sections: list[EsKitResponse]) -> str:
    lines = [
        f"# eskit Project Report: `{path}`",
        "",
        f"Generated: `{now_stamp()}`",
        "",
        "## Summary",
        "",
        "| Section | Count | Query |",
        "|---|---:|---|",
    ]
    for section in sections:
        lines.append(f"| {section.action} | {section.count} | `{section.query or ''}` |")
    lines.append("")
    for section in sections:
        lines.append(markdown_report(section, title=f"{section.action}: {section.count} result(s)"))
        lines.append("")
    return "\n".join(lines)


def save_project_report(path: str, text: str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
