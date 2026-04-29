import sys

import pytest

from eskit import __version__
from eskit.cli import entrypoint


def test_entrypoint_version_exits_before_typer(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["eskit", "--version"])

    with pytest.raises(SystemExit) as exc:
        entrypoint()

    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_entrypoint_help_uses_direct_search_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["eskit", "--help"])

    with pytest.raises(SystemExit) as exc:
        entrypoint()

    output = capsys.readouterr().out
    assert exc.value.code == 0
    assert "快速语法" in output
    assert "常用例子" in output
    assert "参数速查" in output
    assert "COMMAND [ARGS]" not in output
