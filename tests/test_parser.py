"""解析器单元测试."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from wow_dbc_tool.core.exceptions import DBCFormatError
from wow_dbc_tool.parser.header import DBCHeader
from wow_dbc_tool.parser.reader import DBCReader
from wow_dbc_tool.parser.writer import DBCWriter


class TestDBCHeader:
    """测试 DBCHeader."""

    def test_from_bytes_valid(self):
        """测试从有效字节解析文件头."""
        data = b"WDBC" + struct.pack("<4I", 100, 5, 20, 1024)
        header = DBCHeader.from_bytes(data)

        assert header.magic == "WDBC"
        assert header.record_count == 100
        assert header.field_count == 5
        assert header.record_size == 20
        assert header.string_block_size == 1024

    def test_from_bytes_invalid_magic(self):
        """测试无效魔数."""
        data = b"DB2 " + struct.pack("<4I", 100, 5, 20, 1024)
        with pytest.raises(DBCFormatError, match="Invalid WDBC magic"):
            DBCHeader.from_bytes(data)

    def test_from_bytes_too_short(self):
        """测试数据不足."""
        data = b"WDBC" + b"\x00" * 10
        with pytest.raises(DBCFormatError, match="文件头数据不足"):
            DBCHeader.from_bytes(data)

    def test_from_bytes_size_mismatch(self):
        """测试记录大小不匹配."""
        data = b"WDBC" + struct.pack("<4I", 100, 5, 30, 1024)
        with pytest.raises(DBCFormatError, match="记录大小不匹配"):
            DBCHeader.from_bytes(data)

    def test_to_bytes(self):
        """测试转为字节."""
        header = DBCHeader("WDBC", 100, 5, 20, 1024)
        data = header.to_bytes()

        assert len(data) == 20
        assert data[:4] == b"WDBC"
        assert struct.unpack("<4I", data[4:]) == (100, 5, 20, 1024)

    def test_to_dict(self):
        """测试转为字典."""
        header = DBCHeader("WDBC", 100, 5, 20, 1024)
        d = header.to_dict()

        assert d["magic"] == "WDBC"
        assert d["record_count"] == 100
        assert d["field_count"] == 5

    def test_data_size(self):
        """测试数据区大小计算."""
        header = DBCHeader("WDBC", 10, 5, 20, 100)
        assert header.data_size == 200

    def test_total_file_size(self):
        """测试文件总大小计算."""
        header = DBCHeader("WDBC", 10, 5, 20, 100)
        assert header.total_file_size == 20 + 200 + 100


class TestDBCReader:
    """测试 DBCReader."""

    def test_read_minimal(self, minimal_dbc: Path):
        """测试读取最小 DBC 文件."""
        reader = DBCReader(minimal_dbc)
        reader.read()

        assert reader.header is not None
        assert reader.header.magic == "WDBC"
        assert reader.header.record_count == 2
        assert len(reader.records) == 2
        assert len(reader.string_block) > 0

    def test_read_file_not_found(self):
        """测试文件不存在."""
        reader = DBCReader("/nonexistent/file.dbc")
        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_get_string(self, minimal_dbc: Path):
        """测试字符串解析."""
        reader = DBCReader(minimal_dbc)
        reader.read()

        # 第一个字符串在偏移 0
        s = reader.get_string(0)
        assert s == "Hello"

        # 第二个字符串
        hello_len = len("Hello") + 1  # 包含 \0
        s = reader.get_string(hello_len)
        assert s == "World"

    def test_get_string_invalid_offset(self, minimal_dbc: Path):
        """测试无效偏移."""
        reader = DBCReader(minimal_dbc)
        reader.read()

        with pytest.raises(DBCFormatError, match="偏移量越界"):
            reader.get_string(99999)

    def test_get_string_negative_offset(self, minimal_dbc: Path):
        """测试负偏移."""
        reader = DBCReader(minimal_dbc)
        reader.read()

        with pytest.raises(DBCFormatError, match="偏移量越界"):
            reader.get_string(-1)


class TestDBCWriter:
    """测试 DBCWriter."""

    def test_write_roundtrip(self, tmp_path: Path):
        """测试写入后读取一致性."""
        output = tmp_path / "output.dbc"
        header = DBCHeader("WDBC", 0, 2, 8, 0)  # 记录数在写入时更新

        writer = DBCWriter(output, header)

        # 添加字符串
        offset1 = writer.add_string("Test1")
        offset2 = writer.add_string("Test2")

        # 添加记录
        record1 = struct.pack("<2I", 1, offset1)
        record2 = struct.pack("<2I", 2, offset2)
        writer.add_record(record1)
        writer.add_record(record2)

        writer.write()

        # 读取验证
        reader = DBCReader(output)
        reader.read()

        assert reader.header.record_count == 2
        assert len(reader.records) == 2
        assert reader.get_string(offset1) == "Test1"
        assert reader.get_string(offset2) == "Test2"

    def test_add_string_deduplication(self, tmp_path: Path):
        """测试字符串去重."""
        output = tmp_path / "output.dbc"
        header = DBCHeader("WDBC", 0, 1, 4, 0)

        writer = DBCWriter(output, header)

        offset1 = writer.add_string("same")
        offset2 = writer.add_string("same")

        assert offset1 == offset2

    def test_add_record_size_mismatch(self, tmp_path: Path):
        """测试记录大小不匹配."""
        output = tmp_path / "output.dbc"
        header = DBCHeader("WDBC", 0, 2, 8, 0)

        writer = DBCWriter(output, header)

        with pytest.raises(ValueError, match="记录大小不匹配"):
            writer.add_record(b"\x00" * 4)  # 4 bytes != 8 bytes

    def test_string_block_property(self, tmp_path: Path):
        """测试字符串块属性."""
        output = tmp_path / "output.dbc"
        header = DBCHeader("WDBC", 0, 1, 4, 0)

        writer = DBCWriter(output, header)
        writer.add_string("hello")

        assert writer.string_block == b"hello\x00"
