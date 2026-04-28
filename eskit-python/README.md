# eskit (Python)

**WSL-first Windows 文件搜索工具 — Python 实现**

[![PyPI version](https://img.shields.io/pypi/v/eskit-python?style=flat)](https://pypi.org/project/eskit-python/)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/deliuou/eskit/blob/main/eskit-python/LICENSE)

> 如果你同时使用 Windows 和 WSL，一定有这种经历：Windows 上有文件，但想不起来存在哪个盘、哪个文件夹。`Everything` 很快但交互太原始，`Listary` 很好但没有命令行。**eskit 就是给这种场景设计的。**

## 🎯 特性

- **无需学习成本** — `eskit d .pdf ODL` 就是搜索 D 盘里名字含 ODL 的 PDF
- **WSL 原生** — 路径自动转换，`/mnt/d/Projects` 和 `D:\Projects` 等价
- **模糊 + 拼音** — `ODL` 可以匹配"我的开题报告"（拼音首字母）
- **搜索后直接操作** — 打开、打开所在位置、复制路径、复制到指定目录
- **JSON/NDJSON 一等支持** — 方便脚本、AI agent、系统集成

## ⚡ 快速开始

```bash
pip install eskit-python
export ESKIT_ES_PATH=/mnt/c/你的路径/es.exe    # 首次需要指定 es.exe 位置
eskit doctor                                      # 检查环境是否就绪

# 搜索
eskit d .pdf ODL
eskit d f .pdf .pptx .docx 开题 报告
eskit d f .pdf ODL --sort size --top 10

# 脚本 / AI agent 用 JSON
eskit d .pdf ODL --json
```

## 🔧 安装

### 前置依赖：Windows 端

1. 安装 [Everything](https://www.voidtools.com/downloads/)
2. 下载 [es.exe](https://www.voidtools.com/downloads/)（Everything Command-line Interface）

### 安装 eskit

```bash
pip install eskit-python
```

指定 es.exe 路径（建议写入 `~/.bashrc`）：

```bash
export ESKIT_ES_PATH=/mnt/c/你的路径/es.exe
eskit doctor
```

## 📖 核心语法

```
eskit [盘符...] [路径...] [文件类型...] [关键词...] [选项...]
```

**盘符简写：** `d` = D:\, `f` = F:\, ... 自动转换为 Windows 路径

**文件类型：** `.pdf` `.jpg` `.docx` `.pptx` `.md` `folder` `dir`

**常用选项：**

| 选项 | 作用 |
|------|------|
| `--sort name/path/ext/size/modified` | 排序 |
| `--top N` | 取前 N 条结果 |
| `--stats` | 显示统计信息 |
| `--json` / `--ndjson` | JSON 输出 |
| `--open` | 打开文件 |
| `--reveal` | 在资源管理器中打开位置 |
| `--copy-path` | 复制完整路径 |
| `--copy-to DIR` | 复制到指定目录 |

## 💡 典型场景

```bash
# 找文件
eskit .pdf 开题
eskit d f .pdf 开题

# 找图片
eskit d .jpg .png 截图
eskit d .jpg 微信 2024

# AI agent / 脚本集成
eskit d f .pdf .pptx ODL --json --limit 20

# 快速打开
eskit d .pdf ODL --open --index 1
```

## 🛠️ 开发

```bash
git clone https://github.com/deliuou/eskit.git
cd eskit/eskit-python
pip install -e .
eskit doctor
```

## 📁 项目结构

```
eskit-python/
├── eskit/            ← 源码
│   ├── cli.py        ← 命令行入口
│   ├── es.py         ← es.exe 客户端
│   ├── grammar.py    ← 参数解析
│   ├── fuzzy.py      ← 模糊匹配 + 拼音
│   ├── actions.py    ← 动作执行
│   ├── formatters.py ← 输出格式化
│   ├── exporters.py  ← JSON/CSV 导出
│   └── listary.py    ← Listary 风格交互
├── tests/            ← 单元测试
├── pyproject.toml
└── README.md
```

## 📝 License

MIT
