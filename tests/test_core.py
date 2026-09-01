"""核心 API 单元测试."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from wow_dbc_tool.core.dbc_file import DBCFile
from wow_dbc_tool.core.dbc_record import DBCRecord
from wow_dbc_tool.core.exceptions import (
    DBCError,
    DBCNotLoadedError,
    DBCQueryError,
    DBCSchemaError,
)
from wow_dbc_tool.schema.field_def import FieldDef


class TestDBCRecord:
    """测试 DBCRecord."""

    def test_get_uint32(self):
        """测试读取 uint32 字段."""
        raw = struct.pack("<3I", 123, 456, 789)
        schema = [
            FieldDef("ID", "uint32", 0),
            FieldDef("Value", "uint32", 4),
            FieldDef("Extra", "uint32", 8),
        ]
        record = DBCRecord(raw, schema, b"")

        assert record.get("ID") == 123
        assert record.get("Value") == 456
        assert record.get("Extra") == 789

    def test_get_int32(self):
        """测试读取 int32 字段."""
        raw = struct.pack("<i", -42)
        schema = [FieldDef("Signed", "int32", 0)]
        record = DBCRecord(raw, schema, b"")

        assert record.get("Signed") == -42

    def test_get_float(self):
        """测试读取 float 字段."""
        raw = struct.pack("<f", 3.14)
        schema = [FieldDef("Ratio", "float", 0)]
        record = DBCRecord(raw, schema, b"")

        assert abs(record.get("Ratio") - 3.14) < 0.01

    def test_get_string(self):
        """测试读取 string 字段."""
        string_block = b"Hello\x00World\x00"
        raw = struct.pack("<2I", 0, 6)  # 偏移 0 和 6
        schema = [
            FieldDef("Name", "string", 0),
            FieldDef("Title", "string", 4),
        ]
        record = DBCRecord(raw, schema, string_block)

        assert record.get("Name") == "Hello"
        assert record.get("Title") == "World"

    def test_get_string_empty(self):
        """测试空字符串偏移."""
        string_block = b"\x00"
        raw = struct.pack("<I", 0)
        schema = [FieldDef("Name", "string", 0)]
        record = DBCRecord(raw, schema, string_block)

        assert record.get("Name") == ""

    def test_get_field_not_found(self):
        """测试字段不存在."""
        raw = struct.pack("<I", 1)
        schema = [FieldDef("ID", "uint32", 0)]
        record = DBCRecord(raw, schema, b"")

        with pytest.raises(DBCSchemaError, match="字段不存在"):
            record.get("NonExistent")

    def test_set_uint32(self):
        """测试设置 uint32 字段."""
        raw = struct.pack("<I", 1)
        schema = [FieldDef("ID", "uint32", 0)]
        record = DBCRecord(raw, schema, b"")

        record.set("ID", 999)
        assert record.get("ID") == 999

    def test_set_int32(self):
        """测试设置 int32 字段."""
        raw = struct.pack("<i", 0)
        schema = [FieldDef("Value", "int32", 0)]
        record = DBCRecord(raw, schema, b"")

        record.set("Value", -100)
        assert record.get("Value") == -100

    def test_set_float(self):
        """测试设置 float 字段."""
        raw = struct.pack("<f", 0.0)
        schema = [FieldDef("Ratio", "float", 0)]
        record = DBCRecord(raw, schema, b"")

        record.set("Ratio", 2.5)
        assert abs(record.get("Ratio") - 2.5) < 0.01

    def test_set_string(self):
        """测试设置 string 字段."""
        raw = struct.pack("<I", 0)
        schema = [FieldDef("Name", "string", 0)]
        record = DBCRecord(raw, schema, b"")

        record.set("Name", "NewName")
        # 此时 raw 中是占位符，保存时重建
        pending = record.get_pending_strings()
        assert pending["Name"] == "NewName"

    def test_set_type_mismatch(self):
        """测试类型不匹配."""
        raw = struct.pack("<I", 0)
        schema = [FieldDef("ID", "uint32", 0)]
        record = DBCRecord(raw, schema, b"")

        with pytest.raises(DBCSchemaError, match="需要 int"):
            record.set("ID", "string")

    def test_to_dict(self):
        """测试转为字典."""
        raw = struct.pack("<2I", 123, 456)
        schema = [
            FieldDef("ID", "uint32", 0),
            FieldDef("Value", "uint32", 4),
        ]
        record = DBCRecord(raw, schema, b"")

        d = record.to_dict()
        assert d == {"ID": 123, "Value": 456}

    def test_raw_property(self):
        """测试 raw 属性."""
        raw = struct.pack("<I", 123)
        schema = [FieldDef("ID", "uint32", 0)]
        record = DBCRecord(raw, schema, b"")

        assert record.raw == raw

    def test_eq(self):
        """测试相等比较."""
        raw = struct.pack("<I", 123)
        schema = [FieldDef("ID", "uint32", 0)]
        r1 = DBCRecord(raw, schema, b"")
        r2 = DBCRecord(raw, schema, b"")

        assert r1 == r2


class TestDBCFile:
    """测试 DBCFile."""

    def test_load(self, minimal_dbc: Path, sample_schema):
        """测试加载文件."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        assert dbc.header is not None
        assert dbc.header.record_count == 2
        assert len(dbc.records) == 2

    def test_load_not_found(self):
        """测试文件不存在."""
        dbc = DBCFile("/nonexistent.dbc")
        with pytest.raises(FileNotFoundError):
            dbc.load()

    def test_query_not_loaded(self):
        """测试未加载时查询."""
        dbc = DBCFile("test.dbc")
        with pytest.raises(DBCNotLoadedError):
            dbc.query(ID=1)

    def test_query_exact_match(self, minimal_dbc: Path, sample_schema):
        """测试精确查询."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        results = dbc.query(ID=1)
        assert len(results) == 1
        assert results[0].get("ID") == 1

    def test_query_no_match(self, minimal_dbc: Path, sample_schema):
        """测试无匹配."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        results = dbc.query(ID=999)
        assert len(results) == 0

    def test_query_gt_operator(self, minimal_dbc: Path, sample_schema):
        """测试大于操作符."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        results = dbc.query(ID__gt=0)
        assert len(results) == 2

    def test_query_lt_operator(self, minimal_dbc: Path, sample_schema):
        """测试小于操作符."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        results = dbc.query(ID__lt=2)
        assert len(results) == 1
        assert results[0].get("ID") == 1

    def test_query_contains_operator(self, minimal_dbc: Path, sample_schema):
        """测试包含操作符."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        results = dbc.query(Name__contains="ell")
        assert len(results) == 1
        assert results[0].get("Name") == "Hello"

    def test_query_multiple_conditions(self, minimal_dbc: Path, sample_schema):
        """测试多条件 AND."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        results = dbc.query(ID__gt=0, ID__lt=3)
        assert len(results) == 2

    def test_query_invalid_operator(self, minimal_dbc: Path, sample_schema):
        """测试无效操作符."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        with pytest.raises(DBCQueryError, match="不支持的操作符"):
            dbc.query(ID__invalid=1)

    def test_get_single(self, minimal_dbc: Path, sample_schema):
        """测试获取单条."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        record = dbc.get(ID=1)
        assert record is not None
        assert record.get("ID") == 1

    def test_get_none(self, minimal_dbc: Path, sample_schema):
        """测试无匹配返回 None."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        record = dbc.get(ID=999)
        assert record is None

    def test_get_multiple_raises(self, minimal_dbc: Path, sample_schema):
        """测试多条匹配抛异常."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        with pytest.raises(DBCQueryError, match="期望单条记录"):
            dbc.get(ID__gt=0)

    def test_all(self, minimal_dbc: Path, sample_schema):
        """测试获取所有记录."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        records = dbc.all()
        assert len(records) == 2

    def test_edit(self, minimal_dbc: Path, sample_schema):
        """测试修改记录."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        record = dbc.get(ID=1)
        dbc.edit(record, Value=999)

        assert record.get("Value") == 999
        assert dbc._modified is True

    def test_delete(self, minimal_dbc: Path, sample_schema):
        """测试删除记录."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        deleted = dbc.delete(ID=1)
        assert deleted == 1
        assert len(dbc.records) == 1
        assert dbc._modified is True

    def test_delete_no_match(self, minimal_dbc: Path, sample_schema):
        """测试删除无匹配."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        deleted = dbc.delete(ID=999)
        assert deleted == 0
        assert len(dbc.records) == 2

    def test_add(self, minimal_dbc: Path, sample_schema):
        """测试添加记录."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        record = dbc.add(ID=3, Value=100)
        assert len(dbc.records) == 3
        assert record.get("ID") == 3
        assert record.get("Value") == 100
        assert dbc._modified is True

    def test_save(self, minimal_dbc: Path, sample_schema, tmp_path: Path):
        """测试保存文件."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        # 修改
        record = dbc.get(ID=1)
        dbc.edit(record, Value=999)

        # 保存到新文件
        output = tmp_path / "saved.dbc"
        dbc.save(output)

        # 重新加载验证
        dbc2 = DBCFile(output, schema=sample_schema)
        dbc2.load()

        assert len(dbc2.records) == 2
        saved_record = dbc2.get(ID=1)
        assert saved_record.get("Value") == 999

    def test_save_rebuilds_string_block(self, minimal_dbc: Path, sample_schema, tmp_path: Path):
        """测试保存时重建字符串块."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        # 修改字符串字段
        record = dbc.get(ID=1)
        dbc.edit(record, Name="Modified")

        # 保存
        output = tmp_path / "saved.dbc"
        dbc.save(output)

        # 验证
        dbc2 = DBCFile(output, schema=sample_schema)
        dbc2.load()
        saved_record = dbc2.get(ID=1)
        assert saved_record.get("Name") == "Modified"

    def test_to_json(self, minimal_dbc: Path, sample_schema):
        """测试导出 JSON."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        data = dbc.to_json()
        assert len(data) == 2
        assert data[0]["ID"] == 1
        assert data[1]["ID"] == 2

    def test_auto_load_schema(self, minimal_dbc: Path):
        """测试自动加载 schema."""
        dbc = DBCFile(minimal_dbc)
        dbc.load()

        # 无内置定义，使用推断（minimal_dbc 默认 3 字段）
        assert len(dbc.schema) == 3
        assert dbc.schema[0].name == "field_0"

    def test_repr_loaded(self, minimal_dbc: Path, sample_schema):
        """测试 repr（已加载）."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        r = repr(dbc)
        assert "DBCFile" in r
        assert "records=2" in r

    def test_repr_not_loaded(self):
        """测试 repr（未加载）."""
        dbc = DBCFile("test.dbc")
        r = repr(dbc)
        assert "not loaded" in r


class TestDBCSaveSafety:
    """save() 规范化与安全防护回归测试."""

    def test_save_canonical_leading_null_byte(
        self, minimal_dbc: Path, sample_schema, tmp_path: Path
    ):
        """字符串块以规范的前导 \\x00 开头（offset 0 = 空字符串）."""
        dbc = DBCFile(minimal_dbc, schema=sample_schema)
        dbc.load()

        output = tmp_path / "saved.dbc"
        dbc.save(output)

        data = output.read_bytes()
        string_block_size = struct.unpack("<I", data[16:20])[0]
        string_block = data[len(data) - string_block_size :]
        assert string_block.startswith(b"\x00")
        # 原 offset 0 的 "Hello" 应后移至 offset 1
        record = dbc.get(ID=1)
        assert record.raw[4:8] == struct.pack("<I", 1)
        assert record.get("Name") == "Hello"

    def test_save_idempotent(self, minimal_dbc: Path, sample_schema, tmp_path: Path):
        """save(load(save(x))) == save(x)."""
        out1 = tmp_path / "gen1.dbc"
        DBCFile(minimal_dbc, schema=sample_schema).load().save(out1)
        out2 = tmp_path / "gen2.dbc"
        DBCFile(out1, schema=sample_schema).load().save(out2)
        assert out1.read_bytes() == out2.read_bytes()

    def test_save_rejects_inferred_schema_with_strings(self, minimal_dbc: Path, tmp_path: Path):
        """未注册 schema 且含字符串块时拒绝保存，避免字符串悬空."""
        dbc = DBCFile(minimal_dbc)
        dbc.load()
        assert not dbc._schema_registered

        with pytest.raises(DBCError):
            dbc.save(tmp_path / "rejected.dbc")

    def test_save_allows_inferred_schema_without_strings(
        self, minimal_dbc_no_strings: Path, tmp_path: Path
    ):
        """无字符串字段的文件即使走推断 schema 也允许保存."""
        dbc = DBCFile(minimal_dbc_no_strings)
        dbc.load()

        output = tmp_path / "allowed.dbc"
        dbc.save(output)

        dbc2 = DBCFile(output).load()
        assert len(dbc2.records) == 2
        assert dbc2.query(field_0=1)[0].get("field_2") == 10
