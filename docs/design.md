# Design

`eskit` wraps Everything `es.exe` with a predictable grammar:

```text
eskit [drive/path ...] [file-type ...] [filename ...] [action options]
```

The parser classifies tokens in this order:

1. Drive/path tokens: `d`, `d/Projects`, `/mnt/d/Projects`, `D:/Projects`.
2. File type tokens: `.pdf`, `*.jpg`, `.jpg;.png`.
3. Filename tokens: everything else.

The search layer runs multiple attempts:

1. Everything `ext:` search.
2. Wildcard fallback for single file type.
3. Optional fuzzy/pinyin fallback over extension-filtered candidates.

The UI layer is intentionally not exposed as a separate `tui` command. A normal search opens a compact keyboard selector in a real terminal; table/JSON/export/stats/count modes disable the selector.

Result processing happens after search:

1. Optional metadata enrichment for size/modified sorting and statistics.
2. Optional sorting and trimming with `--sort` and `--top`.
3. Optional one-shot action such as open/reveal/copy.
4. Optional output such as table/JSON/export/stats/count.
