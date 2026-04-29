# eskit command reference

## Daily syntax

```text
eskit [盘符/路径 ...] [文件类型 ...] [文件名 ...] [对结果的处理]
```

Examples:

```powershell
eskit .pdf ODL
eskit d .pdf ODL
eskit d e .jpg .png ODL
eskit d/Projects .pdf 开题
eskit /mnt/d/Projects .pdf ODL
```

A plain search opens the keyboard selector in a real terminal. Use `--table`, `--json`, `--ndjson`, `--export`, `--stats`, or `--count` for non-selector output.

## Keyboard selector

```powershell
eskit .pdf ODL
eskit d .pdf ODL
```

Controls:

```text
Up/Down     choose result or menu item
Right       more actions
Left        close action menu or page up
Enter       run action
Esc         exit
```

After any action, eskit exits.

Table-only output:

```powershell
eskit d .pdf ODL --table
eskit d .pdf ODL --no-select
```

## Drive/path tokens

```text
d                 -> D:\
d/Projects        -> D:\Projects
/mnt/d/Projects   -> D:\Projects
D:/Projects       -> D:\Projects
```

Multiple roots:

```powershell
eskit d e g .pdf ODL
```

## File type tokens

```powershell
eskit .pdf ODL
eskit .jpg .png ODL
eskit .pdf .docx .pptx 开题
```

## Filename tokens

```powershell
eskit .pdf ODL
eskit .pdf 开题 报告
eskit d .jpg screenshot ODL
```

Fuzzy and pinyin-initial matching are enabled by default. Disable them with:

```powershell
eskit .pdf ODL --no-fuzzy
```

## Actions

```powershell
eskit d .pdf ODL --open --index 2
eskit d .pdf ODL --reveal
eskit d .pdf ODL --copy-path
eskit d .pdf ODL --copy-name
eskit d .pdf ODL --copy-to d/Temp
```

Only one action can be used at a time.

## Sorting

```powershell
eskit d .pdf ODL --sort name --table
eskit d .pdf ODL --sort path --table
eskit d .pdf ODL --sort ext --table
eskit d .pdf ODL --sort size --desc --table
eskit d .pdf ODL --sort modified --top 20
```

| Option | Meaning |
|---|---|
| `--sort name` | Sort by filename |
| `--sort path` | Sort by full path |
| `--sort ext` | Sort by extension/file type |
| `--sort size` | Sort by file size; default descending |
| `--sort modified` | Sort by modified time; default newest first |
| `--asc` / `--desc` | Force direction |
| `--top N` | Keep first N results after sorting |

## Statistics

```powershell
eskit d .pdf ODL --count
eskit d .pdf ODL --stats
eskit d .jpg .png screenshot --stats
```

`--stats` groups results by kind, extension, and drive, and shows known total size.

## Output

```powershell
eskit d .pdf ODL --table
eskit d .pdf ODL --json
eskit d .pdf ODL --ndjson
eskit d .pdf ODL --export result.md
eskit d .pdf ODL --export result.csv
eskit d .pdf ODL --export result.json
eskit d .pdf ODL --debug
```

## Maintenance commands

```powershell
eskit doctor
eskit doctor --json
eskit path d/Projects
eskit path /mnt/d/Projects --json
```

Daily usage should use the direct grammar above instead of subcommands.


## 文件夹筛选

```bash
eskit d folder ODL
eskit d dir ODL
eskit d 文件夹 ODL
eskit d ODL --folders
eskit d folder .pdf ODL
```

`folder` / `dir` / `目录` / `文件夹` 是类型过滤词，不会当成文件名关键词。`.pdf` 等扩展名默认代表文件类型。
