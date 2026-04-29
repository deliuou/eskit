from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .util import is_wsl, split_drive_alias, to_local_path, to_windows_path


def _as_windows_for_shell(path: str) -> str:
    if split_drive_alias(path) or path.startswith('/mnt/'):
        return to_windows_path(path) or path
    return path


def _as_local_for_python(path: str) -> str:
    return to_local_path(path) or path


def open_path(path: str) -> None:
    """Open a file/folder with the OS default application."""
    if is_wsl():
        win_path = _as_windows_for_shell(path)
        subprocess.Popen(['cmd.exe', '/C', 'start', '', win_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if sys.platform.startswith('win'):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', _as_local_for_python(path)])


def reveal_in_file_manager(path: str) -> None:
    """Open the containing folder and select the item when the platform supports it."""
    if is_wsl():
        win_path = _as_windows_for_shell(path)
        subprocess.Popen(['explorer.exe', f'/select,{win_path}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if sys.platform.startswith('win'):
        subprocess.Popen(['explorer', f'/select,{path}'])
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', '-R', path])
    else:
        local = Path(_as_local_for_python(path))
        folder = local if local.is_dir() else local.parent
        subprocess.Popen(['xdg-open', str(folder)])


def copy_text_to_clipboard(text: str) -> None:
    """Copy text to clipboard using platform-native tools where possible."""
    if is_wsl():
        ps = shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        if ps:
            subprocess.run(
                [ps, '-NoProfile', '-Command', 'Set-Clipboard -Value $input'],
                input=text,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        clip = shutil.which('clip.exe')
        if clip:
            subprocess.run([clip], input=text, text=True, check=True)
            return
    if sys.platform.startswith('win'):
        subprocess.run(['powershell', '-NoProfile', '-Command', 'Set-Clipboard -Value $input'], input=text, text=True, check=True)
        return
    if sys.platform == 'darwin':
        subprocess.run(['pbcopy'], input=text, text=True, check=True)
        return
    for cmd in (['wl-copy'], ['xclip', '-selection', 'clipboard'], ['xsel', '--clipboard', '--input']):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text, text=True, check=True)
            return
    raise RuntimeError('No clipboard command found. Install wl-copy, xclip, or xsel.')


def copy_file_to(src: str, destination: str) -> str:
    """Copy a file to a destination file or folder. Returns the final path."""
    src_path = Path(_as_local_for_python(src))
    dst_path = Path(_as_local_for_python(destination))
    if not src_path.exists():
        raise FileNotFoundError(f'Source does not exist: {src}')
    if src_path.is_dir():
        raise IsADirectoryError('copy_file_to expects a file; use the file manager for folders.')
    if dst_path.exists() and dst_path.is_dir():
        dst_path = dst_path / src_path.name
    elif str(destination).endswith(('/', '\\')):
        dst_path.mkdir(parents=True, exist_ok=True)
        dst_path = dst_path / src_path.name
    else:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dst_path)
    return str(dst_path)
