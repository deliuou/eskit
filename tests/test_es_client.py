from types import SimpleNamespace

from eskit.es import EsClient


def test_run_raw_requests_utf8_code_page(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0, stdout="D:\\开题.pdf\n".encode(), stderr=b"")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = EsClient(es_path="es.exe").run_raw(["-n", "1", "*.pdf"])

    assert result.ok is True
    assert result.command == ["es.exe", "-cp", "65001", "-n", "1", "*.pdf"]
    assert result.stdout == "D:\\开题.pdf\n"
    assert calls[0][1]["text"] is False


def test_run_raw_falls_back_when_code_page_option_is_unknown(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "-cp" in cmd:
            return SimpleNamespace(returncode=6, stdout=b"", stderr=b"Unknown switch")
        return SimpleNamespace(returncode=0, stdout="D:\\开题.pdf\n".encode("gb18030"), stderr=b"")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = EsClient(es_path="es.exe").run_raw(["-n", "1", "*.pdf"])

    assert calls == [
        ["es.exe", "-cp", "65001", "-n", "1", "*.pdf"],
        ["es.exe", "-n", "1", "*.pdf"],
    ]
    assert result.ok is True
    assert result.command == ["es.exe", "-n", "1", "*.pdf"]
    assert result.stdout == "D:\\开题.pdf\n"
