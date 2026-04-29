from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .es import token_to_exts
from .util import split_drive_alias, to_windows_path


@dataclass
class SearchSpec:
    """Parsed direct-search grammar.

    Grammar:
        eskit [root ...] [type ...] [name ...] [options]

    Examples:
        eskit d .pdf ODL
        eskit d e .jpg .png ODL
        eskit d/Projects .pdf ODL
        eskit .pdf ODL --open --index 2
    """

    roots: list[str] = field(default_factory=list)
    exts: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)  # file | folder
    name_tokens: list[str] = field(default_factory=list)
    raw_tokens: list[str] = field(default_factory=list)

    @property
    def query(self) -> str:
        return " ".join(self.name_tokens).strip() or "*"

_KIND_ALIASES = {
    "file": "file",
    "files": "file",
    "fichier": "file",
    "文件": "file",
    "文件类型": "file",
    "folder": "folder",
    "folders": "folder",
    "dir": "folder",
    "dirs": "folder",
    "directory": "folder",
    "directories": "folder",
    "文件夹": "folder",
    "目录": "folder",
}


def token_to_kind(token: str) -> str | None:
    """Return an item-kind filter encoded by a user token.

    Examples:
      folder / folders / dir / 目录 / 文件夹 -> "folder"
      file / files / 文件 -> "file"
      .folder / .dir and .file are also accepted because they sit in the
      same grammar slot as file-type tokens like .pdf.
    """
    raw = token.strip().strip('"').strip("'")
    if not raw:
        return None
    lowered = raw.casefold()
    if lowered.startswith('*.'):
        lowered = lowered[2:]
    elif lowered.startswith('.'):
        lowered = lowered[1:]
    lowered = lowered.strip()
    return _KIND_ALIASES.get(lowered)


def _dedupe(items: Iterable[str], *, casefold: bool = True) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.casefold() if casefold else item
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _looks_like_drive_letter(token: str) -> bool:
    raw = token.strip().strip('"').strip("'")
    if len(raw) == 1 and raw.isalpha():
        return True
    if len(raw) == 2 and raw[0].isalpha() and raw[1] == ':':
        return True
    return False


def _drive_root(token: str) -> str:
    drive = token.strip().strip('"').strip("'")[0].upper()
    return f"{drive}:\\"


def _looks_like_path_root(token: str) -> bool:
    raw = token.strip().strip('"').strip("'")
    if not raw:
        return False
    if raw.startswith('/mnt/'):
        return True
    parsed = split_drive_alias(raw)
    if not parsed:
        return False
    drive, rest = parsed
    # Treat D:/, D:\, d/Projects, /d/Projects, d:Projects as roots.
    # A bare single letter is handled separately and only allowed in the root prefix.
    return bool(drive and (rest or ':' in raw or '/' in raw or '\\' in raw))


def _normalize_root(token: str) -> str:
    if _looks_like_drive_letter(token):
        return _drive_root(token)
    return to_windows_path(token) or token


def parse_search_tokens(tokens: Iterable[str]) -> SearchSpec:
    """Parse positional search tokens.

    Rules are intentionally simple and predictable:
      * Drive/root tokens come first: d, e, d/Projects, /mnt/d/Projects.
      * File type tokens are dot tokens: .pdf, *.jpg, .jpg;.png.
      * Remaining tokens are filename keywords.
      * Single-letter tokens after the name has started are treated as keywords.
    """
    spec = SearchSpec(raw_tokens=list(tokens))
    roots_allowed = True

    for raw_token in spec.raw_tokens:
        token = raw_token.strip()
        if not token:
            continue

        kind_value = token_to_kind(token)
        if kind_value:
            spec.kinds.append(kind_value)
            roots_allowed = False
            continue

        ext_values = token_to_exts(token)
        if ext_values:
            spec.exts.extend(ext_values)
            # Extension filters imply files unless the user explicitly also asks for folders.
            spec.kinds.append("file")
            roots_allowed = False
            continue

        if _looks_like_path_root(token):
            spec.roots.append(_normalize_root(token))
            # A path root can still appear before or after types, but after a filename
            # token this is almost certainly a user mistake. We keep it as a root
            # because explicit path syntax is unambiguous.
            continue

        if roots_allowed and _looks_like_drive_letter(token):
            spec.roots.append(_normalize_root(token))
            continue

        roots_allowed = False
        spec.name_tokens.append(token)

    spec.roots = _dedupe(spec.roots)
    spec.exts = _dedupe([e.strip().lstrip('*.').lstrip('.') for e in spec.exts if e.strip()])
    spec.kinds = _dedupe([k for k in spec.kinds if k in {'file', 'folder'}])
    return spec
