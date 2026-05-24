"""测试文档存储模块."""

import json

from wow_dbc_tool.utils.doc_store import DocEntry, DocStore


class TestDocEntry:
    """测试 DocEntry 数据类."""

    def test_default_creation(self):
        """测试默认创建."""
        entry = DocEntry(name="Spell.dbc")
        assert entry.name == "Spell.dbc"
        assert entry.title == ""
        assert entry.version == "3.3.5a"

    def test_to_dict(self):
        """测试序列化为字典."""
        entry = DocEntry(
            name="Spell.dbc",
            title="Spell.dbc - 法术定义",
            field_count=5,
            fields=[{"name": "ID", "type": "uint32"}],
        )
        data = entry.to_dict()
        assert data["name"] == "Spell.dbc"
        assert data["field_count"] == 5
        assert len(data["fields"]) == 1


class TestDocStore:
    """测试 DocStore 类."""

    def test_init_with_custom_dir(self, tmp_path):
        """测试自定义目录初始化."""
        store = DocStore(tmp_path)
        assert store.docs_dir == tmp_path
        assert store.index_path == tmp_path / "index.json"

    def test_save_and_load(self, tmp_path):
        """测试保存和加载文档."""
        store = DocStore(tmp_path)
        entry = DocEntry(
            name="Test.dbc",
            title="Test DBC",
            field_count=3,
            record_size=12,
            fields=[
                {"name": "ID", "type": "uint32", "offset": 0, "description": "ID 字段"},
                {"name": "Name", "type": "string", "offset": 4},
            ],
            overview="测试文档",
            examples=["wow-dbc-tool read Test.dbc"],
        )

        store.save(entry)

        # 验证文件存在
        assert (tmp_path / "Test.md").exists()
        assert (tmp_path / "index.json").exists()

        # 验证索引
        with open(tmp_path / "index.json", encoding="utf-8") as f:
            index = json.load(f)
        assert index["Test.dbc"] == "Test.md"

    def test_get_existing(self, tmp_path):
        """测试获取存在的文档."""
        store = DocStore(tmp_path)
        entry = DocEntry(
            name="Test.dbc",
            title="Test DBC",
            field_count=2,
            fields=[{"name": "ID", "type": "uint32"}],
        )
        store.save(entry)

        loaded = store.get("Test.dbc")
        assert loaded is not None
        assert loaded.name == "Test.dbc"
        assert loaded.field_count == 2

    def test_get_missing(self, tmp_path):
        """测试获取不存在的文档."""
        store = DocStore(tmp_path)
        result = store.get("Nonexistent.dbc")
        assert result is None

    def test_list_all(self, tmp_path):
        """测试列出所有文档."""
        store = DocStore(tmp_path)
        store.save(DocEntry(name="A.dbc", title="A"))
        store.save(DocEntry(name="B.dbc", title="B"))

        docs = store.list_all()
        assert "A.dbc" in docs
        assert "B.dbc" in docs

    def test_parse_markdown(self, tmp_path):
        """测试解析 Markdown 文件."""
        # 创建测试 Markdown 文件
        md_content = """# Spell.dbc

> 来源: https://wowdev.wiki/Spell.dbc
> 版本: 3.3.5a
> 最后同步: 2025-05-10

## 概述

Spell.dbc 包含游戏中所有法术的定义。

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
- **示例**: 133

### Name
- **偏移**: 4
- **类型**: string
- **说明**: 法术名称

## 常见用法

```bash
wow-dbc-tool query Spell.dbc --filter ID=133 --json
```
"""
        md_path = tmp_path / "Spell.md"
        md_path.write_text(md_content, encoding="utf-8")

        # 创建索引
        index = {"Spell.dbc": "Spell.md"}
        (tmp_path / "index.json").write_text(json.dumps(index), encoding="utf-8")

        store = DocStore(tmp_path)
        entry = store.get("Spell.dbc")

        assert entry is not None
        assert entry.name == "Spell.dbc"
        assert entry.title == "Spell.dbc"
        assert entry.source == "https://wowdev.wiki/Spell.dbc"
        assert entry.version == "3.3.5a"
        assert entry.field_count == 234
        assert entry.record_size == 936
        assert "法术" in entry.overview
        assert len(entry.fields) == 2
        assert entry.fields[0]["name"] == "ID"
        assert entry.fields[0]["offset"] == 0
        assert entry.fields[1]["name"] == "Name"

    def test_render_markdown(self, tmp_path):
        """测试渲染 Markdown."""
        store = DocStore(tmp_path)
        entry = DocEntry(
            name="Test.dbc",
            title="Test DBC",
            source="https://example.com",
            version="3.3.5a",
            last_sync="2025-05-10",
            field_count=2,
            record_size=8,
            fields=[
                {"name": "ID", "type": "uint32", "offset": 0, "description": "ID"},
            ],
            overview="测试",
            examples=["wow-dbc-tool read Test.dbc"],
        )

        store.save(entry)

        # 读取并验证
        content = (tmp_path / "Test.md").read_text(encoding="utf-8")
        assert "# Test DBC" in content
        assert "> 来源: https://example.com" in content
        assert "## 概述" in content
        assert "### ID" in content
        assert "**偏移**: 0" in content

    def test_search_fields(self, tmp_path):
        """测试字段搜索."""
        store = DocStore(tmp_path)
        store.save(
            DocEntry(
                name="Spell.dbc",
                fields=[
                    {"name": "ID", "type": "uint32"},
                    {"name": "Name", "type": "string"},
                ],
            )
        )
        store.save(
            DocEntry(
                name="Item.dbc",
                fields=[
                    {"name": "ID", "type": "uint32"},
                    {"name": "DisplayName", "type": "string"},
                ],
            )
        )

        results = store.search_fields("Name")
        assert len(results) >= 1
        # 至少找到 Spell.dbc 的 Name 字段
        spell_names = [r for r in results if r["dbc_name"] == "Spell.dbc"]
        assert len(spell_names) >= 1

    def test_cache(self, tmp_path):
        """测试缓存机制."""
        store = DocStore(tmp_path)
        entry = DocEntry(name="Test.dbc", title="Test")
        store.save(entry)

        # 第一次加载
        first = store.get("Test.dbc")
        assert first is not None

        # 第二次应该从缓存获取
        second = store.get("Test.dbc")
        assert second is first  # 同一对象
