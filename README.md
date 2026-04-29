# eskit

`eskit` 是一个面向开发者和重度文件用户的 **Everything / es.exe 命令行增强工具**。它把 Windows 上极快的 Everything 文件索引能力，包装成更适合日常手敲、WSL 使用、脚本自动化和 AI agent 调用的 `eskit` 命令。

安装后使用的命令是：

```bash
eskit
```

核心语法接近 Listary：

```bash
eskit [盘符/路径 ...] [文件类型 ...] [文件名关键词 ...] [对结果的处理]
```

例如：

```bash
eskit d .pdf ODL
eskit d f .pdf .pptx 开题 --sort modified --top 20
eskit d folder report
eskit d/Projects .jpg screenshot --table
eskit d .pdf 开题 --copy-path --index 2
eskit d .pdf ODL --json
```

## 为什么做这个项目

Everything 在 Windows 上搜索文件非常快，但开发者在 WSL、终端、脚本和自动化场景里经常会遇到这些问题：

1. `es.exe` 原生命令语法偏底层，日常输入成本高；
2. WSL 路径 `/mnt/d/Projects`、盘符简写 `d/Projects` 和 Windows 路径 `D:\Projects` 需要频繁转换；
3. 想像 Listary 一样输入几个词就快速定位文件；
4. 搜索后常见动作不只是查看结果，还包括打开、定位、复制路径、复制文件；
5. 脚本、CI、小工具和 AI agent 更需要稳定的 JSON / NDJSON 输出。

`eskit` 的定位是：

> 保留 Everything 的速度，把 `es.exe` 变成适合人和程序一起使用的现代命令行搜索接口。

## 适合谁

- 长期使用 Windows + WSL 的开发者；
- 经常在终端里找论文、代码、截图、日志、素材、Office 文档的人；
- 希望用脚本批量处理本机文件搜索结果的人；
- 想给 AI agent、自动化工具或个人工作流提供本地文件搜索能力的人；
- 喜欢 Everything 的速度，但不想每天直接拼 `es.exe` 参数的人。

## 主要特性

| 能力 | 说明 |
|---|---|
| Listary 风格语法 | `eskit d .pdf ODL` 即可表达盘符、类型和关键词 |
| WSL 友好路径 | 自动处理 `d`、`d/Projects`、`/mnt/d/Projects`、`D:\Projects` |
| 多盘符搜索 | `eskit d f .pdf report` |
| 多类型搜索 | `eskit .pdf .docx .pptx 开题` |
| 文件夹筛选 | `folder`、`dir`、`目录`、`文件夹` |
| 文件/文件夹混合搜索 | `eskit d folder .pdf ODL` |
| 模糊和拼音首字母匹配 | 默认启用，适合中文文件名和缩写搜索 |
| 结果动作 | `--open`、`--reveal`、`--copy-path`、`--copy-name`、`--copy-to` |
| 排序和截取 | `--sort size|modified|name|path|ext`、`--top N` |
| 统计和导出 | `--stats`、`--count`、`--export` |
| 程序化输出 | `--json`、`--ndjson`，方便脚本和 agent 消费 |

## 和 Everything / es.exe 的关系

`eskit` 不重新实现文件索引，也不替代 Everything。它依赖 Windows 端的 Everything 和官方命令行工具 `es.exe`。

| 组件 | 作用 |
|---|---|
| Everything | Windows 端文件索引和搜索引擎 |
| es.exe | Everything 官方命令行接口 |
| eskit | 语法包装、路径转换、排序、统计、选择、动作和结构化输出 |

官方资源：

- Everything 官网：https://www.voidtools.com/
- Everything 下载页：https://www.voidtools.com/downloads/
- Everything 命令行接口文档：https://www.voidtools.com/support/everything/command_line_interface/
- es.exe GitHub 仓库：https://github.com/voidtools/ES
- Everything 1.5 Alpha：https://www.voidtools.com/everything-1.5a/

注意：`es.exe` 需要 Windows 端 Everything 搜索客户端正在运行。如果 `eskit doctor` 出现 `Error 8: Everything IPC not found`，通常表示 Everything GUI/search client 没有启动。

## 系统要求

- Python 3.9 或更高版本；
- Windows 上已安装并启动 Everything；
- 已安装 Everything Command-line Interface，也就是 `es.exe`；
- 在 WSL/Linux 使用时，`eskit` 需要能够找到 Windows 端的 `es.exe`。

说明：

- 推荐使用场景是 **WSL/Linux shell 调用 Windows Everything**；
- 原生 Linux 本身没有 Everything 的 Windows 文件索引服务，因此只有在你能访问并执行 Windows 端 `es.exe` 的环境中才有实际意义；
- Windows 原生命令行也可以直接安装和使用 `eskit`。

## 安装前准备：Windows 端

无论你打算在 WSL/Linux 里用，还是在 Windows PowerShell / CMD 里用，都建议先完成 Windows 端准备。

### 1. 安装 Everything

到 Everything 下载页安装 Everything：

```text
https://www.voidtools.com/downloads/
```

推荐安装正常版本，并开启 Everything Service。Everything Service 负责权限和索引相关能力，但 `es.exe` 查询时仍需要 Everything 搜索客户端正在运行。

### 2. 安装 es.exe

在同一个下载页找到：

```text
Download Everything Command-line Interface
```

下载对应架构的 `ES-*.zip`，解压后得到 `es.exe`。

常见放置位置：

```text
C:\Users\<你的用户名>\AppData\Local\Microsoft\WindowsApps\es.exe
C:\Program Files\Everything\es.exe
I:\Software\Everything\es.exe
```

### 3. 确认 es.exe 可用

在 PowerShell 里测试：

```powershell
es.exe -n 5 "*.pdf"
```

如果这个命令可以输出结果，说明 Everything 和 `es.exe` 基本正常。

## 安装：Linux / WSL

这里的 Linux 主要指 WSL。当前推荐直接从 GitHub 源码安装：

```bash
git clone https://github.com/deliuou/eskit.git
cd eskit
python3 -m pip install -e .
```

安装后检查：

```bash
eskit --version
```

### 设置 es.exe 路径

如果 `eskit doctor` 找不到 `es.exe`，在 WSL 中设置 `ESKIT_ES_PATH`：

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
```

建议写入 shell 配置：

```bash
echo 'export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe' >> ~/.bashrc
source ~/.bashrc
```

如果你使用 zsh：

```bash
echo 'export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe' >> ~/.zshrc
source ~/.zshrc
```

然后运行：

```bash
eskit doctor
```

Everything 1.5 Alpha 用户可以指定实例名：

```bash
eskit doctor --instance 1.5a
export ESKIT_ES_INSTANCE=1.5a
```

持久化：

```bash
echo 'export ESKIT_ES_INSTANCE=1.5a' >> ~/.bashrc
```

## 卸载：Linux / WSL

在源码目录或任意目录执行：

```bash
python3 -m pip uninstall eskit
```

如果你之前写入了环境变量，可以从 `~/.bashrc` 或 `~/.zshrc` 中删除这些行：

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
export ESKIT_ES_INSTANCE=1.5a
```

## 安装：Windows

Windows 原生命令行推荐在 PowerShell 中从 GitHub 源码安装：

```powershell
git clone https://github.com/deliuou/eskit.git
cd eskit
py -m pip install -e .
```

安装后检查：

```powershell
eskit --version
eskit doctor
```

### 设置 es.exe 路径

如果 `eskit doctor` 找不到 `es.exe`，可以临时指定：

```powershell
$env:ESKIT_ES_PATH = "I:\Software\Everything\es.exe"
eskit doctor
```

也可以写入用户环境变量：

```powershell
[Environment]::SetEnvironmentVariable("ESKIT_ES_PATH", "I:\Software\Everything\es.exe", "User")
```

重新打开 PowerShell 后生效。

Everything 1.5 Alpha 用户：

```powershell
[Environment]::SetEnvironmentVariable("ESKIT_ES_INSTANCE", "1.5a", "User")
```

## 卸载：Windows

在源码目录或任意目录执行：

```powershell
py -m pip uninstall eskit
```

如果你设置过环境变量，可以删除：

```powershell
[Environment]::SetEnvironmentVariable("ESKIT_ES_PATH", $null, "User")
[Environment]::SetEnvironmentVariable("ESKIT_ES_INSTANCE", $null, "User")
```

如果你不再需要底层搜索能力，可以另外卸载 Everything 和删除 `es.exe`。这不属于 `eskit` 的卸载范围。

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

### 输出 JSON

```bash
eskit d .pdf ODL --json
eskit d .pdf ODL --ndjson
```

## 路径语法

`eskit` 会自动把 WSL 路径、盘符简写和 Windows 路径统一成 Everything 能理解的 Windows 路径。

| 输入 | 等价路径 |
|---|---|
| `d` | `D:\` |
| `f` | `F:\` |
| `d/Projects` | `D:\Projects` |
| `/mnt/d/Projects` | `D:\Projects` |
| `D:/Projects` | `D:\Projects` |
| `D:\Projects` | `D:\Projects` |

检查路径转换：

```bash
eskit path d
eskit path d/Projects
eskit path /mnt/d/Projects
```

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

说明：

- `.pdf`、`.jpg` 这类扩展名默认表示文件；
- `folder`、`dir`、`目录`、`文件夹` 是类型过滤词，不会被当成文件名关键词；
- `folder .pdf ODL` 会同时返回名称匹配 `ODL` 的文件夹和 PDF 文件。

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

## 搜索后的键盘选择

在真实终端中，普通搜索会进入一个轻量选择界面：

```bash
eskit d .pdf ODL
```

操作逻辑：

```text
Up / Down   选择结果
Right       更多操作
Left        关闭动作菜单或上一页
Enter       执行动作
Esc         退出
```

如果只想输出表格：

```bash
eskit d .pdf ODL --table
eskit d .pdf ODL --no-select
```

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

一次只能使用一个结果动作。

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

## 常见工作流

### 找最近修改的项目文档

```bash
eskit d e .pdf .docx .pptx 项目 --sort modified --top 30
```

### 找大文件

```bash
eskit d f --sort size --top 20 --table
```

### 找截图并复制第 2 个结果路径

```bash
eskit d .jpg .png screenshot --sort modified --top 10 --copy-path --index 2
```

### 给脚本读取搜索结果

```bash
eskit d .csv report --json --limit 50
```

### 查找文件夹和同名文档

```bash
eskit d folder .pdf ODL --stats
```

## 诊断

```bash
eskit doctor
```

常见问题：

### 1. 找不到 es.exe

WSL/Linux：

```bash
export ESKIT_ES_PATH=/mnt/i/Software/Everything/es.exe
```

Windows PowerShell：

```powershell
$env:ESKIT_ES_PATH = "I:\Software\Everything\es.exe"
```

也可以直接对单次命令传参：

```bash
eskit doctor --es-path /mnt/i/Software/Everything/es.exe
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

## 命令参考

更多命令细节见：

- [docs/commands.md](docs/commands.md)
- [docs/everything-es.md](docs/everything-es.md)
- [docs/wsl.md](docs/wsl.md)

也可以直接查看内置帮助：

```bash
eskit --help
eskit --help-full
```

## 开发

从源码安装开发环境：

```bash
git clone https://github.com/deliuou/eskit.git
cd eskit
python3 -m pip install -e .
```

运行测试：

```bash
python3 -m pytest
```

项目结构：

```text
eskit/
  cli.py          CLI 入口和参数处理
  grammar.py      直接搜索语法解析
  es.py           es.exe 调用和查询构造
  fuzzy.py        模糊匹配和拼音匹配
  actions.py      打开、定位、复制等结果动作
  formatters.py   表格、JSON、统计输出
docs/             设计和命令文档
tests/            单元测试
```

欢迎贡献这些方向：

- 更多 Everything 查询语法的友好包装；
- 更好的跨 shell 路径兼容；
- 更稳定的 Windows / WSL 剪贴板和文件管理器动作；
- 更适合 agent 的结构化输出；
- 更多真实工作流示例和测试用例。

## 设计原则

- WSL 优先，同时兼容 Windows 原生命令行；
- 不替代 Everything，只增强 `es.exe` 的日常体验；
- 一个直接语法，不强迫用户记复杂子命令；
- 多盘符、多文件类型、多关键词都应该自然可组合；
- 搜索结果可以继续排序、统计、导出、复制和打开；
- JSON / NDJSON 是一等输出，方便脚本和 agent；
- 默认动作尽量安全，涉及结果处理时明确指定动作。

## License

MIT
