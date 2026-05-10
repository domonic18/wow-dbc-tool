# wow-dbc-tool Help + Explain + Wowdev Wiki 集成架构设计

> 版本: 1.0  
> 日期: 2025-05-10  
> 状态: 已定稿  
> 基于: wow-dbc-tool v0.1.0 现有架构

---

## 1. 需求分析

### 1.1 功能需求

| 需求 | 优先级 | 说明 |
|------|--------|------|
| 增强 Help 功能 | P0 | 分级帮助：--help（简洁）/ --help-full（详细含示例） |
| 子命令独立帮助 | P0 | 每个子命令独立的帮助页 |
| Wowdev Wiki 文档集成 | P0 | 从 wowdev.wiki 下载 DBC 字段定义 |
| 文档存储 | P0 | Markdown 格式，docs/definitions/<Name>.md |
| Explain 查询 | P0 | 查询整个文件说明 / 查询特定字段 |
| JSON 输出 | P0 | 便于 Agent 消费 |

### 1.2 非功能需求

| 需求 | 目标 |
|------|------|
| 文档格式 | Markdown（单一格式，兼顾人类和 Agent） |
| 爬虫 | requests + BeautifulSoup / 或直接使用已下载的 Wiki 数据 |
| 存储 | docs/definitions/<Name>.md |
| 索引 | JSON 索引文件便于快速查找 |
| 向后兼容 | 不破坏现有 CLI 接口 |
| 零依赖新增 | 尽量使用标准库，可选 requests |

### 1.3 现有架构约束

- CLI 使用 argparse，子命令模式
- 现有命令: read, query, edit, delete, add, diff, schema
- 输出格式: JSON（--json/--compact）
- 项目结构: src/wow_dbc_tool/ 下分模块
- definitions/ 目录已存在（空）

---

## 2. 高层架构设计

### 2.1 扩展后的系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  read   │ │ query   │ │  edit   │ │ delete  │          │
│  │  add    │ │  diff   │ │ schema  │ │  help   │ ◄── 新增  │
│  │ explain │ │  wiki   │ │         │ │         │ ◄── 新增  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │
└───────┼────────────┼────────────┼────────────┼──────────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                           │
                    ┌──────▼──────┐
                    │  Core API   │
                    │  (DBCFile)  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐    ┌─────▼─────┐
   │  Parser │      │   Schema    │    │   Diff    │
   │ (WDBC)  │      │  Registry   │    │  Engine   │
   └────┬────┘      └─────────────┘    └─────┬─────┘
        │                                    │
   ┌────▼────┐                         ┌────▼────┐
   │  Writer │                         │  Report │
   │ (WDBC)  │                         │  JSON   │
   └─────────┘                         └─────────┘
        │
   ┌────▼────────────────────────────────────┐
   │         新增: Docs / Help 模块           │
   │  ┌──────────┐  ┌──────────┐            │
   │  │ DocStore  │  │HelpSystem│            │
   │  │(Markdown) │  │(分级帮助)│            │
   │  └──────────┘  └──────────┘            │
   │  ┌──────────┐  ┌──────────┐            │
   │  │WikiCrawler│  │DocIndex  │            │
   │  │(可选)     │  │(JSON)    │            │
   │  └──────────┘  └──────────┘            │
   └─────────────────────────────────────────┘
```

### 2.2 新增模块划分

| 模块 | 职责 | 核心类/函数 |
|------|------|------------|
| `docs` | 文档存储与查询 | `DocStore`, `DocEntry` |
| `help` | 分级帮助系统 | `HelpSystem`, `CommandHelp` |
| `wiki` | Wiki 爬虫与同步 | `WikiCrawler`, `WikiSync` |

---

## 3. 详细设计

### 3.1 文档存储模块 (DocStore)

#### 3.1.1 文档目录结构

```
wow-dbc-tool/
├── docs/
│   ├── architecture.md         # 现有架构文档
│   └── definitions/            # DBC 字段定义文档（新增）
│       ├── index.json          # 索引文件
│       ├── Spell.md            # Spell.dbc 说明
│       ├── Item.md             # Item.dbc 说明
│       └── ...
```

#### 3.1.2 Markdown 文档格式规范

每个 DBC 文档采用统一格式，兼顾人类可读性和 Agent 解析：

```markdown
# Spell.dbc

> 来源: https://wowdev.wiki/Spell.dbc  
> 版本: 3.3.5a  
> 最后同步: 2025-05-10

## 概述

Spell.dbc 包含游戏中所有法术的定义，包括法术名称、效果、消耗、冷却等属性。

## 文件头信息

| 属性 | 值 |
|------|-----|
| field_count | 234 |
| record_size | 936 |

## 字段定义

### ID
- **偏移**: 0
- **类型**: uint32
- **说明**: 法术唯一标识符
- **示例**: 133 (Fireball)

### Name
- **偏移**: 4
- **类型**: string
- **说明**: 法术名称（客户端显示）
- **示例**: "Fireball"

### Category
- **偏移**: 8
- **类型**: uint32
- **说明**: 法术分类（用于冷却分组）

## 常见用法

```bash
# 查询特定法术
wow-dbc-tool query Spell.dbc --filter ID=133 --json

# 修改法术名称
wow-dbc-tool edit Spell.dbc --filter ID=133 --set Name="New Name"
```
```

#### 3.1.3 DocStore 接口

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DocEntry:
    """文档条目"""
    name: str           # DBC 名称（如 "Spell.dbc"）
    title: str          # 文档标题
    source: str         # 来源 URL
    version: str        # 游戏版本
    last_sync: str      # 最后同步时间
    field_count: int    # 字段数量
    record_size: int    # 记录大小
    fields: list[dict]  # 字段定义列表
    overview: str       # 概述文本
    examples: list[str] # 示例用法

    def to_dict(self) -> dict[str, Any]:
        """转为字典（JSON 输出）"""
        return {
            "name": self.name,
            "title": self.title,
            "source": self.source,
            "version": self.version,
            "last_sync": self.last_sync,
            "field_count": self.field_count,
            "record_size": self.record_size,
            "fields": self.fields,
            "overview": self.overview,
            "examples": self.examples,
        }


class DocStore:
    """文档存储管理器.

    管理 docs/definitions/ 目录下的 Markdown 文档和索引。
    """

    def __init__(self, docs_dir: str | Path | None = None):
        """初始化文档存储.

        Args:
            docs_dir: 文档目录路径，None 使用默认路径
        """
        if docs_dir is None:
            # 默认路径：项目根目录下的 docs/definitions/
            self.docs_dir = self._find_default_docs_dir()
        else:
            self.docs_dir = Path(docs_dir)

        self.index_path = self.docs_dir / "index.json"
        self._index: dict[str, str] = {}  # name -> markdown_file

    def _find_default_docs_dir(self) -> Path:
        """查找默认文档目录.

        从安装位置或开发位置查找。
        """
        # 1. 尝试从包路径推导
        import wow_dbc_tool
        pkg_dir = Path(wow_dbc_tool.__file__).parent
        # 向上找到项目根目录
        project_root = pkg_dir.parent.parent  # src/wow_dbc_tool -> src -> project_root
        docs_dir = project_root / "docs" / "definitions"
        if docs_dir.exists():
            return docs_dir

        # 2. 使用包内嵌文档（安装模式）
        embedded = pkg_dir / "docs" / "definitions"
        if embedded.exists():
            return embedded

        # 3. 默认创建在当前工作目录
        return Path.cwd() / "docs" / "definitions"

    def load_index(self) -> dict[str, str]:
        """加载索引文件.

        Returns:
            索引字典: {dbc_name: markdown_filename}
        """
        if self.index_path.exists():
            import json
            with open(self.index_path, encoding="utf-8") as f:
                self._index = json.load(f)
        return self._index

    def save_index(self) -> None:
        """保存索引文件."""
        import json
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)

    def get(self, dbc_name: str) -> DocEntry | None:
        """获取指定 DBC 的文档.

        Args:
            dbc_name: DBC 文件名（如 "Spell.dbc"）

        Returns:
            文档条目，未找到返回 None
        """
        self.load_index()
        md_file = self._index.get(dbc_name)
        if md_file is None:
            return None

        path = self.docs_dir / md_file
        if not path.exists():
            return None

        return self._parse_markdown(path)

    def list_all(self) -> list[str]:
        """列出所有已文档化的 DBC.

        Returns:
            DBC 名称列表
        """
        self.load_index()
        return list(self._index.keys())

    def save(self, entry: DocEntry) -> None:
        """保存文档条目.

        Args:
            entry: 文档条目
        """
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        # 生成 Markdown 文件
        md_file = f"{entry.name.replace('.dbc', '')}.md"
        path = self.docs_dir / md_file

        content = self._render_markdown(entry)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # 更新索引
        self._index[entry.name] = md_file
        self.save_index()

    def _parse_markdown(self, path: Path) -> DocEntry:
        """解析 Markdown 文件为 DocEntry.

        Args:
            path: Markdown 文件路径

        Returns:
            文档条目
        """
        # 解析 frontmatter 和正文
        # 提取字段定义、概述、示例等信息
        ...

    def _render_markdown(self, entry: DocEntry) -> str:
        """渲染 DocEntry 为 Markdown.

        Args:
            entry: 文档条目

        Returns:
            Markdown 文本
        """
        # 按规范格式生成 Markdown
        ...
```

### 3.2 帮助系统模块 (HelpSystem)

#### 3.2.1 分级帮助设计

```
┌─────────────────────────────────────────┐
│           帮助层级结构                   │
├─────────────────────────────────────────┤
│ Level 1: --help                         │
│   - 工具简介                            │
│   - 子命令列表（名称 + 一句话说明）      │
│   - 全局选项                            │
├─────────────────────────────────────────┤
│ Level 2: <command> --help               │
│   - 子命令详细说明                      │
│   - 参数列表                            │
│   - 1-2 个基础示例                      │
├─────────────────────────────────────────┤
│ Level 3: --help-full                   │
│   - 完整帮助（所有层级合并）             │
│   - 所有子命令详细说明                   │
│   - 完整示例集                          │
│   - 常见用例                            │
│   - 注意事项                            │
└─────────────────────────────────────────┘
```

#### 3.2.2 HelpSystem 接口

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandHelp:
    """子命令帮助信息"""
    name: str
    brief: str          # 一句话说明
    description: str    # 详细描述
    args: list[dict]    # 参数列表
    examples: list[str]  # 示例
    notes: list[str]    # 注意事项


class HelpSystem:
    """分级帮助系统.

    管理所有帮助文本，支持分级输出和 JSON 格式。
    """

    def __init__(self):
        """初始化帮助系统."""
        self._commands: dict[str, CommandHelp] = {}
        self._global_options: list[dict] = []
        self._tool_description = ""
        self._load_builtin_helps()

    def _load_builtin_helps(self) -> None:
        """加载内置帮助文本."""
        # 所有帮助文本内嵌在代码中，不依赖外部文件
        self._tool_description = (
            "wow-dbc-tool: 魔兽世界 3.3.5 DBC 文件操作工具\n"
            "支持读取、查询、编辑、删除、添加记录以及 Diff 对比。"
        )

        self._commands["read"] = CommandHelp(
            name="read",
            brief="读取 DBC 文件内容",
            description="读取 DBC 文件并输出所有记录。支持限制输出条数和指定字段定义。",
            args=[
                {"name": "file", "type": "Path", "required": True, "help": "DBC 文件路径"},
                {"name": "--limit", "type": "int", "required": False, "help": "限制输出条数"},
                {"name": "--schema", "type": "Path", "required": False, "help": "字段定义文件"},
            ],
            examples=[
                "wow-dbc-tool read Spell.dbc --json",
                "wow-dbc-tool read Spell.dbc --limit 10 --json",
            ],
            notes=["默认输出 JSON 格式", "大文件建议配合 --limit 使用"],
        )

        # ... 其他命令

    def get_brief_help(self) -> dict[str, Any]:
        """获取简洁帮助（Level 1）.

        Returns:
            JSON 可序列化的帮助信息
        """
        return {
            "tool": "wow-dbc-tool",
            "description": self._tool_description,
            "commands": [
                {"name": cmd.name, "brief": cmd.brief}
                for cmd in self._commands.values()
            ],
            "global_options": self._global_options,
        }

    def get_command_help(self, command: str) -> dict[str, Any] | None:
        """获取子命令帮助（Level 2）.

        Args:
            command: 子命令名称

        Returns:
            帮助信息，命令不存在返回 None
        """
        cmd = self._commands.get(command)
        if cmd is None:
            return None

        return {
            "command": cmd.name,
            "description": cmd.description,
            "args": cmd.args,
            "examples": cmd.examples,
            "notes": cmd.notes,
        }

    def get_full_help(self) -> dict[str, Any]:
        """获取完整帮助（Level 3）.

        Returns:
            JSON 可序列化的完整帮助信息
        """
        return {
            "tool": "wow-dbc-tool",
            "description": self._tool_description,
            "commands": [
                {
                    "name": cmd.name,
                    "brief": cmd.brief,
                    "description": cmd.description,
                    "args": cmd.args,
                    "examples": cmd.examples,
                    "notes": cmd.notes,
                }
                for cmd in self._commands.values()
            ],
            "global_options": self._global_options,
            "usage_tips": [
                "所有命令默认输出 JSON，便于 Agent 消费",
                "使用 --compact 获取紧凑 JSON",
                "使用 --schema 指定自定义字段定义",
            ],
        }
```

#### 3.2.3 CLI 集成

```python
def cmd_help(args: argparse.Namespace) -> int:
    """help 子命令."""
    help_system = HelpSystem()

    if args.full:
        # --help-full: 完整帮助
        data = help_system.get_full_help()
    elif args.command:
        # <command> --help: 子命令帮助
        data = help_system.get_command_help(args.command)
        if data is None:
            _error_json(f"未知命令: {args.command}", "HelpError")
            return 1
    else:
        # --help: 简洁帮助
        data = help_system.get_brief_help()

    _output_json(data, pretty=not args.compact)
    return 0
```

### 3.3 Explain 查询模块

#### 3.3.1 功能设计

```bash
# 查询整个文件说明
wow-dbc-tool explain Spell.dbc --json

# 查询特定字段
wow-dbc-tool explain Spell.dbc --field Name --json

# 查询多个字段
wow-dbc-tool explain Spell.dbc --field Name --field Category --json
```

#### 3.3.2 输出格式

**文件说明：**
```json
{
  "dbc_name": "Spell.dbc",
  "title": "Spell.dbc - 法术定义",
  "overview": "包含游戏中所有法术的定义...",
  "field_count": 234,
  "record_size": 936,
  "source": "https://wowdev.wiki/Spell.dbc",
  "last_sync": "2025-05-10",
  "fields_summary": [
    {"name": "ID", "type": "uint32", "offset": 0, "description": "法术唯一标识符"},
    {"name": "Name", "type": "string", "offset": 4, "description": "法术名称"},
    ...
  ],
  "examples": [
    "wow-dbc-tool query Spell.dbc --filter ID=133 --json"
  ]
}
```

**特定字段：**
```json
{
  "dbc_name": "Spell.dbc",
  "field": {
    "name": "Name",
    "type": "string",
    "offset": 4,
    "description": "法术名称（客户端显示）",
    "examples": ["Fireball", "Frostbolt"]
  }
}
```

#### 3.3.3 Explain 接口

```python
class ExplainService:
    """Explain 查询服务.

    基于 DocStore 提供 DBC 文件和字段的说明查询。
    """

    def __init__(self, doc_store: DocStore | None = None):
        """初始化服务.

        Args:
            doc_store: 文档存储实例，None 创建默认实例
        """
        self.doc_store = doc_store or DocStore()

    def explain_file(self, dbc_name: str) -> dict[str, Any] | None:
        """查询整个文件的说明.

        Args:
            dbc_name: DBC 文件名

        Returns:
            文件说明信息，未找到返回 None
        """
        entry = self.doc_store.get(dbc_name)
        if entry is None:
            return None

        return {
            "dbc_name": entry.name,
            "title": entry.title,
            "overview": entry.overview,
            "field_count": entry.field_count,
            "record_size": entry.record_size,
            "source": entry.source,
            "last_sync": entry.last_sync,
            "fields_summary": [
                {"name": f["name"], "type": f["type"], "offset": f["offset"], "description": f.get("description", "")}
                for f in entry.fields
            ],
            "examples": entry.examples,
        }

    def explain_field(self, dbc_name: str, field_name: str) -> dict[str, Any] | None:
        """查询特定字段的说明.

        Args:
            dbc_name: DBC 文件名
            field_name: 字段名

        Returns:
            字段说明信息，未找到返回 None
        """
        entry = self.doc_store.get(dbc_name)
        if entry is None:
            return None

        for field in entry.fields:
            if field["name"] == field_name:
                return {
                    "dbc_name": entry.name,
                    "field": field,
                }

        return None
```

### 3.4 Wiki 爬虫模块 (WikiCrawler)

#### 3.4.1 设计决策

📐 Wiki 数据获取 - 决策

Context:
- 需要从 wowdev.wiki 获取 DBC 字段定义
- 网络爬虫可能不稳定，且 Wiki 结构可能变化
- 需要支持离线使用

Options:
1. 实时爬虫（requests + BeautifulSoup）
   - Pros: 数据始终最新
   - Cons: 依赖网络，Wiki 结构变化会破坏爬虫，增加外部依赖

2. 预下载 + 本地缓存
   - Pros: 离线可用，不依赖外部服务，可控
   - Cons: 数据可能过时，需要定期手动更新

3. 混合模式（预下载为主 + 可选实时同步）
   - Pros: 兼顾离线和最新数据
   - Cons: 实现稍复杂

Decision: 方案 2（预下载 + 本地缓存）为主，预留方案 3 扩展接口
Rationale:
- wowdev.wiki 结构稳定，不频繁变化
- DBC 定义在 3.3.5a 版本下是固定的
- 离线可用对 Agent 工具更重要
- 减少外部依赖，简化安装
Trade-offs: 放弃自动实时更新，改为手动/定时同步

#### 3.4.2 WikiCrawler 接口

```python
from pathlib import Path
from typing import Any


class WikiCrawler:
    """Wowdev Wiki 爬虫.

    从 wowdev.wiki 下载 DBC 字段定义。
    可选模块，不导入时不影响核心功能。
    """

    BASE_URL = "https://wowdev.wiki"

    def __init__(self, output_dir: str | Path | None = None):
        """初始化爬虫.

        Args:
            output_dir: 输出目录，None 使用默认 docs/definitions/
        """
        self.output_dir = Path(output_dir) if output_dir else self._default_output_dir()

    def _default_output_dir(self) -> Path:
        """获取默认输出目录."""
        import wow_dbc_tool
        pkg_dir = Path(wow_dbc_tool.__file__).parent
        project_root = pkg_dir.parent.parent
        return project_root / "docs" / "definitions"

    def fetch_dbc_page(self, dbc_name: str) -> str | None:
        """获取 DBC 页面 HTML.

        Args:
            dbc_name: DBC 文件名（如 "Spell.dbc"）

        Returns:
            HTML 内容，失败返回 None
        """
        try:
            import requests
            url = f"{self.BASE_URL}/{dbc_name}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def parse_dbc_fields(self, html: str) -> list[dict[str, Any]]:
        """解析 HTML 提取字段定义.

        Args:
            html: 页面 HTML

        Returns:
            字段定义列表
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            fields = []
            # Wiki 页面通常有表格定义字段
            # 需要根据实际页面结构调整选择器
            tables = soup.find_all("table", class_="wikitable")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 3:
                        fields.append({
                            "name": cells[0].get_text(strip=True),
                            "type": cells[1].get_text(strip=True),
                            "offset": cells[2].get_text(strip=True),
                            "description": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        })

            return fields
        except Exception:
            return []

    def sync_dbc(self, dbc_name: str) -> DocEntry | None:
        """同步单个 DBC 定义.

        Args:
            dbc_name: DBC 文件名

        Returns:
            同步后的文档条目，失败返回 None
        """
        html = self.fetch_dbc_page(dbc_name)
        if html is None:
            return None

        fields = self.parse_dbc_fields(html)
        if not fields:
            return None

        # 创建 DocEntry
        from datetime import datetime
        entry = DocEntry(
            name=dbc_name,
            title=f"{dbc_name} - DBC 定义",
            source=f"{self.BASE_URL}/{dbc_name}",
            version="3.3.5a",
            last_sync=datetime.now().isoformat(),
            field_count=len(fields),
            record_size=len(fields) * 4,  # 假设所有字段 4 字节
            fields=fields,
            overview=f"{dbc_name} 的字段定义",
            examples=[],
        )

        return entry

    def sync_all(self, dbc_names: list[str] | None = None) -> dict[str, DocEntry | None]:
        """同步多个 DBC 定义.

        Args:
            dbc_names: DBC 名称列表，None 同步常见 DBC

        Returns:
            同步结果: {dbc_name: DocEntry | None}
        """
        if dbc_names is None:
            dbc_names = ["Spell.dbc", "Item.dbc", "Achievement.dbc"]

        results = {}
        for name in dbc_names:
            results[name] = self.sync_dbc(name)

        return results
```

### 3.5 CLI 命令扩展

#### 3.5.1 新增子命令

```python
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="wow-dbc-tool",
        description="魔兽世界 3.3.5 DBC 文件操作工具",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ... 现有命令 ...

    # ── help 命令 ──
    help_parser = subparsers.add_parser("help", help="显示帮助信息")
    help_parser.add_argument("command", nargs="?", help="子命令名称（可选）")
    help_parser.add_argument("--full", action="store_true", help="显示完整帮助")
    help_parser.add_argument("--json", action="store_true", help="JSON 输出")
    help_parser.add_argument("--compact", action="store_true", help="紧凑 JSON")
    help_parser.set_defaults(func=cmd_help)

    # ── explain 命令 ──
    explain_parser = subparsers.add_parser("explain", help="查询 DBC 说明")
    explain_parser.add_argument("dbc_name", help="DBC 文件名")
    explain_parser.add_argument("--field", action="append", default=[], help="查询特定字段")
    explain_parser.add_argument("--json", action="store_true", help="JSON 输出")
    explain_parser.add_argument("--compact", action="store_true", help="紧凑 JSON")
    explain_parser.set_defaults(func=cmd_explain)

    # ── wiki 命令 ──
    wiki_parser = subparsers.add_parser("wiki", help="Wiki 文档管理")
    wiki_subparsers = wiki_parser.add_subparsers(dest="wiki_command", help="wiki 子命令")

    # wiki sync
    wiki_sync = wiki_subparsers.add_parser("sync", help="同步 Wiki 文档")
    wiki_sync.add_argument("dbc_name", nargs="?", help="DBC 文件名，省略则同步所有")
    wiki_sync.add_argument("--all", action="store_true", help="同步所有已知 DBC")
    wiki_sync.set_defaults(func=cmd_wiki_sync)

    # wiki list
    wiki_list = wiki_subparsers.add_parser("list", help="列出本地文档")
    wiki_list.set_defaults(func=cmd_wiki_list)

    # ... 解析参数 ...
```

#### 3.5.2 命令处理函数

```python
def cmd_explain(args: argparse.Namespace) -> int:
    """explain 子命令."""
    from wow_dbc_tool.docs.explain import ExplainService
    from wow_dbc_tool.docs.store import DocStore

    service = ExplainService(DocStore())

    if args.field:
        # 查询特定字段
        results = {}
        for field_name in args.field:
            result = service.explain_field(args.dbc_name, field_name)
            if result:
                results[field_name] = result["field"]

        data = {
            "dbc_name": args.dbc_name,
            "fields": results,
            "not_found": [f for f in args.field if f not in results],
        }
    else:
        # 查询整个文件
        data = service.explain_file(args.dbc_name)
        if data is None:
            _error_json(f"未找到 {args.dbc_name} 的说明文档", "DocError")
            return 1

    _output_json(data, pretty=not args.compact)
    return 0


def cmd_wiki_sync(args: argparse.Namespace) -> int:
    """wiki sync 子命令."""
    try:
        from wow_dbc_tool.wiki.crawler import WikiCrawler
        from wow_dbc_tool.docs.store import DocStore
    except ImportError as e:
        _error_json(f"Wiki 同步需要 requests 和 beautifulsoup4: {e}", "ImportError")
        return 1

    crawler = WikiCrawler()
    store = DocStore()

    if args.all or args.dbc_name is None:
        # 同步所有
        results = crawler.sync_all()
    else:
        # 同步单个
        result = crawler.sync_dbc(args.dbc_name)
        results = {args.dbc_name: result}

    # 保存到本地
    saved = []
    failed = []
    for name, entry in results.items():
        if entry:
            store.save(entry)
            saved.append(name)
        else:
            failed.append(name)

    data = {
        "saved": saved,
        "failed": failed,
        "total": len(results),
    }
    _output_json(data, pretty=True)
    return 0 if not failed else 1


def cmd_wiki_list(args: argparse.Namespace) -> int:
    """wiki list 子命令."""
    from wow_dbc_tool.docs.store import DocStore

    store = DocStore()
    docs = store.list_all()

    data = {
        "docs_dir": str(store.docs_dir),
        "count": len(docs),
        "docs": docs,
    }
    _output_json(data, pretty=True)
    return 0
```

---

## 4. 项目目录结构（更新后）

```
wow-dbc-tool/
├── pyproject.toml              # 项目配置（新增可选依赖 requests, beautifulsoup4）
├── README.md
├── docs/
│   ├── architecture.md         # 现有架构文档
│   └── definitions/            # DBC 字段定义文档（新增）
│       ├── index.json          # 索引文件
│       └── *.md                # DBC 定义文档
├── src/wow_dbc_tool/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI 入口（扩展新命令）
│   ├── commands/               # 子命令实现（新增）
│   │   ├── __init__.py
│   │   ├── read.py
│   │   ├── query.py
│   │   ├── edit.py
│   │   ├── delete.py
│   │   ├── add.py
│   │   ├── diff.py
│   │   ├── schema.py
│   │   ├── help.py             # 新增
│   │   ├── explain.py          # 新增
│   │   └── wiki.py             # 新增
│   ├── core/                   # 核心库
│   │   ├── __init__.py
│   │   ├── dbc_file.py
│   │   ├── dbc_record.py
│   │   └── exceptions.py
│   ├── parser/                 # WDBC 解析
│   │   ├── __init__.py
│   │   ├── reader.py
│   │   ├── writer.py
│   │   └── header.py
│   ├── schema/                 # 字段定义
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── field_def.py
│   │   └── builtins/
│   ├── diff/                   # Diff 引擎
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   └── report.py
│   ├── docs/                   # 新增: 文档模块
│   │   ├── __init__.py
│   │   ├── store.py            # DocStore
│   │   └── explain.py          # ExplainService
│   ├── help/                   # 新增: 帮助模块
│   │   ├── __init__.py
│   │   └── system.py           # HelpSystem
│   └── wiki/                   # 新增: Wiki 模块（可选）
│       ├── __init__.py
│       └── crawler.py          # WikiCrawler
├── schemas/                    # 用户可加载的 Schema 文件
└── tests/                      # 测试
    ├── __init__.py
    ├── conftest.py
    ├── test_parser.py
    ├── test_core.py
    ├── test_diff.py
    ├── test_cli.py
    ├── test_docs.py            # 新增
    ├── test_help.py            # 新增
    └── fixtures/
```

---

## 5. 数据流图

### 5.1 Explain 查询流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLI     │───▶│ Explain  │───▶│ DocStore │───▶│ Markdown │
│ explain  │    │ Service  │    │ .get()   │    │  文件    │
│  cmd     │    │          │    │          │    │          │
└──────────┘    └────┬─────┘    └──────────┘    └──────────┘
                     │
                     ▼
               ┌──────────┐
               │  JSON    │
               │  输出    │
               └──────────┘
```

### 5.2 Wiki 同步流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLI     │───▶│ Wiki     │───▶│ wowdev   │───▶│  HTML    │
│ wiki     │    │ Crawler  │    │ .wiki    │    │  页面    │
│ sync cmd │    │          │    │          │    │          │
└──────────┘    └────┬─────┘    └──────────┘    └──────────┘
                     │
                     ▼
               ┌──────────┐
               │ Parse    │
               │ Fields   │
               └────┬─────┘
                    │
                    ▼
               ┌──────────┐    ┌──────────┐
               │ DocEntry │───▶│ DocStore │───▶ Markdown
               │          │    │ .save()  │     + index.json
               └──────────┘    └──────────┘
```

---

## 6. 错误处理策略

### 6.1 新增异常类型

```python
class DBCError(Exception):
    """基类"""
    pass

# 现有异常...

class DocError(DBCError):
    """文档错误（文档不存在、格式错误等）"""
    pass

class HelpError(DBCError):
    """帮助错误（未知命令等）"""
    pass

class WikiError(DBCError):
    """Wiki 同步错误（网络、解析失败等）"""
    pass
```

### 6.2 CLI 错误输出

```json
{
  "error": true,
  "type": "DocError",
  "message": "未找到 Spell.dbc 的说明文档。请运行 'wow-dbc-tool wiki sync Spell.dbc' 同步。"
}
```

---

## 7. 架构决策记录 (ADR)

### ADR-006: 文档格式选择 Markdown

- **上下文**: 需要一种格式存储 DBC 字段定义，兼顾人类可读和 Agent 解析
- **选项**: Markdown / JSON / YAML / 纯文本
- **决策**: Markdown
- **理由**: 
  - 人类可读性好，可直接在 GitHub 浏览
  - 结构清晰，便于 Agent 用简单规则解析
  - 与现有 docs/architecture.md 保持一致
  - 支持 frontmatter 存储元数据
- **权衡**: 需要写解析器，但解析逻辑简单

### ADR-007: 帮助文本内嵌 vs 外置

- **上下文**: 帮助文本存储位置
- **选项**: 内嵌在代码中 / 外置 JSON/YAML 文件
- **决策**: 内嵌在代码中（HelpSystem 类）
- **理由**: 
  - 不增加额外文件依赖
  - 与代码版本同步
  - 安装后无需携带数据文件
- **权衡**: 修改帮助需要改代码，但帮助文本变更频率低

### ADR-008: Wiki 数据预下载为主

- **上下文**: 如何获取 wowdev.wiki 的 DBC 定义
- **选项**: 实时爬虫 / 预下载缓存 / 混合
- **决策**: 预下载缓存为主
- **理由**: 
  - wowdev.wiki 结构稳定，3.3.5a DBC 定义不变
  - 离线可用对 Agent 工具更重要
  - 减少外部依赖（requests, bs4 为可选）
- **权衡**: 数据不会自动更新，需要手动同步

### ADR-009: 文档与 Schema 的关系

- **上下文**: 文档（Markdown）和 Schema（FieldDef 列表）的关系
- **选项**: 完全分离 / 文档生成 Schema / Schema 生成文档
- **决策**: 文档和 Schema 独立，但字段定义保持一致
- **理由**: 
  - Schema 是运行时必需的（解析 DBC 文件）
  - 文档是查询用的（说明字段含义）
  - 两者用途不同，不应耦合
- **权衡**: 需要维护两份字段列表，但可通过工具同步

### ADR-010: 新增模块位置

- **上下文**: docs, help, wiki 模块放在哪里
- **选项**: 放在 src/wow_dbc_tool/ 下 / 放在独立包中
- **决策**: 放在 src/wow_dbc_tool/ 下作为子模块
- **理由**: 
  - 与现有模块结构一致
  - 便于导入和使用
  - 不增加包管理复杂度
- **权衡**: 核心包体积稍增，但可接受

---

## 8. 测试策略

### 8.1 新增测试

```python
# test_docs.py
def test_doc_store_save_and_load():
    """测试文档保存和加载"""

def test_doc_store_get_missing():
    """测试获取不存在的文档"""

def test_doc_entry_to_dict():
    """测试文档条目序列化"""

# test_help.py
def test_help_system_brief():
    """测试简洁帮助"""

def test_help_system_command():
    """测试子命令帮助"""

def test_help_system_full():
    """测试完整帮助"""

def test_help_unknown_command():
    """测试未知命令帮助"""

# test_explain.py
def test_explain_file():
    """测试文件说明查询"""

def test_explain_field():
    """测试字段说明查询"""

def test_explain_missing_doc():
    """测试文档不存在"""
```

### 8.2 测试数据

```python
# tests/fixtures/docs/
# 提供示例 Markdown 文档用于测试
```

---

## 9. 安装与使用（更新后）

### 9.1 安装

```bash
git clone <repo>
cd wow-dbc-tool
pip install -e .

# 可选：安装 Wiki 同步依赖
pip install -e ".[wiki]"
```

### 9.2 pyproject.toml 更新

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "black>=23.0",
    "ruff>=0.1.0",
]
wiki = [
    "requests>=2.28.0",
    "beautifulsoup4>=4.11.0",
]
```

### 9.3 CLI 使用（新增命令）

```bash
# 帮助
wow-dbc-tool help                    # 简洁帮助
wow-dbc-tool help read               # read 命令帮助
wow-dbc-tool help --full             # 完整帮助

# 说明查询
wow-dbc-tool explain Spell.dbc --json
wow-dbc-tool explain Spell.dbc --field Name --json

# Wiki 同步
wow-dbc-tool wiki sync Spell.dbc     # 同步单个
wow-dbc-tool wiki sync --all         # 同步所有
wow-dbc-tool wiki list               # 列出本地文档
```

---

## 10. 质量检查清单

- [x] 所有需求已覆盖（Help/Explain/Wiki 集成）
- [x] 向后兼容（不破坏现有 CLI 接口）
- [x] 新增模块职责单一
- [x] 文档格式规范明确（Markdown）
- [x] 帮助系统分级清晰
- [x] Explain 输出 JSON 可序列化
- [x] Wiki 爬虫为可选依赖
- [x] 错误处理策略明确
- [x] 测试策略覆盖新增模块
- [x] 架构决策有记录和 rationale
- [x] 项目目录结构更新完整

---

*文档结束。本设计可直接用于开发实现。*
