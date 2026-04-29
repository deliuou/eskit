# Changelog

## 1.0.0

- Initial GitHub release of the Python `eskit` package.
- Add Listary-like direct grammar: `eskit [drive/path ...] [file-type ...] [filename ...] [actions]`.
- Support WSL-friendly path normalization for `d`, `d/Projects`, `/mnt/d/Projects`, and `D:\Projects`.
- Add multi-drive and multi-extension search with result merging and deduplication.
- Add folder/file filters: `folder`, `dir`, `文件夹`, `目录`, `file`, `files`, and `文件`.
- Add fuzzy and pinyin-initial matching for local result refinement.
- Add sorting, limiting, statistics, and count options.
- Add result actions including open, reveal, copy path/name, and copy-to.
- Add script-friendly `--json`, `--ndjson`, and export modes.

## 0.9.0

- Introduced the direct grammar: `eskit [drive/path ...] [file-type ...] [filename ...] [action options]`.
