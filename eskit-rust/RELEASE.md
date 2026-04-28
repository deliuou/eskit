# eskit-rust v0.1.0

Rust rewrite of eskit-python.

## Highlights

- Same direct grammar: `eskit [drive/path ...] [file-type ...] [filename ...] [actions]`
- WSL path aliases: `d`, `d/Projects`, `/mnt/d/Projects`, `D:/Projects`
- Multi-drive and multi-extension search: `eskit d f .pdf .pptx ODL`
- Folder filtering: `folder`, `dir`, `目录`, `--folders`
- Sorting, top, count, stats, JSON/NDJSON/export
- Keyboard selector with arrow keys and action menu
- Open/reveal/copy path/copy name/copy file actions
- WSL-first integration with Windows Everything/es.exe

## Requirements

- Windows Everything running
- `es.exe` installed
- In WSL, set `ESKIT_ES_PATH` if `es.exe` is not in PATH
