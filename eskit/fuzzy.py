from __future__ import annotations

import re
from dataclasses import dataclass

try:  # pypinyin is optional at runtime but declared as a dependency.
    from pypinyin import Style, lazy_pinyin
except Exception:  # pragma: no cover - fallback for minimal installs
    Style = None  # type: ignore[assignment]
    lazy_pinyin = None  # type: ignore[assignment]


def basename_any(path: str) -> str:
    """Return the basename for either Windows or POSIX style paths."""
    raw = str(path).rstrip("\\/")
    if not raw:
        return str(path)
    return re.split(r"[\\/]", raw)[-1]


def dirname_any(path: str) -> str:
    """Return the parent path for either Windows or POSIX style paths."""
    raw = str(path).rstrip("\\/")
    parts = re.split(r"[\\/]", raw)
    if len(parts) <= 1:
        return ""
    sep = "\\" if "\\" in raw else "/"
    return sep.join(parts[:-1])


def extension_any(path: str) -> str:
    name = basename_any(path)
    if "." not in name or name.endswith("."):
        return ""
    return name.rsplit(".", 1)[-1].casefold()


def stem_any(path: str) -> str:
    name = basename_any(path)
    if "." not in name or name.endswith("."):
        return name
    return name.rsplit(".", 1)[0]


_SEP_RE = re.compile(r"[\s_\-\.\(\)\[\]{}（）【】《》,，;；:：]+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-zA-Z]+")


def compact_ascii(text: str) -> str:
    return _NON_ALNUM_RE.sub("", text).casefold()


def wordish_ascii(text: str) -> str:
    return _SEP_RE.sub(" ", text).strip().casefold()


def _pinyin_full(text: str) -> str:
    if lazy_pinyin is None:
        return text.casefold()
    try:
        return "".join(lazy_pinyin(text, errors="default")).casefold()
    except Exception:
        return text.casefold()


def _pinyin_initials(text: str) -> str:
    if lazy_pinyin is None or Style is None:
        return compact_ascii(text)
    try:
        return "".join(lazy_pinyin(text, style=Style.FIRST_LETTER, errors="default")).casefold()
    except Exception:
        return compact_ascii(text)


@dataclass(frozen=True)
class MatchInfo:
    score: int
    reason: str


def is_subsequence(needle: str, haystack: str) -> bool:
    if not needle:
        return True
    it = iter(haystack)
    return all(ch in it for ch in needle)


def _score_token(token: str, path: str) -> MatchInfo | None:
    token_raw = token.strip().strip('"').strip("'")
    if not token_raw:
        return MatchInfo(0, "empty")
    t = compact_ascii(token_raw)
    if not t:
        t = token_raw.casefold()

    name = basename_any(path)
    stem = stem_any(path)
    parent = dirname_any(path)

    name_l = name.casefold()
    stem_l = stem.casefold()
    path_l = path.casefold()
    parent_l = parent.casefold()

    name_compact = compact_ascii(name)
    stem_compact = compact_ascii(stem)
    path_compact = compact_ascii(path)

    py_full = _pinyin_full(stem)
    py_initials = _pinyin_initials(stem)
    parent_initials = _pinyin_initials(parent)

    # Exact and substring matches should beat fuzzy/pinyin matches.
    if t == compact_ascii(stem):
        return MatchInfo(1000, "stem-exact")
    if t == compact_ascii(name):
        return MatchInfo(980, "name-exact")
    if t in stem_l or t in stem_compact:
        return MatchInfo(900 - max(0, len(stem_compact) - len(t)), "stem-substring")
    if t in name_l or t in name_compact:
        return MatchInfo(850 - max(0, len(name_compact) - len(t)), "name-substring")
    if t in path_l or t in path_compact:
        return MatchInfo(700, "path-substring")

    # Pinyin support: ODL -> 欧得柳, kg -> 开关, etc.
    if py_initials.startswith(t):
        return MatchInfo(820 - max(0, len(py_initials) - len(t)), "pinyin-initial-prefix")
    if t in py_initials:
        return MatchInfo(760 - max(0, len(py_initials) - len(t)), "pinyin-initial-substring")
    if py_full.startswith(t):
        return MatchInfo(740 - max(0, len(py_full) - len(t)), "pinyin-full-prefix")
    if t in py_full:
        return MatchInfo(680 - max(0, len(py_full) - len(t)), "pinyin-full-substring")
    if t in parent_initials:
        return MatchInfo(520, "parent-pinyin-initial")

    # Fuzzy subsequence, useful for abbreviations in English filenames.
    if len(t) >= 2 and is_subsequence(t, stem_compact):
        return MatchInfo(560 - max(0, len(stem_compact) - len(t)), "stem-subsequence")
    if len(t) >= 2 and is_subsequence(t, py_initials):
        return MatchInfo(540 - max(0, len(py_initials) - len(t)), "pinyin-initial-subsequence")
    if len(t) >= 3 and is_subsequence(t, path_compact):
        return MatchInfo(420, "path-subsequence")

    return None


def listary_score(path: str, query_terms: list[str], exts: list[str] | None = None) -> tuple[int, list[str]] | None:
    """Return a score for Listary-like matching or None when not matched.

    All non-extension query terms must match somewhere in the path/name/pinyin key.
    Extension filters are treated as hard filters.
    """
    ext_filters = [e.strip().lstrip("*. ").lstrip(".").casefold() for e in (exts or []) if e.strip()]
    if ext_filters:
        ext = extension_any(path)
        if ext not in ext_filters:
            return None

    total = 0
    reasons: list[str] = []
    if ext_filters:
        total += 200
        reasons.append("ext")

    for token in query_terms:
        info = _score_token(token, path)
        if info is None:
            return None
        total += info.score
        reasons.append(f"{token}:{info.reason}")

    # Prefer shorter and basename-focused matches.
    name_len = len(compact_ascii(basename_any(path)))
    total += max(0, 120 - name_len)
    return total, reasons


def sort_paths_listary(paths: list[str], query_terms: list[str], exts: list[str] | None = None) -> tuple[list[str], dict[str, dict]]:
    """Filter and sort paths by Listary-like fuzzy/pinyin score."""
    scored: list[tuple[int, str, list[str]]] = []
    metadata: dict[str, dict] = {}
    for path in paths:
        match = listary_score(path, query_terms, exts)
        if match is None:
            continue
        score, reasons = match
        scored.append((score, path, reasons))
    scored.sort(key=lambda item: (-item[0], basename_any(item[1]).casefold(), item[1].casefold()))
    for score, path, reasons in scored:
        metadata[path] = {"score": score, "reasons": reasons}
    return [path for score, path, reasons in scored], metadata
