# eskit-python v1.5.0

`eskit-python` is a WSL-first Listary-like Windows file search tool powered by Everything / es.exe.

## Highlights

- PyPI package name: `eskit-python`
- CLI command: `eskit`
- Direct grammar: `eskit [drive/path ...] [file-type ...] [filename ...] [actions]`
- WSL path normalization: `d/Projects == /mnt/d/Projects == D:\Projects`
- Multi-drive search: `eskit d f .pdf .pptx ODL`
- Folder filter: `eskit d folder ODL`
- Sorting: `--sort name|path|ext|size|modified`
- Statistics: `--stats`, `--count`
- Result actions: `--open`, `--reveal`, `--copy-path`, `--copy-name`, `--copy-to`
- Script outputs: `--json`, `--ndjson`, `--export`

## Requirements

- Windows Everything must be installed and running.
- Everything command line interface `es.exe` must be installed.
- In WSL, set `ESKIT_ES_PATH` if `es.exe` is not on PATH.

## Quick start

```bash
pipx install eskit-python
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
eskit doctor
eskit d .pdf ODL
```
