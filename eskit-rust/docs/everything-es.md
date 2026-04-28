# Everything / es.exe 依赖说明

`eskit-rust` 本身不负责建立 Windows 文件索引。它调用 Windows 端的 Everything 和官方命令行工具 `es.exe`。

## 官方链接

- Everything 官网：https://www.voidtools.com/
- Everything 下载页：https://www.voidtools.com/downloads/
- Everything 命令行接口文档：https://www.voidtools.com/support/everything/command_line_interface/
- es.exe GitHub 仓库：https://github.com/voidtools/ES
- Everything 1.5 Alpha：https://www.voidtools.com/everything-1.5a/

## 安装流程

1. 在 Windows 安装 Everything。
2. 启动 Everything GUI/search client。
3. 下载 Everything Command-line Interface，即 ES zip 包。
4. 解压得到 `es.exe`。
5. 在 WSL 中设置 `ESKIT_ES_PATH`。

示例：

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
eskit doctor
```

## 为什么需要 Everything 正在运行

`es.exe` 是 Everything 的命令行接口，它通过 Everything IPC 与正在运行的 Everything 搜索客户端通信。

如果 Everything 没启动，会出现：

```text
Error 8: Everything IPC not found. Please make sure Everything is running.
```

解决：在 Windows 端启动 Everything，然后重新执行：

```bash
eskit doctor
```
