from eskit.util import (
    human_size,
    parse_size,
    quote_everything_token,
    to_everything_path,
    to_local_path,
    to_windows_path,
    to_wsl_path,
)


def test_parse_size():
    assert parse_size("1KB") == 1024
    assert parse_size("1.5MB") == int(1.5 * 1024 * 1024)
    assert parse_size("1024") == 1024


def test_human_size():
    assert human_size(1024) == "1.0 KB"
    assert human_size(None) == ""


def test_quote_everything_token():
    assert quote_everything_token("D:/My Files") == '"D:/My Files"'


def test_drive_alias_to_windows_path():
    assert to_windows_path("/mnt/d/Projects") == r"D:\Projects"
    assert to_windows_path("d/Projects") == r"D:\Projects"
    assert to_windows_path(r"d\Projects") == r"D:\Projects"
    assert to_windows_path("D:/Projects") == r"D:\Projects"
    assert to_windows_path(r"D:\Projects") == r"D:\Projects"
    assert to_windows_path("d:Projects") == r"D:\Projects"


def test_drive_alias_to_wsl_path():
    assert to_wsl_path("/mnt/d/Projects") == "/mnt/d/Projects"
    assert to_wsl_path("d/Projects") == "/mnt/d/Projects"
    assert to_wsl_path(r"D:\Projects") == "/mnt/d/Projects"


def test_everything_and_local_path_aliases():
    assert to_everything_path("d/Projects") == r"D:\Projects"
    assert to_local_path("d/Projects") == "/mnt/d/Projects"
