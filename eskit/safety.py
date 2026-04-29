from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.prompt import Confirm
from send2trash import send2trash

from .models import SearchResult
from .util import split_drive_alias, to_local_path


def is_dangerous_root(path: str) -> bool:
    parsed = split_drive_alias(path)
    if parsed and not parsed[1].strip("\\/"):
        return True
    p = Path(to_local_path(path) or path)
    try:
        resolved = p.resolve()
    except OSError:
        resolved = p.absolute()
    text = str(resolved).replace("/", "\\").rstrip("\\")
    # Refuse obvious drive/root/home/system-level operations.
    if len(text) <= 3 and text.endswith(":"):
        return True
    if text in {"C:", "C:\\", "D:", "D:\\", "E:", "E:\\", "\\", "\\mnt\\c", "\\mnt\\d", "\\mnt\\e"}:
        return True
    dangerous_names = {"windows", "program files", "program files (x86)", "users"}
    return resolved.name.lower() in dangerous_names


def verify_empty_folders(paths: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in paths:
        p = Path(to_local_path(raw) or raw)
        try:
            if p.exists() and p.is_dir() and not any(p.iterdir()):
                out.append(raw)
        except OSError:
            continue
    return out


def remove_empty_folders(
    folders: Iterable[str],
    *,
    trash: bool = True,
    dry_run: bool = True,
    interactive: bool = False,
    yes: bool = False,
    console: Console | None = None,
) -> dict:
    console = console or Console()
    verified = verify_empty_folders(folders)
    if dry_run:
        return {"ok": True, "dry_run": True, "removed": [], "would_remove": verified, "failed": []}
    if not yes:
        if interactive:
            console.print(f"[yellow]About to remove {len(verified)} empty folder(s).[/]")
            if not Confirm.ask("Continue?", default=False):
                return {"ok": False, "cancelled": True, "removed": [], "would_remove": verified, "failed": []}
        else:
            raise RuntimeError("Refusing to delete without --yes or --yes confirmation.")
    removed: list[str] = []
    failed: list[dict] = []
    for folder in verified:
        try:
            local_folder = to_local_path(folder) or folder
            if trash:
                send2trash(local_folder)
            else:
                os.rmdir(local_folder)
            removed.append(folder)
        except Exception as exc:  # noqa: BLE001 - CLI reports failures to user.
            failed.append({"path": folder, "error": str(exc)})
    return {"ok": len(failed) == 0, "dry_run": False, "removed": removed, "would_remove": [], "failed": failed}
