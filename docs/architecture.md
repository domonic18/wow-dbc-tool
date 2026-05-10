# wow-dbc-tool 架构设计文档

> 版本: 1.0  
> 日期: 2025-05-10  
> 状态: 已定稿  

---

## 1. 项目概述

**wow-dbc-tool** 是一个面向 AI Agent 的魔兽世界 3.3.5 DBC 文件操作工具，支持读取、查询、编辑、删除、添加记录以及 Diff 对比功能。

### 1.1 设计目标

| 目标 | 说明 |
|------|------|
| Agent 友好 | 纯 Python，JSON 结构化输出，无 GUI 依赖 |
| 完整 CRUD | 支持 DBC 记录的增删改查 |
| Diff 能力 | 对比两个 DBC 版本，输出结构化差异报告 |
| 可扩展 | 支持自定义字段定义，内置常见 DBC 定义 |
| 易安装 | `pip install -e .` 一键安装 |

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
│  │  add    │ │  diff   │ │  --json │ │ --format │          │
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
```

### 2.2 模块划分

| 模块 | 职责 | 核心类/函数 |
|------|------|------------|
| `parser` | WDBC 格式解析 | `DBCReader`, `DBCHeader` |
| `writer` | WDBC 格式写入 | `DBCWriter` |
| `schema` | 字段定义管理 | `SchemaRegistry`, `FieldDef` |
| `core` | 业务逻辑封装 | `DBCFile` |
| `diff` | 差异对比引擎 | `DBCDiff`, `DiffReport` |
| `cli` | 命令行接口 | `main()`, 各子命令函数 |

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

## 6. Diff 引擎设计

### 6.1 Diff 算法

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
    
    def to_json(self) -> dict:
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

### 6.2 Modified 记录结构

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

## 7. CLI 接口设计

### 7.1 命令结构

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

Global Options:
  --json              JSON 输出（所有命令）
  --schema FILE       指定字段定义文件
  --output FILE       输出到文件
  --help              显示帮助
```

### 7.2 各子命令详细设计

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

---

## 8. 项目目录结构

```
wow-dbc-tool/
├── pyproject.toml              # 项目配置
├── README.md
├── docs/
│   └── architecture.md         # 本文件
├── src/
│   └── wow_dbc_tool/
│       ├── __init__.py
│       ├── __main__.py         # python -m wow_dbc_tool
│       ├── cli.py              # CLI 入口
│       ├── commands/           # 子命令实现
│       │   ├── __init__.py
│       │   ├── read.py
│       │   ├── query.py
│       │   ├── edit.py
│       │   ├── delete.py
│       │   ├── add.py
│       │   ├── diff.py
│       │   └── schema.py
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
│       │   ├── field_def.py    # FieldDef
│       │   └── builtins/       # 内置定义
│       │       ├── __init__.py
│       │       └── spell.py    # Spell.dbc 定义示例
│       └── diff/               # Diff 引擎
│           ├── __init__.py
│           ├── engine.py       # DBCDiff
│           └── report.py       # DiffReport
├── schemas/                    # 用户可加载的 Schema 文件
│   └── example.json
└── tests/                      # 测试
    ├── __init__.py
    ├── conftest.py
    ├── test_parser.py
    ├── test_core.py
    ├── test_diff.py
    ├── test_cli.py
    └── fixtures/               # 测试数据
        ├── minimal.dbc         # 最小测试 DBC
        └── Spell.dbc           # 真实 DBC 样本
```

---

## 9. 数据流图

### 9.1 读取流程

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

### 9.2 写入流程

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

### 9.3 Diff 流程

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

---

## 10. 测试策略

### 10.1 测试分层

| 层级 | 范围 | 工具 | 说明 |
|------|------|------|------|
| 单元测试 | parser, schema, diff | pytest | 纯逻辑，无 IO |
| 集成测试 | DBCFile 完整流程 | pytest + tmp_path | 读写真实文件 |
| CLI 测试 | 命令行接口 | pytest + subprocess | 端到端 |

### 10.2 测试数据

```python
# tests/fixtures/minimal.dbc
# 手工构造的最小 DBC 文件：
# - Magic: WDBC
# - 2 条记录，每条 8 字节（2 个 uint32）
# - 字符串块: "Hello\0World\0"

# 用于测试解析器的基础功能
```

### 10.3 关键测试用例

```python
# test_parser.py
def test_read_header():
    """验证文件头解析"""

def test_read_records():
    """验证记录读取"""

def test_string_lookup():
    """验证字符串偏移解析"""

def test_write_roundtrip():
    """验证读写一致性"""

# test_core.py
def test_query_exact_match():
    """精确查询"""

def test_query_operators():
    """操作符查询（gt, lt, contains）"""

def test_edit_record():
    """修改记录"""

def test_delete_record():
    """删除记录"""

def test_add_record():
    """添加记录"""

def test_save_rebuilds_string_block():
    """保存时重建字符串块"""

# test_diff.py
def test_diff_added():
    """检测新增记录"""

def test_diff_removed():
    """检测删除记录"""

def test_diff_modified():
    """检测修改记录"""

def test_diff_unchanged():
    """未变更记录"""

# test_cli.py
def test_cli_read_json():
    """CLI read --json 输出"""

def test_cli_query_filter():
    """CLI query --filter"""

def test_cli_diff():
    """CLI diff 输出格式"""
```

---

## 11. 错误处理策略

### 11.1 异常体系

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
```

### 11.2 CLI 错误输出

```json
{
  "error": true,
  "type": "DBCFormatError",
  "message": "Invalid WDBC magic: expected 'WDBC', got 'DB2 '"
}
```

---

## 12. 架构决策记录 (ADR)

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

---

## 13. 安装与使用

### 13.1 安装

```bash
git clone <repo>
cd wow-dbc-tool
pip install -e .
```

### 13.2 快速开始

```bash
# 读取 DBC
wow-dbc-tool read Spell.dbc --json

# 查询
wow-dbc-tool query Spell.dbc --filter ID=133 --json

# 修改
wow-dbc-tool edit Spell.dbc --filter ID=133 --set Name="New Spell" --output Spell_new.dbc

# 对比
wow-dbc-tool diff Spell.dbc Spell_new.dbc --json
```

### 13.3 Python API

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
print(report.to_json())
```

---

## 14. 质量检查清单

- [x] 所有需求已覆盖（读取/查询/编辑/删除/添加/Diff）
- [x] 模块划分清晰，职责单一
- [x] 解析器支持 WDBC 完整格式
- [x] Schema 机制支持内置 + 自定义
- [x] CLI 接口完整，JSON 输出统一
- [x] Diff 算法支持主键匹配和索引匹配
- [x] 错误处理策略明确
- [x] 测试策略覆盖单元/集成/CLI
- [x] 架构决策有记录和 rationale

---

*文档结束。本设计可直接用于开发实现。*