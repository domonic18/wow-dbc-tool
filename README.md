# wow-dbc-tool

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **面向 AI Agent 的魔兽世界 3.3.5a DBC 文件操作工具**
>
> 支持读取、查询、编辑、对比、导出 DBC 文件，提供 JSON 结构化输出，便于自动化处理和 AI 工作流集成。

---

## 📖 项目简介

`wow-dbc-tool` 是一个专为 **AI Agent** 和自动化工作流设计的魔兽世界 DBC（Database Client）文件操作工具。它提供命令行接口（CLI）和 Python API，支持对 WDBC 格式文件的完整操作：

- **读取** - 解析 WDBC 格式，输出结构化 JSON 数据
- **查询** - 支持多种操作符（eq/ne/gt/lt/contains）的灵活过滤
- **编辑** - 增删改记录，保存为新文件
- **对比** - Diff 两个 DBC 版本，输出结构化差异报告
- **导出** - 将 DBC 导出为 CSV（支持自动加载 JSON schema）
- **生成 Schema** - 从 CSV + WoWDBDefs 自动生成 DBC 物理字段定义

### 面向 Agent 的设计

- ✅ **JSON 结构化输出** - 所有命令默认 JSON 输出，便于程序解析
- ✅ **非交互式操作** - 适合脚本和自动化流程
- ✅ **自动 Schema 加载** - 从 `schemas/*.schema.json` 自动匹配字段定义
- ✅ **分级帮助系统** - `--help` 简洁模式，`--help-full` 详细模式
- ✅ **explain 字段查询** - 查询 DBC 字段含义，降低使用门槛

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/domonic18/wow-dbc-tool.git
cd wow-dbc-tool
pip install -e ".[dev]"
```

### 验证安装

```bash
python -m wow_dbc_tool --help
```

### 基本使用

```bash
# 读取 DBC 文件
python -m wow_dbc_tool read Spell.dbc --json

# 导出 DBC 为 CSV（自动加载 schema）
python -m wow_dbc_tool export data/DBFilesClient/Spell.dbc \
    --keep-header tables/Spell.csv --output tables/Spell.csv

# 查询记录（ID 等于 133）
python -m wow_dbc_tool query Spell.dbc --filter ID=133 --json

# 查询记录（名称包含 Fire）
python -m wow_dbc_tool query Spell.dbc --filter "SpellName4__contains=Fire" --json

# 对比两个 DBC 文件
python -m wow_dbc_tool diff Spell_old.dbc Spell_new.dbc --json

# 查询字段含义
python -m wow_dbc_tool explain Spell.dbc --field ManaCost --json

# 生成 schema（从 CSV + WoWDBDefs）
python -m wow_dbc_tool schema generate
python -m wow_dbc_tool schema generate --table Spell
```

---

## 📚 完整功能文档

### CLI 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `read` | 读取 DBC 文件 | `read Spell.dbc --json` |
| `export` | 导出 DBC 为 CSV | `export Spell.dbc --output Spell.csv` |
| `query` | 查询记录 | `query Spell.dbc --filter ID=133 --json` |
| `edit` | 修改记录 | `edit Spell.dbc --filter ID=133 --set ManaCost=100 --output out.dbc` |
| `delete` | 删除记录 | `delete Spell.dbc --filter ID=133 --output out.dbc --json` |
| `add` | 添加记录 | `add Spell.dbc --field ID=9999 --field SpellName4="Custom" --output out.dbc` |
| `diff` | 对比文件 | `diff old.dbc new.dbc --json` |
| `schema` | Schema 管理 | `schema list`, `schema show Spell.dbc`, `schema generate` |
| `explain` | 字段含义查询 | `explain Spell.dbc --field ManaCost --json` |
| `help` | 帮助系统 | `help read --json` |

### Schema 子命令

| 子命令 | 说明 | 示例 |
|--------|------|------|
| `list` | 列出所有已知 schema | `schema list --json` |
| `show` | 显示指定 DBC 的字段定义 | `schema show Spell.dbc --json` |
| `infer` | 从文件结构推断字段定义 | `schema infer Spell.dbc --json` |
| `validate` | 验证字段定义与文件一致性 | `schema validate Spell.dbc --json` |
| `generate` | 从 CSV + WoWDBDefs 生成 schema | `schema generate --table Spell` |

### 查询操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `eq` / `=` | 等于 | `ID=133` |
| `ne` / `!=` | 不等于 | `ID__ne=133` |
| `gt` / `>` | 大于 | `ID__gt=100` |
| `lt` / `<` | 小于 | `ID__lt=500` |
| `gte` / `>=` | 大于等于 | `ID__gte=100` |
| `lte` / `<=` | 小于等于 | `ID__lte=500` |
| `contains` | 包含子串 | `SpellName4__contains=Fire` |

### Python API

```python
from wow_dbc_tool import DBCFile

# 加载 DBC 文件
dbc = DBCFile('Spell.dbc')
dbc.load()

# 查询记录
records = dbc.query(SpellName4__contains="Fire")

# 修改记录
for r in records:
    r.set('ManaCost', 100)

# 保存
dbc.save('Spell_modified.dbc')

# Diff 对比
from wow_dbc_tool.diff import DBCDiff
report = DBCDiff(dbc_old, dbc_new).compare()
print(report.to_json())

# Schema 生成
from wow_dbc_tool.schema.generator import generate_schemas
generate_schemas(
    csv_dir=Path("tables"),
    dbd_dir=Path("third-party/WoWDBDefs/definitions"),
    output_dir=Path("schemas"),
)
```

---

## 🏗️ 项目结构

```
wow-dbc-tool/
├── pyproject.toml          # 项目配置（含 ruff/mypy/pytest 配置）
├── README.md               # 本文件
├── LICENSE                 # MIT 许可证
├── MANIFEST.in             # 打包数据文件（schemas/ + docs/definitions/）
├── schemas/                # JSON schema 数据（从 WoWDBDefs 生成）
│   ├── Achievement.schema.json
│   ├── Spell.schema.json
│   └── ...
├── docs/
│   ├── guides/architecture.md        # 架构设计文档
│   └── definitions/                  # DBC 字段定义文档（Markdown）
│       ├── Spell.md
│       ├── Item.md
│       └── ...
├── src/wow_dbc_tool/       # 源代码
│   ├── __init__.py
│   ├── __main__.py         # CLI 入口
│   ├── cli.py              # 命令行接口
│   ├── core/               # 核心引擎
│   │   ├── dbc_file.py
│   │   ├── dbc_record.py
│   │   └── exceptions.py
│   ├── parser/             # WDBC 解析器
│   │   ├── header.py
│   │   ├── reader.py
│   │   └── writer.py
│   ├── schema/             # Schema 定义与生成
│   │   ├── field_def.py    # 字段定义数据类
│   │   ├── registry.py     # Schema 注册表（从 JSON 加载）
│   │   └── generator.py    # 从 CSV + WoWDBDefs 生成 schema
│   ├── diff/               # Diff 引擎
│   │   └── engine.py
│   └── utils/              # 工具模块
│       ├── doc_store.py    # Markdown 文档管理
│       └── help_system.py  # 分级帮助系统
└── tests/                  # 测试套件
    ├── data/               # 测试固件
    │   ├── fixtures/
    │   ├── samples/
    │   └── schemas/
    ├── conftest.py
    ├── test_parser.py
    ├── test_core.py
    ├── test_schema.py
    ├── test_diff.py
    ├── test_real_dbc.py
    ├── test_help.py
    ├── test_docs.py
    └── test_cli_explain.py
```

---

## 🧪 开发与测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行全部测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_real_dbc.py -v

# 带覆盖率报告
python -m pytest tests/ --cov=wow_dbc_tool --cov-report=term

# 代码风格检查
python -m ruff check src/wow_dbc_tool tests/

# 类型检查
python -m mypy src/wow_dbc_tool
```

---

## 🔧 CI / GitHub Actions

本项目已配置 GitHub Actions CI，每次 Push 和 PR 时自动执行：

- ✅ **ruff** — 代码风格检查
- ✅ **mypy** — 静态类型检查
- ✅ **pytest** — 测试用例执行（含覆盖率报告）

---

## 📋 分支说明

| 分支 | 说明 | 稳定性 |
|------|------|--------|
| `main` | **主分支**，稳定版本 | ⭐ 生产就绪 |
| `feature/*` | 功能开发分支 | 🚧 开发中 |

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

**提交前请确保：**
- `ruff check src/wow_dbc_tool tests/` 通过
- `mypy src/wow_dbc_tool` 通过
- `pytest tests/` 全部通过

---

## 📄 许可证

[MIT License](LICENSE) © 2025 domonic18

---

## 🙏 致谢

- [WoWDBDefs](https://github.com/wowdev/WoWDBDefs) — DBC 字段类型定义
- [Wowdev Wiki](https://wowdev.wiki/) — DBC 字段语义参考
- [TrinityCore](https://github.com/TrinityCore/TrinityCore) — 魔兽世界服务端项目
- [AzerothCore](https://github.com/azerothcore/azerothcore-wotlk) — 魔兽世界服务端项目

---

> **注意**: 本项目仅供学习和研究使用，请遵守相关法律法规和服务条款。
