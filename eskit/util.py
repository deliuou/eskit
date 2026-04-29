from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SIZE_UNITS = {
    "b": 1,
    "kb": 1024,
    "k": 1024,
    "mb": 1024**2,
    "m": 1024**2,
    "gb": 1024**3,
    "g": 1024**3,
    "tb": 1024**4,
    "t": 1024**4,
}


def is_wsl() -> bool:
    """Return True when running inside Windows Subsystem for Linux."""
    if "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ:
        return True
    try:
        text = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower()
        return "microsoft" in text or "wsl" in text
    except OSError:
        return False


def configure_windows_console_utf8() -> None:
    """Best-effort UTF-8 console setup for native Windows terminals."""
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        return


def strip_outer_quotes(path: str) -> str:
    return path.strip().strip('"').strip("'")


def looks_like_windows_drive_path(path: str) -> bool:
    """Return True for C:\\foo, C:/foo, C:foo, c/foo, or c\\foo style inputs."""
    raw = strip_outer_quotes(path)
    return bool(re.match(r"^[a-zA-Z]:(?:[\\/].*|.*)$", raw) or re.match(r"^[a-zA-Z][\\/].+", raw))


def split_drive_alias(path: str) -> tuple[str, str] | None:
    """Parse friendly Windows drive aliases.

    Supported examples:
      - /mnt/d/Projects      -> ("D", "Projects")
      - d/Projects           -> ("D", "Projects")
      - d\\Projects          -> ("D", "Projects")
      - D:/Projects          -> ("D", "Projects")
      - D:\\Projects         -> ("D", "Projects")
      - d:Projects           -> ("D", "Projects")  # user-friendly, not cmd.exe semantics
      - /d/Projects          -> ("D", "Projects")
    """
    raw = strip_outer_quotes(path).strip()
    if not raw:
        return None

    # WSL mount path.
    m = re.match(r"^/mnt/([a-zA-Z])(?:/(.*))?$", raw)
    if m:
        return m.group(1).upper(), m.group(2) or ""

    # Optional slash drive shorthand: /d/Projects.
    m = re.match(r"^/([a-zA-Z])/(.+)$", raw)
    if m:
        return m.group(1).upper(), m.group(2)

    # Native Windows path or forgiving d:Projects form.
    m = re.match(r"^([a-zA-Z]):[\\/]?(.*)$", raw)
    if m:
        return m.group(1).upper(), m.group(2) or ""

    # Friendly shorthand requested by users: d/Projects or d\\Projects.
    # Do not treat './d/Projects' or '../d/Projects' as drive aliases.
    m = re.match(r"^([a-zA-Z])[\\/](.+)$", raw)
    if m:
        return m.group(1).upper(), m.group(2)

    return None


def to_windows_path(path: str | None) -> str | None:
    """Convert common user path forms to a Windows path for Everything.

    This is intentionally forgiving because eskit is often called from WSL, PowerShell,
    Git Bash, or by scripts that may emit any of these forms:

      /mnt/d/Projects == d/Projects == D:/Projects == D:\\Projects
    """
    if path is None:
        return None
    raw = strip_outer_quotes(path)
    parsed = split_drive_alias(raw)
    if not parsed:
        return raw
    drive, rest = parsed
    rest = rest.replace("/", "\\").lstrip("\\")
    return f"{drive}:\\{rest}" if rest else f"{drive}:\\"


def to_wsl_path(path: str | None) -> str | None:
    """Convert common Windows drive path forms to /mnt/<drive>/... for WSL local checks."""
    if path is None:
        return None
    raw = strip_outer_quotes(path)
    parsed = split_drive_alias(raw)
    if not parsed:
        return raw
    drive, rest = parsed
    rest = rest.replace("\\", "/").lstrip("/")
    return f"/mnt/{drive.lower()}/{rest}" if rest else f"/mnt/{drive.lower()}"


# Backwards-compatible names kept for old imports/docs.
def wsl_to_windows_path(path: str | None) -> str | None:
    return to_windows_path(path)


def windows_to_wsl_path(path: str | None) -> str | None:
    return to_wsl_path(path)


def to_everything_path(path: str | None) -> str | None:
    """Normalize a user path for Everything search text."""
    if path is None:
        return None
    raw = strip_outer_quotes(path)
    parsed = split_drive_alias(raw)
    if parsed:
        return to_windows_path(raw)
    if is_wsl():
        return to_windows_path(raw)
    return raw


def to_local_path(path: str | None) -> str | None:
    """Normalize a result path for local Python filesystem operations."""
    if path is None:
        return None
    raw = strip_outer_quotes(path)
    if is_wsl() or split_drive_alias(raw):
        return to_wsl_path(raw)
    return raw


def display_path_equivalence(path: str) -> dict[str, str | None]:
    """Return path forms useful for doctor/debug JSON output."""
    return {
        "input": path,
        "everything": to_everything_path(path),
        "local": to_local_path(path),
    }


def windows_process_running(process_name: str) -> bool | None:
    """Best-effort check for a Windows process from WSL/Windows.

    Returns None if PowerShell is unavailable.
    """
    ps = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not ps:
        return None
    name = process_name.rsplit(".", 1)[0]
    try:
        proc = subprocess.run(
            [
                ps,
                "-NoProfile",
                "-Command",
                f"if (Get-Process -Name '{name}' -ErrorAction SilentlyContinue) {{ '1' }} else {{ '0' }}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    return proc.stdout.strip().endswith("1")


def parse_size(text: str) -> int:
    s = text.strip().lower().replace(" ", "")
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([kmgt]?b?|)", s)
    if not m:
        raise ValueError(f"Invalid size: {text!r}. Examples: 500MB, 1GB, 1024")
    num = float(m.group(1))
    unit = m.group(2) or "b"
    return int(num * SIZE_UNITS[unit])


def human_size(n: int | None) -> str:
    if n is None:
        return ""
    value = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


def normalize_path(path: str | None) -> str | None:
    if path is None:
        return None
    p = strip_outer_quotes(path)
    if not p:
        return None
    # Keep drive aliases semantic instead of letting pathlib turn d/Projects into a Linux relative path.
    if split_drive_alias(p):
        return to_windows_path(p)
    return str(Path(p))


def quote_everything_token(text: str) -> str:
    # Everything search tokens tolerate quoted paths. Escape double-quotes conservatively.
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def since_expression(days: int | None = None, hours: int | None = None) -> str:
    if days is None and hours is None:
        days = 7
    delta = timedelta(days=days or 0, hours=hours or 0)
    dt = datetime.now() - delta
    # Everything supports date-like comparisons in common installations. We still verify in Python.
    return f"dm:>{dt.strftime('%Y-%m-%d')}"


def find_executable(name: str) -> str | None:
    env_path = os.environ.get("ESKIT_ES_PATH")
    if env_path:
        return env_path
    found = shutil.which(name)
    if found:
        return found
    candidates = [
        Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps" / name,
        Path("C:/Program Files/Everything") / name,
        Path("C:/Program Files (x86)/Everything") / name,
        Path("/mnt/c/Program Files/Everything") / name,
        Path("/mnt/c/Program Files (x86)/Everything") / name,
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def platform_info() -> dict[str, str | bool]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "is_wsl": is_wsl(),
    }


def open_in_file_manager(path: str) -> None:
    if is_wsl():
        win_path = to_windows_path(path) if split_drive_alias(path) or path.startswith("/mnt/") else path
        subprocess.Popen(["explorer.exe", win_path])
        return
    if sys.platform.startswith("win"):
        p = str(Path(path))
        if Path(p).is_file():
            subprocess.Popen(["explorer", "/select,", p])
        else:
            os.startfile(p)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
