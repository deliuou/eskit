# WSL usage

`eskit` can run from WSL while using Windows `es.exe`.

Set the `es.exe` path if it is not on PATH:

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
```

Start Everything on Windows before using `eskit`:

```bash
powershell.exe -NoProfile -Command "Start-Process 'I:\Software\Everything\Everything.exe'"
```

Path aliases are normalized:

```text
d                 -> D:\
d/Projects        -> D:\Projects
/mnt/d/Projects   -> D:\Projects
```

Examples:

```bash
eskit d .pdf ODL
eskit d/Projects .jpg screenshot
eskit /mnt/d/Projects .pdf ODL --json
```
