# eskit (Rust)

**WSL-first Windows 文件搜索工具 — Rust 实现**

[![Rust 1.70+](https://img.shields.io/badge/Rust-1.70+-orange.svg)](https://www.rust-lang.org/)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/deliuou/eskit/blob/main/eskit-rust/LICENSE)

> 如果你同时使用 Windows 和 WSL，一定有这种经历：Windows 上有文件，但想不起来存在哪个盘、哪个文件夹。`Everything` 很快但交互太原始，`Listary` 很好但没有命令行。**eskit 就是给这种场景设计的。**

## 🎯 特性

- **零依赖** — 静态二进制，无需安装任何运行时
- **极致性能** — Rust 原生执行效率
- **WSL 原生** — 路径自动转换，`/mnt/d/Projects` 和 `D:\Projects` 等价
- **模糊 + 拼音** — `ODL` 可以匹配"我的开题报告"（拼音首字母）
- **搜索后直接操作** — 打开、打开所在位置、复制路径
- **JSON/NDJSON 一等支持** — 方便脚本、AI agent、系统集成

## ⚡ 快速开始

### 安装

```bash
cargo install eskit-rust
```

或下载静态二进制文件：👉 [Release 页面](https://github.com/deliuou/eskit/releases)

### 前置依赖：Windows 端

1. 安装 [Everything](https://www.voidtools.com/downloads/)
2. 下载 [es.exe](https://www.voidtools.com/downloads/)（Everything Command-line Interface）

### 配置 es.exe 路径

```bash
export ESKIT_ES_PATH=/mnt/c/你的路径/es.exe
eskit doctor
```

### 搜索

```bash
eskit d .pdf ODL
eskit d f .pdf .pptx .docx 开题 报告
eskit d f .pdf ODL --sort size --top 10

# 脚本 / AI agent 用 JSON
eskit d .pdf ODL --json
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
cd eskit/eskit-rust
cargo build --release
cargo test
```

## 📁 项目结构

```
eskit-rust/
├── src/
│   ├── main.rs        ← 入口
│   ├── cli.rs         ← 命令行解析
│   ├── es.rs          ← es.exe 客户端
│   ├── grammar.rs     ← 参数解析
│   ├── fuzzy.rs       ← 模糊匹配 + 拼音
│   ├── actions.rs     ← 动作执行
│   ├── formatters.rs  ← 输出格式化
│   ├── models.rs      ← 数据模型
│   ├── selector.rs    ← 交互式选择
│   └── util.rs        ← 工具函数
├── Cargo.toml
└── README.md
```

## 📝 License

MIT
