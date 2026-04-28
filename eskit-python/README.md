# eskit (Python 版本)

`eskit-python` 是一个 **WSL 优先** 的 Windows 文件搜索命令行工具。

它不重新实现搜索引擎，而是调用 Windows 端的 **Everything / es.exe**，让你在 WSL 里用接近 Listary 的语法快速搜索 Windows 磁盘文件。

安装后的命令仍然叫：

```bash
eskit
```

核心语法：

```bash
eskit [盘符/路径 ...] [文件类型 ...] [文件名关键词 ...] [对结果的处理]
```

例如：

```bash
eskit d .pdf ODL
eskit d f .pdf .pptx ODL
eskit d folder ODL
eskit d/Projects .jpg screenshot --sort modified --top 20
eskit d .pdf 开题 --copy-path --index 2
```

---

## 这个项目解决什么问题

Windows 端 Everything 搜索速度很快，但在 WSL 里日常使用时会遇到几个问题：

1. `es.exe` 原生命令语法偏底层，不适合每天手敲；
2. WSL 路径 `/mnt/d/Projects` 和 Windows 路径 `D:\\Projects` 需要来回转换；
3. 希望能像 Listary 一样输入几个词就筛选文件；
4. 搜索后经常还要打开文件、打开所在位置、复制路径、复制文件；
5. 脚本和 AI agent 更希望拿到 JSON / NDJSON 输出。

`eskit-python` 的定位就是：

> 在 WSL 中搜索 Windows 文件的 Everything/es.exe 友好包装器。

---

## 和 Everything / es.exe 的关系

`eskit-python` 依赖以下两个 Windows 工具：

| 工具 | 作用 |
|---|---|
| Everything | Windows 端文件索引和搜索引擎 |
| es.exe | Everything 官方命令行接口 |
| eskit-python | 面向 WSL/命令行日常使用的语法包装、路径转换、排序、统计、选择和动作层 |

官方资源：

- Everything 官网：https://www.voidtools.com/
- Everything 下载页：https://www.voidtools.com/downloads/
- Everything 命令行接口文档：https://www.voidtools.com/support/everything/command_line_interface/
- es.exe GitHub 仓库：https://github.com/voidtools/ES
- Everything 1.5 Alpha：https://www.voidtools.com/everything-1.5a/

注意：`es.exe` 需要 Windows 端 Everything 正在运行。如果 `eskit doctor` 出现 `Error 8: Everything IPC not found`，通常表示 Everything GUI/search client 没有启动。

---

## 安装前准备：Windows 端

### 1. 安装 Everything

去 Everything 下载页安装 Everything：

```
https://www.voidtools.com/downloads/
```

推荐安装正常版本，并开启 Everything Service。

### 2. 安装 es.exe

同一个下载页里有：

```
Download Everything Command-line Interface
```

下载对应架构的 `ES-*.zip`，解压得到 `es.exe`。

常见放置方式：

```
C:\Users\<你的用户名>\AppData\Local\Microsoft\WindowsApps\es.exe
```

或者放到你自己的软件目录，例如：

```
I:\Software\Everything\es.exe
```

### 3. 确认 Windows 端可用

在 PowerShell 里测试：

```powershell
es.exe -n 5 "*.pdf"
```

如果这个命令能输出结果，说明 Everything 和 es.exe 基本正常。

---

## 安装 eskit-python

### 开发安装

```bash
git clone https://github.com/deliuou/eskit.git
cd eskit/eskit-python
python -m pip install -e .
eskit doctor
```

### 指定 es.exe 路径

在 WSL 里，如果 `eskit doctor` 找不到 `es.exe`，设置：

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
```

建议写入 `~/.bashrc`：

```bash
echo 'export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe' >> ~/.bashrc
source ~/.bashrc
```

然后检查：

```bash
eskit doctor
```

如果使用 Everything 1.5 Alpha：

```bash
eskit doctor --instance 1.5a
export ESKIT_ES_INSTANCE=1.5a
```

---

## 快速开始

### 搜索 PDF

```bash
eskit .pdf ODL
```

### 限定 D 盘搜索

```bash
eskit d .pdf ODL
```

### 同时搜索 D 盘和 F 盘

```bash
eskit d f .pdf ODL
```

### 同时搜索 PDF 和 PPTX

```bash
eskit d f .pdf .pptx ODL
```

### 搜索文件夹

```bash
eskit d folder ODL
eskit d dir ODL
eskit d 文件夹 ODL
eskit d 目录 ODL
```

### 同时搜索文件夹和文件

```bash
eskit d folder .pdf ODL
```

### 排序并取前 10 个

```bash
eskit d f .pdf .pptx ODL --sort size --top 10
eskit d f .pdf .pptx ODL --sort modified --top 10
```

### 统计结果

```bash
eskit d f .pdf .pptx ODL --stats
```

### 只输出数量

```bash
eskit d f .pdf .pptx ODL --count
```

### 输出 JSON

```bash
eskit d .pdf ODL --json
eskit d .pdf ODL --ndjson
```

---

## 路径语法

`eskit-python` 会自动把 WSL 路径、盘符简写和 Windows 路径统一成 Everything 能理解的 Windows 路径。

| 输入 | 等价路径 |
|---|---|
| `d` | `D:\\` |
| `f` | `F:\\` |
| `d/Projects` | `D:\\Projects` |
| `/mnt/d/Projects` | `D:\\Projects` |
| `D:/Projects` | `D:\\Projects` |
| `D:\\Projects` | `D:\\Projects` |

检查路径转换：

```bash
eskit path d
eskit path d/Projects
eskit path /mnt/d/Projects
```

---

## 文件类型语法

### 扩展名筛选

```bash
eskit .pdf ODL
eskit .jpg ODL
eskit .jpg .png screenshot
eskit .pdf .docx .pptx 开题
```

### 文件夹筛选

```bash
eskit d folder ODL
eskit d dir ODL
eskit d 文件夹 ODL
eskit d 目录 ODL
```

### 只要文件 / 只要文件夹

```bash
eskit d ODL --files
eskit d ODL --folders
```

---

## 文件名关键词

剩下没有被识别成盘符、路径、文件类型或参数的内容，都会被当成文件名关键词。

```bash
eskit d .pdf ODL
eskit d .pdf 开题 报告
eskit d .jpg 微信 截图
```

默认启用模糊匹配和拼音首字母匹配。例如 `ODL` 可以匹配中文文件名的拼音首字母。

关闭模糊匹配：

```bash
eskit d .pdf ODL --no-fuzzy
```

强制开启模糊候选扫描：

```bash
eskit d ODL --fuzzy
```

---

## 搜索后的键盘选择

在真实终端中，普通搜索会进入一个轻量的选择界面：

```bash
eskit d .pdf ODL
```

操作逻辑：

```
↑ / ↓      选择结果
→          更多操作
Enter      执行默认动作
Esc        退出
```

执行任何动作后都会自动退出。

如果只想输出表格：

```bash
eskit d .pdf ODL --table
eskit d .pdf ODL --no-select
```

---

## 对搜索结果的处理

动作默认作用于第 1 个结果，可以用 `--index N` 指定第 N 个结果。

```bash
eskit d .pdf ODL --open
eskit d .pdf ODL --open --index 2
eskit d .pdf ODL --reveal
eskit d .pdf ODL --copy-path
eskit d .pdf ODL --copy-name
eskit d .pdf ODL --copy-to d/Temp
```

| 参数 | 作用 |
|---|---|
| `--open` | 打开选中的文件或文件夹 |
| `--reveal` | 在资源管理器中打开所在位置 |
| `--copy-path` | 复制完整路径 |
| `--copy-name` | 复制文件名 |
| `--copy-to DIR` | 复制文件到指定目录 |
| `--index N` | 指定第 N 个结果 |

---

## 排序、Top、统计

### 排序

```bash
eskit d .pdf ODL --sort name
eskit d .pdf ODL --sort path
eskit d .pdf ODL --sort ext
eskit d .pdf ODL --sort size
eskit d .pdf ODL --sort modified
```

| 排序键 | 含义 | 默认方向 |
|---|---|---|
| `name` | 文件名 | 升序 |
| `path` | 完整路径 | 升序 |
| `ext` | 扩展名 | 升序 |
| `size` | 文件大小 | 降序 |
| `modified` | 修改时间 | 降序 |

指定方向：

```bash
eskit d .pdf ODL --sort size --asc
eskit d .pdf ODL --sort modified --desc
```

取前 N 个：

```bash
eskit d f .pdf .pptx ODL --sort size --top 10
```

### 统计

```bash
eskit d f .pdf .pptx ODL --stats
```

统计内容包括：

- 结果数量；
- 已知总大小；
- 文件 / 文件夹数量；
- 扩展名分布；
- 盘符分布。

只输出数量：

```bash
eskit d f .pdf .pptx ODL --count
```

---

## 导出和脚本化输出

```bash
eskit d .pdf ODL --json
eskit d .pdf ODL --ndjson
eskit d .pdf ODL --export result.md
eskit d .pdf ODL --export result.csv
eskit d .pdf ODL --export result.json
eskit d .pdf ODL --export result.txt
```

适合脚本或 agent 调用的例子：

```bash
eskit d f .pdf .pptx ODL --json --limit 20
eskit d .jpg screenshot --ndjson
eskit d .pdf ODL --copy-path --index 1 --json
```

---

## 诊断

```bash
eskit doctor
```

常见问题：

### 1. 找不到 es.exe

设置：

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
```

### 2. Error 8: Everything IPC not found

启动 Windows 端 Everything。注意：Everything Service 不等于 Everything 搜索客户端，`es.exe` 需要 Everything GUI/search client 正在运行。

### 3. Everything 1.5 Alpha

```bash
eskit doctor --instance 1.5a
export ESKIT_ES_INSTANCE=1.5a
```

### 4. 调试实际查询

```bash
eskit d f .pdf .pptx ODL --debug --table
```

---

## 设计原则

- WSL 优先；
- 不替代 Everything，只增强 es.exe 的日常体验；
- 一个直接语法，不需要复杂子命令；
- 支持多盘符、多文件类型、多关键词；
- 支持文件夹筛选；
- 搜索后可以排序、统计、导出、复制、打开；
- JSON / NDJSON 是一等输出，方便脚本和 agent；
- 默认动作尽量安全。

---

## License

MIT
