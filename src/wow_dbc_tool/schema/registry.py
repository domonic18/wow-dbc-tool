"""Schema 注册表 - 管理所有 DBC 文件的字段定义."""

from __future__ import annotations

import json
from pathlib import Path

from wow_dbc_tool.schema.field_def import FieldDef


# generate-schemas.py 生成的类型映射到 FieldDef 支持类型
_TYPE_MAP = {
    "int": "int32",
    "uint": "uint32",
    "float": "float",
    "string": "string",
    "locstring": "string",
}


def _find_schemas_dir() -> Path | None:
    """查找 schemas 目录.

    尝试以下路径（按优先级）:
    1. 项目根目录下的 schemas/（开发模式）
    2. 包内嵌的 schemas/（pip 安装模式）

    Returns:
        schemas 目录路径，未找到返回 None
    """
    # 1. 从代码位置推导项目根目录
    try:
        code_dir = Path(__file__).resolve().parent  # src/wow_dbc_tool/schema/
        project_root = code_dir.parent.parent.parent  # wow-dbc-tool 根目录
        schemas_dir = project_root / "schemas"
        if schemas_dir.exists():
            return schemas_dir
    except (OSError, NameError):
        pass

    # 2. 尝试包内嵌路径（安装模式，通过 package_data 包含）
    try:
        code_dir = Path(__file__).resolve().parent
        embedded = code_dir / "schemas"
        if embedded.exists():
            return embedded
    except (OSError, NameError):
        pass

    return None


def _parse_project_schema(data: dict) -> list[FieldDef]:
    """解析 generate-schemas.py 生成的 schema JSON.

    输入格式:
    {
        "field_order": ["ID", "Name", ...],
        "properties": {
            "ID": {"type": "int32", "offset": 0},
            ...
        }
    }

    Args:
        data: JSON schema 数据

    Returns:
        FieldDef 列表
    """
    field_order = data.get("field_order", [])
    properties = data.get("properties", {})

    fields: list[FieldDef] = []
    for i, name in enumerate(field_order):
        prop = properties.get(name, {})
        raw_type = prop.get("type", "int32")
        field_type = _TYPE_MAP.get(raw_type, raw_type)
        # 如果映射后仍然不支持，回退为 int32
        if field_type not in FieldDef.VALID_TYPES:
            field_type = "int32"
        fields.append(FieldDef(name, field_type, i * 4))

    return fields


def _load_schemas_from_dir(schemas_dir: Path) -> dict[str, list[FieldDef]]:
    """从目录加载所有 schema 文件.

    Args:
        schemas_dir: schemas 目录路径

    Returns:
        {dbc_name: [FieldDef, ...]}
    """
    builtins: dict[str, list[FieldDef]] = {}
    if not schemas_dir.exists():
        return builtins

    for schema_path in schemas_dir.glob("*.schema.json"):
        try:
            with open(schema_path, encoding="utf-8") as f:
                data = json.load(f)

            table_name = data.get("table_name", schema_path.stem.replace(".schema", ""))
            dbc_name = f"{table_name}.dbc"
            fields = _parse_project_schema(data)

            if fields:
                builtins[dbc_name] = fields
        except (json.JSONDecodeError, OSError):
            continue

    return builtins


class SchemaRegistry:
    """管理所有 DBC 文件的字段定义.

    内置定义从 schemas/*.schema.json 自动加载，支持自定义注册和从文件加载。

    Attributes:
        _builtins: 内置字段定义字典（从 JSON schema 加载）
        _custom: 用户注册的自定义定义
    """

    _builtins: dict[str, list[FieldDef]] = {}
    _custom: dict[str, list[FieldDef]] = {}
    _loaded: bool = False

    @classmethod
    def _ensure_loaded(cls) -> None:
        """确保内置 schema 已加载（延迟加载）."""
        if cls._loaded:
            return

        schemas_dir = _find_schemas_dir()
        if schemas_dir:
            cls._builtins = _load_schemas_from_dir(schemas_dir)

        cls._loaded = True

    @classmethod
    def get(cls, dbc_name: str) -> list[FieldDef] | None:
        """获取指定 DBC 的字段定义.

        优先返回自定义定义，其次返回内置定义。

        Args:
            dbc_name: DBC 文件名（如 "Spell.dbc"）

        Returns:
            字段定义列表，未找到返回 None
        """
        cls._ensure_loaded()
        if dbc_name in cls._custom:
            return cls._custom[dbc_name]
        return cls._builtins.get(dbc_name)

    @classmethod
    def register(cls, dbc_name: str, fields: list[FieldDef]) -> None:
        """注册自定义字段定义.

        Args:
            dbc_name: DBC 文件名
            fields: 字段定义列表
        """
        cls._custom[dbc_name] = fields

    @classmethod
    def load_from_file(cls, path: str | Path) -> None:
        """从 JSON 文件加载字段定义.

        支持两种格式:
        1. Registry 格式: {"Spell.dbc": {"fields": [...]}}
        2. Project schema 格式: {"field_order": [...], "properties": {...}}

        Args:
            path: JSON 文件路径

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式错误
        """
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # 自动检测格式
        if "field_order" in data and "properties" in data:
            # Project schema 格式
            fields = _parse_project_schema(data)
            dbc_name = path.name.replace(".schema.json", ".dbc")
            cls.register(dbc_name, fields)
        else:
            # Registry 格式
            for dbc_name, schema_data in data.items():
                fields = [FieldDef.from_dict(fd) for fd in schema_data.get("fields", [])]
                cls.register(dbc_name, fields)

    @classmethod
    def list_builtins(cls) -> list[str]:
        """列出所有内置定义的 DBC 名称.

        Returns:
            DBC 文件名列表
        """
        cls._ensure_loaded()
        return list(cls._builtins.keys())

    @classmethod
    def list_all(cls) -> list[str]:
        """列出所有已知定义（内置 + 自定义）.

        Returns:
            DBC 文件名列表
        """
        cls._ensure_loaded()
        return list(set(cls._builtins.keys()) | set(cls._custom.keys()))

    @classmethod
    def clear_custom(cls) -> None:
        """清除所有自定义定义."""
        cls._custom.clear()

    @classmethod
    def infer_schema(cls, field_count: int, record_size: int) -> list[FieldDef]:
        """根据 field_count 和 record_size 推断字段布局.

        当没有 Schema 定义时，提供基础推断：
        - 如果 record_size == field_count * 4：所有字段为 int32
        - 否则：按 4 字节均分

        Args:
            field_count: 字段数量
            record_size: 记录大小

        Returns:
            推断的字段定义列表
        """
        if record_size == field_count * 4:
            return [FieldDef(f"field_{i}", "int32", i * 4) for i in range(field_count)]
        else:
            # 非标准情况，按 4 字节分段
            num_fields = record_size // 4
            return [FieldDef(f"field_{i}", "int32", i * 4) for i in range(num_fields)]
