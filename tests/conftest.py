"""测试 fixtures 和工具函数."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest


def create_minimal_dbc(
    path: Path,
    record_count: int = 2,
    field_count: int = 3,
    strings: list[str] | None = None,
) -> Path:
    """创建最小测试 DBC 文件.

    默认创建 3 个字段（ID uint32, Name string, Value uint32），
    与 sample_schema fixture 保持一致。

    Args:
        path: 输出路径
        record_count: 记录数量
        field_count: 字段数量（每个 4 bytes）
        strings: 字符串列表，None 时自动生成

    Returns:
        输出路径
    """
    record_size = field_count * 4

    # 默认字符串
    if strings is None:
        strings = ["Hello", "World"]

    # 构建字符串块
    string_block = bytearray()
    string_offsets: dict[str, int] = {}
    for s in strings:
        if s not in string_offsets:
            offset = len(string_block)
            string_block.extend(s.encode("utf-8") + b"\x00")
            string_offsets[s] = offset

    # 构建记录: ID(uint32) + Name(string) + Value(uint32)
    records_data = bytearray()
    for i in range(record_count):
        # 字段 0: ID
        records_data.extend(struct.pack("<I", i + 1))
        # 字段 1: 字符串偏移 (Name)
        if i < len(strings):
            records_data.extend(struct.pack("<I", string_offsets[strings[i]]))
        else:
            records_data.extend(struct.pack("<I", 0))
        # 字段 2: Value
        records_data.extend(struct.pack("<I", (i + 1) * 10))
        # 其余字段填充 0
        for _ in range(field_count - 3):
            records_data.extend(struct.pack("<I", 0))

    # 文件头
    header = b"WDBC"
    header += struct.pack("<4I", record_count, field_count, record_size, len(string_block))

    with open(path, "wb") as f:
        f.write(header)
        f.write(records_data)
        f.write(string_block)

    return path


def create_dbc_with_data(
    path: Path,
    records: list[dict],
    field_names: list[str],
    string_fields: set[str] | None = None,
) -> Path:
    """根据数据创建 DBC 文件.

    Args:
        path: 输出路径
        records: 记录数据列表
        field_names: 字段名列表
        string_fields: 字符串字段集合

    Returns:
        输出路径
    """
    field_count = len(field_names)
    record_size = field_count * 4
    string_fields = string_fields or set()

    # 收集所有字符串
    all_strings: set[str] = set()
    for record in records:
        for field in string_fields:
            if field in record:
                val = record[field]
                if val:
                    all_strings.add(str(val))

    # 构建字符串块
    string_block = bytearray()
    string_offsets: dict[str, int] = {}
    for s in sorted(all_strings):
        offset = len(string_block)
        string_block.extend(s.encode("utf-8") + b"\x00")
        string_offsets[s] = offset

    # 构建记录
    records_data = bytearray()
    for record in records:
        for field_name in field_names:
            if field_name in string_fields:
                val = record.get(field_name, "")
                if val and str(val) in string_offsets:
                    records_data.extend(struct.pack("<I", string_offsets[str(val)]))
                else:
                    records_data.extend(struct.pack("<I", 0))
            else:
                val = record.get(field_name, 0)
                if isinstance(val, float):
                    records_data.extend(struct.pack("<f", val))
                else:
                    records_data.extend(struct.pack("<I", int(val or 0)))

    # 文件头
    header = b"WDBC"
    header += struct.pack("<4I", len(records), field_count, record_size, len(string_block))

    with open(path, "wb") as f:
        f.write(header)
        f.write(records_data)
        f.write(string_block)

    return path


@pytest.fixture
def minimal_dbc(tmp_path: Path) -> Path:
    """最小测试 DBC fixture."""
    return create_minimal_dbc(tmp_path / "minimal.dbc")


@pytest.fixture
def sample_schema():
    """示例字段定义 fixture."""
    from wow_dbc_tool.schema.field_def import FieldDef

    return [
        FieldDef("ID", "uint32", 0),
        FieldDef("Name", "string", 4),
        FieldDef("Value", "uint32", 8),
    ]
