# eskit

**在 WSL/Linux 里用自然语法搜索 Windows 文件。**

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/deliuou/eskit/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://github.com/deliuou/eskit/tree/main/eskit-python)
[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg)](https://github.com/deliuou/eskit/tree/main/eskit-rust)
[![Stars](https://img.shields.io/github/stars/deliuou/eskit?style=social)](https://github.com/deliuou/eskit)

> 如果你同时使用 Windows 和 WSL，一定有这种经历：Windows 上有文件，但想不起来存在哪个盘、哪个文件夹。`Everything` 很快但交互太原始，`Listary` 很好但没有命令行。**eskit 就是给这种场景设计的。**

## 🎯 特性

- **无需学习成本** — `eskit d .pdf ODL` 就是搜索 D 盘里名字含 ODL 的 PDF，像说话一样自然
- **WSL 原生** — 路径自动转换，`/mnt/d/Projects` 和 `D:\Projects` 等价
- **模糊 + 拼音** — `ODL` 可以匹配"我的开题报告"（拼音首字母）
- **搜索后直接操作** — 打开、打开所在位置、复制路径、复制到指定目录
- **JSON/NDJSON 一等支持** — 方便脚本、AI agent、系统集成
- **双版本** — Python 版开箱即用，Rust 版静态二进制、零依赖

## ⚡ 快速开始

```bash
# 安装 Python 版（pip）
pip install eskit-python

# 或者用 Rust 版（静态二进制）
cargo install eskit-rust

# 搜索 D 盘的 PDF
eskit d .pdf ODL

# 搜索多个盘、多种类型
eskit d f .pdf .pptx .docx 开题 报告

# 搜索后排序取前 10
eskit d f .pdf ODL --sort size --top 10

# 脚本 / AI agent 用 JSON 输出
eskit d .pdf ODL --json
```

## 🔧 安装

### 前置依赖：Windows 端

1. 安装 [Everything](https://www.voidtools.com/downloads/)
2. 下载 [es.exe](https://www.voidtools.com/downloads/)（Everything Command-line Interface）

### Python 版（推荐日常使用）

```bash
pip install eskit-python
export ESKIT_ES_PATH=/mnt/c/你的路径/es.exe    # 首次需要指定 es.exe 位置
eskit doctor                                      # 检查环境是否就绪
```

### Rust 版（适合嵌入式、静态部署）

```bash
cargo install eskit-rust
# 或下载静态二进制：https://github.com/deliuou/eskit/releases
eskit doctor
```

## 📖 核心语法

```
eskit [盘符...] [路径...] [文件类型...] [关键词...] [选项...]
```

**盘符简写：** `d` = D:\, `f` = F:\, ... 自动转换为 Windows 路径

**文件类型：** `.pdf` `.jpg` `.docx` `.pptx` `.md` `folder` `dir`

**关键词：** 任意中英文、数字、拼音首字母，支持模糊匹配

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
| `--no-fuzzy` | 关闭模糊匹配 |

## 💡 典型场景

**找文件（不知道在哪一盘）：**
```bash
eskit .pdf 开题
# 或
eskit d f .pdf 开题
```

**找图片（截图找不到了）：**
```bash
eskit d .jpg .png 截图
eskit d .jpg 微信 2024
```

**AI agent / 脚本集成：**
```bash
eskit d f .pdf .pptx ODL --json --limit 20
# 返回结构化 JSON，方便后续处理
```

**日常快速打开：**
```bash
eskit d .pdf ODL --open --index 1
# 直接用默认应用打开第一个结果
```

## 🏗️ 项目结构

```
eskit/
├── README.md              ← 本文档（统一入口）
├── eskit-python/          ← Python 实现
│   ├── eskit/             ← 源码包
│   ├── pyproject.toml
│   └── ...
└── eskit-rust/            ← Rust 实现
    ├── src/
    ├── Cargo.toml
    └── ...
```

两个版本 API 和命令行接口完全一致，按需选择：

| | Python 版 | Rust 版 |
|--|-----------|---------|
| 安装方式 | `pip install` | `cargo install` / 下载二进制 |
| 依赖 | 需要 Python 3.9+ | 零依赖（静态二进制） |
| 适用场景 | 日常使用、AI agent、系统集成 | 嵌入式、CI/CD、追求极致性能 |

## 🔗 相关资源

- [Everything](https://www.voidtools.com/) — Windows 文件索引引擎
- [es.exe](https://github.com/voidtools/ES) — Everything 命令行接口
- [Listary](https://www.listary.com/) — 灵感来源，优秀的 Windows 文件搜索工具

## 📝 License

MIT
