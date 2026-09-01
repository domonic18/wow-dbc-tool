"""DBC 文件操作主类 - 核心 API."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from wow_dbc_tool.core.dbc_record import DBCRecord
from wow_dbc_tool.core.exceptions import DBCError, DBCNotLoadedError, DBCQueryError, DBCSchemaError
from wow_dbc_tool.parser.header import DBCHeader
from wow_dbc_tool.parser.reader import DBCReader
from wow_dbc_tool.parser.writer import DBCWriter
from wow_dbc_tool.schema.field_def import FieldDef
from wow_dbc_tool.schema.registry import SchemaRegistry

# 支持的查询操作符
OPERATORS: dict[str, Any] = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and b is not None and a > b,
    "gte": lambda a, b: a is not None and b is not None and a >= b,
    "lt": lambda a, b: a is not None and b is not None and a < b,
    "lte": lambda a, b: a is not None and b is not None and a <= b,
    "contains": lambda a, b: b is not None and str(b) in str(a),
}


class DBCFile:
    """DBC 文件操作主类.

    提供加载、查询、修改、保存等完整 CRUD 操作。

    Attributes:
        path: 文件路径
        schema: 字段定义列表
        header: 文件头
        records: 记录列表
    """

    def __init__(
        self,
        path: str | Path,
        schema: list[FieldDef] | None = None,
    ):
        """初始化 DBC 文件对象.

        Args:
            path: DBC 文件路径
            schema: 字段定义列表，None 时自动加载
        """
        self.path = Path(path)
        self._schema = schema
        self._schema_registered = schema is not None
        self.header: DBCHeader | None = None
        self.records: list[DBCRecord] = []
        self._string_block: bytes = b""
        self._modified = False

    def load(self) -> DBCFile:
        """从文件加载.

        Returns:
            self（链式调用）

        Raises:
            FileNotFoundError: 文件不存在
            DBCFormatError: 文件格式错误
        """
        reader = DBCReader(self.path)
        reader.read()

        self.header = reader.header
        self._string_block = reader.string_block

        # 自动加载 schema
        if self._schema is None:
            self._schema = self._auto_load_schema()

        # 创建记录对象
        self.records = [DBCRecord(raw, self._schema, self._string_block) for raw in reader.records]

        self._modified = False
        return self

    def query(self, **filters: Any) -> list[DBCRecord]:
        """按字段值过滤查询.

        支持操作符后缀：
        - ID=123: 精确匹配（默认 eq）
        - ID__gt=100: 大于
        - ID__lt=200: 小于
        - Name__contains="Fire": 字符串包含

        多条件为 AND 关系。

        Args:
            **filters: 过滤条件

        Returns:
            匹配的记录列表

        Raises:
            DBCNotLoadedError: 文件尚未加载
            DBCQueryError: 操作符不支持或字段不存在
        """
        self._ensure_loaded()

        result = self.records[:]
        for key, value in filters.items():
            result = self._apply_filter(result, key, value)

        return result

    def get(self, **filters: Any) -> DBCRecord | None:
        """获取单条记录.

        Args:
            **filters: 过滤条件

        Returns:
            匹配的记录，无匹配返回 None

        Raises:
            DBCQueryError: 多条记录匹配
        """
        results = self.query(**filters)
        if len(results) == 0:
            return None
        if len(results) > 1:
            raise DBCQueryError(f"期望单条记录，但找到 {len(results)} 条")
        return results[0]

    def all(self) -> list[DBCRecord]:
        """获取所有记录.

        Returns:
            所有记录列表

        Raises:
            DBCNotLoadedError: 文件尚未加载
        """
        self._ensure_loaded()
        return self.records[:]

    def edit(self, record: DBCRecord, **changes: Any) -> DBCRecord:
        """修改记录字段.

        Args:
            record: 要修改的记录
            **changes: 字段名和新值的映射

        Returns:
            修改后的记录
        """
        for field_name, value in changes.items():
            record.set(field_name, value)
        self._modified = True
        return record

    def delete(self, **filters: Any) -> int:
        """删除匹配记录.

        Args:
            **filters: 过滤条件

        Returns:
            删除的记录数量
        """
        to_delete = self.query(**filters)
        for record in to_delete:
            self.records.remove(record)
        if to_delete:
            self._modified = True
        return len(to_delete)

    def add(self, **values: Any) -> DBCRecord:
        """添加新记录.

        创建一条新记录，所有未指定的字段默认为 0 或空字符串。

        Args:
            **values: 字段名和值的映射

        Returns:
            新创建的记录
        """
        self._ensure_loaded()

        # 创建空记录
        record_size = self.header.record_size if self.header else len(self._schema or []) * 4
        raw = bytes(record_size)

        # 创建记录对象
        assert self._schema is not None
        record = DBCRecord(raw, self._schema, self._string_block)

        # 设置字段值
        for field_name, value in values.items():
            record.set(field_name, value)

        self.records.append(record)
        self._modified = True
        return record

    def save(self, path: str | Path | None = None) -> None:
        """保存到文件.

        自动重建字符串块（去重 + 排序）。字符串块以规范的空字符串
        开头（offset 0 = ""），与官方/MCC 工具导出的格式保持一致，
        保证 load→save 往返字节稳定。

        Args:
            path: 输出路径，None 使用原路径

        Raises:
            DBCError: schema 为推断结果且原文件含字符串时拒绝保存，
                避免字符串字段缺失导致字符串块清空、引用悬空。
        """
        self._ensure_loaded()
        assert self.header is not None

        if not self._schema_registered and len(self._string_block) > 1:
            raise DBCError(
                f"未找到 {self.path.name} 的注册 schema（当前使用推断 schema），"
                "拒绝保存：推断 schema 缺少字符串字段定义，保存会清空字符串块"
                "并使所有字符串引用悬空。请先通过 SchemaRegistry 注册该 DBC 的字段定义。"
            )

        output_path = Path(path) if path else self.path

        # 重建字符串块
        writer = DBCWriter(
            output_path,
            header=DBCHeader(
                magic="WDBC",
                record_count=0,  # 会在 write() 中更新
                field_count=self.header.field_count,
                record_size=self.header.record_size,
                string_block_size=0,  # 会在 write() 中更新
            ),
        )

        # 收集所有字符串并去重；offset 0 恒为空字符串（规范约定）
        string_offsets: dict[str, int] = {"": 0}
        string_block = bytearray(b"\x00")

        for record in self.records:
            # 处理 pending strings（由 set() 设置的字符串）
            pending = record.get_pending_strings()

            schema = self._schema or []
            for field in schema:
                if field.type == "string":
                    if field.name in pending:
                        s = pending[field.name]
                    else:
                        try:
                            raw_val = record.get(field.name)
                            s = "" if raw_val is None else str(raw_val)
                        except (DBCSchemaError, struct.error):
                            s = ""

                    if s not in string_offsets:
                        offset = len(string_block)
                        encoded = s.encode("utf-8") + b"\x00"
                        string_block.extend(encoded)
                        string_offsets[s] = offset

                    # 更新记录中的偏移量
                    offset = string_offsets[s]
                    record._raw[field.offset : field.offset + 4] = struct.pack("<I", offset)

        # 更新 writer 的字符串块
        writer._string_block = string_block
        writer._string_offsets = string_offsets

        # 添加所有记录
        for record in self.records:
            writer.add_record(record.raw)

        # 写入文件
        writer.write()
        self._modified = False

        # 更新内部状态
        self.path = output_path
        self._string_block = bytes(string_block)
        for record in self.records:
            record._string_block = self._string_block

    def to_json(self) -> list[dict[str, Any]]:
        """导出为 JSON 可序列化的列表.

        Returns:
            记录字典列表
        """
        return [record.to_dict() for record in self.records]

    @property
    def schema(self) -> list[FieldDef]:
        """获取当前字段定义.

        Returns:
            字段定义列表
        """
        return self._schema or []

    def _auto_load_schema(self) -> list[FieldDef]:
        """自动加载字段定义.

        先尝试从注册表获取，失败则推断。

        Returns:
            字段定义列表
        """
        dbc_name = self.path.name

        # 尝试内置/自定义定义
        schema = SchemaRegistry.get(dbc_name)
        if schema is not None:
            self._schema_registered = True
            return schema

        self._schema_registered = False

        # 尝试推断
        if self.header:
            return SchemaRegistry.infer_schema(
                self.header.field_count,
                self.header.record_size,
            )

        # 默认：空定义
        return []

    def _ensure_loaded(self) -> None:
        """确保文件已加载.

        Raises:
            DBCNotLoadedError: 文件尚未加载
        """
        if self.header is None:
            raise DBCNotLoadedError(f"DBC 文件尚未加载: {self.path}. 请先调用 .load()")

    def _apply_filter(
        self,
        records: list[DBCRecord],
        key: str,
        value: Any,
    ) -> list[DBCRecord]:
        """应用单个过滤条件.

        Args:
            records: 记录列表
            key: 字段名（可带操作符后缀，如 "ID__gt"）
            value: 比较值

        Returns:
            过滤后的记录列表
        """
        # 解析字段名和操作符
        if "__" in key:
            field_name, op = key.split("__", 1)
        else:
            field_name, op = key, "eq"

        if op not in OPERATORS:
            raise DBCQueryError(
                f"不支持的操作符: {op!r}. " f"支持的操作符: {list(OPERATORS.keys())}"
            )

        op_func = OPERATORS[op]
        result: list[DBCRecord] = []

        for record in records:
            try:
                field_value = record.get(field_name)
                if op_func(field_value, value):
                    result.append(record)
            except DBCSchemaError:
                # 字段不存在，不匹配
                pass

        return result

    def __repr__(self) -> str:
        if self.header is None:
            return f"DBCFile({self.path}, not loaded)"
        return (
            f"DBCFile({self.path}, " f"records={len(self.records)}, " f"modified={self._modified})"
        )
