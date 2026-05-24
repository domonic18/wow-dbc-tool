# wow-dbc-tool 架构设计文档

> 版本: 1.1
> 日期: 2025-05-10
> 状态: 已定稿

---

## 1. 项目概述

**wow-dbc-tool** 是一个面向 AI Agent 的魔兽世界 3.3.5 DBC 文件操作工具，支持读取、查询、编辑、删除、添加记录、Diff 对比，以及帮助查询、文档说明和 Wiki 同步功能。

### 1.1 设计目标

| 目标 | 说明 |
|------|------|
| Agent 友好 | 纯 Python，JSON 结构化输出，无 GUI 依赖 |
| 完整 CRUD | 支持 DBC 记录的增删改查 |
| Diff 能力 | 对比两个 DBC 版本，输出结构化差异报告 |
| 可扩展 | 支持自定义字段定义，内置常见 DBC 定义 |
| 易安装 | `pip install -e .` 一键安装 |
| 文档集成 | 内置帮助系统，支持 Wowdev Wiki 字段定义同步 |

### 1.2 技术约束

- **语言**: Python 3.9+
- **输出格式**: JSON（机器友好）
- **安装方式**: `pip install -e .`
- **CLI 接口**: 命令行工具，支持 `--json` 输出

---

## 2. 系统架构

### 2.1 高层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  read   │ │ query   │ │  edit   │ │ delete  │          │
│  │  add    │ │  diff   │ │  schema │ │  help   │ ◄── 新增 │
│  │ explain │ │  wiki   │ │         │ │         │ ◄── 新增 │
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
   │         utils 子包（辅助模块）            │
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

### 2.2 模块划分

| 模块 | 职责 | 核心类/函数 |
|------|------|------------|
| `parser` | WDBC 格式解析 | `DBCReader`, `DBCHeader` |
| `writer` | WDBC 格式写入 | `DBCWriter` |
| `schema` | 字段定义管理 | `SchemaRegistry`, `FieldDef` |
| `core` | 业务逻辑封装 | `DBCFile`, `DBCRecord` |
| `diff` | 差异对比引擎 | `DBCDiff`, `DiffReport` |
| `cli` | 命令行接口 | `main()`, 各子命令函数 |
| `utils` | 辅助工具（文档/帮助/Wiki） | `DocStore`, `HelpSystem`, `WowdevWikiCrawler` |

---

## 3. WDBC 格式解析器设计

### 3.1 WDBC 文件结构

```
┌────────────────────────────────────────┐
│              文件头 (20 bytes)          │
│  ├─ Magic      'WDBC' (4 bytes)       │
│  ├─ RecordCount   uint32 (4 bytes)    │
│  ├─ FieldCount    uint32 (4 bytes)    │
│  ├─ RecordSize    uint32 (4 bytes)    │
│  ├─ StringBlockSize uint32 (4 bytes)  │
├────────────────────────────────────────┤
│              记录区                      │
│  ├─ Record 0  (RecordSize bytes)      │
│  ├─ Record 1  (RecordSize bytes)      │
│  ├─ ...                                │
├────────────────────────────────────────┤
│              字符串块                   │
│  ├─ "string1\0"                        │
│  ├─ "string2\0"                        │
│  ├─ ...                                │
└────────────────────────────────────────┘
```

### 3.2 文件头结构

```python
class DBCHeader:
    magic: str           # 'WDBC'
    record_count: int    # 记录数量
    field_count: int     # 字段数量
    record_size: int     # 每条记录字节数
    string_block_size: int  # 字符串块大小
```

### 3.3 字段类型映射

WDBC 字段在文件中是 4 字节对齐的原始数据，需要 Schema 定义来解释类型：

| DBC 原始类型 | Python 类型 | 说明 |
|-------------|------------|------|
| `uint32` | `int` | 无符号整数 |
| `int32` | `int` | 有符号整数 |
| `float` | `float` | 单精度浮点 |
| `string` | `str` | 字符串（偏移量指向字符串块） |

### 3.4 解析器接口

```python
class DBCReader:
    """WDBC 文件读取器"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.header: DBCHeader | None = None
        self.records: list[bytes] = []
        self.string_block: bytes = b''

    def read(self) -> None:
        """解析整个 DBC 文件"""
        # 1. 读取并验证文件头
        # 2. 读取所有记录到内存
        # 3. 读取字符串块

    def get_string(self, offset: int) -> str:
        """从字符串块获取字符串"""
        # 从 offset 开始读取到 \0 结束
```

### 3.5 写入器接口

```python
class DBCWriter:
    """WDBC 文件写入器"""

    def __init__(self, path: str | Path, header: DBCHeader):
        self.path = Path(path)
        self.header = header
        self.records: list[bytes] = []
        self.string_block: bytearray = bytearray()
        self.string_offsets: dict[str, int] = {}  # 字符串去重

    def add_record(self, raw_bytes: bytes) -> None:
        """添加原始记录"""

    def add_string(self, s: str) -> int:
        """添加字符串到字符串块，返回偏移量"""

    def write(self) -> None:
        """写入完整 DBC 文件"""
        # 1. 更新 header（record_count, string_block_size）
        # 2. 写入文件头
        # 3. 写入记录区
        # 4. 写入字符串块
```

---

## 4. 字段定义（Schema）管理

### 4.1 Schema 设计

每个 DBC 文件需要字段定义来正确解析。字段定义采用声明式格式：

```python
@dataclass
class FieldDef:
    name: str           # 字段名（如 "ID", "Name"）
    type: str           # 类型："uint32", "int32", "float", "string"
    offset: int         # 在记录中的字节偏移（从 0 开始，4 字节对齐）
```

### 4.2 Schema 注册表

```python
class SchemaRegistry:
    """管理所有 DBC 文件的字段定义"""

    # 内置常见 DBC 定义
    _builtins: dict[str, list[FieldDef]] = {
        'Spell.dbc': [
            FieldDef('ID', 'uint32', 0),
            FieldDef('Name', 'string', 4),
            # ...
        ],
        'Item.dbc': [
            # ...
        ],
        # 更多内置定义...
    }

    @classmethod
    def get(cls, dbc_name: str) -> list[FieldDef] | None:
        """获取指定 DBC 的字段定义"""

    @classmethod
    def register(cls, dbc_name: str, fields: list[FieldDef]) -> None:
        """注册自定义字段定义"""

    @classmethod
    def load_from_file(cls, path: str | Path) -> None:
        """从 JSON/YAML 文件加载字段定义"""
```

### 4.3 Schema 文件格式（JSON）

```json
{
  "Spell.dbc": {
    "fields": [
      {"name": "ID", "type": "uint32", "offset": 0},
      {"name": "Name", "type": "string", "offset": 4},
      {"name": "Rank", "type": "string", "offset": 8},
      {"name": "SpellIconID", "type": "uint32", "offset": 12}
    ]
  }
}
```

### 4.4 自动字段推断

当没有 Schema 定义时，提供基础推断：

```python
def infer_schema(field_count: int, record_size: int) -> list[FieldDef]:
    """
    根据 field_count 和 record_size 推断字段布局。

    简单策略：
    - 如果 record_size == field_count * 4：所有字段为 uint32
    - 否则：按 4 字节均分，标记为 "unknown"

    返回通用字段名：field_0, field_1, ...
    """
```

---

## 5. 核心 API 设计（DBCFile）

### 5.1 核心类接口

```python
class DBCRecord:
    """单条 DBC 记录"""

    def __init__(self, raw_data: bytes, schema: list[FieldDef], string_block: bytes):
        self._raw = raw_data
        self._schema = schema
        self._string_block = string_block

    def get(self, field_name: str) -> int | float | str | None:
        """获取字段值"""

    def set(self, field_name: str, value: int | float | str) -> None:
        """设置字段值（修改内部 raw_data）"""

    def to_dict(self) -> dict:
        """转为字典（用于 JSON 输出）"""

    @property
    def raw(self) -> bytes:
        """获取原始字节（用于写入）"""


class DBCFile:
    """DBC 文件操作主类"""

    def __init__(self, path: str | Path, schema: list[FieldDef] | None = None):
        self.path = Path(path)
        self.schema = schema or self._auto_load_schema()
        self.header: DBCHeader | None = None
        self.records: list[DBCRecord] = []
        self._string_block: bytes = b''
        self._modified = False

    # ── 加载 ──
    def load(self) -> 'DBCFile':
        """从文件加载"""

    # ── 查询 ──
    def query(self, **filters) -> list[DBCRecord]:
        """
        按字段值过滤查询。

        示例:
            dbc.query(ID=123)
            dbc.query(Name="Fireball")
            dbc.query(ID__gt=100)  # 大于
            dbc.query(Name__contains="Fire")
        """

    def get(self, **filters) -> DBCRecord | None:
        """获取单条记录，无匹配返回 None，多条抛异常"""

    def all(self) -> list[DBCRecord]:
        """获取所有记录"""

    # ── 修改 ──
    def edit(self, record: DBCRecord, **changes) -> DBCRecord:
        """修改记录字段"""

    def delete(self, **filters) -> int:
        """删除匹配记录，返回删除数量"""

    def add(self, **values) -> DBCRecord:
        """添加新记录"""

    # ── 保存 ──
    def save(self, path: str | Path | None = None) -> None:
        """保存到文件（自动重建字符串块）"""

    # ── 导出 ──
    def to_json(self) -> list[dict]:
        """导出为 JSON 可序列化的列表"""
```

### 5.2 查询操作符设计

```python
# 支持的查询操作符
OPERATORS = {
    'eq':    lambda a, b: a == b,      # 默认，可省略
    'ne':    lambda a, b: a != b,
    'gt':    lambda a, b: a > b,
    'gte':   lambda a, b: a >= b,
    'lt':    lambda a, b: a < b,
    'lte':   lambda a, b: a <= b,
    'contains': lambda a, b: b in str(a),  # 字符串包含
}

# 使用方式：字段名__操作符=值
dbc.query(Name__contains="Fire")
dbc.query(ID__gt=100, ID__lt=200)
```

---

## 6. 文档与帮助系统

### 6.1 文档存储模块（DocStore）

#### 文档目录结构

```
wow-dbc-tool/
├── docs/
│   ├── architecture.md         # 架构文档
│   ├── guides/                 # 使用指南
│   └── definitions/            # DBC 字段定义文档
│       ├── index.json          # 索引文件
│       ├── Spell.md            # Spell.dbc 说明
│       ├── Item.md             # Item.dbc 说明
│       └── ...
```

#### Markdown 文档格式规范

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

## 常见用法

```bash
# 查询特定法术
wow-dbc-tool query Spell.dbc --filter ID=133 --json

# 修改法术名称
wow-dbc-tool edit Spell.dbc --filter ID=133 --set Name="New Name"
```
```

#### DocStore 接口

```python
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


class DocStore:
    """文档存储管理器。

    管理 docs/definitions/ 目录下的 Markdown 文档和索引。
    """

    def __init__(self, docs_dir: str | Path | None = None): ...
    def get(self, dbc_name: str) -> DocEntry | None: ...
    def list_all(self) -> list[str]: ...
    def save(self, entry: DocEntry) -> None: ...
    def search_fields(self, query: str) -> list[dict]: ...
```

### 6.2 帮助系统模块（HelpSystem）

#### 分级帮助设计

```
┌─────────────────────────────────────────┐
│           帮助层级结构                   │
├─────────────────────────────────────────┤
│ Level 1: help                           │
│   - 工具简介                            │
│   - 子命令列表（名称 + 一句话说明）      │
│   - 全局选项                            │
├─────────────────────────────────────────┤
│ Level 2: help <command>                 │
│   - 子命令详细说明                      │
│   - 参数列表                            │
│   - 1-2 个基础示例                      │
├─────────────────────────────────────────┤
│ Level 3: help --full                    │
│   - 完整帮助（所有层级合并）             │
│   - 所有子命令详细说明                   │
│   - 完整示例集                          │
│   - 常见用例                            │
│   - 注意事项                            │
└─────────────────────────────────────────┘
```

#### HelpSystem 接口

```python
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
    """分级帮助系统。

    管理所有帮助文本，支持分级输出和 JSON 格式。
    帮助文本内嵌在代码中，不依赖外部文件。
    """

    def get_brief_help(self) -> dict: ...
    def get_command_help(self, command: str) -> dict | None: ...
    def get_full_help(self) -> dict: ...
    def list_commands(self) -> list[str]: ...
```

### 6.3 Explain 查询模块

基于 DocStore 提供 DBC 文件和字段的说明查询。

```bash
# 查询整个文件说明
wow-dbc-tool explain Spell.dbc --json

# 查询特定字段
wow-dbc-tool explain Spell.dbc --field Name --json
```

**文件说明输出：**

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
    {"name": "Name", "type": "string", "offset": 4, "description": "法术名称"}
  ],
  "examples": [
    "wow-dbc-tool query Spell.dbc --filter ID=133 --json"
  ]
}
```

### 6.4 Wiki 爬虫模块（WowdevWikiCrawler）

从 https://wowdev.wiki/ 下载 DBC 字段定义。可选模块，不导入时不影响核心功能。

```python
class WowdevWikiCrawler:
    """Wowdev Wiki 爬虫。

    从 wowdev.wiki 下载 DBC 字段定义。
    可选模块，需要 requests 和 beautifulsoup4。
    """

    BASE_URL = "https://wowdev.wiki"

    def fetch_dbc_page(self, dbc_name: str) -> str | None: ...
    def parse_dbc_fields(self, html: str) -> list[dict]: ...
    def sync_dbc(self, dbc_name: str) -> DocEntry | None: ...
    def sync_all(self, dbc_names: list[str] | None = None) -> dict[str, DocEntry | None]: ...
    def sync_and_save(self, dbc_names: list[str] | None = None) -> dict[str, bool]: ...
```

**设计决策：** 预下载缓存为主，预留实时同步扩展接口。

- wowdev.wiki 结构稳定，3.3.5a DBC 定义不变
- 离线可用对 Agent 工具更重要
- requests 和 beautifulsoup4 为可选依赖

---

## 7. Diff 引擎设计

### 7.1 Diff 算法

```python
class DBCDiff:
    """DBC 文件差异对比引擎"""

    def __init__(self, old: DBCFile, new: DBCFile, key_field: str = 'ID'):
        """
        key_field: 用于匹配记录的主键字段（默认 'ID'）
        """
        self.old = old
        self.new = new
        self.key_field = key_field

    def compare(self) -> DiffReport:
        """
        对比两个 DBC 文件，返回结构化差异报告。

        算法步骤：
        1. 以 key_field 为键，建立 old 和 new 的索引
        2. 找出 added: 在 new 中但不在 old 中的记录
        3. 找出 removed: 在 old 中但不在 new 中的记录
        4. 找出 modified: key 相同但字段值不同的记录
        5. 找出 unchanged: 完全相同的记录（可选）
        """

    def compare_by_index(self) -> DiffReport:
        """
        按记录索引对比（不依赖 key_field，逐行对比）。
        用于记录顺序有意义的场景。
        """


@dataclass
class DiffReport:
    """差异报告"""

    added: list[dict]       # 新增记录
    removed: list[dict]     # 删除记录
    modified: list[dict]    # 修改记录（包含 old/new 对比）
    unchanged: list[dict]   # 未变更记录（可选）
    summary: DiffSummary

    def to_dict(self) -> dict:
        """转为 JSON 结构"""


@dataclass
class DiffSummary:
    """差异摘要"""

    total_old: int
    total_new: int
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
```

### 7.2 Modified 记录结构

```json
{
  "modified": [
    {
      "key": {"ID": 123},
      "changes": {
        "Name": {
          "old": "Fireball",
          "new": "Fireball Rank 1"
        },
        "SpellIconID": {
          "old": 1,
          "new": 2
        }
      }
    }
  ]
}
```

---

## 8. CLI 接口设计

### 8.1 命令结构

```
wow-dbc-tool <command> [options] <dbc-file>

Commands:
  read      读取并输出 DBC 内容
  query     按条件查询记录
  edit      修改记录字段
  delete    删除记录
  add       添加新记录
  diff      对比两个 DBC 文件
  schema    管理字段定义
  help      显示帮助信息              # 新增
  explain   查询 DBC 说明             # 新增
  wiki      Wiki 文档管理             # 新增

Global Options:
  --json              JSON 输出（所有命令）
  --schema FILE       指定字段定义文件
  --output FILE       输出到文件
  --help              显示帮助
```

### 8.2 各子命令详细设计

#### `read` - 读取 DBC

```bash
# 输出所有记录
wow-dbc-tool read Spell.dbc --json

# 限制输出条数
wow-dbc-tool read Spell.dbc --limit 10 --json

# 指定字段定义
wow-dbc-tool read Spell.dbc --schema schemas/spell.json --json
```

输出格式：
```json
{
  "file": "Spell.dbc",
  "header": {
    "magic": "WDBC",
    "record_count": 1234,
    "field_count": 56,
    "record_size": 224,
    "string_block_size": 45678
  },
  "records": [
    {"ID": 1, "Name": "Fireball", ...},
    ...
  ]
}
```

#### `query` - 查询记录

```bash
# 精确匹配
wow-dbc-tool query Spell.dbc --filter ID=123 --json

# 范围查询
wow-dbc-tool query Spell.dbc --filter "ID__gt=100" --filter "ID__lt=200" --json

# 字符串包含
wow-dbc-tool query Spell.dbc --filter "Name__contains=Fire" --json

# 多条件 AND
wow-dbc-tool query Spell.dbc --filter ID=123 --filter Name=Fireball --json
```

#### `edit` - 修改记录

```bash
# 按条件查找并修改
wow-dbc-tool edit Spell.dbc --filter ID=123 --set Name="New Name" --json

# 修改多个字段
wow-dbc-tool edit Spell.dbc --filter ID=123 \
  --set Name="New Name" \
  --set SpellIconID=5 \
  --output Spell_modified.dbc
```

输出格式：
```json
{
  "modified": 1,
  "records": [
    {"ID": 123, "Name": "New Name", "SpellIconID": 5, ...}
  ]
}
```

#### `delete` - 删除记录

```bash
# 按条件删除
wow-dbc-tool delete Spell.dbc --filter ID=123 --output Spell_modified.dbc --json

# 批量删除
wow-dbc-tool delete Spell.dbc --filter "ID__gt=1000" --output Spell_modified.dbc --json
```

输出格式：
```json
{
  "deleted": 5,
  "remaining": 1229
}
```

#### `add` - 添加记录

```bash
# 添加单条记录
wow-dbc-tool add Spell.dbc \
  --field ID=9999 \
  --field Name="Custom Spell" \
  --field SpellIconID=1 \
  --output Spell_modified.dbc --json
```

输出格式：
```json
{
  "added": 1,
  "new_record": {"ID": 9999, "Name": "Custom Spell", ...}
}
```

#### `diff` - 对比文件

```bash
# 对比两个 DBC 文件
wow-dbc-tool diff Spell_old.dbc Spell_new.dbc --json

# 指定主键字段
wow-dbc-tool diff Spell_old.dbc Spell_new.dbc --key-field ID --json

# 按索引对比（不按 ID）
wow-dbc-tool diff Spell_old.dbc Spell_new.dbc --by-index --json
```

输出格式：
```json
{
  "summary": {
    "total_old": 1234,
    "total_new": 1235,
    "added_count": 2,
    "removed_count": 1,
    "modified_count": 5,
    "unchanged_count": 1227
  },
  "added": [...],
  "removed": [...],
  "modified": [
    {
      "key": {"ID": 123},
      "changes": {
        "Name": {"old": "Old", "new": "New"}
      }
    }
  ]
}
```

#### `schema` - 字段定义管理

```bash
# 列出内置定义
wow-dbc-tool schema list --json

# 显示某个 DBC 的字段定义
wow-dbc-tool schema show Spell.dbc --json

# 导出推断的字段定义
wow-dbc-tool schema infer Spell.dbc --output spell_schema.json

# 验证字段定义
wow-dbc-tool schema validate Spell.dbc --schema schemas/spell.json
```

#### `help` - 帮助信息（新增）

```bash
# 简洁帮助
wow-dbc-tool help --json

# 子命令帮助
wow-dbc-tool help read --json

# 完整帮助
wow-dbc-tool help --full --json
```

#### `explain` - DBC 说明查询（新增）

```bash
# 查询文件说明
wow-dbc-tool explain Spell.dbc --json

# 查询特定字段
wow-dbc-tool explain Spell.dbc --field Name --json
```

#### `wiki` - Wiki 文档管理（新增）

```bash
# 同步单个 DBC 定义
wow-dbc-tool wiki sync Spell.dbc --json

# 同步所有常见 DBC
wow-dbc-tool wiki sync --all --json

# 列出本地已同步的文档
wow-dbc-tool wiki list --json
```

---

## 9. 项目目录结构

```
wow-dbc-tool/
├── pyproject.toml              # 项目配置
├── README.md
├── LICENSE                     # MIT 许可证
├── .gitignore
├── docs/
│   ├── guides/                 # 架构文档与使用指南
│   │   ├── architecture.md     # 本文件
│   │   ├── ARCHITECTURE_COMPLETE_REPORT.md
│   │   ├── help-explain-wowdev-architecture.md
│   │   └── MOUNT_CONFIGURATION_GUIDE.md
│   └── definitions/            # DBC 字段定义文档
│       ├── index.json          # 索引文件
│       ├── Spell.md
│       ├── Item.md
│       └── ...
├── src/
│   └── wow_dbc_tool/
│       ├── __init__.py
│       ├── __main__.py         # python -m wow_dbc_tool
│       ├── cli.py              # CLI 入口
│       ├── core/               # 核心库
│       │   ├── __init__.py
│       │   ├── dbc_file.py     # DBCFile 类
│       │   ├── dbc_record.py   # DBCRecord 类
│       │   └── exceptions.py   # 自定义异常
│       ├── parser/             # WDBC 解析
│       │   ├── __init__.py
│       │   ├── reader.py       # DBCReader
│       │   ├── writer.py       # DBCWriter
│       │   └── header.py       # DBCHeader
│       ├── schema/             # 字段定义
│       │   ├── __init__.py
│       │   ├── registry.py     # SchemaRegistry
│       │   └── field_def.py    # FieldDef
│       ├── diff/               # Diff 引擎
│       │   ├── __init__.py
│       │   └── engine.py       # DBCDiff
│       └── utils/              # 辅助工具
│           ├── __init__.py
│           ├── doc_store.py    # DocStore, DocEntry
│           ├── help_system.py  # HelpSystem, CommandHelp
│           └── wowdev_crawler.py  # WowdevWikiCrawler
├── test_data/                  # 测试数据
│   ├── fixtures/               # 小型合成测试文件
│   ├── schemas/                # 自定义 schema 定义
│   └── samples/                # 真实 DBC 样本
│       ├── original/
│       └── diy/
├── tests/                      # 测试
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_cli_explain.py
│   ├── test_core.py
│   ├── test_diff.py
│   ├── test_docs.py
│   ├── test_help.py
│   ├── test_parser.py
│   ├── test_real_dbc.py
│   └── test_wiki_crawler.py
└── htmlcov/                    # 覆盖率报告（生成文件，不提交）
```

---

## 10. 数据流图

### 10.1 读取流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLI     │───▶│ DBCFile  │───▶│DBCReader │───▶│ 文件系统 │
│ read cmd │    │  .load() │    │  .read() │    │ .dbc文件 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                      │
                      ▼
                ┌──────────┐
                │SchemaReg.│
                │ .get()   │
                └──────────┘
                      │
                      ▼
                ┌──────────┐
                │DBCRecord │
                │ 列表     │
                └──────────┘
                      │
                      ▼
                ┌──────────┐
                │ JSON输出  │
                └──────────┘
```

### 10.2 写入流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 修改操作  │───▶│ DBCRecord│───▶│DBCWriter │───▶│ 文件系统 │
│edit/add/ │    │.set()   │    │ .write() │    │ .dbc文件 │
│ delete   │    └──────────┘    └──────────┘    └──────────┘
└──────────┘         │
                     ▼
               ┌──────────┐
               │重建字符串块│
               │(去重+排序) │
               └──────────┘
```

### 10.3 Diff 流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ old.dbc  │───▶│ DBCFile  │───┐
└──────────┘    │  .load() │   │    ┌──────────┐
                └──────────┘   ├───▶│ DBCDiff  │───▶ DiffReport
┌──────────┐    ┌──────────┐   │    │.compare()│      (JSON)
│ new.dbc  │───▶│ DBCFile  │───┘    └──────────┘
└──────────┘    │  .load() │
                └──────────┘
```

### 10.4 Explain 查询流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLI     │───▶│ cmd_     │───▶│ DocStore │───▶│ Markdown │
│ explain  │    │ explain  │    │ .get()   │    │  文件    │
│  cmd     │    │          │    │          │    │          │
└──────────┘    └────┬─────┘    └──────────┘    └──────────┘
                     │
                     ▼
               ┌──────────┐
               │  JSON    │
               │  输出    │
               └──────────┘
```

### 10.5 Wiki 同步流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  CLI     │───▶│ Wowdev   │───▶│ wowdev   │───▶│  HTML    │
│ wiki     │    │ Wiki     │    │ .wiki    │    │  页面    │
│ sync cmd │    │ Crawler  │    │          │    │          │
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

## 11. 测试策略

### 11.1 测试分层

| 层级 | 范围 | 工具 | 说明 |
|------|------|------|------|
| 单元测试 | parser, schema, diff | pytest | 纯逻辑，无 IO |
| 集成测试 | DBCFile 完整流程 | pytest + tmp_path | 读写真实文件 |
| CLI 测试 | 命令行接口 | pytest + subprocess | 端到端 |
| 文档测试 | DocStore, HelpSystem | pytest + tmp_path | 辅助模块 |

### 11.2 关键测试用例

```python
# test_parser.py
def test_read_header(): ...
def test_read_records(): ...
def test_string_lookup(): ...
def test_write_roundtrip(): ...

# test_core.py
def test_query_exact_match(): ...
def test_query_operators(): ...
def test_edit_record(): ...
def test_delete_record(): ...
def test_add_record(): ...
def test_save_rebuilds_string_block(): ...

# test_diff.py
def test_diff_added(): ...
def test_diff_removed(): ...
def test_diff_modified(): ...

# test_cli.py
def test_cli_read_json(): ...
def test_cli_query_filter(): ...
def test_cli_diff(): ...

# test_docs.py（新增）
def test_doc_store_save_and_load(): ...
def test_doc_store_parse_markdown(): ...

# test_help.py（新增）
def test_help_system_brief(): ...
def test_help_system_command(): ...
def test_help_system_full(): ...
```

---

## 12. 错误处理策略

### 12.1 异常体系

```python
class DBCError(Exception):
    """基类"""
    pass

class DBCFormatError(DBCError):
    """文件格式错误（Magic 不对、尺寸不匹配等）"""
    pass

class DBCSchemaError(DBCError):
    """字段定义错误（找不到定义、类型不匹配等）"""
    pass

class DBCQueryError(DBCError):
    """查询错误（字段不存在、操作符不支持等）"""
    pass

class DBCDiffError(DBCError):
    """Diff 错误（key_field 不存在等）"""
    pass

class DocError(DBCError):
    """文档错误（文档不存在、格式错误等）"""
    pass

class HelpError(DBCError):
    """帮助错误（未知命令等）"""
    pass
```

### 12.2 CLI 错误输出

```json
{
  "error": true,
  "type": "DBCFormatError",
  "message": "Invalid WDBC magic: expected 'WDBC', got 'DB2 '"
}
```

---

## 13. 架构决策记录 (ADR)

### ADR-001: 纯 Python 实现

- **上下文**: 需要 Agent 生态友好
- **选项**: Python / Go / Rust
- **决策**: Python
- **理由**: Agent 工具链以 Python 为主，易于集成
- **权衡**: 性能不如 Rust，但 DBC 文件通常不大（<100MB），Python 足够

### ADR-002: 全内存加载

- **上下文**: DBC 文件大小通常在 1-50MB
- **选项**: 全内存 / 内存映射 / 流式
- **决策**: 全内存加载
- **理由**: 简化实现，支持随机查询和修改
- **权衡**: 大文件（>100MB）内存占用高，但魔兽世界 DBC 不会这么大

### ADR-003: Schema 外置 + 内置默认

- **上下文**: DBC 需要字段定义才能正确解析字符串和类型
- **选项**: 完全外置 / 完全内置 / 混合
- **决策**: 混合模式（内置常见定义 + 支持外置加载）
- **理由**: 开箱即用，同时支持自定义和扩展
- **权衡**: 内置定义需要维护，可能不全

### ADR-004: 字符串块重建策略

- **上下文**: 修改记录后字符串块会变化
- **选项**: 增量更新 / 完全重建
- **决策**: 保存时完全重建字符串块
- **理由**: 实现简单，自动去重，保证一致性
- **权衡**: 字符串偏移全部改变，但不影响功能

### ADR-005: Diff 主键匹配策略

- **上下文**: 对比两个 DBC 版本需要匹配对应记录
- **选项**: 按索引位置 / 按主键字段
- **决策**: 默认按主键（ID），支持按索引
- **理由**: DBC 记录顺序可能变化，ID 是唯一稳定标识
- **权衡**: 需要指定正确的主键字段

### ADR-006: 文档格式选择 Markdown

- **上下文**: 需要一种格式存储 DBC 字段定义，兼顾人类可读和 Agent 解析
- **选项**: Markdown / JSON / YAML / 纯文本
- **决策**: Markdown
- **理由**: 人类可读性好，可直接在 GitHub 浏览；结构清晰，便于 Agent 用简单规则解析
- **权衡**: 需要写解析器，但解析逻辑简单

### ADR-007: 帮助文本内嵌 vs 外置

- **上下文**: 帮助文本存储位置
- **选项**: 内嵌在代码中 / 外置 JSON/YAML 文件
- **决策**: 内嵌在代码中（HelpSystem 类）
- **理由**: 不增加额外文件依赖，与代码版本同步，安装后无需携带数据文件
- **权衡**: 修改帮助需要改代码，但帮助文本变更频率低

### ADR-008: Wiki 数据预下载为主

- **上下文**: 如何获取 wowdev.wiki 的 DBC 定义
- **选项**: 实时爬虫 / 预下载缓存 / 混合
- **决策**: 预下载缓存为主
- **理由**: wowdev.wiki 结构稳定，3.3.5a DBC 定义不变；离线可用对 Agent 工具更重要；减少外部依赖
- **权衡**: 数据不会自动更新，需要手动同步

### ADR-009: 文档与 Schema 的关系

- **上下文**: 文档（Markdown）和 Schema（FieldDef 列表）的关系
- **选项**: 完全分离 / 文档生成 Schema / Schema 生成文档
- **决策**: 文档和 Schema 独立，但字段定义保持一致
- **理由**: Schema 是运行时必需的（解析 DBC 文件），文档是查询用的（说明字段含义），两者用途不同，不应耦合
- **权衡**: 需要维护两份字段列表，但可通过工具同步

### ADR-010: 辅助模块归入 utils 子包

- **上下文**: doc_store、help_system、wowdev_crawler 等辅助模块的组织方式
- **选项**: 放在包根目录 / 放在独立子包中
- **决策**: 放在 `utils/` 子包中
- **理由**: 避免包根目录过于拥挤，职责边界清晰，与核心模块（core/parser/schema/diff）分离
- **权衡**: 导入路径多一层 `utils.`，但语义更清晰

---

## 14. 安装与使用

### 14.1 安装

```bash
git clone <repo>
cd wow-dbc-tool
pip install -e .

# 可选：安装 Wiki 同步依赖
pip install requests beautifulsoup4
```

### 14.2 快速开始

```bash
# 读取 DBC
wow-dbc-tool read Spell.dbc --json

# 查询
wow-dbc-tool query Spell.dbc --filter ID=133 --json

# 修改
wow-dbc-tool edit Spell.dbc --filter ID=133 --set Name="New Spell" --output Spell_new.dbc

# 对比
wow-dbc-tool diff Spell.dbc Spell_new.dbc --json

# 帮助
wow-dbc-tool help --json

# 说明查询
wow-dbc-tool explain Spell.dbc --json
```

### 14.3 Python API

```python
from wow_dbc_tool import DBCFile

# 加载
dbc = DBCFile('Spell.dbc').load()

# 查询
records = dbc.query(Name__contains="Fire")

# 修改
for r in records:
    r.set('Name', r.get('Name') + ' (Modified)')

# 保存
dbc.save('Spell_modified.dbc')

# Diff
from wow_dbc_tool.diff import DBCDiff
report = DBCDiff(dbc_old, dbc_new).compare()
print(report.to_dict())
```

---

## 15. 质量检查清单

- [x] 所有需求已覆盖（读取/查询/编辑/删除/添加/Diff/Help/Explain/Wiki）
- [x] 模块划分清晰，职责单一
- [x] 解析器支持 WDBC 完整格式
- [x] Schema 机制支持内置 + 自定义
- [x] CLI 接口完整，JSON 输出统一
- [x] Diff 算法支持主键匹配和索引匹配
- [x] 文档存储与帮助系统集成
- [x] Wiki 爬虫为可选依赖
- [x] 错误处理策略明确
- [x] 测试策略覆盖单元/集成/CLI/文档
- [x] 架构决策有记录和 rationale

---

*文档结束。本设计可直接用于开发实现。*
