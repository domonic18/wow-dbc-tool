# wow-dbc-tool

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **面向 AI Agent 的魔兽世界 3.3.5a DBC 文件操作工具**
>
> 支持读取、查询、编辑、对比 DBC 文件，提供 JSON 结构化输出，便于自动化处理和 AI 工作流集成。

---

## 📖 项目简介

`wow-dbc-tool` 是一个专为 **AI Agent** 和自动化工作流设计的魔兽世界 DBC（Database Client）文件操作工具。它提供命令行接口（CLI）和 Python API，支持对 WDBC 格式文件的完整操作：

- **读取** - 解析 WDBC 格式，输出结构化数据
- **查询** - 支持多种操作符（eq/ne/gt/lt/contains）的灵活过滤
- **编辑** - 增删改记录，保存为新文件
- **对比** - Diff 两个 DBC 版本，输出结构化差异报告
- **文档** - 集成 Wowdev Wiki 字段定义，支持字段含义查询

### 面向 Agent 的设计

- ✅ **JSON 结构化输出** - 所有命令支持 `--json` 输出，便于程序解析
- ✅ **非交互式操作** - 适合脚本和自动化流程
- ✅ **字段定义查询** - `explain` 命令查询 DBC 字段含义，降低使用门槛
- ✅ **分级帮助系统** - `--help` 简洁模式，`--help-full` 详细模式

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/domonic18/wow-dbc-tool.git
cd wow-dbc-tool
pip install -e .
```

### 验证安装

```bash
python3 -m wow_dbc_tool --help
```

### 基本使用

```bash
# 读取 DBC 文件
python3 -m wow_dbc_tool read Spell.dbc --json

# 查询记录（ID 等于 133）
python3 -m wow_dbc_tool query Spell.dbc --filter ID=133 --json

# 查询记录（名称包含 Fire）
python3 -m wow_dbc_tool query Spell.dbc --filter "SpellName4__contains=Fire" --json

# 对比两个 DBC 文件
python3 -m wow_dbc_tool diff Spell_old.dbc Spell_new.dbc --json

# 查询字段含义
python3 -m wow_dbc_tool explain Spell.dbc --field ManaCost --json
```

---

## 📚 完整功能文档

### CLI 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `read` | 读取 DBC 文件 | `read Spell.dbc --json` |
| `query` | 查询记录 | `query Spell.dbc --filter ID=133 --json` |
| `edit` | 修改记录 | `edit Spell.dbc --filter ID=133 --set ManaCost=100 --output out.dbc` |
| `delete` | 删除记录 | `delete Spell.dbc --filter ID=133 --output out.dbc --json` |
| `add` | 添加记录 | `add Spell.dbc --field ID=9999 --field SpellName4="Custom" --output out.dbc` |
| `diff` | 对比文件 | `diff old.dbc new.dbc --json` |
| `schema` | Schema 管理 | `schema list --json` |
| `explain` | 字段含义查询 | `explain Spell.dbc --field ManaCost --json` |
| `help` | 帮助系统 | `help read --json` |
| `wiki` | Wiki 文档同步 | `wiki sync-all` |

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
```

---

## 🏗️ 项目结构

```
wow-dbc-tool/
├── pyproject.toml          # 项目配置
├── README.md               # 本文件
├── LICENSE                 # MIT 许可证
├── docs/
│   ├── architecture.md     # 架构设计文档
│   ├── help-explain-wowdev-architecture.md  # Help/Explain 架构
│   └── definitions/        # DBC 字段定义文档（Markdown）
│       ├── Spell.md
│       ├── Item.md
│       └── ...
├── src/wow_dbc_tool/       # 源代码
│   ├── __init__.py
│   ├── __main__.py         # CLI 入口
│   ├── cli.py              # 命令行接口
│   ├── help_system.py      # 帮助系统
│   ├── doc_store.py        # 文档存储
│   ├── wowdev_crawler.py   # Wowdev Wiki 爬虫
│   ├── core/               # 核心引擎
│   │   ├── dbc_file.py
│   │   ├── dbc_record.py
│   │   └── exceptions.py
│   ├── parser/             # WDBC 解析器
│   │   ├── header.py
│   │   ├── reader.py
│   │   └── writer.py
│   ├── schema/             # Schema 定义
│   │   ├── field_def.py
│   │   └── registry.py
│   └── diff/               # Diff 引擎
│       └── engine.py
└── tests/                  # 测试套件
    ├── test_parser.py
    ├── test_core.py
    ├── test_schema.py
    ├── test_diff.py
    ├── test_real_dbc.py    # 真实 DBC 文件测试
    ├── test_help.py
    ├── test_docs.py
    ├── test_wiki_crawler.py
    └── test_cli_explain.py
```

---

## 🧪 测试

```bash
# 运行全部测试
python3 -m pytest tests/ -v

# 运行特定测试
python3 -m pytest tests/test_real_dbc.py -v

# 带覆盖率报告
python3 -m pytest tests/ --cov=wow_dbc_tool --cov-report=term
```

**测试覆盖**: 148 个测试，71% 代码覆盖率

---

## 📋 分支说明

本项目使用以下分支策略：

| 分支 | 说明 | 稳定性 |
|------|------|--------|
| `main` | **主分支**，稳定版本 | ⭐ 生产就绪 |
| `feature/*` | 功能开发分支 | 🚧 开发中 |

**当前主分支**: `main`

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

[MIT License](LICENSE) © 2025 domonic18

---

## 🙏 致谢

- [Wowdev Wiki](https://wowdev.wiki/) - DBC 字段定义参考
- [TrinityCore](https://github.com/TrinityCore/TrinityCore) - 魔兽世界服务端项目
- [AzerothCore](https://github.com/azerothcore/azerothcore-wotlk) - 魔兽世界服务端项目

---

> **注意**: 本项目仅供学习和研究使用，请遵守相关法律法规和服务条款。
