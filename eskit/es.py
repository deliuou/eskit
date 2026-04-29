from __future__ import annotations

import locale
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Iterable, Sequence

from .models import CommandResult, EsKitResponse, SearchResult, unique_results
from .fuzzy import sort_paths_listary
from .util import find_executable, since_expression, to_everything_path


class EsNotFoundError(RuntimeError):
    pass


class EsError(RuntimeError):
    def __init__(self, message: str, result: CommandResult | None = None):
        super().__init__(message)
        self.result = result


class EsClient:
    def __init__(self, es_path: str | None = None, timeout: int = 30, instance: str | None = None):
        self.es_path = es_path or find_executable("es.exe") or find_executable("es")
        self.timeout = timeout
        self.instance = instance or os.environ.get("ESKIT_ES_INSTANCE")

    @property
    def available(self) -> bool:
        return bool(self.es_path)

    def require(self) -> str:
        if not self.es_path:
            raise EsNotFoundError(
                "Cannot find es.exe. Install Everything CLI or set ESKIT_ES_PATH to the es.exe path."
            )
        return self.es_path

    def _command(self, args: list[str], *, utf8_code_page: bool = True) -> list[str]:
        cmd = [self.require()]
        if self.instance:
            cmd.extend(["-instance", self.instance])
        if utf8_code_page:
            cmd.extend(["-cp", "65001"])
        cmd.extend(args)
        return cmd

    @staticmethod
    def _decode_output(data: bytes | str | None, *, prefer_utf8: bool = True) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data

        env_encoding = os.environ.get("ESKIT_ES_ENCODING")
        encodings: list[str] = []
        if env_encoding:
            encodings.append(env_encoding)
        if prefer_utf8:
            encodings.extend(["utf-8-sig", "utf-8"])
        encodings.extend(
            [
                locale.getpreferredencoding(False),
                "gb18030",
                "cp1252",
            ]
        )

        seen: set[str] = set()
        for encoding in encodings:
            if not encoding:
                continue
            key = encoding.casefold()
            if key in seen:
                continue
            seen.add(key)
            try:
                return data.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                continue
        return data.decode("utf-8", errors="replace")

    def _run_command(self, cmd: list[str], *, prefer_utf8: bool) -> CommandResult:
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            result = CommandResult(
                False,
                cmd,
                124,
                self._decode_output(exc.stdout, prefer_utf8=prefer_utf8),
                self._decode_output(exc.stderr, prefer_utf8=prefer_utf8),
                elapsed,
            )
            raise EsError("es.exe timed out", result) from exc
        elapsed = int((time.perf_counter() - start) * 1000)
        stdout = self._decode_output(proc.stdout, prefer_utf8=prefer_utf8)
        stderr = self._decode_output(proc.stderr, prefer_utf8=prefer_utf8)
        return CommandResult(proc.returncode == 0, cmd, proc.returncode, stdout, stderr, elapsed)

    def run_raw(self, args: list[str]) -> CommandResult:
        cmd = self._command(args, utf8_code_page=True)
        result = self._run_command(cmd, prefer_utf8=True)
        if result.returncode != 6:
            return result

        # Older ES builds may not support -cp. Retry once without it and decode
        # with local fallbacks so Chinese Windows output still has a chance to survive.
        fallback_cmd = self._command(args, utf8_code_page=False)
        return self._run_command(fallback_cmd, prefer_utf8=False)

    def search_paths(
        self,
        expression: str | Sequence[str],
        *,
        limit: int = 200,
        sort: str | None = None,
        files_only: bool = False,
        folders_only: bool = False,
    ) -> tuple[list[str], CommandResult]:
        """Run Everything search and return full paths.

        `expression` may be either a legacy single search string or a list of
        search tokens.  Passing a list is preferred.  It avoids the WSL/Windows
        quoting bug where `"odl ext:pdf"` can behave differently from
        `odl ext:pdf` when launched through subprocess.
        """
        args = ["-full-path-and-name", "-n", str(limit)]
        if sort:
            args.extend(["-sort", sort])
        if files_only:
            args.append("file:")
        if folders_only:
            args.append("folder:")
        if isinstance(expression, str):
            args.append(expression)
        else:
            args.extend([str(x) for x in expression if str(x).strip()])
        result = self.run_raw(args)
        if not result.ok:
            raise EsError("es.exe returned a non-zero exit code", result)
        return unique_results(result.stdout.splitlines()), result


def _split_query_terms(query: str) -> list[str]:
    """Split user query into safe search tokens.

    We keep quoted phrases together but do not fail on malformed quotes.
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        return shlex.split(q, posix=False)
    except ValueError:
        return q.split()


def _display_expression(tokens: Sequence[str]) -> str:
    return " ".join(tokens).strip()


def build_find_terms(
    query: str,
    path: str | None = None,
    exts: Iterable[str] | None = None,
    contains: str | None = None,
    *,
    ext_mode: str = "ext",
) -> list[str]:
    """Build search terms for es.exe.

    ext_mode="ext" produces `ext:pdf`.
    ext_mode="glob" produces `*.pdf` for the single-extension fallback.
    """
    terms: list[str] = []
    if path:
        # Do not add literal quotes here. subprocess already passes the whole
        # path as one argv token, including paths with spaces.
        terms.append(to_everything_path(path) or path)
    terms.extend(_split_query_terms(query))
    if contains:
        terms.extend(_split_query_terms(contains))
    ext_list = [e.strip().lstrip("*.").lstrip(".") for e in (exts or []) if e.strip()]
    if ext_list:
        if ext_mode == "glob" and len(ext_list) == 1:
            terms.append(f"*.{ext_list[0]}")
        else:
            terms.append("ext:" + ";".join(ext_list))
    return [t for t in terms if t]


def build_find_expression(
    query: str,
    path: str | None = None,
    exts: Iterable[str] | None = None,
    contains: str | None = None,
) -> str:
    """Human-readable search expression kept for response metadata."""
    return _display_expression(build_find_terms(query, path=path, exts=exts, contains=contains))


_EXT_TOKEN_REPLACEMENTS = {"jpeg": "jpg"}


def token_to_exts(token: str) -> list[str]:
    """Return extension filters encoded by a user token.

    Examples:
      .jpg       -> ["jpg"]
      *.jpg      -> ["jpg"]
      .jpg,.png  -> ["jpg", "png"]
      .jpg;.png  -> ["jpg", "png"]

    Plain words such as "pdf" are deliberately not treated as extensions,
    because users often search for ordinary text tokens.
    """
    raw = token.strip().strip('"').strip("'")
    if not raw:
        return []
    if raw.startswith('*.'):
        raw = raw[1:]
    if not raw.startswith('.'):
        return []
    if any(sep in raw for sep in ('/', '\\')):
        return []
    parts = [x.strip().lstrip('*.').lstrip('.') for x in raw.replace(',', ';').split(';')]
    out: list[str] = []
    for item in parts:
        if not item:
            continue
        item = _EXT_TOKEN_REPLACEMENTS.get(item.casefold(), item)
        if item and item not in out:
            out.append(item)
    return out


def build_smart_query(tokens: Iterable[str]) -> tuple[str, list[str]]:
    """Split default-search tokens into Everything query text and extension filters."""
    query_terms: list[str] = []
    exts: list[str] = []
    for token in tokens:
        token_exts = token_to_exts(token)
        if token_exts:
            for ext in token_exts:
                if ext not in exts:
                    exts.append(ext)
        else:
            query_terms.append(token)
    return (" ".join(query_terms).strip() or "*"), exts


def _run_find_attempt(
    client: EsClient,
    *,
    action: str,
    query: str,
    path: str | None,
    exts: list[str],
    limit: int,
    verify: bool,
    files_only: bool,
    folders_only: bool,
    ext_mode: str = "ext",
    es_sort: str | None = None,
) -> EsKitResponse:
    terms = build_find_terms(query, path=path, exts=exts, ext_mode=ext_mode)
    expression = _display_expression(terms)
    paths, raw = client.search_paths(
        terms,
        limit=limit,
        sort=es_sort,
        files_only=files_only,
        folders_only=folders_only,
    )
    return result_response(
        action,
        expression,
        paths,
        verify=verify,
        meta={"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "search_terms": terms},
    )


def _merge_ordered_paths(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for path in group:
            key = path.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
    return out


def smart_find(
    client: EsClient,
    tokens: list[str],
    path: str | None,
    extra_exts: list[str],
    limit: int,
    verify: bool,
    files_only: bool,
    folders_only: bool,
    *,
    listary: str | bool = "auto",
    candidate_limit: int = 5000,
    es_sort: str | None = None,
) -> EsKitResponse:
    """Default eskit search: `eskit .jpg ODL` -> Listary-like search."""
    query, token_exts = build_smart_query(tokens)
    exts = token_exts + [e.strip().lstrip('*').lstrip('.') for e in extra_exts if e.strip()]
    seen: set[str] = set()
    exts = [e for e in exts if not (e.casefold() in seen or seen.add(e.casefold()))]
    query_terms = [t for t in _split_query_terms(query) if t != "*"]

    attempts: list[dict] = []
    warnings: list[str] = []

    resp = _run_find_attempt(
        client,
        action="search",
        query=query,
        path=path,
        exts=exts,
        limit=limit,
        verify=verify,
        files_only=files_only,
        folders_only=folders_only,
        ext_mode="ext",
        es_sort=es_sort,
    )
    exact_paths = [r.path for r in resp.results]
    attempts.append(
        {
            "mode": "everything-ext",
            "query": resp.query,
            "count": resp.count,
            "raw_command": resp.meta.get("raw_command"),
            "elapsed_ms": resp.meta.get("elapsed_ms"),
        }
    )

    glob_paths: list[str] = []
    if len(exts) == 1:
        fallback = _run_find_attempt(
            client,
            action="search",
            query=query,
            path=path,
            exts=exts,
            limit=limit,
            verify=verify,
            files_only=files_only,
            folders_only=folders_only,
            ext_mode="glob",
            es_sort=es_sort,
        )
        glob_paths = [r.path for r in fallback.results]
        attempts.append(
            {
                "mode": "everything-glob",
                "query": fallback.query,
                "count": fallback.count,
                "raw_command": fallback.meta.get("raw_command"),
                "elapsed_ms": fallback.meta.get("elapsed_ms"),
            }
        )

    listary_paths: list[str] = []
    listary_meta: dict[str, dict] = {}
    listary_mode = "on" if listary is True else "off" if listary is False else str(listary or "auto").lower()
    bare_drive_root = bool(path) and len(path) == 3 and path[1:] == ":\\"
    root_is_global = path is None or bare_drive_root
    already_enough = (len(exact_paths) + len(glob_paths)) >= limit
    should_listary = (
        listary_mode == "on"
        or (
            listary_mode == "auto"
            and query_terms
            and not already_enough
            and (bool(exts) or not root_is_global)
        )
    )
    if should_listary and query_terms:
        candidate_terms = build_find_terms("*", path=path, exts=exts, ext_mode="glob" if len(exts) == 1 else "ext")
        if not exts:
            candidate_terms = build_find_terms("*", path=path, exts=[], ext_mode="ext")
        try:
            candidate_paths, raw = client.search_paths(
                candidate_terms,
                limit=max(limit, candidate_limit),
                sort=es_sort,
                files_only=files_only,
                folders_only=folders_only,
            )
            listary_paths, listary_meta = sort_paths_listary(candidate_paths, query_terms, exts)
            listary_paths = listary_paths[:limit]
            attempts.append(
                {
                    "mode": "listary-fuzzy",
                    "query": _display_expression(candidate_terms),
                    "candidate_count": len(candidate_paths),
                    "count": len(listary_paths),
                    "raw_command": raw.command,
                    "elapsed_ms": raw.elapsed_ms,
                    "query_terms": query_terms,
                }
            )
            if candidate_paths and not listary_paths and exts:
                warnings.append("Listary fuzzy pass inspected extension-filtered candidates but found no fuzzy/pinyin match.")
        except EsError as exc:
            attempts.append({"mode": "listary-fuzzy", "ok": False, "error": str(exc)})

    merged = _merge_ordered_paths(listary_paths, glob_paths, exact_paths)[:limit]
    expression = _display_expression(build_find_terms(query, path=path, exts=exts, ext_mode="glob" if len(exts) == 1 else "ext"))
    return result_response(
        "search",
        expression,
        merged,
        verify=verify,
        warnings=warnings,
        meta={
            "tokens": tokens,
            "extension_filters": exts,
            "smart_query": query,
            "query_terms": query_terms,
            "attempts": attempts,
            "listary_scores": listary_meta,
        },
    )

def result_response(
    action: str,
    expression: str,
    paths: list[str],
    *,
    verify: bool = False,
    warnings: list[str] | None = None,
    meta: dict | None = None,
) -> EsKitResponse:
    results = [SearchResult.from_path(p, verify=verify) for p in paths]
    return EsKitResponse(
        ok=True,
        action=action,
        query=expression,
        count=len(results),
        results=results,
        warnings=warnings or [],
        meta=meta or {},
    )


def find(client: EsClient, query: str, path: str | None, exts: list[str], limit: int, verify: bool, files_only: bool, folders_only: bool) -> EsKitResponse:
    resp = _run_find_attempt(
        client,
        action="find",
        query=query,
        path=path,
        exts=exts,
        limit=limit,
        verify=verify,
        files_only=files_only,
        folders_only=folders_only,
        ext_mode="ext",
    )
    if resp.count == 0 and len(exts) == 1:
        fallback = _run_find_attempt(
            client,
            action="find",
            query=query,
            path=path,
            exts=exts,
            limit=limit,
            verify=verify,
            files_only=files_only,
            folders_only=folders_only,
            ext_mode="glob",
        )
        resp.meta["attempts"] = [
            {"mode": "ext", "query": resp.query, "count": resp.count, "raw_command": resp.meta.get("raw_command")},
            {"mode": "glob", "query": fallback.query, "count": fallback.count, "raw_command": fallback.meta.get("raw_command")},
        ]
        if fallback.count > 0:
            fallback.warnings.append("Primary ext: search returned 0 results; used wildcard fallback instead.")
            resp = fallback
    return resp


def empty(client: EsClient, path: str, limit: int, verify: bool) -> EsKitResponse:
    es_path = to_everything_path(path) or path
    terms = [es_path, "folder:", "empty:"]
    paths, raw = client.search_paths(terms, limit=limit, folders_only=False)
    warnings: list[str] = []
    if verify:
        verified = []
        for p in paths:
            r = SearchResult.from_path(p, verify=True)
            if r.exists and r.kind == "folder" and r.is_empty:
                verified.append(p)
        if len(verified) != len(paths):
            warnings.append("Some es.exe candidates were removed because Python verification said they are not empty folders.")
        paths = verified
    return result_response(
        "empty",
        _display_expression(terms),
        paths,
        verify=verify,
        warnings=warnings,
        meta={"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "search_terms": terms},
    )


def large(client: EsClient, path: str, min_size: str, limit: int, verify: bool) -> EsKitResponse:
    es_path = to_everything_path(path) or path
    terms = [es_path, "file:", f"size:>{min_size}"]
    paths, raw = client.search_paths(terms, limit=limit, sort="size-descending")
    return result_response(
        "large",
        _display_expression(terms),
        paths,
        verify=verify,
        meta={"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "min_size": min_size, "search_terms": terms},
    )


def recent(client: EsClient, path: str, days: int | None, hours: int | None, limit: int, verify: bool) -> EsKitResponse:
    expr_date = since_expression(days=days, hours=hours)
    es_path = to_everything_path(path) or path
    terms = [es_path, expr_date]
    paths, raw = client.search_paths(terms, limit=limit, sort="date-modified-descending")
    return result_response(
        "recent",
        _display_expression(terms),
        paths,
        verify=verify,
        meta={"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "days": days, "hours": hours, "search_terms": terms},
    )


def duplicates_by_name(client: EsClient, path: str, limit: int, verify: bool) -> EsKitResponse:
    es_path = to_everything_path(path) or path
    terms = [es_path, "file:"]
    paths, raw = client.search_paths(terms, limit=limit)
    groups: dict[str, list[str]] = {}
    for p in paths:
        name = Path(p).name.casefold()
        groups.setdefault(name, []).append(p)
    dup_paths: list[str] = []
    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    for items in dup_groups.values():
        dup_paths.extend(items)
    return result_response(
        "dup-name",
        _display_expression(terms),
        dup_paths,
        verify=verify,
        meta={"raw_command": raw.command, "elapsed_ms": raw.elapsed_ms, "groups": dup_groups, "search_terms": terms},
    )
