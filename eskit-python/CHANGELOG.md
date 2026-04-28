# Changelog

## 1.4.0

- Add folder/type grammar: `folder`, `dir`, `文件夹`, `目录` filter folders.
- Add file/type grammar: `file`, `files`, `文件` filter files.
- Support mixed searches like `eskit d folder .pdf ODL`, which returns matching folders and PDF files.
- Add `--folders`, `--dirs`, and `--directories` aliases for folder-only filtering.


## 1.3.0

- Fixed multi-extension searches such as `eskit d f .pdf .pptx ODL`.
- eskit now queries each extension separately and merges/deduplicates results, avoiding unreliable `ext:pdf;pptx` behavior across Everything/es.exe setups.
- Debug output now shows one attempt per drive and extension, making multi-drive/multi-type searches easier to inspect.


## 1.1.0

- Replaced the root help screen with a detailed direct-grammar usage guide.
- Added `--sort name/path/ext/size/modified` plus `--asc`, `--desc`, and `--top`.
- Added `--count` and `--stats` for common result-processing workflows.
- Hid the old subcommand-first mental model from daily usage; `doctor` and `path` remain as maintenance commands.

## 1.0.0

- Removed standalone `tui`, `interactive`, and `agent` commands.
- Restored keyboard selection as the default behavior for direct searches in a real terminal.
- Added `--table` / `--no-select` for table-only output.
- Added `--select` to force the selector.
- Kept script-friendly `--json`, `--ndjson`, and `--export` modes.

## 0.9.0

- Introduced the direct grammar: `eskit [drive/path ...] [file-type ...] [filename ...] [action options]`.
