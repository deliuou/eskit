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

