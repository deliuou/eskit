from __future__ import annotations

import math
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.prompt import Prompt

from .actions import copy_file_to, copy_text_to_clipboard, open_path, reveal_in_file_manager
from .fuzzy import basename_any, dirname_any, extension_any
from .models import EsKitResponse, SearchResult
from .util import human_size

# A compact Listary-like palette.  The UI intentionally avoids j/k/number
# shortcuts in the visible hints; arrow keys are the main interaction model.
_LISTARY_STYLE = Style.from_dict(
    {
        "bar": "bg:#2e3440 #eceff4",
        "query": "bg:#2e3440 bold #ffffff",
        "count": "bg:#2e3440 #d8dee9",
        "hint": "#6b7280",
        "muted": "#8a8f98",
        "divider": "#3b4252",
        "badge": "bg:#4c566a #eceff4",
        "folder.badge": "bg:#a3be8c #1f2937",
        "pdf.badge": "bg:#b48ead #ffffff",
        "image.badge": "bg:#5e81ac #ffffff",
        "code.badge": "bg:#88c0d0 #0f172a",
        "name": "#e5e7eb",
        "path": "#8a8f98",
        "meta": "#9ca3af",
        "selected.name": "bg:#3b4252 bold #ffffff",
        "selected.path": "bg:#3b4252 #d8dee9",
        "selected.meta": "bg:#3b4252 #e5e7eb",
        "selected.badge": "bg:#81a1c1 #111827",
        "selector": "#88c0d0 bold",
        "action.title": "bold #ebcb8b",
        "action": "#e5e7eb",
        "action.selected": "bg:#4c566a bold #ffffff",
        "status": "#a3be8c",
        "warning": "#ebcb8b",
    }
)

_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "tif", "tiff", "svg"}
_CODE_EXTS = {"py", "js", "ts", "tsx", "jsx", "f90", "f", "c", "cpp", "h", "hpp", "wl", "md", "json", "yaml", "yml", "toml"}


def _kind_label(result: SearchResult) -> tuple[str, str]:
    if result.kind == "folder":
        return "DIR", "class:folder.badge"
    ext = extension_any(result.path).lower()
    if ext == "pdf":
        return "PDF", "class:pdf.badge"
    if ext in _IMAGE_EXTS:
        return ext[:4].upper(), "class:image.badge"
    if ext in _CODE_EXTS:
        return ext[:4].upper(), "class:code.badge"
    if ext:
        return ext[:4].upper(), "class:badge"
    return "FILE", "class:badge"


def _truncate_middle(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    left = max(1, width // 2 - 1)
    right = max(1, width - left - 1)
    return text[:left] + "…" + text[-right:]


def _pad(text: str, width: int) -> str:
    if len(text) >= width:
        return text[:width]
    return text + " " * (width - len(text))


def _meta(result: SearchResult) -> str:
    bits: list[str] = []
    if result.kind != "folder" and result.size_bytes is not None:
        bits.append(human_size(result.size_bytes))
    if result.modified:
        bits.append(result.modified[:10])
    return " · ".join(bits)


def listary_results(response: EsKitResponse, *, initial_query: str | None = None) -> None:
    """Listary-like fullscreen result picker.

    Behavior:
      - Up/Down: choose a result/action
      - Left/Right: close/open the action panel or flip pages
      - Enter: run the current action
      - Esc: return

    After any real action (open, reveal, copy path/name, copy file) the picker
    exits immediately.  This mirrors launcher behavior: search -> act -> done.
    """
    console = Console()
    if not response.results:
        console.print(f"[yellow]No results:[/] {response.query or ''}")
        if response.warnings:
            for w in response.warnings:
                console.print(f"[yellow]• {w}[/]")
        return

    selected = 0
    action_selected = 0
    in_actions = False
    warning = "\n".join(response.warnings[:3]) if response.warnings else ""
    actions = [
        ("open", "打开"),
        ("reveal", "打开所在位置"),
        ("copy_path", "复制路径"),
        ("copy_name", "复制文件名"),
        ("copy_file", "复制文件到..."),
    ]

    kb = KeyBindings()
    app: Optional[Application] = None

    def page_size() -> int:
        if app is None:
            return 8
        # Each result uses two lines; leave room for header, hint and action panel.
        return max(4, min(10, (app.output.get_size().rows - 8) // 2))

    def invalidate() -> None:
        if app is not None:
            app.invalidate()

    def move_to(value: int) -> None:
        nonlocal selected
        selected = max(0, min(len(response.results) - 1, value))
        invalidate()

    def move_action(value: int) -> None:
        nonlocal action_selected
        action_selected = max(0, min(len(actions) - 1, value))
        invalidate()

    def current() -> SearchResult:
        return response.results[selected]

    def run_action(action: str, event) -> None:  # noqa: ANN001
        result = current()
        path = result.path
        try:
            if action == "open":
                open_path(path)
                event.app.exit(result=("done", f"已打开：{basename_any(path)}"))
            elif action == "reveal":
                reveal_in_file_manager(path)
                event.app.exit(result=("done", f"已打开所在位置：{basename_any(path)}"))
            elif action == "copy_path":
                copy_text_to_clipboard(path)
                event.app.exit(result=("done", "已复制文件路径"))
            elif action == "copy_name":
                copy_text_to_clipboard(basename_any(path))
                event.app.exit(result=("done", "已复制文件名"))
            elif action == "copy_file":
                event.app.exit(result=("copy_file", path))
        except Exception as exc:  # noqa: BLE001
            event.app.exit(result=("error", f"操作失败：{exc}"))

    @kb.add("up")
    def _up(event) -> None:  # noqa: ANN001
        if in_actions:
            move_action(action_selected - 1)
        else:
            move_to(selected - 1)

    @kb.add("down")
    def _down(event) -> None:  # noqa: ANN001
        if in_actions:
            move_action(action_selected + 1)
        else:
            move_to(selected + 1)

    @kb.add("left")
    def _left(event) -> None:  # noqa: ANN001
        nonlocal in_actions
        if in_actions:
            in_actions = False
            invalidate()
        else:
            move_to(selected - page_size())

    @kb.add("right")
    def _right(event) -> None:  # noqa: ANN001
        nonlocal in_actions
        in_actions = True
        invalidate()

    @kb.add("pageup")
    def _pageup(event) -> None:  # noqa: ANN001
        move_to(selected - page_size())

    @kb.add("pagedown")
    def _pagedown(event) -> None:  # noqa: ANN001
        move_to(selected + page_size())

    @kb.add("enter")
    def _enter(event) -> None:  # noqa: ANN001
        if in_actions:
            run_action(actions[action_selected][0], event)
        else:
            run_action("open", event)

    @kb.add("escape")
    def _escape(event) -> None:  # noqa: ANN001
        nonlocal in_actions
        if in_actions:
            in_actions = False
            invalidate()
        else:
            event.app.exit(result=None)

    @kb.add("c-c")
    def _ctrl_c(event) -> None:  # noqa: ANN001
        event.app.exit(result=None)

    def render() -> FormattedText:
        assert app is not None
        size = app.output.get_size()
        width = max(72, size.columns)
        ps = page_size()
        page = selected // ps
        start = page * ps
        end = min(len(response.results), start + ps)
        total_pages = max(1, math.ceil(len(response.results) / ps))
        query = initial_query or response.query or ""
        header_width = min(width - 1, 118)
        name_width = max(20, min(62, width - 28))
        path_width = max(26, min(100, width - 11))
        meta_width = 20

        parts: list[tuple[str, str]] = []
        # Launcher-style query bar.
        q = _truncate_middle(query, max(12, header_width - 34))
        suffix = f" {len(response.results)} 个结果 · {page + 1}/{total_pages} "
        parts.append(("class:bar", " eskit "))
        parts.append(("class:query", q))
        parts.append(("class:count", suffix))
        remaining = max(0, header_width - len(" eskit ") - len(q) - len(suffix))
        parts.append(("class:bar", " " * remaining + "\n"))
        parts.append(("class:hint", "  方向键选择 · 右方向键更多操作 · Enter 执行 · Esc 退出\n"))
        parts.append(("class:divider", "─" * header_width + "\n"))

        for idx in range(start, end):
            r = response.results[idx]
            name = basename_any(r.path)
            parent = dirname_any(r.path)
            label, badge_style = _kind_label(r)
            meta = _truncate_middle(_meta(r), meta_width)
            is_selected = idx == selected
            selector_style = "class:selector" if is_selected else ""
            name_style = "class:selected.name" if is_selected else "class:name"
            path_style = "class:selected.path" if is_selected else "class:path"
            meta_style = "class:selected.meta" if is_selected else "class:meta"
            active_badge = "class:selected.badge" if is_selected else badge_style
            prefix = " ❯ " if is_selected else "   "

            first_line_width = max(10, header_width - 4)
            name_part_width = max(8, first_line_width - 11 - meta_width)
            parts.append((selector_style, prefix))
            parts.append((active_badge, f" {_pad(label, 4)} "))
            parts.append(("", "  "))
            parts.append((name_style, _pad(_truncate_middle(name, name_part_width), name_part_width)))
            parts.append((meta_style, _pad(meta, meta_width)))
            parts.append(("", "\n"))
            parts.append(("", "     "))
            parts.append((path_style, _truncate_middle(parent, path_width)))
            parts.append(("", "\n"))

        if in_actions:
            parts.append(("class:divider", "\n" + "─" * header_width + "\n"))
            parts.append(("class:action.title", "  更多操作\n"))
            for idx, (_, label) in enumerate(actions):
                marker = " ❯ " if idx == action_selected else "   "
                style = "class:action.selected" if idx == action_selected else "class:action"
                parts.append((style, f"{marker}{label}\n"))
        if warning:
            parts.append(("class:warning", "\n" + warning + "\n"))
        return FormattedText(parts)

    control = FormattedTextControl(render, focusable=True)
    root = Window(content=control, always_hide_cursor=True, wrap_lines=False)
    app = Application(layout=Layout(root), key_bindings=kb, style=_LISTARY_STYLE, full_screen=True, mouse_support=False)

    result = app.run()
    if result is None:
        return
    if isinstance(result, tuple) and result[0] == "copy_file":
        src = result[1]
        destination = Prompt.ask("复制到目标文件夹或目标文件路径")
        try:
            final_path = copy_file_to(src, destination)
            console.print(f"[green]已复制文件到：[/]{final_path}")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]复制失败：[/]{exc}")
        return
    if isinstance(result, tuple) and result[0] == "done":
        console.print(f"[green]{result[1]}[/]")
        return
    if isinstance(result, tuple) and result[0] == "error":
        console.print(f"[red]{result[1]}[/]")
        return
