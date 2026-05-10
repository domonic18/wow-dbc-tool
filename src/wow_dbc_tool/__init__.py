"""wow-dbc-tool - 魔兽世界 3.3.5 DBC 文件操作工具."""

from wow_dbc_tool.core.dbc_file import DBCFile
from wow_dbc_tool.core.dbc_record import DBCRecord
from wow_dbc_tool.schema.field_def import FieldDef
from wow_dbc_tool.schema.registry import SchemaRegistry

__all__ = [
    "DBCFile",
    "DBCRecord",
    "FieldDef",
    "SchemaRegistry",
]
