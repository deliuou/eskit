from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .util import to_local_path
from typing import Any, Iterable


@dataclass
class SearchResult:
    path: str
    kind: str = "unknown"  # file | folder | unknown
    size_bytes: int | None = None
    modified: str | None = None
    exists: bool | None = None
    is_empty: bool | None = None

    @classmethod
    def from_path(cls, path: str, verify: bool = False) -> "SearchResult":
        result = cls(path=path)
        if verify:
            local = to_local_path(path) or path
            p = Path(local)
            result.exists = p.exists()
            if p.exists():
                try:
                    st = p.stat()
                    result.modified = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
                    if p.is_dir():
                        result.kind = "folder"
                        result.size_bytes = None
                        try:
                            result.is_empty = not any(p.iterdir())
                        except OSError:
                            result.is_empty = None
                    else:
                        result.kind = "file"
                        result.size_bytes = int(st.st_size)
                except OSError:
                    pass
        return result

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandResult:
    ok: bool
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EsKitResponse:
    ok: bool
    action: str
    query: str | None
    count: int
    results: list[SearchResult]
    warnings: list[str]
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "query": self.query,
            "count": self.count,
            "results": [r.to_dict() for r in self.results],
            "warnings": self.warnings,
            "meta": self.meta,
        }


def unique_results(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in paths:
        p = raw.strip().strip("\ufeff")
        if not p:
            continue
        key = p.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out
