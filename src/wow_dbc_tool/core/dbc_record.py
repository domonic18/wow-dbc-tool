"""DBC 记录类 - 单条记录的解析和操作."""

from __future__ import annotations

import struct
from typing import Any

from wow_dbc_tool.core.exceptions import DBCSchemaError
from wow_dbc_tool.schema.field_def import FieldDef


class DBCRecord:
    """单条 DBC 记录.

    封装原始字节数据，通过 Schema 定义解析字段值。
    支持读取和修改字段值。

    Attributes:
        _raw: 原始字节数据
        _schema: 字段定义列表
        _string_block: 字符串块（用于解析 string 类型）
    """

    def __init__(
        self,
        raw_data: bytes,
        schema: list[FieldDef],
        string_block: bytes,
    ):
        """初始化记录.

        Args:
            raw_data: 记录的原始字节数据
            schema: 字段定义列表
            string_block: 字符串块字节数据
        """
        self._raw = bytearray(raw_data)
        self._schema = schema
        self._string_block = string_block
        self._schema_by_name: dict[str, FieldDef] = {f.name: f for f in schema}

    def get(self, field_name: str) -> int | float | str | None:
        """获取字段值.

        优先返回 pending strings（由 set() 设置但未保存的值），
        然后尝试从 raw 数据解析。

        Args:
            field_name: 字段名

        Returns:
            字段值。uint32/int32 -> int, float -> float, string -> str

        Raises:
            DBCSchemaError: 字段不存在
        """
        field = self._schema_by_name.get(field_name)
        if field is None:
            raise DBCSchemaError(f"字段不存在: {field_name!r}")

        # 优先返回 pending strings
        if hasattr(self, "_pending_strings") and field_name in self._pending_strings:
            return self._pending_strings[field_name]

        offset = field.offset
        raw = self._raw[offset : offset + 4]

        if field.type == "uint32":
            return struct.unpack("<I", raw)[0]
        elif field.type == "int32":
            return struct.unpack("<i", raw)[0]
        elif field.type == "float":
            return struct.unpack("<f", raw)[0]
        elif field.type == "string":
            string_offset = struct.unpack("<I", raw)[0]
            return self._get_string_at_offset(string_offset)
        else:
            raise DBCSchemaError(f"不支持的字段类型: {field.type!r}")

    def set(self, field_name: str, value: int | float | str) -> None:
        """设置字段值（修改内部 raw_data）.

        注意：对于 string 类型，此处仅修改偏移量占位符。
        实际字符串块在保存时由 DBCFile 重建。

        Args:
            field_name: 字段名
            value: 新值

        Raises:
            DBCSchemaError: 字段不存在或类型不匹配
        """
        field = self._schema_by_name.get(field_name)
        if field is None:
            raise DBCSchemaError(f"字段不存在: {field_name!r}")

        offset = field.offset

        if field.type == "uint32":
            if not isinstance(value, int):
                raise DBCSchemaError(f"字段 {field_name!r} 需要 int, 得到 {type(value).__name__}")
            self._raw[offset : offset + 4] = struct.pack("<I", value & 0xFFFFFFFF)
        elif field.type == "int32":
            if not isinstance(value, int):
                raise DBCSchemaError(f"字段 {field_name!r} 需要 int, 得到 {type(value).__name__}")
            self._raw[offset : offset + 4] = struct.pack("<i", value)
        elif field.type == "float":
            if not isinstance(value, (int, float)):
                raise DBCSchemaError(f"字段 {field_name!r} 需要 float, 得到 {type(value).__name__}")
            self._raw[offset : offset + 4] = struct.pack("<f", float(value))
        elif field.type == "string":
            if not isinstance(value, str):
                raise DBCSchemaError(f"字段 {field_name!r} 需要 str, 得到 {type(value).__name__}")
            # 字符串类型：写入占位偏移量，保存时重建
            # 使用特殊标记值 0xFFFFFFFF 表示需要重建
            self._raw[offset : offset + 4] = struct.pack("<I", 0xFFFFFFFF)
            # 存储字符串值供后续重建使用
            if not hasattr(self, "_pending_strings"):
                self._pending_strings = {}
            self._pending_strings[field_name] = value
        else:
            raise DBCSchemaError(f"不支持的字段类型: {field.type!r}")

    def to_dict(self) -> dict[str, Any]:
        """转为字典（用于 JSON 输出）.

        Returns:
            包含所有字段值的字典
        """
        result: dict[str, Any] = {}
        for field in self._schema:
            try:
                result[field.name] = self.get(field.name)
            except (DBCSchemaError, struct.error):
                result[field.name] = None
        return result

    @property
    def raw(self) -> bytes:
        """获取原始字节（用于写入）.

        Returns:
            记录的字节数据
        """
        return bytes(self._raw)

    def _get_string_at_offset(self, offset: int) -> str:
        """从字符串块获取字符串.

        Args:
            offset: 字符串偏移量

        Returns:
            解码后的字符串
        """
        if offset < 0 or offset >= len(self._string_block):
            return ""

        end = self._string_block.find(b"\x00", offset)
        if end == -1:
            end = len(self._string_block)

        raw = self._string_block[offset:end]
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def __repr__(self) -> str:
        try:
            id_val = self.get("ID")
            return f"DBCRecord(ID={id_val})"
        except (DBCSchemaError, struct.error):
            return f"DBCRecord(raw={len(self._raw)} bytes)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DBCRecord):
            return NotImplemented
        return self._raw == other._raw

    def get_pending_strings(self) -> dict[str, str]:
        """获取待写入的字符串字段.

        Returns:
            字段名到字符串值的映射
        """
        return getattr(self, "_pending_strings", {})
